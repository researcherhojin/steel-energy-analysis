import pytest

from steelenergy import validate


def test_all_checks_pass(df):
    failed = [c for c in validate.run_checks(df) if not c.passed]
    assert not failed, failed


def test_day_label_check_catches_calendar_midnight(df):
    broken = df.copy()
    broken["operating_day"] = broken.index.normalize()
    names = {c.name for c in validate.run_checks(broken) if not c.passed}
    assert "day_of_week_label" in names


def test_holm_matches_hand_computation():
    from steelenergy.stats import holm

    # sorted 0.005, 0.01, 0.03, 0.04 × (4, 3, 2, 1) = 0.02, 0.03, 0.06, 0.04;
    # running max, then back to input order
    assert holm([0.01, 0.04, 0.03, 0.005]) == pytest.approx([0.03, 0.06, 0.06, 0.02])
    assert holm([0.6, 0.7]).tolist() == [1.0, 1.0]  # 0.6 × 2 = 1.2, capped at 1
