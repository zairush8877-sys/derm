"""HTTP-эндпоинты магазина."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import JSONResponse

from app.auth.deps import token_user_id
from app.shop import catalog, loyalty, orders, service
from app.shop.catalog import Category

router = APIRouter(prefix="/api/shop", tags=["Магазин"])


def _parse_category(category: str | None) -> Category | None:
    if not category:
        return None
    try:
        return Category(category)
    except ValueError:
        raise HTTPException(status_code=400, detail="Неизвестная категория")


@router.get("/products")
def products(category: str | None = None, q: str | None = None) -> JSONResponse:
    cat = _parse_category(category)
    items = catalog.search(q, cat) if q else catalog.all_products(cat)
    return JSONResponse(
        {
            "categories": catalog.categories(),
            "products": [p.model_dump(mode="json") for p in items],
        }
    )


@router.get("/search")
def search(q: str, category: str | None = None) -> JSONResponse:
    cat = _parse_category(category)
    items = catalog.search(q, cat)
    return JSONResponse({"query": q, "products": [p.model_dump(mode="json") for p in items]})


@router.get("/product/{product_id}")
def product(product_id: str) -> JSONResponse:
    p = catalog.get_product(product_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return JSONResponse(p.model_dump(mode="json"))


@router.get("/cart")
def cart(user_id: str = "demo-user", auth_id: str | None = Depends(token_user_id)) -> JSONResponse:
    return JSONResponse(service.get_cart(auth_id or user_id))


@router.post("/cart/add")
def cart_add(
    user_id: str = Form("demo-user"),
    product_id: str = Form(...),
    qty: int = Form(1),
    auth_id: str | None = Depends(token_user_id),
) -> JSONResponse:
    user_id = auth_id or user_id
    try:
        service.add_to_cart(user_id, product_id, qty)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return JSONResponse(service.get_cart(user_id))


@router.post("/cart/remove")
def cart_remove(
    user_id: str = Form("demo-user"),
    product_id: str = Form(...),
    auth_id: str | None = Depends(token_user_id),
) -> JSONResponse:
    user_id = auth_id or user_id
    service.remove_from_cart(user_id, product_id)
    return JSONResponse(service.get_cart(user_id))


@router.post("/cart/clear")
def cart_clear(user_id: str = Form("demo-user"), auth_id: str | None = Depends(token_user_id)) -> JSONResponse:
    user_id = auth_id or user_id
    service.clear_cart(user_id)
    return JSONResponse(service.get_cart(user_id))


@router.get("/delivery")
def delivery(user_id: str = "demo-user", auth_id: str | None = Depends(token_user_id)) -> JSONResponse:
    cart = service.get_cart(auth_id or user_id)
    return JSONResponse(orders.delivery_quote(cart["total_rub"]))


@router.post("/checkout")
def checkout(
    user_id: str = Form("demo-user"),
    address: str = Form(...),
    name: str = Form(""),
    phone: str = Form(""),
    auth_id: str | None = Depends(token_user_id),
) -> JSONResponse:
    try:
        result = orders.checkout(auth_id or user_id, address=address, name=name, phone=phone)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return JSONResponse(result)


@router.get("/orders")
def order_history(user_id: str = "demo-user", auth_id: str | None = Depends(token_user_id)) -> JSONResponse:
    return JSONResponse(orders.list_orders(auth_id or user_id))


@router.get("/loyalty")
def loyalty_status(user_id: str = "demo-user", auth_id: str | None = Depends(token_user_id)) -> JSONResponse:
    return JSONResponse(loyalty.status(auth_id or user_id))
