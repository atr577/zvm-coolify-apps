---
id: T32
title: "API Reject Endpoint"
status: todo
priority: low
created: 2026-01-10
updated: 2026-01-10
tags: ['api']
depends_on: ['T24']
estimate: "2h"
branch: ""
---

# Task 32: API Reject Endpoint

> **Источник:** [TARGET_WORKFLOW.md](../../docs/TARGET_WORKFLOW.md) секция 14

---

## Цель

Добавить endpoint для явного reject (для аналитики):
- `POST /{video_id}/{step_type}/reject`

**Note:** Reject — это **действие для аналитики**, не меняет статус.
После reject user может:
- Regenerate с feedback
- Выбрать другой вариант

---

## Задачи

### 32.1 Reject endpoint (1h)

**Файл:** `backend/app/api/workflow_v2.py`

```python
class RejectRequest(BaseModel):
    reason: Optional[str] = None
    variant_id: Optional[int] = None  # Which variant was rejected

@router.post("/{video_id}/{step_type}/reject")
async def reject_step(
    video_id: int,
    step_type: StepType,
    body: RejectRequest = RejectRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Record rejection for analytics.

    Reject does NOT change status - it's an analytics event.
    After reject, user can regenerate or select another variant.
    """
    video, step = get_video_and_step(video_id, step_type, db, current_user)

    if step.status != StepStatus.AWAITING_APPROVAL:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject: step is {step.status.value}, expected AWAITING_APPROVAL"
        )

    # Record rejection event (for analytics)
    rejection = StepRejection(
        step_id=step.id,
        variant_id=body.variant_id or step.selected_variant_id,
        reason=body.reason,
        user_id=current_user.id,
        created_at=datetime.utcnow()
    )
    db.add(rejection)
    db.commit()

    # Count available variants for response
    all_variants = []
    for attempt in step.attempts:
        all_variants.extend(attempt.variants)

    return {
        "step_type": step_type.value,
        "status": "rejected",
        "available_actions": ["regenerate", "select_other_variant"],
        "previous_variants_count": len(all_variants),
        "rejection_id": rejection.id
    }
```

---

### 32.2 StepRejection model (0.5h)

**Файл:** `backend/app/models/step_rejection.py` (NEW)

```python
from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base

class StepRejection(Base):
    """Records rejection events for analytics."""
    __tablename__ = "step_rejections"

    id = Column(Integer, primary_key=True, index=True)
    step_id = Column(Integer, ForeignKey("workflow_steps.id", ondelete="CASCADE"), nullable=False)
    variant_id = Column(Integer, ForeignKey("variants.id", ondelete="SET NULL"), nullable=True)
    reason = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    step = relationship("WorkflowStep")
    variant = relationship("Variant")
    user = relationship("User")
```

**Файл:** `backend/app/models/__init__.py`

```python
from app.models.step_rejection import StepRejection

__all__ = [
    # ... existing ...
    "StepRejection",
]
```

---

### 32.3 Migration (0.5h)

```bash
alembic revision --autogenerate -m "add step_rejections table"
alembic upgrade head
```

**Проверить:**
- step_rejections table создана
- Foreign keys корректны

---

## Analytics Use Cases

Rejections позволяют анализировать:

1. **Какие шаги чаще reject:**
   ```sql
   SELECT step_type, COUNT(*) as rejections
   FROM step_rejections sr
   JOIN workflow_steps ws ON sr.step_id = ws.id
   GROUP BY step_type
   ORDER BY rejections DESC;
   ```

2. **Частые причины rejection:**
   ```sql
   SELECT reason, COUNT(*) as count
   FROM step_rejections
   WHERE reason IS NOT NULL
   GROUP BY reason
   ORDER BY count DESC;
   ```

3. **Сколько попыток до approve:**
   ```sql
   SELECT ws.step_type,
          AVG(attempt_count) as avg_attempts,
          MAX(attempt_count) as max_attempts
   FROM (
     SELECT step_id, COUNT(*) as attempt_count
     FROM step_rejections
     GROUP BY step_id
   ) sr
   JOIN workflow_steps ws ON sr.step_id = ws.id
   GROUP BY ws.step_type;
   ```

---

## Acceptance Criteria

- [ ] POST /{video_id}/{step_type}/reject работает
- [ ] Rejection записывается в БД
- [ ] Статус шага НЕ меняется
- [ ] Response содержит available_actions
- [ ] Можно указать reason (опционально)

---

## Тестирование

```python
@pytest.mark.asyncio
async def test_reject_records_event():
    video = create_video(status=WorkflowStatus.AWAITING_APPROVAL)
    step = create_step(video, StepType.IMAGE, status=StepStatus.AWAITING_APPROVAL)

    response = await client.post(
        f"/workflow/{video.id}/image/reject",
        json={"reason": "Too dark"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert "regenerate" in response.json()["available_actions"]

    # Check rejection recorded
    rejection = db.query(StepRejection).filter(StepRejection.step_id == step.id).first()
    assert rejection is not None
    assert rejection.reason == "Too dark"

@pytest.mark.asyncio
async def test_reject_does_not_change_status():
    video = create_video(status=WorkflowStatus.AWAITING_APPROVAL)
    step = create_step(video, StepType.IMAGE, status=StepStatus.AWAITING_APPROVAL)

    await client.post(f"/workflow/{video.id}/image/reject")

    db.refresh(step)
    db.refresh(video)

    # Status should NOT change
    assert step.status == StepStatus.AWAITING_APPROVAL
    assert video.status == WorkflowStatus.AWAITING_APPROVAL

@pytest.mark.asyncio
async def test_reject_only_from_awaiting_approval():
    video = create_video(status=WorkflowStatus.IN_PROGRESS)
    step = create_step(video, StepType.IMAGE, status=StepStatus.IN_PROGRESS)

    response = await client.post(f"/workflow/{video.id}/image/reject")

    assert response.status_code == 400
    assert "AWAITING_APPROVAL" in response.json()["detail"]
```

---

## Frontend Integration

```typescript
// After reject, show options
async function handleReject(reason?: string) {
  const result = await api.post(`/workflow/${videoId}/${stepType}/reject`, { reason });

  // Show regenerate dialog or variant selector
  if (result.previous_variants_count > 1) {
    showVariantSelector();
  } else {
    showRegenerateDialog();
  }
}
```

---

## Checklist

- [ ] 32.1 POST /{video_id}/{step_type}/reject endpoint
- [ ] 32.2 StepRejection model
- [ ] 32.3 Alembic migration
- [ ] Tests pass
- [ ] Code review

---

**Создано:** 2026-01-10
**Статус:** TODO
