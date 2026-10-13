"""Run every analysis step and write outputs/analysis.json.

    uv run python -m steelenergy.pipeline

Each analysis module exposes run(), returning one result object; this module only wires
them together in dependency order. Nothing here computes analysis results itself.
"""
from dataclasses import dataclass

import pandas as pd

from steelenergy import anomaly, config, eda, export, features, io, scenarios, stats, validate
from steelenergy.models import classify, regress, split


@dataclass
class Results:
    df: pd.DataFrame
    checks: pd.DataFrame
    run_info: dict
    split: split.Split
    eda: eda.EdaResults
    stats: stats.StatsResults
    regression: regress.RegressionReport
    classification: classify.ClassifierReport
    anomaly: anomaly.AnomalyResults
    scenarios: scenarios.ScenarioResults


def describe(df: pd.DataFrame, daily: pd.DataFrame, sp: split.Split) -> dict:
    """Facts about this run's data, written into the JSON's `meta` block."""
    return {
        "rows": len(df),
        "first_interval_end": df.index.min(),
        "last_interval_end": df.index.max(),
        "split": sp.periods(),
        "history_days_dropped": max(features.LAGS.values()) // config.SLOTS_PER_DAY,
        "operating_days": int(daily.shape[0]),
        "year": int(daily.index[0].year),
    }


def run() -> Results:
    raw = io.load()
    checks = validate.checks_frame(validate.run_checks(raw))
    if not checks["passed"].all():
        raise ValueError(f"validation failed:\n{checks[~checks['passed']]}")
    df = features.build(raw)
    daily = eda.daily_totals(df)
    sp = split.by_date(df)
    expected = regress.out_of_fold_forecast(split.monthly_folds(df))
    return Results(
        df=df,
        checks=checks,
        run_info=describe(df, daily, sp),
        split=sp,
        eda=eda.run(df, daily),
        stats=stats.run(df, daily),
        regression=regress.evaluate(sp),
        classification=classify.run(sp, df),
        anomaly=anomaly.run(df, daily, expected),
        scenarios=scenarios.run(df),
    )


def main() -> None:
    results = run()
    path = export.write(export.payload(results), config.OUTPUT_DIR / "analysis.json")
    print(f"wrote {path.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
