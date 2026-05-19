import json
from collections  import defaultdict

days=["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"]
start_day=9*60
end_day=18*60
braek_min=15
academ_hour=45

#первод времени в стандартный вид
def time(minutes):
    return f"{minutes//60:02d}:{minutes%60:02d}"

#перевод времени в удобный вид для проверки
def use_time(value):
    start_text, end_text=[part.strip() for part in value.split("–")]
    start_hour, start_minute=map(int, start_text.split(":"))
    end_hour, end_minute=map(int, end_text.split(":"))
    return start_hour*60 + start_minute, end_hour*60+end_minute

#нормализация текста 
def norm_lesson(lesson):
    start, end=use_time(lesson["время"])
    groups=[group.strip() for group in str(lesson.get("группа", "")).split(",") if group.strip()]
    return {
        "start": start,
        "end": end,
        "groups": groups,
        "day": lesson.get("день_недели", "").strip(),
        "teacher": lesson.get("преподаватель", "").strip(),
        "auditoriums": str(lesson.get("аудитория", "")).strip(),
        "name": f"{lesson.get('тип', '')} по предмету {lesson.get('предмет', '')}"
    }

#общий формат под вывод ошибок
def add_error(errors, kind, key, lesson1, lesson2):
    common_start=max(lesson1["start"], lesson2["start"])
    common_end=min(lesson1["end"], lesson2["end"])
    common_time=(f"{time(common_start)} – {time(common_end)}")

    if kind=="group":
        errors.append(f"У группы {key} есть {lesson1['name']} и {lesson2['name']} в одно время ({lesson1['day']}, {common_time}).")
    elif kind=="teacher":
        errors.append(f"У преподавателя {key} есть {lesson1['name']} и {lesson2['name']} в одно время ({lesson1['day']}, {common_time}).")
    elif kind=="auditoriums":
        errors.append(f"Кабинет {key} занят {lesson1['name']} и {lesson2['name']} в одно время ({lesson1['day']}, {common_time}).")

#сами проверки
def validator(schedule_data):
    errors=[]

    group_busy=defaultdict(list)
    teacher_busy=defaultdict(list)
    auditoriums_busy=defaultdict(list)

    for lesson_number, lesson in enumerate(schedule_data.get("lessons", []), start=1):
        try:
            item=norm_lesson(lesson)
        except Exception as error:
            errors.append(f"Занятие №{lesson_number}: некорректный формат времени или полей ({error}).")
            continue

        for group in item["groups"]:
            group_busy[group].append(item)
        teacher_busy[item["teacher"]].append(item)
        auditoriums_busy[item["auditoriums"]].append(item)

    checks=[
        (group_busy, "group"),
        (teacher_busy, "teacher"),
        (auditoriums_busy, "auditoriums")
    ]

    for busy_dict, kind in checks:
        for key, lessons in busy_dict.items():
            lessons=sorted(
                lessons,
                key=lambda item: (item["day"], item["start"], item["end"])
            )

            for i in range(len(lessons)):
                for j in range(i+1, len(lessons)):
                    lesson1=lessons[i]
                    lesson2=lessons[j]
                    if lesson1["day"]!=lesson2["day"]:
                        continue
                    if lesson1["start"]<lesson2["end"] and lesson2["start"]<lesson1["end"]:
                        add_error(errors, kind, key, lesson1, lesson2)
    return errors

#вывод занятий которые не удалось поставить если такие есть
def print_unplaced(schedule_data):
    if "unplaced_lessons" not in schedule_data:
        return
    unplaced=schedule_data.get("unplaced_lessons", [])
    if not unplaced:
        return
    print("Занятия которые не удалось поставить:")
    for lesson in unplaced:
        print(f"- {lesson}")

#вывод ошибок
def check_schedule(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        schedule_data=json.load(file)
    errors=validator(schedule_data)
    if errors:
        print("Ошибки:")
        for error in errors:
            print(error)
        print(f"Количество ошибок: {len(errors)}")
    else:
        print("Ошибок в расписании не найдено")
    print_unplaced(schedule_data)

if __name__=="__main__":
    check_schedule("schedule.json")
