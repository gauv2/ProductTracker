"""Derive the price-history chart's points from listings[] at read time.

Per data-model.md: "The chart ... is derived, not stored" — grouped by day
(or week for long ranges), computed here rather than maintained as a
parallel stored history.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

_PERIOD_DAYS = {"1m": 30, "3m": 90, "6m": 180, "year": 365, "all": None}


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def compute_price_history(listings: list[dict], period: str = "all") -> list[dict]:
    if period not in _PERIOD_DAYS:
        period = "all"
    days = _PERIOD_DAYS[period]
    cutoff = datetime.now(timezone.utc) - timedelta(days=days) if days else None

    buckets: dict[str, list[float]] = {}
    for listing in listings:
        price = listing.get("price")
        if not isinstance(price, (int, float)):
            continue
        when = _parse_dt(listing.get("posted_at")) or _parse_dt(listing.get("seen_at"))
        if when is None:
            continue
        if cutoff and when < cutoff:
            continue
        bucket_key = when.strftime("%Y-%m-%d") if days is None or days <= 180 else when.strftime("%Y-W%W")
        buckets.setdefault(bucket_key, []).append(float(price))

    points = []
    for date in sorted(buckets):
        prices = buckets[date]
        points.append(
            {
                "date": date,
                "min": min(prices),
                "avg": round(sum(prices) / len(prices), 2),
            }
        )
    return points
