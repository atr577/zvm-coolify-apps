# Task 02: Backend - API Endpoints

**Phase:** 2
**Приоритет:** Высокий
**Оценка:** 4-6 часов
**Зависимости:** Task 01 (Backend Models)

## Цель

Создать API endpoints для работы с проектами, видео и генерации контента.

## Подзадачи

### 2.1 Projects CRUD API

**Файл:** `backend/app/api/projects.py` (переписать)

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.base import get_db
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse

router = APIRouter()

@router.post("/", response_model=ProjectResponse)
async def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    """Создать новый проект"""
    db_project = Project(**project.dict())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Получить список проектов"""
    projects = db.query(Project).offset(skip).limit(limit).all()
    return projects

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: int, db: Session = Depends(get_db)):
    """Получить проект по ID"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    db: Session = Depends(get_db)
):
    """Обновить проект (редактирование шаблона)"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    for field, value in project_update.dict(exclude_unset=True).items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)
    return project

@router.delete("/{project_id}")
async def delete_project(project_id: int, db: Session = Depends(get_db)):
    """Удалить проект"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()
    return {"message": "Project deleted successfully"}
```

**Чеклист:**
- [ ] POST /api/projects - создание проекта
- [ ] GET /api/projects - список проектов
- [ ] GET /api/projects/{id} - получить проект
- [ ] PATCH /api/projects/{id} - обновить проект
- [ ] DELETE /api/projects/{id} - удалить проект

---

### 2.2 Videos CRUD API

**Файл:** `backend/app/api/videos.py` (новый)

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.base import get_db
from app.models.video import Video
from app.models.project import Project
from app.schemas.video import VideoCreate, VideoUpdate, VideoResponse

router = APIRouter()

@router.post("/", response_model=VideoResponse)
async def create_video(video: VideoCreate, db: Session = Depends(get_db)):
    """Создать новое видео"""
    # Проверить что проект существует
    project = db.query(Project).filter(Project.id == video.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db_video = Video(**video.dict())
    db.add(db_video)
    db.commit()
    db.refresh(db_video)
    return db_video

@router.get("/project/{project_id}", response_model=List[VideoResponse])
async def list_videos_by_project(
    project_id: int,
    db: Session = Depends(get_db)
):
    """Получить все видео проекта"""
    videos = db.query(Video).filter(Video.project_id == project_id).all()
    return videos

@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(video_id: int, db: Session = Depends(get_db)):
    """Получить видео по ID"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video

@router.patch("/{video_id}", response_model=VideoResponse)
async def update_video(
    video_id: int,
    video_update: VideoUpdate,
    db: Session = Depends(get_db)
):
    """Обновить видео"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    for field, value in video_update.dict(exclude_unset=True).items():
        setattr(video, field, value)

    db.commit()
    db.refresh(video)
    return video

@router.delete("/{video_id}")
async def delete_video(video_id: int, db: Session = Depends(get_db)):
    """Удалить видео"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    db.delete(video)
    db.commit()
    return {"message": "Video deleted successfully"}
```

**Чеклист:**
- [ ] POST /api/videos - создание видео
- [ ] GET /api/videos/project/{project_id} - список видео проекта
- [ ] GET /api/videos/{id} - получить видео
- [ ] PATCH /api/videos/{id} - обновить видео
- [ ] DELETE /api/videos/{id} - удалить видео

---

### 2.3 AI Content Generation API

**Файл:** `backend/app/api/ai_generation.py` (новый)

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.db.base import get_db
from app.models.project import Project
from app.services.openai_service import openai_service

router = APIRouter()

@router.post("/generate-variants")
async def generate_content_variants(
    project_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Генерирует 10 вариантов контента на основе Story Template проекта

    Возвращает:
    {
        "variants": [
            {
                "id": 1,
                "description": "Блондинка в красном платье, Ferrari красная, Париж, закат",
                "content_variables": {
                    "character": {
                        "appearance": "blonde",
                        "outfit": "red evening dress",
                        "age": "25"
                    },
                    "vehicle": {
                        "brand": "Ferrari SF90",
                        "color": "red"
                    },
                    "location": {
                        "city": "Paris",
                        "landmark": "Eiffel Tower",
                        "time": "sunset"
                    }
                }
            },
            ... (еще 9 вариантов)
        ]
    }
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Вызываем AI для генерации вариантов
    variants = await openai_service.generate_content_variants(
        story_template=project.story_template,
        count=10
    )

    return {"variants": variants}

@router.post("/regenerate-variants")
async def regenerate_content_variants(
    project_id: int,
    exclude_variants: List[Dict[str, Any]] = [],
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Регенерирует 10 новых вариантов, исключая уже показанные
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    variants = await openai_service.generate_content_variants(
        story_template=project.story_template,
        count=10,
        exclude=exclude_variants
    )

    return {"variants": variants}
```

**Чеклист:**
- [ ] POST /api/ai/generate-variants - генерация 10 вариантов
- [ ] POST /api/ai/regenerate-variants - регенерация вариантов
- [ ] Интеграция с openai_service
- [ ] Обработка ошибок AI

---

### 2.4 Workflow API (переписать)

**Файл:** `backend/app/api/workflow.py` (переписать)

Основные изменения:
- Все endpoints теперь работают с `video_id` вместо `project_id`
- WorkflowStep связан с Video, а не с Project

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.db.base import get_db
from app.models.video import Video, WorkflowStep, StepType, WorkflowStatus
from app.models.validation_result import ValidationResult, ValidationStatus
from app.schemas.workflow import (
    GenerateStoryRequest,
    GenerateDescriptionRequest,
    GeneratePromptRequest,
    GenerateImageRequest,
    GenerateScenarioRequest,
    GenerateVideoRequest,
    AdaptForPlatformsRequest,
    ApprovalRequest
)
from app.services.openai_service import openai_service
from app.services.kling_service import kling_service

router = APIRouter()

@router.post("/generate-story")
async def generate_story(
    video_id: int,
    request: GenerateStoryRequest,
    db: Session = Depends(get_db)
):
    """Этап 1: Генерация сюжета для конкретного видео"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Создаем workflow step
    step = WorkflowStep(
        video_id=video.id,
        step_type=StepType.STORY,
        status=WorkflowStatus.IN_PROGRESS,
        started_at=datetime.utcnow()
    )
    db.add(step)
    db.commit()

    # Генерируем сюжет (Story Template + Content Variables)
    story_data = await openai_service.generate_story_from_template(
        story_template=video.project.story_template,
        content_variables=video.content_variables,
        duration=video.project.duration,
        platforms=video.project.platforms
    )

    step.content = story_data
    video.story_data = story_data
    video.current_step = StepType.STORY
    video.status = WorkflowStatus.IN_PROGRESS

    # Валидация (если это template video)
    if video.is_template:
        validation = await validate_and_save(db, step, story_data, "story")
    else:
        # Для обычных видео - пропускаем валидацию
        step.status = WorkflowStatus.APPROVED
        step.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(step)

    return {
        "step_id": step.id,
        "content": story_data,
        "validation": validation if video.is_template else None
    }

# Аналогично для остальных endpoints:
# - generate-description
# - generate-prompt
# - generate-image
# - generate-scenario
# - generate-video
# - adapt-for-platforms

@router.post("/approve-step")
async def approve_step(
    request: ApprovalRequest,
    db: Session = Depends(get_db)
):
    """Одобрение/отклонение checkpoint"""
    step = db.query(WorkflowStep).filter(WorkflowStep.id == request.step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    step.user_approved = request.approved
    step.user_feedback = request.feedback

    if request.approved:
        step.status = WorkflowStatus.APPROVED
        step.completed_at = datetime.utcnow()

        # Update video current_step to next step
        video = step.video
        next_step_map = {
            StepType.STORY: StepType.DESCRIPTION,
            StepType.DESCRIPTION: StepType.PROMPT,
            StepType.PROMPT: StepType.IMAGE,
            StepType.IMAGE: StepType.SCENARIO,
            StepType.SCENARIO: StepType.VIDEO,
            StepType.VIDEO: StepType.ADAPTATION,
            StepType.ADAPTATION: StepType.PUBLISHING,
        }
        if step.step_type in next_step_map:
            video.current_step = next_step_map[step.step_type]
    else:
        if request.regenerate:
            step.status = WorkflowStatus.PENDING
            step.user_approved = False
            step.validation_attempts = 0
            message = "Step rejected. Ready for regeneration."
        else:
            step.status = WorkflowStatus.REJECTED
            message = "Step rejected"

    db.commit()
    db.refresh(step)

    return {
        "step_id": step.id,
        "status": step.status.value,
        "message": "Step approved" if request.approved else message
    }

@router.post("/auto-generate-to-video")
async def auto_generate_to_video(
    video_id: int,
    db: Session = Depends(get_db)
):
    """
    Автоматическая генерация всех этапов до видео (для обычных роликов)
    Steps 1-6 без checkpoints
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Последовательная генерация всех этапов
    # 1. Story
    await generate_story(video_id, ...)
    # 2. Description
    await generate_description(video_id, ...)
    # 3. Prompt
    # 4. Image
    # 5. Scenario
    # 6. Video

    return {"message": "Video generated successfully", "video_id": video_id}
```

**Чеклист:**
- [ ] Переписать все workflow endpoints для работы с video_id
- [ ] Добавить логику для template vs обычных видео
- [ ] Реализовать auto-generate-to-video endpoint
- [ ] Обновить схемы запросов (убрать project_id, добавить video_id)
- [ ] Добавить сохранение prompt_used и generation_time в WorkflowStep

---

### 2.5 Обновить main.py

**Файл:** `backend/app/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import projects, videos, ai_generation, workflow, publishing

app = FastAPI(title="REGGY")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(videos.router, prefix="/api/videos", tags=["videos"])
app.include_router(ai_generation.router, prefix="/api/ai", tags=["ai"])
app.include_router(workflow.router, prefix="/api/workflow", tags=["workflow"])
app.include_router(publishing.router, prefix="/api/publish", tags=["publishing"])

@app.get("/")
def read_root():
    return {"message": "REGGY API"}
```

**Чеклист:**
- [ ] Добавить новые роутеры
- [ ] Обновить CORS если нужно
- [ ] Проверить что все endpoints доступны

---

### 2.6 Обновить AI Service

**Файл:** `backend/app/services/openai_service.py`

Добавить новый метод:

```python
async def generate_content_variants(
    self,
    story_template: str,
    count: int = 10,
    exclude: List[Dict] = []
) -> List[Dict]:
    """
    Генерирует N вариантов контента на основе Story Template

    Returns:
    [
        {
            "id": 1,
            "description": "Блондинка, Ferrari, Париж",
            "content_variables": {...}
        },
        ...
    ]
    """
    prompt = f"""
    Based on this story template, generate {count} unique content variations.

    Story Template:
    {story_template}

    For each variation, provide:
    1. Character details (appearance, outfit, age)
    2. Vehicle details (brand, model, color)
    3. Location details (city, landmark, time of day)

    Make variations diverse and interesting.
    Avoid these already generated variations: {exclude}

    Return as JSON array.
    """

    response = await self.aimlapi_client.generate_json(
        prompt=prompt,
        model=self.model
    )

    return response

async def generate_story_from_template(
    self,
    story_template: str,
    content_variables: Dict,
    duration: int,
    platforms: List[str]
) -> Dict:
    """
    Генерирует Story, комбинируя шаблон и конкретные переменные
    """
    prompt = f"""
    Create a detailed story based on:

    Template: {story_template}

    Specific content:
    - Character: {content_variables.get('character')}
    - Vehicle: {content_variables.get('vehicle')}
    - Location: {content_variables.get('location')}

    Duration: {duration} seconds
    Platforms: {', '.join(platforms)}

    Return detailed story structure as JSON.
    """

    response = await self.aimlapi_client.generate_json(
        prompt=prompt,
        model=self.model
    )

    return response
```

**Чеклист:**
- [ ] Добавить generate_content_variants
- [ ] Добавить generate_story_from_template
- [ ] Обновить остальные методы если нужно
- [ ] Добавить error handling

---

## Проверка результата

Тестирование через Swagger UI (http://localhost:8000/docs):

1. **Projects API:**
   - [ ] Создать проект
   - [ ] Получить список проектов
   - [ ] Обновить проект
   - [ ] Удалить проект

2. **AI Generation:**
   - [ ] Сгенерировать 10 вариантов
   - [ ] Регенерировать варианты

3. **Videos API:**
   - [ ] Создать видео с выбранным вариантом
   - [ ] Получить список видео проекта

4. **Workflow API:**
   - [ ] Запустить генерацию story
   - [ ] Approve step
   - [ ] Автогенерация до видео

**Критерии приемки:**
- [ ] Все endpoints работают без ошибок
- [ ] Данные корректно сохраняются в БД
- [ ] Relationships между моделями работают
- [ ] AI генерация возвращает валидные данные

---

**Статус:** ✅ Завершено (частично)

**Выполнено:**
- ✅ Projects CRUD API (переписан)
- ✅ Videos CRUD API (создан)
- ✅ AI Generation API (создан: generate-variants, regenerate-variants)
- ✅ Workflow API (переписан на video_id вместо project_id)
- ✅ main.py обновлен (добавлены новые роутеры)
- ✅ openai_service.py обновлен (добавлен generate_content_variants)
- ✅ workflow schemas обновлены (video_id вместо project_id)

**TODO для будущей итерации:**
- [ ] Workflow API: добавить логику template vs обычные видео (skip validation для не-template)
- [ ] Добавить endpoint /auto-generate-to-video для автоматической генерации
- [ ] Добавить метод generate_story_from_template в openai_service.py
- [ ] Сохранение prompt_used и generation_time в WorkflowStep (debug поля уже есть в модели)

**Ответственный:** Backend Developer
