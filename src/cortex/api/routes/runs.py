from __future__ import annotations

import json
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from cortex.api.app import get_conn
from cortex.core import runs

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("")
def list_runs(limit: int = 50, conn: sqlite3.Connection = Depends(get_conn)) -> list[dict]:
    return runs.list_runs(conn, limit)


@router.get("/{run_id}")
def get_run(run_id: int, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "run not found")
    record = dict(row)
    record["result"] = json.loads(record.pop("result_json"))
    return record
