# Task: Step Versioning & History

## Problem
При регенерации шага (например, Image) создаётся новый WorkflowStep, а предыдущая версия теряется или остаётся как отдельный "Step 2". Пользователь не может:
- Видеть предыдущие версии генерации
- Сравнивать версии
- Вернуться к предыдущей версии, если она была лучше

## Current Behavior
- Step 1: Image (первая генерация)
- Step 2: Image (регенерация) ← неправильно, должно быть Step 1.2

## Expected Behavior
- Step 1: Image
  - v1.1 (первая генерация)
  - v1.2 (регенерация с фидбеком)
  - v1.3 (ещё одна регенерация)
- Пользователь может просмотреть все версии
- Пользователь может выбрать любую версию как "активную"

## Implementation Plan

### 1. Database Model Changes
```python
# app/models/workflow_step.py
class WorkflowStep(Base):
    # ... existing fields ...
    iteration = Column(Integer, default=1)  # Version number: 1, 2, 3...
    is_active = Column(Boolean, default=True)  # Currently selected version
    parent_step_id = Column(Integer, ForeignKey('workflow_steps.id'), nullable=True)  # Link to first iteration
```

### 2. Backend Changes

**При регенерации:**
- НЕ удалять/перезаписывать старый шаг
- Создать новый шаг с `iteration = previous.iteration + 1`
- Установить `is_active = False` для старых версий
- Установить `is_active = True` для новой версии
- Связать через `parent_step_id` с первой итерацией

**Новые эндпоинты:**
- `GET /api/workflow/step/{step_id}/versions` — получить все версии шага
- `POST /api/workflow/step/{step_id}/select-version` — выбрать версию как активную

### 3. Frontend Changes

**UI для версий:**
```
Step 1: Image [v1.3] ▼
├─ v1.1 - 10:30 [feedback: "make it brighter"]
├─ v1.2 - 10:35 [feedback: "add more contrast"]
└─ v1.3 - 10:40 [current] ✓
```

**Компоненты:**
- Dropdown/accordion для просмотра версий
- Thumbnail preview для каждой версии (для Image/Video)
- Кнопка "Use this version" для выбора
- Badge с номером версии: "v1.3"

### 4. Step Numbering Logic
```
Step Type Order:
1. Story
2. Description
3. Prompt
4. Image
5. Scenario
6. Video
7. Audio
8. Adaptation
9. Publishing

Display format: "Step {type_order}.{iteration}"
Example: "Step 4.2" = Image, 2nd iteration
```

## Files to Modify
- `backend/app/models/workflow_step.py` — добавить поля
- `backend/app/api/workflow.py` — логика версионирования
- `backend/app/services/workflow/base.py` — создание итераций
- `backend/app/schemas/workflow.py` — новые схемы
- `frontend/src/pages/VideoDetail.tsx` — UI версий
- `frontend/src/components/StepVersionSelector.tsx` — новый компонент
- Alembic migration для новых полей

## Priority
Medium — улучшает UX, но не блокирует основной функционал

## Estimate
~4-6 часов работы
