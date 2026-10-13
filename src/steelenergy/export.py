"""Serialize pipeline results into the JSON contract read by the pages and the notebook.

This module maps values to keys, joins display labels and cleans types. It computes
nothing: every number comes from a result object built by an analysis module.
"""
import json
import math
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from steelenergy import config, labels

SCHEMA_VERSION = 1


def _clean(obj):
    if isinstance(obj, dict):
        return {str(k): _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        return None if math.isnan(obj) else round(float(obj), 6)
    return obj


def _records(frame: pd.DataFrame, index: str | None = None) -> list[dict]:
    if index:
        frame = frame.rename_axis(index).reset_index()
    return frame.to_dict(orient="records")


def _columns(frame: pd.DataFrame) -> dict:
    """Column-oriented form for large tables; about a third the size of records."""
    return {c: frame[c].astype(str if frame[c].dtype.name == "category" else frame[c].dtype)
            .tolist() for c in frame.columns}


def _with_classification_labels(rows: list[dict]) -> list[dict]:
    return [{**r, "label": labels.CLASSIFICATION[r["model"]][0],
             "inputs": labels.CLASSIFICATION[r["model"]][1]} for r in rows]


def _meta(r) -> dict:
    return {
        **config.DATASET,
        **{k: v for k, v in r.run_info.items() if k not in ("operating_days", "year")},
        "interval_min": config.INTERVAL_MIN,
        "tariff": config.TARIFF_ASSUMPTIONS,
        "winter_months": list(config.WINTER_MONTHS),
        "anomaly_z_day": config.ANOMALY_Z_DAY,
        "anomaly_z_interval": config.ANOMALY_Z_INTERVAL,
        "operating_days": r.run_info["operating_days"],
        "year": r.run_info["year"],
        "forecast_week": list(config.FORECAST_WEEK),
        "shutdown_ratio": config.SHUTDOWN_RATIO,
        "pf_target": config.PF_TARGET,
        "shift_example": config.SHIFT_EXAMPLE,
    }


def _kpi(r) -> dict:
    e, h = r.eda, r.eda.headline
    return {
        "annual_kwh": h["annual_kwh"],
        "annual_co2_t": h["annual_co2_t"],
        "annual_pf": h["annual_pf"],
        "peak_kw": h["peak_kw"],
        "mean_daily_kwh": h["mean_daily_kwh"],
        "anomalous_days": r.anomaly.anomalous_days,
        "holiday_shutdowns": e.holiday_counts["holiday_shutdowns"],
        "holidays": e.holiday_counts["holidays"],
        "weekday_holidays": e.holiday_counts["weekday_holidays"],
        "regular_weekday_median_kwh": e.regular_weekday_median,
        "weekend_holidays": e.holiday_counts["weekend_holidays"],
        "co2_t_per_mwh": r.stats.emission["ratio_of_sums"],
        "weekday_shutdowns": len(e.shutdowns),
        "weekday_daytime": e.concentration,
        "idle": e.idle,
        "weekday_mean_kwh": h["weekday_mean_kwh"],
        "saturday_mean_kwh": h["saturday_mean_kwh"],
        "sunday_mean_kwh": h["sunday_mean_kwh"],
    }


def _classification(clf) -> dict:
    return {
        "scores": _with_classification_labels(_records(clf.scores, "model")),
        "confusion": {"labels": clf.labels, "matrix": clf.confusion.values.tolist()},
        "errors_by_daytype": _records(clf.errors_by_daytype, "daytype"),
        "reverse": _with_classification_labels(_records(clf.reverse, "model")),
    }


def _regression(reg) -> dict:
    return {
        "scores": [{**s, "label": labels.REGRESSION[s["model"]],
                    "desc": labels.REGRESSION_DESC[s["model"]]} for s in _records(reg.scores, "model")],
        "best_naive": reg.best_naive,
        "importance": [{**f, "label": labels.FEATURES[f["feature"]]}
                       for f in _records(reg.importance.head(config.TOP_FEATURES), "feature")],
        "error_by_hour": _records(reg.error_by_hour, "hour"),
        "week": _records(reg.example_week, "t"),
        "test_daily": _records(reg.test_daily, "date"),
        "test_mean_kwh": reg.test_mean_kwh,
    }


def _anomaly(r) -> dict:
    a, e = r.anomaly, r.eda
    return {
        "days": _records(a.days[a.days["flag"]], "date"),
        "daily_z": _records(a.days[["kwh", "dow", "expected_kwh", "z", "holiday"]], "date"),
        "first_judged_day": a.first_judged_day,
        "near_threshold": _records(a.near_threshold, "date"),
        "min_run_minutes": config.ANOMALY_MIN_RUN * config.INTERVAL_MIN,
        "holidays": _records(e.holidays, "date"),
        "weekday_shutdowns": _records(e.shutdowns, "date"),
        "shutdown_runs": _records(e.shutdown_runs),
        "episodes": _records(a.episodes.head(config.TOP_EPISODES)),
        "episode_count": len(a.episodes),
        "interval_flag_rate": a.interval_flag_rate,
        "sensitivity": _records(a.sensitivity),
        "iforest": a.iforest,
    }


def _scenarios(s) -> dict:
    return {
        "pf": _records(s.pf_grid),
        "pf_default": s.pf_default,
        "first_demand_increase": s.first_demand_increase,
        "shift": _records(s.shift_grid),
        "bill": _records(s.bill, "month"),
        "surcharge": s.surcharge,
    }


def payload(r) -> dict:
    """Everything the dashboard, report and notebook prose read. `r` is a pipeline.Results."""
    e = r.eda
    data = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "meta": _meta(r),
        "validation": [{**c, "label": labels.CHECKS[c["name"]]} for c in _records(r.checks)],
        "kpi": _kpi(r),
        "daily": _records(e.daily.drop(columns=["is_weekend"]), "date"),
        "night_load": _records(e.night_load.to_frame(), "month"),
        "correlations": {k: float(v) for k, v in e.kwh_correlations.items()},
        "date_notes": labels.DATE_NOTES,
        "monthly": _records(e.monthly, "month"),
        "profile": _columns(e.profile),
        "load_types": _records(e.load_types, "load_type"),
        "pf_by_load": _records(e.pf_by_load, "kwh_bin"),
        "tou_schedule": _records(e.tou_schedule, "hour"),
        "stats": {"tests": _records(r.stats.tests), "emission": r.stats.emission,
                  "co2_zero_share": r.stats.co2_zero_share},
        "classification": _classification(r.classification),
        "regression": _regression(r.regression),
        "anomaly": _anomaly(r),
        "scenarios": _scenarios(r.scenarios),
    }
    return _clean(data)


def write(data: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return path
