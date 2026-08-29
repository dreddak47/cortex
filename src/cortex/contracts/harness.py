from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from cortex.contracts.events import RunState


class Constraints(BaseModel):
    max_cost_usd: float | None = None
    max_duration_s: int = 1800
    permission_mode: str = "acceptEdits"
    allowed_tools: list[str] = Field(default_factory=list)


class RunResult(BaseModel):
    state: RunState
    summary: str = ""
    pr_url: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    duration_s: float = 0.0
    logs: str = ""


@runtime_checkable
class HarnessAdapter(Protocol):
    """A black-box coding harness (Claude Code, Codex, Pi...)."""

    name: str

    def run(self, task: str, workspace: str, constraints: Constraints) -> RunResult: ...
