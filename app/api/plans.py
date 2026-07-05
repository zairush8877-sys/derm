"""Тарифы B2B для брендов: pay-per-scan и SaaS-подписки с квотой сканов.

Модель монетизации #1: бренды платят либо за каждый скан, либо по подписке
с включённой месячной квотой сканов (сверх квоты — доплата за скан).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Plan:
    id: str
    name: str
    monthly_price_usd: int      # цена подписки в месяц ($); 0 для pay-per-scan
    included_scans: int          # включённые сканы в месяц (0 = без включённых)
    price_per_scan_usd: float    # цена за скан / за скан сверх квоты


PLANS: dict[str, Plan] = {
    "payg": Plan("payg", "Pay-as-you-go", 0, 0, 0.30),
    "starter": Plan("starter", "Starter", 499, 2500, 0.20),
    "growth": Plan("growth", "Growth", 1499, 10000, 0.15),
    "enterprise": Plan("enterprise", "Enterprise", 4999, 50000, 0.10),
}

DEFAULT_PLAN = "payg"


def get_plan(plan_id: str) -> Plan:
    return PLANS.get(plan_id, PLANS[DEFAULT_PLAN])


def estimate_cost_usd(plan_id: str, scans_this_month: int) -> float:
    """Оценить стоимость за месяц по плану и числу сканов."""
    plan = get_plan(plan_id)
    overage = max(0, scans_this_month - plan.included_scans)
    return round(plan.monthly_price_usd + overage * plan.price_per_scan_usd, 2)
