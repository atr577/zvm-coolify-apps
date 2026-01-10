---
id: T1
title: "Backend - Database Models"
status: done
priority: high
created: 2026-01-10
updated: 2026-01-10
tags: ['backend']
depends_on: []
estimate: "2-3 часа"
branch: ""
---

# Task 01: Backend - Database Models

## Цель

Создать новые модели базы данных с чистого листа.

## Подзадачи

### 1.1 Drop существующие таблицы

**Файл:** `backend/app/db/base.py` или через Alembic

```bash
# Вариант 1: Удалить файл базы данных (если SQLite)
rm backend/data/app.db

# Вариант 2: Через Alembic
alembic downgrade base
```

**Чеклист:**
- [ ] Удалить файл БД или выполнить downgrade
- [ ] Удалить папку `backend/alembic/versions/`
- [ ] Создать новую начальную миграцию

---

### 1.2 Создать новую модель Project

**Файл:** `backend/app/models/project.py`

```python
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base_class import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Template
    story_template = Column(Text, nullable=False)

    # Settings
    platforms = Column(JSON, nullable=False)  # ["instagram", "tiktok", "youtube"]
    duration = Column(Integer, nullable=False)  # 5, 10, 15

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    videos = relationship("Video", back_populates="project", cascade="all, delete-orphan")
```

**Чеклист:**
- [ ] Создать класс Project
- [ ] Добавить все поля
- [ ] Настроить relationship с Video
- [ ] Добавить __repr__ для отладки

---

### 1.3 Создать новую модель Video

**Файл:** `backend/app/models/video.py`

```python
from sqlalchemy import Column, Integer, String, Text, JSON, Boolean, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base_class import Base
import enum

class StepType(str, enum.Enum):
    STORY = "story"
    DESCRIPTION = "description"
    PROMPT = "prompt"
    IMAGE = "image"
    SCENARIO = "scenario"
    VIDEO = "video"
    ADAPTATION = "adaptation"
    PUBLISHING = "publishing"

class WorkflowStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VALIDATING = "validating"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"
    VALIDATION_FAILED = "validation_failed"

class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    title = Column(String(255), nullable=False)

    # Template flag
    is_template = Column(Boolean, default=False)
    template_video_id = Column(Integer, ForeignKey("videos.id"), nullable=True)

    # AI-generated variables
    content_variables = Column(JSON, nullable=True)

    # Workflow data
    story_data = Column(JSON, nullable=True)
    description_data = Column(JSON, nullable=True)
    image_prompt = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)
    scenario_data = Column(JSON, nullable=True)
    video_url = Column(Text, nullable=True)
    adaptation_data = Column(JSON, nullable=True)

    # State
    current_step = Column(SQLEnum(StepType), default=StepType.STORY)
    status = Column(SQLEnum(WorkflowStatus), default=WorkflowStatus.PENDING)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="videos")
    workflow_steps = relationship("WorkflowStep", back_populates="video", cascade="all, delete-orphan")
    template_video = relationship("Video", remote_side=[id], backref="derived_videos")
```

**Чеклист:**
- [ ] Создать Enums (StepType, WorkflowStatus)
- [ ] Создать класс Video
- [ ] Добавить все поля
- [ ] Настроить relationships (project, workflow_steps, template_video)
- [ ] Добавить __repr__

---

### 1.4 Создать модель WorkflowStep

**Файл:** `backend/app/models/workflow_step.py`

```python
from sqlalchemy import Column, Integer, String, Text, JSON, Boolean, Float, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base_class import Base
from app.models.video import StepType, WorkflowStatus

class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)

    step_type = Column(SQLEnum(StepType), nullable=False)
    status = Column(SQLEnum(WorkflowStatus), default=WorkflowStatus.PENDING)
    content = Column(JSON, nullable=True)

    # User feedback
    user_approved = Column(Boolean, nullable=True)
    user_feedback = Column(Text, nullable=True)

    # Validation
    validation_attempts = Column(Integer, default=0)
    max_validation_attempts = Column(Integer, default=3)

    # Debug info
    prompt_used = Column(Text, nullable=True)
    generation_time_seconds = Column(Float, nullable=True)

    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    video = relationship("Video", back_populates="workflow_steps")
    validations = relationship("ValidationResult", back_populates="step", cascade="all, delete-orphan")
```

**Чеклист:**
- [ ] Создать класс WorkflowStep
- [ ] Добавить все поля
- [ ] Настроить relationships (video, validations)
- [ ] Добавить __repr__

---

### 1.5 Создать модель ValidationResult

**Файл:** `backend/app/models/validation_result.py`

```python
from sqlalchemy import Column, Integer, Float, JSON, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base_class import Base
import enum

class ValidationStatus(str, enum.Enum):
    PASS = "pass"
    PASS_WITH_WARNINGS = "pass_with_warnings"
    FAIL = "fail"

class ValidationResult(Base):
    __tablename__ = "validation_results"

    id = Column(Integer, primary_key=True, index=True)
    step_id = Column(Integer, ForeignKey("workflow_steps.id"), nullable=False)

    status = Column(SQLEnum(ValidationStatus), nullable=False)
    score = Column(Float, nullable=True)

    criteria_results = Column(JSON, nullable=True)
    warnings = Column(JSON, nullable=True)
    errors = Column(JSON, nullable=True)
    recommendations = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    step = relationship("WorkflowStep", back_populates="validations")
```

**Чеклист:**
- [ ] Создать Enum ValidationStatus
- [ ] Создать класс ValidationResult
- [ ] Добавить все поля
- [ ] Настроить relationship (step)
- [ ] Добавить __repr__

---

### 1.6 Обновить схемы Pydantic

**Файл:** `backend/app/schemas/project.py` (новый)

```python
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    story_template: str
    platforms: List[str]
    duration: int

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    story_template: Optional[str] = None
    platforms: Optional[List[str]] = None
    duration: Optional[int] = None

class ProjectResponse(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

**Файл:** `backend/app/schemas/video.py` (новый)

```python
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class VideoBase(BaseModel):
    title: str
    is_template: bool = False
    content_variables: Optional[Dict[str, Any]] = None

class VideoCreate(VideoBase):
    project_id: int

class VideoUpdate(BaseModel):
    title: Optional[str] = None
    is_template: Optional[bool] = None
    content_variables: Optional[Dict[str, Any]] = None

class VideoResponse(VideoBase):
    id: int
    project_id: int
    template_video_id: Optional[int] = None

    story_data: Optional[Dict[str, Any]] = None
    description_data: Optional[Dict[str, Any]] = None
    image_prompt: Optional[str] = None
    image_url: Optional[str] = None
    scenario_data: Optional[Dict[str, Any]] = None
    video_url: Optional[str] = None
    adaptation_data: Optional[Dict[str, Any]] = None

    current_step: str
    status: str

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

**Чеклист:**
- [ ] Создать schemas/project.py
- [ ] Создать schemas/video.py
- [ ] Обновить schemas/workflow.py (если нужно)
- [ ] Удалить старые неиспользуемые схемы

---

### 1.7 Создать Alembic миграцию

```bash
cd backend
alembic revision --autogenerate -m "Initial schema: projects and videos"
alembic upgrade head
```

**Чеклист:**
- [ ] Сгенерировать миграцию
- [ ] Проверить сгенерированный файл миграции
- [ ] Применить миграцию
- [ ] Проверить что все таблицы созданы

---

## Проверка результата

```python
# Тестовый скрипт для проверки
from app.db.base import SessionLocal
from app.models.project import Project
from app.models.video import Video

db = SessionLocal()

# Создать проект
project = Project(
    name="Test Project",
    story_template="Test template",
    platforms=["instagram", "tiktok"],
    duration=5
)
db.add(project)
db.commit()

# Создать видео
video = Video(
    project_id=project.id,
    title="Test Video",
    is_template=True,
    content_variables={"test": "data"}
)
db.add(video)
db.commit()

print(f"Project: {project.id} - {project.name}")
print(f"Video: {video.id} - {video.title}")
print(f"Relationship works: {project.videos}")

db.close()
```

**Критерии приемки:**
- [ ] Все модели созданы и работают
- [ ] Relationships между моделями работают
- [ ] Миграция применена успешно
- [ ] Тестовый скрипт выполняется без ошибок

---

**Статус:** ✅ Выполнено
**Ответственный:** Backend Developer

## Ключевые моменты выполнения

### Выполнено:
- ✅ Удалена старая БД (generator.db)
- ✅ Создана модель Project (без workflow данных, только template)
- ✅ Создана модель Video (с workflow данными, связь с Project)
- ✅ Создана модель WorkflowStep (связь с Video через video_id)
- ✅ Создана модель ValidationResult (связь с WorkflowStep)
- ✅ Обновлены Pydantic схемы (project.py, video.py)
- ✅ Инициализирован Alembic
- ✅ Сгенерирована миграция: `12f3862d5db2_initial_schema_projects_and_videos.py`
- ✅ Применена миграция: 4 таблицы созданы

### Таблицы в БД:
```sql
projects - шаблоны проектов
videos - отдельные ролики с workflow данными
workflow_steps - этапы генерации (связаны с videos)
validation_results - результаты валидации
```

### Изменения:
- Исправлен импорт: `app.db.base_class` → `app.db.base`
- Все модели используют `from app.db.base import Base`
- Enums (StepType, WorkflowStatus, ValidationStatus) в отдельных модулях
