"""HTTP-эндпоинты лаборатории: панели, запись, мои заявки."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Header
from fastapi.responses import JSONResponse

from app.auth.deps import token_user_id
from app.lab import service
from app.lab.catalog import LAB_DISCLAIMER, list_panels

router = APIRouter(prefix="/api/lab", tags=["Лаборатория"])


@router.get("/panels")
def panels() -> JSONResponse:
    return JSONResponse({
        "panels": [p.model_dump() for p in list_panels()],
        "disclaimer": LAB_DISCLAIMER,
    })


@router.post("/book")
def book(
    panel_id: str = Form(...),
    city: str = Form(...),
    phone: str = Form(...),
    preferred_date: str = Form(default=""),
    comment: str = Form(default=""),
    user_id: str = Form(default="demo-user"),
    auth_id: str | None = Depends(token_user_id),
) -> JSONResponse:
    try:
        booking = service.book(
            auth_id or user_id, panel_id, city, phone, preferred_date, comment
        )
    except service.BookingError as e:
        return JSONResponse(status_code=422, content={"error": str(e)})
    return JSONResponse({"booking": booking})


@router.get("/bookings")
def bookings(
    user_id: str = "demo-user",
    auth_id: str | None = Depends(token_user_id),
) -> JSONResponse:
    return JSONResponse({"bookings": service.list_for(auth_id or user_id)})


@router.post("/cancel")
def cancel(
    booking_id: str = Form(...),
    user_id: str = Form(default="demo-user"),
    auth_id: str | None = Depends(token_user_id),
) -> JSONResponse:
    try:
        booking = service.cancel(auth_id or user_id, booking_id)
    except service.BookingError as e:
        return JSONResponse(status_code=422, content={"error": str(e)})
    return JSONResponse({"booking": booking})


@router.get("/admin/bookings")
def admin_bookings(
    x_admin_token: str = Header(default="", alias="X-Admin-Token"),
) -> JSONResponse:
    from app.admin.api import _guard

    _guard(x_admin_token)
    return JSONResponse({"bookings": service.list_all()})
