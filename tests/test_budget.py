from cortex.contracts import RunState
from cortex.core import budget, ledger, runs


def test_allows_under_cap(tmp_db):
    caps = budget.Budgets(global_daily_usd=2.0, per_run_usd=0.5)
    decision = budget.check(tmp_db, caps, 0.10)
    assert decision.allowed


def test_blocks_over_per_run_cap(tmp_db):
    caps = budget.Budgets(global_daily_usd=2.0, per_run_usd=0.5)
    decision = budget.check(tmp_db, caps, 0.60)
    assert not decision.allowed
    assert "per-run cap" in decision.reason


def test_blocks_when_daily_cap_exhausted(tmp_db):
    caps = budget.Budgets(global_daily_usd=1.0, per_run_usd=0.5)
    ledger.record_call(tmp_db, model="cheap/haiku", cost_usd=0.9)
    decision = budget.check(tmp_db, caps, 0.2)
    assert not decision.allowed
    assert "daily cap" in decision.reason


def test_dispatch_degrades_to_budget_blocked(tmp_db, registry):
    # exhaust the daily budget, then dispatch: run must queue as blocked, not fail
    ledger.record_call(tmp_db, model="premium/sonnet", cost_usd=registry.budgets.global_daily_usd)
    run = runs.dispatch_harness(
        tmp_db, registry, "claude-code", task="do something", workspace="/tmp", dry_run=True
    )
    assert run.state == RunState.BUDGET_BLOCKED
    row = tmp_db.execute("SELECT state FROM runs WHERE id = ?", (run.id,)).fetchone()
    assert row["state"] == "budget_blocked"


def test_dry_run_dispatch_records_command(tmp_db, registry):
    run = runs.dispatch_harness(
        tmp_db, registry, "claude-code", task="add a README badge", workspace="/tmp", dry_run=True
    )
    assert run.result["dry_run"] is True
    assert run.result["command"][0] == "claude"
