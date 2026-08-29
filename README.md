# Cortex — Personal AI Control Plane

One local system where ideas enter, agents work, memory compounds, costs stay
governed, and your growth is measured.

Cortex is not an app; it is a **control plane** over four swappable registries —
**harnesses, models, agents, tools** — plus a memory layer and an event bus
underneath. Every capability is a plug. Dashboards are views over state that
already exists.

```
                    ┌── ideas in (CLI / API / channels) ──┐
                    ▼                                      │
   ┌─────────── CORE SERVER (FastAPI) ────────────┐        │
   │ event bus · run engine · budget gate · HITL  │        │
   ├──────────┬─────────┬─────────┬────────┬──────┤        │
   │ HARNESSES│ MODELS  │ AGENTS  │ TOOLS  │ CHAN │        │
   │ claude-  │ LiteLLM │ spec/   │ MCP    │ slack│◄───────┘
   │ code,    │ proxy   │ code    │ servers│ tg…  │
   │ codex, pi│ (tiers) │         │        │      │
   ├──────────┴─────────┴─────────┴────────┴──────┤
   │ MEMORY: markdown vault + retrieval index     │
   │ LEDGER: SQLite — every run, token, dollar    │
   └──────────────────────────────────────────────┘
```

**Design principles:** local-first (SQLite + markdown are the source of truth) ·
contracts before features · cost-governed by default · HITL is a first-class
state · everything logged · growth is a feature.

## Status

| Phase | Scope | State |
|---|---|---|
| 0 | Contracts, event bus, ledger, LiteLLM gateway | ✅ done |
| 1 | Idea inbox → Router/Planner → Claude Code harness → PR | ✅ working (plain-Python router) |
| 2 | Memory vault + retrieve/writeback | `vault/` placeholder |
| 3 | Scheduler, HITL queue, channels | contracts exist (`Channel`, `RunState.NEEDS_HUMAN`) |
| 4 | Metrics, growth tracking, cloud mirror | ledger schema is DuckDB-attachable |
| 5 | More harnesses, agent lab, policy engine | adapter contract ready |

## Quickstart

```bash
uv sync                          # install
cp .env.example .env             # add API keys when you have them
uv run pytest                    # 14 tests
make dev                         # API on :8000 (docs at /docs)
make gateway                     # LiteLLM proxy on :4000 (needs keys in .env)
```

The system works **without any API keys**: the router degrades to
deterministic routing, and the Claude Code harness runs on your existing
subscription.

## The daily loop

```bash
# capture ideas the moment they occur
uv run cortex idea "cache the retrieval index" --project cortex

# register a project once (repo for issues, workspace for harness runs)
uv run cortex project add cortex --repo you/cortex --workspace ~/Documents/cortex

# route: new ideas → concrete tasks → GitHub issues
uv run cortex route --dry-run     # preview
uv run cortex route               # file the issues

# dispatch an approved task to a harness → it opens a PR
uv run cortex run "issue #12: cache the retrieval index" --project cortex --dry-run
uv run cortex run "issue #12: cache the retrieval index" --project cortex

# governance
uv run cortex costs               # spend vs caps, by model
```

## The contracts (`src/cortex/contracts/`)

Everything is built against five interfaces plus memory — swap implementations,
never rewrite callers:

| Contract | Shape |
|---|---|
| `HarnessAdapter` | `run(task, workspace, constraints) -> RunResult` |
| `ModelInfo` | name, tier (`free\|cheap\|premium`), cost/Mtok, strengths |
| `AgentSpec` | md + YAML frontmatter; `type: spec` (prompt) or `type: code` (Python entrypoint) |
| `ToolEntry` | an MCP server: name, transport, scopes |
| `Channel` | `emit(event)` / `notify(message, reply_hook)` |
| `MemoryStore` | `retrieve(project, task, k) -> ContextBundle` / `writeback(...)` |

Registries live in `config/registries/` — add a model to `models.yaml`, a
harness to `harnesses.yaml`, or drop an agent `.md` into `agents/` and it is
loaded at startup.

## Cost governance (the spine)

Two rails, belt and suspenders:

1. **LiteLLM proxy** (`config/litellm.yaml`) — per-key budgets at the gateway.
2. **`core/budget.py`** — the run engine checks per-run and daily caps
   (`config/registries/models.yaml → budgets:`) before every dispatch.
   A blocked run becomes `budget_blocked` and queues — it never hard-fails.

Tier routing: triage/routing = free tier always; research = cheap;
implementation = premium, and only on approved tasks.

## Rules that never change

- Agents never push to main. PRs only, forever.
- No run without a budget check.
- Metrics are a byproduct of logging (`ledger` table), never a separate system.
- Views (dashboards) come last in every phase.
