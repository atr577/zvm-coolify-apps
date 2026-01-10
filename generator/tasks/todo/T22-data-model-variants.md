---
id: T22
title: "Data Model - Variant Hierarchy (Phase 2)"
status: todo
priority: high
created: 2026-01-10
updated: 2026-01-10
tags: []
depends_on: ['T21']
estimate: "8h"
branch: ""
---

# Task 22: Data Model - Variant Hierarchy (Phase 2)

> **Источник:** [IMPLEMENTATION_PLAN.md](../../docs/IMPLEMENTATION_PLAN.md) Phase 2
> **Целевая архитектура:** [TARGET_WORKFLOW.md](../../docs/TARGET_WORKFLOW.md) секция 8

---

## Цель

Создать иерархию `WorkflowStep → StepAttempt → Variant` для поддержки:
- Множественных попыток генерации
- Множественных вариантов на попытку
- Истории генераций
- Feedback-based refinement

---

## Задачи

### 22.1 Создать StepAttempt model (2h)

**Файл:** `backend/app/models/step_attempt.py` (NEW)

```python
from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, Text, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
from enum import Enum

class AttemptStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"

class StepAttempt(Base):
    __tablename__ = "step_attempts"

    id = Column(Integer, primary_key=True, index=True)
    step_id = Column(Integer, ForeignKey("workflow_steps.id", ondelete="CASCADE"), nullable=False)
    attempt_number = Column(Integer, default=1)
    status = Column(SQLEnum(AttemptStatus), default=AttemptStatus.PENDING)
    parent_variant_id = Column(Integer, ForeignKey("variants.id"), nullable=True)
    feedback = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    step = relationship("WorkflowStep", back_populates="attempts")
    variants = relationship("Variant", back_populates="attempt", foreign_keys="Variant.attempt_id")
    parent_variant = relationship("Variant", foreign_keys=[parent_variant_id])
```

---

### 22.2 Создать Variant model (2h)

**Файл:** `backend/app/models/variant.py` (NEW)

```python
from sqlalchemy import Column, Integer, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base

class Variant(Base):
    __tablename__ = "variants"

    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("step_attempts.id", ondelete="CASCADE"), nullable=False)
    variant_number = Column(Integer, default=1)
    content = Column(JSON, nullable=False)  # Step-specific content
    is_selected = Column(Boolean, default=False)

    # Relationships
    attempt = relationship("StepAttempt", back_populates="variants", foreign_keys=[attempt_id])
```

---

### 22.3 Обновить WorkflowStep model (30m)

**Файл:** `backend/app/models/workflow_step.py`

```python
# Добавить:
selected_variant_id = Column(Integer, ForeignKey("variants.id"), nullable=True)

# Добавить relationship:
attempts = relationship("StepAttempt", back_populates="step", cascade="all, delete-orphan")
selected_variant = relationship("Variant", foreign_keys=[selected_variant_id])
```

---

### 22.4 Добавить Video.is_published (30m)

**Файл:** `backend/app/models/video.py`

```python
# Добавить поле:
is_published = Column(Boolean, default=False, index=True)
```

---

### 22.5 Alembic migration (1h)

```bash
cd backend
alembic revision --autogenerate -m "add step_attempts and variants tables"
alembic upgrade head
```

**Проверить миграцию:**
- step_attempts table создана
- variants table создана
- workflow_steps.selected_variant_id добавлен
- videos.is_published добавлен
- Foreign keys корректны

---

### 22.6 Feature Flag (30m)

**Файл:** `backend/app/core/config.py`

```python
class Settings(BaseSettings):
    # ... existing ...
    USE_VARIANT_MODEL: bool = False
```

**Файл:** `backend/app/services/workflow/base.py`

```python
from app.core.config import settings

async def save_step_result(self, content: Any):
    if settings.USE_VARIANT_MODEL:
        # New code: create StepAttempt + Variant
        attempt = StepAttempt(
            step_id=self.step.id,
            attempt_number=self._get_next_attempt_number(),
            status=AttemptStatus.SUCCESS
        )
        self.db.add(attempt)
        self.db.flush()

        variant = Variant(
            attempt_id=attempt.id,
            variant_number=1,
            content=content,
            is_selected=True  # Auto-select in AUTO mode
        )
        self.db.add(variant)
        self.step.selected_variant_id = variant.id
    else:
        # Old code: write directly to Video
        setattr(self.video, self.content_field, content)

    self.db.commit()
```

---

### 22.7 Миграция существующих данных (1h)

**Файл:** `backend/scripts/migrate_to_variants.py` (NEW)

```python
"""
Migration script to create StepAttempt and Variant records
for existing workflow data.

Run: python -m scripts.migrate_to_variants
"""
from app.core.database import SessionLocal
from app.models import Video, WorkflowStep, StepAttempt, Variant, StepType

STEP_CONTENT_FIELDS = {
    StepType.STORY: "story_data",
    StepType.DESCRIPTION: "description_data",
    StepType.PROMPT: "prompt_data",
    StepType.IMAGE: "image_url",
    StepType.SCENARIO: "scenario_data",
    StepType.VIDEO: "video_url",
    StepType.AUDIO: "audio_variants",
}

def migrate_existing_data():
    db = SessionLocal()
    try:
        videos = db.query(Video).all()
        migrated = 0

        for video in videos:
            for step in video.workflow_steps:
                # Skip if already has attempts
                if step.attempts:
                    continue

                # Get content from Video model
                content_field = STEP_CONTENT_FIELDS.get(step.step_type)
                if not content_field:
                    continue

                content = getattr(video, content_field, None)
                if not content:
                    continue

                # Create attempt
                attempt = StepAttempt(
                    step_id=step.id,
                    attempt_number=1,
                    status=AttemptStatus.SUCCESS
                )
                db.add(attempt)
                db.flush()

                # Create variant
                variant = Variant(
                    attempt_id=attempt.id,
                    variant_number=1,
                    content={"value": content} if not isinstance(content, dict) else content,
                    is_selected=True
                )
                db.add(variant)
                db.flush()

                step.selected_variant_id = variant.id
                migrated += 1

        db.commit()
        print(f"Migrated {migrated} steps to variant model")

    finally:
        db.close()

if __name__ == "__main__":
    migrate_existing_data()
```

---

### 22.8 Frontend TypeScript types (30m)

**Файл:** `frontend/src/types/workflow.ts`

```typescript
export interface StepAttempt {
  id: number;
  step_id: number;
  attempt_number: number;
  status: 'pending' | 'success' | 'failed';
  feedback?: string;
  started_at: string;
  completed_at?: string;
  variants: Variant[];
}

export interface Variant {
  id: number;
  attempt_id: number;
  variant_number: number;
  content: Record<string, any>;
  is_selected: boolean;
}

export interface WorkflowStepWithVariants extends WorkflowStep {
  attempts: StepAttempt[];
  selected_variant_id?: number;
  selected_variant?: Variant;
}
```

---

### 22.9 API Response Example

**GET /api/workflow/{video_id}/story/variants**

```json
{
  "step_type": "story",
  "total_attempts": 2,
  "variants": [
    {
      "id": 1,
      "attempt_number": 1,
      "variant_number": 1,
      "content": {"story": "First version..."},
      "is_selected": false,
      "feedback": null
    },
    {
      "id": 2,
      "attempt_number": 2,
      "variant_number": 1,
      "content": {"story": "Improved version..."},
      "is_selected": true,
      "feedback": "Make it more dramatic"
    }
  ]
}
```

---

## Acceptance Criteria

- [ ] Модели StepAttempt и Variant созданы
- [ ] Alembic migration успешна
- [ ] Feature flag `USE_VARIANT_MODEL` работает
- [ ] При `USE_VARIANT_MODEL=true` создаются Variant записи
- [ ] При `USE_VARIANT_MODEL=false` работает старый код
- [ ] Существующие данные мигрированы

---

## Тестирование

```python
def test_variant_creation():
    # With feature flag ON
    settings.USE_VARIANT_MODEL = True

    step = create_workflow_step()
    await step_handler.save_step_result({"story": "test"})

    # Should create attempt + variant
    assert len(step.attempts) == 1
    assert len(step.attempts[0].variants) == 1
    assert step.selected_variant_id is not None

def test_backward_compatibility():
    # With feature flag OFF
    settings.USE_VARIANT_MODEL = False

    video = create_video()
    step = create_workflow_step(video)
    await step_handler.save_step_result({"story": "test"})

    # Should write to Video directly
    assert video.story_data == {"story": "test"}
    assert len(step.attempts) == 0
```

---

## Rollback

1. Set `USE_VARIANT_MODEL=false` in .env
2. If needed: `alembic downgrade -1`

---

## Checklist

- [ ] 22.1 StepAttempt model created
- [ ] 22.2 Variant model created
- [ ] 22.3 WorkflowStep updated
- [ ] 22.4 Video.is_published added
- [ ] 22.5 Alembic migration applied
- [ ] 22.6 Feature flag implemented
- [ ] 22.7 Migration script works
- [ ] Unit tests pass
- [ ] Integration tests pass

---

**Создано:** 2026-01-10
**Статус:** TODO
