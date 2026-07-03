"""HTTP-эндпоинты магазина."""

from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import JSONResponse

from app.shop import catalog, service
from app.shop.catalog import Category

router = APIRouter(prefix="/api/shop", tags=["Магазин"])


@router.get("/products")
def products(category: str | None = None) -> JSONResponse:
    cat = None
    if category:
        try:
            cat = Category(category)
        except ValueError:
            raise HTTPException(status_code=400, detail="Неизвестная категория")
    items = catalog.all_products(cat)
    return JSONResponse(
        {
            "categories": [c.value for c in Category],
            "products": [p.model_dump(mode="json") for p in items],
        }
    )


@router.get("/product/{product_id}")
def product(product_id: str) -> JSONResponse:
    p = catalog.get_product(product_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return JSONResponse(p.model_dump(mode="json"))


@router.get("/cart")
def cart(user_id: str = "demo-user") -> JSONResponse:
    return JSONResponse(service.get_cart(user_id))


@router.post("/cart/add")
def cart_add(
    user_id: str = Form("demo-user"),
    product_id: str = Form(...),
    qty: int = Form(1),
) -> JSONResponse:
    try:
        service.add_to_cart(user_id, product_id, qty)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return JSONResponse(service.get_cart(user_id))


@router.post("/cart/remove")
def cart_remove(user_id: str = Form("demo-user"), product_id: str = Form(...)) -> JSONResponse:
    service.remove_from_cart(user_id, product_id)
    return JSONResponse(service.get_cart(user_id))


@router.post("/cart/clear")
def cart_clear(user_id: str = Form("demo-user")) -> JSONResponse:
    service.clear_cart(user_id)
    return JSONResponse(service.get_cart(user_id))
