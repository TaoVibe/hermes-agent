"""DeepSeek provider profile."""

from providers.base import ProviderProfile
from providers import register_provider

deepseek = ProviderProfile(
    name="deepseek",
    aliases=("deepseek-chat",),
    env_vars=("DEEPSEEK_API_KEY",),
    base_url="https://api.deepseek.com/v1",
)

register_provider(deepseek)
