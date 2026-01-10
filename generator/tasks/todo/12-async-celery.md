# Task 12: Перевод генерации на Celery

**Приоритет:** P0 (критический)
**Оценка:** 1 неделя
**Зависимости:** Task 11 (тесты)

## Проблема

Синхронные long-polling операции блокируют workers до 15 минут.

**Текущий код (`piapi_client.py:337-383`):**

```python
async def wait_for_video(self, task_id: str, max_wait_time: int = 900, ...):
    elapsed = 0
    while elapsed < max_wait_time:  # 900 секунд = 15 МИНУТ!
        result = await self.get_task_status(task_id)
        if status in ["completed", "succeeded", "success"]:
            return video_url
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval
```

**Проблемы:**
- HTTP request висит до 15 минут
- Блокирует uvicorn worker
- Nginx/browser timeout
- Нет прогресса для пользователя
- Retry невозможен

## Цель

Асинхронная генерация через Celery с real-time обновлениями.

## Целевая архитектура

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│    Redis    │
│             │     │   FastAPI   │     │   (Queue)   │
└─────────────┘     └─────────────┘     └──────┬──────┘
       │                                       │
       │ WebSocket                             │
       │ (status updates)                      ▼
       │                              ┌─────────────┐
       └─────────────────────────────▶│   Celery    │
                                      │   Worker    │
                                      └──────┬──────┘
                                             │
                                             ▼
                                      ┌─────────────┐
                                      │   PiAPI     │
                                      │  (KLING)    │
                                      └─────────────┘
```

## Детальный план

### Phase 1: Celery Tasks (3-4 часа)

**Файл:** `backend/app/tasks/workflow_tasks.py`

```python
from celery import shared_task
from sqlalchemy.orm import Session
from app.db.base import SessionLocal
from app.models.video import Video, StepType, WorkflowStatus
from app.models.workflow_step import WorkflowStep
from app.services.piapi_client import piapi_client
from app.services.openai_service import openai_service
import logging

logger = logging.getLogger(__name__)

def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_image_task(self, video_id: int, prompt: str, aspect_ratio: str = "9:16"):
    """Background task for image generation"""
    db = get_db()

    try:
        video = db.query(Video).get(video_id)
        step = db.query(WorkflowStep).filter(
            WorkflowStep.video_id == video_id,
            WorkflowStep.step_type == StepType.IMAGE
        ).first()

        if not step:
            step = WorkflowStep(
                video_id=video_id,
                step_type=StepType.IMAGE,
                status=WorkflowStatus.IN_PROGRESS
            )
            db.add(step)
            db.commit()

        # Update status
        step.status = WorkflowStatus.IN_PROGRESS
        step.celery_task_id = self.request.id
        db.commit()

        # Sync wrapper for async function
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            image_url = loop.run_until_complete(
                piapi_client.generate_image(prompt=prompt, aspect_ratio=aspect_ratio)
            )
        finally:
            loop.close()

        # Update with result
        step.content = {"image_url": image_url}
        step.status = WorkflowStatus.AWAITING_APPROVAL
        video.image_url = image_url
        video.current_step = StepType.IMAGE
        db.commit()

        return {"status": "completed", "image_url": image_url}

    except Exception as e:
        logger.exception(f"Image generation failed for video {video_id}")
        if step:
            step.status = WorkflowStatus.FAILED
            step.content = {"error": str(e)}
            db.commit()
        raise self.retry(exc=e)
    finally:
        db.close()


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def generate_video_task(self, video_id: int, image_url: str, prompt: str, duration: int = 5):
    """Background task for video generation (long-running)"""
    db = get_db()

    try:
        video = db.query(Video).get(video_id)
        step = db.query(WorkflowStep).filter(
            WorkflowStep.video_id == video_id,
            WorkflowStep.step_type == StepType.VIDEO
        ).first()

        if not step:
            step = WorkflowStep(
                video_id=video_id,
                step_type=StepType.VIDEO,
                status=WorkflowStatus.IN_PROGRESS
            )
            db.add(step)
            db.commit()

        step.status = WorkflowStatus.IN_PROGRESS
        step.celery_task_id = self.request.id
        db.commit()

        # Run async in sync context
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            video_url, task_id = loop.run_until_complete(
                piapi_client.generate_video_from_image(
                    image_url=image_url,
                    prompt=prompt,
                    duration=duration,
                    return_task_id=True
                )
            )
        finally:
            loop.close()

        step.content = {"video_url": video_url, "task_id": task_id}
        step.status = WorkflowStatus.AWAITING_APPROVAL
        video.video_url = video_url
        video.video_task_id = task_id
        video.current_step = StepType.VIDEO
        db.commit()

        return {"status": "completed", "video_url": video_url, "task_id": task_id}

    except Exception as e:
        logger.exception(f"Video generation failed for video {video_id}")
        if step:
            step.status = WorkflowStatus.FAILED
            db.commit()
        raise self.retry(exc=e)
    finally:
        db.close()


@shared_task(bind=True)
def auto_generate_task(self, video_id: int):
    """Full auto-generation pipeline as background task"""
    db = get_db()

    try:
        video = db.query(Video).get(video_id)
        project = video.project

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Step 1: Story
            update_step_status(db, video_id, StepType.STORY, WorkflowStatus.IN_PROGRESS)
            story_data = loop.run_until_complete(
                openai_service.generate_story_from_template(
                    story_template=project.story_template,
                    content_variables=video.content_variables or {},
                    duration=project.duration,
                    platforms=project.platforms
                )
            )
            save_step_result(db, video, StepType.STORY, story_data, "story_data")

            # Step 2: Description
            update_step_status(db, video_id, StepType.DESCRIPTION, WorkflowStatus.IN_PROGRESS)
            description_data = loop.run_until_complete(
                openai_service.generate_description(story_data)
            )
            save_step_result(db, video, StepType.DESCRIPTION, description_data, "description_data")

            # ... остальные шаги аналогично

        finally:
            loop.close()

        return {"status": "completed", "video_id": video_id}

    except Exception as e:
        logger.exception(f"Auto-generation failed for video {video_id}")
        video.status = WorkflowStatus.FAILED
        db.commit()
        raise
    finally:
        db.close()


def update_step_status(db: Session, video_id: int, step_type: StepType, status: WorkflowStatus):
    """Helper to update step status"""
    step = db.query(WorkflowStep).filter(
        WorkflowStep.video_id == video_id,
        WorkflowStep.step_type == step_type
    ).first()

    if not step:
        step = WorkflowStep(video_id=video_id, step_type=step_type)
        db.add(step)

    step.status = status
    db.commit()


def save_step_result(db: Session, video: Video, step_type: StepType, content: dict, field: str):
    """Helper to save step result"""
    step = db.query(WorkflowStep).filter(
        WorkflowStep.video_id == video.id,
        WorkflowStep.step_type == step_type
    ).first()

    step.content = content
    step.status = WorkflowStatus.APPROVED  # Auto-approve in auto mode
    setattr(video, field, content)
    db.commit()
```

### Phase 2: API Endpoints (2-3 часа)

**Файл:** `backend/app/api/workflow.py` (обновление)

```python
from app.tasks.workflow_tasks import generate_image_task, generate_video_task, auto_generate_task
from celery.result import AsyncResult

@router.post("/generate-image")
async def generate_image(
    request: GenerateImageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Запуск генерации изображения в фоне"""
    video = db.query(Video).filter(Video.id == request.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    verify_video_ownership(db, video, current_user)

    # Создаем step
    step = WorkflowStep(
        video_id=video.id,
        step_type=StepType.IMAGE,
        status=WorkflowStatus.PENDING
    )
    db.add(step)
    db.commit()

    # Запускаем в Celery
    task = generate_image_task.delay(
        video_id=video.id,
        prompt=request.prompt or request.prompt_data.get("main_prompt", ""),
        aspect_ratio=request.aspect_ratio
    )

    # Сохраняем task_id
    step.celery_task_id = task.id
    step.status = WorkflowStatus.IN_PROGRESS
    db.commit()

    return {
        "step_id": step.id,
        "task_id": task.id,
        "status": "queued",
        "message": "Image generation started. Poll /api/workflow/status/{task_id} for updates."
    }


@router.get("/status/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Получить статус Celery task"""
    result = AsyncResult(task_id)

    response = {
        "task_id": task_id,
        "status": result.status,
        "ready": result.ready()
    }

    if result.ready():
        if result.successful():
            response["result"] = result.result
        else:
            response["error"] = str(result.result)

    return response


@router.post("/auto-generate-to-video")
async def auto_generate_to_video(
    request: AutoGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Запуск полной автогенерации в фоне"""
    video = db.query(Video).filter(Video.id == request.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    verify_video_ownership(db, video, current_user)

    # Запускаем в Celery
    task = auto_generate_task.delay(video_id=video.id)

    video.status = WorkflowStatus.IN_PROGRESS
    db.commit()

    return {
        "video_id": video.id,
        "task_id": task.id,
        "status": "queued",
        "message": "Auto-generation started. This may take 5-15 minutes."
    }
```

### Phase 3: WebSocket для обновлений (4-6 часов)

**Файл:** `backend/app/api/websocket.py`

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set
import asyncio
import json

router = APIRouter()

# Connection manager
class ConnectionManager:
    def __init__(self):
        # video_id -> set of websockets
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, video_id: int):
        await websocket.accept()
        if video_id not in self.active_connections:
            self.active_connections[video_id] = set()
        self.active_connections[video_id].add(websocket)

    def disconnect(self, websocket: WebSocket, video_id: int):
        if video_id in self.active_connections:
            self.active_connections[video_id].discard(websocket)

    async def broadcast_to_video(self, video_id: int, message: dict):
        if video_id in self.active_connections:
            dead_connections = set()
            for websocket in self.active_connections[video_id]:
                try:
                    await websocket.send_json(message)
                except:
                    dead_connections.add(websocket)

            # Cleanup dead connections
            self.active_connections[video_id] -= dead_connections

manager = ConnectionManager()


@router.websocket("/ws/video/{video_id}")
async def video_status_websocket(
    websocket: WebSocket,
    video_id: int
):
    """WebSocket для real-time обновлений статуса видео"""
    await manager.connect(websocket, video_id)

    try:
        while True:
            # Keep connection alive, receive any client messages
            data = await websocket.receive_text()
            # Could handle ping/pong here
    except WebSocketDisconnect:
        manager.disconnect(websocket, video_id)


# Helper to broadcast from Celery tasks
def notify_video_status(video_id: int, step_type: str, status: str, data: dict = None):
    """Call this from Celery tasks to notify clients"""
    import asyncio
    from app.core.redis import get_redis

    message = {
        "video_id": video_id,
        "step_type": step_type,
        "status": status,
        "data": data or {}
    }

    # Publish to Redis channel
    redis = get_redis()
    redis.publish(f"video:{video_id}", json.dumps(message))
```

**Файл:** `backend/app/core/redis.py`

```python
import redis
from app.core.config import settings

_redis_client = None

def get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL)
    return _redis_client
```

### Phase 4: Frontend Integration (3-4 часа)

**Файл:** `frontend/src/hooks/useVideoStatus.ts`

```typescript
import { useEffect, useState, useCallback } from 'react';

interface VideoStatus {
  step_type: string;
  status: string;
  data?: any;
}

export function useVideoStatus(videoId: number) {
  const [status, setStatus] = useState<VideoStatus | null>(null);
  const [connected, setConnected] = useState(false);
  const [ws, setWs] = useState<WebSocket | null>(null);

  useEffect(() => {
    const wsUrl = `ws://localhost:8000/api/ws/video/${videoId}`;
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      setConnected(true);
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setStatus(data);
    };

    socket.onclose = () => {
      setConnected(false);
    };

    setWs(socket);

    return () => {
      socket.close();
    };
  }, [videoId]);

  return { status, connected };
}
```

**Файл:** `frontend/src/components/VideoGenerationProgress.tsx`

```typescript
import { useVideoStatus } from '@/hooks/useVideoStatus';

interface Props {
  videoId: number;
  onComplete: () => void;
}

const STEP_LABELS: Record<string, string> = {
  story: 'Generating Story',
  description: 'Creating Description',
  prompt: 'Building Prompt',
  image: 'Generating Image',
  scenario: 'Creating Scenario',
  video: 'Generating Video',
  audio: 'Adding Audio',
  adaptation: 'Adapting for Platforms'
};

export function VideoGenerationProgress({ videoId, onComplete }: Props) {
  const { status, connected } = useVideoStatus(videoId);

  useEffect(() => {
    if (status?.status === 'completed') {
      onComplete();
    }
  }, [status, onComplete]);

  if (!connected) {
    return <div>Connecting...</div>;
  }

  if (!status) {
    return <div>Waiting for updates...</div>;
  }

  const label = STEP_LABELS[status.step_type] || status.step_type;

  return (
    <div className="p-4 bg-gray-100 rounded-lg">
      <div className="flex items-center space-x-3">
        <div className="animate-spin h-5 w-5 border-2 border-blue-500 border-t-transparent rounded-full" />
        <span className="font-medium">{label}</span>
      </div>
      {status.status === 'failed' && (
        <div className="mt-2 text-red-500">
          Generation failed. Please try again.
        </div>
      )}
    </div>
  );
}
```

### Phase 5: Обновление Celery tasks для WebSocket (2 часа)

**Файл:** `backend/app/tasks/workflow_tasks.py` (обновление)

```python
from app.api.websocket import notify_video_status

@shared_task(bind=True, max_retries=3)
def generate_video_task(self, video_id: int, image_url: str, prompt: str, duration: int = 5):
    db = get_db()

    try:
        # Notify: started
        notify_video_status(video_id, "video", "in_progress")

        # ... generation logic ...

        # Notify: completed
        notify_video_status(video_id, "video", "completed", {"video_url": video_url})

        return {"status": "completed", "video_url": video_url}

    except Exception as e:
        # Notify: failed
        notify_video_status(video_id, "video", "failed", {"error": str(e)})
        raise
```

## Конфигурация

**Файл:** `backend/app/core/celery_app.py` (обновление)

```python
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "generator",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.workflow_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,  # 30 min max
    worker_prefetch_multiplier=1,  # One task at a time for long-running
)
```

## Команды запуска

```bash
# Redis
docker run -d -p 6379:6379 redis:7

# Celery worker
cd backend
celery -A app.core.celery_app worker --loglevel=info --concurrency=4

# Celery flower (мониторинг)
celery -A app.core.celery_app flower --port=5555
```

## Чеклист

- [ ] Создать `app/tasks/workflow_tasks.py`
- [ ] Обновить API endpoints для возврата task_id
- [ ] Добавить `/status/{task_id}` endpoint
- [ ] Реализовать WebSocket manager
- [ ] Добавить Redis pub/sub для уведомлений
- [ ] Создать `useVideoStatus` hook
- [ ] Создать `VideoGenerationProgress` компонент
- [ ] Обновить Celery конфигурацию
- [ ] Добавить Flower для мониторинга
- [ ] Тесты для tasks

## Метрики успеха

| Метрика | До | После |
|---------|-----|-------|
| Время ответа API | 15 мин | <1 сек |
| Workers блокированы | Да | Нет |
| Real-time progress | Нет | Да |
| Retry при ошибке | Нет | Автоматический |

---

**Статус:** Ожидает Task 11 (тесты)
**Ответственный:** TBD
