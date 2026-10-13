import pandas as pd

from steelenergy import config, io


def test_header_bom_is_stripped(raw):
    assert raw.columns[0] == "timestamp_raw"


def test_naive_parse_is_out_of_order(raw):
    naive = pd.to_datetime(raw["timestamp_raw"], format="%d/%m/%Y %H:%M")
    assert not naive.is_monotonic_increasing


def test_midnight_rows_move_to_next_day(df):
    assert df.index.is_monotonic_increasing
    assert df.index.min() == pd.Timestamp("2018-01-01 00:15")
    assert df.index.max() == pd.Timestamp("2019-01-01 00:00")
    midnight = df[df["nsm"] == 0]
    assert (midnight["operating_day"] == midnight.index.normalize() - pd.Timedelta(days=1)).all()


def test_every_operating_day_has_96_slots(df):
    assert (df.groupby("operating_day").size() == config.SLOTS_PER_DAY).all()


def test_fix_timestamps_on_tiny_frame():
    raw = pd.DataFrame({"timestamp_raw": ["01/01/2018 23:45", "01/01/2018 00:00", "02/01/2018 00:15"],
                        "nsm": [85500, 0, 900]})
    out = io.fix_timestamps(raw)
    assert out["timestamp"].tolist() == list(pd.to_datetime(
        ["2018-01-01 23:45", "2018-01-02 00:00", "2018-01-02 00:15"]))
    assert out["operating_day"].dt.day.tolist() == [1, 1, 2]
