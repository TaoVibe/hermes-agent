"""Context-sensitive autonomous contract selection for outer Hermes sessions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

_AUTONOMOUS_TRIGGER_PHRASES = (
    "run autonomously",
    "do this autonomously",
    "autonomous mode",
    "run in autonomous mode",
)
_RESEARCH_KEYWORDS = (
    "research",
    "investigate",
    "explore",
    "compare",
    "survey",
    "discover",
    "options",
)
_REPO_CONTRACT_CANDIDATES = (
    ".hermes-autonomy.json",
    ".hermes/router_contract.json",
)


class AutonomyBranch(StrEnum):
    REPO_LOCAL = "repo_local"
    CRON = "cron"
    CURRENT_TASK = "current_task"
    RESEARCH = "research"
    GENERIC = "generic"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True, slots=True)
class RepoContractSummary:
    path: str
    contract_name: str | None


@dataclass(frozen=True, slots=True)
class AutonomyResolution:
    activated: bool
    branch: AutonomyBranch | None
    reason: str | None
    matched_phrase: str | None
    repo_contract: RepoContractSummary | None


def _normalized(text: str) -> str:
    return " ".join(text.casefold().split())


def _find_git_root(start: Path) -> Path | None:
    current = start.resolve()
    for parent in [current, *current.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def _search_repo_contract(cwd: Path) -> Path | None:
    repo_root = _find_git_root(cwd)
    search_roots = [cwd.resolve(), *(cwd.resolve().parents)]
    if repo_root is not None and repo_root not in search_roots:
        search_roots.append(repo_root)

    for directory in search_roots:
        for candidate in _REPO_CONTRACT_CANDIDATES:
            path = directory / candidate
            if path.is_file():
                return path
        explicit_kalshi = (
            directory
            / "src"
            / "kalshi_bot"
            / "tooling"
            / "autonomy"
            / "router_contract.json"
        )
        if explicit_kalshi.is_file():
            return explicit_kalshi
        if repo_root is not None and directory == repo_root:
            break
    return None


def _load_repo_contract_summary(path: Path) -> RepoContractSummary:
    contract_name: str | None = None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            root = payload.get("router_contract")
            if isinstance(root, dict):
                mode_triggers = root.get("mode_triggers")
                if isinstance(mode_triggers, dict):
                    autonomous = mode_triggers.get("autonomous")
                    if isinstance(autonomous, dict):
                        raw_name = autonomous.get("inject_contract")
                        if isinstance(raw_name, str) and raw_name:
                            contract_name = raw_name
    except Exception:
        contract_name = None
    return RepoContractSummary(path=str(path), contract_name=contract_name)


def resolve_autonomy_context(
    user_message: str,
    *,
    cwd: str | Path,
    platform: str | None,
    has_conversation_history: bool,
) -> AutonomyResolution:
    normalized = _normalized(user_message)
    matched_phrase = next(
        (
            phrase
            for phrase in _AUTONOMOUS_TRIGGER_PHRASES
            if _normalized(phrase) in normalized
        ),
        None,
    )
    if matched_phrase is None:
        return AutonomyResolution(
            activated=False,
            branch=None,
            reason=None,
            matched_phrase=None,
            repo_contract=None,
        )

    cwd_path = Path(cwd).resolve()
    repo_contract_path = _search_repo_contract(cwd_path)
    if repo_contract_path is not None:
        return AutonomyResolution(
            activated=True,
            branch=AutonomyBranch.REPO_LOCAL,
            reason="active_repo_has_repo_local_contract",
            matched_phrase=matched_phrase,
            repo_contract=_load_repo_contract_summary(repo_contract_path),
        )

    if (platform or "").casefold() == "cron":
        return AutonomyResolution(
            activated=True,
            branch=AutonomyBranch.CRON,
            reason="cron_session_context",
            matched_phrase=matched_phrase,
            repo_contract=None,
        )

    if has_conversation_history:
        return AutonomyResolution(
            activated=True,
            branch=AutonomyBranch.CURRENT_TASK,
            reason="existing_scoped_session_context",
            matched_phrase=matched_phrase,
            repo_contract=None,
        )

    if any(keyword in normalized for keyword in _RESEARCH_KEYWORDS):
        return AutonomyResolution(
            activated=True,
            branch=AutonomyBranch.RESEARCH,
            reason="research_intent_detected",
            matched_phrase=matched_phrase,
            repo_contract=None,
        )

    if normalized.strip() in {
        _normalized(phrase) for phrase in _AUTONOMOUS_TRIGGER_PHRASES
    }:
        return AutonomyResolution(
            activated=True,
            branch=AutonomyBranch.INSUFFICIENT,
            reason="insufficient_scope_for_safe_autonomy",
            matched_phrase=matched_phrase,
            repo_contract=None,
        )

    return AutonomyResolution(
        activated=True,
        branch=AutonomyBranch.GENERIC,
        reason="generic_bounded_autonomy_fallback",
        matched_phrase=matched_phrase,
        repo_contract=None,
    )


def build_autonomy_context_block(resolution: AutonomyResolution) -> str:
    if not resolution.activated or resolution.branch is None:
        return ""

    header = [
        "<autonomy-contract>",
        f"branch: {resolution.branch.value}",
        f"reason: {resolution.reason or 'unknown'}",
    ]
    if resolution.matched_phrase is not None:
        header.append(f"trigger_phrase: {resolution.matched_phrase}")
    if resolution.repo_contract is not None:
        header.append(f"repo_contract_path: {resolution.repo_contract.path}")
        if resolution.repo_contract.contract_name is not None:
            header.append(
                f"repo_contract_name: {resolution.repo_contract.contract_name}"
            )

    if resolution.branch is AutonomyBranch.REPO_LOCAL:
        body = [
            "Use the repo-local autonomous contract and treat it as stronger than generic fallback behavior.",
            "Follow the repo's own bounds, review gates, stop rules, and evidence requirements.",
        ]
    elif resolution.branch is AutonomyBranch.CRON:
        body = [
            "This is an unattended scheduled run.",
            "Do not ask the user questions.",
            "Act within the scheduled task's scope and stop if blocked or if evidence is insufficient.",
        ]
    elif resolution.branch is AutonomyBranch.CURRENT_TASK:
        body = [
            "Continue the already-scoped current task autonomously.",
            "Do not silently broaden scope or switch into repo-queue triage.",
            "Ask only if blocked by a real choice that changes the agreed work.",
        ]
    elif resolution.branch is AutonomyBranch.RESEARCH:
        body = [
            "Use research-mode autonomy.",
            "Gather evidence, compare options, and keep uncertainty explicit.",
            "Stop when evidence plateaus or when you can produce a decision artifact.",
        ]
    elif resolution.branch is AutonomyBranch.GENERIC:
        body = [
            "Use bounded generic autonomy.",
            "Act without routine approval, require evidence, and stop on low confidence.",
        ]
    else:
        body = [
            "The request to run autonomously is under-specified in this context.",
            "Ask one clarifying question focused on scope instead of guessing.",
        ]

    return "\n".join([*header, *body, "</autonomy-contract>"])
