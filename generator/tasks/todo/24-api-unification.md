# Task 24: API Unification (Phase 4)

**Приоритет:** P2 (MEDIUM)
**Оценка:** 14h
**Зависимости:** Task 22, 23 (Data Model + Breakpoints)
**Блокирует:** Phase 5

> **Источник:** [IMPLEMENTATION_PLAN.md](../../docs/IMPLEMENTATION_PLAN.md) Phase 4
> **API спецификация:** [TARGET_WORKFLOW.md](../../docs/TARGET_WORKFLOW.md) секция 14

---

## Цель

Создать унифицированный API pattern:
```
POST /workflow/{video_id}/{step_type}/action
```

Вместо текущего:
```
POST /workflow/generate-story
POST /workflow/generate-description
POST /workflow/approve-step
...
```

---

## Задачи

### 24.1 Создать новый router (4h)

**Файл:** `backend/app/api/workflow_v2.py` (NEW)

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user
from app.models.video import Video, StepType
from app.models.user import User

router = APIRouter(prefix="/workflow", tags=["workflow-v2"])

def get_video_and_step(
    video_id: int,
    step_type: StepType,
    db: Session,
    current_user: User
) -> tuple[Video, WorkflowStep]:
    """Common helper to get video and step with ownership check."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    verify_video_ownership(db, video, current_user)

    step = db.query(WorkflowStep).filter(
        WorkflowStep.video_id == video_id,
        WorkflowStep.step_type == step_type
    ).first()

    return video, step
```

---

### 24.2 Endpoint: select-variant (1h)

```python
class SelectVariantRequest(BaseModel):
    variant_id: int

@router.post("/{video_id}/{step_type}/select-variant")
async def select_variant(
    video_id: int,
    step_type: StepType,
    body: SelectVariantRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Select a variant for a step (does NOT approve, just marks selection)."""
    video, step = get_video_and_step(video_id, step_type, db, current_user)

    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    # Verify variant belongs to this step
    variant = db.query(Variant).filter(Variant.id == body.variant_id).first()
    if not variant or variant.attempt.step_id != step.id:
        raise HTTPException(status_code=400, detail="Invalid variant")

    # Deselect all, select new
    db.query(Variant).filter(
        Variant.attempt_id.in_([a.id for a in step.attempts])
    ).update({"is_selected": False})

    variant.is_selected = True
    step.selected_variant_id = variant.id
    db.commit()

    return {"status": "selected", "variant_id": variant.id}
```

---

### 24.3 Endpoint: approve (1h)

```python
@router.post("/{video_id}/{step_type}/approve")
async def approve_step(
    video_id: int,
    step_type: StepType,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve current step and copy selected variant content to Video."""
    video, step = get_video_and_step(video_id, step_type, db, current_user)

    if step.status != StepStatus.AWAITING_APPROVAL:
        raise HTTPException(status_code=400, detail="Step not awaiting approval")

    # Copy selected variant content to Video
    if step.selected_variant_id:
        variant = db.query(Variant).get(step.selected_variant_id)
        content_field = STEP_CONTENT_FIELDS[step_type]
        setattr(video, content_field, variant.content)

    step.status = StepStatus.APPROVED
    db.commit()

    return {
        "status": "approved",
        "step_type": step_type.value,
        "next_action": "call /auto-generate-to-video to continue"
    }
```

---

### 24.4 Endpoint: regenerate (1h)

```python
class RegenerateRequest(BaseModel):
    feedback: Optional[str] = None
    variant_count: int = 1

@router.post("/{video_id}/{step_type}/regenerate")
async def regenerate_step(
    video_id: int,
    step_type: StepType,
    body: RegenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Regenerate step with optional feedback."""
    video, step = get_video_and_step(video_id, step_type, db, current_user)

    # Create new attempt
    attempt = StepAttempt(
        step_id=step.id,
        attempt_number=len(step.attempts) + 1,
        feedback=body.feedback,
        parent_variant_id=step.selected_variant_id
    )
    db.add(attempt)

    # Generate new variants
    step.status = StepStatus.IN_PROGRESS
    db.commit()

    # Trigger async generation (returns immediately)
    background_tasks.add_task(
        generate_step_variants,
        step_id=step.id,
        attempt_id=attempt.id,
        variant_count=body.variant_count,
        feedback=body.feedback
    )

    return {
        "status": "regenerating",
        "attempt_id": attempt.id
    }
```

---

### 24.5 Endpoint: variants GET (1h)

```python
@router.get("/{video_id}/{step_type}/variants")
async def get_variants(
    video_id: int,
    step_type: StepType,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all variants for a step across all attempts."""
    video, step = get_video_and_step(video_id, step_type, db, current_user)

    variants = []
    for attempt in step.attempts:
        for variant in attempt.variants:
            variants.append({
                "id": variant.id,
                "attempt_number": attempt.attempt_number,
                "variant_number": variant.variant_number,
                "content": variant.content,
                "is_selected": variant.is_selected,
                "feedback": attempt.feedback
            })

    return {
        "step_type": step_type.value,
        "total_attempts": len(step.attempts),
        "variants": variants
    }
```

---

### 24.6 Endpoint: rollback-to (2h)

```python
@router.post("/{video_id}/rollback-to/{target_step}")
async def rollback_to_step(
    video_id: int,
    target_step: StepType,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Rollback workflow to a previous step."""
    video = db.query(Video).filter(Video.id == video_id).first()
    verify_video_ownership(db, video, current_user)

    # Check if published
    if video.is_published:
        raise HTTPException(
            status_code=400,
            detail="Cannot rollback published video"
        )

    # Get step order
    step_order = [s.value for s in StepType]
    target_index = step_order.index(target_step.value)

    # Delete steps after target
    for step in video.workflow_steps:
        step_index = step_order.index(step.step_type.value)
        if step_index > target_index:
            db.delete(step)

    # Clear Video fields after target
    fields_to_clear = get_fields_after_step(target_step)
    for field in fields_to_clear:
        setattr(video, field, None)

    # Reset target step to AWAITING_APPROVAL
    target_step_obj = db.query(WorkflowStep).filter(
        WorkflowStep.video_id == video_id,
        WorkflowStep.step_type == target_step
    ).first()

    if target_step_obj:
        target_step_obj.status = StepStatus.AWAITING_APPROVAL

    video.current_step = target_step
    video.status = WorkflowStatus.AWAITING_APPROVAL
    db.commit()

    return {
        "status": "rolled_back",
        "current_step": target_step.value
    }
```

---

### 24.7 Обновить frontend (4h)

**Файл:** `frontend/src/services/api.ts`

```typescript
export const workflowApi = {
  // New unified API
  selectVariant: (videoId: number, stepType: string, variantId: number) =>
    api.post(`/api/workflow/${videoId}/${stepType}/select-variant`, { variant_id: variantId }),

  approve: (videoId: number, stepType: string) =>
    api.post(`/api/workflow/${videoId}/${stepType}/approve`),

  regenerate: (videoId: number, stepType: string, feedback?: string) =>
    api.post(`/api/workflow/${videoId}/${stepType}/regenerate`, { feedback }),

  getVariants: (videoId: number, stepType: string) =>
    api.get(`/api/workflow/${videoId}/${stepType}/variants`),

  rollbackTo: (videoId: number, targetStep: string) =>
    api.post(`/api/workflow/${videoId}/rollback-to/${targetStep}`),

  // Keep old API for backward compatibility (deprecated)
  /** @deprecated Use approve() instead */
  approveStep: (stepId: number, approved: boolean) =>
    api.post('/api/workflow/approve-step', { step_id: stepId, approved }),
}
```

**Обновить компоненты:**
- `VideoDetail.tsx` - использовать новые endpoints
- `InProgressView.tsx` - использовать новые endpoints

---

### 24.8 Deprecate старые endpoints (30m)

**Файл:** `backend/app/api/workflow.py`

```python
from warnings import warn

@router.post("/approve-step")
async def approve_step_deprecated(...):
    """
    DEPRECATED: Use POST /workflow/{video_id}/{step_type}/approve instead.
    """
    warn("approve-step endpoint is deprecated", DeprecationWarning)
    # ... existing code for backward compatibility
```

---

## HTTP Error Codes

Каждый endpoint должен возвращать стандартные коды:

| Endpoint | Success | Errors |
|----------|---------|--------|
| `POST /{video_id}/{step}/select-variant` | 200 | 400 (invalid variant), 404 (video/step not found), 403 (not owner) |
| `POST /{video_id}/{step}/approve` | 200 | 400 (not awaiting approval), 404, 403 |
| `POST /{video_id}/{step}/regenerate` | 202 | 400 (step not started), 404, 403, 429 (rate limit) |
| `GET /{video_id}/{step}/variants` | 200 | 404, 403 |
| `POST /{video_id}/rollback-to/{step}` | 200 | 400 (published), 404, 403 |

**Пример curl запросов:**

```bash
# Select variant
curl -X POST http://localhost:8000/api/workflow/1/image/select-variant \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"variant_id": 5}'

# Approve step
curl -X POST http://localhost:8000/api/workflow/1/image/approve \
  -H "Authorization: Bearer $TOKEN"

# Get variants
curl http://localhost:8000/api/workflow/1/story/variants \
  -H "Authorization: Bearer $TOKEN"

# Rollback
curl -X POST http://localhost:8000/api/workflow/1/rollback-to/prompt \
  -H "Authorization: Bearer $TOKEN"
```

---

## Feature Flag

```python
# config.py
USE_WORKFLOW_V2_API: bool = False
```

**Файл:** `backend/app/main.py`
```python
if settings.USE_WORKFLOW_V2_API:
    app.include_router(workflow_v2.router, prefix="/api")
```

---

## Acceptance Criteria

- [ ] Все 6 новых endpoints работают
- [ ] Frontend использует новые endpoints
- [ ] Старые endpoints помечены deprecated
- [ ] Rollback запрещён для опубликованных видео
- [ ] select-variant не копирует данные (только approve копирует)

---

## Тестирование

```python
@pytest.mark.asyncio
async def test_select_variant():
    response = await client.post(
        f"/workflow/{video_id}/image/select-variant",
        json={"variant_id": variant_id}
    )
    assert response.status_code == 200
    assert step.selected_variant_id == variant_id
    # Content NOT copied to video yet
    assert video.image_url is None

@pytest.mark.asyncio
async def test_approve_copies_content():
    # First select
    await client.post(f"/workflow/{video_id}/image/select-variant", ...)

    # Then approve - should copy content
    response = await client.post(f"/workflow/{video_id}/image/approve")
    assert response.status_code == 200
    assert video.image_url == variant.content["url"]

@pytest.mark.asyncio
async def test_rollback_blocked_after_publish():
    video.is_published = True
    response = await client.post(f"/workflow/{video_id}/rollback-to/image")
    assert response.status_code == 400
    assert "Cannot rollback published video" in response.json()["detail"]
```

---

## Rollback

1. Set `USE_WORKFLOW_V2_API=false`
2. Frontend: revert to old endpoints

---

## Checklist

- [ ] 24.1 workflow_v2.py router created
- [ ] 24.2 select-variant endpoint
- [ ] 24.3 approve endpoint
- [ ] 24.4 regenerate endpoint
- [ ] 24.5 variants GET endpoint
- [ ] 24.6 rollback-to endpoint
- [ ] 24.7 Frontend updated
- [ ] 24.8 Old endpoints deprecated
- [ ] Feature flag works
- [ ] All tests pass

---

**Создано:** 2026-01-10
**Статус:** TODO
