from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    NEEDS_HUMAN = "needs_human"
    DONE = "done"
    FAILED = "failed"
    BUDGET_BLOCKED = "budget_blocked"


class Event(BaseModel):
    id: int | None = None
    ts: str = Field(default_factory=utcnow)
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)


class Run(BaseModel):
    id: int | None = None
    ts: str = Field(default_factory=utcnow)
    agent: str
    harness: str | None = None
    task: str
    workspace: str | None = None
    state: RunState = RunState.QUEUED
    result: dict[str, Any] = Field(default_factory=dict)
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    duration_s: float = 0.0
