# План реализации: Проект как шаблон + множественные ролики

## Концепция

**Проект** = Шаблон концепции (Story Template + настройки)
**Video** = Контентная вариация (девушка + авто + локация + время)

## Ключевые изменения архитектуры

### До (текущая версия):
```
Project (1 проект = 1 ролик)
  └── WorkflowStep (этапы генерации)
```

### После (новая версия):
```
Project (шаблон/контейнер)
  └── Video (много роликов)
        └── WorkflowStep (этапы для каждого ролика)
```

## Workflow

### 1. Создание проекта
- Название, описание
- Story Template (концепция ролика)
- Platforms (Instagram, TikTok, YouTube)
- Duration (5, 10, 15 секунд)
- → Сразу после создания → создание первого ролика

### 2. Создание первого ролика (Template Video)
- AI анализирует Story Template
- Генерирует 10 вариантов контента (текстом)
- Пользователь выбирает 1 вариант
- Проходит ВСЕ 8 этапов с checkpoints:
  1. Story
  2. Description
  3. Prompt
  4. Image
  5. Scenario
  6. Video
  7. Adaptation
  8. Publishing
- Автоматически помечается как `is_template = True`

### 3. Создание последующих роликов (обычные)
- AI генерирует 10 новых вариантов
- Пользователь выбирает 1 вариант
- Автоматическая генерация этапов 1-6 БЕЗ checkpoints
- Останавливается на Step 6 (Video) → ждет approve
- После approve:
  - ✓ Approve → автоматом Step 7 → Step 8
  - ✗ Reject → 3 опции:
    - 🔄 Быстрая регенерация (с фидбеком)
    - ✏️ Ручное редактирование (полный workflow)
    - 🗑️ Удалить ролик

### 4. Template Video - управление
- Первый ролик автоматически = template
- Любой обычный ролик можно "повысить" до template через настройки
- Можно иметь несколько template videos для A/B теста

## UI Структура

### Dashboard
```
▼ 📁 Девушки и авто
┌─────────────────────────────────────────┐
│ 5 роликов • 3 опубликовано             │
│                                         │
│ Ролики:                                 │
│ • 🎬 Париж, закат - ✅ Опубликован     │
│ • 🎬 Дубай, ночь - 🔄 Генерация видео  │
│ • 🎬 LA, день - 📝 Черновик            │
│                                         │
│ [+ Новый ролик] [⚙️ Настройки]         │
└─────────────────────────────────────────┘

▶ 📁 Рецепты аэрогриля (12 роликов)
▶ 📁 Бостон терьеры (3 ролика)

[+ Создать новый проект]
```

### Project Detail (редактирование шаблона)
```
[< Назад к проектам]

Проект: "Девушки и авто"

Story Template:
┌────────────────────────────────────────┐
│ Элегантная девушка выходит из авто... │
└────────────────────────────────────────┘

Platforms: ☑ Instagram ☑ TikTok ☐ YouTube
Duration: ○ 5 сек ● 10 сек ○ 15 сек

[Сохранить изменения]
```

### Video Detail (просмотр ролика)
```
Video: "Блондинка, Ferrari, Париж, закат"
Проект: Девушки и авто

▼ Step 1: Story ✅
  Промпт: "Generate story based on..."
  Результат: {...}
  Время генерации: 3.2 сек

▶ Step 2: Description ✅
▶ Step 3: Prompt ✅
▶ Step 4: Image ✅
▼ Step 5: Scenario ⚙️ Генерируется...
  Промпт: "Create scenario for..."
  Отправлено: 2 сек назад

▶ Step 6: Video ⏳ Ожидание
...
```

## Database Schema

```python
Project:
  - id, name, description
  - story_template
  - platforms (JSON)
  - duration (int)

Video:
  - id, project_id (FK)
  - title
  - is_template (bool)
  - template_video_id (FK -> Video, optional)
  - content_variables (JSON)
  - story_data, description_data, image_prompt,
    image_url, scenario_data, video_url, adaptation_data
  - current_step, status

WorkflowStep:
  - id, video_id (FK -> Video)
  - step_type, status, content
  - user_approved, user_feedback
  - prompt_used, generation_time_seconds

ValidationResult:
  - id, step_id (FK -> WorkflowStep)
  - status, score, criteria_results
  - warnings, errors, recommendations
```

## Этапы реализации

### Phase 1: Backend - Database & Models
- Новые модели SQLAlchemy
- Alembic: drop все таблицы + создание новых
- Тесты моделей (опционально)

### Phase 2: Backend - API Endpoints
- Projects CRUD
- Videos CRUD
- AI Generation endpoints
- Workflow endpoints

### Phase 3: Frontend - Components
- ProjectCard (раскрываемая карточка)
- VideoCard (карточка ролика)
- ProjectForm (создание/редактирование проекта)
- VideoVariantSelector (выбор из 10 вариантов)
- VideoWorkflowView (просмотр этапов с деталями)

### Phase 4: Frontend - Pages
- Dashboard (новый, с раскрываемыми проектами)
- ProjectDetail (редактирование шаблона)
- VideoDetail (просмотр/редактирование ролика)

### Phase 5: Integration & Testing
- Полный flow: создание проекта → template video → обычные ролики
- Тестирование всех сценариев
- Отладка и фиксы

## Оценка времени

- Phase 1: 2-3 часа
- Phase 2: 4-6 часов
- Phase 3: 4-5 часов
- Phase 4: 3-4 часа
- Phase 5: 2-3 часа

**Итого: ~15-21 час чистой разработки**

## Следующие шаги

1. ✅ Обсудили концепцию
2. ⏳ Создать задачи по этапам
3. ⏳ Начать реализацию с Phase 1

---

**Создано:** 2026-01-08
**Статус:** В разработке
