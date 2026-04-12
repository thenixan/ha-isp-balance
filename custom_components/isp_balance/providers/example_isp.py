"""Example ISP provider — demonstrates the scraping pattern."""

from __future__ import annotations

import aiohttp
from bs4 import BeautifulSoup

from .base import AuthenticationError, AuthResult, BalanceData, ISPProvider


class ExampleISPProvider(ISPProvider):
    """Skeleton provider for an example ISP portal."""

    LOGIN_URL = "https://portal.example-isp.com/login"
    BALANCE_URL = "https://portal.example-isp.com/account"

    @staticmethod
    def provider_id() -> str:
        return "example_isp"

    @staticmethod
    def provider_name() -> str:
        return "Example ISP"

    async def authenticate(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
    ) -> AuthResult:
        async with session.post(
            self.LOGIN_URL,
            data={"login": username, "password": password},
        ) as resp:
            if resp.status != 200:
                raise ConnectionError(f"ISP portal returned {resp.status}")

            cookie = resp.cookies.get("session_id")
            if not cookie:
                raise AuthenticationError("Login failed: no session cookie returned")

            return AuthResult(
                auth_token=cookie.value,
                account_name=username,
            )

    async def fetch_balance(
        self,
        session: aiohttp.ClientSession,
        auth_token: str,
    ) -> BalanceData:
        cookies = {"session_id": auth_token}
        async with session.get(self.BALANCE_URL, cookies=cookies) as resp:
            if resp.status == 401:
                raise AuthenticationError("Session expired")

            html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")

            balance_el = soup.select_one(".account-balance .amount")
            if balance_el is None:
                raise ValueError("Could not find balance element on page")

            balance = float(balance_el.text.strip().replace(",", ""))

            return BalanceData(balance=balance, currency="USD")
