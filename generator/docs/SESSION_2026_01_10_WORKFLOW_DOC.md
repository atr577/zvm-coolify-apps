# Session Summary: TARGET_WORKFLOW.md Finalization

**Date:** 2026-01-10
**Document:** TARGET_WORKFLOW.md
**Status:** Ready for implementation

---

## Key Decisions Made

### 1. State Model
- **REJECTED is an action, not a state** — нет статуса REJECTED нигде
- **Video statuses:** PENDING, IN_PROGRESS, AWAITING_APPROVAL, COMPLETED, FAILED
- **WorkflowStep statuses:** PENDING, IN_PROGRESS, AWAITING_APPROVAL, APPROVED, FAILED
- **StepAttempt statuses:** PENDING, SUCCESS, FAILED

### 2. Concurrency
- **Принцип:** Первый запрос выигрывает, остальные 409 Conflict
- **Video-level lock:** `with_for_update()` при `/auto-generate-to-video`
- **Step-level lock:** `with_for_update()` при approve/regenerate/select

### 3. API Naming Convention
- **Паттерн:** `/workflow/{video_id}/{step_type}/action`
- **step_type:** STORY, DESCRIPTION, PROMPT, IMAGE, SCENARIO, VIDEO, AUDIO
- **Унификация:** все операции над шагами используют этот паттерн

### 4. Variant Model
- **AUTO mode создаёт Variant записи** (1 шт) — для консистентности данных
- **Content копируется в Video при approve**, не при select
- **select-variant** — только отмечает выбор, данные не копируются

### 5. Discover vs Remix
- **Discover:** creative_inputs (свободные параметры) → LLM генерирует креативно
- **Remix:** templates + content_variables → string replacement
- **Все комбинации валидны:** Discover+AUTO, Discover+MANUAL, Remix+AUTO, Remix+MANUAL

### 6. Remix PREPARE
- **Auto-fill из suggestions:** если user не указал переменную
- **Batch mode:** round-robin (равномерное покрытие комбинаций)
- **Single mode:** LLM выбирает лучшее для контекста
- **Валидация при создании Project:** все placeholders должны иметь suggestions

### 7. Rollback
- **Стандартная логика работает для всех шагов**, включая AUDIO
- **После rollback:** target step → AWAITING_APPROVAL
- **Запрещён после публикации:** is_published = true блокирует rollback

### 8. Publishing
- **is_published flag:** true после первой успешной публикации
- **Auto-retry до успеха**, кроме permanent errors (NO_AUTH, BANNED, CONTENT_REJECTED)
- **После публикации:** только update meta, rollback запрещён

### 9. Timeouts
- **Backend контролирует timeout**, не frontend
- **STEP_TIMEOUT:** VIDEO = 20 min, остальные 2-5 min
- **Frontend:** просто polling до terminal status

### 10. publishing_meta
- **LLM генерирует** при approve AUDIO шага
- **Контекст:** story_data, description_data, platforms
- **Output:** viral-optimized titles, descriptions, hashtags для каждой платформы

---

## TBD Items (отложено)

| Item | Описание |
|------|----------|
| Batch API | Способ создания множества Remix видео |
| Template Builder UI | Entry points, user flow |
| Variant.content structure | Точная схема для каждого step type |
| AI Validation | Отложено, только структурная валидация |

---

## Architecture Insights

### Data Flow
```
Discover: creative_inputs → LLM → story_data → ... → video
Remix: templates + content_variables → PREPARE → prompt_data/scenario_data → video
```

### Status Flow (MANUAL)
```
PENDING → IN_PROGRESS → AWAITING_APPROVAL → (approve) → IN_PROGRESS → ... → COMPLETED
                              ↓
                        (regenerate) → IN_PROGRESS
```

### Hierarchy
```
Video
  └── WorkflowStep (один на step type)
        └── StepAttempt (одна попытка генерации)
              └── Variant (1 или N результатов)
```

---

## API Endpoints Summary

### Workflow Operations
```
POST /workflow/auto-generate-to-video        # Start/continue generation
POST /workflow/{video_id}/{step}/select-variant
POST /workflow/{video_id}/{step}/approve
POST /workflow/{video_id}/{step}/reject
POST /workflow/{video_id}/{step}/regenerate
POST /workflow/{video_id}/{step}/retry
GET  /workflow/{video_id}/{step}/variants
POST /workflow/{video_id}/rollback-to/{step}
```

### Publishing
```
POST /publish/{video_id}                     # Publish to platform
PUT  /publish/{video_id}/{platform}/meta     # Update meta
```

---

## Critical Rules

1. **Rollback после публикации запрещён**
2. **AUTO mode всё равно создаёт Variant записи**
3. **Content копируется в Video только при approve**
4. **Publishing retry до успеха** (кроме permanent errors)
5. **Backend контролирует timeout**, не frontend
6. **Все placeholder должны иметь suggestions** (валидация при создании project)

---

## Document Quality

**Final state:** 17 секций, консистентные API paths, все flows описаны

**Проверено:**
- ✅ Нет дублирования секций
- ✅ API paths консистентны
- ✅ State machine корректна
- ✅ Все комбинации (project_type × mode) описаны
- ✅ Error handling и timeouts документированы
- ✅ Publishing flow с is_published flag
- ✅ Frontend integration обновлён
- ✅ Checklist актуален

---

## Next Steps

1. **Имплементация** по документу
2. **Batch API** — определить при необходимости
3. **Template Builder UI** — дизайн flow
4. **AI Validation** — добавить позже
