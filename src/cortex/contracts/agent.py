from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class HitlPolicy(StrEnum):
    NEVER = "never"
    ON_PREMIUM = "on_premium"
    ALWAYS = "always"


class BudgetPolicy(BaseModel):
    per_run_usd: float | None = None
    daily_usd: float | None = None


class AgentSpec(BaseModel):
    """An agent definition. type=spec: instructions sent to a model via the
    gateway. type=code: entrypoint is a `module:function` in this process
    (plain Python today, LangGraph later — same contract)."""

    name: str
    role: str
    type: Literal["spec", "code"] = "spec"
    instructions: str = ""
    entrypoint: str | None = None
    model_pref: str | None = None
    harness_pref: str | None = None
    tools: list[str] = Field(default_factory=list)
    triggers: list[str] = Field(default_factory=list)
    budget: BudgetPolicy = Field(default_factory=BudgetPolicy)
    hitl_policy: HitlPolicy = HitlPolicy.ON_PREMIUM
