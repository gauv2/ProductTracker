"""Common adapter interface: ``search(query, filters) -> Listing[]``.

Every platform adapter implements :class:`PlatformAdapter`. Adapters raise
:class:`AdapterError` for a *complete* failure of that platform (network
down, auth rejected, markup changed) — callers (the scan cycle) are
expected to catch it per-adapter so one platform's outage never blocks the
others, per docs/api-contract.md's "Platform adapters" section.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol


@dataclass
class SearchFilters:
    title_includes: list[str] = field(default_factory=list)
    exclude_words: list[str] = field(default_factory=list)
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    mp_distance_km: Optional[float] = None
    mp_postcode: Optional[str] = None


@dataclass
class Listing:
    platform: str
    title: str
    price: Optional[float]
    currency: str
    location: str
    distance_km: Optional[float]
    posted_at: Optional[str]
    url: str

    def as_dict(self) -> dict:
        return {
            "platform": self.platform,
            "title": self.title,
            "price": self.price,
            "currency": self.currency,
            "location": self.location,
            "distance_km": self.distance_km,
            "posted_at": self.posted_at,
            "url": self.url,
        }


class AdapterError(Exception):
    """Raised when a platform adapter fails outright for this search."""


class PlatformAdapter(Protocol):
    name: str

    def search(self, query: str, filters: SearchFilters) -> list[Listing]:
        ...


def apply_client_side_filters(listings: list[Listing], filters: SearchFilters) -> list[Listing]:
    """Re-apply title/price/distance filters locally.

    Adapters best-effort pass filters upstream (query params, API filter
    strings) but upstream support is inconsistent across platforms, so the
    scan cycle always re-filters client-side as the source of truth.
    """
    out = []
    for listing in listings:
        title_lower = listing.title.lower()
        if filters.title_includes and not all(
            term.lower() in title_lower for term in filters.title_includes
        ):
            continue
        if filters.exclude_words and any(
            word.lower() in title_lower for word in filters.exclude_words
        ):
            continue
        if filters.min_price is not None and listing.price is not None and listing.price < filters.min_price:
            continue
        if filters.max_price is not None and listing.price is not None and listing.price > filters.max_price:
            continue
        if (
            filters.mp_distance_km is not None
            and listing.distance_km is not None
            and listing.distance_km > filters.mp_distance_km
        ):
            continue
        out.append(listing)
    return out
