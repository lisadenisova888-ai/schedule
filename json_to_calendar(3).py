import argparse
import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path


DEFAULT_INPUT_FILE = Path("schedule.json")
DEFAULT_OUTPUT_FILE = Path("schedule.ics")
DEFAULT_TIMEZONE = "Asia/Novosibirsk"

WEEKDAY_OFFSETS = {
    "понедельник": 0,
    "вторник": 1,
    "среда": 2,
    "четверг": 3,
    "пятница": 4,
    "суббота": 5,
    "воскресенье": 6,
}


def next_monday(today=None):
    today = today or date.today()
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        return today
    return today + timedelta(days=days_until_monday)


def parse_date(value):
    if not value:
        return next_monday()
    return datetime.strptime(value, "%Y-%m-%d").date()


def parse_time_range(value):
    normalized = str(value).replace("—", "–").replace("-", "–")
    parts = [part.strip() for part in normalized.split("–")]
    if len(parts) != 2:
        raise ValueError(f"Некорректный формат времени: {value}")

    start_time = datetime.strptime(parts[0], "%H:%M").time()
    end_time = datetime.strptime(parts[1], "%H:%M").time()
    return start_time, end_time


def escape_ics_text(value):
    text = "" if value is None else str(value)
    text = text.replace("\\", "\\\\")
    text = text.replace(";", "\\;")
    text = text.replace(",", "\\,")
    text = text.replace("\r\n", "\\n").replace("\n", "\\n")
    return text


def fold_ics_line(line, limit=75):
    encoded = line.encode("utf-8")
    if len(encoded) <= limit:
        return line

    result = []
    current = ""
    current_length = 0

    for char in line:
        char_length = len(char.encode("utf-8"))
        if current and current_length + char_length > limit:
            result.append(current)
            current = " " + char
            current_length = 1 + char_length
        else:
            current += char
            current_length += char_length

    if current:
        result.append(current)
    return "\r\n".join(result)


def make_uid(lesson, event_start):
    raw = "|".join([
        str(event_start),
        str(lesson.get("день_недели", "")),
        str(lesson.get("время", "")),
        str(lesson.get("группа", "")),
        str(lesson.get("предмет", "")),
        str(lesson.get("преподаватель", "")),
        str(lesson.get("аудитория", "")),
    ])
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()
    return f"{digest}@schedule-project"


def format_ics_datetime(value, timezone):
    return f"TZID={timezone}:{value.strftime('%Y%m%dT%H%M%S')}"


def lesson_to_event(lesson, week_start, timezone, repeat_weeks=1):
    day_name = str(lesson.get("день_недели", "")).strip().lower()
    if day_name not in WEEKDAY_OFFSETS:
        raise ValueError(f"Неизвестный день недели: {lesson.get('день_недели')}")

    start_time, end_time = parse_time_range(lesson.get("время", ""))
    event_date = week_start + timedelta(days=WEEKDAY_OFFSETS[day_name])
    event_start = datetime.combine(event_date, start_time)
    event_end = datetime.combine(event_date, end_time)

    if event_end <= event_start:
        event_end += timedelta(days=1)

    subject = lesson.get("предмет", "")
    lesson_type = lesson.get("тип", "")
    group = lesson.get("группа", "")
    teacher = lesson.get("преподаватель", "")
    auditorium = lesson.get("аудитория", "")

    summary = f"{lesson_type}: {subject} | группа {group}"
    description = (
        f"Предмет: {subject}\\n"
        f"Тип занятия: {lesson_type}\\n"
        f"Группа: {group}\\n"
        f"Преподаватель: {teacher}\\n"
        f"Аудитория: {auditorium}"
    )

    lines = [
        "BEGIN:VEVENT",
        f"UID:{make_uid(lesson, event_start)}",
        f"DTSTAMP:{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        f"DTSTART;{format_ics_datetime(event_start, timezone)}",
        f"DTEND;{format_ics_datetime(event_end, timezone)}",
        f"SUMMARY:{escape_ics_text(summary)}",
        f"DESCRIPTION:{escape_ics_text(description)}",
        f"LOCATION:{escape_ics_text(auditorium)}",
    ]

    if repeat_weeks > 1:
        lines.append(f"RRULE:FREQ=WEEKLY;COUNT={repeat_weeks}")

    lines.append("END:VEVENT")
    return lines


def load_lessons(input_file):
    with open(input_file, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data.get("lessons", [])


def convert_json_to_calendar(
    input_file=DEFAULT_INPUT_FILE,
    output_file=DEFAULT_OUTPUT_FILE,
    week_start=None,
    timezone=DEFAULT_TIMEZONE,
    repeat_weeks=1,
):
    input_file = Path(input_file)
    output_file = Path(output_file)
    week_start = parse_date(week_start)
    lessons = load_lessons(input_file)

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Schedule Project//Schedule Calendar//RU",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Учебное расписание",
        f"X-WR-TIMEZONE:{timezone}",
    ]

    for lesson in lessons:
        lines.extend(lesson_to_event(lesson, week_start, timezone, repeat_weeks))

    lines.append("END:VCALENDAR")

    content = "\r\n".join(fold_ics_line(line) for line in lines) + "\r\n"
    output_file.write_text(content, encoding="utf-8", newline="")
    return output_file, len(lessons), week_start


def parse_args():
    parser = argparse.ArgumentParser(
        description="Конвертирует готовое расписание schedule.json в календарь .ics."
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=str(DEFAULT_INPUT_FILE),
        help=f"JSON-файл готового расписания. По умолчанию: {DEFAULT_INPUT_FILE}",
    )
    parser.add_argument(
        "output",
        nargs="?",
        default=str(DEFAULT_OUTPUT_FILE),
        help=f"ICS-файл для календаря. По умолчанию: {DEFAULT_OUTPUT_FILE}",
    )
    parser.add_argument(
        "--week-start",
        default=None,
        help="Дата понедельника учебной недели в формате YYYY-MM-DD. Если не указана, берется ближайший понедельник.",
    )
    parser.add_argument(
        "--timezone",
        default=DEFAULT_TIMEZONE,
        help=f"Часовой пояс календаря. По умолчанию: {DEFAULT_TIMEZONE}",
    )
    parser.add_argument(
        "--repeat-weeks",
        type=int,
        default=1,
        help="Сколько недель повторять каждое занятие. По умолчанию: 1, без повторов.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    output_file, lesson_count, week_start = convert_json_to_calendar(
        input_file=args.input,
        output_file=args.output,
        week_start=args.week_start,
        timezone=args.timezone,
        repeat_weeks=args.repeat_weeks,
    )
    print(f"Календарь создан: {output_file}")
    print(f"Занятий добавлено: {lesson_count}")
    print(f"Понедельник учебной недели: {week_start}")


if __name__ == "__main__":
    main()
