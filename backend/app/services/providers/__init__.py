"""Providers package for virtual assistant chat generation."""

import os
from app.services.providers.base import BaseProvider
from app.services.providers.config import ProviderConfig, read_provider_config
from app.services.providers.gemini_provider import GeminiProvider
from app.services.providers.groq_provider import GroqProvider
from app.services.providers.provider_service import (
    ProviderService,
    build_provider_service,
    is_fallback_eligible,
)

_global_provider_service: ProviderService | None = None


def get_provider_service(force_reload: bool = False) -> ProviderService:
    """Return globally cached ProviderService instance or build from environment."""
    global _global_provider_service
    if _global_provider_service is None or force_reload:
        cfg = read_provider_config(os.environ, check_credentials=False)
        _global_provider_service = build_provider_service(cfg)
    return _global_provider_service


def set_provider_service(service: ProviderService | None) -> None:
    """Explicitly set or reset the global ProviderService instance (useful for tests)."""
    global _global_provider_service
    _global_provider_service = service


__all__ = [
    "BaseProvider",
    "GeminiProvider",
    "GroqProvider",
    "ProviderConfig",
    "ProviderService",
    "build_provider_service",
    "get_provider_service",
    "set_provider_service",
    "is_fallback_eligible",
    "read_provider_config",
]
