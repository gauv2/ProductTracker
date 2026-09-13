"""Request/response shapes for the API layer.

Frontmatter itself (the persisted shape) stays plain dicts per
data-model.md — these pydantic models are only for validating what comes
in over HTTP and shaping list/summary responses.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Platform = Literal["marktplaats", "ebay", "facebook"]


class ProductCreate(BaseModel):
    name: str
    category: str = ""


class ProductPatch(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None


class SavedSearchCreate(BaseModel):
    label: str
    query: str
    platforms: list[Platform]
    title_includes: list[str] = Field(default_factory=list)
    exclude_words: list[str] = Field(default_factory=list)
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    mp_distance_km: Optional[float] = None
    mp_postcode: Optional[str] = None
    enabled: bool = True


class SavedSearchPatch(BaseModel):
    label: Optional[str] = None
    query: Optional[str] = None
    platforms: Optional[list[Platform]] = None
    title_includes: Optional[list[str]] = None
    exclude_words: Optional[list[str]] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    mp_distance_km: Optional[float] = None
    mp_postcode: Optional[str] = None
    enabled: Optional[bool] = None


class ListingPatch(BaseModel):
    is_new: Optional[bool] = None
