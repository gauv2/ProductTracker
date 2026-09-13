from .base import AdapterError, Listing, PlatformAdapter, SearchFilters
from .ebay import EbayAdapter
from .facebook import FacebookAdapter
from .marktplaats import MarktplaatsAdapter

__all__ = [
    "AdapterError",
    "Listing",
    "PlatformAdapter",
    "SearchFilters",
    "MarktplaatsAdapter",
    "EbayAdapter",
    "FacebookAdapter",
]

ADAPTER_REGISTRY = {
    "marktplaats": MarktplaatsAdapter,
    "ebay": EbayAdapter,
    "facebook": FacebookAdapter,
}
