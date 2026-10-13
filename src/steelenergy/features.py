import numpy as np
import pandas as pd

from steelenergy import config

CALENDAR = ["slot", "hour", "dow", "is_weekend", "hour_sin", "hour_cos", "dow_sin", "dow_cos"]
# Month is kept as a column for grouping but not used as a model input: with a Jan–Oct
# training window, Nov and Dec are values the model has never seen.
# Load_Type follows a time-of-use band schedule that switches between Nov–Feb and Mar–Oct.
SEASON = ["is_winter"]
LAGS = {"kwh_lag1": 1, "kwh_lag2": 2, "kwh_lag4": 4, "kwh_lag96": 96, "kwh_lag672": 672}
ROLLING = {"kwh_roll4": 4, "kwh_roll96": 96}
HISTORY = list(LAGS) + list(ROLLING)
# Measured in the same interval as the target; never allowed in the forecasting feature set.
SAME_INTERVAL = ["kwh", "lag_kvarh", "lead_kvarh", "lag_pf", "lead_pf"]


def add_calendar(df: pd.DataFrame) -> pd.DataFrame:
    """Calendar fields keyed to the interval start, so 24:00 stays on its operating day."""
    out = df.copy()
    start = df.index - pd.Timedelta(minutes=config.INTERVAL_MIN)
    out["slot"] = start.hour * 4 + start.minute // config.INTERVAL_MIN
    out["hour"] = start.hour
    out["dow"] = df["operating_day"].dt.dayofweek
    out["month"] = df["operating_day"].dt.month
    out["is_weekend"] = (out["dow"] >= 5).astype(int)
    out["is_winter"] = out["month"].isin(config.WINTER_MONTHS).astype(int)
    out["hour_sin"] = np.sin(2 * np.pi * out["slot"] / config.SLOTS_PER_DAY)
    out["hour_cos"] = np.cos(2 * np.pi * out["slot"] / config.SLOTS_PER_DAY)
    out["dow_sin"] = np.sin(2 * np.pi * out["dow"] / 7)
    out["dow_cos"] = np.cos(2 * np.pi * out["dow"] / 7)
    return out


def add_history(df: pd.DataFrame) -> pd.DataFrame:
    """Lagged and rolling kWh. Every window ends at t-1."""
    out = df.copy()
    past = df["kwh"].shift(1)
    for name, k in LAGS.items():
        out[name] = df["kwh"].shift(k)
    for name, w in ROLLING.items():
        out[name] = past.rolling(w).mean()
    return out


def build(df: pd.DataFrame) -> pd.DataFrame:
    return add_history(add_calendar(df))
