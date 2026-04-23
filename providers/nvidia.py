"""NVIDIA NIM provider profile."""

from providers.base import ProviderProfile
from providers import register_provider

nvidia = ProviderProfile(
    name="nvidia",
    aliases=("nvidia-nim",),
    env_vars=("NVIDIA_API_KEY",),
    base_url="https://integrate.api.nvidia.com/v1",
    default_max_tokens=16384,
)

register_provider(nvidia)
