from __future__ import annotations

import json
import sqlite3
from typing import Any

from cortex.contracts import Event
from cortex.contracts.events import utcnow


def publish(conn: sqlite3.Connection, type: str, payload: dict[str, Any] | None = None) -> Event:
    event = Event(type=type, payload=payload or {})
    cur = conn.execute(
        "INSERT INTO events (ts, type, payload_json) VALUES (?, ?, ?)",
        (event.ts, event.type, json.dumps(event.payload)),
    )
    conn.commit()
    event.id = cur.lastrowid
    return event


def tail(conn: sqlite3.Connection, limit: int = 50) -> list[Event]:
    rows = conn.execute(
        "SELECT id, ts, type, payload_json FROM events ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [
        Event(id=r["id"], ts=r["ts"], type=r["type"], payload=json.loads(r["payload_json"]))
        for r in rows
    ]
