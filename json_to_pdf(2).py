"""Экспорт готового расписания JSON в PDF.

Файл вынесен из функции export_schedule_pdf в app.py исходной сборки.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


DEFAULT_INPUT_FILE = Path("schedule.json")
DEFAULT_OUTPUT_FILE = Path("schedule_export.pdf")

DAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"]
LESSON_HEADERS = [
    "день_недели",
    "время",
    "группа",
    "предмет",
    "тип",
    "преподаватель",
    "аудитория",
]


def load_schedule(input_path):
    with open(input_path, "r", encoding="utf-8") as file:
        return json.load(file)


def lessons_by_group(schedule_data):
    lessons = schedule_data.get("lessons", []) if isinstance(schedule_data, dict) else []
    groups = defaultdict(list)

    for lesson in lessons:
        raw_groups = str(lesson.get("группа", "")).split(",")
        for group in [group.strip() for group in raw_groups if group.strip()]:
            groups[group].append(lesson)

    return dict(sorted(groups.items(), key=lambda item: item[0]))


def sorted_lessons(lessons):
    day_index = {day: index for index, day in enumerate(DAYS)}
    return sorted(
        lessons,
        key=lambda item: (
            day_index.get(item.get("день_недели", ""), 99),
            str(item.get("время", "")),
        ),
    )


def detect_font():
    font_name = "Helvetica"

    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]

    for candidate in candidates:
        if Path(candidate).exists():
            pdfmetrics.registerFont(TTFont("LocalSans", candidate))
            font_name = "LocalSans"
            break

    return font_name


def export_schedule_pdf(schedule_data, output_path):
    font_name = detect_font()

    document = SimpleDocTemplate(
        str(output_path),
        pagesize=landscape(A4),
        leftMargin=18,
        rightMargin=18,
        topMargin=18,
        bottomMargin=18,
    )

    styles = getSampleStyleSheet()
    styles["Title"].fontName = font_name
    styles["Normal"].fontName = font_name

    story = []

    def add_table(title, lessons):
        story.append(Paragraph(title, styles["Title"]))
        story.append(Spacer(1, 10))

        rows = [[
            "День недели",
            "Время",
            "Группа",
            "Предмет",
            "Тип",
            "Преподаватель",
            "Аудитория",
        ]]

        for lesson in sorted_lessons(lessons):
            rows.append([str(lesson.get(key, "")) for key in LESSON_HEADERS])

        table = Table(
            rows,
            repeatRows=1,
            colWidths=[78, 70, 72, 180, 70, 170, 70],
        )

        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
        ]))

        story.append(table)

    add_table("Общее расписание", schedule_data.get("lessons", []))

    for group, group_lessons in lessons_by_group(schedule_data).items():
        story.append(PageBreak())
        add_table(f"Группа {group}", group_lessons)

    document.build(story)


def convert_json_to_pdf(input_file=DEFAULT_INPUT_FILE, output_file=DEFAULT_OUTPUT_FILE):
    input_file = Path(input_file)
    output_file = Path(output_file)

    schedule_data = load_schedule(input_file)
    export_schedule_pdf(schedule_data, output_file)

    return output_file, len(schedule_data.get("lessons", []))


def parse_args():
    parser = argparse.ArgumentParser(
        description="Конвертирует готовое расписание schedule.json в PDF."
    )
    parser.add_argument("input", nargs="?", default=str(DEFAULT_INPUT_FILE))
    parser.add_argument("output", nargs="?", default=str(DEFAULT_OUTPUT_FILE))
    return parser.parse_args()


def main():
    args = parse_args()
    output_file, lesson_count = convert_json_to_pdf(args.input, args.output)
    print(f"PDF создан: {output_file}")
    print(f"Занятий экспортировано: {lesson_count}")


if __name__ == "__main__":
    main()
