"""Каталог товаров Aura (демо-данные для РФ, цены в рублях).

Категории по брифу: уходовая и декоративная косметика, гаджеты, спортпит,
витамины и БАДы, пептиды, biohacking, функциональные напитки, healthy food,
лабораторная диагностика и wellness check-up программы.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

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
    image: str | None = Field(None, description="Путь к фото товара (/static/products/…)")

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

    # ===== Jan Marini (Marini SkinSolutions) — профессиональный уход =====
    # Реальный ассортимент по прайсу дистрибьютора, цены РРЦ.
    # Системы ухода
    Product(id="jm-001", name="Skin Care Management System (Normal-Combo) SPF 33", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=42900, hit=True,
            description="Легендарная система ухода из 5 шагов для нормальной и комбинированной кожи с SPF 33.",
            for_concerns=["wrinkles", "texture", "pigmentation"], tags=["система", "spf", "anti-age", "MSS001"]),
    Product(id="jm-002", name="Skin Care Management System (Normal-Combo) SPF 45", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=42900,
            description="Система ухода для нормальной и комбинированной кожи с усиленной защитой SPF 45.",
            for_concerns=["wrinkles", "texture", "pigmentation"], tags=["система", "spf", "MSS002"]),
    Product(id="jm-003", name="Skin Care Management System (Dry-Very Dry) SPF 33", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=42900,
            description="Система ухода для сухой и очень сухой кожи с SPF 33.",
            for_concerns=["hydration", "wrinkles"], tags=["система", "сухая кожа", "MSS003"]),
    Product(id="jm-004", name="Skin Care Management System (Dry-Very Dry) SPF 45", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=42900,
            description="Система ухода для сухой и очень сухой кожи с SPF 45.",
            for_concerns=["hydration", "wrinkles"], tags=["система", "сухая кожа", "MSS004"]),
    Product(id="jm-005", name="Marini Men's System", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=33500,
            description="Система ухода, разработанная для мужской кожи.",
            for_concerns=["texture", "oiliness"], tags=["мужской уход", "система", "MSS058"]),
    Product(id="jm-006", name="Starter Skin Care Management System SPF 33 (Travel)", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=28500,
            description="Стартовый тревел-формат легендарной системы для нормальной кожи с SPF 33.",
            for_concerns=["wrinkles", "texture"], tags=["система", "travel", "MSS009"]),
    Product(id="jm-007", name="PostTX 1 Recovery Enhancement System", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=25500,
            description="Система восстановления и ухода за чувствительной и повреждённой кожей.",
            for_concerns=["redness", "hydration"], tags=["восстановление", "постпроцедурный", "MSS066"]),
    Product(id="jm-008", name="PostTX 2 Recovery Enhancement System", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=21900,
            description="Система постпроцедурного восстановления и усиления результатов.",
            for_concerns=["redness"], tags=["восстановление", "постпроцедурный", "MSS067"]),
    # Очищение
    Product(id="jm-010", name="Bioglycolic Face Cleanser, 178 мл", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=6450,
            description="Очищающая эмульсия на основе гликолевой кислоты для выравнивания тона и рельефа.",
            for_concerns=["texture", "pigmentation"], tags=["очищение", "кислоты", "MSS014"]),
    Product(id="jm-011", name="Bioglycolic Oily Skin Cleansing Gel, 178 мл", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=6450,
            description="Очищающий гель с гликолевой кислотой для жирной и комбинированной кожи.",
            for_concerns=["oiliness", "pores", "acne"], tags=["очищение", "жирная кожа", "MSS015"]),
    Product(id="jm-012", name="C-ESTA Cleansing Gel, 178 мл", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=6450,
            description="Очищающий гель с витамином C и DMAE.",
            for_concerns=["texture", "wrinkles"], tags=["очищение", "витамин c", "MSS016"]),
    Product(id="jm-013", name="Clean Zyme, 178 мл", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=7500,
            description="Очищающий и обновляющий энзимный гель с папаином.",
            for_concerns=["texture"], tags=["очищение", "энзимы", "MSS041"]),
    Product(id="jm-014", name="Gentle Cleanser, 178 мл", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=6450,
            description="Нежная очищающая эмульсия для чувствительной и реактивной кожи.",
            for_concerns=["redness"], tags=["очищение", "чувствительная", "MSS017"]),
    # Ремоделирование и восстановление
    Product(id="jm-020", name="C-ESTA Face Serum, 30 мл", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=16950, hit=True,
            description="Ремоделирующая сыворотка с витамином C и DMAE — тонус, сияние, чёткий овал.",
            for_concerns=["wrinkles", "texture", "pigmentation"], tags=["сыворотка", "витамин c", "MSS018"]),
    Product(id="jm-021", name="C-ESTA Face Cream, 28 г", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=16950,
            description="Ремоделирующий крем с витамином C и DMAE.",
            for_concerns=["wrinkles", "texture"], tags=["крем", "витамин c", "MSS020"]),
    Product(id="jm-022", name="Bioclear Face Lotion, 30 мл", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=12500,
            description="Многофункциональная корректирующая сыворотка с комплексом кислот.",
            for_concerns=["acne", "texture", "pores"], tags=["кислоты", "MSS021"]),
    Product(id="jm-023", name="Bioclear Face Cream, 28 г", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=12500,
            description="Многофункциональный корректирующий крем с комплексом кислот.",
            for_concerns=["acne", "texture"], tags=["кислоты", "MSS022"]),
    Product(id="jm-024", name="Transformation Face Cream, 28 г", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=15950,
            description="Трансформирующий крем для восстановления дермальных структур.",
            for_concerns=["wrinkles", "hydration"], tags=["восстановление", "MSS023"]),
    Product(id="jm-025", name="Age Intervention Face Cream, 28 г", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=15950,
            description="Обогащённый антивозрастной крем с фитоэстрогенами.",
            for_concerns=["wrinkles", "hydration"], tags=["anti-age", "MSS025"]),
    Product(id="jm-026", name="PeptideXtreme, 30 мл", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=15950,
            description="Обогащённая антивозрастная сыворотка с пептидным комплексом.",
            for_concerns=["wrinkles"], tags=["пептиды", "anti-age", "MSS026"]),
    # Защита от солнца
    Product(id="jm-030", name="Antioxidant Daily Face Protectant SPF 33, 57 г", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=7600, hit=True,
            description="Антиоксидантный солнцезащитный крем с увлажняющим действием.",
            for_concerns=["pigmentation", "wrinkles"], tags=["spf", "MSS027"]),
    Product(id="jm-031", name="Physical Protectant Tinted SPF 45 (Fair to Light)", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=7600,
            description="Солнцезащитный крем с тональным эффектом, оттенок Light.",
            for_concerns=["pigmentation", "redness"], tags=["spf", "тональный", "MSS068"]),
    Product(id="jm-032", name="Physical Protectant Tinted SPF 45 (Light to Medium)", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=7600,
            description="Солнцезащитный крем с тональным эффектом, оттенок Medium.",
            for_concerns=["pigmentation"], tags=["spf", "тональный", "MSS029"]),
    # Акселераторы с ретинолом
    Product(id="jm-040", name="Retinol Plus, 28 г", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=13950, hit=True,
            description="Крем-акселератор с ретинолом 0,5% против видимых возрастных изменений.",
            for_concerns=["wrinkles", "texture"], tags=["ретинол", "anti-age", "MSS030"]),
    Product(id="jm-041", name="Retinol Plus XC, 28 г", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=14500,
            description="Крем-акселератор с ретинолом 1% для выраженных возрастных изменений.",
            for_concerns=["wrinkles", "texture"], tags=["ретинол", "MSS031"]),
    Product(id="jm-042", name="Marini Luminate, 30 мл", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=15100,
            description="Крем-акселератор с ретинолом 0,3% для борьбы с пигментацией.",
            for_concerns=["pigmentation"], tags=["ретинол", "пигментация", "MSS032"]),
    Product(id="jm-043", name="Marini Luminate XC, 30 мл", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=15650,
            description="Крем-акселератор с ретинолом 0,75% для выраженной пигментации.",
            for_concerns=["pigmentation"], tags=["ретинол", "пигментация", "MSS033"]),
    Product(id="jm-044", name="Duality, 28 г", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=15000,
            description="Крем-акселератор с ретинолом 0,6% для ухода за кожей с акне.",
            for_concerns=["acne", "texture"], tags=["ретинол", "акне", "MSS061"]),
    # Акселераторы BPO (акне)
    Product(id="jm-050", name="BPO Acne Treatment Wash 2.5%, 178 мл", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=7000,
            description="Очищающая эмульсия для ухода за кожей с акне (бензоилпероксид 2,5%).",
            for_concerns=["acne", "oiliness"], tags=["акне", "bpo", "MSS081"]),
    Product(id="jm-051", name="BPO Acne Treatment Lotion 5%, 60 мл", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=4800,
            description="Лосьон для ухода за кожей с акне (бензоилпероксид 5%).",
            for_concerns=["acne"], tags=["акне", "bpo", "MSS082"]),
    Product(id="jm-052", name="BPO Acne Treatment Lotion 10%, 60 мл", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=4800,
            description="Лосьон для ухода за кожей с выраженным акне (бензоилпероксид 10%).",
            for_concerns=["acne"], tags=["акне", "bpo", "MSS083"]),
    # Гиалуроновая линия
    Product(id="jm-060", name="Hyla3D Face Serum, 30 мл", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=15200, hit=True,
            description="Сыворотка-акселератор с 3D гиалуроновым комплексом — глубокое увлажнение.",
            for_concerns=["hydration", "wrinkles"], tags=["гиалуроновая", "увлажнение", "MSS035"]),
    Product(id="jm-061", name="Hyla3D Face Cream, 28 г", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=15200,
            description="Ультра-увлажняющий крем, восстанавливающий барьерные функции, с 3D гиалуроновым комплексом.",
            for_concerns=["hydration", "redness"], tags=["гиалуроновая", "барьер", "MSS057"]),
    # Пептиды / факторы роста
    Product(id="jm-070", name="NeuroSmooth, 30 мл", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=23500,
            description="Нейропептидная омолаживающая сыворотка для безупречной гладкости кожи.",
            for_concerns=["wrinkles"], tags=["пептиды", "MSS079"]),
    Product(id="jm-071", name="RosaLieve, 30 мл", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=14500,
            description="Крем-акселератор для комплексного решения проблем розацеа.",
            for_concerns=["redness"], tags=["розацеа", "покраснения", "MSS036"]),
    Product(id="jm-072", name="Regeneration Booster, 30 мл", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=28000,
            description="Сыворотка-бустер с революционным комплексом для клеточного омоложения.",
            for_concerns=["wrinkles", "texture"], tags=["бустер", "anti-age", "MSS037"]),
    Product(id="jm-073", name="Marini BioShield, 28 г", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=11500,
            description="Крем для мгновенного восстановления и защиты после травматичных процедур.",
            for_concerns=["redness", "hydration"], tags=["постпроцедурный", "MSS038"]),
    # Маски и пилинги
    Product(id="jm-080", name="Retinol Plus Mask, 48 г", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=13500,
            description="Высококонцентрированная маска с ретинолом 1%.",
            for_concerns=["wrinkles", "texture"], tags=["маска", "ретинол", "MSS039"]),
    Product(id="jm-081", name="Marini Luminate Face Mask, 48 г", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=13500,
            description="Осветляющая маска для сияния кожи.",
            for_concerns=["pigmentation"], tags=["маска", "сияние", "MSS040"]),
    Product(id="jm-082", name="Hyla3D Face Mask, 48 г", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=13500,
            description="Ревитализирующая маска для экстремального увлажнения и восстановления барьера.",
            for_concerns=["hydration"], tags=["маска", "увлажнение", "MSS063"]),
    Product(id="jm-083", name="Skin Zyme, 48 г", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=10500,
            description="Обновляющая и восстанавливающая энзимная маска с папаином.",
            for_concerns=["texture"], tags=["маска", "энзимы", "MSS042"]),
    Product(id="jm-084", name="Marini ResurFace Peel Pads, 30 шт", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=12500,
            description="Мультикислотные пилинг-диски для глубокого обновления кожи.",
            for_concerns=["texture", "pigmentation"], tags=["пилинг", "кислоты", "MSS060"]),
    Product(id="jm-085", name="Marini Clear Corrective Pads, 30 шт", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=12500,
            description="Корректирующие пилинг-диски для комбинированной, жирной и склонной к воспалениям кожи.",
            for_concerns=["acne", "oiliness", "pores"], tags=["пилинг", "акне", "MSS054"]),
    # Глаза и губы
    Product(id="jm-090", name="Marini Luminate Eye Gel, 15 мл", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=13500, hit=True,
            description="Концентрированная сыворотка для кожи вокруг глаз против тёмных кругов и морщин.",
            for_concerns=["dark_circles", "wrinkles"], tags=["глаза", "MSS045"]),
    Product(id="jm-091", name="Age Intervention Eye Cream, 14 г", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=12100,
            description="Антивозрастной крем для улучшения тонуса и тургора кожи вокруг глаз.",
            for_concerns=["dark_circles", "wrinkles"], tags=["глаза", "MSS046"]),
    Product(id="jm-092", name="C-ESTA Eye Repair, 14 г", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=12100,
            description="Сыворотка-концентрат для интенсивного лифтинга кожи вокруг глаз с витамином C и DMAE.",
            for_concerns=["dark_circles", "wrinkles"], tags=["глаза", "лифтинг", "MSS048"]),
    Product(id="jm-093", name="Hyla3D HA Lip Complex, 14 г", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=9500,
            description="Крем для губ с 3D гиалуроновым комплексом.",
            for_concerns=["hydration"], tags=["губы", "MSS049"]),
    # Шея и тело
    Product(id="jm-094", name="Juveneck, 48 г", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=11700,
            description="Омолаживающий лифтинг-крем против дряблости кожи шеи и декольте.",
            for_concerns=["wrinkles"], tags=["шея", "лифтинг", "MSS050"]),
    Product(id="jm-095", name="Bioglycolic Body Scrub, 178 мл", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=8900,
            description="Скраб для тела с двойным полирующим действием.",
            for_concerns=["texture"], tags=["тело", "скраб", "MSS051"]),
    Product(id="jm-096", name="CelluliTx, 119 г", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=16500,
            description="Высокоэффективный антицеллюлитный крем.",
            tags=["тело", "MSS052"]),
    Product(id="jm-097", name="BodyTx AHA Body Lotion, 119 мл", brand="Jan Marini",
            category=Category.SKINCARE, price_rub=10500,
            description="Восстанавливающий лосьон для тела с AHA и PHA кислотами для идеальной гладкости.",
            for_concerns=["texture"], tags=["тело", "кислоты", "MSS064"]),
]

# Автопривязка фото: если в static/products лежит <id>.jpg — товар получает фото.
# Достаточно положить файл с именем позиции (например, jm-020.jpg) — без правок кода.
_IMG_DIR = Path(__file__).resolve().parent.parent / "static" / "products"
for _p in _CATALOG:
    if _p.image is None and (_IMG_DIR / f"{_p.id}.jpg").is_file():
        _p.image = f"/static/products/{_p.id}.jpg"

_BY_ID: dict[str, Product] = {p.id: p for p in _CATALOG}


def _custom_products() -> list[Product]:
    """«Живые» товары из БД (добавлены владельцем через Telegram-бота/админку)."""
    import json as _json

    from app.db import store

    try:
        with store.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM products ORDER BY created_at DESC"
            ).fetchall()
    except Exception:  # таблицы ещё нет (старая БД до init) — каталог из кода
        return []
    items: list[Product] = []
    for r in rows:
        try:
            items.append(Product(
                id=r["id"], name=r["name"], brand=r["brand"],
                category=Category(r["category"]), price_rub=r["price_rub"],
                old_price_rub=r["old_price_rub"], description=r["description"],
                tags=_json.loads(r["tags_json"] or "[]"),
                in_stock=bool(r["in_stock"]), is_service=bool(r["is_service"]),
                hit=bool(r["hit"]), image=r["image"],
            ))
        except Exception:
            continue  # битую строку пропускаем, каталог не падает
    return items


def all_products(category: Category | None = None) -> list[Product]:
    merged = _custom_products() + list(_CATALOG)
    if category is None:
        return merged
    return [p for p in merged if p.category == category]


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
    found = _BY_ID.get(product_id)
    if found is not None:
        return found
    return next((p for p in _custom_products() if p.id == product_id), None)


# Приоритетные (профессиональные) бренды в рекомендациях после скана.
PRO_BRANDS = {"Jan Marini"}


def recommend_for_concerns(concern_keys: list[str], limit: int = 6) -> list[Product]:
    """Подобрать товары под проблемы кожи (для связки с анализом).

    Ранжирование: сначала по числу совпавших проблем, затем профессиональные
    бренды (Jan Marini) и хиты — чтобы скан продвигал реальный товар с маржой.
    """
    wanted = set(concern_keys)

    def score(p: Product) -> tuple:
        matches = len(wanted & set(p.for_concerns))
        return (matches, p.brand in PRO_BRANDS, p.hit, -p.price_rub)

    candidates = [p for p in _CATALOG if wanted & set(p.for_concerns)]
    candidates.sort(key=score, reverse=True)
    return candidates[:limit]


def categories() -> list[str]:
    return [c.value for c in Category]
