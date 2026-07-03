"""Каталог товаров магазина (демо-данные для РФ, цены в рублях)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Category(str, Enum):
    GADGETS = "гаджеты"
    SPORTPIT = "спортпит"
    SKINCARE = "уходовая косметика"


class Product(BaseModel):
    id: str
    name: str
    brand: str
    category: Category
    price_rub: int = Field(..., ge=0)
    description: str
    # Ключи проблем кожи, которым помогает товар (для рекомендаций по анализу).
    for_concerns: list[str] = Field(default_factory=list)
    in_stock: bool = True


# Демонстрационный каталог. В проде заменяется на реальную витрину/БД.
_CATALOG: list[Product] = [
    # Уходовая косметика
    Product(id="sk-001", name="Сыворотка с витамином C 15%", brand="AwaraSkin",
            category=Category.SKINCARE, price_rub=1290,
            description="Антиоксидантная сыворотка для ровного тона и сияния.",
            for_concerns=["pigmentation", "texture"]),
    Product(id="sk-002", name="Ниацинамид 10% + цинк", brand="AwaraSkin",
            category=Category.SKINCARE, price_rub=890,
            description="Себорегуляция, сужение пор, ровный тон.",
            for_concerns=["pores", "oiliness", "acne"]),
    Product(id="sk-003", name="Крем с гиалуроновой кислотой", brand="HydraLab",
            category=Category.SKINCARE, price_rub=1490,
            description="Глубокое увлажнение и восстановление барьера.",
            for_concerns=["hydration", "redness"]),
    Product(id="sk-004", name="Ретинол 0.3% ночной уход", brand="NightRx",
            category=Category.SKINCARE, price_rub=1990,
            description="Мягкое обновление кожи, работа с морщинами.",
            for_concerns=["wrinkles", "texture"]),
    Product(id="sk-005", name="Солнцезащитный флюид SPF50", brand="SunGuard",
            category=Category.SKINCARE, price_rub=1150,
            description="Лёгкая защита от UV, база анти-эйдж ухода.",
            for_concerns=["pigmentation", "wrinkles"]),
    Product(id="sk-006", name="Патчи для зоны вокруг глаз", brand="HydraLab",
            category=Category.SKINCARE, price_rub=690,
            description="Кофеин и пептиды против тёмных кругов и отёков.",
            for_concerns=["dark_circles"]),
    # Гаджеты
    Product(id="gd-001", name="Умные весы с анализом состава тела", brand="FitScale",
            category=Category.GADGETS, price_rub=2790,
            description="Bluetooth-весы: вес, % жира, мышцы, вода."),
    Product(id="gd-002", name="LED-маска для лица", brand="GlowTech",
            category=Category.GADGETS, price_rub=6490,
            description="Светотерапия для тонуса кожи и работы с высыпаниями.",
            for_concerns=["acne", "wrinkles"]),
    Product(id="gd-003", name="Массажёр-микротоки для лица", brand="GlowTech",
            category=Category.GADGETS, price_rub=4990,
            description="Микротоковый лифтинг и тонус кожи.",
            for_concerns=["wrinkles", "texture"]),
    Product(id="gd-004", name="Фитнес-браслет с пульсометром", brand="FitScale",
            category=Category.GADGETS, price_rub=3490,
            description="Шаги, пульс, сон, тренировки."),
    # Спортпит
    Product(id="sp-001", name="Протеин сывороточный 900 г, ваниль", brand="ProFuel",
            category=Category.SPORTPIT, price_rub=1990,
            description="24 г белка на порцию, для восстановления мышц."),
    Product(id="sp-002", name="Коллаген + витамин C, 30 порций", brand="ProFuel",
            category=Category.SPORTPIT, price_rub=1490,
            description="Поддержка кожи, суставов и связок.",
            for_concerns=["wrinkles", "hydration"]),
    Product(id="sp-003", name="Омега-3, 120 капсул", brand="VitaCore",
            category=Category.SPORTPIT, price_rub=1290,
            description="ЭПК/ДГК для кожи, сердца и мозга.",
            for_concerns=["redness", "hydration"]),
    Product(id="sp-004", name="Креатин моногидрат 300 г", brand="ProFuel",
            category=Category.SPORTPIT, price_rub=1190,
            description="Сила и выносливость на тренировках."),
    Product(id="sp-005", name="Витамин D3 2000 МЕ, 90 капсул", brand="VitaCore",
            category=Category.SPORTPIT, price_rub=690,
            description="Иммунитет и общий тонус."),
]

_BY_ID: dict[str, Product] = {p.id: p for p in _CATALOG}


def all_products(category: Category | None = None) -> list[Product]:
    if category is None:
        return list(_CATALOG)
    return [p for p in _CATALOG if p.category == category]


def get_product(product_id: str) -> Product | None:
    return _BY_ID.get(product_id)


def recommend_for_concerns(concern_keys: list[str], limit: int = 6) -> list[Product]:
    """Подобрать товары под проблемы кожи (для связки с анализом)."""
    wanted = set(concern_keys)
    scored = [
        (len(wanted & set(p.for_concerns)), p)
        for p in _CATALOG
        if wanted & set(p.for_concerns)
    ]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:limit]]
