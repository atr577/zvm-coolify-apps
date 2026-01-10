# Task 29: Error Handling & Retry Policy

**Приоритет:** P2 (MEDIUM)
**Оценка:** 6h
**Зависимости:** Task 24 (API Unification)
**Блокирует:** Production stability

> **Источник:** [TARGET_WORKFLOW.md](../../docs/TARGET_WORKFLOW.md) секция 11

---

## Цель

Реализовать robustную обработку ошибок:
- Retry policy для каждого сервиса
- Timeout detection
- Step-level error handling
- User-facing retry/regenerate options

---

## Задачи

### 29.1 Retry Policy Configuration (1h)

**Файл:** `backend/app/core/config.py`

```python
class Settings(BaseSettings):
    # ... existing ...

    # Retry policy per service
    LLM_MAX_RETRIES: int = 3
    LLM_RETRY_BACKOFF: float = 1.0  # seconds, exponential: 1s, 2s, 4s

    IMAGE_GEN_MAX_RETRIES: int = 2
    IMAGE_GEN_RETRY_BACKOFF: float = 2.0  # 2s, 4s

    VIDEO_GEN_MAX_RETRIES: int = 2
    VIDEO_GEN_RETRY_BACKOFF: float = 5.0  # 5s, 10s

    AUDIO_GEN_MAX_RETRIES: int = 2
    AUDIO_GEN_RETRY_BACKOFF: float = 2.0  # 2s, 4s

    # Step timeouts (seconds)
    STEP_TIMEOUT_STORY: int = 120        # 2 min
    STEP_TIMEOUT_DESCRIPTION: int = 120
    STEP_TIMEOUT_PROMPT: int = 120
    STEP_TIMEOUT_IMAGE: int = 300        # 5 min
    STEP_TIMEOUT_SCENARIO: int = 120
    STEP_TIMEOUT_VIDEO: int = 1200       # 20 min (VideoGen slow)
    STEP_TIMEOUT_AUDIO: int = 300        # 5 min
```

**Файл:** `backend/app/core/retry.py` (NEW)

```python
from dataclasses import dataclass
from app.core.config import settings
from app.models.video import StepType

@dataclass
class RetryConfig:
    max_retries: int
    backoff_seconds: float

RETRY_CONFIGS = {
    "llm": RetryConfig(settings.LLM_MAX_RETRIES, settings.LLM_RETRY_BACKOFF),
    "image": RetryConfig(settings.IMAGE_GEN_MAX_RETRIES, settings.IMAGE_GEN_RETRY_BACKOFF),
    "video": RetryConfig(settings.VIDEO_GEN_MAX_RETRIES, settings.VIDEO_GEN_RETRY_BACKOFF),
    "audio": RetryConfig(settings.AUDIO_GEN_MAX_RETRIES, settings.AUDIO_GEN_RETRY_BACKOFF),
}

STEP_TIMEOUTS = {
    StepType.STORY: settings.STEP_TIMEOUT_STORY,
    StepType.DESCRIPTION: settings.STEP_TIMEOUT_DESCRIPTION,
    StepType.PROMPT: settings.STEP_TIMEOUT_PROMPT,
    StepType.IMAGE: settings.STEP_TIMEOUT_IMAGE,
    StepType.SCENARIO: settings.STEP_TIMEOUT_SCENARIO,
    StepType.VIDEO: settings.STEP_TIMEOUT_VIDEO,
    StepType.AUDIO: settings.STEP_TIMEOUT_AUDIO,
}

def get_service_type(step_type: StepType) -> str:
    """Map step type to service type."""
    if step_type in [StepType.STORY, StepType.DESCRIPTION, StepType.PROMPT, StepType.SCENARIO]:
        return "llm"
    elif step_type == StepType.IMAGE:
        return "image"
    elif step_type == StepType.VIDEO:
        return "video"
    elif step_type == StepType.AUDIO:
        return "audio"
    return "llm"
```

---

### 29.2 Retry Decorator (1.5h)

**Файл:** `backend/app/core/retry.py`

```python
import asyncio
import logging
from functools import wraps
from typing import Callable, TypeVar, Any

logger = logging.getLogger(__name__)

T = TypeVar('T')

def with_retry(service_type: str):
    """Decorator for automatic retry with exponential backoff."""
    config = RETRY_CONFIGS.get(service_type, RETRY_CONFIGS["llm"])

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < config.max_retries:
                        wait_time = config.backoff_seconds * (2 ** attempt)
                        logger.warning(
                            f"{func.__name__} attempt {attempt + 1} failed: {e}. "
                            f"Retrying in {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {config.max_retries + 1} attempts: {e}"
                        )

            raise last_exception

        return wrapper
    return decorator
```

**Usage in services:**

```python
# backend/app/services/openai_service.py
from app.core.retry import with_retry

class OpenAIService:
    @with_retry("llm")
    async def generate_story(self, inputs: dict) -> dict:
        # ... implementation
        pass

    @with_retry("llm")
    async def generate_description(self, story_data: dict) -> dict:
        # ... implementation
        pass


# backend/app/services/kling_service.py
from app.core.retry import with_retry

class KlingService:
    @with_retry("image")
    async def generate_image(self, prompt: str) -> str:
        # ... implementation
        pass

    @with_retry("video")
    async def generate_video(self, image_url: str, scenario: dict) -> str:
        # ... implementation
        pass
```

---

### 29.3 Timeout Detection (1.5h)

**Файл:** `backend/app/services/workflow/timeout_monitor.py` (NEW)

```python
import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.retry import STEP_TIMEOUTS
from app.models import Video, WorkflowStep, WorkflowStatus, StepStatus

logger = logging.getLogger(__name__)

async def check_step_timeouts():
    """Background task to detect and handle step timeouts."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()

        # Find steps that are IN_PROGRESS for too long
        in_progress_steps = db.query(WorkflowStep).filter(
            WorkflowStep.status == StepStatus.IN_PROGRESS
        ).all()

        for step in in_progress_steps:
            timeout_seconds = STEP_TIMEOUTS.get(step.step_type, 300)
            timeout_at = step.started_at + timedelta(seconds=timeout_seconds)

            if now > timeout_at:
                logger.warning(f"Step {step.id} ({step.step_type.value}) timed out")

                # Mark step as failed
                step.status = StepStatus.FAILED
                step.error_message = f"Generation timeout after {timeout_seconds}s"

                # Mark video as failed
                video = db.query(Video).filter(Video.id == step.video_id).first()
                if video:
                    video.status = WorkflowStatus.FAILED

                db.commit()

    finally:
        db.close()


async def timeout_monitor_loop():
    """Run timeout check every 30 seconds."""
    while True:
        try:
            await check_step_timeouts()
        except Exception as e:
            logger.error(f"Timeout monitor error: {e}")
        await asyncio.sleep(30)
```

**Register in app startup:**

```python
# backend/app/main.py
from app.services.workflow.timeout_monitor import timeout_monitor_loop

@app.on_event("startup")
async def startup():
    # Start timeout monitor
    asyncio.create_task(timeout_monitor_loop())
```

---

### 29.4 Step Error Handling (1h)

**Файл:** `backend/app/services/workflow/orchestrator.py`

```python
async def _run_step_with_error_handling(
    self,
    step_type: StepType,
    handler: Callable
) -> Any:
    """Run a step with proper error handling."""
    step = self._get_or_create_step(step_type)
    step.status = StepStatus.IN_PROGRESS
    step.started_at = datetime.utcnow()
    self.db.commit()

    try:
        result = await handler()

        step.status = StepStatus.AWAITING_APPROVAL if self._should_pause(step_type) else StepStatus.APPROVED
        step.completed_at = datetime.utcnow()
        self.db.commit()

        return result

    except Exception as e:
        logger.error(f"Step {step_type.value} failed: {e}")

        step.status = StepStatus.FAILED
        step.error_message = str(e)
        step.completed_at = datetime.utcnow()

        self.video.status = WorkflowStatus.FAILED
        self.db.commit()

        raise WorkflowError(
            step_type=step_type,
            message=str(e),
            video_id=self.video.id
        )
```

**Файл:** `backend/app/services/workflow/errors.py` (NEW)

```python
from app.models.video import StepType

class WorkflowError(Exception):
    """Base workflow error."""
    def __init__(self, step_type: StepType, message: str, video_id: int):
        self.step_type = step_type
        self.message = message
        self.video_id = video_id
        super().__init__(f"Step {step_type.value} failed: {message}")


class GenerationTimeoutError(WorkflowError):
    """Generation exceeded timeout."""
    pass


class RetryExhaustedError(WorkflowError):
    """All retries exhausted."""
    pass
```

---

### 29.5 Retry/Regenerate API (1h)

**Файл:** `backend/app/api/workflow_v2.py`

```python
@router.post("/{video_id}/{step_type}/retry")
async def retry_step(
    video_id: int,
    step_type: StepType,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retry a failed step (same parameters)."""
    video, step = get_video_and_step(video_id, step_type, db, current_user)

    if step.status != StepStatus.FAILED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot retry: step is {step.status.value}, expected FAILED"
        )

    # Reset step status
    step.status = StepStatus.IN_PROGRESS
    step.error_message = None
    step.started_at = datetime.utcnow()

    # Reset video status
    video.status = WorkflowStatus.IN_PROGRESS
    db.commit()

    # Start generation in background
    background_tasks.add_task(
        resume_step_generation,
        video_id=video.id,
        step_type=step_type
    )

    return {
        "status": "retrying",
        "step_type": step_type.value,
        "video_id": video_id
    }
```

---

## Acceptance Criteria

- [ ] Retry policy настраивается через env variables
- [ ] LLM calls: 3 retries с exponential backoff
- [ ] Image/Audio: 2 retries с backoff
- [ ] Video: 2 retries с большим backoff (5s, 10s)
- [ ] Timeout detection работает в background
- [ ] Failed step можно retry через API
- [ ] Error messages сохраняются в step.error_message

---

## Тестирование

```python
@pytest.mark.asyncio
async def test_retry_on_transient_error():
    with patch("openai_service.generate_story") as mock:
        # Fail twice, succeed on third
        mock.side_effect = [
            Exception("API error"),
            Exception("API error"),
            {"story": "Success"}
        ]

        result = await orchestrator._generate_story()

        assert result["story"] == "Success"
        assert mock.call_count == 3

@pytest.mark.asyncio
async def test_retry_exhausted():
    with patch("openai_service.generate_story") as mock:
        mock.side_effect = Exception("Always fails")

        with pytest.raises(Exception):
            await orchestrator._generate_story()

        assert mock.call_count == 4  # 1 + 3 retries

@pytest.mark.asyncio
async def test_timeout_detection():
    step = create_step(status=StepStatus.IN_PROGRESS)
    step.started_at = datetime.utcnow() - timedelta(minutes=30)  # Long ago
    db.commit()

    await check_step_timeouts()

    db.refresh(step)
    assert step.status == StepStatus.FAILED
    assert "timeout" in step.error_message.lower()

@pytest.mark.asyncio
async def test_retry_api():
    video = create_video(status=WorkflowStatus.FAILED)
    step = create_step(video, StepType.STORY, status=StepStatus.FAILED)

    response = await client.post(f"/workflow/{video.id}/story/retry")

    assert response.status_code == 200
    db.refresh(step)
    assert step.status == StepStatus.IN_PROGRESS
```

---

## Checklist

- [ ] 29.1 Retry config in settings
- [ ] 29.2 @with_retry decorator
- [ ] 29.3 Timeout monitor background task
- [ ] 29.4 Step error handling in orchestrator
- [ ] 29.5 POST /{video_id}/{step_type}/retry endpoint
- [ ] All services use @with_retry
- [ ] Tests pass
- [ ] Code review

---

**Создано:** 2026-01-10
**Статус:** TODO
