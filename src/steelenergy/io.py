import pandas as pd

from steelenergy import config


def read_csv(path=config.RAW_CSV) -> pd.DataFrame:
    """Read the raw CSV with short column names, no other changes."""
    return pd.read_csv(path, encoding="utf-8-sig").rename(columns=config.COLUMNS)


def fix_timestamps(raw: pd.DataFrame) -> pd.DataFrame:
    """Parse day-first dates and move each day's 00:00 row to the following midnight."""
    df = raw.copy()
    ts = pd.to_datetime(df["timestamp_raw"], format="%d/%m/%Y %H:%M")
    # The file closes each day with a 00:00 row stamped with that same date (NSM == 0).
    # It is the 24:00 reading, so it belongs to the next calendar midnight.
    ts = ts.where(df["nsm"] != 0, ts + pd.Timedelta(days=1))
    df["timestamp"] = ts
    # Interval-ending stamps: the slot that ends at 00:00 was consumed the previous day.
    df["operating_day"] = (ts - pd.Timedelta(minutes=config.INTERVAL_MIN)).dt.normalize()
    return df.sort_values("timestamp").reset_index(drop=True)


def load() -> pd.DataFrame:
    """Raw data, cleaned timestamps, categoricals typed. Indexed by interval end."""
    df = fix_timestamps(read_csv())
    df["load_type"] = pd.Categorical(df["load_type"], categories=config.LOAD_TYPES, ordered=True)
    df["day_of_week"] = pd.Categorical(df["day_of_week"], categories=config.WEEKDAYS, ordered=True)
    return df.drop(columns="timestamp_raw").set_index("timestamp")
