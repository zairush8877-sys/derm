"""Движок генерации персонального протокола ухода.

По результату анализа кожи (+ опциональные ответы квиза) строит протокол
утро/вечер. Используется детерминированная экспертная логика на основе топовых
проблем — это надёжный fallback, который работает без обращения к LLM.
"""

from __future__ import annotations

from datetime import timedelta

from app.protocol.quiz import QuizAnswers
from app.schemas import Protocol, ProtocolStep, SkinAnalysis, SkinType

# Рекомендации по категориям средств под каждую проблему кожи.
_CONCERN_PLAYBOOK: dict[str, dict[str, ProtocolStep]] = {
    "acne": {
        "pm": ProtocolStep(
            step="Точечно средство с салициловой кислотой (BHA)",
            category="Кислотный уход / BHA",
            why="Очищает поры и снижает количество высыпаний",
        ),
    },
    "redness": {
        "am": ProtocolStep(
            step="Успокаивающая сыворотка с центеллой/ниацинамидом",
            category="Успокаивающий уход",
            why="Уменьшает покраснения и укрепляет барьер кожи",
        ),
    },
    "pigmentation": {
        "am": ProtocolStep(
            step="Сыворотка с витамином C",
            category="Антиоксидант / осветление",
            why="Выравнивает тон и работает с пигментацией",
        ),
    },
    "wrinkles": {
        "pm": ProtocolStep(
            step="Ретиноид (начать с низкой концентрации)",
            category="Anti-age / ретиноиды",
            why="Стимулирует обновление кожи и разглаживает морщины",
        ),
    },
    "hydration": {
        "pm": ProtocolStep(
            step="Сыворотка с гиалуроновой кислотой + плотный крем",
            category="Увлажнение",
            why="Восстанавливает уровень влаги и комфорт кожи",
        ),
    },
    "pores": {
        "pm": ProtocolStep(
            step="Ниацинамид 5-10%",
            category="Себорегуляция",
            why="Визуально сужает поры и нормализует себум",
        ),
    },
    "oiliness": {
        "am": ProtocolStep(
            step="Лёгкий гель-увлажнитель, без масел",
            category="Себорегуляция",
            why="Увлажняет без перегрузки жирной кожи",
        ),
    },
    "dark_circles": {
        "am": ProtocolStep(
            step="Крем для век с кофеином/витамином K",
            category="Уход за зоной вокруг глаз",
            why="Снижает выраженность тёмных кругов и отёчности",
        ),
    },
    "texture": {
        "pm": ProtocolStep(
            step="Мягкий пилинг с AHA 1-2 раза в неделю",
            category="Эксфолиация / AHA",
            why="Сглаживает рельеф и улучшает текстуру кожи",
        ),
    },
}


def _base_cleanser(skin_type: SkinType) -> ProtocolStep:
    if skin_type in {SkinType.OILY, SkinType.COMBINATION}:
        cat = "Очищение (гель)"
    elif skin_type == SkinType.DRY:
        cat = "Очищение (мягкое, кремовое)"
    else:
        cat = "Очищение (деликатное)"
    return ProtocolStep(step="Умывание", category=cat, why="Базовый шаг — очищение кожи утром и вечером")


def build_protocol(analysis: SkinAnalysis, quiz: QuizAnswers | None = None) -> Protocol:
    """Построить протокол утро/вечер из анализа и (опционально) квиза."""
    quiz = quiz or QuizAnswers()

    top_concerns = sorted(analysis.concerns, key=lambda c: c.score, reverse=True)
    active_keys = [c.key for c in top_concerns if c.score >= 34][:4]

    am: list[ProtocolStep] = [_base_cleanser(analysis.skin_type)]
    pm: list[ProtocolStep] = [_base_cleanser(analysis.skin_type)]

    for key in active_keys:
        play = _CONCERN_PLAYBOOK.get(key, {})
        if "am" in play:
            am.append(play["am"])
        if "pm" in play:
            step = play["pm"]
            # Беременность/ГВ: исключаем ретиноиды и сильные кислоты.
            if quiz.pregnant and key in {"wrinkles", "texture", "acne"}:
                continue
            pm.append(step)

    # Увлажнение и SPF — обязательная база.
    am.append(ProtocolStep(step="Увлажняющий крем", category="Увлажнение", why="Поддерживает барьер кожи"))
    am.append(
        ProtocolStep(
            step="Солнцезащита SPF 30+",
            category="Защита от солнца",
            why="Главный анти-возрастной шаг и защита от пигментации",
        )
    )
    pm.append(ProtocolStep(step="Ночной крем", category="Увлажнение", why="Восстановление кожи во время сна"))

    weekly = ["Маска под тип кожи 1-2 раза в неделю"]
    if "texture" in active_keys or "pores" in active_keys:
        weekly.append("Мягкий пилинг (AHA/BHA) 1-2 раза в неделю — не совмещать с ретиноидом в один вечер")

    lifestyle = [
        "Пить достаточно воды и высыпаться",
        "Не трогать лицо руками и менять наволочку 1-2 раза в неделю",
    ]
    if quiz.sun_exposure == "высокая":
        lifestyle.append("Обновлять SPF каждые 2-3 часа на солнце")
    if quiz.sensitivity or analysis.skin_type == SkinType.SENSITIVE:
        lifestyle.append("Вводить активы постепенно — по одному новому средству за раз")

    return Protocol(
        am_steps=am,
        pm_steps=pm,
        weekly=weekly,
        lifestyle=lifestyle,
        next_review=analysis.created_at + timedelta(days=30),
    )
