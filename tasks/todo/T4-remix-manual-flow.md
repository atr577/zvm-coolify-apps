# T4: Remix + MANUAL Flow

**Status:** todo
**Priority:** P0
**Created:** 2026-01-10

## Цель
Remix + MANUAL: PREPARE → IMAGE (pause) → VIDEO (pause) → AUDIO (pause) → COMPLETED.

## Ожидаемый результат для пользователя
User контролирует качество при тиражировании. На IMAGE — выбор из 3 вариантов. На AUDIO — выбор из 3 вариантов. После approve — auto-continue.

---

## Backend Checklist

### Orchestrator
- [ ] Remix + MANUAL: pause после IMAGE, VIDEO, AUDIO
- [ ] IMAGE: 3 варианта
- [ ] VIDEO: 1 вариант
- [ ] AUDIO: 3 варианта

### All endpoints from T2
- [ ] variants, select, approve, reject, regenerate — должны работать для Remix

### Tests
- [ ] tests/test_remix_manual.py

---

## Frontend Checklist

### Всё из T2 должно работать для Remix:
- [ ] ApprovalView для IMAGE с 3 вариантами
- [ ] ApprovalView для VIDEO с 1 вариантом
- [ ] ApprovalView для AUDIO с 3 вариантами
- [ ] Auto-continue после approve

### InProgressView.tsx
- [ ] Для Remix MANUAL: показывать 3 шага с progress

---

## E2E Критерии

```
1. User: создать Remix проект с templates
2. User: создать Video, выбрать MANUAL mode
3. User: нажать Generate
4. System: PREPARE заполняет templates
5. System: генерирует 3 IMAGE варианта → AWAITING_APPROVAL
6. User: видит 3 картинки, выбирает
7. User: Approve
8. System: генерирует VIDEO → AWAITING_APPROVAL
9. User: видит видео, Approve
10. System: генерирует 3 AUDIO варианта → AWAITING_APPROVAL
11. User: выбирает audio, Approve
12. System: COMPLETED
```

Все 12 шагов должны работать без багов!

---

## Тестирование

```bash
# Backend
cd backend && venv/bin/pytest tests/test_remix_manual.py -v

# Frontend
cd frontend && npm run build

# E2E Manual
Full scenario above — step by step verification
```

---

## Файлы

### Backend
- `app/services/workflow/orchestrator_v2.py` — Remix MANUAL branch
- `tests/test_remix_manual.py` — TODO

### Frontend
- Все компоненты из T2 должны работать
- `src/components/video/InProgressView.tsx` — Remix steps

---

## Зависимости
- T1 (orchestrator)
- T2 (approval flow, все компоненты)
- T3 (PREPARE phase)
