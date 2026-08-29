from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from cortex.contracts.events import utcnow


def record_call(
    conn: sqlite3.Connection,
    model: str,
    provider: str = "",
    tokens_in: int = 0,
    tokens_out: int = 0,
    cost_usd: float = 0.0,
    purpose: str = "",
    run_id: int | None = None,
) -> None:
    conn.execute(
        "INSERT INTO ledger (ts, run_id, model, provider, tokens_in, tokens_out, cost_usd, purpose)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (utcnow(), run_id, model, provider, tokens_in, tokens_out, cost_usd, purpose),
    )
    conn.commit()


def spend_today(conn: sqlite3.Connection) -> float:
    day_start = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00")
    row = conn.execute(
        "SELECT COALESCE(SUM(cost_usd), 0) AS total FROM ledger WHERE ts >= ?", (day_start,)
    ).fetchone()
    return float(row["total"])


def summary(conn: sqlite3.Connection) -> dict:
    total = conn.execute("SELECT COALESCE(SUM(cost_usd), 0) AS t FROM ledger").fetchone()["t"]
    by_model = conn.execute(
        "SELECT model, COUNT(*) AS calls, SUM(tokens_in) AS tokens_in,"
        " SUM(tokens_out) AS tokens_out, SUM(cost_usd) AS cost_usd"
        " FROM ledger GROUP BY model ORDER BY cost_usd DESC"
    ).fetchall()
    return {
        "total_usd": float(total),
        "today_usd": spend_today(conn),
        "by_model": [dict(r) for r in by_model],
    }
