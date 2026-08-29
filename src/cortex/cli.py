from __future__ import annotations

import json

import typer

from cortex.contracts.events import utcnow
from cortex.core import db, events, ledger
from cortex.core import registry as registry_loader
from cortex.core import runs as run_engine

app = typer.Typer(help="Cortex — personal AI control plane.", no_args_is_help=True)
project_app = typer.Typer(help="Manage projects (repo + workspace).", no_args_is_help=True)
app.add_typer(project_app, name="project")


@app.command()
def idea(text: str, project: str = typer.Option(None), source: str = "cli") -> None:
    """Capture an idea into the inbox."""
    conn = db.connect()
    cur = conn.execute(
        "INSERT INTO ideas (ts, text, project, source) VALUES (?, ?, ?, ?)",
        (utcnow(), text, project, source),
    )
    conn.commit()
    events.publish(conn, "idea.captured", {"idea_id": cur.lastrowid, "project": project})
    typer.echo(f"idea #{cur.lastrowid} captured" + (f" → {project}" if project else ""))


@app.command()
def ideas(status: str = typer.Option(None)) -> None:
    """List captured ideas."""
    conn = db.connect()
    query = "SELECT * FROM ideas" + (" WHERE status = ?" if status else "") + " ORDER BY id"
    rows = conn.execute(query, (status,) if status else ()).fetchall()
    for r in rows:
        typer.echo(f'#{r["id"]} [{r["status"]}] ({r["project"] or "-"}) {r["text"]}')


@app.command()
def route(dry_run: bool = typer.Option(False, "--dry-run")) -> None:
    """Run the Router/Planner: new ideas → tasks → GitHub issues."""
    from cortex.agents.router_planner import route_ideas
    from cortex.gateway import Gateway

    conn = db.connect()
    registry = registry_loader.load()
    tasks = route_ideas(conn, registry, gateway=Gateway(conn, registry), dry_run=dry_run)
    if not tasks:
        typer.echo("no new ideas to route")
        return
    for t in tasks:
        marker = t.get("issue_url") or ("(dry-run)" if dry_run else "(no repo — not filed)")
        typer.echo(f'[{t.get("project")}] {t.get("title")} {marker}')


@app.command()
def run(
    task: str,
    project: str = typer.Option(None, help="use this project's workspace"),
    workspace: str = typer.Option(None, help="or an explicit path"),
    harness: str = "claude-code",
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Dispatch a task to a coding harness (opens a PR when done)."""
    conn = db.connect()
    registry = registry_loader.load()
    if project and not workspace:
        row = conn.execute(
            "SELECT workspace_path FROM projects WHERE name = ?", (project,)
        ).fetchone()
        workspace = row["workspace_path"] if row else None
    if not workspace:
        typer.echo("error: need --workspace or a --project with a workspace_path", err=True)
        raise typer.Exit(1)

    result = run_engine.dispatch_harness(conn, registry, harness, task, workspace, dry_run=dry_run)
    typer.echo(f"run #{result.id} → {result.state.value}")
    if result.result:
        typer.echo(json.dumps(result.result, indent=2))


@app.command()
def costs() -> None:
    """Spend summary from the ledger."""
    conn = db.connect()
    registry = registry_loader.load()
    report = ledger.summary(conn)
    caps = registry.budgets
    typer.echo(f'today: ${report["today_usd"]:.4f} / ${caps.global_daily_usd:.2f} daily cap')
    typer.echo(f'total: ${report["total_usd"]:.4f}')
    for row in report["by_model"]:
        typer.echo(
            f'  {row["model"]}: {row["calls"]} calls, '
            f'{row["tokens_in"]}/{row["tokens_out"]} tok, ${row["cost_usd"]:.4f}'
        )


@app.command()
def serve(port: int = 8000, reload: bool = True) -> None:
    """Start the API server."""
    import uvicorn

    uvicorn.run("cortex.api.app:create_app", factory=True, port=port, reload=reload)


@project_app.command("add")
def project_add(
    name: str,
    repo: str = typer.Option(None, help="owner/repo for GitHub issues"),
    workspace: str = typer.Option(None, help="local clone path for harness runs"),
) -> None:
    conn = db.connect()
    conn.execute(
        "INSERT INTO projects (name, repo, workspace_path) VALUES (?, ?, ?)"
        " ON CONFLICT(name) DO UPDATE SET repo = excluded.repo,"
        " workspace_path = excluded.workspace_path",
        (name, repo, workspace),
    )
    conn.commit()
    typer.echo(f"project {name} registered")


@project_app.command("list")
def project_list() -> None:
    conn = db.connect()
    for r in conn.execute("SELECT * FROM projects ORDER BY name").fetchall():
        typer.echo(f'{r["name"]}: repo={r["repo"] or "-"} workspace={r["workspace_path"] or "-"}')


if __name__ == "__main__":
    app()
