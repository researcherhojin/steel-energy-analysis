from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from steelenergy import config, features
from steelenergy.models.split import Split

TARGET = "kwh"
# One-step-ahead forecast: only what is known at the end of interval t-1.
FEATURES = features.CALENDAR + features.SEASON + features.HISTORY


def metrics(y_true, y_pred) -> dict:
    """MAE, RMSE and WAPE. MAPE is undefined-ish here: half the slots sit near 3 kWh."""
    err = np.asarray(y_true) - np.asarray(y_pred)
    return {"mae": float(np.abs(err).mean()),
            "rmse": float(np.sqrt((err**2).mean())),
            "wape": float(np.abs(err).sum() / np.abs(y_true).sum())}


class Naive:
    def __init__(self, column: str):
        self.column = column

    def fit(self, X, y):
        return self

    def predict(self, X):
        return X[self.column].values


def ridge():
    pre = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), ["dow", "hour"]),
        ("num", StandardScaler(), [c for c in FEATURES if c not in ("dow", "hour")]),
    ])
    return make_pipeline(pre, Ridge(alpha=config.RIDGE_ALPHA))


def hgb():
    return HistGradientBoostingRegressor(**config.HGB_REGRESSOR, random_state=config.SEED)


CANDIDATES = {
    "naive_last": lambda: Naive("kwh_lag1"),
    "naive_day": lambda: Naive("kwh_lag96"),
    "naive_week": lambda: Naive("kwh_lag672"),
    "ridge": ridge,
    "hgb": hgb,
}


@dataclass
class RegressionReport:
    scores: pd.DataFrame
    best_naive: str
    test_predictions: pd.DataFrame
    error_by_hour: pd.DataFrame
    importance: pd.DataFrame

    @property
    def example_week(self) -> pd.DataFrame:
        """Actual, forecast and naive values for `config.FORECAST_WEEK` (operating days)."""
        day = self.test_predictions["operating_day"]
        return self.test_predictions.loc[day.between(*config.FORECAST_WEEK), ["kwh", "pred", "naive"]]

    @property
    def test_daily(self) -> pd.DataFrame:
        return self.test_predictions.groupby("operating_day")[["kwh", "pred", "naive"]].sum()

    @property
    def test_mean_kwh(self) -> float:
        """Mean 15-min kWh over the test period, the scale to read the MAE against."""
        return float(self.test_predictions["kwh"].mean())


def evaluate(split: Split, selected: str = "hgb") -> RegressionReport:
    rows, preds = [], {}
    for name, make in CANDIDATES.items():
        model = make().fit(split.train[FEATURES], split.train[TARGET])
        val = metrics(split.valid[TARGET], model.predict(split.valid[FEATURES]))
        model = make().fit(split.train_valid[FEATURES], split.train_valid[TARGET])
        preds[name] = model.predict(split.test[FEATURES])
        test = metrics(split.test[TARGET], preds[name])
        rows.append({"model": name, **{f"valid_{k}": v for k, v in val.items()},
                     **{f"test_{k}": v for k, v in test.items()}})
        if name == selected:
            final = model

    scores = pd.DataFrame(rows).set_index("model")
    best_naive = scores.filter(like="naive", axis=0)["valid_mae"].idxmin()
    scores["test_mae_vs_best_naive"] = 1 - scores["test_mae"] / scores.loc[best_naive, "test_mae"]

    out = split.test[["operating_day", "hour", "is_weekend", TARGET]].copy()
    out["pred"] = preds[selected]
    out["naive"] = preds[best_naive]
    abs_err = (out[TARGET] - out["pred"]).abs()
    by_hour = abs_err.groupby(out["hour"]).mean().rename("mae").to_frame()
    by_hour["naive_mae"] = (out[TARGET] - out["naive"]).abs().groupby(out["hour"]).mean()

    imp = permutation_importance(final, split.test[FEATURES], split.test[TARGET],
                                 scoring="neg_mean_absolute_error", n_repeats=config.PERMUTATION_REPEATS,
                                 random_state=config.SEED)
    importance = pd.DataFrame({"mae_increase": imp.importances_mean, "std": imp.importances_std},
                              index=FEATURES).sort_values("mae_increase", ascending=False)
    return RegressionReport(scores, best_naive, out, by_hour, importance)


def out_of_fold_forecast(folds) -> pd.Series:
    """One-step forecasts where each month is predicted by a model fit only on earlier months."""
    parts = []
    for _, train, test in folds:
        model = hgb().fit(train[FEATURES], train[TARGET])
        parts.append(pd.Series(model.predict(test[FEATURES]), index=test.index))
    return pd.concat(parts).rename("expected_kwh")
