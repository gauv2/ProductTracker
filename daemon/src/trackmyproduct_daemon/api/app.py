"""FastAPI app: routes per docs/api-contract.md.

The daemon is the only writer of ``stats``/``new_price``/
``notifications_sent``; this layer only ever lets callers touch the fields
docs/api-contract.md says are theirs (product name/category, saved
searches, ``is_new``, deleting a listing).
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .. import __version__
from ..adapters import ADAPTER_REGISTRY
from ..config import Config
from ..notifications import TelegramChannel
from ..pricing import refresh_new_price
from ..price_history import compute_price_history
from ..scan import run_scan_cycle
from ..vault.models import new_tmp_id, utc_now_iso
from ..vault.store import ProductNotFoundError, VaultStore
from .errors import ApiError, NotFoundError, ValidationErrorApi, error_body
from .schemas import ListingPatch, ProductCreate, ProductPatch, SavedSearchCreate, SavedSearchPatch

logger = logging.getLogger(__name__)

_SORT_KEYS = {
    "newest": lambda l: l.get("seen_at") or "",
    "cheapest": lambda l: l.get("price") if l.get("price") is not None else float("inf"),
    "nearest": lambda l: l.get("distance_km") if l.get("distance_km") is not None else float("inf"),
}


def _best_score(listing: dict) -> float:
    price = listing.get("price")
    distance = listing.get("distance_km")
    price_component = price if price is not None else 0.0
    distance_component = (distance or 0.0) * 10  # 10 EUR-equivalent penalty per km, simple heuristic
    return price_component + distance_component


def create_app(config: Config) -> FastAPI:
    app = FastAPI(title="TrackMyProduct Daemon", version=__version__)
    store = VaultStore(config.ensure_vault_dir())
    app.state.config = config
    app.state.store = store
    app.state.last_scan_cycle_at: str | None = None

    @app.exception_handler(ApiError)
    async def handle_api_error(_request, exc: ApiError):
        return JSONResponse(status_code=exc.status_code, content=error_body(exc.code, exc.message))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content=error_body("validation_error", str(exc)))

    def _get_product_or_404(tmp_id: str) -> dict:
        try:
            return store.get(tmp_id)
        except ProductNotFoundError as exc:
            raise NotFoundError(f"product {tmp_id!r} not found") from exc

    def _find_saved_search(product: dict, sid: str) -> dict:
        for ss in product.get("saved_searches", []):
            if ss["id"] == sid:
                return ss
        raise NotFoundError(f"saved search {sid!r} not found")

    def _find_listing(product: dict, lid: str) -> dict:
        for listing in product.get("listings", []):
            if listing["id"] == lid:
                return listing
        raise NotFoundError(f"listing {lid!r} not found")

    def _build_adapters() -> dict:
        return {
            "marktplaats": ADAPTER_REGISTRY["marktplaats"](base_url=config.marktplaats_base_url),
            "ebay": ADAPTER_REGISTRY["ebay"](
                client_id=config.ebay_client_id,
                client_secret=config.ebay_client_secret,
                marketplace_id=config.ebay_marketplace_id,
            ),
            "facebook": ADAPTER_REGISTRY["facebook"](
                cookie=config.facebook_cookie, locale=config.facebook_locale
            ),
        }

    def _build_channels() -> list:
        return [TelegramChannel(config.telegram_bot_token, config.telegram_chat_id)]

    # -- health -------------------------------------------------------

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "daemon_version": __version__,
            "last_scan_cycle_at": app.state.last_scan_cycle_at,
        }

    # -- products -------------------------------------------------------

    @app.get("/products")
    def list_products():
        summaries = []
        for product in store.list_products():
            summaries.append(
                {
                    "tmp_id": product["tmp_id"],
                    "name": product["name"],
                    "category": product.get("category", ""),
                    "stats": product.get("stats", {}),
                    "listing_count": len(product.get("listings", [])),
                    "saved_search_count": len(product.get("saved_searches", [])),
                }
            )
        return summaries

    @app.post("/products", status_code=201)
    def create_product(body: ProductCreate):
        return store.create(name=body.name, category=body.category)

    @app.get("/products/{tmp_id}")
    def get_product(tmp_id: str):
        return _get_product_or_404(tmp_id)

    @app.patch("/products/{tmp_id}")
    def patch_product(tmp_id: str, body: ProductPatch):
        product = _get_product_or_404(tmp_id)
        if body.name is not None:
            product["name"] = body.name
        if body.category is not None:
            product["category"] = body.category
        product["updated_at"] = utc_now_iso()
        store.save(product)
        return product

    @app.delete("/products/{tmp_id}", status_code=204)
    def delete_product(tmp_id: str):
        try:
            store.delete(tmp_id)
        except ProductNotFoundError as exc:
            raise NotFoundError(f"product {tmp_id!r} not found") from exc
        return None

    # -- saved searches ---------------------------------------------------

    @app.post("/products/{tmp_id}/saved-searches", status_code=201)
    def create_saved_search(tmp_id: str, body: SavedSearchCreate):
        product = _get_product_or_404(tmp_id)
        saved_search = {
            "id": f"ss-{new_tmp_id()}",
            "label": body.label,
            "platforms": body.platforms,
            "query": body.query,
            "title_includes": body.title_includes,
            "exclude_words": body.exclude_words,
            "min_price": body.min_price,
            "max_price": body.max_price,
            "mp_distance_km": body.mp_distance_km,
            "mp_postcode": body.mp_postcode,
            "enabled": body.enabled,
            "last_scanned_at": None,
        }
        product.setdefault("saved_searches", []).append(saved_search)
        product["updated_at"] = utc_now_iso()
        store.save(product)
        return saved_search

    @app.patch("/products/{tmp_id}/saved-searches/{sid}")
    def patch_saved_search(tmp_id: str, sid: str, body: SavedSearchPatch):
        product = _get_product_or_404(tmp_id)
        saved_search = _find_saved_search(product, sid)
        for field, value in body.model_dump(exclude_unset=True).items():
            saved_search[field] = value
        product["updated_at"] = utc_now_iso()
        store.save(product)
        return saved_search

    @app.delete("/products/{tmp_id}/saved-searches/{sid}", status_code=204)
    def delete_saved_search(tmp_id: str, sid: str):
        product = _get_product_or_404(tmp_id)
        _find_saved_search(product, sid)  # raises 404 if missing
        product["saved_searches"] = [s for s in product["saved_searches"] if s["id"] != sid]
        product["updated_at"] = utc_now_iso()
        store.save(product)
        return None

    @app.post("/products/{tmp_id}/saved-searches/{sid}/scan")
    def scan_saved_search_now(tmp_id: str, sid: str):
        product = _get_product_or_404(tmp_id)
        _find_saved_search(product, sid)  # raises 404 if missing
        run_scan_cycle(
            store,
            _build_adapters(),
            _build_channels(),
            saved_search_filter=(tmp_id, sid),
        )
        app.state.last_scan_cycle_at = utc_now_iso()
        return _get_product_or_404(tmp_id)

    # -- listings -------------------------------------------------------

    @app.get("/products/{tmp_id}/listings")
    def get_listings(
        tmp_id: str,
        sort: str = Query("newest"),
        saved_search_id: str | None = Query(None),
    ):
        product = _get_product_or_404(tmp_id)
        listings = product.get("listings", [])
        if saved_search_id:
            listings = [l for l in listings if l.get("saved_search_id") == saved_search_id]

        if sort == "best":
            listings = sorted(listings, key=_best_score)
        elif sort in _SORT_KEYS:
            reverse = sort == "newest"
            listings = sorted(listings, key=_SORT_KEYS[sort], reverse=reverse)
        else:
            raise ValidationErrorApi(f"invalid sort {sort!r}")

        return listings

    @app.patch("/products/{tmp_id}/listings/{lid}")
    def patch_listing(tmp_id: str, lid: str, body: ListingPatch):
        product = _get_product_or_404(tmp_id)
        listing = _find_listing(product, lid)
        if body.is_new is not None:
            listing["is_new"] = body.is_new
        store.save(product)
        return listing

    @app.delete("/products/{tmp_id}/listings/{lid}", status_code=204)
    def delete_listing(tmp_id: str, lid: str):
        product = _get_product_or_404(tmp_id)
        _find_listing(product, lid)  # raises 404 if missing
        product["listings"] = [l for l in product["listings"] if l["id"] != lid]
        store.save(product)
        return None

    # -- price history / new price ---------------------------------------

    @app.get("/products/{tmp_id}/price-history")
    def get_price_history(tmp_id: str, period: str = Query("all")):
        product = _get_product_or_404(tmp_id)
        return {"points": compute_price_history(product.get("listings", []), period)}

    @app.post("/products/{tmp_id}/refresh-new-price")
    def refresh_new_price_route(tmp_id: str):
        product = _get_product_or_404(tmp_id)
        product["new_price"] = refresh_new_price(product["name"], config)
        product["updated_at"] = utc_now_iso()
        store.save(product)
        return product["new_price"]

    return app
