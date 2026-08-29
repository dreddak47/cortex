from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ToolEntry(BaseModel):
    """An MCP server registration."""

    name: str
    transport: Literal["stdio", "sse", "http"] = "stdio"
    command: str | None = None
    url: str | None = None
    scopes: list[str] = Field(default_factory=list)
