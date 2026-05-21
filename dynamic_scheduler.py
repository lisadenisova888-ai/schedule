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


# =========================================================
# БАЗОВЫЕ ФУНКЦИИ
# =========================================================

def normalize_schedule(schedule_data):
    lessons = deepcopy(schedule_data.get("lessons", [])) if isinstance(schedule_data, dict) else []
    unplaced = deepcopy(schedule_data.get("unplaced_lessons", [])) if isinstance(schedule_data, dict) else []

    for index, lesson in enumerate(lessons):
        lesson.setdefault("_id", f"lesson-{index}")

    return {
        "lessons": lessons,
        "unplaced_lessons": unplaced
    }


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
    return [
        item.strip()
        for item in str(value or "").split(",")
        if item.strip()
    ]


def overlaps(start_a, end_a, start_b, end_b):
    return start_a < end_b and start_b < end_a


def lesson_id(lesson):
    return str(lesson.get("_id"))


def selected_lessons(lessons, ids):
    ids = {str(item) for item in ids or []}
    return [lesson for lesson in lessons if lesson_id(lesson) in ids]


def sort_lessons(lessons):
    return sorted(
        lessons,
        key=lambda lesson: (
            DAYS.index(lesson.get(DAY_KEY)) if lesson.get(DAY_KEY) in DAYS else 99,
            parse_time_range(lesson.get(TIME_KEY))[0] or 0,
            str(lesson.get(GROUP_KEY, "")),
            str(lesson.get(SUBJECT_KEY, ""))
        )
    )


# =========================================================
# ДАННЫЕ ОБ УЧИТЕЛЯХ, ПРЕДМЕТАХ, АУДИТОРИЯХ
# =========================================================

def build_subject_maps(source_data):
    subjects = source_data.get("предметы", [])

    id_to_name = {}
    name_to_id = {}

    for subject in subjects:
        subject_id = str(subject.get("id", "")).strip()
        name = str(subject.get("название", "")).strip()

        if subject_id and name:
            id_to_name[subject_id] = name
            name_to_id[name] = subject_id

    return id_to_name, name_to_id


def build_teacher_subjects(source_data):
    id_to_name, _ = build_subject_maps(source_data)

    result = {}

    for teacher in source_data.get("преподаватели", []):
        name = str(teacher.get("ФИО", "")).strip()

        subject_ids = teacher.get("преподает предметы (id)", [])
        subject_names = set()

        for subject_id in subject_ids:
            subject_id = str(subject_id).strip()
            subject_name = id_to_name.get(subject_id)

            if subject_name:
                subject_names.add(subject_name)

        if name:
            result[name] = subject_names

    return result


def teacher_can_teach(source_data, teacher_name, subject_name):
    teacher_subjects = build_teacher_subjects(source_data)

    if teacher_name not in teacher_subjects:
        return False

    return subject_name in teacher_subjects[teacher_name]


def get_suitable_teachers(source_data, subject_name, exclude_teacher=None):
    teacher_subjects = build_teacher_subjects(source_data)

    teachers = []

    for teacher, subjects in teacher_subjects.items():
        if teacher == exclude_teacher:
            continue

        if subject_name in subjects:
            teachers.append(teacher)

    return teachers


# =========================================================
# ПРОВЕРКА КОНФЛИКТОВ
# =========================================================

def lesson_conflicts(candidate, lesson, ignore_ids=None):
    ignore_ids = set(ignore_ids or [])

    if lesson_id(lesson) in ignore_ids:
        return False

    if candidate.get(DAY_KEY) != lesson.get(DAY_KEY):
        return False

    cand_start, cand_end = parse_time_range(candidate.get(TIME_KEY))
    start, end = parse_time_range(lesson.get(TIME_KEY))

    if cand_start is None or start is None:
        return False

    if not overlaps(cand_start, cand_end, start, end):
        return False

    candidate_groups = set(split_groups(candidate.get(GROUP_KEY)))
    lesson_groups = set(split_groups(lesson.get(GROUP_KEY)))

    same_group = bool(candidate_groups & lesson_groups)

    same_teacher = (
        candidate.get(TEACHER_KEY)
        and candidate.get(TEACHER_KEY) != "-"
        and candidate.get(TEACHER_KEY) == lesson.get(TEACHER_KEY)
    )

    same_room = (
        candidate.get(ROOM_KEY)
        and candidate.get(ROOM_KEY) != "-"
        and candidate.get(ROOM_KEY) == lesson.get(ROOM_KEY)
    )

    return same_group or same_teacher or same_room


def is_slot_free(lessons, candidate, ignore_ids=None):
    ignore_ids = set(ignore_ids or [])

    for lesson in lessons:
        if lesson_conflicts(candidate, lesson, ignore_ids):
            return False

    return True


# =========================================================
# ОЦЕНКА ИЗМЕНЕНИЙ
# =========================================================

def movement_score(original_lesson, new_day, new_start):
    old_day = original_lesson.get(DAY_KEY)
    old_start, _ = parse_time_range(original_lesson.get(TIME_KEY))

    score = 0

    if old_day != new_day:
        old_day_index = DAYS.index(old_day) if old_day in DAYS else 0
        new_day_index = DAYS.index(new_day) if new_day in DAYS else 0
        score += abs(new_day_index - old_day_index) * 300

    if old_start is not None:
        score += abs(new_start - old_start)

    return score


def find_best_free_slot(lessons, source_lesson, ignore_ids=None, preferred_day=None, preferred_start=None):
    ignore_ids = set(ignore_ids or [])
    duration = lesson_duration(source_lesson)

    best_slot = None
    best_score = None

    days = [preferred_day] if preferred_day else DAYS

    for day in days:
        if day not in DAYS:
            continue

        for start in range(START_DAY, END_DAY - duration + 1, STEP_MIN):
            end = start + duration

            candidate = deepcopy(source_lesson)
            candidate[DAY_KEY] = day
            candidate[TIME_KEY] = format_time_range(start, end)

            if not is_slot_free(lessons, candidate, ignore_ids):
                continue

            score = movement_score(source_lesson, day, start)

            if preferred_start is not None:
                score += abs(start - preferred_start)

            if best_score is None or score < best_score:
                best_score = score
                best_slot = day, start, end

    return best_slot


def move_lesson_to_best_slot(lessons, lesson, extra_ignore_ids=None):
    ignore_ids = {lesson_id(lesson)}
    ignore_ids.update(extra_ignore_ids or [])

    slot = find_best_free_slot(
        lessons=lessons,
        source_lesson=lesson,
        ignore_ids=ignore_ids
    )

    if slot is None:
        return False

    day, start, end = slot

    lesson[DAY_KEY] = day
    lesson[TIME_KEY] = format_time_range(start, end)

    return True


# =========================================================
# ПОДБОР ПРЕПОДАВАТЕЛЯ
# =========================================================

def find_teacher_for_lesson(source_data, lessons, lesson, preferred_teacher=None):
    subject = str(lesson.get(SUBJECT_KEY, "")).strip()
    old_teacher = str(lesson.get(TEACHER_KEY, "")).strip()

    candidates = []

    if preferred_teacher:
        candidates.append(preferred_teacher)

    for teacher in get_suitable_teachers(source_data, subject, exclude_teacher=old_teacher):
        if teacher not in candidates:
            candidates.append(teacher)

    for teacher in candidates:
        if not teacher_can_teach(source_data, teacher, subject):
            continue

        test_lesson = deepcopy(lesson)
        test_lesson[TEACHER_KEY] = teacher

        if is_slot_free(lessons, test_lesson, ignore_ids={lesson_id(lesson)}):
            return teacher, False

    for teacher in candidates:
        if not teacher_can_teach(source_data, teacher, subject):
            continue

        test_lesson = deepcopy(lesson)
        test_lesson[TEACHER_KEY] = teacher

        slot = find_best_free_slot(
            lessons=lessons,
            source_lesson=test_lesson,
            ignore_ids={lesson_id(lesson)}
        )

        if slot is not None:
            return teacher, True

    return None, False


# =========================================================
# OPTIONS ДЛЯ САЙТА
# =========================================================

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
        return sorted({
            str(value).strip()
            for value in values
            if str(value).strip()
        })

    return {
        "teachers": unique(teachers + [lesson.get(TEACHER_KEY, "") for lesson in lessons]),
        "subjects": unique(subjects + [lesson.get(SUBJECT_KEY, "") for lesson in lessons]),
        "rooms": unique(rooms + [lesson.get(ROOM_KEY, "") for lesson in lessons]),
        "groups": unique(groups + [
            group
            for lesson in lessons
            for group in split_groups(lesson.get(GROUP_KEY))
        ]),
        "days": DAYS,
        "times": unique([lesson.get(TIME_KEY, "") for lesson in lessons]),
        "lessons": lessons
    }


# =========================================================
# 1. ЗАМЕНА ПРЕПОДАВАТЕЛЯ
# =========================================================

def apply_replace_teacher(lessons, source_data, change):
    ids = change.get("lesson_ids", [])
    preferred_teacher = str(change.get("teacher") or "").strip()

    if not ids:
        raise ValueError("Выберите занятия для изменения.")

    for lesson in selected_lessons(lessons, ids):
        subject = str(lesson.get(SUBJECT_KEY, "")).strip()

        if preferred_teacher and not teacher_can_teach(source_data, preferred_teacher, subject):
            raise ValueError(
                f"Преподаватель {preferred_teacher} не может вести предмет «{subject}»."
            )

        teacher, need_move = find_teacher_for_lesson(
            source_data=source_data,
            lessons=lessons,
            lesson=lesson,
            preferred_teacher=preferred_teacher or None
        )

        if not teacher:
            raise ValueError(
                f"Не найден подходящий преподаватель для предмета «{subject}»."
            )

        lesson[TEACHER_KEY] = teacher

        if need_move:
            moved = move_lesson_to_best_slot(lessons, lesson)

            if not moved:
                raise ValueError(
                    f"Преподаватель найден, но свободный слот для занятия «{subject}» не найден."
                )


# =========================================================
# 2. УБРАТЬ ЗАНЯТИЕ
# =========================================================

def apply_remove_lesson(result, lessons, change):
    ids = {str(item) for item in change.get("lesson_ids", [])}
    mode = change.get("mode")

    if not ids:
        raise ValueError("Выберите занятия для изменения.")

    if mode == "move":
        for lesson in selected_lessons(lessons, ids):
            moved = move_lesson_to_best_slot(lessons, lesson)

            if not moved:
                raise ValueError(
                    f"Не удалось перенести занятие «{lesson.get(SUBJECT_KEY)}»."
                )

        return lessons

    lessons = [
        lesson
        for lesson in lessons
        if lesson_id(lesson) not in ids
    ]

    result["lessons"] = lessons
    return lessons


# =========================================================
# 3. ЗАМЕНИТЬ ПРЕДМЕТ
# =========================================================

def apply_replace_lesson(lessons, source_data, change):
    ids = change.get("lesson_ids", [])

    new_subject = str(change.get("subject") or "").strip()
    new_teacher = str(change.get("teacher") or "").strip()
    new_room = str(change.get("room") or "").strip()

    if not ids:
        raise ValueError("Выберите занятия для изменения.")

    if not new_subject:
        raise ValueError("Укажите новый предмет.")

    for lesson in selected_lessons(lessons, ids):
        lesson[SUBJECT_KEY] = new_subject

        if new_room:
            lesson[ROOM_KEY] = new_room

        if new_teacher:
            if not teacher_can_teach(source_data, new_teacher, new_subject):
                raise ValueError(
                    f"Преподаватель {new_teacher} не может вести предмет «{new_subject}»."
                )

            lesson[TEACHER_KEY] = new_teacher
        else:
            teacher, need_move = find_teacher_for_lesson(
                source_data=source_data,
                lessons=lessons,
                lesson=lesson
            )

            if not teacher:
                raise ValueError(
                    f"Не найден преподаватель для предмета «{new_subject}»."
                )

            lesson[TEACHER_KEY] = teacher

        if not is_slot_free(lessons, lesson, ignore_ids={lesson_id(lesson)}):
            moved = move_lesson_to_best_slot(lessons, lesson)

            if not moved:
                raise ValueError(
                    f"Не удалось найти свободный слот для нового предмета «{new_subject}»."
                )


# =========================================================
# 4. ДОБАВИТЬ ОКНО
# =========================================================

def apply_add_window(lessons, change):
    day = str(change.get("day") or "").strip()
    time_range = str(change.get("time") or "").strip()
    group = str(change.get("group") or "").strip()

    if not day or not time_range or not group:
        raise ValueError("Укажите день, время и группу для окна.")

    start, end = parse_time_range(time_range)

    if start is None:
        raise ValueError("Время должно быть в формате 09:00 или 09:00 – 10:30.")

    window = {
        "_id": f"window-{datetime.utcnow().timestamp()}",
        ROOM_KEY: "-",
        TEACHER_KEY: "-",
        SUBJECT_KEY: "Окно",
        TYPE_KEY: "Окно",
        GROUP_KEY: group,
        DAY_KEY: day,
        TIME_KEY: format_time_range(start, end)
    }

    conflicting_lessons = []

    for lesson in lessons:
        if lesson.get(DAY_KEY) != day:
            continue

        lesson_start, lesson_end = parse_time_range(lesson.get(TIME_KEY))

        if lesson_start is None:
            continue

        same_group = group in split_groups(lesson.get(GROUP_KEY))

        if same_group and overlaps(start, end, lesson_start, lesson_end):
            conflicting_lessons.append(lesson)

    for lesson in conflicting_lessons:
        moved = move_lesson_to_best_slot(
            lessons=lessons,
            lesson=lesson,
            extra_ignore_ids={lesson_id(item) for item in conflicting_lessons}
        )

        if not moved:
            raise ValueError(
                f"Не удалось освободить место для окна. Не переносится занятие «{lesson.get(SUBJECT_KEY)}»."
            )

    if not is_slot_free(lessons, window):
        raise ValueError("Не удалось добавить окно: выбранный слот всё ещё занят.")

    lessons.append(window)


# =========================================================
# ГЛАВНАЯ ФУНКЦИЯ
# =========================================================

def apply_dynamic_change(schedule_data, source_data, change):
    result = normalize_schedule(schedule_data)

    lessons = result["lessons"]
    action = change.get("action")

    if action == "replace_teacher":
        apply_replace_teacher(lessons, source_data, change)

    elif action == "remove_lesson":
        lessons = apply_remove_lesson(result, lessons, change)

    elif action == "replace_lesson":
        apply_replace_lesson(lessons, source_data, change)

    elif action == "add_window":
        apply_add_window(lessons, change)

    else:
        raise ValueError("Выберите тип изменения расписания.")

    result["lessons"] = sort_lessons(lessons)

    return result