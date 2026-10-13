import numpy as np
import pandas as pd

from steelenergy import anomaly, config, eda


def test_holidays_are_never_flagged(featured):
    days = anomaly.daily_deviation(eda.daily_totals(featured))
    assert not days.loc[days["holiday"].notna(), "flag"].any()


def test_trailing_median_uses_only_earlier_regular_days():
    idx = pd.date_range("2018-01-01", periods=6, freq="7D")
    kwh = pd.Series([1.0, 2.0, 100.0, 3.0, 4.0, 5.0], index=idx)
    regular = pd.Series([True, True, False, True, True, True], index=idx)
    out = anomaly._trailing_median(kwh, regular, 2)
    assert np.isnan(out.iloc[1])
    assert out.iloc[2] == 1.5  # the holiday itself gets a reference
    assert out.iloc[3] == 1.5  # but is skipped when building the next one
    assert out.iloc[4] == 2.5


def test_holiday_table_covers_calendar(featured):
    table = eda.holiday_operation(eda.daily_totals(featured))
    assert len(table) == len(config.KR_HOLIDAYS_2018)


def test_weekend_holidays_are_not_counted_as_shutdowns(featured):
    table = eda.holiday_operation(eda.daily_totals(featured))
    assert not table.loc[table["is_weekend"], "shutdown"].any()
