"""Facebook Marketplace adapter — best-effort, isolated by design.

**Read this before relying on it.** Facebook Marketplace has no public
search API, its search results are rendered client-side by JavaScript, and
anonymous (logged-out) requests are generally redirected to a login wall —
confirmed by manual testing against ``mbasic.facebook.com/marketplace``
during development (2026-09-13), which returned a login-required response
without an authenticated session cookie. There is no reliable way to query
it with plain HTTP requests.

This adapter therefore:

1. Only attempts anything if a logged-in session cookie is configured
   (``facebook_cookie`` in the daemon config — copy the ``cookie`` request
   header from a browser session logged into facebook.com; it will expire
   periodically and need refreshing by hand).
2. Scrapes the lightweight ``mbasic.facebook.com`` marketplace search HTML
   (no JS execution required) and extracts listing cards with best-effort
   regex/BeautifulSoup parsing. Facebook's markup changes without notice,
   so this WILL break silently from time to time — that's expected, not a
   bug to chase.
3. Never raises out of ``search()`` for a scrape/parse failure: it logs a
   warning and returns an empty list. The scan cycle in ``scan.py`` treats
   this platform as "isolated" on top of that — even an unexpected
   exception here is caught per-adapter so a Facebook outage/block never
   blocks Marktplaats or eBay scans, per docs/api-contract.md.

If you need Facebook Marketplace coverage more reliably than this, the
realistic options are a headless browser with a persistent logged-in
profile (out of scope for this daemon — heavy, and against Facebook's
ToS for automated access) or a paid third-party scraping API. Neither is
implemented here; ship what's honestly maintainable instead of a fragile
illusion of coverage.
"""

from __future__ import annotations

import logging
import re

import httpx
from bs4 import BeautifulSoup

from .base import Listing, SearchFilters, apply_client_side_filters

logger = logging.getLogger(__name__)

SEARCH_URL = "https://mbasic.facebook.com/marketplace/search/"
_UA = "Mozilla/5.0 (compatible; TrackMyProductDaemon/0.1; +local)"
_PRICE_RE = re.compile(r"([€$£]|EUR)\s?([\d.,]+)")


class FacebookAdapter:
    name = "facebook"

    def __init__(self, cookie: str = "", locale: str = "nl_NL", timeout: float = 15.0):
        self.cookie = cookie
        self.locale = locale
        self.timeout = timeout

    def search(self, query: str, filters: SearchFilters) -> list[Listing]:
        """Best-effort search. Never raises — returns [] on any failure."""
        if not self.cookie:
            logger.warning(
                "facebook adapter skipped: no facebook_cookie configured "
                "(see README's Facebook Marketplace caveats)"
            )
            return []

        try:
            listings = self._scrape(query)
        except Exception:  # noqa: BLE001 - deliberately broad, see module docstring
            logger.warning("facebook adapter failed for query %r", query, exc_info=True)
            return []

        return apply_client_side_filters(listings, filters)

    def _scrape(self, query: str) -> list[Listing]:
        response = httpx.get(
            SEARCH_URL,
            params={"query": query, "locale": self.locale},
            headers={"User-Agent": _UA, "Cookie": self.cookie},
            timeout=self.timeout,
            follow_redirects=True,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        listings = []
        for anchor in soup.select("a[href*='/marketplace/item/']"):
            href = anchor.get("href", "")
            if not href:
                continue
            url = href if href.startswith("http") else f"https://www.facebook.com{href}"
            url = url.split("?", 1)[0]

            text = anchor.get_text(" ", strip=True)
            price_match = _PRICE_RE.search(text)
            price = None
            if price_match:
                cleaned = price_match.group(2).replace(".", "").replace(",", ".")
                try:
                    price = float(cleaned)
                except ValueError:
                    price = None

            title = text
            if price_match:
                title = text[: price_match.start()].strip() or text

            listings.append(
                Listing(
                    platform=self.name,
                    title=title,
                    price=price,
                    currency="EUR",
                    location="",
                    distance_km=None,
                    posted_at=None,
                    url=url,
                )
            )

        # De-dupe within a single scrape (the same card can appear twice in the markup).
        seen_urls = set()
        unique = []
        for listing in listings:
            if listing.url in seen_urls:
                continue
            seen_urls.add(listing.url)
            unique.append(listing)
        return unique
