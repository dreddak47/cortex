"""Capture your first ideas interactively. The system is alive from day one."""

from cortex.contracts.events import utcnow
from cortex.core import db, events


def main() -> None:
    conn = db.connect()
    print("Type ideas one per line, optionally prefixed 'project: idea'. Empty line to stop.\n")
    count = 0
    while True:
        line = input("> ").strip()
        if not line:
            break
        project, _, rest = line.partition(":")
        if rest.strip():
            project, text = project.strip(), rest.strip()
        else:
            project, text = None, line
        cur = conn.execute(
            "INSERT INTO ideas (ts, text, project, source) VALUES (?, ?, ?, 'seed')",
            (utcnow(), text, project),
        )
        conn.commit()
        events.publish(conn, "idea.captured", {"idea_id": cur.lastrowid, "project": project})
        count += 1
    print(f"\n{count} ideas captured. Run `uv run cortex route --dry-run` to see the routing.")


if __name__ == "__main__":
    main()
