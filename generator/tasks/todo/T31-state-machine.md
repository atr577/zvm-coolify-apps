---
id: T31
title: "Formal State Machine"
status: todo
priority: low
created: 2026-01-10
updated: 2026-01-10
tags: ['backend']
depends_on: ['T24']
estimate: "3h"
branch: ""
---

# Task 31: Formal State Machine

> **Источник:** [TARGET_WORKFLOW.md](../../docs/TARGET_WORKFLOW.md) секция 6

---

## Цель

Формализовать state machine с валидацией переходов:
- Определить допустимые переходы
- Валидировать перед изменением статуса
- Предотвратить невалидные состояния

---

## Задачи

### 31.1 State Machine Definition (1h)

**Файл:** `backend/app/models/state_machine.py` (NEW)

```python
from enum import Enum
from typing import Dict, Set
from app.models.video import WorkflowStatus, StepStatus

# Video status transitions
VIDEO_TRANSITIONS: Dict[WorkflowStatus, Set[WorkflowStatus]] = {
    WorkflowStatus.PENDING: {
        WorkflowStatus.IN_PROGRESS,
    },
    WorkflowStatus.IN_PROGRESS: {
        WorkflowStatus.AWAITING_APPROVAL,
        WorkflowStatus.COMPLETED,
        WorkflowStatus.FAILED,
    },
    WorkflowStatus.AWAITING_APPROVAL: {
        WorkflowStatus.IN_PROGRESS,  # approve → continue OR regenerate
        WorkflowStatus.COMPLETED,    # approve last step (AUDIO)
    },
    WorkflowStatus.COMPLETED: set(),  # Terminal (rollback is delete + reset, not transition)
    WorkflowStatus.FAILED: {
        WorkflowStatus.IN_PROGRESS,  # retry
    },
}

# Step status transitions
STEP_TRANSITIONS: Dict[StepStatus, Set[StepStatus]] = {
    StepStatus.PENDING: {
        StepStatus.IN_PROGRESS,
    },
    StepStatus.IN_PROGRESS: {
        StepStatus.AWAITING_APPROVAL,
        StepStatus.APPROVED,  # AUTO mode
        StepStatus.FAILED,
    },
    StepStatus.AWAITING_APPROVAL: {
        StepStatus.APPROVED,
        StepStatus.IN_PROGRESS,  # regenerate
    },
    StepStatus.APPROVED: set(),  # Terminal
    StepStatus.FAILED: {
        StepStatus.IN_PROGRESS,  # retry
    },
}


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    def __init__(self, entity: str, current: Enum, target: Enum):
        self.entity = entity
        self.current = current
        self.target = target
        super().__init__(
            f"Invalid {entity} transition: {current.value} → {target.value}"
        )


def validate_video_transition(current: WorkflowStatus, target: WorkflowStatus) -> bool:
    """Check if video status transition is valid."""
    valid_targets = VIDEO_TRANSITIONS.get(current, set())
    return target in valid_targets


def validate_step_transition(current: StepStatus, target: StepStatus) -> bool:
    """Check if step status transition is valid."""
    valid_targets = STEP_TRANSITIONS.get(current, set())
    return target in valid_targets


def assert_video_transition(current: WorkflowStatus, target: WorkflowStatus) -> None:
    """Assert video transition is valid, raise if not."""
    if not validate_video_transition(current, target):
        raise InvalidTransitionError("video", current, target)


def assert_step_transition(current: StepStatus, target: StepStatus) -> None:
    """Assert step transition is valid, raise if not."""
    if not validate_step_transition(current, target):
        raise InvalidTransitionError("step", current, target)
```

---

### 31.2 Integration with Models (1h)

**Файл:** `backend/app/models/video.py`

```python
from app.models.state_machine import assert_video_transition, InvalidTransitionError

class Video(Base):
    # ... existing fields ...

    def set_status(self, new_status: WorkflowStatus) -> None:
        """Set video status with transition validation."""
        if self.status == new_status:
            return  # No change

        assert_video_transition(self.status, new_status)
        self.status = new_status
```

**Файл:** `backend/app/models/workflow_step.py`

```python
from app.models.state_machine import assert_step_transition, InvalidTransitionError

class WorkflowStep(Base):
    # ... existing fields ...

    def set_status(self, new_status: StepStatus) -> None:
        """Set step status with transition validation."""
        if self.status == new_status:
            return  # No change

        assert_step_transition(self.status, new_status)
        self.status = new_status
```

---

### 31.3 Update All Status Changes (1h)

**Найти и заменить прямые присвоения:**

```bash
# Find all direct status assignments
grep -rn "\.status = " backend/app/
```

**Файл:** `backend/app/services/workflow/orchestrator.py`

```python
# БЫЛО:
self.video.status = WorkflowStatus.IN_PROGRESS

# СТАНЕТ:
self.video.set_status(WorkflowStatus.IN_PROGRESS)


# БЫЛО:
step.status = StepStatus.AWAITING_APPROVAL

# СТАНЕТ:
step.set_status(StepStatus.AWAITING_APPROVAL)
```

**Файл:** `backend/app/api/workflow_v2.py`

```python
# БЫЛО:
step.status = StepStatus.APPROVED

# СТАНЕТ:
step.set_status(StepStatus.APPROVED)
```

**Handle InvalidTransitionError:**

```python
from app.models.state_machine import InvalidTransitionError

@router.post("/{video_id}/{step_type}/approve")
async def approve_step(...):
    try:
        step.set_status(StepStatus.APPROVED)
    except InvalidTransitionError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_transition",
                "message": str(e),
                "current_status": e.current.value,
                "target_status": e.target.value
            }
        )
```

---

## State Diagram

```
VIDEO STATUS:

  PENDING ──────────────────────────────────────────────────────┐
     │                                                           │
     ▼ (auto-generate)                                           │
  IN_PROGRESS ─────────────────────────────────────────────────┬┤
     │         │                                                ││
     │         │ (step complete,                                ││
     │         │  MANUAL mode)                                  ││
     │         ▼                                                ││
     │    AWAITING_APPROVAL ───────────────────────────────────┤│
     │         │         │                                      ││
     │         │ (approve│                                      ││
     │         │  + cont)│ (approve last step)                  ││
     │         │         ▼                                      ││
     │         │    COMPLETED ◄─────────────────────────────────┘│
     │         │                                                 │
     │         └──(regenerate)───────────────────────────────────┤
     │                                                           │
     ▼ (error after retries)                                     │
  FAILED ─────────────────────────────────────────────────────(retry)
```

```
STEP STATUS:

  PENDING ─────────────────────────────────────────────────────┐
     │                                                          │
     ▼ (generation starts)                                      │
  IN_PROGRESS ─────────────────────────────────────────────────┤
     │         │         │                                      │
     │ (AUTO)  │ (MANUAL)│ (error)                             │
     ▼         ▼         ▼                                      │
  APPROVED  AWAITING   FAILED ────────────────────────────(retry)
     │      APPROVAL      │
     │         │          │
     │         ▼ (approve)│
     │      APPROVED      │
     │         │          │
     └─────────┴──────────┘
```

---

## Acceptance Criteria

- [ ] VIDEO_TRANSITIONS и STEP_TRANSITIONS определены
- [ ] validate_*_transition() функции работают
- [ ] Video.set_status() и Step.set_status() используют валидацию
- [ ] Все прямые присвоения `.status = ` заменены на `.set_status()`
- [ ] InvalidTransitionError конвертируется в HTTP 400
- [ ] Невалидные переходы предотвращаются

---

## Тестирование

```python
def test_valid_video_transitions():
    assert validate_video_transition(WorkflowStatus.PENDING, WorkflowStatus.IN_PROGRESS) == True
    assert validate_video_transition(WorkflowStatus.IN_PROGRESS, WorkflowStatus.AWAITING_APPROVAL) == True
    assert validate_video_transition(WorkflowStatus.AWAITING_APPROVAL, WorkflowStatus.COMPLETED) == True

def test_invalid_video_transitions():
    assert validate_video_transition(WorkflowStatus.PENDING, WorkflowStatus.COMPLETED) == False
    assert validate_video_transition(WorkflowStatus.COMPLETED, WorkflowStatus.IN_PROGRESS) == False
    assert validate_video_transition(WorkflowStatus.FAILED, WorkflowStatus.COMPLETED) == False

def test_video_set_status_valid():
    video = Video(status=WorkflowStatus.PENDING)
    video.set_status(WorkflowStatus.IN_PROGRESS)
    assert video.status == WorkflowStatus.IN_PROGRESS

def test_video_set_status_invalid():
    video = Video(status=WorkflowStatus.PENDING)
    with pytest.raises(InvalidTransitionError) as exc_info:
        video.set_status(WorkflowStatus.COMPLETED)

    assert exc_info.value.current == WorkflowStatus.PENDING
    assert exc_info.value.target == WorkflowStatus.COMPLETED

def test_api_returns_400_on_invalid_transition():
    video = create_video(status=WorkflowStatus.COMPLETED)
    step = create_step(video, StepType.STORY, status=StepStatus.APPROVED)

    response = await client.post(f"/workflow/{video.id}/story/approve")

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "invalid_transition"
```

---

## Checklist

- [ ] 31.1 state_machine.py with transitions
- [ ] 31.2 Video.set_status() and Step.set_status()
- [ ] 31.3 Replace all direct .status = assignments
- [ ] HTTP 400 on InvalidTransitionError
- [ ] Tests pass
- [ ] Code review

---

**Создано:** 2026-01-10
**Статус:** TODO
