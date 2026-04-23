"""OpenRouter provider profile."""

from typing import Any, Dict, Tuple

from providers.base import ProviderProfile
from providers import register_provider


class OpenRouterProfile(ProviderProfile):
    """OpenRouter — provider preferences, full reasoning config passthrough."""

    def build_extra_body(self, *, session_id: str = None, **context) -> Dict[str, Any]:
        body = {}
        prefs = context.get("provider_preferences")
        if prefs:
            body["provider"] = prefs
        return body

    def build_api_kwargs_extras(self, *, reasoning_config: dict = None,
                                 supports_reasoning: bool = False,
                                 **context) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """OpenRouter passes the FULL reasoning_config dict as extra_body.reasoning."""
        extra_body = {}
        if supports_reasoning:
            if reasoning_config is not None:
                extra_body["reasoning"] = dict(reasoning_config)
            else:
                extra_body["reasoning"] = {"enabled": True, "effort": "medium"}
        return extra_body, {}


openrouter = OpenRouterProfile(
    name="openrouter",
    aliases=("or",),
    env_vars=("OPENROUTER_API_KEY",),
    base_url="https://openrouter.ai/api/v1",
)

register_provider(openrouter)
