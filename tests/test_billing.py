"""Тесты биллинга: кредиты и оплата."""

import pytest

from app.billing import payments
from app.billing import service as credits
from app.config import get_settings


def test_new_user_gets_trial():
    # По умолчанию начисляется free_trial_scans (1).
    assert credits.balance("new-user") == get_settings().free_trial_scans


def test_charge_and_insufficient():
    credits.grant("u1", 2)
    start = credits.balance("u1")
    credits.charge("u1", 1)
    assert credits.balance("u1") == start - 1
    # Списываем всё, затем ждём ошибку.
    credits.charge("u1", credits.balance("u1"))
    with pytest.raises(credits.InsufficientCredits):
        credits.charge("u1", 1)


def test_grant_rejects_nonpositive():
    with pytest.raises(ValueError):
        credits.grant("u2", 0)


def test_payment_flow_grants_credits():
    before = credits.balance("buyer")
    payment = payments.create_payment("buyer", pack="5")
    assert payment.status == "pending"
    assert payment.credits == 5
    assert payment.amount_rub > 0

    confirmed = payments.confirm_payment(payment.id)
    assert confirmed.status == "succeeded"
    assert credits.balance("buyer") == before + 5


def test_pack_volume_discount():
    # Пакет на 20 сканов дешевле, чем 20 × цена одного.
    base = get_settings().scan_price_rub
    p20 = payments.create_payment("d", pack="20")
    assert p20.amount_rub < base * 20
