"""Каталог лаборатории: панели биомаркеров и check-up программы.

Формат «wellness», не медицина: анализы выполняют лицензированные
лаборатории-партнёры, Aura помогает выбрать панель и записаться.
Интерпретация результатов — образовательная, не диагноз (см. DISCLAIMER).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

LAB_DISCLAIMER = (
    "Анализы выполняют лицензированные лаборатории-партнёры. Aura не оказывает "
    "медицинских услуг: подбор панелей и разбор результатов носят образовательный "
    "характер и не заменяют консультацию врача."
)


class Panel(BaseModel):
    id: str
    name: str
    tagline: str = Field(..., description="Короткая подпись — для кого/зачем")
    biomarkers: list[str] = Field(..., description="Что входит в панель")
    price_rub: int = Field(..., ge=0)
    old_price_rub: int | None = None
    days: int = Field(2, description="Срок готовности, рабочих дней")
    fasting: bool = Field(True, description="Кровь сдаётся натощак")
    popular: bool = False
    category: str = Field("панель", description="панель | check-up")


PANELS: list[Panel] = [
    Panel(
        id="lab-base",
        name="Базовый чек-ап",
        tagline="Раз в год каждому: общее состояние и главные дефициты",
        biomarkers=[
            "Общий анализ крови", "Глюкоза", "Липидный профиль",
            "Витамин D (25-OH)", "Ферритин", "ТТГ",
        ],
        price_rub=4900, old_price_rub=6300, days=2, popular=True,
        category="check-up",
    ),
    Panel(
        id="lab-skin-hair",
        name="Кожа и волосы",
        tagline="Дефициты, из-за которых тускнеет кожа и выпадают волосы",
        biomarkers=[
            "Ферритин", "Цинк", "Витамин D (25-OH)", "Витамин B12",
            "ТТГ", "Общий белок",
        ],
        price_rub=5400, days=2, popular=True,
    ),
    Panel(
        id="lab-energy",
        name="Энергия и усталость",
        tagline="Когда «всё время нет сил» — ищем причину в цифрах",
        biomarkers=[
            "Ферритин", "Витамин B12", "Фолиевая кислота",
            "Витамин D (25-OH)", "ТТГ", "Кортизол (утренний)",
        ],
        price_rub=5200, days=3,
    ),
    Panel(
        id="lab-female",
        name="Женское здоровье",
        tagline="Гормональный фон: цикл, кожа, настроение",
        biomarkers=[
            "ТТГ, Т4 свободный", "Пролактин", "Эстрадиол",
            "Прогестерон", "Тестостерон общий", "ДГЭА-С", "Ферритин",
        ],
        price_rub=6900, old_price_rub=8200, days=3, popular=True,
    ),
    Panel(
        id="lab-vitamins",
        name="Витамины и минералы",
        tagline="Что реально пить из БАДов — а что у вас и так в норме",
        biomarkers=[
            "Витамин D (25-OH)", "Витамин B12", "Фолиевая кислота",
            "Ферритин", "Цинк", "Магний", "Омега-3 индекс",
        ],
        price_rub=4400, days=3,
    ),
    Panel(
        id="lab-gut",
        name="ЖКТ и пищеварение",
        tagline="Вздутие, тяжесть, непереносимости — смотрим глубже",
        biomarkers=[
            "Общий анализ крови", "СРБ", "Ферритин",
            "Панкреатическая эластаза", "Хеликобактер (IgG)", "Витамин B12",
        ],
        price_rub=5800, days=4,
    ),
    Panel(
        id="lab-sport",
        name="Спорт и восстановление",
        tagline="Для тренирующихся: ресурсы, восстановление, перетрен",
        biomarkers=[
            "Общий анализ крови", "Ферритин", "Креатинкиназа",
            "Тестостерон общий", "Кортизол", "Магний", "Витамин D (25-OH)",
        ],
        price_rub=5600, days=3,
    ),
    Panel(
        id="lab-longevity",
        name="Longevity (расширенный)",
        tagline="Углублённый чек-ап: метаболизм, воспаление, гормоны",
        biomarkers=[
            "Расширенная биохимия (14 показателей)", "Гликированный гемоглобин",
            "Инсулин + индекс HOMA", "СРБ высокочувствительный", "Гомоцистеин",
            "Липидный профиль расширенный", "Панель щитовидной железы",
            "Витамин D (25-OH)", "Ферритин",
        ],
        price_rub=12900, old_price_rub=15900, days=5,
        category="check-up",
    ),
]


def list_panels() -> list[Panel]:
    return PANELS


def get_panel(panel_id: str) -> Panel | None:
    return next((p for p in PANELS if p.id == panel_id), None)
