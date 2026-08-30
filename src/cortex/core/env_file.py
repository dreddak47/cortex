"""Read/write the local .env — the dashboard's settings backend.

The .env is the single place keys live (docker compose reads it directly).
Writes preserve comments and unrelated lines; values are never logged and
GET responses only ever see masked hints.
"""

from __future__ import annotations

import os
from pathlib import Path

KEY_FIELDS = [
    "LITELLM_MASTER_KEY",
    "OPENROUTER_API_KEY",
    "GROQ_API_KEY",
    "ANTHROPIC_API_KEY",
]
CONFIG_FIELDS = ["CORTEX_GATEWAY_URL", "CORTEX_DB"]

DEFAULT_PATH = ".env"


def read(path: str | Path = DEFAULT_PATH) -> dict[str, str]:
    env_path = Path(path)
    if not env_path.exists():
        return {}
    values: dict[str, str] = {}
    for line in env_path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        values[key.strip()] = value.split("#")[0].strip()
    return values


def get(key: str, default: str = "", path: str | Path = DEFAULT_PATH) -> str:
    return os.environ.get(key) or read(path).get(key, "") or default


def update(updates: dict[str, str], path: str | Path = DEFAULT_PATH) -> None:
    env_path = Path(path)
    lines = env_path.read_text().splitlines() if env_path.exists() else []
    remaining = dict(updates)
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        key = stripped.partition("=")[0].strip() if "=" in stripped else None
        if key in remaining and not stripped.startswith("#"):
            out.append(f"{key}={remaining.pop(key)}")
        else:
            out.append(line)
    for key, value in remaining.items():
        out.append(f"{key}={value}")
    env_path.write_text("\n".join(out) + "\n")


def mask(value: str) -> dict:
    if not value:
        return {"set": False, "hint": ""}
    hint = value[-4:] if len(value) > 8 else ""
    return {"set": True, "hint": f"…{hint}" if hint else "set"}
