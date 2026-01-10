---
id: T28
title: "Concurrency Protection"
status: todo
priority: medium
created: 2026-01-10
updated: 2026-01-10
tags: []
depends_on: ['T24']
estimate: "4h"
branch: ""
---

# Task 28: Concurrency Protection

> **Источник:** [TARGET_WORKFLOW.md](../../docs/TARGET_WORKFLOW.md) секция 10

---

## Цель

Защита от race conditions при параллельных запросах:
- Два таба браузера
- Двойной клик
- Параллельные API вызовы

**Принцип:** Первый запрос выигрывает, остальные получают 409 Conflict.

---

## Задачи

### 28.1 Video-level locking (1.5h)

**Файл:** `backend/app/api/workflow.py`

```python
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

@router.post("/auto-generate-to-video")
async def auto_generate_to_video(
    body: AutoGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start or continue video generation with locking."""

    # Lock the video row for update
    video = db.execute(
        select(Video)
        .where(Video.id == body.video_id)
        .with_for_update(nowait=True)  # Fail immediately if locked
    ).scalar_one_or_none()

    if not video:
        raise HTTPException(404, "Video not found")

    verify_video_ownership(db, video, current_user)

    # Check valid starting states
    if video.status == WorkflowStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "conflict",
                "message": "Generation already in progress",
                "action": "Please wait or refresh the page"
            }
        )

    if video.status == WorkflowStatus.COMPLETED:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "conflict",
                "message": "Video already completed",
                "action": "Use rollback to make changes"
            }
        )

    # Valid states: PENDING, AWAITING_APPROVAL, FAILED
    video.status = WorkflowStatus.IN_PROGRESS
    db.commit()

    # Start background job
    background_tasks.add_task(run_workflow, video.id)

    return {"status": "started", "video_id": video.id}
```

**Handle lock acquisition failure:**

```python
from sqlalchemy.exc import OperationalError

@router.post("/auto-generate-to-video")
async def auto_generate_to_video(...):
    try:
        video = db.execute(
            select(Video).where(Video.id == body.video_id).with_for_update(nowait=True)
        ).scalar_one_or_none()
    except OperationalError:
        # Row is locked by another transaction
        raise HTTPException(
            status_code=409,
            detail={
                "error": "conflict",
                "message": "Another operation is in progress",
                "action": "Please wait and try again"
            }
        )
```

---

### 28.2 Step-level locking (1.5h)

**Файл:** `backend/app/api/workflow_v2.py`

```python
@router.post("/{video_id}/{step_type}/approve")
async def approve_step(
    video_id: int,
    step_type: StepType,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve step with locking."""

    try:
        step = db.execute(
            select(WorkflowStep)
            .where(
                WorkflowStep.video_id == video_id,
                WorkflowStep.step_type == step_type
            )
            .with_for_update(nowait=True)
        ).scalar_one_or_none()
    except OperationalError:
        raise HTTPException(409, "Another operation is in progress")

    if not step:
        raise HTTPException(404, "Step not found")

    # Verify ownership via video
    video = db.query(Video).filter(Video.id == video_id).first()
    verify_video_ownership(db, video, current_user)

    # Check valid state
    if step.status != StepStatus.AWAITING_APPROVAL:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "invalid_state",
                "message": f"Cannot approve: step is {step.status.value}",
                "current_status": step.status.value
            }
        )

    step.status = StepStatus.APPROVED
    # ... rest of approve logic
```

**Apply to all state-changing endpoints:**
- `POST /{video_id}/{step_type}/select-variant`
- `POST /{video_id}/{step_type}/regenerate`
- `POST /{video_id}/rollback-to/{target_step}`

---

### 28.3 Helper decorator (1h)

**Файл:** `backend/app/core/locking.py` (NEW)

```python
from functools import wraps
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from fastapi import HTTPException

def with_video_lock(func):
    """Decorator to acquire video lock before operation."""
    @wraps(func)
    async def wrapper(*args, video_id: int, db: Session, **kwargs):
        try:
            video = db.execute(
                select(Video)
                .where(Video.id == video_id)
                .with_for_update(nowait=True)
            ).scalar_one_or_none()
        except OperationalError:
            raise HTTPException(
                status_code=409,
                detail="Another operation is in progress. Please wait."
            )

        if not video:
            raise HTTPException(status_code=404, detail="Video not found")

        return await func(*args, video_id=video_id, db=db, video=video, **kwargs)

    return wrapper


def with_step_lock(func):
    """Decorator to acquire step lock before operation."""
    @wraps(func)
    async def wrapper(*args, video_id: int, step_type: StepType, db: Session, **kwargs):
        try:
            step = db.execute(
                select(WorkflowStep)
                .where(
                    WorkflowStep.video_id == video_id,
                    WorkflowStep.step_type == step_type
                )
                .with_for_update(nowait=True)
            ).scalar_one_or_none()
        except OperationalError:
            raise HTTPException(
                status_code=409,
                detail="Another operation is in progress. Please wait."
            )

        if not step:
            raise HTTPException(status_code=404, detail="Step not found")

        return await func(*args, video_id=video_id, step_type=step_type, db=db, step=step, **kwargs)

    return wrapper
```

**Usage:**

```python
@router.post("/{video_id}/{step_type}/approve")
@with_step_lock
async def approve_step(
    video_id: int,
    step_type: StepType,
    step: WorkflowStep,  # Injected by decorator
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # step is already locked
    ...
```

---

## Valid State Transitions

### Video

| From | Action | To | Notes |
|------|--------|-----|-------|
| PENDING | auto-generate | IN_PROGRESS | Start workflow |
| AWAITING_APPROVAL | auto-generate | IN_PROGRESS | Continue after approve |
| IN_PROGRESS | — | 409 Conflict | Wait for completion |
| COMPLETED | — | 409 Conflict | Use rollback |
| FAILED | retry | IN_PROGRESS | Retry workflow |

### WorkflowStep

| From | Action | To | Notes |
|------|--------|-----|-------|
| AWAITING_APPROVAL | approve | APPROVED | Finalize step |
| AWAITING_APPROVAL | regenerate | IN_PROGRESS | New attempt |
| AWAITING_APPROVAL | select-variant | AWAITING_APPROVAL | Just update selection |
| IN_PROGRESS | — | 409 Conflict | Wait for generation |
| FAILED | retry | IN_PROGRESS | Retry step |

---

## Acceptance Criteria

- [ ] Параллельный auto-generate возвращает 409
- [ ] Параллельный approve возвращает 409
- [ ] Lock освобождается после commit/rollback
- [ ] 409 response содержит понятное сообщение для user
- [ ] Декораторы работают корректно

---

## Тестирование

```python
import asyncio

@pytest.mark.asyncio
async def test_concurrent_auto_generate():
    video = create_video(status=WorkflowStatus.PENDING)

    # Start two concurrent requests
    async def call_generate():
        return await client.post("/workflow/auto-generate-to-video", json={"video_id": video.id})

    results = await asyncio.gather(
        call_generate(),
        call_generate(),
        return_exceptions=True
    )

    # One should succeed, one should get 409
    statuses = [r.status_code for r in results]
    assert 202 in statuses  # One accepted
    assert 409 in statuses  # One conflict

@pytest.mark.asyncio
async def test_concurrent_approve():
    video = create_video(status=WorkflowStatus.AWAITING_APPROVAL)
    step = create_step(video, StepType.STORY, status=StepStatus.AWAITING_APPROVAL)

    async def call_approve():
        return await client.post(f"/workflow/{video.id}/story/approve")

    results = await asyncio.gather(
        call_approve(),
        call_approve(),
        return_exceptions=True
    )

    statuses = [r.status_code for r in results]
    assert 200 in statuses
    assert 409 in statuses

@pytest.mark.asyncio
async def test_409_response_format():
    video = create_video(status=WorkflowStatus.IN_PROGRESS)

    response = await client.post("/workflow/auto-generate-to-video", json={"video_id": video.id})

    assert response.status_code == 409
    data = response.json()
    assert data["detail"]["error"] == "conflict"
    assert "message" in data["detail"]
    assert "action" in data["detail"]
```

---

## Frontend Handling

```typescript
async function handleGenerate(videoId: number) {
  try {
    await api.post('/workflow/auto-generate-to-video', { video_id: videoId });
    startPolling(videoId);
  } catch (error) {
    if (error.response?.status === 409) {
      // Show user-friendly message
      toast.warning(error.response.data.detail.message);
      // Refresh to get current state
      await refreshVideo(videoId);
    } else {
      throw error;
    }
  }
}
```

---

## Checklist

- [ ] 28.1 Video-level locking implemented
- [ ] 28.2 Step-level locking implemented
- [ ] 28.3 Helper decorators created
- [ ] All state-changing endpoints use locking
- [ ] 409 responses have proper format
- [ ] Concurrent tests pass
- [ ] Code review

---

**Создано:** 2026-01-10
**Статус:** TODO
