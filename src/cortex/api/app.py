from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterator

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from cortex.core import db, registry as registry_loader

STATIC_DIR = Path(__file__).parent / "static"


def get_conn() -> Iterator[sqlite3.Connection]:
    conn = db.connect()
    try:
        yield conn
    finally:
        conn.close()


def create_app(config_dir: str = "config") -> FastAPI:
    from cortex.api.routes import actions, agents, costs, events, ideas, projects, runs, settings

    app = FastAPI(title="Cortex", description="Personal AI control plane")
    app.state.registry = registry_loader.load(config_dir)

    # run migrations once at startup
    db.connect().close()

    for router in (
        ideas.router,
        events.router,
        runs.router,
        agents.router,
        costs.router,
        projects.router,
        settings.router,
        actions.router,
    ):
        app.include_router(router)

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def dashboard() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/meta")
    def meta() -> dict:
        return {
            "name": "cortex",
            "agents": [a.name for a in app.state.registry.agents],
            "harnesses": [h.name for h in app.state.registry.harnesses],
            "models": [m.name for m in app.state.registry.models],
        }

    return app
