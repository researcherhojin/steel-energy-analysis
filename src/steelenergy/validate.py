from dataclasses import dataclass

import pandas as pd

from steelenergy import config


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str


def _check(name: str, passed: bool, detail: str) -> Check:
    return Check(name, bool(passed), detail)


def run_checks(df: pd.DataFrame) -> list[Check]:
    """Structural and range checks on the output of io.load()."""
    idx = df.index
    steps = idx.to_series().diff().dropna()
    per_day = df.groupby("operating_day").size()
    labelled_dow = df["day_of_week"].astype(str)
    actual_dow = df["operating_day"].dt.day_name()
    weekend = df["operating_day"].dt.dayofweek >= 5
    status = df["week_status"].eq("Weekend")
    numeric = ["kwh", "lag_kvarh", "lead_kvarh", "co2_t"]
    pf = ["lag_pf", "lead_pf"]

    return [
        _check("row_count", len(df) == config.EXPECTED_ROWS,
               f"{len(df):,}행 (기대값 {config.EXPECTED_ROWS:,}행)"),
        _check("missing_values", df.isna().sum().sum() == 0,
               f"결측 {int(df.isna().sum().sum())}칸"),
        _check("unique_timestamps", idx.is_unique, f"중복 {int(idx.duplicated().sum())}건"),
        _check("monotonic_index", idx.is_monotonic_increasing, "구간 끝 시각 기준 오름차순"),
        _check("regular_interval", (steps == pd.Timedelta(minutes=config.INTERVAL_MIN)).all(),
               f"간격 이상 {int((steps != pd.Timedelta(minutes=config.INTERVAL_MIN)).sum())}건"),
        _check("slots_per_day", (per_day == config.SLOTS_PER_DAY).all(),
               f"운영일 {per_day.size}일, 96개 미만 {int((per_day != config.SLOTS_PER_DAY).sum())}일"),
        _check("day_of_week_label", (labelled_dow == actual_dow).all(),
               f"운영일과 불일치 {int((labelled_dow != actual_dow).sum())}건"),
        _check("week_status_label", (weekend == status).all(),
               f"운영일과 불일치 {int((weekend != status).sum())}건"),
        _check("non_negative", (df[numeric] >= 0).all().all(), "사용량·무효전력·CO₂ 모두 0 이상"),
        _check("power_factor_range", df[pf].apply(lambda s: s.between(0, 100)).all().all(),
               "모든 값이 0–100% 범위"),
        _check("nsm_consistent",
               (df["nsm"] == (idx.hour * 3600 + idx.minute * 60)).all(),
               "구간 끝 시각의 자정 이후 초와 일치"),
    ]


def checks_frame(checks: list[Check]) -> pd.DataFrame:
    return pd.DataFrame([c.__dict__ for c in checks])
