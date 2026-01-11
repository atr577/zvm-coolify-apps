# T2: Discover + MANUAL Flow

**Status:** todo
**Priority:** P0
**Created:** 2026-01-10

## Цель
Discover + MANUAL: пауза после каждого шага, user approve → auto-continue к следующему.

## Ожидаемый результат для пользователя
User контролирует каждый шаг: видит результат → approve → следующий шаг генерируется автоматически. Для IMAGE и AUDIO — выбор из 3 вариантов. Никаких лишних кликов между approve и генерацией.

---

## Backend Checklist

### API Endpoints (app/api/workflow_v2.py)
- [ ] `GET /api/workflow/{video_id}/{step}/variants` — получить варианты
- [ ] `POST /api/workflow/{video_id}/{step}/select` — выбрать вариант
- [ ] `POST /api/workflow/{video_id}/{step}/approve` — approve + auto_continue
- [ ] `POST /api/workflow/{video_id}/{step}/reject` — для аналитики
- [ ] `POST /api/workflow/{video_id}/{step}/regenerate` — с feedback

### Orchestrator
- [ ] MANUAL mode: pause после каждого шага
- [ ] `Video.status = AWAITING_APPROVAL` после генерации шага
- [ ] IMAGE: генерация 3 вариантов
- [ ] AUDIO: генерация 3 вариантов
- [ ] Остальные шаги: 1 вариант

### Approve Logic
- [ ] При approve: копировать variant.content → Video.{field}
- [ ] Возвращать `auto_continue: true` если не последний шаг
- [ ] Возвращать `next_step` для информации

### Tests
- [ ] tests/test_discover_manual.py

---

## Frontend Checklist

### API Layer (src/services/api.ts)
- [x] `workflowApi.getVariants(videoId, stepType)`
- [x] `workflowApi.selectVariant(videoId, stepType, variantId)`
- [x] `workflowApi.approveStepV2(videoId, stepType)`
- [x] `workflowApi.rejectStep(videoId, stepType, reason)`
- [x] `workflowApi.regenerateStep(videoId, stepType, variantId, feedback)`

### Hook — useVideoWorkflow.ts ПОЛНАЯ ПЕРЕРАБОТКА
- [ ] `approveStepMutation` — вызывает approveStepV2, при `auto_continue` вызывает startWorkflow
- [ ] `selectVariantMutation` — выбор варианта
- [ ] `regenerateMutation` — regenerate с feedback
- [ ] `variantsQuery` — получение вариантов для текущего шага

### VideoDetail.tsx
- [ ] При `status === 'awaiting_approval'` — показать ApprovalView
- [ ] Polling останавливается на awaiting_approval

### НОВЫЙ КОМПОНЕНТ: ApprovalView.tsx
- [ ] Определить тип шага из `video.current_step`
- [ ] Если 1 вариант → SingleVariantApproval
- [ ] Если N вариантов → MultiVariantSelector

### НОВЫЙ КОМПОНЕНТ: SingleVariantApproval.tsx
- [ ] Показать content варианта (текст для STORY/DESCRIPTION/PROMPT/SCENARIO, картинка для IMAGE, видео для VIDEO)
- [ ] Кнопки: Approve, Regenerate
- [ ] Input для feedback при regenerate

### НОВЫЙ КОМПОНЕНТ: MultiVariantSelector.tsx
- [ ] Grid из N вариантов (картинки или audio players)
- [ ] Выбор варианта (highlight selected)
- [ ] Кнопки: Approve Selected, Regenerate

### НОВЫЙ КОМПОНЕНТ: VariantCard.tsx
- [ ] Рендер варианта по типу: image, video, audio, text
- [ ] Selected state styling

### StepContentRenderer.tsx (utility)
- [ ] Рендер content по step_type:
  - STORY, DESCRIPTION, PROMPT, SCENARIO → JSON viewer или formatted text
  - IMAGE → `<img>`
  - VIDEO → `<video>`
  - AUDIO → `<audio>` player

---

## E2E Критерии

1. [ ] Создать Discover проект + Video (MANUAL)
2. [ ] Generate → STORY генерируется → AWAITING_APPROVAL
3. [ ] UI показывает story content + Approve/Regenerate
4. [ ] Approve → автоматически DESCRIPTION генерируется
5. [ ] Пройти все 7 шагов
6. [ ] На IMAGE: показаны 3 картинки, выбор + approve
7. [ ] На AUDIO: показаны 3 audio, выбор + approve
8. [ ] После AUDIO approve → COMPLETED

---

## Тестирование

```bash
# Backend
cd backend && venv/bin/pytest tests/test_discover_manual.py -v

# Frontend
cd frontend && npm run build

# E2E Manual
1. Login
2. Create Discover project
3. Create Video (MANUAL mode)
4. Click Generate
5. Approve each step (7 times)
6. On IMAGE: select from 3 variants
7. On AUDIO: select from 3 variants
8. Verify completed video
```

---

## Файлы

### Backend
- `app/api/workflow_v2.py` — endpoints done, approve logic TODO
- `app/services/workflow/orchestrator_v2.py` — MANUAL pause TODO
- `tests/test_discover_manual.py` — TODO

### Frontend (ВСЕ TODO)
- `src/hooks/useVideoWorkflow.ts` — переработка
- `src/pages/VideoDetail.tsx` — awaiting_approval handling
- `src/components/video/ApprovalView.tsx` — NEW
- `src/components/video/SingleVariantApproval.tsx` — NEW
- `src/components/video/MultiVariantSelector.tsx` — NEW
- `src/components/video/VariantCard.tsx` — NEW
- `src/components/video/StepContentRenderer.tsx` — NEW

---

## Зависимости
- T1 (базовый orchestrator, startWorkflow)
