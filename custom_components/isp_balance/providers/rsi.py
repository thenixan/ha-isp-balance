"""RSI-Net provider — ООО «РамСвязьИнвест» subscriber cabinet.

Unlike NTS Center and Parus Telecom, lk.rsi-net.ru is not an LbWeb portal: it
is a Joomla! 3 site using com_users form authentication. Three consequences
shape this implementation:

- The CSRF field's *name* is a random 32-hex string regenerated on every page
  load (its value is always "1"), so the whole hidden-input set must be
  scraped from the login form rather than hardcoded.
- Joomla answers both successful and failed logins with a 303, so the POST
  status says nothing about whether the credentials were accepted. We confirm
  by requesting the cabinet and checking that we are not bounced back.
- Account data is a single two-column <th>/<td> table rather than the
  purpose-built markup LbWeb emits, so it is read by row label rather than by
  a CSS path.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag

from .base import AuthenticationError, AuthResult, BalanceData, ISPProvider
from .common import (
    USER_AGENT,
    build_cookie_header,
    clean_text,
    new_session,
    parse_balance,
)

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Endpoint configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RsiEndpoints:
    """URLs for a Joomla-based RSI subscriber cabinet."""

    login_page: str
    """Page hosting the login form — also where logged-out users land."""

    login_post: str
    """com_users login task endpoint."""

    cabinet: str
    """Authenticated page carrying the balance."""


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

# The balance is labelled in Russian; the portal has used more than one
# wording for it, so match the family rather than one exact string.
# Deliberately excludes "лицевой счёт" — that labels the account *number*,
# and matching it would report a 10-digit account id as a currency value.
_BALANCE_LABEL_RE = re.compile(
    r"баланс|состояние\s+сч[ёе]та|на\s+сч[ёе]те",
    re.IGNORECASE,
)


_LOGIN_FORM_SELECTOR = 'form[action*="task=user.login"]'

# Row labels in the cabinet's info table, matched after normalization
# (lowercased, ё→е, trailing colon stripped).
_LABEL_BALANCE = re.compile(r"^баланс$")

# Non-personal rows worth surfacing as sensor attributes. The portal ships a
# typo in the charge-date label ("следующго"), so match the stem loosely
# rather than depending on it staying misspelled.
_EXTRA_LABELS: dict[str, re.Pattern[str]] = {
    "login": re.compile(r"^логин$"),
    "blocking": re.compile(r"^блокировка$"),
    "tariff": re.compile(r"^тариф$"),
    "next_charge_date": re.compile(r"^дата следующ\w* списания$"),
    "total_cost": re.compile(r"^общая стоимость$"),
}


def _lookup(rows: dict[str, str], pattern: re.Pattern[str]) -> str | None:
    """Return the value of the first row whose label matches `pattern`."""
    for label, value in rows.items():
        if pattern.search(label):
            return value
    return None


def _first_money(text: str) -> float | None:
    """Return the first monetary amount in `text`, or None if there is none."""
    try:
        return parse_balance(text)
    except ValueError:
        return None


def _find_balance(soup: BeautifulSoup) -> float:
    """Locate the balance by anchoring on its label.

    For each occurrence of a balance label, the first monetary value that
    follows it wins — searching the remainder of the label's own text node
    first, then the label element's following siblings, then the enclosing
    element. This survives markup reshuffles that a CSS path would not.
    """
    for label in soup.find_all(string=_BALANCE_LABEL_RE):
        match = _BALANCE_LABEL_RE.search(label)
        if match is None:  # pragma: no cover — find_all already matched
            continue

        candidates: list[str] = [label[match.end() :]]

        element = label.parent
        if element is not None:
            candidates += [
                sibling.get_text() if isinstance(sibling, Tag) else str(sibling)
                for sibling in element.next_siblings
            ]
            if element.parent is not None:
                # Last resort: everything after the label within the row.
                candidates.append(
                    element.parent.get_text().split(match.group(), 1)[-1]
                )

        for candidate in candidates:
            value = _first_money(candidate.replace("\xa0", " "))
            if value is not None:
                return value

    raise ValueError("Balance not found in RSI cabinet page")


def _normalize_label(text: str) -> str:
    """Normalize a row label for matching: lowercase, ё→е, no trailing colon."""
    return " ".join(text.lower().replace("ё", "е").split()).rstrip(":")


def _read_info_table(soup: BeautifulSoup) -> dict[str, str]:
    """Map each row label of the cabinet's info table to its value.

    The cabinet renders everything as a single two-column table of
    <th>label</th><td>value</td> rows, with section captions occupying a
    full-width <th colspan="2"> and therefore no <td> — those are skipped.
    """
    rows: dict[str, str] = {}

    for row in soup.select("table tr"):
        header = row.find("th")
        value = row.find("td")
        if header is None or value is None:
            continue
        rows[_normalize_label(clean_text(header))] = clean_text(value)

    return rows


def _parse_cabinet(html: str) -> BalanceData:
    """Parse the authenticated cabinet page into structured data."""
    soup = BeautifulSoup(html, "html.parser")

    rows = _read_info_table(soup)

    raw_balance = _lookup(rows, _LABEL_BALANCE)
    if raw_balance is not None:
        balance = parse_balance(raw_balance)
    else:
        # Table layout changed — fall back to scanning for the label in prose.
        balance = _find_balance(soup)

    # Everything the portal publishes that is useful and non-personal. The
    # info table also carries the subscriber's name, address and phone; those
    # are deliberately not exposed, since attributes are persisted by the
    # recorder and shown in the UI.
    extra: dict[str, str] = {}
    for key, pattern in _EXTRA_LABELS.items():
        value = _lookup(rows, pattern)
        if value:
            extra[key] = value

    # The operator name is published in the page metadata, which is stable
    # across the cabinet's views.
    operator: str | None = None
    rights = soup.select_one('meta[name="rights"]')
    if rights is not None:
        operator = rights.get("content") or None

    # Joomla renders portal messages into a fixed container; it is present but
    # empty when there is nothing to show.
    notification: str | None = None
    container = soup.select_one("#system-message-container")
    if container is not None:
        notification = clean_text(container) or None

    return BalanceData(
        balance=balance,
        currency="RUB",
        # The cabinet does not expose an overdraft / credit limit on this
        # page — it lives behind the separate "Доверительный платёж" view.
        overdraft=None,
        operator=operator,
        notification=notification,
        extra=extra,
    )


# ---------------------------------------------------------------------------
# Provider implementation
# ---------------------------------------------------------------------------


class RsiProvider(ISPProvider):
    """Provider for the Joomla-based RSI-Net subscriber cabinet."""

    def __init__(self, endpoints: RsiEndpoints) -> None:
        self._endpoints = endpoints

    async def authenticate(
        self,
        username: str,
        password: str,
    ) -> AuthResult:
        headers = {"User-Agent": USER_AGENT}

        async with new_session() as session:
            # Step 1: GET the login page — collect the session cookie and the
            # hidden fields (per-request CSRF token name plus `return`).
            async with session.get(
                self._endpoints.login_page, headers=headers, allow_redirects=False
            ) as resp:
                if resp.status >= 400:
                    raise ConnectionError(f"ISP portal returned HTTP {resp.status}")

                cookies = {c.key: c.value for c in resp.cookies.values()}
                hidden = _extract_hidden_fields(await resp.text())

            # Step 2: POST the credentials alongside the scraped hidden fields.
            form_data = {
                **hidden,
                "username": username,
                "password": password,
            }

            async with session.post(
                self._endpoints.login_post,
                data=form_data,
                headers={**headers, "Cookie": build_cookie_header(cookies)},
                allow_redirects=False,
            ) as resp:
                if resp.status >= 400:
                    raise ConnectionError(f"Login returned HTTP {resp.status}")

                # Joomla regenerates the session id on a successful login.
                for cookie in resp.cookies.values():
                    cookies[cookie.key] = cookie.value

            # Step 3: Joomla 303s on both success and failure, so the only
            # reliable signal is whether the cabinet is now reachable.
            async with session.get(
                self._endpoints.cabinet,
                headers={**headers, "Cookie": build_cookie_header(cookies)},
                allow_redirects=False,
            ) as resp:
                if 300 <= resp.status < 400:
                    raise AuthenticationError("Invalid credentials")
                if resp.status >= 400:
                    raise ConnectionError(f"Cabinet returned HTTP {resp.status}")

        return AuthResult(
            auth_token=json.dumps(cookies, separators=(",", ":")),
            account_name=username,
        )

    async def fetch_balance(
        self,
        auth_token: str,
    ) -> BalanceData:
        cookies: dict[str, str] = json.loads(auth_token)
        headers = {
            "User-Agent": USER_AGENT,
            "Cookie": build_cookie_header(cookies),
        }

        async with new_session() as session:
            async with session.get(
                self._endpoints.cabinet, headers=headers, allow_redirects=False
            ) as resp:
                # A logged-out request for the cabinet is bounced to the
                # login page, which is how an expired session surfaces.
                if 300 <= resp.status < 400:
                    raise AuthenticationError("Session expired")

                if resp.status >= 400:
                    raise ConnectionError(f"Cabinet returned HTTP {resp.status}")

                html = await resp.text()

        # Joomla can also serve the login form with a 200 if the menu item is
        # public but its content is not.
        if _contains_login_form(html):
            raise AuthenticationError("Session expired")

        return _parse_cabinet(html)


def _extract_hidden_fields(html: str) -> dict[str, str]:
    """Collect the login form's hidden inputs (CSRF token and `return`)."""
    soup = BeautifulSoup(html, "html.parser")

    form = soup.select_one(_LOGIN_FORM_SELECTOR)
    if form is None:
        raise ConnectionError("Login form not found on RSI cabinet page")

    fields: dict[str, str] = {}
    for field in form.find_all("input", attrs={"type": "hidden"}):
        name = field.get("name")
        if name:
            fields[name] = field.get("value", "")

    return fields


def _contains_login_form(html: str) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    return soup.select_one(_LOGIN_FORM_SELECTOR) is not None
