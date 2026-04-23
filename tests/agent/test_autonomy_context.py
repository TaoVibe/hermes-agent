from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from agent.autonomy_context import (
    AutonomyBranch,
    build_autonomy_context_block,
    resolve_autonomy_context,
)
from run_agent import AIAgent


def test_resolve_autonomy_context_prefers_repo_local_contract(
    tmp_path: Path, monkeypatch
):
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    contract_path = repo / "src" / "kalshi_bot" / "tooling" / "autonomy"
    contract_path.mkdir(parents=True)
    (contract_path / "router_contract.json").write_text(
        '{"router_contract":{"mode_triggers":{"autonomous":{"inject_contract":"repo_autonomous_run"}}}}',
        encoding="utf-8",
    )

    resolution = resolve_autonomy_context(
        "run autonomously",
        cwd=repo,
        platform=None,
        has_conversation_history=False,
    )

    assert resolution.activated is True
    assert resolution.branch is AutonomyBranch.REPO_LOCAL
    assert resolution.repo_contract is not None
    assert resolution.repo_contract.contract_name == "repo_autonomous_run"


def test_resolve_autonomy_context_uses_cron_branch_without_repo_contract(
    tmp_path: Path,
):
    resolution = resolve_autonomy_context(
        "run autonomously",
        cwd=tmp_path,
        platform="cron",
        has_conversation_history=False,
    )

    assert resolution.branch is AutonomyBranch.CRON


def test_resolve_autonomy_context_uses_current_task_before_research(tmp_path: Path):
    resolution = resolve_autonomy_context(
        "run autonomously and research options",
        cwd=tmp_path,
        platform=None,
        has_conversation_history=True,
    )

    assert resolution.branch is AutonomyBranch.CURRENT_TASK


def test_resolve_autonomy_context_uses_research_branch(tmp_path: Path):
    resolution = resolve_autonomy_context(
        "run autonomously and research options",
        cwd=tmp_path,
        platform=None,
        has_conversation_history=False,
    )

    assert resolution.branch is AutonomyBranch.RESEARCH


def test_resolve_autonomy_context_fails_closed_for_bare_trigger(tmp_path: Path):
    resolution = resolve_autonomy_context(
        "run autonomously",
        cwd=tmp_path,
        platform=None,
        has_conversation_history=False,
    )

    assert resolution.branch is AutonomyBranch.INSUFFICIENT
    block = build_autonomy_context_block(resolution)
    assert "Ask one clarifying question" in block


def test_run_conversation_injects_autonomy_context_without_persisting_it(
    tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    with (
        patch("run_agent.get_tool_definitions", return_value=[]),
        patch("run_agent.check_toolset_requirements", return_value={}),
        patch("run_agent.OpenAI"),
    ):
        agent = AIAgent(
            api_key="test-key-1234567890",
            base_url="https://openrouter.ai/api/v1",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
        )
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="done", tool_calls=None),
                finish_reason="stop",
            )
        ]
    )
    agent._cached_system_prompt = "You are helpful."
    agent.client = MagicMock()
    agent.client.chat.completions.create.return_value = response
    agent._persist_session = lambda *args, **kwargs: None
    agent._save_trajectory = lambda *args, **kwargs: None
    agent._save_session_log = lambda *args, **kwargs: None
    agent._cleanup_task_resources = lambda *args, **kwargs: None
    agent._interruptible_api_call = lambda kwargs: response

    result = agent.run_conversation("run autonomously and research options")

    assert result["completed"] is True
    sent_messages = result["messages"]
    assert "<autonomy-contract>" in sent_messages[0]["content"]
    assert "branch: research" in sent_messages[0]["content"]
    assert sent_messages[0]["content"].startswith(
        "run autonomously and research options"
    )
