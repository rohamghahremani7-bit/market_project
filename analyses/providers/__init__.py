"""AI provider factory.

Keep provider selection in this package so services can use a stable
`get_provider()` import regardless of the configured backend.
"""
from django.conf import settings

from .base import AIProviderError


def get_provider(name: str | None = None):
    """Return the configured AI provider implementation."""
    provider_name = (name or settings.AI_PROVIDER or "openai").strip().lower()
    if provider_name == "openai":
        from .openai_provider import OpenAIProvider

        return OpenAIProvider()
    raise AIProviderError(
        f"ارائه‌دهنده {provider_name} در این نسخه پیکربندی نشده است."
    )


__all__ = ["AIProviderError", "get_provider"]
