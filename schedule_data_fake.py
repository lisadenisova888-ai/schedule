"""Генерация демонстрационной Excel-базы для построения расписания.

Скрипт создаёт случайные данные четырёх справочников:

1. Для аудиторий назначаются id, номер, вместимость и случайный набор
   характеристик ``тех`` и ``экран``.
2. Для каждого названия предмета создаются две записи: лекция и семинар.
   Записи получают случайную недельную нагрузку, длительность и требования к
   аудитории.
3. Через ``Faker`` генерируются имена преподавателей. Затем каждому
   преподавателю назначается случайный набор предметов, а дополнительный
   проход гарантирует, что выбранные предметы не останутся без преподавателя.
4. Для групп выбираются размер и список предметов. Дополнительный проход
   гарантирует, что выбранные предметы присутствуют хотя бы у одной группы.
5. Полученные разделы записываются в книгу ``schedule_data.xlsx`` на отдельные
   листы: аудитории, преподаватели, предметы и группы.

При записи ссылок на предметы в листах преподавателей и групп скрипт заменяет
id на читаемые названия с типом занятия. Это удобно для просмотра Excel-файла,
но отличается от формата id, который ожидает конвертер ``excel_to_json.py``.
"""

from openpyxl import Workbook
import random
from faker import Faker

fake=Faker('ru_RU')

n_auditoriums =10
n_teachers= 10
n_subject= 5
n_groups= 5

#аудитории
auditoriums=[]
for i in range(1, n_auditoriums+1):
  type=[]
  if random.random()<0.2:
    type.append("тех")
  if random.random()<0.5:
    type.append("экран")
  if not type:
    type.append("-")
  
  auditoriums.append({
      "id": i,
      "номер": 100+i,
      "вместимость": random.randint(30, 120),
      "тип аудитории": type
  })

#предметы
subject=[]
subject_name=[
    "математика", "русский", "литература", "информатика", "естествознание", "экономика", "философия"]
for i in range(1, n_subject+1):
  sub_name=subject_name[i-1]
  for typ in [1,0]: #1-лекция, 0-семинар
      dop=[]
      if random.random()<0.2:
        dop.append("тех")
      if random.random()<0.5:
        dop.append("экран")
      if not dop:
        dop.append("-")
      subject.append({
        "id": len(subject)+1,
        "название": sub_name,
        "часы в неделю": random.randrange(2,8,2),
        "тип занятия": typ,
        "длительность": random.choice([45, 90]),
        "дополнительны условия": dop
      })
subject_ids=[subj["id"] for subj in subject]
subject_dict = {subj["id"]: subj["название"] for subj in subject}
    
#преподаватели
teachers_name=[]
for _ in range(n_teachers):
  teachers_name.append(fake.name())

sub_to_teach={subj_id:[] for subj_id in subject_ids}
teachers=[]
for i in range(1, n_teachers+1):
  num_subjects_teah=random.randint(1,3)  
  analable_subj_teah=[subj_id for subj_id in range(1, n_subject+1) if len (sub_to_teach[subj_id])<3]
  if not analable_subj_teah:
    analable_subj_teah=list(range(1, n_subject+1))
  teachers_subject=random.sample(analable_subj_teah, min(num_subjects_teah, len(analable_subj_teah)))
  for subj_id in teachers_subject:
    sub_to_teach[subj_id].append(i)

  teachers.append({
      "id": i,
      "ФИО": teachers_name[i-1],
      "занятость в неделю": random.randint(12,30),
      "преподает предметы (id)": teachers_subject
  })

for subj_id in range(1, n_subject+1):
  if len(sub_to_teach[subj_id])==0:
    teach_id=random.randint(1, n_teachers)
    sub_to_teach[subj_id].append(teach_id)
    if subj_id not in teachers[teach_id-1]["преподает предметы (id)"]:
      teachers[teach_id-1]["преподает предметы (id)"].append(subj_id)


  #группы
groups=[]
sub_to_gr={subj_id:[] for subj_id in subject_ids}
for i in range(1, n_groups+1):
  num_subjects_gr=random.randint(5,10)
  analable_subj_gr=[subj_id for subj_id in range(1, n_subject+1) if len (sub_to_gr[subj_id])<3]
  if not analable_subj_gr:
    analable_subj_gr=list(range(1,n_subject+1))
  groups_subject=random.sample(analable_subj_gr,min(num_subjects_gr, len(analable_subj_gr)))
  for subj_id in groups_subject:
    sub_to_gr[subj_id].append(i)

  groups.append({
      "id": i,
      "номер": 10+i,
      "кол-во человек": random.randint(10,30),
      "предметы (id)": groups_subject
  })

for subj_id in range(1, n_subject+1):
  if len(sub_to_gr[subj_id])==0:
    groups_id=random.randint(1, n_groups)
    sub_to_gr[subj_id].append(groups_id)
    if subj_id not in groups[groups_id-1]["предметы (id)"]:
      groups[groups_id-1]["предметы (id)"].append(subj_id)

  #сборка в один словарь
  data={
      "аудитории": auditoriums,
      "преподаватели": teachers,
      "предметы": subject,
      "группы": groups
  }


# сохранение в Excel
wb = Workbook()

# удаляем стандартный лист
wb.remove(wb.active)

for sheet_name, rows in data.items():
    ws = wb.create_sheet(title=sheet_name)

    if rows:
        headers = list(rows[0].keys())
        ws.append(headers)

        for row in rows:
          new_row = []
          for key, value in row.items():
            if key in ["преподает предметы (id)", "предметы (id)"]:
              subjects_names = []
              for subj_id in value:
                  subj = next(
                      s for s in subject
                      if s["id"] == subj_id)
                  lesson_type = (
                      "лекция"
                      if subj["тип занятия"] == 1
                      else "семинар")
                  subjects_names.append(
                      f'{subj["название"]} ({lesson_type})')
              new_row.append(", ".join(subjects_names))
            else:
              if isinstance(value, list):
                  new_row.append(", ".join(value))
              else:
                  new_row.append(str(value))
          ws.append(new_row)

wb.save("schedule_data.xlsx")

print("Excel база данных сохранена")
