"""Plain-dict domain shapes mirroring docs/data-model.md frontmatter exactly.

We deliberately keep products as nested ``dict``/``list`` structures (not
pydantic models) at the vault layer, since that is what gets round-tripped
to/from YAML frontmatter verbatim. The API layer (schemas.py) defines the
typed request/response shapes.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_tmp_id() -> str:
    """Generate a stable 6-char product id, per data-model.md ('a1b2c3')."""
    return secrets.token_hex(3)


def listing_id_for(platform: str, url: str) -> str:
    """Deterministic listing id derived from (platform, url).

    Re-scans must resolve to the same id for the same (platform, url) pair
    so diffing is skip-if-exists rather than order-dependent, per
    data-model.md's invariant on ``listings[].id``.
    """
    digest = hashlib.sha1(f"{platform}:{url}".encode("utf-8")).hexdigest()
    return f"l-{digest[:8]}"


def empty_product(tmp_id: str, name: str, category: str = "") -> dict:
    now = utc_now_iso()
    return {
        "tmp_id": tmp_id,
        "tmp_type": "product",
        "name": name,
        "category": category,
        "created_at": now,
        "updated_at": now,
        "saved_searches": [],
        "listings": [],
        "stats": {
            "all_time_high": None,
            "all_time_low": None,
        },
        "new_price": {
            "price": None,
            "currency": "EUR",
            "source": None,
            "source_url": None,
            "fetched_at": None,
        },
        "notifications_sent": [],
    }


def empty_saved_search(sid: str, label: str, query: str, platforms: list[str]) -> dict:
    return {
        "id": sid,
        "label": label,
        "platforms": platforms,
        "query": query,
        "title_includes": [],
        "exclude_words": [],
        "min_price": None,
        "max_price": None,
        "mp_distance_km": None,
        "mp_postcode": None,
        "enabled": True,
        "last_scanned_at": None,
    }
