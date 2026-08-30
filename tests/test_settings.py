import shutil

import pytest
from fastapi.testclient import TestClient

from cortex.api.app import create_app
from cortex.api.routes import settings as settings_route
from cortex.core import env_file


@pytest.fixture
def client(tmp_db):
    return TestClient(create_app("config"))


def test_env_file_round_trip(tmp_path):
    env = tmp_path / ".env"
    env.write_text("# comment stays\nGROQ_API_KEY=\nCORTEX_DB=data/cortex.db\n")
    env_file.update({"GROQ_API_KEY": "gsk_abc123456789", "OPENROUTER_API_KEY": "sk-or-xyz"}, env)

    text = env.read_text()
    assert "# comment stays" in text
    values = env_file.read(env)
    assert values["GROQ_API_KEY"] == "gsk_abc123456789"
    assert values["OPENROUTER_API_KEY"] == "sk-or-xyz"  # appended
    assert values["CORTEX_DB"] == "data/cortex.db"      # untouched


def test_mask_never_leaks_full_value():
    masked = env_file.mask("gsk_abc123456789")
    assert masked["set"] is True
    assert "gsk_abc" not in masked["hint"]
    assert env_file.mask("") == {"set": False, "hint": ""}


def test_get_settings_returns_masked_keys(client):
    data = client.get("/settings").json()
    assert set(data["keys"]) == set(env_file.KEY_FIELDS)
    for meta in data["keys"].values():
        assert set(meta) == {"set", "hint"}  # never the value itself
    assert data["budgets"]["global_daily_usd"] > 0


def test_put_keys_rejects_unknown_and_empty(client, monkeypatch):
    saved = {}
    monkeypatch.setattr(settings_route.env_file, "update", lambda u, path=None: saved.update(u))

    resp = client.put("/settings/keys", json={"EVIL_KEY": "x", "GROQ_API_KEY": "  "})
    assert resp.status_code == 400

    resp = client.put("/settings/keys", json={"GROQ_API_KEY": "gsk_new", "EVIL_KEY": "x"})
    assert resp.json()["saved"] == ["GROQ_API_KEY"]
    assert saved == {"GROQ_API_KEY": "gsk_new"}


def test_put_budgets_edits_yaml_and_reloads(client, tmp_path, monkeypatch):
    yaml_copy = tmp_path / "models.yaml"
    shutil.copy(settings_route.MODELS_YAML, yaml_copy)
    monkeypatch.setattr(settings_route, "MODELS_YAML", yaml_copy)

    resp = client.put("/settings/budgets", json={"global_daily_usd": 5.0, "per_run_usd": 1.0})
    assert resp.status_code == 200
    text = yaml_copy.read_text()
    assert "global_daily_usd: 5.00" in text
    assert "# Model registry" in text  # comments survive the edit


def test_route_action_endpoint(client, tmp_db, registry):
    client.post("/ideas", json={"text": "test the dashboard route button", "project": "cortex"})
    resp = client.post("/actions/route", json={"dry_run": True})
    tasks = resp.json()["tasks"]
    assert len(tasks) == 1
    assert tasks[0]["filed"] is False


def test_dispatch_requires_workspace(client):
    resp = client.post("/actions/dispatch", json={"task": "x", "project": "nonexistent"})
    assert resp.status_code == 400


def test_dashboard_served_at_root(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "CORTEX" in resp.text
