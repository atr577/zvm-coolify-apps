---
id: T14
title: "Устранение дублирования данных"
status: todo
priority: critical
created: 2026-01-10
updated: 2026-01-10
tags: []
depends_on: ['T11']
estimate: "2-3 дня"
branch: ""
---

# Task 14: Устранение дублирования данных

## Проблема

Данные хранятся в двух местах: Video и WorkflowStep.

**Video model:**
```python
class Video(Base):
    story_data = Column(JSON)
    description_data = Column(JSON)
    prompt_data = Column(JSON)
    image_url = Column(Text)
    scenario_data = Column(JSON)
    video_url = Column(Text)
    audio_variants = Column(JSON)
    video_with_audio_url = Column(Text)
    adaptation_data = Column(JSON)
```

**WorkflowStep model:**
```python
class WorkflowStep(Base):
    video_id = ForeignKey("videos.id")
    step_type = Column(Enum(StepType))
    content = Column(JSON)  # ТЕ ЖЕ ДАННЫЕ!
```

**Код записи:**
```python
story_data = await openai_service.generate_story(...)
step.content = story_data      # Записываем в step
video.story_data = story_data  # Записываем в video — ДУБЛИКАТ!
```

**Проблемы:**
1. Данные могут рассинхронизироваться
2. Двойной размер в БД
3. Непонятно откуда читать

## Цель

Единый источник истины — WorkflowStep.

## Решение

### Вариант A: Property-based доступ (рекомендуется)

Данные хранятся только в `WorkflowStep.content`.
`Video` модель предоставляет property для доступа.

**Преимущества:**
- Минимум изменений в API
- Обратная совместимость
- Единый источник истины

**Недостатки:**
- Дополнительные queries при доступе

### Вариант B: Полный рефакторинг

Удалить все `*_data` поля из Video.
Везде использовать `video.workflow_steps`.

**Преимущества:**
- Чистая архитектура

**Недостатки:**
- Много изменений
- Ломает существующий код

## Детальный план (Вариант A)

### Phase 1: Добавить properties в Video (2-3 часа)

**Файл:** `backend/app/models/video.py`

```python
from sqlalchemy.orm import relationship
from typing import Optional, Dict, Any

class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"))
    title = Column(String(255), nullable=False)
    workflow_mode = Column(SQLEnum(WorkflowMode), default=WorkflowMode.AUTO)
    content_variables = Column(JSON, nullable=True)
    current_step = Column(SQLEnum(StepType), default=StepType.STORY)
    status = Column(SQLEnum(WorkflowStatus), default=WorkflowStatus.PENDING)
    author_rating = Column(Integer, nullable=True)

    # Legacy fields - DEPRECATED, use properties below
    # These will be removed in future migration
    _story_data = Column("story_data", JSON, nullable=True)
    _description_data = Column("description_data", JSON, nullable=True)
    _prompt_data = Column("prompt_data", JSON, nullable=True)
    _image_url = Column("image_url", Text, nullable=True)
    _scenario_data = Column("scenario_data", JSON, nullable=True)
    _video_url = Column("video_url", Text, nullable=True)
    _video_task_id = Column("video_task_id", String(255), nullable=True)
    _audio_variants = Column("audio_variants", JSON, nullable=True)
    _video_with_audio_url = Column("video_with_audio_url", Text, nullable=True)
    _adaptation_data = Column("adaptation_data", JSON, nullable=True)

    # Relationships
    project = relationship("Project", back_populates="videos")
    workflow_steps = relationship(
        "WorkflowStep",
        back_populates="video",
        cascade="all, delete-orphan",
        lazy="selectin"  # Eager loading для избежания N+1
    )

    # ========== Properties для доступа к данным через WorkflowStep ==========

    def _get_step_content(self, step_type: StepType) -> Optional[Dict[str, Any]]:
        """Helper: получить content для step_type"""
        for step in self.workflow_steps:
            if step.step_type == step_type:
                return step.content
        return None

    def _get_step_field(self, step_type: StepType, field: str) -> Optional[Any]:
        """Helper: получить конкретное поле из content"""
        content = self._get_step_content(step_type)
        if content and isinstance(content, dict):
            return content.get(field)
        return None

    @property
    def story_data(self) -> Optional[Dict[str, Any]]:
        return self._get_step_content(StepType.STORY)

    @property
    def description_data(self) -> Optional[Dict[str, Any]]:
        return self._get_step_content(StepType.DESCRIPTION)

    @property
    def prompt_data(self) -> Optional[Dict[str, Any]]:
        return self._get_step_content(StepType.PROMPT)

    @property
    def image_url(self) -> Optional[str]:
        return self._get_step_field(StepType.IMAGE, "image_url")

    @property
    def scenario_data(self) -> Optional[Dict[str, Any]]:
        return self._get_step_content(StepType.SCENARIO)

    @property
    def video_url(self) -> Optional[str]:
        return self._get_step_field(StepType.VIDEO, "video_url")

    @property
    def video_task_id(self) -> Optional[str]:
        return self._get_step_field(StepType.VIDEO, "task_id")

    @property
    def audio_variants(self) -> Optional[list]:
        return self._get_step_field(StepType.AUDIO, "audio_variants")

    @property
    def video_with_audio_url(self) -> Optional[str]:
        # Это выбранный вариант, может храниться в AUDIO step
        content = self._get_step_content(StepType.AUDIO)
        if content:
            return content.get("selected_url")
        return None

    @property
    def adaptation_data(self) -> Optional[Dict[str, Any]]:
        return self._get_step_content(StepType.ADAPTATION)

    # ========== Методы для backward compatibility ==========

    def get_step(self, step_type: StepType) -> Optional["WorkflowStep"]:
        """Получить WorkflowStep по типу"""
        for step in self.workflow_steps:
            if step.step_type == step_type:
                return step
        return None

    def get_latest_step(self) -> Optional["WorkflowStep"]:
        """Получить последний (текущий) step"""
        return self.get_step(self.current_step)
```

### Phase 2: Обновить workflow.py (3-4 часа)

**До:**
```python
story_data = await openai_service.generate_story(...)
step.content = story_data
video.story_data = story_data  # Дублирование!
video.current_step = StepType.STORY
```

**После:**
```python
story_data = await openai_service.generate_story(...)
step.content = story_data
video.current_step = StepType.STORY
# Данные доступны через video.story_data (property)
```

**Полный пример:**

```python
@router.post("/generate-story")
async def generate_story(
    request: GenerateStoryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    video = db.query(Video).filter(Video.id == request.video_id).first()
    if not video:
        raise NotFoundError("Video")

    verify_video_ownership(db, video, current_user)
    step = get_or_create_step(db, video.id, StepType.STORY)

    try:
        story_data = await openai_service.generate_story(...)

        # Сохраняем ТОЛЬКО в step
        step.content = story_data
        video.current_step = StepType.STORY
        video.status = WorkflowStatus.IN_PROGRESS

        # Валидация
        validation = await validate_and_save(db, step, story_data, "story")

        return {
            "step_id": step.id,
            "content": story_data,  # Или video.story_data - одинаково
            "validation": {...}
        }
    except Exception as e:
        step.status = WorkflowStatus.FAILED
        db.commit()
        raise
```

### Phase 3: Обновить схемы ответов (1-2 часа)

**Файл:** `backend/app/schemas/video.py`

```python
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class VideoResponse(BaseModel):
    id: int
    title: str
    project_id: int
    workflow_mode: str
    current_step: str
    status: str

    # Данные из steps (вычисляемые)
    story_data: Optional[Dict[str, Any]] = None
    description_data: Optional[Dict[str, Any]] = None
    prompt_data: Optional[Dict[str, Any]] = None
    image_url: Optional[str] = None
    scenario_data: Optional[Dict[str, Any]] = None
    video_url: Optional[str] = None
    audio_variants: Optional[List[str]] = None
    video_with_audio_url: Optional[str] = None
    adaptation_data: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
```

### Phase 4: Миграция данных (2-3 часа)

**Файл:** `backend/alembic/versions/xxx_migrate_to_step_content.py`

```python
"""Migrate video data to workflow_steps

Revision ID: xxx
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy import text

def upgrade():
    """
    Копируем данные из Video в WorkflowStep.content
    для существующих записей
    """
    bind = op.get_bind()
    session = Session(bind=bind)

    # Получаем все videos с данными
    result = session.execute(text("""
        SELECT id, story_data, description_data, prompt_data,
               image_url, scenario_data, video_url, video_task_id,
               audio_variants, video_with_audio_url, adaptation_data
        FROM videos
        WHERE story_data IS NOT NULL
           OR image_url IS NOT NULL
           OR video_url IS NOT NULL
    """))

    step_type_map = {
        'story_data': ('story', lambda r: r.story_data),
        'description_data': ('description', lambda r: r.description_data),
        'prompt_data': ('prompt', lambda r: r.prompt_data),
        'image_url': ('image', lambda r: {'image_url': r.image_url} if r.image_url else None),
        'scenario_data': ('scenario', lambda r: r.scenario_data),
        'video_url': ('video', lambda r: {'video_url': r.video_url, 'task_id': r.video_task_id} if r.video_url else None),
        'audio_variants': ('audio', lambda r: {'audio_variants': r.audio_variants, 'selected_url': r.video_with_audio_url} if r.audio_variants else None),
        'adaptation_data': ('adaptation', lambda r: r.adaptation_data),
    }

    for row in result:
        for field, (step_type, extractor) in step_type_map.items():
            content = extractor(row)
            if content:
                # Проверяем, есть ли уже step
                existing = session.execute(text("""
                    SELECT id FROM workflow_steps
                    WHERE video_id = :video_id AND step_type = :step_type
                """), {'video_id': row.id, 'step_type': step_type}).first()

                if existing:
                    # Обновляем если content пустой
                    session.execute(text("""
                        UPDATE workflow_steps
                        SET content = :content
                        WHERE id = :id AND (content IS NULL OR content = '{}')
                    """), {'id': existing.id, 'content': content})
                else:
                    # Создаем новый step
                    session.execute(text("""
                        INSERT INTO workflow_steps
                        (video_id, step_type, status, content, created_at)
                        VALUES (:video_id, :step_type, 'completed', :content, datetime('now'))
                    """), {
                        'video_id': row.id,
                        'step_type': step_type,
                        'content': content
                    })

    session.commit()


def downgrade():
    """
    Копируем данные обратно из WorkflowStep в Video
    """
    # Обратная миграция если нужно
    pass
```

### Phase 5: Удаление legacy полей (после стабилизации)

**Файл:** `backend/alembic/versions/yyy_remove_legacy_video_fields.py`

```python
"""Remove legacy data fields from videos table

Revision ID: yyy
Depends: xxx (migrate_to_step_content)
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Удаляем legacy поля
    with op.batch_alter_table('videos') as batch_op:
        batch_op.drop_column('story_data')
        batch_op.drop_column('description_data')
        batch_op.drop_column('prompt_data')
        batch_op.drop_column('image_url')
        batch_op.drop_column('image_prompt')  # deprecated
        batch_op.drop_column('scenario_data')
        batch_op.drop_column('video_url')
        batch_op.drop_column('video_task_id')
        batch_op.drop_column('audio_variants')
        batch_op.drop_column('video_with_audio_url')
        batch_op.drop_column('adaptation_data')

def downgrade():
    # Восстанавливаем поля если нужен откат
    with op.batch_alter_table('videos') as batch_op:
        batch_op.add_column(sa.Column('story_data', sa.JSON))
        # ... остальные поля
```

## Чеклист

- [ ] Добавить properties в Video model
- [ ] Обновить relationship с `lazy="selectin"`
- [ ] Обновить workflow.py — убрать запись в video.*_data
- [ ] Обновить VideoResponse schema
- [ ] Написать тесты для properties
- [ ] Создать миграцию данных
- [ ] Протестировать миграцию на копии БД
- [ ] Выполнить миграцию
- [ ] Мониторинг на проде
- [ ] Удалить legacy поля (через 1-2 недели)

## Риски

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| N+1 queries | Средняя | `lazy="selectin"` |
| Рассинхронизация при миграции | Низкая | Тесты, проверка данных |
| Сломается API | Низкая | Properties обеспечивают совместимость |

## Метрики успеха

| Метрика | До | После |
|---------|-----|-------|
| Источников данных | 2 | 1 |
| Размер videos table | X MB | 0.7X MB |
| Риск рассинхронизации | Высокий | Нулевой |

---

**Статус:** Ожидает Task 11 (тесты)
**Ответственный:** TBD
