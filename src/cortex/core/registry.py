from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from cortex.contracts import AgentSpec, ModelInfo
from cortex.core.budget import Budgets


class HarnessEntry(BaseModel):
    name: str
    binary: str
    adapter: str
    constraints: dict = Field(default_factory=dict)


class Registry(BaseModel):
    models: list[ModelInfo] = Field(default_factory=list)
    harnesses: list[HarnessEntry] = Field(default_factory=list)
    agents: list[AgentSpec] = Field(default_factory=list)
    budgets: Budgets = Field(default_factory=Budgets)

    def model(self, name: str) -> ModelInfo | None:
        return next((m for m in self.models if m.name == name), None)

    def harness(self, name: str) -> HarnessEntry | None:
        return next((h for h in self.harnesses if h.name == name), None)

    def agent(self, name: str) -> AgentSpec | None:
        return next((a for a in self.agents if a.name == name), None)


def parse_agent_file(path: Path) -> AgentSpec:
    """AgentSpec files are markdown with YAML frontmatter; the body is the
    agent's instructions."""
    text = path.read_text()
    if not text.startswith("---"):
        raise ValueError(f"{path}: agent spec must start with YAML frontmatter")
    _, frontmatter, body = text.split("---", 2)
    meta = yaml.safe_load(frontmatter)
    meta["instructions"] = body.strip()
    return AgentSpec.model_validate(meta)


def load(config_dir: str | Path = "config") -> Registry:
    config = Path(config_dir)
    registries = config / "registries"

    models_doc = yaml.safe_load((registries / "models.yaml").read_text())
    harness_doc = yaml.safe_load((registries / "harnesses.yaml").read_text())
    agents = [parse_agent_file(p) for p in sorted((registries / "agents").glob("*.md"))]

    return Registry(
        models=[ModelInfo.model_validate(m) for m in models_doc.get("models", [])],
        budgets=Budgets.model_validate(models_doc.get("budgets", {})),
        harnesses=[HarnessEntry.model_validate(h) for h in harness_doc.get("harnesses", [])],
        agents=agents,
    )
