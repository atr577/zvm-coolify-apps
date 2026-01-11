# GAP Analysis: Current State vs TARGET_WORKFLOW.md

**Дата:** 2026-01-10
**Цель:** Определить все расхождения между текущим кодом и спецификацией

---

## 1. Матрица Flows

| Flow | Спека | Текущее | Статус |
|------|-------|---------|--------|
| Discover + AUTO | 7 шагов без пауз → COMPLETED | Частично работает | ⚠️ |
| Discover + MANUAL | Пауза после каждого шага, approve → auto-start next | Не auto-start | ❌ |
| Remix + AUTO | PREPARE → 3 шага без пауз | PREPARE не вызывается | ❌ |
| Remix + MANUAL | PREPARE → 3 шага с паузами | Сломан полностью | ❌ |

---

## 2. Models

### Video (L477-483)

| Поле | Спека | Текущее | GAP |
|------|-------|---------|-----|
| `workflow_mode` | `AUTO \| MANUAL` | ✅ Есть | — |
| `creative_inputs` | Discover: theme, mood, etc. | ❌ Нет | Добавить |
| `content_variables` | Remix: значения placeholders | ✅ Есть | — |
| `status` | State machine (L489-509) | ⚠️ Есть, но transitions кривые | Исправить |
| `current_step` | Текущий шаг | ✅ Есть | — |

### Project - Remix (L432-440)

| Поле | Спека | Текущее | GAP |
|------|-------|---------|-----|
| `source_video_ids` | int[] | ✅ Есть | — |
| `prompt_template` | string с {placeholders} | ❌ Используется `story_template` | Переименовать или алиас |
| `scenario_template` | JSON с {placeholders} | ✅ Есть | — |
| `placeholders` | string[] | ✅ Есть | — |
| `placeholder_suggestions` | JSON | ✅ Есть | — |

**Валидация (L289-303):**
- ❌ Remix проект создаётся БЕЗ обязательного `scenario_template`
- ⚠️ `placeholder_suggestions` валидация есть частично

### WorkflowStep / StepAttempt / Variant (L594-641)

| Модель | Спека | Текущее | GAP |
|--------|-------|---------|-----|
| WorkflowStep | step_type, status, selected_variant_id | ✅ Есть | — |
| StepAttempt | attempt_number, parent_variant_id, feedback | ✅ Есть | Не используется |
| Variant | content, is_selected | ✅ Есть | Не используется |

**Критично:** Модели есть, но workflow НЕ создаёт StepAttempt/Variant — сохраняет данные напрямую в Video.

---

## 3. API Contract

### Спека (L1156-1391)

| Endpoint | Спека | Текущее | GAP |
|----------|-------|---------|-----|
| `POST /workflow/auto-generate-to-video` | Запуск workflow | ✅ Есть | — |
| `GET /videos/{id}` | Polling status | ✅ Есть | — |
| `POST /workflow/{video_id}/{step}/approve` | Approve шага | ❌ Нет | Есть `POST /workflow/approve-step` (by step_id) |
| `POST /workflow/{video_id}/{step}/select-variant` | Выбор варианта | ❌ Нет | — |
| `POST /workflow/{video_id}/{step}/regenerate` | Regenerate | ❌ Нет | Есть разные endpoints |
| `GET /workflow/{video_id}/{step}/variants` | Получить варианты | ❌ Нет | — |
| `POST /workflow/{video_id}/rollback-to/{step}` | Rollback | ❌ Нет | — |

**Критично:** API структура не соответствует спеке. URL pattern `/{video_id}/{step}/action` не реализован.

### Response Contract

| Поле | Спека | Текущее | GAP |
|------|-------|---------|-----|
| `continue_workflow` | При approve → true | ⚠️ Частично | Не для всех handlers |
| `next_step` | Следующий шаг | ❌ Нет | — |
| `auto_continue` | Frontend должен auto-start | ❌ Не реализовано | — |

---

## 4. PREPARE Phase (L242-287)

| Аспект | Спека | Текущее | GAP |
|--------|-------|---------|-----|
| Когда вызывается | В начале Remix workflow | ❌ Не вызывается при старте | Вызывать в orchestrator |
| Что делает | Заполняет prompt_data + scenario_data | ⚠️ Частично | scenario_data не заполняется если нет template |
| Валидация | Все placeholders должны быть | ❌ Нет | — |

---

## 5. State Machine (L487-565)

### Video.status transitions

| Transition | Спека | Текущее | GAP |
|------------|-------|---------|-----|
| PENDING → IN_PROGRESS | При старте | ✅ Работает | — |
| IN_PROGRESS → AWAITING_APPROVAL | MANUAL: шаг готов | ⚠️ Работает | — |
| AWAITING_APPROVAL → IN_PROGRESS | После approve | ❌ Не меняется | Исправить |
| IN_PROGRESS → COMPLETED | AUTO: все шаги | ✅ Работает | — |

### Step transitions (L539-542)

| Паттерн | Спека | Текущее |
|---------|-------|---------|
| Шаг готов → AWAITING_APPROVAL | ✅ | ✅ |
| Approve → IN_PROGRESS, current_step = next | ✅ | ❌ current_step меняется, статус нет |
| Approve → auto-start next step | ✅ | ❌ Нужен ручной клик |

---

## 6. Frontend (L1394-1506)

### Polling (L1396-1433)

| Аспект | Спека | Текущее | GAP |
|--------|-------|---------|-----|
| Polling interval | 3 сек | ✅ Есть | — |
| Stop on AWAITING_APPROVAL | Показать UI | ⚠️ Работает | — |
| После approve | Auto-call generate | ❌ Не работает | Исправить |

### Lifecycle (L1436-1453)

| Шаг | Спека | Текущее |
|-----|-------|---------|
| 1. Создать Video | ✅ | ✅ |
| 2. Выбрать mode | ✅ | ✅ |
| 3. Generate → polling | ✅ | ✅ |
| 4. AWAITING → GET variants | ❌ | Нет endpoint |
| 5. Select variant | ❌ | Нет endpoint |
| 6. Approve → auto-continue | ❌ | Не работает |

---

## 7. Variants (L442-470)

| Аспект | Спека | Текущее | GAP |
|--------|-------|---------|-----|
| IMAGE: 3 варианта | MANUAL mode | ❌ Всегда 1 | Реализовать |
| AUDIO: 3 варианта | MANUAL mode | ⚠️ Есть audio_variants | Унифицировать с Variant model |
| AUTO: 1 вариант | Всегда | ✅ Работает | — |
| Select → Approve flow | L677-721 | ❌ Нет | Реализовать |

---

## 8. Приоритеты фиксов

### P0: Блокеры (без этого ничего не работает)

1. **State transitions** — approve должен менять status + auto-start next
2. **API contract** — endpoint pattern `/{video_id}/{step}/action`
3. **PREPARE phase** — вызывать для Remix при старте

### P1: Core функционал

4. **Variants** — генерация N вариантов, select-variant endpoint
5. **Remix validation** — требовать scenario_template
6. **Frontend approve flow** — auto-continue после approve

### P2: Дополнительно

7. **Rollback** — endpoint + логика
8. **StepAttempt/Variant** — использовать модели вместо прямого сохранения
9. **creative_inputs** — добавить поле для Discover

---

## 9. Решение: Rewrite vs Refactor

| Компонент | Решение | Причина |
|-----------|---------|---------|
| Models | Refactor | 80% полей есть, добавить недостающие |
| Backend API | **Rewrite** | Структура endpoints не та, проще переписать workflow.py |
| Orchestrator | Refactor | Логика есть, добавить PREPARE + transitions |
| Frontend hooks | Refactor | useVideoWorkflow нужен, исправить flow |
| Frontend components | Refactor | Компоненты есть, исправить логику |

---

## 10. Порядок реализации

```
1. Backend: новые API endpoints (по спеке)
2. Backend: state transitions fix
3. Backend: PREPARE phase integration
4. Frontend: подключить к новым endpoints
5. Frontend: auto-continue после approve
6. Test: Discover + AUTO
7. Test: Discover + MANUAL
8. Test: Remix + AUTO
9. Test: Remix + MANUAL
```
