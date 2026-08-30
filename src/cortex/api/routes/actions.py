from __future__ import annotations

import sqlite3
import threading

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from cortex.api.app import get_conn
from cortex.agents.router_planner import route_ideas
from cortex.core import db
from cortex.core import runs as run_engine
from cortex.gateway import Gateway

router = APIRouter(prefix="/actions", tags=["actions"])


class RouteIn(BaseModel):
    dry_run: bool = True


@router.post("/route")
def trigger_route(
    body: RouteIn, request: Request, conn: sqlite3.Connection = Depends(get_conn)
) -> dict:
    registry = request.app.state.registry
    tasks = route_ideas(
        conn, registry, gateway=Gateway(conn, registry), dry_run=body.dry_run
    )
    return {"dry_run": body.dry_run, "tasks": tasks}


class DispatchIn(BaseModel):
    task: str
    project: str | None = None
    workspace: str | None = None
    harness: str = "claude-code"
    dry_run: bool = True


@router.post("/dispatch")
def dispatch(
    body: DispatchIn, request: Request, conn: sqlite3.Connection = Depends(get_conn)
) -> dict:
    registry = request.app.state.registry
    workspace = body.workspace
    if body.project and not workspace:
        row = conn.execute(
            "SELECT workspace_path FROM projects WHERE name = ?", (body.project,)
        ).fetchone()
        workspace = row["workspace_path"] if row else None
    if not workspace:
        raise HTTPException(400, "need a workspace or a project with a workspace_path")

    if body.dry_run:
        run = run_engine.dispatch_harness(
            conn, registry, body.harness, body.task, workspace, dry_run=True
        )
        return {"run_id": run.id, "state": run.state.value, "result": run.result}

    def _background() -> None:
        bg_conn = db.connect()  # sqlite connections are per-thread
        try:
            run_engine.dispatch_harness(
                bg_conn, registry, body.harness, body.task, workspace, dry_run=False
            )
        finally:
            bg_conn.close()

    threading.Thread(target=_background, daemon=True).start()
    return {"queued": True, "note": "harness running in background — watch the Runs view"}
