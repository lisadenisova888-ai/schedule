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


def normalize_text(value):
    return str(value or "").strip()


def normalize_key(value):
    return normalize_text(value).lower().replace("ё", "е")


def normalize_lesson_type(value):
    text = normalize_key(value)

    if text in {"1", "лекция", "lecture"}:
        return "лекция"

    if text in {"0", "семинар", "seminar"}:
        return "семинар"

    return text


def normalize_schedule(schedule_data):
    lessons = deepcopy(schedule_data.get("lessons", [])) if isinstance(schedule_data, dict) else []
    unplaced = deepcopy(schedule_data.get("unplaced_lessons", [])) if isinstance(schedule_data, dict) else []

    for index, lesson in enumerate(lessons):
        lesson.setdefault("_id", f"lesson-{index}")

    return {
        "lessons": lessons,
        "unplaced_lessons": unplaced
    }


def lesson_id(lesson):
    return str(lesson.get("_id"))


def selected_lessons(lessons, ids):
    ids = {str(item) for item in ids or []}

    return [
        lesson
        for lesson in lessons
        if lesson_id(lesson) in ids
    ]


def split_groups(value):
    return [
        item.strip()
        for item in str(value or "").split(",")
        if item.strip()
    ]


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


def lesson_duration(lesson, source_data=None):
    start, end = parse_time_range(lesson.get(TIME_KEY))

    if start is not None and end is not None and end > start:
        return end - start

    subject = find_subject_for_lesson(source_data, lesson) if source_data else None

    if subject:
        return int(subject.get("длительность") or DEFAULT_DURATION)

    return DEFAULT_DURATION


def overlaps(start_a, end_a, start_b, end_b):
    return start_a < end_b and start_b < end_a


def subject_signature(name, lesson_type):
    return f"{normalize_key(name)} ({normalize_lesson_type(lesson_type)})"


def build_subject_index(source_data):
    result = {}

    for subject in source_data.get("предметы", []):
        key = subject_signature(
            subject.get("название"),
            subject.get("тип занятия")
        )

        result[key] = subject

    return result


def find_subject_for_lesson(source_data, lesson):
    if not source_data:
        return None

    subject_index = build_subject_index(source_data)

    key = subject_signature(
        lesson.get(SUBJECT_KEY),
        lesson.get(TYPE_KEY)
    )

    return subject_index.get(key)


def subject_id_for_lesson(source_data, lesson):
    subject = find_subject_for_lesson(source_data, lesson)

    if not subject:
        return None

    return subject.get("id")


def teacher_can_teach_lesson(source_data, teacher_name, lesson):
    teacher_name = normalize_text(teacher_name)
    subject_id = subject_id_for_lesson(source_data, lesson)

    if subject_id is None:
        return False

    for teacher in source_data.get("преподаватели", []):
        if normalize_text(teacher.get("ФИО")) != teacher_name:
            continue

        return subject_id in teacher.get("преподает предметы (id)", [])

    return False


def get_suitable_teachers_for_lesson(source_data, lesson, exclude_teacher=None):
    subject_id = subject_id_for_lesson(source_data, lesson)

    if subject_id is None:
        return []

    result = []

    for teacher in source_data.get("преподаватели", []):
        name = normalize_text(teacher.get("ФИО"))

        if not name:
            continue

        if exclude_teacher and name == exclude_teacher:
            continue

        if subject_id in teacher.get("преподает предметы (id)", []):
            result.append(name)

    return result


def room_number(room):
    return str(room.get("номер", "")).strip()


def group_size(source_data, group_value):
    groups = split_groups(group_value)
    total = 0

    for group in source_data.get("группы", []):
        if str(group.get("номер")) in groups:
            total += int(group.get("кол-во человек") or 0)

    return total


def room_is_suitable(source_data, room_number_value, lesson):
    room_number_value = str(room_number_value).strip()

    if room_number_value in {"", "-"}:
        return True

    subject = find_subject_for_lesson(source_data, lesson)

    for room in source_data.get("аудитории", []):
        if room_number(room) != room_number_value:
            continue

        needed_size = group_size(source_data, lesson.get(GROUP_KEY))

        if int(room.get("вместимость") or 0) < needed_size:
            return False

        if subject:
            room_types = set(room.get("тип аудитории", []))
            needs = set(subject.get("дополнительны условия", []))

            needs.discard("-")

            if needs and not needs.issubset(room_types):
                return False

        return True

    return False


def suitable_rooms(source_data, lesson):
    result = []

    for room in source_data.get("аудитории", []):
        number = room_number(room)

        if room_is_suitable(source_data, number, lesson):
            result.append(number)

    return result


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


def get_conflicts(lessons, candidate, ignore_ids=None):
    return [
        lesson
        for lesson in lessons
        if lesson_conflicts(candidate, lesson, ignore_ids)
    ]


def is_slot_free(lessons, candidate, ignore_ids=None):
    return not get_conflicts(lessons, candidate, ignore_ids)



def movement_score(original_lesson, new_day, new_start):
    old_day = original_lesson.get(DAY_KEY)
    old_start, _ = parse_time_range(original_lesson.get(TIME_KEY))

    score = 0

    if old_day != new_day:
        old_day_index = DAYS.index(old_day) if old_day in DAYS else 0
        new_day_index = DAYS.index(new_day) if new_day in DAYS else 0
        score += abs(new_day_index - old_day_index) * 500

    if old_start is not None:
        score += abs(new_start - old_start)

    return score


def total_change_score(original_lessons, changed_lessons):
    original_by_id = {
        lesson_id(lesson): lesson
        for lesson in original_lessons
    }

    score = 0

    for lesson in changed_lessons:
        original = original_by_id.get(lesson_id(lesson))

        if not original:
            continue

        if original.get(DAY_KEY) != lesson.get(DAY_KEY):
            score += 500

        if original.get(TIME_KEY) != lesson.get(TIME_KEY):
            old_start, _ = parse_time_range(original.get(TIME_KEY))
            new_start, _ = parse_time_range(lesson.get(TIME_KEY))

            if old_start is not None and new_start is not None:
                score += abs(new_start - old_start)

        if original.get(TEACHER_KEY) != lesson.get(TEACHER_KEY):
            score += 30

        if original.get(ROOM_KEY) != lesson.get(ROOM_KEY):
            score += 15

        if original.get(SUBJECT_KEY) != lesson.get(SUBJECT_KEY):
            score += 100

    return score


def generate_slots_for_lesson(lessons, source_data, lesson, ignore_ids=None):
    ignore_ids = set(ignore_ids or [])
    duration = lesson_duration(lesson, source_data)

    variants = []

    for day in DAYS:
        for start in range(START_DAY, END_DAY - duration + 1, STEP_MIN):
            end = start + duration
            old_day = lesson.get(DAY_KEY)
            old_start, _ = parse_time_range(lesson.get(TIME_KEY))

            if day == old_day and start == old_start:
                continue

            candidate = deepcopy(lesson)
            candidate[DAY_KEY] = day
            candidate[TIME_KEY] = format_time_range(start, end)

            if is_slot_free(lessons, candidate, ignore_ids):
                score = movement_score(lesson, day, start)
                variants.append((score, day, start, end))

    variants.sort(key=lambda item: item[0])
    return variants


def move_lesson_to_best_slot(lessons, source_data, lesson, extra_ignore_ids=None):
    old_day = lesson.get(DAY_KEY)
    old_time = lesson.get(TIME_KEY)

    ignore_ids = {lesson_id(lesson)}
    ignore_ids.update(extra_ignore_ids or [])

    variants = generate_slots_for_lesson(
        lessons=lessons,
        source_data=source_data,
        lesson=lesson,
        ignore_ids=ignore_ids
    )

    if not variants:
        return False

    _, day, start, end = variants[0]

    lesson[DAY_KEY] = day
    lesson[TIME_KEY] = format_time_range(start, end)

    lesson["_moved_from"] = {
        "день_недели": old_day,
        "время": old_time
    }

    lesson["_moved_to"] = {
        "день_недели": day,
        "время": lesson[TIME_KEY]
    }

    return True


def try_relocate_lessons_with_min_score(lessons, source_data, lessons_to_move):


    original_lessons = deepcopy(lessons)
    move_ids = {lesson_id(lesson) for lesson in lessons_to_move}

    best_lessons = None
    best_score = None

    def recursive(current_lessons, index):
        nonlocal best_lessons, best_score

        if index >= len(lessons_to_move):
            score = total_change_score(original_lessons, current_lessons)

            if best_score is None or score < best_score:
                best_score = score
                best_lessons = deepcopy(current_lessons)

            return

        current_id = lesson_id(lessons_to_move[index])

        lesson = next(
            item
            for item in current_lessons
            if lesson_id(item) == current_id
        )

        ignore_ids = {current_id} | move_ids

        variants = generate_slots_for_lesson(
            lessons=current_lessons,
            source_data=source_data,
            lesson=lesson,
            ignore_ids=ignore_ids
        )

        for _, day, start, end in variants[:20]:
            candidate_lessons = deepcopy(current_lessons)

            candidate_lesson = next(
                item
                for item in candidate_lessons
                if lesson_id(item) == current_id
            )

            candidate_lesson[DAY_KEY] = day
            candidate_lesson[TIME_KEY] = format_time_range(start, end)

            recursive(candidate_lessons, index + 1)

    recursive(deepcopy(lessons), 0)

    if best_lessons is None:
        return None

    return best_lessons


def find_teacher_for_lesson(source_data, lessons, lesson, preferred_teacher=None):
    old_teacher = normalize_text(lesson.get(TEACHER_KEY))

    candidates = []

    if preferred_teacher:
        candidates.append(preferred_teacher)

    for teacher in get_suitable_teachers_for_lesson(
        source_data,
        lesson,
        exclude_teacher=old_teacher
    ):
        if teacher not in candidates:
            candidates.append(teacher)

    for teacher in candidates:
        if not teacher_can_teach_lesson(source_data, teacher, lesson):
            continue

        test_lesson = deepcopy(lesson)
        test_lesson[TEACHER_KEY] = teacher

        if is_slot_free(lessons, test_lesson, ignore_ids={lesson_id(lesson)}):
            return teacher, False

    for teacher in candidates:
        if not teacher_can_teach_lesson(source_data, teacher, lesson):
            continue

        test_lesson = deepcopy(lesson)
        test_lesson[TEACHER_KEY] = teacher

        variants = generate_slots_for_lesson(
            lessons=lessons,
            source_data=source_data,
            lesson=test_lesson,
            ignore_ids={lesson_id(lesson)}
        )

        if variants:
            return teacher, True

    return None, False


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
        "teachers": unique(teachers + [
            lesson.get(TEACHER_KEY, "")
            for lesson in lessons
        ]),

        "subjects": unique(subjects + [
            lesson.get(SUBJECT_KEY, "")
            for lesson in lessons
        ]),

        "rooms": unique(rooms + [
            lesson.get(ROOM_KEY, "")
            for lesson in lessons
        ]),

        "groups": unique(groups + [
            group
            for lesson in lessons
            for group in split_groups(lesson.get(GROUP_KEY))
        ]),

        "days": DAYS,

        "times": unique([
            lesson.get(TIME_KEY, "")
            for lesson in lessons
        ]),

        "lessons": lessons
    }


def apply_replace_teacher(lessons, source_data, change):
    ids = change.get("lesson_ids", [])
    teacher_by_lesson = change.get("teacher_by_lesson", {})

    if not ids:
        raise ValueError("Выберите занятия для изменения.")

    for lesson in selected_lessons(lessons, ids):
        preferred_teacher = normalize_text(teacher_by_lesson.get(lesson_id(lesson)))
        if preferred_teacher:
            if not teacher_can_teach_lesson(source_data, preferred_teacher, lesson):
                raise ValueError(
                    f"Преподаватель {preferred_teacher} не может вести "
                    f"«{lesson.get(SUBJECT_KEY)}» ({lesson.get(TYPE_KEY)})."
                )

        teacher, need_move = find_teacher_for_lesson(
            source_data=source_data,
            lessons=lessons,
            lesson=lesson,
            preferred_teacher=preferred_teacher or None
        )

        if not teacher:
            raise ValueError(
                f"Нельзя заменить преподавателя для пары "
                f"«{lesson.get(SUBJECT_KEY)}» ({lesson.get(TYPE_KEY)}), "
                f"{lesson.get(DAY_KEY)}, {lesson.get(TIME_KEY)}. "
                f"Нет преподавателя, который может вести этот предмет "
                f"и которого можно поставить без конфликтов."
            )

        lesson[TEACHER_KEY] = teacher

        if need_move:
            moved = move_lesson_to_best_slot(
                lessons=lessons,
                source_data=source_data,
                lesson=lesson
            )

            if not moved:
                raise ValueError(
                    f"Преподаватель найден, но свободный слот для занятия "
                    f"«{lesson.get(SUBJECT_KEY)}» не найден."
                )


def apply_remove_lesson(result, lessons, source_data, change):
    ids = {str(item) for item in change.get("lesson_ids", [])}
    mode = change.get("mode")

    if not ids:
        raise ValueError("Выберите занятия для изменения.")

    if mode == "move":
        moved_messages = []

        for lesson in selected_lessons(lessons, ids):
            old_day = lesson.get(DAY_KEY)
            old_time = lesson.get(TIME_KEY)

            moved = move_lesson_to_best_slot(
                lessons=lessons,
                source_data=source_data,
                lesson=lesson
            )

            if not moved:
                raise ValueError(
                    f"Не удалось перенести занятие «{lesson.get(SUBJECT_KEY)}»."
                )

            moved_messages.append(
                f"Занятие «{lesson.get(SUBJECT_KEY)}» "
                f"перенесено с {old_day}, {old_time} "
                f"на {lesson.get(DAY_KEY)}, {lesson.get(TIME_KEY)}."
            )

        result["message"] = "\n".join(moved_messages)

        return lessons

    lessons = [
        lesson
        for lesson in lessons
        if lesson_id(lesson) not in ids
    ]

    result["lessons"] = lessons
    return lessons


def apply_replace_lesson(lessons, source_data, change):
    ids = change.get("lesson_ids", [])

    new_subject = normalize_text(change.get("subject"))
    new_teacher = normalize_text(change.get("teacher"))
    new_room = normalize_text(change.get("room"))
    subject_mode = normalize_text(change.get("subject_mode"))

    if not ids:
        raise ValueError("Выберите занятия для изменения.")

    if not new_subject:
        raise ValueError("Укажите новый предмет.")

    for lesson in selected_lessons(lessons, ids):
        lesson[SUBJECT_KEY] = new_subject

        if new_room:
            if not room_is_suitable(source_data, new_room, lesson):
                raise ValueError(
                    f"Аудитория {new_room} не подходит для занятия «{new_subject}»."
                )

            lesson[ROOM_KEY] = new_room

        if subject_mode == "custom":
            if new_teacher:
                test_lesson = deepcopy(lesson)
                test_lesson[TEACHER_KEY] = new_teacher

                if not is_slot_free(
                    lessons,
                    test_lesson,
                    ignore_ids={lesson_id(lesson)}
                ):
                    moved = move_lesson_to_best_slot(
                        lessons=lessons,
                        source_data=source_data,
                        lesson=test_lesson
                    )

                    if not moved:
                        raise ValueError(
                            f"Преподаватель {new_teacher} занят в это время, "
                            f"и свободный слот для занятия «{new_subject}» не найден."
                        )

                    lesson[DAY_KEY] = test_lesson[DAY_KEY]
                    lesson[TIME_KEY] = test_lesson[TIME_KEY]

                lesson[TEACHER_KEY] = new_teacher

            continue
        if new_teacher:
            if not teacher_can_teach_lesson(source_data, new_teacher, lesson):
                raise ValueError(
                    f"Преподаватель {new_teacher} не может вести "
                    f"«{new_subject}» ({lesson.get(TYPE_KEY)})."
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
            moved = move_lesson_to_best_slot(
                lessons=lessons,
                source_data=source_data,
                lesson=lesson
            )

            if not moved:
                raise ValueError(
                    f"Не удалось найти свободный слот для нового предмета "
                    f"«{new_subject}»."
                )


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


def apply_dynamic_change(schedule_data, source_data, change):
    result = normalize_schedule(schedule_data)

    lessons = result["lessons"]
    action = change.get("action")

    if action == "replace_teacher":
        apply_replace_teacher(lessons, source_data, change)

    elif action == "remove_lesson":
        lessons = apply_remove_lesson(result, lessons, source_data, change)

    elif action == "replace_lesson":
        apply_replace_lesson(lessons, source_data, change)

    else:
        raise ValueError("Выберите тип изменения расписания.")

    result["lessons"] = sort_lessons(lessons)

    return result