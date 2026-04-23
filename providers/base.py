"""Provider profile base class.

A ProviderProfile declares everything about an inference provider in one place:
auth, endpoints, client quirks, request-time quirks. The transport reads this
instead of receiving 20+ boolean flags.

Provider profiles are DECLARATIVE — they describe the provider's behavior.
They do NOT own client construction, credential rotation, or streaming.
Those stay on AIAgent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# Sentinel for "omit temperature entirely" (Kimi: server manages it)
OMIT_TEMPERATURE = object()


@dataclass
class ProviderProfile:
    """Base provider profile — subclass or instantiate with overrides."""

    # ── Identity ─────────────────────────────────────────────
    name: str
    api_mode: str = "chat_completions"
    aliases: tuple = ()

    # ── Auth ─────────────────────────────────────────────────
    env_vars: tuple = ()
    base_url: str = ""
    auth_type: str = "api_key"  # api_key | oauth_device_code | oauth_external | copilot | aws

    # ── Client-level quirks (set once at client construction) ─
    default_headers: Dict[str, str] = field(default_factory=dict)

    # ── Request-level quirks ─────────────────────────────────
    # Temperature: None = use caller's default, OMIT_TEMPERATURE = don't send
    fixed_temperature: Any = None
    default_max_tokens: Optional[int] = None

    # ── Hooks (override in subclass for complex providers) ───

    def prepare_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Provider-specific message preprocessing.

        Called AFTER codex field sanitization, BEFORE developer role swap.
        Default: pass-through.
        """
        return messages

    def build_extra_body(self, *, session_id: str = None, **context) -> Dict[str, Any]:
        """Provider-specific extra_body fields.

        Merged into the API kwargs extra_body. Default: empty dict.
        """
        return {}

    def build_api_kwargs_extras(self, *, reasoning_config: dict = None,
                                 **context) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Provider-specific kwargs that go to BOTH extra_body and top-level api_kwargs.

        Returns (extra_body_additions, top_level_kwargs).
        The transport merges extra_body_additions into extra_body, and
        top_level_kwargs directly into api_kwargs.

        This split exists because some providers put reasoning config in
        extra_body (OpenRouter: extra_body.reasoning) while others put it
        as top-level api_kwargs (Kimi: api_kwargs.reasoning_effort).

        Default: ({}, {}).
        """
        return {}, {}
