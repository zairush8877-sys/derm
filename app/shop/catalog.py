"""Каталог товаров Aura (демо-данные для РФ, цены в рублях).

Категории по брифу: уходовая и декоративная косметика, гаджеты, спортпит,
витамины и БАДы, пептиды, biohacking, функциональные напитки, healthy food,
лабораторная диагностика и wellness check-up программы.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Category(str, Enum):
    SKINCARE = "уходовая косметика"
    MAKEUP = "декоративная косметика"
    GADGETS = "гаджеты"
    SPORTPIT = "спортпит"
    VITAMINS = "витамины и БАДы"
    PEPTIDES = "пептиды"
    BIOHACKING = "biohacking"
    DRINKS = "функциональные напитки"
    HEALTHY_FOOD = "healthy food"
    LAB = "лабораторная диагностика"
    CHECKUP = "wellness check-up"


class Product(BaseModel):
    id: str
    name: str
    brand: str
    category: Category
    price_rub: int = Field(..., ge=0)
    old_price_rub: int | None = Field(None, ge=0, description="Цена до скидки (перечёркнутая)")
    description: str
    for_concerns: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list, description="Метки для поиска/подбора")
    in_stock: bool = True
    is_service: bool = Field(False, description="Услуга (диагностика/check-up), не товар")
    hit: bool = Field(False, description="Хит продаж — выделяется бейджем")

    @property
    def discount_pct(self) -> int:
        if self.old_price_rub and self.old_price_rub > self.price_rub:
            return round((1 - self.price_rub / self.old_price_rub) * 100)
        return 0


_CATALOG: list[Product] = [
    # --- Уходовая косметика ---
    Product(id="sk-001", name="Сыворотка с витамином C 15%", brand="Aura Lab",
            category=Category.SKINCARE, price_rub=1290, old_price_rub=1690, hit=True,
            description="Антиоксидантная сыворотка со стабильной формой витамина C: "
                        "выравнивает тон, придаёт сияние и защищает от свободных радикалов.",
            for_concerns=["pigmentation", "texture"], tags=["сияние", "тон", "антиоксидант"]),
    Product(id="sk-002", name="Ниацинамид 10% + цинк", brand="Aura Lab",
            category=Category.SKINCARE, price_rub=890,
            description="Себорегуляция, сужение пор, ровный тон.",
            for_concerns=["pores", "oiliness", "acne"], tags=["поры", "жирность"]),
    Product(id="sk-003", name="Крем с гиалуроновой кислотой", brand="HydraLab",
            category=Category.SKINCARE, price_rub=1490,
            description="Глубокое увлажнение и восстановление барьера.",
            for_concerns=["hydration", "redness"], tags=["увлажнение", "барьер"]),
    Product(id="sk-004", name="Ретинол 0.3% ночной уход", brand="NightRx",
            category=Category.SKINCARE, price_rub=1990, hit=True,
            description="Мягкая стартовая концентрация ретинола: обновляет кожу, "
                        "разглаживает рельеф и работает с первыми морщинами. Вводить постепенно.",
            for_concerns=["wrinkles", "texture"], tags=["anti-age", "ретинол"]),
    Product(id="sk-005", name="Солнцезащитный флюид SPF50", brand="SunGuard",
            category=Category.SKINCARE, price_rub=1150,
            description="Лёгкая защита от UV, база анти-эйдж ухода.",
            for_concerns=["pigmentation", "wrinkles"], tags=["spf", "защита"]),
    Product(id="sk-006", name="Патчи для зоны вокруг глаз", brand="HydraLab",
            category=Category.SKINCARE, price_rub=690,
            description="Кофеин и пептиды против тёмных кругов и отёков.",
            for_concerns=["dark_circles"], tags=["глаза", "отёки"]),
    # --- Декоративная косметика ---
    Product(id="mk-001", name="Тональный флюид SPF20, 6 тонов", brand="Aura Beauty",
            category=Category.MAKEUP, price_rub=1690,
            description="Лёгкое покрытие с уходовой формулой и защитой.",
            tags=["тон", "макияж", "spf"]),
    Product(id="mk-002", name="Тинт для губ и щёк", brand="Aura Beauty",
            category=Category.MAKEUP, price_rub=790, description="Натуральный оттенок 2-в-1.",
            tags=["губы", "румяна"]),
    Product(id="mk-003", name="Тушь-уход с пептидами", brand="Aura Beauty",
            category=Category.MAKEUP, price_rub=990, description="Объём и уход за ресницами.",
            tags=["ресницы", "макияж"]),
    # --- Гаджеты ---
    Product(id="gd-001", name="Умные весы с анализом состава тела", brand="FitScale",
            category=Category.GADGETS, price_rub=2790,
            description="Bluetooth-весы: вес, % жира, мышцы, вода.", tags=["весы", "состав тела"]),
    Product(id="gd-002", name="LED-маска для лица", brand="GlowTech",
            category=Category.GADGETS, price_rub=6490,
            description="Светотерапия для тонуса кожи и работы с высыпаниями.",
            for_concerns=["acne", "wrinkles"], tags=["led", "устройство"]),
    Product(id="gd-003", name="Массажёр-микротоки для лица", brand="GlowTech",
            category=Category.GADGETS, price_rub=4990,
            description="Микротоковый лифтинг и тонус кожи.",
            for_concerns=["wrinkles", "texture"], tags=["лифтинг", "устройство"]),
    Product(id="gd-004", name="Кольцо-трекер сна и активности", brand="Aura Ring",
            category=Category.GADGETS, price_rub=18900, old_price_rub=23900, hit=True,
            description="Умное кольцо: отслеживает сон, пульс, HRV и готовность к нагрузке. "
                        "Титановый корпус, до 7 дней автономности. В стиле Oura.",
            tags=["сон", "hrv", "трекер", "biohacking"]),
    # --- Спортпит ---
    Product(id="sp-001", name="Протеин сывороточный 900 г, ваниль", brand="ProFuel",
            category=Category.SPORTPIT, price_rub=1990, old_price_rub=2490, hit=True,
            description="Изолят и концентрат сыворотки: 24 г белка на порцию, "
                        "растворяется без комков. Для восстановления и роста мышц.",
            tags=["протеин", "белок"]),
    Product(id="sp-002", name="Коллаген + витамин C, 30 порций", brand="ProFuel",
            category=Category.SPORTPIT, price_rub=1490,
            description="Поддержка кожи, суставов и связок.",
            for_concerns=["wrinkles", "hydration"], tags=["коллаген", "суставы"]),
    Product(id="sp-003", name="Креатин моногидрат 300 г", brand="ProFuel",
            category=Category.SPORTPIT, price_rub=1190,
            description="Сила и выносливость на тренировках.", tags=["креатин", "сила"]),
    # --- Витамины и БАДы ---
    Product(id="vt-001", name="Омега-3, 120 капсул", brand="VitaCore",
            category=Category.VITAMINS, price_rub=1290,
            description="ЭПК/ДГК для кожи, сердца и мозга.",
            for_concerns=["redness", "hydration"], tags=["омега", "жкт", "кожа"]),
    Product(id="vt-002", name="Витамин D3 2000 МЕ, 90 капсул", brand="VitaCore",
            category=Category.VITAMINS, price_rub=690, old_price_rub=890, hit=True,
            description="Холекальциферол на MCT-масле для лучшего усвоения. "
                        "Иммунитет, настроение и общий тонус — особенно важен зимой.",
            tags=["витамин d", "иммунитет"]),
    Product(id="vt-003", name="Магний B6, 60 таблеток", brand="VitaCore",
            category=Category.VITAMINS, price_rub=790,
            description="Нервная система, сон и восстановление.", tags=["магний", "сон", "стресс"]),
    Product(id="vt-004", name="Цинк + селен, 90 капсул", brand="VitaCore",
            category=Category.VITAMINS, price_rub=650,
            description="Кожа, иммунитет, антиоксидантная защита.",
            for_concerns=["acne"], tags=["цинк", "кожа"]),
    # --- Пептиды ---
    Product(id="pp-001", name="Пептидный комплекс для кожи", brand="PeptidX",
            category=Category.PEPTIDES, price_rub=3490,
            description="Поддержка синтеза коллагена и упругости кожи.",
            for_concerns=["wrinkles"], tags=["пептиды", "anti-age"]),
    Product(id="pp-002", name="Пептиды для суставов и связок", brand="PeptidX",
            category=Category.PEPTIDES, price_rub=2990,
            description="Восстановление соединительной ткани.", tags=["пептиды", "суставы"]),
    # --- Biohacking ---
    Product(id="bh-001", name="NMN 500 мг, 60 капсул", brand="LongevityLab",
            category=Category.BIOHACKING, price_rub=5900,
            description="Поддержка уровня NAD+ и клеточной энергии (longevity).",
            tags=["nmn", "longevity", "энергия"]),
    Product(id="bh-002", name="Ресвератрол 500 мг", brand="LongevityLab",
            category=Category.BIOHACKING, price_rub=2490,
            description="Антиоксидант для здорового старения.", tags=["ресвератрол", "longevity"]),
    Product(id="bh-003", name="Очки блокировки синего света", brand="SleepWell",
            category=Category.BIOHACKING, price_rub=2190,
            description="Гигиена сна и циркадные ритмы.", tags=["сон", "циркадные"]),
    # --- Функциональные напитки ---
    Product(id="dr-001", name="Матча-латте функциональный, 20 порций", brand="Aura Cafe",
            category=Category.DRINKS, price_rub=1190,
            description="L-теанин + матча для мягкой энергии и фокуса.", tags=["матча", "фокус"]),
    Product(id="dr-002", name="Адаптогенный какао с рейши", brand="Aura Cafe",
            category=Category.DRINKS, price_rub=1290,
            description="Грибы-адаптогены для стресса и восстановления.", tags=["адаптогены", "стресс"]),
    Product(id="dr-003", name="Электролиты без сахара, 30 стиков", brand="HydraLab",
            category=Category.DRINKS, price_rub=890,
            description="Гидратация и минералы для тренировок.", tags=["электролиты", "гидратация"]),
    # --- Healthy food ---
    Product(id="hf-001", name="Протеиновые батончики, 12 шт", brand="Aura Kitchen",
            category=Category.HEALTHY_FOOD, price_rub=1490,
            description="20 г белка, без добавленного сахара.", tags=["батончик", "перекус"]),
    Product(id="hf-002", name="Гранола без сахара, 400 г", brand="Aura Kitchen",
            category=Category.HEALTHY_FOOD, price_rub=590,
            description="Цельные злаки и орехи для завтрака.", tags=["завтрак", "клетчатка"]),
    Product(id="hf-003", name="Ореховая паста 100%, 350 г", brand="Aura Kitchen",
            category=Category.HEALTHY_FOOD, price_rub=690,
            description="Без сахара и масел — только орехи.", tags=["перекус", "жиры"]),
    # --- Лабораторная диагностика (услуги) ---
    Product(id="lb-001", name="Чек витаминов D, B12, ферритин", brand="Aura Diagnostics",
            category=Category.LAB, price_rub=3900, is_service=True,
            description="Базовая панель дефицитов. Забор крови в партнёрской лаборатории.",
            tags=["анализы", "дефициты"]),
    Product(id="lb-002", name="Гормональная панель (щитовидка + половые)", brand="Aura Diagnostics",
            category=Category.LAB, price_rub=6900, is_service=True,
            description="Расширенная гормональная диагностика.", tags=["гормоны", "анализы"]),
    # --- Wellness check-up ---
    Product(id="cu-001", name="Экспресс wellness check-up (60 мин)", brand="Aura Space",
            category=Category.CHECKUP, price_rub=7900, is_service=True,
            description="Состав тела, консультация, персональные рекомендации.",
            tags=["checkup", "консультация"]),
    Product(id="cu-002", name="Longevity-программа (расширенная)", brand="Aura Space",
            category=Category.CHECKUP, price_rub=24900, is_service=True,
            description="Диагностика + план biohacking и питания на 3 месяца.",
            tags=["longevity", "программа"]),

    # --- Расширение ассортимента ---
    # Уходовая косметика
    Product(id="sk-007", name="Гель для умывания с AHA/BHA", brand="Aura Lab",
            category=Category.SKINCARE, price_rub=790,
            description="Мягкое кислотное очищение: растворяет загрязнения в порах "
                        "и обновляет кожу без стянутости.",
            for_concerns=["pores", "oiliness", "acne"], tags=["очищение", "кислоты"]),
    Product(id="sk-008", name="Азелаиновая кислота 10%", brand="NightRx",
            category=Category.SKINCARE, price_rub=1390,
            description="Работает с покраснениями, постакне и неровным тоном. "
                        "Подходит чувствительной коже.",
            for_concerns=["redness", "acne", "pigmentation"], tags=["азелаин", "постакне"]),
    Product(id="sk-009", name="Тонер с пантенолом", brand="HydraLab",
            category=Category.SKINCARE, price_rub=690,
            description="Успокаивает, восстанавливает барьер и готовит кожу к уходу.",
            for_concerns=["redness", "hydration"], tags=["тонер", "успокоение"]),
    Product(id="sk-010", name="Крем-SPF 50 для чувствительной кожи", brand="SunGuard",
            category=Category.SKINCARE, price_rub=1290, old_price_rub=1590,
            description="Минеральный фильтр без белых следов, для реактивной кожи.",
            for_concerns=["redness", "pigmentation"], tags=["spf", "чувствительная"]),

    # Декоративная косметика
    Product(id="mk-004", name="Консилер с уходовой формулой", brand="Aura Beauty",
            category=Category.MAKEUP, price_rub=890,
            description="Перекрывает круги и покраснения, ухаживает в течение дня.",
            for_concerns=["dark_circles"], tags=["консилер", "макияж"]),
    Product(id="mk-005", name="Хайлайтер жидкий «сияние»", brand="Aura Beauty",
            category=Category.MAKEUP, price_rub=990, description="Естественное сияние без блёсток.",
            tags=["хайлайтер", "сияние"]),
    Product(id="mk-006", name="Помада-бальзам, 6 оттенков", brand="Aura Beauty",
            category=Category.MAKEUP, price_rub=690, description="Цвет и уход с маслами ши и жожоба.",
            tags=["губы", "макияж"]),

    # Гаджеты
    Product(id="gd-005", name="Массажёр-гуаша электрический", brand="GlowTech",
            category=Category.GADGETS, price_rub=3490,
            description="Тепло + вибрация для лимфодренажа и тонуса лица.",
            for_concerns=["texture", "dark_circles"], tags=["гуаша", "лифтинг"]),
    Product(id="gd-006", name="Умная бутылка с напоминанием о воде", brand="HydraLab",
            category=Category.GADGETS, price_rub=1990, description="Подсветка-напоминание и подсчёт воды за день.",
            tags=["вода", "гидратация", "трекер"]),
    Product(id="gd-007", name="Портативный анализатор кожи", brand="GlowTech",
            category=Category.GADGETS, price_rub=8900, old_price_rub=11900,
            description="Домашний датчик влажности и жирности кожи с приложением.",
            for_concerns=["hydration", "oiliness"], tags=["устройство", "анализ"]),

    # Спортпит
    Product(id="sp-004", name="BCAA 2:1:1, 300 г", brand="ProFuel",
            category=Category.SPORTPIT, price_rub=1290, description="Аминокислоты для восстановления и защиты мышц.",
            tags=["bcaa", "аминокислоты"]),
    Product(id="sp-005", name="Растительный протеин (гороховый), 750 г", brand="ProFuel",
            category=Category.SPORTPIT, price_rub=1790, description="Веган-белок с полным аминокислотным профилем.",
            tags=["протеин", "веган"]),
    Product(id="sp-006", name="L-карнитин жидкий, 500 мл", brand="ProFuel",
            category=Category.SPORTPIT, price_rub=990, description="Поддержка энергообмена во время тренировок.",
            tags=["карнитин", "энергия"]),

    # Витамины и БАДы
    Product(id="vt-005", name="Железо + витамин C, 60 капсул", brand="VitaCore",
            category=Category.VITAMINS, price_rub=790,
            description="Бисглицинат железа — мягко для желудка, против усталости.",
            tags=["железо", "энергия", "ферритин"]),
    Product(id="vt-006", name="Пробиотик 10 штаммов, 30 капсул", brand="VitaCore",
            category=Category.VITAMINS, price_rub=1490, old_price_rub=1890, hit=True,
            description="Поддержка микробиома, пищеварения и кожи.",
            for_concerns=["acne"], tags=["пробиотик", "жкт", "кожа"]),
    Product(id="vt-007", name="Комплекс витаминов группы B", brand="VitaCore",
            category=Category.VITAMINS, price_rub=690, description="Энергия, нервная система, обмен веществ.",
            tags=["витамины b", "энергия"]),
    Product(id="vt-008", name="Коэнзим Q10 100 мг", brand="VitaCore",
            category=Category.VITAMINS, price_rub=1190, description="Энергия клеток и антиоксидантная защита.",
            for_concerns=["wrinkles"], tags=["q10", "энергия"]),

    # Пептиды
    Product(id="pp-003", name="Пептиды коллагена морского, 200 г", brand="PeptidX",
            category=Category.PEPTIDES, price_rub=2290, hit=True,
            description="Гидролизат с высокой биодоступностью для кожи, волос и ногтей.",
            for_concerns=["wrinkles", "hydration"], tags=["коллаген", "пептиды"]),

    # Biohacking
    Product(id="bh-004", name="Магниевое масло-спрей", brand="SleepWell",
            category=Category.BIOHACKING, price_rub=990, description="Трансдермальный магний для расслабления и сна.",
            tags=["магний", "сон"]),
    Product(id="bh-005", name="Спермидин из ростков пшеницы", brand="LongevityLab",
            category=Category.BIOHACKING, price_rub=3290, description="Аутофагия и клеточное обновление (longevity).",
            tags=["спермидин", "longevity"]),

    # Функциональные напитки
    Product(id="dr-004", name="Коллагеновый напиток «сияние», 10 стиков", brand="Aura Cafe",
            category=Category.DRINKS, price_rub=1490, description="Коллаген + витамин C + гиалуронка в удобных стиках.",
            for_concerns=["hydration", "wrinkles"], tags=["коллаген", "красота"]),
    Product(id="dr-005", name="Пребиотический лимонад, 6 шт", brand="Aura Cafe",
            category=Category.DRINKS, price_rub=990, description="Клетчатка и пробиотики, мало сахара.",
            tags=["пребиотик", "жкт"]),

    # Healthy food
    Product(id="hf-004", name="Смесь орехов и ягод, 5 порций", brand="Aura Kitchen",
            category=Category.HEALTHY_FOOD, price_rub=490, description="Сбалансированный перекус без сахара.",
            tags=["перекус", "орехи"]),
    Product(id="hf-005", name="Протеиновая каша, 8 порций", brand="Aura Kitchen",
            category=Category.HEALTHY_FOOD, price_rub=790, description="15 г белка, цельные злаки, быстрый завтрак.",
            tags=["завтрак", "белок"]),

    # Лабораторная диагностика
    Product(id="lb-003", name="Комплекс «Красота изнутри» (кожа/волосы)", brand="Aura Diagnostics",
            category=Category.LAB, price_rub=5400, is_service=True,
            description="Цинк, витамин D, ферритин, гормоны — для кожи и волос.",
            tags=["анализы", "кожа"]),
]

_BY_ID: dict[str, Product] = {p.id: p for p in _CATALOG}


def all_products(category: Category | None = None) -> list[Product]:
    if category is None:
        return list(_CATALOG)
    return [p for p in _CATALOG if p.category == category]


def search(query: str, category: Category | None = None) -> list[Product]:
    """Поиск по названию, бренду, описанию и меткам."""
    q = query.strip().lower()
    base = all_products(category)
    if not q:
        return base
    results = []
    for p in base:
        haystack = " ".join([p.name, p.brand, p.description, " ".join(p.tags)]).lower()
        if q in haystack:
            results.append(p)
    return results


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


def categories() -> list[str]:
    return [c.value for c in Category]
