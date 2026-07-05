"""Тесты магазина: каталог, фильтр, корзина, рекомендации."""

from app.shop import catalog, service
from app.shop.catalog import Category


def test_catalog_has_all_categories():
    for cat in Category:
        assert catalog.all_products(cat), f"нет товаров в категории {cat.value}"


def test_filter_by_category():
    skincare = catalog.all_products(Category.SKINCARE)
    assert all(p.category == Category.SKINCARE for p in skincare)


def test_get_product():
    assert catalog.get_product("sk-001") is not None
    assert catalog.get_product("нет-такого") is None


def test_recommend_for_concerns():
    recs = catalog.recommend_for_concerns(["acne", "pores"])
    assert recs
    assert any("acne" in p.for_concerns or "pores" in p.for_concerns for p in recs)


def test_cart_add_get_remove():
    service.clear_cart("shopper")
    service.add_to_cart("shopper", "sk-001", 2)
    service.add_to_cart("shopper", "gd-001", 1)
    cart = service.get_cart("shopper")
    assert cart["count"] == 3
    expected = catalog.get_product("sk-001").price_rub * 2 + catalog.get_product("gd-001").price_rub
    assert cart["total_rub"] == expected

    service.remove_from_cart("shopper", "gd-001")
    assert service.get_cart("shopper")["count"] == 2


def test_cart_add_merges_qty():
    service.clear_cart("merger")
    service.add_to_cart("merger", "sp-001", 1)
    service.add_to_cart("merger", "sp-001", 2)
    cart = service.get_cart("merger")
    assert cart["count"] == 3
