from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from steelenergy import config

MAD_TO_SIGMA = 1.4826
IFOREST_FEATURES = ["kwh", "lag_kvarh", "lead_kvarh", "lag_pf", "lead_pf",
                    "hour_sin", "hour_cos", "is_weekend", "is_winter"]


def robust_z(residual: pd.Series, groups: list[pd.Series]) -> pd.Series:
    """Residual scaled by the MAD of its own (weekend, hour) cell.

    A single global scale would flag every daytime slot, because night residuals are near zero.
    """
    med = residual.groupby(groups).transform("median")
    mad = (residual - med).abs().groupby(groups).transform("median") * MAD_TO_SIGMA
    floor = mad[mad > 0].quantile(0.05)  # idle hours can have MAD ≈ 0
    return (residual - med) / mad.clip(lower=floor)


def day_type(df: pd.DataFrame) -> pd.Series:
    """Weekday / Saturday / Sunday. Saturdays run a partial shift and behave unlike either."""
    return df["dow"].map(lambda d: "Sunday" if d == 6 else "Saturday" if d == 5 else "Weekday")


def flag(df: pd.DataFrame, expected: pd.Series, z_threshold=config.ANOMALY_Z_INTERVAL) -> pd.DataFrame:
    """Interval-level flags from out-of-fold one-step forecast residuals."""
    cols = ["operating_day", "hour", "dow", "is_weekend", "load_type", "kwh"]
    out = df.loc[expected.index, cols].copy()
    out["expected_kwh"] = expected
    out["residual"] = out["kwh"] - out["expected_kwh"]
    out["day_type"] = day_type(out)
    out["z"] = robust_z(out["residual"], [out["day_type"], out["hour"]])
    out["flag"] = out["z"].abs() >= z_threshold
    return out


def _trailing_median(kwh: pd.Series, regular: pd.Series, n: int) -> pd.Series:
    """Median of the previous `n` regular days in the series (holidays are skipped)."""
    out = pd.Series(np.nan, index=kwh.index)
    history: list[float] = []
    for day, value in kwh.items():
        if len(history) >= n:
            out[day] = np.median(history[-n:])
        if regular[day]:
            history.append(value)
    return out


def daily_deviation(daily: pd.DataFrame, weeks: int = 4, z_threshold=config.ANOMALY_Z_DAY,
                    holidays=config.KR_HOLIDAYS_2018) -> pd.DataFrame:
    """Each day against the median of the same weekday over the previous `weeks` regular weeks.

    Public holidays are known in advance, so they are kept out of the reference and are
    not flagged. The expected value uses only past days, but the robust scale (median and
    MAD of residuals) is taken over the whole year: this is a retrospective review, not an
    alarm that could have fired on the day. The reference uses only past days: a change in operating regime is
    flagged once and then absorbed instead of being flagged for the rest of the year.
    """
    out = daily[["kwh", "dow"]].copy()
    out["holiday"] = out.index.strftime("%Y-%m-%d").map(holidays)
    regular = out["holiday"].isna()
    out["expected_kwh"] = pd.concat(
        _trailing_median(g["kwh"], regular[g.index], weeks) for _, g in out.groupby("dow"))
    out = out.dropna(subset=["expected_kwh"])
    out["residual"] = out["kwh"] - out["expected_kwh"]
    out["day_type"] = day_type(out)
    reg = out[out["holiday"].isna()]
    center = reg.groupby("day_type")["residual"].median()
    scale = reg.groupby("day_type")["residual"].apply(
        lambda r: (r - r.median()).abs().median() * MAD_TO_SIGMA)
    out["z"] = (out["residual"] - out["day_type"].map(center)) / out["day_type"].map(scale)
    out["flag"] = (out["z"].abs() >= z_threshold) & out["holiday"].isna()
    out["weekday"] = out.index.day_name()
    return out


def near_threshold(days: pd.DataFrame, lower: float = config.NEAR_THRESHOLD_Z) -> pd.DataFrame:
    """Non-holiday days just under the flag threshold: worth a look, not flagged."""
    return days[(days["z"].abs() >= lower) & ~days["flag"] & days["holiday"].isna()]


def episodes(flagged: pd.DataFrame, min_run=config.ANOMALY_MIN_RUN) -> pd.DataFrame:
    """Merge consecutive flagged slots of the same sign into episodes."""
    step = pd.Timedelta(minutes=config.INTERVAL_MIN)
    f = flagged[flagged["flag"]].copy()
    if f.empty:
        return pd.DataFrame()
    f["sign"] = np.sign(f["residual"])
    new = (f.index.to_series().diff() != step) | (f["sign"] != f["sign"].shift())
    f["episode"] = new.cumsum().values
    g = f.groupby("episode")
    ep = pd.DataFrame({
        "start": g.apply(lambda d: d.index.min() - step),
        "end": g.apply(lambda d: d.index.max()),
        "slots": g.size(),
        "direction": g["sign"].first().map({1.0: "high", -1.0: "low"}),
        "kwh": g["kwh"].sum(),
        "expected_kwh": g["expected_kwh"].sum(),
        "excess_kwh": g["residual"].sum(),
        "max_abs_z": g["z"].apply(lambda z: z.abs().max()),
        "is_weekend": g["is_weekend"].first().astype(bool),
        "load_type": g["load_type"].agg(lambda s: s.mode().iloc[0]),
        "holiday": g["operating_day"].first().dt.strftime("%Y-%m-%d").map(config.KR_HOLIDAYS_2018),
    })
    ep = ep[ep["slots"] >= min_run]
    return ep.sort_values("excess_kwh", key=np.abs, ascending=False).reset_index(drop=True)


def sensitivity(flagged: pd.DataFrame, thresholds=(3, 4, 5, 6, 8)) -> pd.DataFrame:
    """Flag rate and episode count at several thresholds, to show the choice is not knife-edge."""
    rows = []
    for t in thresholds:
        f = flagged.assign(flag=flagged["z"].abs() >= t)
        rows.append({"z": t, "flag_rate": float(f["flag"].mean()), "episodes": len(episodes(f))})
    return pd.DataFrame(rows)


def isolation_forest_agreement(df: pd.DataFrame, flagged: pd.DataFrame) -> dict:
    """Cross-check with a method that sees the electrical readings but not the residual."""
    X = df.loc[flagged.index, IFOREST_FEATURES]
    rate = float(flagged["flag"].mean())
    iso = IsolationForest(contamination=max(rate, 1e-3), random_state=config.SEED).fit(X)
    iso_flag = pd.Series(iso.predict(X) == -1, index=X.index)
    both = (iso_flag & flagged["flag"]).sum()
    return {
        "residual_rate": rate,
        "iforest_rate": float(iso_flag.mean()),
        "share_of_residual_flags_also_iforest": float(both / max(flagged["flag"].sum(), 1)),
        "jaccard": float(both / max((iso_flag | flagged["flag"]).sum(), 1)),
        # Same-size random flags would overlap by roughly this much.
        "chance_overlap": float(iso_flag.mean()),
    }




@dataclass
class AnomalyResults:
    intervals: pd.DataFrame
    episodes: pd.DataFrame
    sensitivity: pd.DataFrame
    iforest: dict
    days: pd.DataFrame
    near_threshold: pd.DataFrame

    @property
    def anomalous_days(self) -> int:
        return int(self.days["flag"].sum())

    @property
    def interval_flag_rate(self) -> float:
        return float(self.intervals["flag"].mean())

    @property
    def first_judged_day(self) -> pd.Timestamp:
        return self.days.index.min()


def run(df: pd.DataFrame, daily: pd.DataFrame, expected: pd.Series) -> AnomalyResults:
    """`expected` is an out-of-fold 15-min forecast (see regress.out_of_fold_forecast)."""
    intervals = flag(df, expected)
    days = daily_deviation(daily)
    return AnomalyResults(
        intervals=intervals,
        episodes=episodes(intervals),
        sensitivity=sensitivity(intervals),
        iforest=isolation_forest_agreement(df, intervals),
        days=days,
        near_threshold=near_threshold(days),
    )
