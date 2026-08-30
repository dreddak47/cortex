from __future__ import annotations

import re
import subprocess
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from cortex.core import env_file
from cortex.core import registry as registry_loader

router = APIRouter(prefix="/settings", tags=["settings"])

MODELS_YAML = Path("config/registries/models.yaml")


@router.get("")
def get_settings(request: Request) -> dict:
    values = env_file.read()
    return {
        "keys": {k: env_file.mask(values.get(k, "")) for k in env_file.KEY_FIELDS},
        "config": {k: values.get(k, "") for k in env_file.CONFIG_FIELDS},
        "budgets": request.app.state.registry.budgets.model_dump(),
    }


@router.put("/keys")
def put_keys(body: dict[str, str]) -> dict:
    allowed = set(env_file.KEY_FIELDS + env_file.CONFIG_FIELDS)
    updates = {k: v.strip() for k, v in body.items() if k in allowed and v and v.strip()}
    if not updates:
        raise HTTPException(400, "no recognized non-empty settings in request")
    env_file.update(updates)
    return {"saved": sorted(updates.keys())}


class BudgetsIn(BaseModel):
    global_daily_usd: float
    per_run_usd: float


@router.put("/budgets")
def put_budgets(body: BudgetsIn, request: Request) -> dict:
    # targeted line edit so the yaml comments survive
    text = MODELS_YAML.read_text()
    text = re.sub(r"(global_daily_usd:\s*)[\d.]+", rf"\g<1>{body.global_daily_usd:.2f}", text)
    text = re.sub(r"(per_run_usd:\s*)[\d.]+", rf"\g<1>{body.per_run_usd:.2f}", text)
    MODELS_YAML.write_text(text)
    request.app.state.registry = registry_loader.load()
    return request.app.state.registry.budgets.model_dump()


@router.get("/gateway")
def gateway_status() -> dict:
    url = env_file.get("CORTEX_GATEWAY_URL", "http://localhost:4000").rstrip("/")
    try:
        resp = httpx.get(f"{url}/health/liveliness", timeout=2.0)
        return {"url": url, "up": resp.status_code < 500}
    except (httpx.HTTPError, OSError):
        return {"url": url, "up": False}


@router.post("/gateway/restart")
def gateway_restart() -> dict:
    """User-clicked: (re)start the LiteLLM container so freshly saved keys load."""
    try:
        proc = subprocess.run(
            ["docker", "compose", "up", "-d", "--force-recreate", "litellm"],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        raise HTTPException(502, f"docker compose failed: {exc}")
    if proc.returncode != 0:
        raise HTTPException(502, proc.stderr[-1000:])
    return {"restarted": True}
