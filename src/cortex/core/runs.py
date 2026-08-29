from __future__ import annotations

import importlib
import json
import sqlite3

from cortex.contracts import Constraints, HarnessAdapter, Run, RunState
from cortex.core import budget, events, ledger
from cortex.core.registry import Registry


def create_run(
    conn: sqlite3.Connection,
    agent: str,
    task: str,
    harness: str | None = None,
    workspace: str | None = None,
    state: RunState = RunState.QUEUED,
) -> Run:
    run = Run(agent=agent, task=task, harness=harness, workspace=workspace, state=state)
    cur = conn.execute(
        "INSERT INTO runs (ts, agent, harness, task, workspace, state) VALUES (?, ?, ?, ?, ?, ?)",
        (run.ts, run.agent, run.harness, run.task, run.workspace, run.state.value),
    )
    conn.commit()
    run.id = cur.lastrowid
    events.publish(conn, "run.created", {"run_id": run.id, "agent": agent, "task": task[:200]})
    return run


def update_run(conn: sqlite3.Connection, run_id: int, **fields) -> None:
    columns, values = [], []
    for key, value in fields.items():
        if key == "result":
            key, value = "result_json", json.dumps(value)
        if isinstance(value, RunState):
            value = value.value
        columns.append(f"{key} = ?")
        values.append(value)
    conn.execute(f"UPDATE runs SET {', '.join(columns)} WHERE id = ?", (*values, run_id))
    conn.commit()


def list_runs(conn: sqlite3.Connection, limit: int = 50) -> list[dict]:
    rows = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def load_adapter(adapter_path: str, binary: str) -> HarnessAdapter:
    module_name, class_name = adapter_path.split(":")
    cls = getattr(importlib.import_module(module_name), class_name)
    return cls(binary=binary)


def dispatch_harness(
    conn: sqlite3.Connection,
    registry: Registry,
    harness_name: str,
    task: str,
    workspace: str,
    dry_run: bool = False,
) -> Run:
    entry = registry.harness(harness_name)
    if entry is None:
        raise ValueError(f"unknown harness: {harness_name!r}")

    adapter = load_adapter(entry.adapter, entry.binary)
    constraints = Constraints(
        max_cost_usd=registry.budgets.per_run_usd, **entry.constraints
    )

    run = create_run(conn, agent="dispatch", task=task, harness=harness_name, workspace=workspace)

    decision = budget.check(conn, registry.budgets, registry.budgets.per_run_usd)
    if not decision.allowed:
        update_run(conn, run.id, state=RunState.BUDGET_BLOCKED, result={"reason": decision.reason})
        events.publish(conn, "run.budget_blocked", {"run_id": run.id, "reason": decision.reason})
        run.state = RunState.BUDGET_BLOCKED
        return run

    if dry_run:
        command = adapter.build_command(task, constraints)
        update_run(conn, run.id, result={"dry_run": True, "command": command})
        run.result = {"dry_run": True, "command": command}
        return run

    update_run(conn, run.id, state=RunState.RUNNING)
    result = adapter.run(task, workspace, constraints)
    update_run(
        conn,
        run.id,
        state=result.state,
        result=result.model_dump(exclude={"logs"}),
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        cost_usd=result.cost_usd,
        duration_s=result.duration_s,
    )
    ledger.record_call(
        conn,
        model=harness_name,
        provider="harness",
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        cost_usd=result.cost_usd,
        purpose="harness_run",
        run_id=run.id,
    )
    events.publish(
        conn,
        "run.finished",
        {"run_id": run.id, "state": result.state.value, "pr_url": result.pr_url},
    )
    run.state = result.state
    return run
