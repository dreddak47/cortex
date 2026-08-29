from cortex.contracts import AgentSpec, Constraints, RunResult, RunState, Tier
from cortex.adapters.claude_code import ClaudeCodeAdapter
from cortex.contracts.harness import HarnessAdapter


def test_registry_loads_all_registries(registry):
    assert registry.model("free/llama-70b").tier == Tier.FREE
    assert registry.model("premium/sonnet").tier == Tier.PREMIUM
    assert registry.harness("claude-code").binary == "claude"
    assert registry.budgets.global_daily_usd > 0


def test_agent_spec_parses_frontmatter_and_instructions(registry):
    spec = registry.agent("router-planner")
    assert spec is not None
    assert spec.type == "code"
    assert spec.entrypoint == "cortex.agents.router_planner:route_ideas"
    assert spec.model_pref == "free/llama-70b"
    assert "strict JSON" in spec.instructions


def test_agent_spec_round_trip():
    spec = AgentSpec(name="x", role="y", instructions="do things")
    assert AgentSpec.model_validate(spec.model_dump()) == spec


def test_claude_code_adapter_satisfies_harness_contract():
    adapter = ClaudeCodeAdapter()
    assert isinstance(adapter, HarnessAdapter)
    cmd = adapter.build_command("fix the bug", Constraints())
    assert cmd[0] == "claude"
    assert "--output-format" in cmd
    assert "--permission-mode" in cmd


def test_run_result_defaults():
    result = RunResult(state=RunState.DONE)
    assert result.cost_usd == 0.0
    assert result.pr_url is None
