from pathlib import Path

import pytest

from trackmyproduct_daemon.vault.store import ProductNotFoundError, VaultStore


def test_create_then_get_round_trips(tmp_path: Path):
    store = VaultStore(tmp_path)
    product = store.create(name="NVIDIA DGX Spark", category="Computer hardware")

    fetched = store.get(product["tmp_id"])
    assert fetched["name"] == "NVIDIA DGX Spark"
    assert fetched["category"] == "Computer hardware"
    assert fetched["tmp_type"] == "product"


def test_get_missing_product_raises(tmp_path: Path):
    store = VaultStore(tmp_path)
    with pytest.raises(ProductNotFoundError):
        store.get("doesnotexist")


def test_list_products_only_returns_product_notes(tmp_path: Path):
    store = VaultStore(tmp_path)
    store.create(name="Product A")
    (tmp_path / "not-a-product.md").write_text("---\ntmp_type: other\n---\nbody", encoding="utf-8")

    products = store.list_products()
    assert len(products) == 1
    assert products[0]["name"] == "Product A"


def test_delete_removes_note(tmp_path: Path):
    store = VaultStore(tmp_path)
    product = store.create(name="To Delete")
    store.delete(product["tmp_id"])
    with pytest.raises(ProductNotFoundError):
        store.get(product["tmp_id"])


def test_save_preserves_body_text(tmp_path: Path):
    store = VaultStore(tmp_path)
    product = store.create(name="With Notes")
    path = next(tmp_path.glob("*.md"))
    path.write_text(path.read_text(encoding="utf-8") + "my personal note", encoding="utf-8")

    reloaded = store.get(product["tmp_id"])
    reloaded["category"] = "updated"
    store.save(reloaded)

    assert "my personal note" in path.read_text(encoding="utf-8")
