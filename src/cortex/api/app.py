from __future__ import annotations

import sqlite3
from typing import Iterator

from fastapi import FastAPI

from cortex.core import db, registry as registry_loader


def get_conn() -> Iterator[sqlite3.Connection]:
    conn = db.connect()
    try:
        yield conn
    finally:
        conn.close()


def create_app(config_dir: str = "config") -> FastAPI:
    from cortex.api.routes import agents, costs, events, ideas, projects, runs

    app = FastAPI(title="Cortex", description="Personal AI control plane")
    app.state.registry = registry_loader.load(config_dir)

    # run migrations once at startup
    db.connect().close()

    for router in (ideas.router, events.router, runs.router, agents.router, costs.router, projects.router):
        app.include_router(router)

    @app.get("/")
    def root() -> dict:
        return {
            "name": "cortex",
            "agents": [a.name for a in app.state.registry.agents],
            "harnesses": [h.name for h in app.state.registry.harnesses],
            "models": [m.name for m in app.state.registry.models],
        }

    return app
