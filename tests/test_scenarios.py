import numpy as np
import pytest

from steelenergy import scenarios


@pytest.mark.parametrize("fraction", [0.0, 0.1, 0.3])
def test_shift_conserves_daily_energy(featured, fraction):
    shifted, _ = scenarios.shift_peak_load(featured, fraction)
    by_day = shifted.groupby(featured["operating_day"]).sum()
    assert np.allclose(by_day, featured["kwh"].groupby(featured["operating_day"]).sum())


def test_pf_correction_only_reduces_reactive_power(featured):
    kvarh = scenarios.correct_power_factor(featured, 0.95)
    assert (kvarh <= featured["lag_kvarh"] + 1e-9).all()
    result = scenarios.pf_scenario(featured, 0.95)
    assert result["annual_pf_after"] >= 0.95 - 1e-6


@pytest.mark.parametrize("fraction", [0.1, 0.3])
def test_shift_conserves_daily_reactive_energy(featured, fraction):
    _, kvarh = scenarios.shift_peak_load(featured, fraction)
    by_day = kvarh.groupby(featured["operating_day"]).sum()
    assert np.allclose(by_day, featured["lag_kvarh"].groupby(featured["operating_day"]).sum())


def test_shift_cost_lines_add_up(featured):
    r = scenarios.shift_scenario(featured, 0.1)
    parts = r["energy_cost_after"] + r["demand_cost_after"] + r["surcharge_after"]
    assert parts == pytest.approx(r["total_cost_after"])
