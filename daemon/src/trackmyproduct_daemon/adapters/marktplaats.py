"""Marktplaats adapter — reference implementation.

Uses Marktplaats' own unofficial search JSON endpoint, the same one their
web frontend calls (``GET /lrp/api/search``). There is no official public
API for search; this endpoint is undocumented, unauthenticated, and can
change or disappear without notice. Verified manually against
``https://www.marktplaats.nl/lrp/api/search?query=...`` on 2026-09-13,
which returns:

```json
{"listings": [{
  "itemId": "m2441918539",
  "title": "...",
  "priceInfo": {"priceCents": 52000, "priceType": "MIN_BID" | "FIXED" | "SEE_DESCRIPTION" | ...},
  "location": {"cityName": "Rotterdam", "distanceMeters": -1000, ...},
  "date": "Vandaag" | "Gisteren" | "13 sep '26" | ...,   # relative/partial Dutch string, not ISO
  "vipUrl": "/v/category/subcategory/m2441918539-slug"
}]}
```

Caveats (documented in ``/daemon/README.md`` too):
- ``priceInfo`` is absent or ``priceType`` is non-numeric (e.g. "Bieden" /
  "Zie omschrijving") for some ads; we surface ``price=None`` rather than
  guessing.
- ``location.distanceMeters`` is only meaningful when a ``postcode`` was
  supplied and is ``-1000`` (sentinel "unknown") otherwise.
- ``date`` is a relative/partial string, not a timestamp; we best-effort
  parse common Dutch formats and fall back to ``None`` (the store then uses
  ``seen_at`` for ordering).
- Passing ``postcode``/``distanceMeters``/``priceFrom``/``priceTo`` as query
  params did not visibly change results in manual testing, so we treat
  server-side filtering as unreliable and always re-filter client-side via
  :func:`apply_client_side_filters`.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

import httpx

from .base import AdapterError, Listing, SearchFilters, apply_client_side_filters

SEARCH_URL = "https://www.marktplaats.nl/lrp/api/search"
_UA = "Mozilla/5.0 (compatible; TrackMyProductDaemon/0.1; +local)"

_DUTCH_MONTHS = {
    "jan": 1, "feb": 2, "mrt": 3, "apr": 4, "mei": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "okt": 10, "nov": 11, "dec": 12,
}


def _parse_relative_date(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip().lower()
    now = datetime.now(timezone.utc)
    if raw == "vandaag":
        return now.strftime("%Y-%m-%dT00:00:00Z")
    if raw == "gisteren":
        return now.replace(day=now.day).strftime("%Y-%m-%dT00:00:00Z")
    match = re.match(r"(\d{1,2})\s+([a-z]{3})\s*'?(\d{2,4})", raw)
    if match:
        day, month_str, year = match.groups()
        month = _DUTCH_MONTHS.get(month_str)
        if month:
            year_int = int(year) if len(year) == 4 else 2000 + int(year)
            try:
                return datetime(year_int, month, int(day), tzinfo=timezone.utc).strftime(
                    "%Y-%m-%dT00:00:00Z"
                )
            except ValueError:
                return None
    return None


class MarktplaatsAdapter:
    name = "marktplaats"

    def __init__(self, base_url: str = "https://www.marktplaats.nl", timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def search(self, query: str, filters: SearchFilters) -> list[Listing]:
        params: dict[str, str | int] = {"query": query, "limit": 100}
        if filters.mp_postcode:
            params["postcode"] = filters.mp_postcode
        if filters.mp_distance_km is not None:
            params["distanceMeters"] = int(filters.mp_distance_km * 1000)
        if filters.min_price is not None:
            params["priceFrom"] = int(filters.min_price * 100)
        if filters.max_price is not None:
            params["priceTo"] = int(filters.max_price * 100)

        try:
            response = httpx.get(
                f"{self.base_url}/lrp/api/search",
                params=params,
                headers={"User-Agent": _UA},
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AdapterError(f"marktplaats search failed: {exc}") from exc

        listings = [self._to_listing(raw) for raw in data.get("listings", [])]
        return apply_client_side_filters(listings, filters)

    def _to_listing(self, raw: dict) -> Listing:
        price_info = raw.get("priceInfo") or {}
        price_cents = price_info.get("priceCents")
        price = price_cents / 100 if isinstance(price_cents, (int, float)) else None

        location = raw.get("location") or {}
        distance_m = location.get("distanceMeters")
        distance_km = distance_m / 1000 if isinstance(distance_m, (int, float)) and distance_m >= 0 else None

        vip_url = raw.get("vipUrl") or ""
        url = vip_url if vip_url.startswith("http") else f"{self.base_url}{vip_url}"

        return Listing(
            platform=self.name,
            title=raw.get("title", ""),
            price=price,
            currency="EUR",
            location=location.get("cityName", ""),
            distance_km=distance_km,
            posted_at=_parse_relative_date(raw.get("date")),
            url=url,
        )
