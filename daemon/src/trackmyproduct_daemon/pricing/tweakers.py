"""Tweakers Pricewatch new-price lookup — best-effort, fragile by design.

Confirmed by manual testing (2026-09-13) that anonymous requests to
``https://tweakers.net/pricewatch/zoeken/`` are 302-redirected to a DPG
Media consent/cookie wall (``myprivacy.dpgmedia.nl/consent``) before
reaching any pricing content — there is no way to get past this with a
plain HTTP request; it requires a browser to click through a cookie
consent flow once and persist the resulting cookies.

To make this work at all, set ``tweakers_cookie`` in the daemon config to
the ``Cookie`` header captured from a browser session that has already
clicked through the consent wall (DevTools → Network → any tweakers.net
request → copy the Cookie header). It WILL expire periodically. Without it,
this lookup always returns ``None`` — that is the documented, expected
behavior rather than a bug, per the task's "clearly documented if a source
can't be automated reliably."
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

SEARCH_URL = "https://tweakers.net/pricewatch/zoeken/"
_UA = "Mozilla/5.0 (compatible; TrackMyProductDaemon/0.1; +local)"
_PRICE_RE = re.compile(r"€\s?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)")


@dataclass
class PriceResult:
    price: float
    currency: str
    source_url: str


def lookup_new_price(query: str, cookie: str = "", timeout: float = 15.0) -> PriceResult | None:
    if not cookie:
        logger.warning(
            "tweakers pricing lookup skipped: no tweakers_cookie configured "
            "(the consent wall blocks anonymous requests, see module docstring)"
        )
        return None

    try:
        response = httpx.get(
            SEARCH_URL,
            params={"keyword": query},
            headers={"User-Agent": _UA, "Cookie": cookie},
            timeout=timeout,
            follow_redirects=True,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        logger.warning("tweakers pricing lookup failed for %r", query, exc_info=True)
        return None

    if "myprivacy.dpgmedia" in str(response.url):
        logger.warning("tweakers cookie expired or missing consent — hit the consent wall again")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    first_result = soup.select_one("a[href*='/pricewatch/']")
    if first_result is None:
        return None

    href = first_result.get("href", "")
    source_url = href if href.startswith("http") else f"https://tweakers.net{href}"

    price_match = _PRICE_RE.search(soup.get_text(" ", strip=True))
    if not price_match:
        return None

    cleaned = price_match.group(1).replace(".", "").replace(",", ".")
    try:
        price = float(cleaned)
    except ValueError:
        return None

    return PriceResult(price=price, currency="EUR", source_url=source_url)
