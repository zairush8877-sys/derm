"""CLI для derm: анализ кожи из терминала.

Примеры:
    python -m app.cli analyze face.jpg
    python -m app.cli analyze face.jpg --pdf report.pdf --age 32
    python -m app.cli serve --port 8000
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app import __version__


def _cmd_analyze(args: argparse.Namespace) -> int:
    from app.analysis.engine import analyze_image
    from app.protocol.engine import build_protocol
    from app.protocol.quiz import QuizAnswers

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Файл не найден: {image_path}", file=sys.stderr)
        return 1

    data = image_path.read_bytes()
    analysis = analyze_image(data)
    quiz = QuizAnswers(age=args.age, sensitivity=args.sensitivity, pregnant=args.pregnant)
    protocol = build_protocol(analysis, quiz)

    if args.json:
        print(json.dumps(
            {"analysis": analysis.model_dump(mode="json"), "protocol": protocol.model_dump(mode="json")},
            ensure_ascii=False, indent=2,
        ))
    else:
        print(f"Тип кожи: {analysis.skin_type.value}")
        print(f"Резюме: {analysis.summary}\n")
        print("Проблемы кожи (0–100, ниже — лучше):")
        for c in sorted(analysis.concerns, key=lambda x: x.score, reverse=True):
            print(f"  • {c.name:<24} {c.score:>3}/100  ({c.severity.value})")
        print("\nУтренний уход:")
        for i, s in enumerate(protocol.am_steps, 1):
            print(f"  {i}. {s.step} — {s.category}")
        print("Вечерний уход:")
        for i, s in enumerate(protocol.pm_steps, 1):
            print(f"  {i}. {s.step} — {s.category}")

    if args.pdf:
        from app.report.pdf import render_report

        Path(args.pdf).write_bytes(render_report(analysis, protocol))
        print(f"\nPDF-отчёт сохранён: {args.pdf}")

    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.reload)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="derm", description="derm — AI-анализ кожи (CLI)")
    parser.add_argument("--version", action="version", version=f"derm {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_an = sub.add_parser("analyze", help="Проанализировать фото кожи")
    p_an.add_argument("image", help="Путь к фото лица")
    p_an.add_argument("--pdf", help="Сохранить PDF-отчёт по пути")
    p_an.add_argument("--json", action="store_true", help="Вывести результат в JSON")
    p_an.add_argument("--age", type=int, default=None, help="Возраст (для протокола)")
    p_an.add_argument("--sensitivity", action="store_true", help="Чувствительная кожа")
    p_an.add_argument("--pregnant", action="store_true", help="Беременность/ГВ")
    p_an.set_defaults(func=_cmd_analyze)

    p_sv = sub.add_parser("serve", help="Запустить веб-сервер")
    p_sv.add_argument("--host", default="0.0.0.0")
    p_sv.add_argument("--port", type=int, default=8000)
    p_sv.add_argument("--reload", action="store_true")
    p_sv.set_defaults(func=_cmd_serve)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
