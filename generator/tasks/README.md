# Tasks: Video Generation System

Эта папка содержит задачи по разработке системы генерации видео.

## Структура

```
tasks/
├── 00-PLAN.md              # Архив: исходный план
├── README.md               # Этот файл
├── done/                   # Завершённые задачи
│   ├── 01-backend-models.md
│   ├── 03-frontend-components.md
│   └── 04-frontend-pages.md
└── todo/                   # Задачи в работе
    │
    │── [Original Tasks]
    ├── 02-backend-api.md           # IN_PROGRESS
    ├── 05-integration-testing.md   # IN_PROGRESS
    ├── 10-refactor-workflow.md     # TODO
    ├── 11-add-tests.md             # TODO
    ├── 12-async-celery.md          # TODO (blocked by 11)
    ├── 13-error-handling.md        # TODO
    ├── 14-data-deduplication.md    # TODO (blocked by 11)
    ├── 15-vps-deployment.md        # TODO
    ├── 16-prompt-preview-edit.md   # TODO
    ├── REFACTORING.md              # Meta-план
    │
    │── [Workflow Migration - NEW]
    ├── 20-security-fix.md          # P0 CRITICAL - 5h
    ├── 21-fix-broken-features.md   # P1 HIGH - 6h
    ├── 22-data-model-variants.md   # P1 HIGH - 8h
    ├── 23-breakpoints-system.md    # P1 HIGH - 6h
    ├── 24-api-unification.md       # P2 MEDIUM - 14h
    ├── 25-publishing-rollback.md   # P2 MEDIUM - 5.5h
    └── 26-cleanup.md               # P3 LOW - 5.5h
```

---

## Workflow Migration (Tasks 20-26)

> **Источник:** [IMPLEMENTATION_PLAN.md](../docs/IMPLEMENTATION_PLAN.md)

Миграция на новую архитектуру workflow из TARGET_WORKFLOW.md.

### Приоритеты

| Phase | Task | Описание | Effort | Зависимости |
|-------|------|----------|--------|-------------|
| **0** | 20-security-fix | Metrics auth fix | 5h | - |
| **1** | 21-fix-broken-features | Engagement rate, generate_meta | 6h | Phase 0 |
| **2** | 22-data-model-variants | StepAttempt → Variant hierarchy | 8h | Phase 1 |
| **3** | 23-breakpoints-system | workflow_mode работает | 6h | Phase 2 |
| **4** | 24-api-unification | Unified API pattern | 14h | Phase 2,3 |
| **5** | 25-publishing-rollback | is_published, auto-retry | 5.5h | Phase 4 |
| **6** | 26-cleanup | Remove deprecated code | 5.5h | Phase 5 |

**Total:** ~50h

### Порядок выполнения

```
Phase 0 (Security) ─────────────────────────────────────────┐
     │                                                       │
     ▼                                                       │
Phase 1 (Fix Broken) ───────────────────────────────────────┤
     │                                                       │
     ▼                                                       │
Phase 2 (Data Model) ──────┬───────────────────────────────┤
     │                     │                                 │
     ▼                     ▼                                 │
Phase 3 (Breakpoints)    Phase 4 (API) ────────────────────┤
     │                     │                                 │
     └─────────┬───────────┘                                │
               │                                             │
               ▼                                             │
         Phase 5 (Publishing) ──────────────────────────────┤
               │                                             │
               ▼                                             │
         Phase 6 (Cleanup) ─────────────────────────────────┘
```

---

## Original Tasks (01-16)

### Done (3)

| # | Задача | Описание |
|---|--------|----------|
| 01 | Backend Models | Project, Video, WorkflowStep models |
| 03 | Frontend Components | ProjectCard, VideoCard, forms |
| 04 | Frontend Pages | Dashboard, VideoDetail pages |

### In Progress (2)

| # | Задача | Что осталось |
|---|--------|--------------|
| 02 | Backend API | Template logic, auto-generate |
| 05 | Integration Testing | Test execution, cleanup |

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

## Рекомендуемый порядок

**Сейчас критично (начать с этого):**
1. **Task 20** - Security fix (CRITICAL)
2. **Task 21** - Fix broken features

**После security:**
3. **Task 22** - Data model (Variant hierarchy)
4. **Task 23** - Breakpoints system

**Рефакторинг:**
5. **Task 24** - API unification
6. **Task 10** - Refactor workflow.py (может пересекаться с 22-24)

---

## Связанные документы

- [TARGET_WORKFLOW.md](../docs/TARGET_WORKFLOW.md) — целевая архитектура
- [WORKFLOW_ANALYSIS.md](../docs/WORKFLOW_ANALYSIS.md) — текущие баги
- [IMPLEMENTATION_PLAN.md](../docs/IMPLEMENTATION_PLAN.md) — план миграции
- [AUDIT_REPORT_2026_01_10.md](../docs/AUDIT_REPORT_2026_01_10.md) — аудит

---

**Обновлено:** 2026-01-10
