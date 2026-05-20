import re
from copy import deepcopy
from datetime import datetime


DAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"]
START_DAY = 9 * 60
END_DAY = 18 * 60
STEP_MIN = 15
DEFAULT_DURATION = 90

DAY_KEY = "день_недели"
TIME_KEY = "время"
GROUP_KEY = "группа"
SUBJECT_KEY = "предмет"
TYPE_KEY = "тип"
TEACHER_KEY = "преподаватель"
ROOM_KEY = "аудитория"


def lesson_id(index, lesson):
    return str(lesson.get("_id") or f"lesson-{index}")


def normalize_schedule(schedule_data):
    lessons = deepcopy(schedule_data.get("lessons", [])) if isinstance(schedule_data, dict) else []
    for index, lesson in enumerate(lessons):
        lesson.setdefault("_id", f"lesson-{index}")
    return {"lessons": lessons, "unplaced_lessons": deepcopy(schedule_data.get("unplaced_lessons", []))}


def parse_time_range(value):
    text = str(value or "")
    parts = re.findall(r"(\d{1,2}):(\d{2})", text)
    if not parts:
        return None, None
    start = int(parts[0][0]) * 60 + int(parts[0][1])
    if len(parts) > 1:
        end = int(parts[1][0]) * 60 + int(parts[1][1])
    else:
        end = start + DEFAULT_DURATION
    return start, end


def format_time_range(start, end):
    return f"{start // 60:02d}:{start % 60:02d} – {end // 60:02d}:{end % 60:02d}"


def lesson_duration(lesson):
    start, end = parse_time_range(lesson.get(TIME_KEY))
    if start is None or end is None or end <= start:
        return DEFAULT_DURATION
    return end - start


def split_groups(value):
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def overlaps(start_a, end_a, start_b, end_b):
    return start_a < end_b and start_b < end_a


def lesson_conflicts(candidate, lesson, ignore_ids):
    if lesson_id(0, lesson) in ignore_ids:
        return False
    if candidate.get(DAY_KEY) != lesson.get(DAY_KEY):
        return False

    cand_start, cand_end = parse_time_range(candidate.get(TIME_KEY))
    start, end = parse_time_range(lesson.get(TIME_KEY))
    if cand_start is None or start is None or not overlaps(cand_start, cand_end, start, end):
        return False

    cand_groups = set(split_groups(candidate.get(GROUP_KEY)))
    groups = set(split_groups(lesson.get(GROUP_KEY)))
    same_group = bool(cand_groups & groups)
    same_teacher = candidate.get(TEACHER_KEY) and candidate.get(TEACHER_KEY) == lesson.get(TEACHER_KEY)
    same_room = candidate.get(ROOM_KEY) and candidate.get(ROOM_KEY) == lesson.get(ROOM_KEY)
    return same_group or same_teacher or same_room


def find_free_slot(lessons, source_lesson, ignore_ids=None, preferred_day=None, preferred_start=None):
    ignore_ids = set(ignore_ids or [])
    duration = lesson_duration(source_lesson)
    days = [preferred_day] if preferred_day else DAYS
    starts = [preferred_start] if preferred_start is not None else range(START_DAY, END_DAY - duration + 1, STEP_MIN)

    for day in days:
        if day not in DAYS:
            continue
        for start in starts:
            end = start + duration
            candidate = deepcopy(source_lesson)
            candidate[DAY_KEY] = day
            candidate[TIME_KEY] = format_time_range(start, end)
            if all(not lesson_conflicts(candidate, lesson, ignore_ids) for lesson in lessons):
                return day, start, end
    return None


def extract_options(source_data, schedule_data):
    schedule = normalize_schedule(schedule_data)
    lessons = schedule["lessons"]
    teachers = []
    subjects = []
    rooms = []
    groups = []

    for teacher in source_data.get("преподаватели", []):
        name = teacher.get("ФИО")
        if name:
            teachers.append(name)
    for subject in source_data.get("предметы", []):
        name = subject.get("название")
        if name:
            subjects.append(name)
    for room in source_data.get("аудитории", []):
        number = room.get("номер")
        if number not in (None, ""):
            rooms.append(str(number))
    for group in source_data.get("группы", []):
        number = group.get("номер")
        if number not in (None, ""):
            groups.append(str(number))

    def unique(values):
        return sorted({str(value).strip() for value in values if str(value).strip()})

    return {
        "teachers": unique(teachers + [lesson.get(TEACHER_KEY, "") for lesson in lessons]),
        "subjects": unique(subjects + [lesson.get(SUBJECT_KEY, "") for lesson in lessons]),
        "rooms": unique(rooms + [lesson.get(ROOM_KEY, "") for lesson in lessons]),
        "groups": unique(groups + [group for lesson in lessons for group in split_groups(lesson.get(GROUP_KEY))]),
        "days": DAYS,
        "times": unique([lesson.get(TIME_KEY, "") for lesson in lessons]),
        "lessons": lessons,
    }


def selected_lessons(lessons, ids):
    ids = {str(item) for item in ids or []}
    return [lesson for lesson in lessons if str(lesson.get("_id")) in ids]


def apply_dynamic_change(schedule_data, source_data, change):
    result = normalize_schedule(schedule_data)
    lessons = result["lessons"]
    action = change.get("action")
    ids = {str(item) for item in change.get("lesson_ids", [])}

    if action == "replace_teacher":
        new_teacher = str(change.get("teacher") or "").strip()
        if not new_teacher:
            raise ValueError("Выберите нового преподавателя.")
        for lesson in selected_lessons(lessons, ids):
            lesson[TEACHER_KEY] = new_teacher

    elif action == "remove_lesson":
        mode = change.get("mode")
        if not ids:
            raise ValueError("Выберите занятия для изменения.")
        if mode == "move":
            for lesson in selected_lessons(lessons, ids):
                slot = find_free_slot(lessons, lesson, ignore_ids={str(lesson.get("_id"))})
                if slot is None:
                    raise ValueError(f"Не удалось найти свободное время для занятия {lesson.get(SUBJECT_KEY)}.")
                day, start, end = slot
                lesson[DAY_KEY] = day
                lesson[TIME_KEY] = format_time_range(start, end)
        else:
            lessons = [lesson for lesson in lessons if str(lesson.get("_id")) not in ids]
            result["lessons"] = lessons

    elif action == "replace_lesson":
        subject = str(change.get("subject") or "").strip()
        teacher = str(change.get("teacher") or "").strip()
        room = str(change.get("room") or "").strip()
        if not subject:
            raise ValueError("Укажите, на что заменить занятие.")
        for lesson in selected_lessons(lessons, ids):
            lesson[SUBJECT_KEY] = subject
            if teacher:
                lesson[TEACHER_KEY] = teacher
            if room:
                lesson[ROOM_KEY] = room

    elif action == "add_window":
        day = str(change.get("day") or "").strip()
        time_range = str(change.get("time") or "").strip()
        group = str(change.get("group") or "").strip()
        if not day or not time_range or not group:
            raise ValueError("Укажите день, время и группу для окна.")
        start, end = parse_time_range(time_range)
        if start is None:
            raise ValueError("Время должно быть в формате 09:00 или 09:00 – 10:30.")
        candidate = {
            "_id": f"window-{datetime.utcnow().timestamp()}",
            ROOM_KEY: "-",
            TEACHER_KEY: "-",
            SUBJECT_KEY: "Окно",
            TYPE_KEY: "Окно",
            GROUP_KEY: group,
            DAY_KEY: day,
            TIME_KEY: format_time_range(start, end),
        }
        slot = find_free_slot(lessons, candidate, preferred_day=day, preferred_start=start)
        if slot is None:
            raise ValueError("В выбранное время у группы уже есть занятие.")
        lessons.append(candidate)

    else:
        raise ValueError("Выберите тип изменения расписания.")

    result["lessons"] = sorted(
        lessons,
        key=lambda lesson: (
            DAYS.index(lesson.get(DAY_KEY)) if lesson.get(DAY_KEY) in DAYS else 99,
            parse_time_range(lesson.get(TIME_KEY))[0] or 0,
            str(lesson.get(GROUP_KEY, "")),
        ),
    )
    return result
