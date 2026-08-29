from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Request

from cortex.api.app import get_conn
from cortex.core import ledger

router = APIRouter(prefix="/costs", tags=["costs"])


@router.get("")
def costs(request: Request, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    report = ledger.summary(conn)
    caps = request.app.state.registry.budgets
    report["caps"] = caps.model_dump()
    report["daily_remaining_usd"] = max(0.0, caps.global_daily_usd - report["today_usd"])
    return report
