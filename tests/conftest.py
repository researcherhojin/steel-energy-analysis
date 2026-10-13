import pytest

from steelenergy import features, io


@pytest.fixture(scope="session")
def raw():
    return io.read_csv()


@pytest.fixture(scope="session")
def df():
    return io.load()


@pytest.fixture(scope="session")
def featured(df):
    return features.build(df)


@pytest.fixture(scope="session")
def payload():
    from steelenergy import export, pipeline

    return export.payload(pipeline.run())
