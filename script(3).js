/* =========================================================
   БЛОК 1. СОЗДАНИЕ РАСПИСАНИЯ
   ========================================================= */

const store = {
  rooms: [],
  teachers: [],
  subjects: [],
  groups: []
};

let activeTab = 'rooms';

let generatedSchedule = {
  lessons: [],
  unplaced_lessons: []
};

const headers = {
  rooms: ['ID', 'Номер', 'Вместимость', 'Характеристики'],
  teachers: ['ID', 'ФИО', 'Занятость/нед.', 'Предметы'],
  subjects: ['ID', 'Название', 'Часы/нед.', 'Тип', 'Длительность', 'Условия'],
  groups: ['ID', 'Номер', 'Кол-во человек', 'Предметы']
};


/* =========================================================
   ПЕРЕКЛЮЧЕНИЕ СТРАНИЦ
   ========================================================= */

function showPage(id) {
  document.querySelectorAll('.page').forEach(page => {
    page.classList.remove('active');
  });

  document.getElementById(id).classList.add('active');

  if (id === 'result') {
    fillGroupSelect();
    renderSchedule();
  }
}


/* =========================================================
   ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
   ========================================================= */

function splitList(value, numbers = false) {
  return String(value || '')
    .split(',')
    .map(item => item.trim())
    .filter(Boolean)
    .map(item => numbers ? Number(item) : item);
}

function nextId(type) {
  if (!store[type].length) {
    return 1;
  }

  return Math.max(...store[type].map(row => Number(row[0]) || 0)) + 1;
}

function checked(name) {
  return [...document.querySelectorAll(`input[name="${name}"]:checked`)]
    .map(input => input.value)
    .join(', ');
}

function pickedSubjects() {
  return [...document.querySelectorAll('input[name="subjectPick"]:checked')]
    .map(input => input.value)
    .join(', ');
}

function getSubjectNameById(id) {
  const subject = store.subjects.find(item => {
    return String(item[0]) === String(id).trim();
  });

  return subject ? subject[1] : id;
}

function formatPreviewCell(type, value, colIndex) {
  if ((type === 'groups' || type === 'teachers') && colIndex === 3) {
    return String(value || '')
      .split(',')
      .map(id => getSubjectNameById(id))
      .join(', ');
  }

  return value || '—';
}


/* =========================================================
   ФОРМА РУЧНОГО ВВОДА
   ========================================================= */

function subjectOptionsName() {
  if (!store.subjects.length) {
    return `
      <span class="hint danger">
        Сначала добавьте предметы во вкладке «Предметы».
      </span>
    `;
  }

  return store.subjects.map(subject => `
    <label>
      <input type="checkbox" name="subjectPick" value="${subject[0]}">
      ${subject[1]}
      <span class="hint">#${subject[0]}</span>
    </label>
  `).join('');
}

function renderForm() {
  const type = document.getElementById('entityType').value;
  const box = document.getElementById('dynamicForm');

  const forms = {
    rooms: `
      <label>Номер кабинета</label>
      <input id="roomNumber" placeholder="101">

      <label>Вместимость</label>
      <input id="roomCapacity" type="number" placeholder="30">

      <label>Характеристики</label>
      <div class="checks">
        <label>
          <input type="checkbox" name="roomFeatures" value="экран">
          экран
        </label>

        <label>
          <input type="checkbox" name="roomFeatures" value="техника">
          техника
        </label>
      </div>
    `,

    teachers: `
      <label>ФИО преподавателя</label>
      <input id="teacherName">

      <label>Занятость в неделю</label>
      <input id="teacherHours" type="number">

      <label>Предметы</label>
      <div class="subject-list">
        ${subjectOptionsName()}
      </div>
    `,

    subjects: `
      <label>Название предмета</label>
      <input id="subjectName">

      <label>Часы в неделю</label>
      <input id="subjectHours" type="number">

      <label>Тип занятия</label>
      <select id="subjectType">
        <option value="1">Лекция</option>
        <option value="0">Семинар</option>
      </select>

      <label>Длительность, минут</label>
      <input id="subjectDuration" type="number" value="90">

      <label>Условия</label>
      <input id="subjectNeeds" placeholder="экран, техника или -">
    `,

    groups: `
      <label>Номер группы</label>
      <input id="groupNumber">

      <label>Количество человек</label>
      <input id="groupSize" type="number">

      <label>Предметы</label>
      <div class="subject-list">
        ${subjectOptionsName()}
      </div>
    `
  };

  box.innerHTML = forms[type];
}

function addItem() {
  const type = document.getElementById('entityType').value;
  let row;

  if (type === 'rooms') {
    row = [
      nextId(type),
      roomNumber.value,
      roomCapacity.value,
      checked('roomFeatures') || '-'
    ];
  }

  if (type === 'teachers') {
    row = [
      nextId(type),
      teacherName.value,
      teacherHours.value,
      pickedSubjects()
    ];
  }

  if (type === 'subjects') {
    row = [
      nextId(type),
      subjectName.value,
      subjectHours.value,
      subjectType.value,
      subjectDuration.value,
      subjectNeeds.value || '-'
    ];
  }

  if (type === 'groups') {
    row = [
      nextId(type),
      groupNumber.value,
      groupSize.value,
      pickedSubjects()
    ];
  }

  if (!row || !row[1]) {
    alert('Заполните главное поле.');
    return;
  }

  store[type].push(row);
  switchTab(type);
  renderForm();
}


/* =========================================================
   ПРЕДПРОСМОТР ДАННЫХ
   ========================================================= */

function switchTab(type) {
  activeTab = type;

  document.querySelectorAll('.tab').forEach(tab => {
    tab.classList.remove('active');
  });

  const tabText = {
    rooms: 'аудит',
    teachers: 'преподав',
    subjects: 'предмет',
    groups: 'групп'
  };

  [...document.querySelectorAll('.tab')]
    .find(tab => tab.textContent.toLowerCase().includes(tabText[type]))
    ?.classList.add('active');

  renderPreview();
}

function renderPreview() {
  const rows = store[activeTab];

  previewTable.innerHTML = `
    <thead>
      <tr>
        ${headers[activeTab].map(header => `<th>${header}</th>`).join('')}
        <th>×</th>
      </tr>
    </thead>

    <tbody>
      ${
        rows.length
          ? rows.map((row, rowIndex) => `
              <tr>
                ${row.map((cell, cellIndex) => `
                  <td
                    contenteditable="${cellIndex === 0 ? 'false' : 'true'}"
                    oninput="editCell('${activeTab}', ${rowIndex}, ${cellIndex}, this.innerText)"
                  >
                    ${formatPreviewCell(activeTab, cell, cellIndex)}
                  </td>
                `).join('')}

                <td>
                  <button class="tab" onclick="deleteRow('${activeTab}', ${rowIndex})">
                    ×
                  </button>
                </td>
              </tr>
            `).join('')
          : `<tr>
              <td colspan="${headers[activeTab].length + 1}">
                Пока нет данных.
              </td>
            </tr>`
      }
    </tbody>
  `;
}

function editCell(type, row, column, value) {
  if (column !== 0) {
    store[type][row][column] = value;
  }
}

function deleteRow(type, row) {
  store[type].splice(row, 1);
  renderPreview();
  renderForm();
}


/* =========================================================
   ПРЕОБРАЗОВАНИЕ ДАННЫХ ДЛЯ BACKEND
   ========================================================= */

function toBackendData() {
  return {
    'аудитории': store.rooms.map(row => ({
      id: Number(row[0]),
      номер: Number(row[1]),
      вместимость: Number(row[2]),
      'тип аудитории': splitList(row[3])
    })),

    'преподаватели': store.teachers.map(row => ({
      id: Number(row[0]),
      ФИО: row[1],
      'занятость в неделю': Number(row[2]),
      'преподает предметы (id)': splitList(row[3], true)
    })),

    'предметы': store.subjects.map(row => ({
      id: Number(row[0]),
      название: row[1],
      'часы в неделю': Number(row[2]),
      'тип занятия': Number(row[3]),
      длительность: Number(row[4]),
      'дополнительны условия': splitList(row[5])
    })),

    'группы': store.groups.map(row => ({
      id: Number(row[0]),
      номер: row[1],
      'кол-во человек': Number(row[2]),
      'предметы (id)': splitList(row[3], true)
    }))
  };
}

function fromBackendData(data) {
  store.rooms = (data['аудитории'] || []).map(item => [
    item.id,
    item.номер,
    item.вместимость,
    (item['тип аудитории'] || []).join(', ')
  ]);

  store.teachers = (data['преподаватели'] || []).map(item => [
    item.id,
    item.ФИО,
    item['занятость в неделю'],
    (item['преподает предметы (id)'] || []).join(', ')
  ]);

  store.subjects = (data['предметы'] || []).map(item => [
    item.id,
    item.название,
    item['часы в неделю'],
    item['тип занятия'],
    item.длительность,
    (item['дополнительны условия'] || []).join(', ')
  ]);

  store.groups = (data['группы'] || []).map(item => [
    item.id,
    item.номер,
    item['кол-во человек'],
    (item['предметы (id)'] || []).join(', ')
  ]);

  renderForm();
  renderPreview();
}


/* =========================================================
   ЗАГРУЗКА EXCEL И ГЕНЕРАЦИЯ
   ========================================================= */

async function uploadExcel() {
  const file = excelFile.files[0];

  if (!file) {
    alert('Выберите Excel-файл');
    return;
  }

  const formData = new FormData();
  formData.append('file', file);

  uploadStatus.textContent = 'Проверяю файл...';
  uploadStatus.className = 'status';

  const response = await fetch('/api/upload-excel', {
    method: 'POST',
    body: formData
  });

  const result = await response.json();

  if (!response.ok) {
    uploadStatus.innerHTML = `
      ${result.error}<br>
      <a href="/download/template">Скачать и заполнить шаблон</a>
    `;
    uploadStatus.className = 'status error';
    return;
  }

  fromBackendData(result.data);

  uploadStatus.textContent = 'Файл загружен';
  uploadStatus.className = 'status ok';
}

async function generateSchedule() {
  const data = toBackendData();

  const hasAllData =
    data['аудитории'].length &&
    data['преподаватели'].length &&
    data['предметы'].length &&
    data['группы'].length;

  if (!hasAllData) {
    uploadStatus.textContent =
      'Заполните все разделы или загрузите корректный Excel-шаблон.';
    uploadStatus.className = 'status error';
    return;
  }

  const response = await fetch('/api/generate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  });

  const result = await response.json();

  if (!response.ok) {
    uploadStatus.textContent = result.error;
    uploadStatus.className = 'status error';
    return;
  }

  generatedSchedule = result;

  resultStatus.textContent =
    `Расписание создано. Не удалось поставить: ${(result.unplaced_lessons || []).length}`;

  resultStatus.className = 'status ok';

  showPage('result');
}


/* =========================================================
   ОТОБРАЖЕНИЕ ГОТОВОГО РАСПИСАНИЯ
   ========================================================= */

function fillGroupSelect() {
  const groups = [
    ...new Set(
      (generatedSchedule.lessons || []).flatMap(lesson =>
        String(lesson['группа'] || '')
          .split(',')
          .map(group => group.trim())
          .filter(Boolean)
      )
    )
  ];

  groupSelect.innerHTML = ['Все группы', ...groups]
    .map(group => `<option>${group}</option>`)
    .join('');
}

function renderSchedule() {
  const days = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница'];
  const lessons = generatedSchedule.lessons || [];
  const selectedGroup = groupSelect.value || 'Все группы';

  const filteredLessons =
    selectedGroup === 'Все группы'
      ? lessons
      : lessons.filter(lesson =>
          String(lesson['группа'])
            .split(',')
            .map(group => group.trim())
            .includes(selectedGroup)
        );

  const times = [
    ...new Set(filteredLessons.map(lesson => lesson['время']))
  ].sort();

  scheduleTable.innerHTML = `
    <thead>
      <tr>
        <th>Время / День</th>
        ${days.map(day => `<th>${day}</th>`).join('')}
      </tr>
    </thead>

    <tbody>
      ${
        times.length
          ? times.map(time => `
              <tr>
                <td>${time}</td>

                ${days.map(day => {
                  const items = filteredLessons.filter(lesson =>
                    lesson['время'] === time &&
                    lesson['день_недели'] === day
                  );

                  return `
                    <td>
                      ${items.map(lesson => `
                        <span class="lesson">
                          ${lesson['предмет']} (${lesson['тип']})
                        </span>

                        <span class="muted">
                          ${lesson['группа']} · ауд. ${lesson['аудитория']}
                        </span>

                        <span class="muted">
                          ${lesson['преподаватель']}
                        </span>
                      `).join('<hr>')}
                    </td>
                  `;
                }).join('')}
              </tr>
            `).join('')
          : `<tr>
              <td colspan="6">
                Сначала сгенерируйте расписание.
              </td>
            </tr>`
      }
    </tbody>
  `;
}


/* =========================================================
   ПРОВЕРКА И ЭКСПОРТ
   ========================================================= */

async function validateSchedule() {
  const response = await fetch('/api/validate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(generatedSchedule)
  });

  const result = await response.json();

  if (!response.ok) {
    resultStatus.textContent = result.error;
    resultStatus.className = 'status error';
    return;
  }

  if (result.count) {
    resultStatus.textContent =
      `Ошибки (${result.count}):\n` + result.errors.join('\n');
    resultStatus.className = 'status error';
  } else {
    resultStatus.textContent = 'Ошибок в расписании не найдено';
    resultStatus.className = 'status ok';
  }
}

async function downloadCalendar() {
  downloadViaPost(
    '/api/calendar',
    { schedule: generatedSchedule, repeat_weeks: 16 },
    'schedule.ics'
  );
}

async function downloadExcel() {
  downloadViaPost(
    '/api/excel',
    { schedule: generatedSchedule },
    'schedule_export.xlsx'
  );
}

async function downloadPdf() {
  downloadViaPost(
    '/api/pdf',
    { schedule: generatedSchedule },
    'schedule_export.pdf'
  );
}

async function downloadViaPost(url, payload, filename) {
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    const result = await response.json();
    alert(result.error);
    return;
  }

  const blob = await response.blob();
  const link = document.createElement('a');

  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();

  URL.revokeObjectURL(link.href);
}


/* =========================================================
   БЛОК 2. ДИНАМИЧЕСКОЕ ИЗМЕНЕНИЕ РАСПИСАНИЯ
   ========================================================= */

let sourceData = {};

let dynamicSchedule = {
  lessons: [],
  unplaced_lessons: []
};

let options = {
  teachers: [],
  subjects: [],
  rooms: [],
  groups: [],
  days: ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница'],
  times: [],
  lessons: []
};

const keys = {
  day: 'день_недели',
  time: 'время',
  group: 'группа',
  subject: 'предмет',
  type: 'тип',
  teacher: 'преподаватель',
  room: 'аудитория'
};

const days = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница'];


/* =========================================================
   ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДИНАМИЧЕСКОГО РАСПИСАНИЯ
   ========================================================= */

function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, symbol => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[symbol]));
}

function splitGroups(value) {
  return String(value || '')
    .split(',')
    .map(group => group.trim())
    .filter(Boolean);
}

function listOptions(items, allLabel = 'Все') {
  return [
    `<option value="">${allLabel}</option>`,
    ...items.map(item => `
      <option value="${esc(item)}">${esc(item)}</option>
    `)
  ].join('');
}

function lessonLine(lesson) {
  return `
    ${lesson[keys.day]} ·
    ${lesson[keys.time]} ·
    ${lesson[keys.group]} ·
    ${lesson[keys.subject]} ·
    ${lesson[keys.teacher]}
  `;
}

function selectedIds() {
  return [...document.querySelectorAll('input[name="lessonPick"]:checked')]
    .map(input => input.value);
}


/* =========================================================
   ЗАГРУЗКА ФАЙЛОВ ДЛЯ ДИНАМИЧЕСКОГО РАСПИСАНИЯ
   ========================================================= */

async function uploadEndpoint(input, url, kind) {
  const file = input.files[0];

  if (!file) {
    alert('Выберите Excel-файл');
    return null;
  }

  const formData = new FormData();
  formData.append('file', file);

  dynamicUploadStatus.textContent = `Загружаю ${kind}...`;
  dynamicUploadStatus.className = 'status';

  const response = await fetch(url, {
    method: 'POST',
    body: formData
  });

  const result = await response.json();

  if (!response.ok) {
    dynamicUploadStatus.textContent = result.error;
    dynamicUploadStatus.className = 'status error';
    return null;
  }

  dynamicUploadStatus.textContent = `${kind} загружен`;
  dynamicUploadStatus.className = 'status ok';

  return result.data;
}

async function uploadSchedule() {
  const data = await uploadEndpoint(
    scheduleFile,
    '/api/upload-schedule',
    'Расписание'
  );

  if (!data) return;

  dynamicSchedule = data;

  await refreshOptions();

  fillDynamicGroupSelect();

  dynamicGroupSelect.value = 'Все группы';

  renderDynamicSchedule();
  renderAction();

  dynamicUploadStatus.textContent = 'Расписание загружено и отображено в таблице';
  dynamicUploadStatus.className = 'status ok';
}

async function uploadData() {
  const data = await uploadEndpoint(
    dataFile,
    '/api/upload-excel',
    'Данные'
  );

  if (!data) return;

  sourceData = data;

  await refreshOptions();
  renderAction();
}

async function refreshOptions() {
  const response = await fetch('/api/dynamic/options', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      source_data: sourceData,
      schedule: dynamicSchedule
    })
  });

  options = await response.json();
}


/* =========================================================
   ОТОБРАЖЕНИЕ ДИНАМИЧЕСКОГО РАСПИСАНИЯ
   ========================================================= */

function fillDynamicGroupSelect() {
  const groups = options.groups.length
    ? options.groups
    : [
        ...new Set(
          (dynamicSchedule.lessons || []).flatMap(lesson =>
            splitGroups(lesson[keys.group])
          )
        )
      ];

  dynamicGroupSelect.innerHTML = ['Все группы', ...groups]
    .map(group => `<option>${esc(group)}</option>`)
    .join('');
}

function renderDynamicSchedule() {
  const lessons = dynamicSchedule.lessons || [];
  const selectedGroup = dynamicGroupSelect.value || 'Все группы';

  const filteredLessons =
    selectedGroup === 'Все группы'
      ? lessons
      : lessons.filter(lesson =>
          splitGroups(lesson[keys.group]).includes(selectedGroup)
        );

  const times = [
    ...new Set(
      filteredLessons
        .map(lesson => lesson[keys.time])
        .filter(Boolean)
    )
  ].sort();

  dynamicScheduleTable.innerHTML = `
    <thead>
      <tr>
        <th>Время / День</th>
        ${days.map(day => `<th>${day}</th>`).join('')}
      </tr>
    </thead>

    <tbody>
      ${
        times.length
          ? times.map(time => `
              <tr>
                <td>${esc(time)}</td>

                ${days.map(day => {
                  const items = filteredLessons.filter(lesson =>
                    lesson[keys.time] === time &&
                    lesson[keys.day] === day
                  );

                  return `
                    <td>
                      ${items.map(lesson => `
                        <span class="lesson">
                          ${esc(lesson[keys.subject])}
                          (${esc(lesson[keys.type])})
                        </span>

                        <span class="muted">
                          ${esc(lesson[keys.group])}
                          · ауд. ${esc(lesson[keys.room])}
                        </span>

                        <span class="muted">
                          ${esc(lesson[keys.teacher])}
                        </span>
                      `).join('<hr>')}
                    </td>
                  `;
                }).join('')}
              </tr>
            `).join('')
          : `<tr>
              <td colspan="6">
                Загрузите расписание, чтобы увидеть таблицу.
              </td>
            </tr>`
      }
    </tbody>
  `;
}


/* =========================================================
   ФИЛЬТРЫ ДЛЯ ИЗМЕНЕНИЙ
   ========================================================= */

function filterLessons() {
  const day = document.getElementById('filterDay')?.value || '';
  const time = document.getElementById('filterTime')?.value || '';
  const group = document.getElementById('filterGroup')?.value || '';
  const subject = document.getElementById('filterSubject')?.value || '';

  if (!day && !time && !group && !subject) {
    return [];
  }

  return (dynamicSchedule.lessons || []).filter(lesson =>
    (!day || lesson[keys.day] === day) &&
    (!time || lesson[keys.time] === time) &&
    (!subject || lesson[keys.subject] === subject) &&
    (!group || splitGroups(lesson[keys.group]).includes(group))
  );
}

function renderLessonChecks(
  lessons,
  emptyText = 'Выберите хотя бы один параметр занятия'
) {
  return `
    <div class="list">
      ${
        lessons.length
          ? lessons.map(lesson => `
              <label>
                <input
                  type="checkbox"
                  name="lessonPick"
                  value="${esc(lesson._id)}"
                >
                ${esc(lessonLine(lesson))}
              </label>
            `).join('')
          : `<span class="hint">${emptyText}</span>`
      }
    </div>
  `;
}

function filtersHtml() {
  return `
    <div class="two">
      <div>
        <label>День</label>
        <select id="filterDay" onchange="renderAction()">
          ${listOptions(days)}
        </select>
      </div>

      <div>
        <label>Время</label>
        <select id="filterTime" onchange="renderAction()">
          ${listOptions(options.times)}
        </select>
      </div>

      <div>
        <label>Группа</label>
        <select id="filterGroup" onchange="renderAction()">
          ${listOptions(options.groups)}
        </select>
      </div>

      <div>
        <label>Предмет</label>
        <select id="filterSubject" onchange="renderAction()">
          ${listOptions(options.subjects)}
        </select>
      </div>
    </div>
  `;
}

function restoreFilters(values) {
  for (const [id, value] of Object.entries(values)) {
    const element = document.getElementById(id);

    if (element) {
      element.value = value;
    }
  }
}


/* =========================================================
   ФОРМА ВЫБОРА ИЗМЕНЕНИЯ
   ========================================================= */

function renderAction() {
  const current = {
    filterDay: document.getElementById('filterDay')?.value || '',
    filterTime: document.getElementById('filterTime')?.value || '',
    filterGroup: document.getElementById('filterGroup')?.value || '',
    filterSubject: document.getElementById('filterSubject')?.value || ''
  };

  const action = actionType.value;

  if (action === 'replace_teacher') {
    renderReplaceTeacherForm();
  }

  if (action === 'remove_lesson') {
    renderRemoveLessonForm(current);
  }

  if (action === 'replace_lesson') {
    renderReplaceLessonForm(current);
  }

  if (action === 'add_window') {
    renderAddWindowForm();
  }
}

function getSuitableTeachersForLesson(lesson) {
  const subjectName = String(lesson[keys.subject] || '').trim().toLowerCase();
  const lessonType = String(lesson[keys.type] || '').trim().toLowerCase();

  const subject = (sourceData['предметы'] || []).find(item => {
    const name = String(item['название'] || '').trim().toLowerCase();
    const type = String(item['тип занятия'] || '').trim();

    const normalizedType =
      type === '1' || type.toLowerCase() === 'лекция'
        ? 'лекция'
        : 'семинар';

    return name === subjectName && normalizedType === lessonType;
  });

  if (!subject) {
    return [];
  }

  return (sourceData['преподаватели'] || [])
    .filter(teacher =>
      (teacher['преподает предметы (id)'] || []).includes(subject.id)
    )
    .map(teacher => teacher['ФИО'])
    .filter(name => name && name !== lesson[keys.teacher]);
}

function renderReplacementTeacherSelectors() {
  const selectedLessonIds = selectedIds();

  const selectedLessons = (dynamicSchedule.lessons || []).filter(lesson =>
    selectedLessonIds.includes(String(lesson._id))
  );

  const box = document.getElementById('teacherReplacementBox');

  if (!box) return;

  if (!selectedLessons.length) {
    box.innerHTML = `
      <span class="hint">
        Выберите одну или несколько пар, чтобы назначить замену.
      </span>
    `;
    return;
  }

  box.innerHTML = selectedLessons.map(lesson => {
    const suitableTeachers = getSuitableTeachersForLesson(lesson);

    return `
      <div class="replacement-card">
        <div class="replacement-title">
          ${esc(lesson[keys.day])} · ${esc(lesson[keys.time])}
        </div>

        <div class="replacement-info">
          ${esc(lesson[keys.subject])} (${esc(lesson[keys.type])})<br>
          Группа: ${esc(lesson[keys.group])}<br>
          Сейчас ведёт: ${esc(lesson[keys.teacher])}
        </div>

        <label>Кем заменить эту пару</label>

        <select
          class="teacher-replacement-select"
          data-lesson-id="${esc(lesson._id)}"
        >
          <option value="">Автоматически подобрать преподавателя</option>
          ${suitableTeachers.map(teacher => `
            <option value="${esc(teacher)}">${esc(teacher)}</option>
          `).join('')}
        </select>
      </div>
    `;
  }).join('');
}

function renderTeacherLessonChecks(lessons, emptyText = 'Выберите преподавателя, чтобы увидеть его занятия') {
  return `
    <div class="list">
      ${
        lessons.length
          ? lessons.map(lesson => `
              <label class="check-line">
                <input
                  type="checkbox"
                  name="lessonPick"
                  value="${esc(lesson._id)}"
                  onchange="renderReplacementTeacherSelectors()"
                >
                <span>${esc(lessonLine(lesson))}</span>
              </label>
            `).join('')
          : `<span class="hint">${emptyText}</span>`
      }
    </div>
  `;
}

function renderReplaceTeacherForm() {
  const selectedTeacher =
    document.getElementById('currentTeacher')?.value || '';

  const lessons = selectedTeacher
    ? (dynamicSchedule.lessons || []).filter(lesson =>
        lesson[keys.teacher] === selectedTeacher
      )
    : [];

  actionForm.innerHTML = `
    <div>
      <label>Преподаватель, которого заменяем</label>
      <select id="currentTeacher" onchange="renderAction()">
        ${listOptions(options.teachers, 'Выберите преподавателя')}
      </select>
    </div>

    ${renderTeacherLessonChecks(
      lessons,
      'Выберите преподавателя, чтобы увидеть его занятия'
    )}

    <div id="teacherReplacementBox" class="replacement-list">
      <span class="hint">
        Выберите пару, чтобы увидеть список подходящих преподавателей.
      </span>
    </div>
  `;

  currentTeacher.value = selectedTeacher;
}

function renderRemoveLessonForm(current) {
  actionForm.innerHTML = `
    ${filtersHtml()}

    ${renderLessonChecks(filterLessons())}

    <div class="row">
      <label>
        <input
          type="checkbox"
          id="removeFull"
          checked
          onchange="moveFree.checked = !this.checked"
        >
        Полностью убрать занятие
      </label>

      <label>
        <input
          type="checkbox"
          id="moveFree"
          onchange="removeFull.checked = !this.checked"
        >
        Перенести занятие на свободное время
      </label>
    </div>
  `;

  restoreFilters(current);
}
function normalizeLessonType(value) {
  const text = String(value || '').trim().toLowerCase();

  if (text === '1' || text === 'лекция') {
    return 'лекция';
  }

  if (text === '0' || text === 'семинар') {
    return 'семинар';
  }

  return text;
}

function getSubjectIdByNameAndType(subjectName, lessonType) {
  const normalizedName = String(subjectName || '').trim().toLowerCase();
  const normalizedType = normalizeLessonType(lessonType);

  const subject = (sourceData['предметы'] || []).find(item => {
    const itemName = String(item['название'] || '').trim().toLowerCase();
    const itemType = normalizeLessonType(item['тип занятия']);

    return itemName === normalizedName && itemType === normalizedType;
  });

  return subject ? subject.id : null;
}

function getTeachersForSubjectAndType(subjectName, lessonType) {
  const subjectId = getSubjectIdByNameAndType(subjectName, lessonType);

  if (!subjectId) {
    return [];
  }

  return (sourceData['преподаватели'] || [])
    .filter(teacher =>
      (teacher['преподает предметы (id)'] || []).includes(subjectId)
    )
    .map(teacher => teacher['ФИО'])
    .filter(Boolean);
}

function getSelectedReplacementLesson() {
  const selectedLessonIds = selectedIds();

  if (!selectedLessonIds.length) {
    return null;
  }

  return (dynamicSchedule.lessons || []).find(lesson =>
    selectedLessonIds.includes(String(lesson._id))
  ) || null;
}

function updateReplacementTeachers() {
  const mode = document.getElementById('subjectMode')?.value || 'existing';
  const teacherBox = document.getElementById('replacementTeacherBox');

  if (!teacherBox) return;

  if (mode === 'custom') {
    teacherBox.innerHTML = `
      <label>Преподаватель</label>
      <select id="replacementTeacher">
        ${listOptions(options.teachers, 'Оставить как было')}
      </select>

      <span class="hint">
        Для своего занятия проверка преподавателя по предмету не выполняется.
      </span>
    `;
    return;
  }

  const selectedLesson = getSelectedReplacementLesson();
  const subjectSelect = document.getElementById('replacementSubject');

  if (!selectedLesson || !subjectSelect) {
    teacherBox.innerHTML = `
      <label>Преподаватель</label>
      <select id="replacementTeacher">
        <option value="">Сначала выберите пару</option>
      </select>
    `;
    return;
  }

  const selectedSubject = subjectSelect.value;
  const lessonType = selectedLesson[keys.type];

  const teachers = getTeachersForSubjectAndType(selectedSubject, lessonType);

  teacherBox.innerHTML = `
    <label>Преподаватель</label>
    <select id="replacementTeacher">
      ${listOptions(teachers, 'Автоматически подобрать преподавателя')}
    </select>
  `;
}

function renderReplaceLessonForm(current) {
  const mode = document.getElementById('subjectMode')?.value || 'existing';

  actionForm.innerHTML = `
    ${filtersHtml()}

    ${renderLessonChecks(filterLessons())}

    <label>На что заменить занятие</label>

    <select id="subjectMode" onchange="renderAction()">
      <option value="existing">Выбрать имеющийся предмет</option>
      <option value="custom">Добавить свой предмет</option>
    </select>

    <div id="subjectBox">
      ${
        mode === 'existing'
          ? `<select id="replacementSubject" onchange="updateReplacementTeachers()">
               ${listOptions(options.subjects, 'Выберите предмет')}
             </select>`
          : `<input id="replacementSubject" placeholder="Название нового занятия">`
      }
    </div>

    <div class="two">
      <div id="replacementTeacherBox">
        <label>Преподаватель</label>
        <select id="replacementTeacher">
          ${
            mode === 'custom'
              ? listOptions(options.teachers, 'Оставить как было')
              : '<option value="">Сначала выберите пару и предмет</option>'
          }
        </select>
      </div>

      <div>
        <label>Кабинет</label>
        <select id="replacementRoom">
          ${listOptions(options.rooms, 'Оставить как было')}
        </select>
      </div>
    </div>
  `;

  restoreFilters(current);
  subjectMode.value = mode;

  if (mode === 'existing') {
    updateReplacementTeachers();
  }
}

function renderAddWindowForm() {
  actionForm.innerHTML = `
    <div class="two">
      <div>
        <label>День</label>
        <select id="windowDay">
          ${days.map(day => `<option>${day}</option>`).join('')}
        </select>
      </div>

      <div>
        <label>Время</label>
        <input id="windowTime" placeholder="09:00 – 10:30">
      </div>

      <div>
        <label>Группа</label>
        <select id="windowGroup">
          ${listOptions(options.groups, 'Выберите группу')}
        </select>
      </div>
    </div>
  `;
}


/* =========================================================
   ПРИМЕНЕНИЕ ИЗМЕНЕНИЯ
   ========================================================= */

async function applyChange() {
  const action = actionType.value;

  let change = {
    action
  };

  if (action === 'replace_teacher') {
  const teacherMap = {};

  document
    .querySelectorAll('.teacher-replacement-select')
    .forEach(select => {
      teacherMap[select.dataset.lessonId] = select.value;
    });

  change = {
    ...change,
    lesson_ids: selectedIds(),
    teacher_by_lesson: teacherMap
  };
}

  if (action === 'remove_lesson') {
    change = {
      ...change,
      mode: moveFree?.checked ? 'move' : 'remove',
      lesson_ids: selectedIds()
    };
  }

  if (action === 'replace_lesson') {
    change = {
      ...change,
      subject: replacementSubject.value,
      teacher: replacementTeacher.value,
      room: replacementRoom.value,
      subject_mode: subjectMode.value,
      lesson_ids: selectedIds()
    };
  }

  if (action === 'add_window') {
    change = {
      ...change,
      day: windowDay.value,
      time: windowTime.value,
      group: windowGroup.value
    };
  }

  changeStatus.textContent = 'Пересобираю расписание...';
  changeStatus.className = 'status';

  const response = await fetch('/api/dynamic/apply', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      source_data: sourceData,
      schedule: dynamicSchedule,
      change
    })
  });

  const result = await response.json();

  if (!response.ok) {
    changeStatus.textContent = result.error;
    changeStatus.className = 'status error';
    return;
  }

  dynamicSchedule = result;

  await refreshOptions();

  fillDynamicGroupSelect();
  renderDynamicSchedule();
  renderAction();

  changeStatus.textContent = result.message || 'Новое расписание составлено';
  changeStatus.className = 'status ok';
}


/* =========================================================
   ЭКСПОРТ ДИНАМИЧЕСКОГО РАСПИСАНИЯ
   ========================================================= */

async function downloadDynamicCalendar() {
  downloadDynamicViaPost(
    '/api/calendar',
    { schedule: dynamicSchedule, repeat_weeks: 16 },
    'dynamic_schedule.ics'
  );
}

async function downloadDynamicExcel() {
  downloadDynamicViaPost(
    '/api/excel',
    { schedule: dynamicSchedule },
    'dynamic_schedule.xlsx'
  );
}

async function downloadDynamicPdf() {
  downloadDynamicViaPost(
    '/api/pdf',
    { schedule: dynamicSchedule },
    'dynamic_schedule.pdf'
  );
}

async function downloadDynamicViaPost(url, payload, filename) {
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    const result = await response.json();
    alert(result.error);
    return;
  }

  const blob = await response.blob();
  const link = document.createElement('a');

  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();

  URL.revokeObjectURL(link.href);
}


/* =========================================================
   ПЕРВИЧНЫЙ ЗАПУСК
   ========================================================= */

renderForm();
renderPreview();
fillDynamicGroupSelect();
renderDynamicSchedule();
renderAction();