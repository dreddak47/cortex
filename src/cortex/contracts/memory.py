from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field


class ContextBundle(BaseModel):
    project: str
    task: str
    snippets: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    style_notes: str = ""


@runtime_checkable
class MemoryStore(Protocol):
    def retrieve(self, project: str, task: str, k: int = 8) -> ContextBundle: ...

    def writeback(
        self,
        project: str,
        run_summary: str,
        decisions: list[str],
        learnings: list[str],
    ) -> None: ...


class NullMemory:
    """Phase 2 placeholder: the vault index replaces this. Every agent already
    speaks the contract, so swapping it in is a one-line change."""

    def retrieve(self, project: str, task: str, k: int = 8) -> ContextBundle:
        return ContextBundle(project=project, task=task)

    def writeback(
        self,
        project: str,
        run_summary: str,
        decisions: list[str],
        learnings: list[str],
    ) -> None:
        return None
