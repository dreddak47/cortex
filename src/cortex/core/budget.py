from __future__ import annotations

import sqlite3

from pydantic import BaseModel

from cortex.core import ledger


class Budgets(BaseModel):
    global_daily_usd: float = 2.0
    per_run_usd: float = 0.5


class BudgetDecision(BaseModel):
    allowed: bool
    reason: str = ""
    spend_today_usd: float = 0.0


def check(conn: sqlite3.Connection, caps: Budgets, estimated_cost_usd: float) -> BudgetDecision:
    """The inner cost rail. LiteLLM enforces at the key level too — belt and
    suspenders. A blocked run queues (budget_blocked), it never hard-fails."""
    spent = ledger.spend_today(conn)
    if estimated_cost_usd > caps.per_run_usd:
        return BudgetDecision(
            allowed=False,
            reason=f"estimated ${estimated_cost_usd:.2f} exceeds per-run cap ${caps.per_run_usd:.2f}",
            spend_today_usd=spent,
        )
    if spent + estimated_cost_usd > caps.global_daily_usd:
        return BudgetDecision(
            allowed=False,
            reason=f"daily cap ${caps.global_daily_usd:.2f} would be exceeded (spent ${spent:.2f})",
            spend_today_usd=spent,
        )
    return BudgetDecision(allowed=True, spend_today_usd=spent)
