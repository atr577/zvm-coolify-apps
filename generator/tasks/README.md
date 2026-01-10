# Tasks: Проект как шаблон + множественные ролики

Эта папка содержит задачи по разработке системы генерации видео.

## Структура

```
tasks/
├── 00-PLAN.md          # Общий план (архив)
├── README.md           # Этот файл
├── done/               # Завершённые задачи
│   ├── 01-backend-models.md
│   ├── 03-frontend-components.md
│   └── 04-frontend-pages.md
└── todo/               # Задачи в работе и ожидающие
    ├── 02-backend-api.md         # IN_PROGRESS
    ├── 05-integration-testing.md # IN_PROGRESS
    ├── 10-refactor-workflow.md   # TODO
    ├── 11-add-tests.md           # TODO
    ├── 12-async-celery.md        # TODO (blocked by 11)
    ├── 13-error-handling.md      # TODO
    ├── 14-data-deduplication.md  # TODO (blocked by 11)
    ├── 15-vps-deployment.md      # TODO
    ├── 16-prompt-preview-edit.md # TODO
    └── REFACTORING.md            # Meta-план рефакторинга
```

---

## Статус задач

### Done (3)

| # | Задача | Описание |
|---|--------|----------|
| 01 | Backend Models | Project, Video, WorkflowStep, ValidationResult models |
| 03 | Frontend Components | ProjectCard, VideoCard, ProjectForm, VideoVariantSelector |
| 04 | Frontend Pages | Dashboard, ProjectEdit, CreateVideo, VideoDetail |

### In Progress (2)

| # | Задача | Что осталось |
|---|--------|--------------|
| 02 | Backend API | Template vs non-template logic, auto-generate endpoint |
| 05 | Integration Testing | Test cases execution, cleanup |

### Todo (7)

| # | Задача | Приоритет | Блокеры |
|---|--------|-----------|---------|
| 10 | Refactor workflow.py | P1 | - |
| 11 | Add Tests | P1 | - |
| 12 | Async Celery | P2 | Task 11 |
| 13 | Error Handling | P2 | - |
| 14 | Data Deduplication | P2 | Task 11 |
| 15 | VPS Deployment | P3 | - |
| 16 | Prompt Preview/Edit | P3 | - |

---

## Связанные документы

Новая документация по workflow находится в `docs/`:

- [TARGET_WORKFLOW.md](../docs/TARGET_WORKFLOW.md) — целевая архитектура workflow
- [WORKFLOW_ANALYSIS.md](../docs/WORKFLOW_ANALYSIS.md) — анализ текущего состояния + баги
- [IMPLEMENTATION_PLAN.md](../docs/IMPLEMENTATION_PLAN.md) — план миграции на новый workflow
- [AUDIT_REPORT_2026_01_10.md](../docs/AUDIT_REPORT_2026_01_10.md) — аудит документации vs код

---

## Приоритеты (актуальные)

**Из IMPLEMENTATION_PLAN.md:**

1. **Phase 0: Security** — Fix metrics auth (CRITICAL)
2. **Phase 1: Broken Features** — Engagement rate, generate_meta duplicate
3. **Phase 2: Data Model** — StepAttempt/Variant hierarchy
4. **Phase 3: Breakpoints** — workflow_mode fix
5. **Phase 4: API Unification** — Unified endpoint pattern
6. **Phase 5: Publishing** — is_published, auto-retry
7. **Phase 6: Cleanup** — Remove deprecated code

---

**Обновлено:** 2026-01-10
