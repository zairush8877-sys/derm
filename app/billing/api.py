"""HTTP-эндпоинты биллинга (кредиты и оплата)."""

from __future__ import annotations

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse, JSONResponse

from app.billing import payments
from app.billing import service as credits
from app.config import get_settings

router = APIRouter(prefix="/api/billing", tags=["Биллинг"])


@router.get("/balance")
def get_balance(user_id: str = "demo-user") -> JSONResponse:
    s = get_settings()
    return JSONResponse(
        {
            "user_id": user_id,
            "balance": credits.balance(user_id),
            "scan_price_rub": s.scan_price_rub,
            "packs": payments.CREDIT_PACKS,
        }
    )


@router.post("/checkout")
def checkout(user_id: str = Form("demo-user"), pack: str = Form("1")) -> JSONResponse:
    """Создать платёж за пакет сканов. Возвращает confirmation_url."""
    payment = payments.create_payment(user_id, pack)
    return JSONResponse(
        {
            "payment_id": payment.id,
            "amount_rub": payment.amount_rub,
            "credits": payment.credits,
            "status": payment.status,
            "provider": payment.provider,
            "confirmation_url": payment.confirmation_url,
        }
    )


@router.get("/confirm")
def confirm(payment_id: str) -> HTMLResponse:
    """Демо-подтверждение оплаты (в проде — webhook провайдера)."""
    payment = payments.confirm_payment(payment_id)
    return HTMLResponse(
        f"""<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
        <title>Оплата</title><meta http-equiv="refresh" content="2; url=/"></head>
        <body style="font-family:sans-serif;text-align:center;padding:60px">
        <h2>✅ Оплата подтверждена</h2>
        <p>Начислено сканов: {payment.credits}. Возвращаемся в приложение…</p>
        </body></html>"""
    )
