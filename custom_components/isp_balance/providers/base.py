"""Base provider interface for ISP balance fetching."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import aiohttp


class AuthenticationError(Exception):
    """Raised when authentication fails or a session expires."""


@dataclass
class AuthResult:
    """Result of a successful authentication."""

    auth_token: str
    """Opaque reusable credential (cookie, bearer token, session ID)."""

    account_name: str
    """Human-readable account label for the config entry title."""

    extra: dict[str, Any] = field(default_factory=dict)
    """Provider-specific metadata to persist alongside the token."""


@dataclass
class BalanceData:
    """Fetched balance information."""

    balance: float
    """Current account balance."""

    currency: str
    """ISO 4217 currency code, e.g. 'USD', 'UAH'."""

    account_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)
    """Additional scraped data (plan name, due date, etc.)."""


class ISPProvider(ABC):
    """Abstract base class for ISP balance providers."""

    @staticmethod
    @abstractmethod
    def provider_id() -> str:
        """Unique slug identifying this provider, e.g. 'example_isp'."""

    @staticmethod
    @abstractmethod
    def provider_name() -> str:
        """Human-readable name shown in the config flow dropdown."""

    @abstractmethod
    async def authenticate(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
    ) -> AuthResult:
        """Authenticate against the ISP portal.

        Returns an AuthResult with a reusable credential.

        Raises:
            AuthenticationError: If credentials are invalid.
            ConnectionError: If the ISP portal is unreachable.
        """

    @abstractmethod
    async def fetch_balance(
        self,
        session: aiohttp.ClientSession,
        auth_token: str,
    ) -> BalanceData:
        """Fetch current balance using a previously obtained auth_token.

        Raises:
            AuthenticationError: If the token has expired.
        """
