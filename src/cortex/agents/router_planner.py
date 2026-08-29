from __future__ import annotations

import json
import sqlite3
import subprocess

from cortex.core import events
from cortex.core.registry import Registry
from cortex.gateway import Gateway, GatewayUnavailable

AGENT_NAME = "router-planner"


def _fallback_tasks(ideas: list[sqlite3.Row]) -> list[dict]:
    """No gateway (or no keys yet): deterministic one-task-per-idea routing so
    the pipeline works end to end from day one."""
    return [
        {
            "idea_id": r["id"],
            "project": r["project"] or "inbox",
            "title": r["text"][:72],
            "body": f"Idea captured {r['ts']} via {r['source']}:\n\n{r['text']}",
        }
        for r in ideas
    ]


def _llm_tasks(gateway: Gateway, spec, ideas: list[sqlite3.Row]) -> list[dict]:
    idea_lines = "\n".join(
        f'- id={r["id"]} project={r["project"] or "?"}: {r["text"]}' for r in ideas
    )
    text = gateway.chat(
        model=spec.model_pref,
        messages=[
            {"role": "system", "content": spec.instructions},
            {"role": "user", "content": f"New ideas:\n{idea_lines}"},
        ],
        purpose="route_ideas",
    )
    start, end = text.find("["), text.rfind("]")
    tasks = json.loads(text[start : end + 1])
    if not isinstance(tasks, list):
        raise ValueError("router output is not a JSON list")
    return tasks


def _file_issue(repo: str, title: str, body: str) -> str:
    proc = subprocess.run(
        ["gh", "issue", "create", "-R", repo, "-t", title, "-b", body],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()  # issue URL


def route_ideas(
    conn: sqlite3.Connection,
    registry: Registry,
    gateway: Gateway | None = None,
    dry_run: bool = False,
) -> list[dict]:
    """Router/Planner: new ideas -> concrete tasks -> GitHub issues.
    Returns the task list (with issue URLs when filed)."""
    spec = registry.agent(AGENT_NAME)
    ideas = conn.execute("SELECT * FROM ideas WHERE status = 'new' ORDER BY id").fetchall()
    if not ideas:
        return []

    tasks: list[dict]
    used_llm = False
    if gateway is not None and spec is not None and spec.model_pref:
        try:
            tasks = _llm_tasks(gateway, spec, ideas)
            used_llm = True
        except (GatewayUnavailable, ValueError, json.JSONDecodeError):
            tasks = _fallback_tasks(ideas)
    else:
        tasks = _fallback_tasks(ideas)

    projects = {
        r["name"]: r["repo"] for r in conn.execute("SELECT name, repo FROM projects").fetchall()
    }
    for task in tasks:
        repo = projects.get(task.get("project", ""))
        if dry_run or not repo:
            task["issue_url"] = None
            task["filed"] = False
        else:
            task["issue_url"] = _file_issue(repo, task["title"], task["body"])
            task["filed"] = True

    if not dry_run:
        routed_ids = [t["idea_id"] for t in tasks if "idea_id" in t]
        conn.executemany("UPDATE ideas SET status = 'routed' WHERE id = ?", [(i,) for i in routed_ids])
        conn.commit()

    events.publish(
        conn,
        "ideas.routed",
        {"count": len(tasks), "used_llm": used_llm, "dry_run": dry_run},
    )
    return tasks
