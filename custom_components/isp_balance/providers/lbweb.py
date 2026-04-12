"""LbWeb billing system provider — shared by NTS Center and Parus Telecom."""

from __future__ import annotations

import json
import logging
from urllib.parse import unquote

import aiohttp
from bs4 import BeautifulSoup

from .base import AuthenticationError, AuthResult, BalanceData, ISPProvider

_LOGGER = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
)

# CSS selectors for the LbWeb account/index dashboard page
BALANCE_SELECTOR = (
    "#wrap-all > section > div.main > div > div > div.content-panel > div > div "
    "> div.content-panel > div > div:nth-child(2) "
    "> div.panel-form-item.panel-form-item-balance > div > div > span"
)
OVERDRAFT_SELECTOR = (
    "#wrap-all > section > div.main > div > div > div.content-panel > div > div "
    "> div.content-panel > div > div:nth-child(3) "
    "> div.panel-form-item.panel-form-item-value > span"
)
OPERATOR_SELECTOR = (
    "#wrap-all > section > div.main > div > div > div.content-panel > div > div "
    "> div.content-panel > div > div:nth-child(4) "
    "> div.panel-form-item.panel-form-item-value > span"
)
NOTIFICATION_SELECTOR = (
    "#wrap-all > section > div.main > div > div.row "
    "> div.alert.alert-block.alert-info"
)


def _clean_text(html_text: str) -> str:
    """Clean scraped text: normalize whitespace and non-breaking spaces."""
    return html_text.replace("\xa0", " ").replace("  ", " ").strip()


class LbWebProvider(ISPProvider):
    """Base provider for ISP portals running the LbWeb billing system.

    Subclass and override provider_id(), provider_name(), and set
    SIGN_IN_URL / DASHBOARD_URL to create a concrete provider.
    """

    SIGN_IN_URL: str
    DASHBOARD_URL: str

    async def authenticate(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
    ) -> AuthResult:
        headers = {"User-Agent": USER_AGENT}

        # Step 1: GET the login page to obtain CSRF token and initial cookies
        async with session.get(
            self.SIGN_IN_URL, headers=headers, allow_redirects=False
        ) as resp:
            if resp.status >= 400:
                raise ConnectionError(f"ISP portal returned {resp.status}")

            cookies: dict[str, str] = {}
            csrf_token = None
            for cookie in resp.cookies.values():
                cookies[cookie.key] = cookie.value
                if cookie.key == "YII_CSRF_TOKEN":
                    csrf_token = unquote(cookie.value)

        # Step 2: POST login form with credentials and CSRF token
        form_data = {
            "LoginForm[login]": username,
            "LoginForm[password]": password,
            "yt0": "Войти",
        }
        if csrf_token:
            form_data["YII_CSRF_TOKEN"] = csrf_token

        cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())

        async with session.post(
            self.SIGN_IN_URL,
            data=form_data,
            headers={**headers, "Cookie": cookie_header},
            allow_redirects=False,
        ) as resp:
            status = resp.status

            if 400 <= status < 500:
                raise AuthenticationError("Invalid credentials")

            # Collect cookies from the login response
            for cookie in resp.cookies.values():
                cookies[cookie.key] = cookie.value

        auth_token = json.dumps(cookies)

        return AuthResult(
            auth_token=auth_token,
            account_name=username,
        )

    async def fetch_balance(
        self,
        session: aiohttp.ClientSession,
        auth_token: str,
    ) -> BalanceData:
        cookies: dict[str, str] = json.loads(auth_token)
        cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())

        headers = {"User-Agent": USER_AGENT, "Cookie": cookie_header}

        async with session.get(
            self.DASHBOARD_URL, headers=headers, allow_redirects=False
        ) as resp:
            # Redirect to login page means session expired
            if resp.status in range(300, 400):
                location = resp.headers.get("Location", "")
                if "site/login" in location:
                    raise AuthenticationError("Session expired")
                raise ConnectionError(f"Unexpected redirect to {location}")

            if resp.status >= 400:
                raise ConnectionError(f"Dashboard returned {resp.status}")

            html = await resp.text()

        soup = BeautifulSoup(html, "html.parser")

        # Parse balance
        balance_el = soup.select_one(BALANCE_SELECTOR)
        balance = _clean_text(balance_el.get_text()) if balance_el else "unknown"

        # Parse extra fields
        extra: dict[str, str] = {}

        overdraft_el = soup.select_one(OVERDRAFT_SELECTOR)
        if overdraft_el:
            extra["overdraft"] = _clean_text(overdraft_el.get_text())

        operator_el = soup.select_one(OPERATOR_SELECTOR)
        if operator_el:
            extra["operator"] = _clean_text(operator_el.get_text())

        notification_el = soup.select_one(NOTIFICATION_SELECTOR)
        if notification_el:
            # Extract only direct text nodes (skip child elements)
            text_parts = [
                part.strip()
                for part in notification_el.find_all(string=True, recursive=False)
                if part.strip()
            ]
            if text_parts:
                extra["notification"] = " ".join(text_parts)

        return BalanceData(
            balance=balance,
            currency="RUB",
            extra=extra,
        )
