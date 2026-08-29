from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from cortex.api.app import get_conn
from cortex.core import events

router = APIRouter(prefix="/events", tags=["events"])


class EventIn(BaseModel):
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)


@router.post("", status_code=201)
def post_event(event: EventIn, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    saved = events.publish(conn, event.type, event.payload)
    return {"id": saved.id, "ts": saved.ts}


@router.get("")
def get_events(limit: int = 50, conn: sqlite3.Connection = Depends(get_conn)) -> list[dict]:
    return [e.model_dump() for e in events.tail(conn, limit)]
