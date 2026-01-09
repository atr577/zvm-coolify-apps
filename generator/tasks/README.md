# План реализации: Проект как шаблон + множественные ролики

Эта папка содержит детальный план работ по переходу от модели "1 проект = 1 ролик" к модели "1 проект = N роликов".

## Структура задач

### [00-PLAN.md](./00-PLAN.md) - Общий план
Высокоуровневое описание концепции, архитектуры и workflow.

**Основная идея:**
- **Проект** = Шаблон концепции (Story Template + настройки)
- **Video** = Контентная вариация (конкретные параметры)
- **Template Video** = первый ролик с полным контролем всех этапов
- **Обычные ролики** = автогенерация до видео, ревью только финального результата

---

### [01-backend-models.md](./01-backend-models.md) - Backend: Database Models
**Phase 1** • **Оценка:** 2-3 часа

- Drop существующих таблиц (начинаем с чистого листа)
- Новые модели: Project, Video, WorkflowStep, ValidationResult
- Alembic миграции
- Pydantic схемы

**Зависимости:** Нет

---

### [02-backend-api.md](./02-backend-api.md) - Backend: API Endpoints
**Phase 2** • **Оценка:** 4-6 часов

- Projects CRUD API
- Videos CRUD API
- AI Content Generation API (генерация 10 вариантов)
- Workflow API (переписать для работы с video_id)
- OpenAI Service (новые методы)

**Зависимости:** Task 01

---

### [03-frontend-components.md](./03-frontend-components.md) - Frontend: Components
**Phase 3** • **Оценка:** 4-5 часов

- ProjectCard (раскрываемая карточка проекта)
- VideoCard (карточка ролика)
- ProjectForm (создание/редактирование проекта)
- VideoVariantSelector (выбор из 10 вариантов)
- VideoWorkflowView (просмотр этапов с деталями)
- TypeScript типы

**Зависимости:** Task 02

---

### [04-frontend-pages.md](./04-frontend-pages.md) - Frontend: Pages
**Phase 4** • **Оценка:** 3-4 часа

- Dashboard (новый, с раскрываемыми проектами)
- ProjectEdit (редактирование шаблона)
- CreateVideo (выбор варианта контента)
- VideoDetail (просмотр/редактирование ролика)
- API клиент (обновленный)
- Роутинг

**Зависимости:** Task 03

---

### [05-integration-testing.md](./05-integration-testing.md) - Integration & Testing
**Phase 5** • **Оценка:** 2-3 часа

- Автогенерация для обычных роликов
- Логика Approve → Adaptation → Publishing
- Полное тестирование всех flow
- Cleanup и оптимизация
- Обновление документации

**Зависимости:** Task 01, 02, 03, 04

---

## Общая оценка времени

**Итого:** ~15-21 час чистой разработки

- Phase 1 (Backend Models): 2-3 часа
- Phase 2 (Backend API): 4-6 часов
- Phase 3 (Frontend Components): 4-5 часов
- Phase 4 (Frontend Pages): 3-4 часа
- Phase 5 (Integration): 2-3 часа

## Порядок выполнения

1. ✅ Обсудили концепцию
2. ✅ Создали план и задачи
3. ⏳ **Начать с Task 01** (Backend Models)
4. ⏳ Task 02 (Backend API)
5. ⏳ Task 03 (Frontend Components)
6. ⏳ Task 04 (Frontend Pages)
7. ⏳ Task 05 (Integration)

## Ключевые решения

### UI Flow

```
Dashboard
  ├─ [+ Создать проект]
  │    └─ Форма создания → Сразу редирект на CreateVideo
  │
  └─ Раскрываемые карточки проектов
       ├─ Preview последних роликов
       ├─ [+ Новый ролик] → CreateVideo
       └─ [⚙️ Настройки] → ProjectEdit

CreateVideo
  ├─ AI генерирует 10 вариантов (текстом)
  ├─ Пользователь выбирает 1
  └─ Редирект на VideoDetail

VideoDetail
  ├─ Template Video → полный workflow (8 этапов с checkpoints)
  └─ Обычный ролик → автогенерация до видео → approve/reject/edit
```

### Database Schema

```
Project (шаблон)
  ├─ id, name, description
  ├─ story_template
  └─ platforms, duration

Video (ролик)
  ├─ id, project_id, title
  ├─ is_template (bool)
  ├─ content_variables (JSON)
  └─ story_data, description_data, image_prompt,
      image_url, scenario_data, video_url, adaptation_data

WorkflowStep
  ├─ id, video_id (FK -> Video)
  ├─ step_type, status, content
  └─ prompt_used, generation_time_seconds
```

### Template Video vs Обычный ролик

| | Template Video | Обычный ролик |
|---|---|---|
| **is_template** | true | false |
| **Workflow** | Все 8 этапов с checkpoints | Автогенерация 1-6, ревью на 6 |
| **Когда создается** | Первый в проекте (автоматически) | Все последующие |
| **Можно сделать template** | Да (изначально) | Да (через настройки) |
| **Количество** | Может быть несколько (A/B тест) | Любое количество |

---

## Начало работы

```bash
# 1. Перейти к Task 01
cd tasks
cat 01-backend-models.md

# 2. Удалить старую БД
rm backend/data/app.db

# 3. Начать реализацию
cd backend
# ... следовать инструкциям в Task 01
```

---

**Дата создания:** 2026-01-08
**Статус:** В разработке
