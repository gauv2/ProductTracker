"""CRUD over product notes in the vault, plus the pure diff/stats helpers
used by the scan cycle (kept side-effect-free so they're easy to unit test).
"""

from __future__ import annotations

import re
from pathlib import Path

from . import models
from .frontmatter import read_note, write_note


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower()
    return slug or "product"


class ProductNotFoundError(Exception):
    pass


class VaultStore:
    """File-backed CRUD for product notes under ``vault_dir``.

    One note per product, named ``<slug>-<tmp_id>.md`` so a rename of
    ``name`` doesn't collide with an existing file and the id is always
    recoverable from the filename alone.
    """

    def __init__(self, vault_dir: Path):
        self.vault_dir = Path(vault_dir)

    def _path_for(self, tmp_id: str, name: str | None = None) -> Path:
        existing = self._find_path(tmp_id)
        if existing is not None:
            return existing
        return self.vault_dir / f"{_slugify(name or tmp_id)}-{tmp_id}.md"

    def _find_path(self, tmp_id: str) -> Path | None:
        if not self.vault_dir.exists():
            return None
        for path in self.vault_dir.glob(f"*-{tmp_id}.md"):
            return path
        return None

    def list_products(self) -> list[dict]:
        if not self.vault_dir.exists():
            return []
        products = []
        for path in sorted(self.vault_dir.glob("*.md")):
            note = read_note(path)
            fm = note.frontmatter
            if fm.get("tmp_type") == "product":
                products.append(fm)
        return products

    def get(self, tmp_id: str) -> dict:
        path = self._find_path(tmp_id)
        if path is None:
            raise ProductNotFoundError(tmp_id)
        return read_note(path).frontmatter

    def create(self, name: str, category: str = "") -> dict:
        tmp_id = models.new_tmp_id()
        while self._find_path(tmp_id) is not None:
            tmp_id = models.new_tmp_id()
        product = models.empty_product(tmp_id, name, category)
        self.save(product)
        return product

    def save(self, product: dict, body: str | None = None) -> None:
        path = self._path_for(product["tmp_id"], product.get("name"))
        if body is None:
            body = read_note(path).body if path.exists() else ""
        write_note(path, product, body)

    def delete(self, tmp_id: str) -> None:
        path = self._find_path(tmp_id)
        if path is None:
            raise ProductNotFoundError(tmp_id)
        path.unlink()


# ---------------------------------------------------------------------------
# Pure helpers (no filesystem access) — scan-cycle logic, unit-testable.
# ---------------------------------------------------------------------------


def dedupe_new_listings(existing: list[dict], candidates: list[dict]) -> list[dict]:
    """Return only the candidates whose (platform, url) isn't already present.

    ``candidates`` are raw adapter results (dicts with at least ``platform``
    and ``url``); returned dicts have ``id`` set per
    ``models.listing_id_for`` so callers can append them directly to
    ``listings[]``.
    """
    seen_ids = {listing["id"] for listing in existing}
    fresh = []
    for candidate in candidates:
        lid = models.listing_id_for(candidate["platform"], candidate["url"])
        if lid in seen_ids:
            continue
        seen_ids.add(lid)
        enriched = dict(candidate)
        enriched["id"] = lid
        enriched.setdefault("is_new", True)
        fresh.append(enriched)
    return fresh


def recompute_stats(listings: list[dict]) -> dict:
    """Recompute all_time_high / all_time_low from a product's listings[].

    Returns the ``stats`` dict shape from data-model.md. Listings without a
    numeric ``price`` are ignored (e.g. "Bieden" / no-price ads).
    """
    priced = [l for l in listings if isinstance(l.get("price"), (int, float))]
    if not priced:
        return {"all_time_high": None, "all_time_low": None}

    highest = max(priced, key=lambda l: l["price"])
    lowest = min(priced, key=lambda l: l["price"])
    return {
        "all_time_high": {
            "price": highest["price"],
            "listing_id": highest["id"],
            "at": highest.get("seen_at"),
        },
        "all_time_low": {
            "price": lowest["price"],
            "listing_id": lowest["id"],
            "at": lowest.get("seen_at"),
        },
    }


def stats_changed(old_stats: dict, new_stats: dict) -> dict:
    """Which of ath/atl changed, as {'ath': bool, 'atl': bool}.

    Compares by listing_id (not just price) so a tie at the same price from
    a different listing still counts as unchanged — the record itself
    hasn't moved.
    """

    def _id(stats: dict, key: str):
        entry = stats.get(key)
        return entry.get("listing_id") if entry else None

    return {
        "ath": _id(old_stats, "all_time_high") != _id(new_stats, "all_time_high"),
        "atl": _id(old_stats, "all_time_low") != _id(new_stats, "all_time_low"),
    }
