import json

import pytest

from steelenergy import export

REQUIRED = {"schema_version", "meta", "validation", "kpi", "daily", "monthly", "profile",
            "load_types", "tou_schedule", "stats", "classification", "regression", "anomaly",
            "scenarios"}


@pytest.fixture(scope="module")
def data(payload):
    return payload


def test_payload_has_schema(data):
    assert data.keys() >= REQUIRED
    assert data["schema_version"] == export.SCHEMA_VERSION


def test_payload_is_strict_json(data):
    json.loads(json.dumps(data, allow_nan=False))


def test_kpi_matches_daily(data):
    assert sum(d["kwh"] for d in data["daily"]) == pytest.approx(data["kpi"]["annual_kwh"], rel=1e-6)
