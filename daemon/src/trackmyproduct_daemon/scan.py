"""Scan-cycle orchestration, per docs/api-contract.md's "Scan cycle" steps.

Kept separate from the adapters/store so the pure decision logic (what
counts as new, what counts as ATH/ATL, what should be notified) stays unit
testable without any network access; ``run_scan_cycle`` is the only piece
that actually calls out to adapters/Telegram/the filesystem.
"""

from __future__ import annotations

import logging
from typing import Iterable

from .adapters.base import AdapterError, Listing, PlatformAdapter, SearchFilters
from .notifications.base import Notification, NotificationChannel
from .vault import models
from .vault.store import VaultStore, dedupe_new_listings, recompute_stats, stats_changed

logger = logging.getLogger(__name__)


def already_notified(notifications_sent: list[dict], key: str) -> bool:
    return any(n.get("key") == key for n in notifications_sent)


def build_queued_notifications(
    product: dict,
    old_listings: list[dict],
    new_listings: list[dict],
    old_stats: dict,
    new_stats: dict,
) -> list[Notification]:
    """Decide which notifications this cycle's changes warrant.

    Steps 4-5 of the scan cycle: ATH/ATL changes and cross-platform-match
    (a platform appearing in ``listings[]`` for the first time). Dedup
    against ``notifications_sent`` happens here so a restart mid-cycle
    can't double-notify. ``old_listings`` is the product's listings *before*
    this cycle's ``new_listings`` were appended, so "first time seen on this
    platform" is judged against pre-scan state.
    """
    sent = product.get("notifications_sent", [])
    queued: list[Notification] = []
    name = product.get("name", product.get("tmp_id", "product"))

    changed = stats_changed(old_stats, new_stats)
    if changed["ath"] and new_stats.get("all_time_high"):
        ath = new_stats["all_time_high"]
        key = f"ath:{ath['listing_id']}"
        if not already_notified(sent, key):
            queued.append(
                Notification(
                    key=key,
                    text=f"📈 New all-time high for {name}: €{ath['price']:.2f}",
                )
            )
    if changed["atl"] and new_stats.get("all_time_low"):
        atl = new_stats["all_time_low"]
        key = f"atl:{atl['listing_id']}"
        if not already_notified(sent, key):
            queued.append(
                Notification(
                    key=key,
                    text=f"📉 New all-time low for {name}: €{atl['price']:.2f}",
                )
            )

    existing_platforms = {l["platform"] for l in old_listings}
    seen_new_platforms = set()
    for listing in new_listings:
        platform = listing["platform"]
        if platform in existing_platforms or platform in seen_new_platforms:
            continue
        seen_new_platforms.add(platform)
        date = listing.get("seen_at", "")[:10]
        key = f"cross-platform:{platform}:{date}"
        if not already_notified(sent, key):
            queued.append(
                Notification(
                    key=key,
                    text=f"🔀 {name} is now available on {platform} too.",
                )
            )

    return queued


def scan_saved_search(
    adapter: PlatformAdapter,
    query: str,
    filters: SearchFilters,
) -> list[Listing]:
    """Run one adapter for one saved search, isolating its failures.

    Returns [] (and logs) instead of raising, so a caller looping over
    multiple platforms never has one platform's failure abort the others —
    this is the isolation the task requires explicitly for Facebook, and
    applied uniformly to every adapter for the same reason.
    """
    try:
        return adapter.search(query, filters)
    except AdapterError:
        logger.warning("%s adapter failed for query %r", adapter.name, query, exc_info=True)
        return []
    except Exception:  # noqa: BLE001 - never let one adapter crash the scan cycle
        logger.exception("%s adapter raised unexpectedly for query %r", adapter.name, query)
        return []


def run_scan_cycle(
    store: VaultStore,
    adapters: dict[str, PlatformAdapter],
    channels: Iterable[NotificationChannel],
    saved_search_filter: tuple[str, str] | None = None,
) -> None:
    """Run enabled saved searches across all products.

    ``saved_search_filter``, if given, is ``(product_id, saved_search_id)``
    to scan just one saved search out-of-band (the
    ``POST /products/{id}/saved-searches/{sid}/scan`` route), otherwise
    every enabled saved search on every product is scanned.
    """
    for product in store.list_products():
        for saved_search in product.get("saved_searches", []):
            if not saved_search.get("enabled", True):
                continue
            if saved_search_filter and (
                product["tmp_id"] != saved_search_filter[0]
                or saved_search["id"] != saved_search_filter[1]
            ):
                continue
            _scan_one(store, product, saved_search, adapters, channels)


def _scan_one(
    store: VaultStore,
    product: dict,
    saved_search: dict,
    adapters: dict[str, PlatformAdapter],
    channels: Iterable[NotificationChannel],
) -> None:
    filters = SearchFilters(
        title_includes=saved_search.get("title_includes") or [],
        exclude_words=saved_search.get("exclude_words") or [],
        min_price=saved_search.get("min_price"),
        max_price=saved_search.get("max_price"),
        mp_distance_km=saved_search.get("mp_distance_km"),
        mp_postcode=saved_search.get("mp_postcode"),
    )

    all_raw: list[Listing] = []
    for platform in saved_search.get("platforms", []):
        adapter = adapters.get(platform)
        if adapter is None:
            logger.warning("no adapter registered for platform %r", platform)
            continue
        all_raw.extend(scan_saved_search(adapter, saved_search["query"], filters))

    now = models.utc_now_iso()
    candidates = []
    for listing in all_raw:
        d = listing.as_dict()
        d["saved_search_id"] = saved_search["id"]
        d["seen_at"] = now
        candidates.append(d)

    old_listings = list(product.get("listings", []))
    new_listings = dedupe_new_listings(old_listings, candidates)
    product["listings"] = old_listings + new_listings

    old_stats = product.get("stats", {"all_time_high": None, "all_time_low": None})
    new_stats = recompute_stats(product["listings"])
    product["stats"] = new_stats

    notifications = build_queued_notifications(product, old_listings, new_listings, old_stats, new_stats)
    for notification in notifications:
        for channel in channels:
            if channel.send(notification):
                product.setdefault("notifications_sent", []).append(
                    {"key": notification.key, "sent_at": models.utc_now_iso()}
                )
                break

    saved_search["last_scanned_at"] = now
    product["updated_at"] = now
    store.save(product)
