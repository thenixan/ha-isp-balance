"""LbWeb billing system provider — shared by NTS Center and Parus Telecom.

LbWeb is a YII-based ISP billing portal. Authentication uses CSRF-protected
form login; account data is scraped from the dashboard HTML page.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from urllib.parse import unquote

import aiohttp
from bs4 import BeautifulSoup, Tag

from .base import AuthenticationError, AuthResult, BalanceData, ISPProvider

_LOGGER = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
)


# ---------------------------------------------------------------------------
# LbWeb endpoint configuration (product type — varies per ISP)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LbWebEndpoints:
    """URLs for a specific LbWeb billing portal instance."""

    sign_in: str
    dashboard: str


# ---------------------------------------------------------------------------
# LbWeb dashboard CSS selectors (shared across all LbWeb instances)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LbWebSelectors:
    """CSS selectors for the LbWeb account/index dashboard page."""

    balance: str
    overdraft: str
    operator: str
    notification: str


SELECTORS = LbWebSelectors(
    balance=(
        "#wrap-all > section > div.main > div > div > div.content-panel > div > div "
        "> div.content-panel > div > div:nth-child(2) "
        "> div.panel-form-item.panel-form-item-balance > div > div > span"
    ),
    overdraft=(
        "#wrap-all > section > div.main > div > div > div.content-panel > div > div "
        "> div.content-panel > div > div:nth-child(3) "
        "> div.panel-form-item.panel-form-item-value > span"
    ),
    operator=(
        "#wrap-all > section > div.main > div > div > div.content-panel > div > div "
        "> div.content-panel > div > div:nth-child(4) "
        "> div.panel-form-item.panel-form-item-value > span"
    ),
    notification=(
        "#wrap-all > section > div.main > div > div.row "
        "> div.alert.alert-block.alert-info"
    ),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clean_text(el: Tag) -> str:
    """Extract text from a BS4 element, normalizing whitespace."""
    return el.get_text().replace("\xa0", " ").replace("  ", " ").strip()


def _extract_direct_text(el: Tag) -> str | None:
    """Extract only direct text nodes from an element (skip child tags)."""
    parts = [
        part.strip()
        for part in el.find_all(string=True, recursive=False)
        if part.strip()
    ]
    return " ".join(parts) if parts else None


_BALANCE_RE = re.compile(r"[^\d.,\-]")


def _parse_balance(raw: str) -> float:
    """Parse a locale-formatted balance string into a float.

    Handles formats like '1 234.56 руб.', '1234,56', '-100.00'.
    """
    cleaned = _BALANCE_RE.sub("", raw)
    # Normalize comma-as-decimal-separator (European/Russian locale)
    cleaned = cleaned.replace(",", ".")
    return float(cleaned)


def _build_cookie_header(cookies: dict[str, str]) -> str:
    return "; ".join(f"{k}={v}" for k, v in cookies.items())


# ---------------------------------------------------------------------------
# Provider implementation
# ---------------------------------------------------------------------------


class LbWebProvider(ISPProvider):
    """Provider for ISP portals running the LbWeb billing system.

    Instantiated with endpoint URLs for a specific ISP. All LbWeb
    instances share the same authentication flow and page structure.
    """

    def __init__(self, endpoints: LbWebEndpoints) -> None:
        self._endpoints = endpoints

    async def authenticate(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
    ) -> AuthResult:
        headers = {"User-Agent": USER_AGENT}

        # Step 1: GET login page — obtain CSRF token and initial cookies.
        async with session.get(
            self._endpoints.sign_in, headers=headers, allow_redirects=False
        ) as resp:
            if resp.status >= 400:
                raise ConnectionError(
                    f"ISP portal returned HTTP {resp.status}"
                )

            cookies: dict[str, str] = {}
            csrf_token: str | None = None

            for cookie in resp.cookies.values():
                cookies[cookie.key] = cookie.value
                if cookie.key == "YII_CSRF_TOKEN":
                    csrf_token = unquote(cookie.value)

        # Step 2: POST login form with credentials and decoded CSRF token.
        form_data: dict[str, str] = {
            "LoginForm[login]": username,
            "LoginForm[password]": password,
            "yt0": "Войти",
        }
        if csrf_token is not None:
            form_data["YII_CSRF_TOKEN"] = csrf_token

        async with session.post(
            self._endpoints.sign_in,
            data=form_data,
            headers={**headers, "Cookie": _build_cookie_header(cookies)},
            allow_redirects=False,
        ) as resp:
            if 400 <= resp.status < 500:
                raise AuthenticationError("Invalid credentials")

            for cookie in resp.cookies.values():
                cookies[cookie.key] = cookie.value

        return AuthResult(
            auth_token=json.dumps(cookies, separators=(",", ":")),
            account_name=username,
        )

    async def fetch_balance(
        self,
        session: aiohttp.ClientSession,
        auth_token: str,
    ) -> BalanceData:
        cookies: dict[str, str] = json.loads(auth_token)
        headers = {
            "User-Agent": USER_AGENT,
            "Cookie": _build_cookie_header(cookies),
        }

        async with session.get(
            self._endpoints.dashboard, headers=headers, allow_redirects=False
        ) as resp:
            if 300 <= resp.status < 400:
                location = resp.headers.get("Location", "")
                if "site/login" in location:
                    raise AuthenticationError("Session expired")
                raise ConnectionError(f"Unexpected redirect to {location}")

            if resp.status >= 400:
                raise ConnectionError(
                    f"Dashboard returned HTTP {resp.status}"
                )

            html = await resp.text()

        return self._parse_dashboard(html)

    @staticmethod
    def _parse_dashboard(html: str) -> BalanceData:
        """Parse the LbWeb account/index page into structured data."""
        soup = BeautifulSoup(html, "html.parser")

        balance_el = soup.select_one(SELECTORS.balance)
        if balance_el is None:
            raise ValueError("Balance element not found on dashboard page")

        raw_balance = _clean_text(balance_el)
        balance = _parse_balance(raw_balance)

        overdraft_el = soup.select_one(SELECTORS.overdraft)
        operator_el = soup.select_one(SELECTORS.operator)
        notification_el = soup.select_one(SELECTORS.notification)

        return BalanceData(
            balance=balance,
            currency="RUB",
            overdraft=_clean_text(overdraft_el) if overdraft_el else None,
            operator=_clean_text(operator_el) if operator_el else None,
            notification=(
                _extract_direct_text(notification_el)
                if notification_el
                else None
            ),
        )
