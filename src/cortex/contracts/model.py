from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Tier(StrEnum):
    FREE = "free"
    CHEAP = "cheap"
    PREMIUM = "premium"


class ModelInfo(BaseModel):
    name: str
    provider: str
    tier: Tier
    cost_per_mtok_in: float = 0.0
    cost_per_mtok_out: float = 0.0
    strengths: list[str] = Field(default_factory=list)
