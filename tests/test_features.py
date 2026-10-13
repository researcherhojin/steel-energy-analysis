import numpy as np

from steelenergy import features
from steelenergy.models import classify, regress


def test_history_uses_only_past(featured):
    k = featured["kwh"].to_numpy()
    assert np.allclose(featured["kwh_lag1"].to_numpy()[1:], k[:-1])
    assert np.isclose(featured["kwh_roll4"].iloc[10], k[6:10].mean())


def test_changing_current_value_does_not_change_its_features(df):
    a = features.build(df)
    bumped = df.copy()
    bumped.iloc[5000, bumped.columns.get_loc("kwh")] += 1000
    b = features.build(bumped)
    row = a.index[5000]
    assert a.loc[row, features.HISTORY].equals(b.loc[row, features.HISTORY])


def test_forecast_features_exclude_same_interval_and_co2():
    banned = set(features.SAME_INTERVAL) | {"co2_t", "kwh", "month"}
    assert not banned & set(regress.FEATURES)
    assert not banned & set(classify.HISTORY)


def test_midnight_slot_belongs_to_previous_day(featured):
    midnight = featured[featured["nsm"] == 0]
    assert (midnight["slot"] == 95).all()
    assert (midnight["hour"] == 23).all()
