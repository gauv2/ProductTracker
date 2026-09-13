from __future__ import annotations

from ..config import Config
from ..vault.models import utc_now_iso
from . import google, tweakers

__all__ = ["google", "tweakers", "refresh_new_price"]


def refresh_new_price(product_name: str, config: Config) -> dict:
    """Best-effort "new price" lookup job for one product.

    Tries Tweakers first (more likely to be the correct EU/NL retail price
    when it works at all), falls back to Google. Returns the ``new_price``
    frontmatter shape from data-model.md; all fields are ``None`` if both
    sources come up empty — that's a valid, expected outcome, not an error.
    """
    result = tweakers.lookup_new_price(product_name, cookie=config.tweakers_cookie)
    source = "tweakers"

    if result is None:
        result = google.lookup_new_price(
            product_name, api_key=config.google_api_key, cse_id=config.google_cse_id
        )
        source = "google"

    if result is None:
        return {
            "price": None,
            "currency": "EUR",
            "source": None,
            "source_url": None,
            "fetched_at": utc_now_iso(),
        }

    return {
        "price": result.price,
        "currency": result.currency,
        "source": source,
        "source_url": result.source_url,
        "fetched_at": utc_now_iso(),
    }
