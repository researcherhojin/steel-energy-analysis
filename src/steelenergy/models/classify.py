from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from steelenergy import config, features
from steelenergy.models.split import Split

TARGET = "load_type"
CALENDAR = features.CALENDAR
SEASONAL = features.CALENDAR + features.SEASON
HISTORY = SEASONAL + features.HISTORY
SAME_INTERVAL = HISTORY + features.SAME_INTERVAL


class ScheduleLookup:
    """Most frequent label per key (e.g. weekend flag × slot) in the training data."""

    def __init__(self, keys=("is_weekend", "slot")):
        self.keys = list(keys)

    def fit(self, X: pd.DataFrame, y: pd.Series):
        idx = pd.MultiIndex.from_frame(X[self.keys])
        self.table_ = pd.Series(y.values, index=idx).groupby(level=self.keys).agg(
            lambda s: s.mode().iloc[0])
        self.fallback_ = y.mode().iloc[0]
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        idx = pd.MultiIndex.from_frame(X[self.keys])
        return self.table_.reindex(idx).fillna(self.fallback_).values


def _logistic(cols):
    categorical = [c for c in ("dow",) if c in cols]
    numeric = [c for c in cols if c not in categorical]
    pre = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
        ("num", StandardScaler(), numeric),
    ])
    return make_pipeline(pre, LogisticRegression(**config.LOGISTIC))


def _hgb():
    return HistGradientBoostingClassifier(**config.HGB_CLASSIFIER, random_state=config.SEED)


def candidates() -> dict:
    """Name → (factory, columns). The first four are the attempts discussed in the notebook."""
    with_season = ["is_winter", "is_weekend", "slot"]
    return {
        "schedule_lookup": (ScheduleLookup, ["is_weekend", "slot"]),
        "hgb_no_season": (_hgb, CALENDAR + ["month"] + features.HISTORY),
        # In Jan–Oct, is_winter and month <= 2 select the same rows, so the tree's choice
        # between them (and hence Nov–Dec predictions) comes down to column order.
        "hgb_season_month_first": (_hgb, CALENDAR[:3] + ["month"] + CALENDAR[3:] + features.SEASON
                                   + features.HISTORY),
        "hgb_season_month_last": (_hgb, HISTORY + ["month"]),
        "schedule_lookup_season": (lambda: ScheduleLookup(with_season), with_season),
        "logistic": (lambda: _logistic(HISTORY), HISTORY),
        "hgb": (_hgb, HISTORY),
        "hgb_same_interval": (_hgb, SAME_INTERVAL),
    }


def reverse_check(df: pd.DataFrame, train_months=range(3, 13), test_months=(1, 2)) -> pd.DataFrame:
    """Fit on Mar–Dec, score Jan–Feb: a separate, reversed split.

    The season fix was chosen after looking at Nov–Dec, so those scores are exploratory.
    Jan–Feb is not untouched (it was in the original training window and in the schedule
    exploration), but it is a second winter period scored by a model that never trained on
    it. With one year of data this is the strongest check available; new data would be better.
    """
    data = df.dropna()
    train = data[data["month"].isin(list(train_months))]
    test = data[data["month"].isin(list(test_months))]
    rows = []
    for name in ("schedule_lookup", "schedule_lookup_season", "hgb"):
        make, cols = candidates()[name]
        model = make().fit(train[cols], train[TARGET].astype(str))
        rows.append({"model": name, **_score(test[TARGET].astype(str), model.predict(test[cols]))})
    return pd.DataFrame(rows).set_index("model")


@dataclass
class ClassifierReport:
    scores: pd.DataFrame
    confusion: pd.DataFrame
    confusions: dict
    errors_by_daytype: pd.DataFrame
    reverse: pd.DataFrame | None = None
    labels: list = field(default_factory=lambda: list(config.LOAD_TYPES))


def _score(y_true, y_pred) -> dict:
    return {"macro_f1": f1_score(y_true, y_pred, average="macro"),
            "accuracy": accuracy_score(y_true, y_pred)}


def evaluate(split: Split, selected: str = "hgb") -> ClassifierReport:
    """Validation scores for every candidate; test scores after refitting on train+valid."""
    rows = []
    cms, preds = {}, {}
    for name, (make, cols) in candidates().items():
        y_tr, y_va = split.train[TARGET].astype(str), split.valid[TARGET].astype(str)
        model = make().fit(split.train[cols], y_tr)
        val = _score(y_va, model.predict(split.valid[cols]))
        tv = split.train_valid
        model = make().fit(tv[cols], tv[TARGET].astype(str))
        pred = model.predict(split.test[cols])
        y_te = split.test[TARGET].astype(str)
        test = _score(y_te, pred)
        cms[name] = pd.DataFrame(confusion_matrix(y_te, pred, labels=config.LOAD_TYPES),
                                 index=config.LOAD_TYPES, columns=config.LOAD_TYPES)
        preds[name] = pred
        rows.append({"model": name, "features": "+".join(_feature_label(cols)),
                     "valid_macro_f1": val["macro_f1"], "valid_accuracy": val["accuracy"],
                     "test_macro_f1": test["macro_f1"], "test_accuracy": test["accuracy"]})
    wrong = pd.Series(preds[selected] != split.test[TARGET].astype(str).values, index=split.test.index)
    daytype = split.test["is_weekend"].map({0: "평일", 1: "주말"})
    errors = pd.DataFrame({"slots": daytype.value_counts(), "errors": wrong.groupby(daytype).sum()})
    errors["error_rate"] = errors["errors"] / errors["slots"]
    errors["share_of_errors"] = errors["errors"] / errors["errors"].sum()
    return ClassifierReport(pd.DataFrame(rows).set_index("model"), cms[selected], cms, errors)


def run(split: Split, df: pd.DataFrame) -> ClassifierReport:
    """Forward evaluation on the chronological split plus the reversed-split check."""
    report = evaluate(split)
    report.reverse = reverse_check(df)
    return report


def column_order_check(split: Split, seeds=(0, 42)) -> pd.DataFrame:
    """Test macro-F1 for the two month-including column orders across seeds.

    If the score moves with column order but not with the seed, the tree is breaking a tie
    between two features that select the same training rows (is_winter and month <= 2).
    """
    tv, y = split.train_valid, split.train_valid[TARGET].astype(str)
    rows = []
    for name in ("hgb_season_month_first", "hgb_season_month_last"):
        cols = candidates()[name][1]
        for seed in seeds:
            model = HistGradientBoostingClassifier(**config.HGB_CLASSIFIER, random_state=seed)
            pred = model.fit(tv[cols], y).predict(split.test[cols])
            rows.append({"model": name, "seed": seed,
                         "test_macro_f1": f1_score(split.test[TARGET].astype(str), pred, average="macro")})
    return pd.DataFrame(rows).pivot(index="model", columns="seed", values="test_macro_f1")


def _feature_label(cols) -> list[str]:
    groups = []
    if set(cols) & set(features.CALENDAR):
        groups.append("calendar")
    if "month" in cols:
        groups.append("month")
    if set(cols) & set(features.SEASON):
        groups.append("season")
    if set(cols) & set(features.HISTORY):
        groups.append("history")
    if set(cols) & set(features.SAME_INTERVAL):
        groups.append("same-interval")
    return groups
