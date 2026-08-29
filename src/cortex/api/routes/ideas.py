from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from cortex.api.app import get_conn
from cortex.contracts.events import utcnow
from cortex.core import events

router = APIRouter(prefix="/ideas", tags=["ideas"])


class IdeaIn(BaseModel):
    text: str
    project: str | None = None
    source: str = "api"


@router.post("", status_code=201)
def create_idea(idea: IdeaIn, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    cur = conn.execute(
        "INSERT INTO ideas (ts, text, project, source) VALUES (?, ?, ?, ?)",
        (utcnow(), idea.text, idea.project, idea.source),
    )
    conn.commit()
    events.publish(conn, "idea.captured", {"idea_id": cur.lastrowid, "project": idea.project})
    return {"id": cur.lastrowid, "status": "new"}


@router.get("")
def list_ideas(status: str | None = None, conn: sqlite3.Connection = Depends(get_conn)) -> list[dict]:
    if status:
        rows = conn.execute("SELECT * FROM ideas WHERE status = ? ORDER BY id DESC", (status,))
    else:
        rows = conn.execute("SELECT * FROM ideas ORDER BY id DESC")
    return [dict(r) for r in rows.fetchall()]
