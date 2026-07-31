"""HTTP and parsing helpers shared by all provider implementations."""

from __future__ import annotations

import re

import aiohttp
from bs4 import Tag

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
)


def new_session() -> aiohttp.ClientSession:
    """Create a private session with DummyCookieJar.

    HA's shared session uses a real CookieJar that intercepts Set-Cookie
    headers, causing resp.cookies to be empty. We need our own session
    to reliably extract cookies from responses.
    """
    return aiohttp.ClientSession(cookie_jar=aiohttp.DummyCookieJar())


def build_cookie_header(cookies: dict[str, str]) -> str:
    return "; ".join(f"{k}={v}" for k, v in cookies.items())


def clean_text(el: Tag) -> str:
    """Extract text from a BS4 element, normalizing whitespace."""
    return el.get_text().replace("\xa0", " ").replace("  ", " ").strip()


def extract_direct_text(el: Tag) -> str | None:
    """Extract only direct text nodes from an element (skip child tags)."""
    parts = [
        part.strip()
        for part in el.find_all(string=True, recursive=False)
        if part.strip()
    ]
    return " ".join(parts) if parts else None


# A monetary amount: optional sign, digits that may be grouped with plain,
# non-breaking or narrow no-break spaces, and an optional decimal part behind
# either a comma or a dot. Deliberately excludes newlines so a match cannot
# run across two cells.
MONEY_RE = re.compile("-?\\d[\\d \u00a0\u202f]*(?:[.,]\\d+)?")

_GROUPING_RE = re.compile("[ \u00a0\u202f]")


def parse_balance(raw: str) -> float:
    """Parse a locale-formatted balance string into a float.

    Handles formats like '1 234.56 руб.', '810,00 р.', '1234,56', '-100.00'.

    The amount is *extracted* rather than filtered out of the string: currency
    suffixes such as 'р.' and 'руб.' end in a period that would otherwise be
    mistaken for part of the number.
    """
    match = MONEY_RE.search(raw)
    if match is None:
        raise ValueError(f"No monetary amount found in {raw!r}")

    cleaned = _GROUPING_RE.sub("", match.group())
    # Normalize comma-as-decimal-separator (European/Russian locale)
    return float(cleaned.replace(",", "."))
