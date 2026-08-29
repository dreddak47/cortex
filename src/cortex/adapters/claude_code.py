from __future__ import annotations

import json
import subprocess
import time

from cortex.contracts import Constraints, RunResult, RunState

PROMPT_TEMPLATE = """You are working on an approved task in this repository.

Task:
{task}

Rules:
- Create a feature branch; never commit to main.
- When done, open a pull request with `gh pr create` and include a summary
  of what changed and how you verified it.
"""


class ClaudeCodeAdapter:
    """Drives Claude Code headless (`claude -p --output-format json`).
    Runs on the user's subscription — no API key required."""

    name = "claude-code"

    def __init__(self, binary: str = "claude"):
        self.binary = binary

    def build_command(self, task: str, constraints: Constraints) -> list[str]:
        cmd = [
            self.binary,
            "-p",
            PROMPT_TEMPLATE.format(task=task),
            "--output-format",
            "json",
            "--permission-mode",
            constraints.permission_mode,
        ]
        if constraints.allowed_tools:
            cmd += ["--allowed-tools", ",".join(constraints.allowed_tools)]
        return cmd

    def run(self, task: str, workspace: str, constraints: Constraints) -> RunResult:
        cmd = self.build_command(task, constraints)
        start = time.monotonic()
        try:
            proc = subprocess.run(
                cmd,
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=constraints.max_duration_s,
            )
        except subprocess.TimeoutExpired:
            return RunResult(
                state=RunState.FAILED,
                summary=f"timed out after {constraints.max_duration_s}s",
                duration_s=time.monotonic() - start,
            )
        duration = time.monotonic() - start

        if proc.returncode != 0:
            return RunResult(
                state=RunState.FAILED,
                summary=f"exit {proc.returncode}",
                logs=proc.stderr[-4000:],
                duration_s=duration,
            )

        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return RunResult(
                state=RunState.FAILED,
                summary="unparseable harness output",
                logs=proc.stdout[-4000:],
                duration_s=duration,
            )

        usage = data.get("usage", {})
        summary = data.get("result", "") or ""
        pr_url = next((w for w in summary.split() if "/pull/" in w), None)
        return RunResult(
            state=RunState.FAILED if data.get("is_error") else RunState.DONE,
            summary=summary[:2000],
            pr_url=pr_url,
            tokens_in=usage.get("input_tokens", 0),
            tokens_out=usage.get("output_tokens", 0),
            cost_usd=data.get("total_cost_usd", 0.0),
            duration_s=duration,
        )
