import pytest
from fastapi.testclient import TestClient

from cortex.api.app import create_app
from cortex.agents.router_planner import route_ideas


@pytest.fixture
def client(tmp_db):
    return TestClient(create_app("config"))


def test_idea_capture_writes_row_and_event(client, tmp_db):
    resp = client.post("/ideas", json={"text": "add dark mode", "project": "cortex"})
    assert resp.status_code == 201
    idea_id = resp.json()["id"]

    ideas = client.get("/ideas", params={"status": "new"}).json()
    assert any(i["id"] == idea_id for i in ideas)

    event_types = [e["type"] for e in client.get("/events").json()]
    assert "idea.captured" in event_types


def test_event_bus_round_trip(client):
    resp = client.post("/events", json={"type": "test.ping", "payload": {"n": 1}})
    assert resp.status_code == 201
    tail = client.get("/events", params={"limit": 5}).json()
    assert tail[0]["type"] == "test.ping"
    assert tail[0]["payload"] == {"n": 1}


def test_costs_reports_caps(client):
    report = client.get("/costs").json()
    assert report["total_usd"] == 0
    assert report["caps"]["global_daily_usd"] > 0
    assert report["daily_remaining_usd"] > 0


def test_router_fallback_routes_without_gateway(client, tmp_db, registry):
    client.post("/ideas", json={"text": "write the vault indexer", "project": "cortex"})
    client.post("/ideas", json={"text": "random thought"})

    tasks = route_ideas(tmp_db, registry, gateway=None, dry_run=False)
    assert len(tasks) == 2
    assert tasks[0]["project"] == "cortex"
    assert tasks[1]["project"] == "inbox"  # untagged ideas land in inbox
    assert all(t["filed"] is False for t in tasks)  # no repos registered

    remaining = tmp_db.execute("SELECT COUNT(*) AS n FROM ideas WHERE status = 'new'").fetchone()
    assert remaining["n"] == 0
