"""Provider registry for ISP balance providers."""

from __future__ import annotations

from .base import ISPProvider
from .example_isp import ExampleISPProvider

PROVIDER_REGISTRY: dict[str, type[ISPProvider]] = {}


def register_provider(cls: type[ISPProvider]) -> type[ISPProvider]:
    """Register a provider class in the registry."""
    PROVIDER_REGISTRY[cls.provider_id()] = cls
    return cls


def get_provider(provider_id: str) -> ISPProvider:
    """Instantiate a provider by its ID."""
    return PROVIDER_REGISTRY[provider_id]()


def get_provider_choices() -> dict[str, str]:
    """Return {provider_id: display_name} for the config flow selector."""
    return {pid: cls.provider_name() for pid, cls in PROVIDER_REGISTRY.items()}


# Register bundled providers
register_provider(ExampleISPProvider)
