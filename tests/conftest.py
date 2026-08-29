import pytest

from cortex.core import db, registry as registry_loader


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    path = str(tmp_path / "test.db")
    monkeypatch.setenv("CORTEX_DB", path)
    conn = db.connect(path)
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def registry():
    return registry_loader.load("config")
