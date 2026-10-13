from steelenergy.models import split


def test_split_is_chronological_and_disjoint(featured):
    s = split.by_date(featured)
    assert s.train.index.max() < s.valid.index.min()
    assert s.valid.index.max() < s.test.index.min()
    assert len(s.train) + len(s.valid) + len(s.test) == len(featured.dropna())


def test_monthly_folds_never_look_ahead(featured):
    for m, train, test in split.monthly_folds(featured):
        assert train["month"].max() < m
        assert (test["month"] == m).all()
