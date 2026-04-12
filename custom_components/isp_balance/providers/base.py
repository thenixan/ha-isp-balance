"""Base provider interface and domain types for ISP balance fetching."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import aiohttp


class AuthenticationError(Exception):
    """Raised when authentication fails or a session expires."""


@dataclass(frozen=True, slots=True)
class AuthResult:
    """Result of a successful provider authentication."""

    auth_token: str
    """Opaque reusable credential (JSON-encoded cookies, bearer token, etc.)."""

    account_name: str
    """Human-readable account label for the config entry title."""


@dataclass(frozen=True, slots=True)
class BalanceData:
    """Fetched account data from the ISP billing portal."""

    balance: float
    """Current account balance as a numeric value."""

    currency: str
    """ISO 4217 currency code, e.g. 'RUB'."""

    overdraft: str | None = None
    """Credit limit / overdraft text, if available."""

    operator: str | None = None
    """Operator or company name, if available."""

    notification: str | None = None
    """Portal notification message, if any."""


class ISPProvider(ABC):
    """Abstract interface for ISP balance providers.

    Implementations handle authentication against a specific ISP billing
    portal and scraping of account data from the authenticated zone.
    """

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
