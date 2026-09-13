"""eBay adapter — real implementation against the official Browse API.

Requires an eBay application (client credentials) token — see
``/daemon/README.md`` "eBay setup" for how to create one in the eBay
Developer Program and where to put ``ebay_client_id`` /
``ebay_client_secret`` in the daemon config. This adapter never scrapes
eBay's HTML, per docs/api-contract.md.

Flow:
1. ``POST https://api.ebay.com/identity/v1/oauth2/token`` (client
   credentials grant, scope ``https://api.ebay.com/oauth/api_scope``) to get
   an application access token. Tokens are cached in-process until they
   expire (typically ~2h).
2. ``GET https://api.ebay.com/buy/browse/v1/item_summary/search`` with the
   token as a Bearer header.
"""

from __future__ import annotations

import time

import httpx

from .base import AdapterError, Listing, SearchFilters, apply_client_side_filters

OAUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
OAUTH_SCOPE = "https://api.ebay.com/oauth/api_scope"


class EbayAdapter:
    name = "ebay"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        marketplace_id: str = "EBAY_NL",
        timeout: float = 15.0,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.marketplace_id = marketplace_id
        self.timeout = timeout
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    def _get_token(self) -> str:
        if self._token and time.monotonic() < self._token_expires_at:
            return self._token

        if not self.client_id or not self.client_secret:
            raise AdapterError(
                "ebay adapter is not configured: set ebay_client_id / "
                "ebay_client_secret (see README's eBay setup section)"
            )

        try:
            response = httpx.post(
                OAUTH_URL,
                auth=(self.client_id, self.client_secret),
                data={"grant_type": "client_credentials", "scope": OAUTH_SCOPE},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AdapterError(f"ebay oauth token request failed: {exc}") from exc

        token = payload.get("access_token")
        expires_in = payload.get("expires_in", 0)
        if not token:
            raise AdapterError("ebay oauth response missing access_token")

        self._token = token
        # Refresh a little early to avoid racing expiry mid-request.
        self._token_expires_at = time.monotonic() + max(expires_in - 60, 0)
        return token

    def search(self, query: str, filters: SearchFilters) -> list[Listing]:
        token = self._get_token()

        filter_parts = ["buyingOptions:{FIXED_PRICE|AUCTION}"]
        if filters.min_price is not None or filters.max_price is not None:
            low = filters.min_price if filters.min_price is not None else ""
            high = filters.max_price if filters.max_price is not None else ""
            filter_parts.append(f"price:[{low}..{high}]")
            filter_parts.append("priceCurrency:EUR")

        params = {
            "q": query,
            "limit": "50",
            "filter": ",".join(filter_parts),
        }

        try:
            response = httpx.get(
                SEARCH_URL,
                params=params,
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-EBAY-C-MARKETPLACE-ID": self.marketplace_id,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AdapterError(f"ebay search failed: {exc}") from exc

        listings = [self._to_listing(raw) for raw in data.get("itemSummaries", [])]
        return apply_client_side_filters(listings, filters)

    def _to_listing(self, raw: dict) -> Listing:
        price = raw.get("price") or {}
        price_value = price.get("value")
        try:
            price_float = float(price_value) if price_value is not None else None
        except ValueError:
            price_float = None

        item_location = raw.get("itemLocation") or {}
        location_parts = [
            item_location.get("city"),
            item_location.get("stateOrProvince"),
            item_location.get("country"),
        ]
        location = ", ".join(p for p in location_parts if p)

        return Listing(
            platform=self.name,
            title=raw.get("title", ""),
            price=price_float,
            currency=price.get("currency", "EUR"),
            location=location,
            distance_km=None,  # eBay Browse API doesn't return caller-relative distance.
            posted_at=raw.get("itemCreationDate"),
            url=raw.get("itemWebUrl", ""),
        )
