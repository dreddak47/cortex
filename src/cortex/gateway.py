from __future__ import annotations

import os
import sqlite3

import httpx

from cortex.core import ledger
from cortex.core.registry import Registry


class GatewayUnavailable(RuntimeError):
    """LiteLLM proxy unreachable or unkeyed. Callers degrade gracefully."""


class Gateway:
    """Thin client for the LiteLLM proxy. Every call lands in the ledger —
    metrics are a byproduct of logging, never a separate system."""

    def __init__(self, conn: sqlite3.Connection, registry: Registry, url: str | None = None):
        self.conn = conn
        self.registry = registry
        self.url = (url or os.environ.get("CORTEX_GATEWAY_URL", "http://localhost:4000")).rstrip("/")
        self.key = os.environ.get("LITELLM_MASTER_KEY", "sk-cortex-local")

    def chat(
        self,
        model: str,
        messages: list[dict],
        purpose: str = "",
        run_id: int | None = None,
        timeout: float = 120.0,
    ) -> str:
        try:
            resp = httpx.post(
                f"{self.url}/chat/completions",
                headers={"Authorization": f"Bearer {self.key}"},
                json={"model": model, "messages": messages},
                timeout=timeout,
            )
            resp.raise_for_status()
        except (httpx.HTTPError, OSError) as exc:
            raise GatewayUnavailable(f"gateway at {self.url}: {exc}") from exc

        data = resp.json()
        usage = data.get("usage", {})
        tokens_in = usage.get("prompt_tokens", 0)
        tokens_out = usage.get("completion_tokens", 0)

        info = self.registry.model(model)
        cost = 0.0
        if info:
            cost = (
                tokens_in * info.cost_per_mtok_in + tokens_out * info.cost_per_mtok_out
            ) / 1_000_000
        ledger.record_call(
            self.conn,
            model=model,
            provider=info.provider if info else "",
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost,
            purpose=purpose,
            run_id=run_id,
        )
        return data["choices"][0]["message"]["content"]
