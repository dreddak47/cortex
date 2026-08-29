from __future__ import annotations

import os
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    type TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS ideas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    text TEXT NOT NULL,
    project TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    source TEXT NOT NULL DEFAULT 'cli'
);

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    agent TEXT NOT NULL,
    harness TEXT,
    task TEXT NOT NULL,
    workspace TEXT,
    state TEXT NOT NULL DEFAULT 'queued',
    result_json TEXT NOT NULL DEFAULT '{}',
    tokens_in INTEGER NOT NULL DEFAULT 0,
    tokens_out INTEGER NOT NULL DEFAULT 0,
    cost_usd REAL NOT NULL DEFAULT 0,
    duration_s REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    run_id INTEGER,
    model TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT '',
    tokens_in INTEGER NOT NULL DEFAULT 0,
    tokens_out INTEGER NOT NULL DEFAULT 0,
    cost_usd REAL NOT NULL DEFAULT 0,
    purpose TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS projects (
    name TEXT PRIMARY KEY,
    repo TEXT,
    workspace_path TEXT
);
"""


def default_path() -> str:
    return os.environ.get("CORTEX_DB", "data/cortex.db")


def connect(path: str | None = None) -> sqlite3.Connection:
    db_path = path or default_path()
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    return conn
