"""Генерация PDF-отчёта по анализу кожи и протоколу ухода.

Использует fpdf2 и встроенный шрифт DejaVu для корректной кириллицы.
"""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

from app.schemas import Protocol, SkinAnalysis

_FONT_DIR = Path(__file__).parent / "fonts"
_BRAND = (37, 99, 235)  # синий акцент
_MUTED = (110, 110, 120)


def _severity_color(score: int) -> tuple[int, int, int]:
    if score <= 33:
        return (22, 163, 74)  # зелёный
    if score <= 66:
        return (217, 119, 6)  # оранжевый
    return (220, 38, 38)  # красный


class _Report(FPDF):
    def header(self) -> None:  # noqa: D102
        self.set_font("DejaVu", "B", 16)
        self.set_text_color(*_BRAND)
        self.cell(0, 10, "derm — отчёт по анализу кожи", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*_BRAND)
        self.set_line_width(0.5)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def footer(self) -> None:  # noqa: D102
        self.set_y(-15)
        self.set_font("DejaVu", "", 7)
        self.set_text_color(*_MUTED)
        self.multi_cell(
            0,
            4,
            "Косметический анализ кожи для подбора ухода, не медицинский диагноз. "
            "Не заменяет консультацию врача-дерматолога.",
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )


def _register_fonts(pdf: FPDF) -> None:
    pdf.add_font("DejaVu", "", str(_FONT_DIR / "DejaVuSans.ttf"))
    pdf.add_font("DejaVu", "B", str(_FONT_DIR / "DejaVuSans-Bold.ttf"))


def _section(pdf: FPDF, title: str) -> None:
    pdf.ln(2)
    pdf.set_font("DejaVu", "B", 13)
    pdf.set_text_color(20, 20, 30)
    pdf.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")


def render_report(analysis: SkinAnalysis, protocol: Protocol) -> bytes:
    """Сформировать PDF-отчёт и вернуть его в виде байтов."""
    pdf = _Report(orientation="P", unit="mm", format="A4")
    _register_fonts(pdf)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # Тип кожи и резюме
    pdf.set_font("DejaVu", "B", 11)
    pdf.set_text_color(20, 20, 30)
    pdf.cell(0, 7, f"Тип кожи: {analysis.skin_type.value}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 10)
    pdf.set_text_color(60, 60, 70)
    pdf.multi_cell(0, 5, analysis.summary, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    # Проблемы кожи
    _section(pdf, "Оценка состояния кожи")
    pdf.set_font("DejaVu", "", 10)
    bar_x = pdf.l_margin + 62
    bar_w = 62
    for c in sorted(analysis.concerns, key=lambda x: x.score, reverse=True):
        y = pdf.get_y()
        pdf.set_text_color(40, 40, 50)
        pdf.cell(60, 7, c.name, new_x="LMARGIN", new_y="TOP")
        # шкала (рисуем прямоугольниками — устойчиво к ширине)
        pdf.set_fill_color(230, 230, 235)
        pdf.rect(bar_x, y + 1.5, bar_w, 4, style="F")
        pdf.set_fill_color(*_severity_color(c.score))
        pdf.rect(bar_x, y + 1.5, max(bar_w * c.score / 100, 0.5), 4, style="F")
        # подпись со счётом
        pdf.set_xy(bar_x + bar_w + 3, y)
        pdf.set_text_color(*_severity_color(c.score))
        pdf.cell(0, 7, f"{c.score}/100 ({c.severity.value})", new_x="LMARGIN", new_y="NEXT")

    # Протокол ухода
    _section(pdf, "Персональный протокол: утро")
    _render_steps(pdf, protocol.am_steps)
    _section(pdf, "Персональный протокол: вечер")
    _render_steps(pdf, protocol.pm_steps)

    if protocol.weekly:
        _section(pdf, "Раз в неделю")
        _render_bullets(pdf, protocol.weekly)
    if protocol.lifestyle:
        _section(pdf, "Образ жизни")
        _render_bullets(pdf, protocol.lifestyle)

    pdf.ln(2)
    pdf.set_font("DejaVu", "B", 10)
    pdf.set_text_color(*_BRAND)
    pdf.cell(
        0,
        7,
        f"Следующее обновление протокола: {protocol.next_review.strftime('%d.%m.%Y')}",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    out = pdf.output()
    return bytes(out)


def _render_steps(pdf: FPDF, steps) -> None:
    for i, s in enumerate(steps, 1):
        pdf.set_font("DejaVu", "B", 10)
        pdf.set_text_color(30, 30, 40)
        pdf.multi_cell(0, 5, f"{i}. {s.step}  —  {s.category}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("DejaVu", "", 9)
        pdf.set_text_color(*_MUTED)
        pdf.multi_cell(0, 5, f"    {s.why}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(0.5)


def _render_bullets(pdf: FPDF, items) -> None:
    pdf.set_font("DejaVu", "", 10)
    pdf.set_text_color(50, 50, 60)
    for item in items:
        pdf.multi_cell(0, 5, f"•  {item}", new_x="LMARGIN", new_y="NEXT")
