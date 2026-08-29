from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from cortex.api.app import get_conn

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectIn(BaseModel):
    name: str
    repo: str | None = None          # owner/repo for gh issue create
    workspace_path: str | None = None  # local clone the harness runs in


@router.put("", status_code=201)
def upsert_project(project: ProjectIn, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    conn.execute(
        "INSERT INTO projects (name, repo, workspace_path) VALUES (?, ?, ?)"
        " ON CONFLICT(name) DO UPDATE SET repo = excluded.repo,"
        " workspace_path = excluded.workspace_path",
        (project.name, project.repo, project.workspace_path),
    )
    conn.commit()
    return project.model_dump()


@router.get("")
def list_projects(conn: sqlite3.Connection = Depends(get_conn)) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM projects ORDER BY name").fetchall()]
