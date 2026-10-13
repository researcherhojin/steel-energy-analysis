from dataclasses import dataclass

import pandas as pd

from steelenergy import config


@dataclass(frozen=True)
class Split:
    train: pd.DataFrame
    valid: pd.DataFrame
    test: pd.DataFrame

    @property
    def train_valid(self) -> pd.DataFrame:
        return pd.concat([self.train, self.valid])

    def periods(self) -> dict:
        def span(d):
            return {"start": str(d["operating_day"].min().date()),
                    "end": str(d["operating_day"].max().date()), "rows": len(d)}
        return {"train": span(self.train), "valid": span(self.valid), "test": span(self.test)}


def by_date(df: pd.DataFrame, train_end=config.TRAIN_END, valid_end=config.VALID_END) -> Split:
    """Chronological split on operating day; rows with incomplete history are dropped first."""
    df = df.dropna()
    day = df["operating_day"]
    return Split(
        train=df[day <= train_end],
        valid=df[(day > train_end) & (day <= valid_end)],
        test=df[day > valid_end],
    )


def monthly_folds(df: pd.DataFrame, first_month: int = 2):
    """Expanding-window folds: fit on every month before m, predict month m."""
    df = df.dropna()
    for m in range(first_month, 13):
        yield m, df[df["month"] < m], df[df["month"] == m]
