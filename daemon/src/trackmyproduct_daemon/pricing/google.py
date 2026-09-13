"""Google new-price lookup — via the official Custom Search JSON API.

Scraping google.com/search directly is against Google's ToS and is
aggressively blocked (captchas) even for occasional requests, so this uses
the legitimate **Google Programmable Search Engine** (Custom Search JSON
API) instead:

1. Create a Programmable Search Engine at
   https://programmablesearchengine.google.com/ (search the whole web).
   Copy its Search engine ID into ``google_cse_id``.
2. Create an API key with the "Custom Search API" enabled at
   https://console.cloud.google.com/apis/credentials, put it in
   ``google_api_key``.
3. Free tier is 100 queries/day — plenty for periodic "new price" refreshes
   but not for the marketplace scan cycle itself.

This is a heuristic, best-effort lookup: it searches for
``<product name> kopen`` / ``<product name> price`` and regexes a price out
of each result's title/snippet. It does not verify the result is actually
selling the exact product — treat the output as "roughly what this costs
new," not authoritative.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

API_URL = "https://www.googleapis.com/customsearch/v1"
_PRICE_RE = re.compile(r"[€$]\s?(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)")


@dataclass
class PriceResult:
    price: float
    currency: str
    source_url: str


def lookup_new_price(query: str, api_key: str, cse_id: str, timeout: float = 15.0) -> PriceResult | None:
    if not api_key or not cse_id:
        logger.warning(
            "google pricing lookup skipped: google_api_key / google_cse_id not configured"
        )
        return None

    try:
        response = httpx.get(
            API_URL,
            params={"key": api_key, "cx": cse_id, "q": f"{query} kopen prijs"},
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError):
        logger.warning("google pricing lookup failed for %r", query, exc_info=True)
        return None

    for item in data.get("items", []):
        haystack = f"{item.get('title', '')} {item.get('snippet', '')}"
        match = _PRICE_RE.search(haystack)
        if not match:
            continue
        cleaned = match.group(1).replace(".", "").replace(",", ".")
        try:
            price = float(cleaned)
        except ValueError:
            continue
        return PriceResult(price=price, currency="EUR", source_url=item.get("link", ""))

    return None
