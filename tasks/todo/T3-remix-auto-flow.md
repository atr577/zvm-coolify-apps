# T3: Remix + AUTO Flow

**Status:** todo
**Priority:** P0
**Created:** 2026-01-10

## Цель
Remix + AUTO: PREPARE → IMAGE → VIDEO → AUDIO без пауз.

## Ожидаемый результат для пользователя
User создаёт Remix проект с шаблонами → создаёт Video с переменными → Generate → готовое видео. Идеально для batch (100 видео автоматом).

---

## Backend Checklist

### PREPARE Phase (app/services/workflow/remix_prepare.py)
- [x] `prepare_remix()` — заполнение templates
- [ ] Интеграция в orchestrator_v2 при `project_type === 'remix'`
- [ ] Auto-fill missing variables из suggestions

### Orchestrator (orchestrator_v2.py)
- [ ] При Remix: вызвать PREPARE перед IMAGE
- [ ] 3 шага: IMAGE → VIDEO → AUDIO
- [ ] AUTO mode: без пауз

### Remix Project Validation
- [ ] При создании project: требовать `prompt_template`
- [ ] При создании project: требовать `scenario_template` (или default)
- [ ] Все placeholders должны иметь suggestions
- [ ] Suggestions не пустые

### Tests
- [ ] tests/test_remix_auto.py

---

## Frontend Checklist

### InProgressView.tsx
- [ ] Определять project_type из video.project
- [ ] Для Remix показывать 3 шага: Image, Video, Audio
- [ ] Для Discover показывать 7 шагов

### Remix Project Form (если есть)
- [ ] Валидация: prompt_template required
- [ ] UI для ввода placeholders и suggestions

---

## E2E Критерии

1. [ ] Создать Remix проект:
   - prompt_template: "A woman in {dress_color} dress"
   - scenario_template: {motion_prompt: "walks through {location}"}
   - placeholders: ["dress_color", "location"]
   - placeholder_suggestions: {dress_color: ["red", "blue"], location: ["park", "beach"]}
2. [ ] Создать Video с content_variables: {dress_color: "red", location: "park"}
3. [ ] Generate → 3 шага без пауз → COMPLETED
4. [ ] Проверить Video.prompt_data содержит "A woman in red dress"
5. [ ] Проверить Video.scenario_data содержит "walks through park"

---

## Тестирование

```bash
# Backend
cd backend && venv/bin/pytest tests/test_remix_auto.py -v

# Frontend
cd frontend && npm run build

# E2E Manual
1. Create Remix project with templates
2. Create Video with content_variables
3. Click Generate
4. Wait for completion
5. Verify prompt_data and scenario_data are filled correctly
```

---

## Файлы

### Backend
- `app/services/workflow/orchestrator_v2.py` — Remix branch
- `app/services/workflow/remix_prepare.py` — уже есть
- `app/api/projects.py` — validation TODO
- `tests/test_remix_auto.py` — TODO

### Frontend
- `src/components/video/InProgressView.tsx` — project_type detection
- Project form components (if exist) — validation

---

## Зависимости
- T1 (базовый orchestrator)
