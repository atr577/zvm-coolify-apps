# T1: Discover + AUTO Flow

**Status:** ready_to_test
**Priority:** P0
**Created:** 2026-01-10

## Цель
Полный Discover + AUTO flow: 7 шагов без пауз → COMPLETED.

## Ожидаемый результат для пользователя
User создаёт Discover проект → выбирает AUTO → нажимает Generate → видит прогресс по шагам → получает готовое видео. Никаких дополнительных действий.

---

## Backend Checklist

### API Endpoints (app/api/workflow_v2.py)
- [x] `POST /api/workflow/{video_id}/start` — запуск workflow
- [x] Router зарегистрирован в main.py

### Orchestrator (app/services/workflow/orchestrator_v2.py)
- [x] `WorkflowOrchestratorV2` class
- [x] 7 шагов: STORY → DESCRIPTION → PROMPT → IMAGE → SCENARIO → VIDEO → AUDIO
- [x] AUTO mode: 1 вариант, auto-select, auto-approve
- [x] Создание WorkflowStep → StepAttempt → Variant
- [x] `Video.status = COMPLETED` при завершении

### Tests (tests/test_discover_auto.py)
- [x] 7 unit tests для orchestrator

---

## Frontend Checklist

### API Layer (src/services/api.ts)
- [x] `workflowApi.startWorkflow(videoId)` → `POST /api/workflow/{video_id}/start`

### Hook (src/hooks/useVideoWorkflow.ts)
- [x] `autoGenerateMutation` использует `startWorkflow`

### VideoDetail.tsx
- [x] Auto-start при `status === 'pending'` и `workflow_mode !== 'MANUAL'`
- [x] Polling ТОЛЬКО когда `status === 'in_progress'` (оптимизация)

### InProgressView.tsx — ГОТОВО
- [x] Показывать текущий шаг из `video.current_step`
- [x] Визуальный прогресс: какие шаги завершены (✓), какой текущий (⏳)
- [x] Список шагов для Discover: Story, Description, Prompt, Image, Scenario, Video, Audio

### CompletedVideoView.tsx
- [x] Показ результата при `status === 'completed'`

---

## E2E Критерии (ВСЕ должны работать)

1. [ ] Создать Discover проект через UI
2. [ ] Создать Video, выбрать AUTO mode
3. [ ] Нажать Generate → workflow стартует автоматически
4. [ ] UI показывает прогресс: Story ✓ → Description ✓ → Prompt ⏳ → ...
5. [ ] После всех шагов: status = completed, видео отображается
6. [ ] В БД: 7 WorkflowSteps, каждый со StepAttempt и Variant

---

## Тестирование

```bash
# 1. Backend tests
cd backend && venv/bin/pytest tests/test_discover_auto.py -v

# 2. Frontend build
cd frontend && npm run build

# 3. Start services
cd backend && venv/bin/uvicorn app.main:app --reload
cd frontend && npm run dev

# 4. Manual E2E
- Open http://localhost:3000
- Login
- Create Discover project
- Create Video (AUTO mode)
- Click Generate
- Watch progress
- Verify completed video
```

---

## Файлы для изменения

### Backend (DONE)
- `app/api/workflow_v2.py` ✓
- `app/services/workflow/orchestrator_v2.py` ✓
- `app/main.py` ✓
- `tests/test_discover_auto.py` ✓

### Frontend (DONE)
- `src/services/api.ts` ✓
- `src/hooks/useVideoWorkflow.ts` ✓
- `src/pages/VideoDetail.tsx` ✓ — polling optimization (only in_progress/pending)
- `src/components/video/InProgressView.tsx` ✓ — AutoProgressView component for AUTO mode
