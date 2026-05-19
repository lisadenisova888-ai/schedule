import json 
import math
from collections import defaultdict

days=["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"]
start_day=9*60
end_day=18*60
braek_min=15
academ_hour=45

input_file="schedule_data.json"
output_file="schedule.json"

#первод времени в стандартный вид
def time(minutes):
    return f"{minutes//60:02d}:{minutes%60:02d}"

#проверка пересечений занятий с учетом перемены
def break_chek(start1, end1, start2, end2, break_min=braek_min):
    return start1<end2+break_min and start2<end1+break_min

#добавление занятости к обекту 
def add_busy(busy, id, day, start, end):
    busy[id][day].append((start, end))

#проверка занятости для обьекта (учитель, кабинет, группа)
def busys(busy, id, day, start, end):
    for busy_start, busy_end in busy[id][day]:
        if break_chek(start, end, busy_start, busy_end):
            return False
    return True

#подсчет окна  
def window(busy, id, day, start, end):
    integral=sorted(busy[id][day]+[(start, end)])
    wind=0
    for i in range (1, len(integral)):
        gap=integral[i][0]-integral[i-1][1]
        if gap>braek_min:
            wind+=gap-braek_min
    return wind

#приоритеты выбора аудитории исходя из доп условий предмета 
def aud_prior(aud, subj):
    aud_type=set(aud.get("тип аудитории", []))
    dop=set(subj.get("дополнительны условия", ["-"]))
    if "тех" in dop:
        if "тех" in aud_type:
            return 0
        if "экран" in aud_type:
            return 1
        return 2
    if "экран" in dop:
        if "экран" in aud_type:
            return 0
        if "тех" in aud_type:
            return 1
        return 2
    return 0

#выбор лучшей совбодной аудитории
def choose_aud(auds, aud_busy, subj, aud_size, day, start, end):
    res_aud=[]
    for aud in auds:
        aud_id=aud["id"]
        if aud.get("вместимость",0)<aud_size:
            continue
        if not busys(aud_busy,aud_id, day, start, end):
            continue
        res_aud.append(aud)
    if not res_aud:
        return None
    if subj.get("тип занятия")==1:
        res_aud.sort(key=lambda aud:(aud_prior(aud, subj), -aud.get("вместимость",0)))
    else:
        res_aud.sort(key=lambda aud:(aud_prior(aud, subj), aud.get("вместимость",0)))
    return res_aud[0]

#выбор преподавателя
def choose_teac(teach, teach_busy, teach_load, subj_id, academ_hour, day, start, end):
    res_teah=[]
    for teacher in teach:
        teach_id=teacher["id"]
        if subj_id not in teacher.get("преподает предметы (id)", []):
            continue
        max_load=teacher.get("занятость в неделю", 0)
        if teach_load[teach_id]+academ_hour>max_load:
            continue
        if not busys(teach_busy, teach_id, day, start, end):
            continue
        res_teah.append(teacher)
    if not res_teah:
        return None
    res_teah.sort(key=lambda teacher: teach_load[teacher["id"]])
    return res_teah[0]

#список занятий которые надо поствить
def build_lesson_tasks(groups, subj_id):
    tasks=[]
    lecture_groups=defaultdict(list)

    for group in groups:
        for subject_id in group.get("предметы (id)", []):
            subj=subj_id[subject_id]
            if subj.get("тип занятия")==1:
                lecture_groups[subject_id].append(group)
            else:
                total_min=subj.get("часы в неделю", 0) * academ_hour
                mint=subj.get("длительность", academ_hour)
                lesson_count=math.ceil(total_min/mint)
                for lesson_n in range(lesson_count):
                    tasks.append({
                        "groups": [group],
                        "subj": subj,
                        "subject_id": subject_id,
                        "mint": mint,
                        "lesson_number": lesson_n+1
                    })
    for subject_id, groups_for_lecture in lecture_groups.items():
        subj=subj_id[subject_id]
        total_min=subj.get("часы в неделю", 0)*academ_hour
        mint=subj.get("длительность", academ_hour)
        lesson_count=math.ceil(total_min/mint)
        for lesson_n in range(lesson_count):
            tasks.append({
                "groups": groups_for_lecture,
                "subj": subj,
                "subject_id": subject_id,
                "mint": mint,
                "lesson_number": lesson_n+1
                })
    tasks.sort(key=lambda task: (-task["mint"], -task["subj"].get("часы в неделю", 0)))
    return tasks


def schedule(data):
    aud=data["аудитории"]
    teach=data["преподаватели"]
    subj=data["предметы"]
    gr=data["группы"]

    subj__id={subject["id"]: subject for subject in subj}
    gr_busy=defaultdict(lambda: defaultdict(list))
    teach_busy=defaultdict(lambda: defaultdict(list))
    aud_busy=defaultdict(lambda: defaultdict(list))
    teach_load=defaultdict(float)
    schedule=[]
    unplaced=[]

    tasks=build_lesson_tasks(gr, subj__id)

    for task in tasks:
        groups_for_lesson=task["groups"]
        subject=task["subj"]
        subject_id=task["subject_id"]
        mint=task["mint"]
        group_size=sum(group.get("кол-во человек", 0) for group in groups_for_lesson)
        lesson_academic_hours=mint/academ_hour
        best_variant=None
        best_score=float("inf")

        for day in days:
            latest_start=end_day-mint
            for start in range(start_day, latest_start+1, braek_min):
                end=start+mint
                groups_free=True
                for group in groups_for_lesson:
                    if not busys(gr_busy, group["id"], day, start, end):
                        groups_free=False
                        break
                if not groups_free:
                    continue
                teacher = choose_teac(teach, teach_busy, teach_load, subject_id, lesson_academic_hours, day, start, end)
                if teacher is None:
                    continue
                room = choose_aud(aud, aud_busy, subject, group_size, day, start, end)
                if room is None:
                    continue

                gr_windows=0
                for group in groups_for_lesson:
                    gr_windows += window(gr_busy, group["id"], day, start, end)
                teach_windows=window(teach_busy, teacher["id"], day, start, end)
                aud_score=aud_prior(room, subject)
                early_score=start-start_day
                load_score=teach_load[teacher["id"]]
                score=gr_windows*10+teach_windows*5+aud_score*100+early_score*0.01+load_score

                if score<best_score:
                    best_score=score
                    best_variant=(day, start, end, teacher, room)

        if best_variant is None:
            unplaced.append({
                "группа": ", ".join(str(group.get("номер")) for group in groups_for_lesson),
                "предмет": subject.get("название"),
                "тип": "Лекция" if subject.get("тип занятия")==1 else "Семинар",
                "длительность": mint,
                "причина": "не найден свободный преподаватель, кабинет или время с учетом ограничений"
            })
            continue

        day, start, end, teacher, room=best_variant
        for group in groups_for_lesson:
            add_busy(gr_busy, group["id"], day, start, end)
        add_busy(teach_busy, teacher["id"], day, start, end)
        add_busy(aud_busy, room["id"], day, start, end)
        teach_load[teacher["id"]]+=lesson_academic_hours

        schedule.append({
            "аудитория": str(room["номер"]),
            "преподаватель": teacher["ФИО"],
            "предмет": subject["название"],
            "тип": "Лекция" if subject.get("тип занятия")==1 else "Семинар",
            "группа": ", ".join(str(group.get("номер")) for group in groups_for_lesson),
            "день_недели": day,
            "время": f"{time(start)} – {time(end)}"
        })

    schedule.sort(key=lambda lesson: (days.index(lesson["день_недели"]), lesson["время"], lesson["группа"]))
    return {"lessons": schedule, "unplaced_lessons": unplaced}

def main():
    with open(input_file,"r",encoding="utf-8") as file:
        data=json.load(file)
    res=schedule(data)
    with open(output_file,"w", encoding="utf-8") as file:
        json.dump(res, file, ensure_ascii=False, indent=4)
    print (f"Расписание созданно. Не удалость поставить {len(res['unplaced_lessons'])} занятий")

if __name__=="__main__":
    main()