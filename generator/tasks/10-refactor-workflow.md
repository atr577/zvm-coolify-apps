# Task 10: Рефакторинг workflow.py

**Приоритет:** P0 (критический)
**Оценка:** 1 неделя
**Зависимости:** Task 11 (тесты) — нужны тесты перед рефакторингом

## Проблема

Файл `backend/app/api/workflow.py` содержит 1145 строк с массивным дублированием кода.

### Текущее состояние

```python
# Этот паттерн повторяется 8+ раз:
@router.post("/generate-{step}")
async def generate_{step}(request, db, current_user):
    video = db.query(Video).filter(Video.id == request.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    verify_video_ownership(db, video, current_user)
    step = get_or_create_step(db, video.id, StepType.XXX)

    try:
        xxx_data = await openai_service.generate_xxx(...)
        step.content = xxx_data
        video.xxx_data = xxx_data
        video.current_step = StepType.XXX
        validation = await validate_and_save(db, step, xxx_data, "xxx")
        return {"step_id": step.id, "content": xxx_data, "validation": {...}}
    except Exception as e:
        step.status = WorkflowStatus.FAILED
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))
```

### approve_step — 290 строк вложенных if/elif

```python
if request.approved:
    if step.step_type == StepType.VIDEO:
        # 30 строк
    elif step.step_type == StepType.ADAPTATION:
        # 15 строк
    else:
        if video.workflow_mode == WorkflowMode.MANUAL:
            if step.step_type == StepType.STORY:
                # 20 строк
            elif step.step_type == StepType.DESCRIPTION:
                # 20 строк
            # ... x8
```

## Цель

Разбить на изолированные, тестируемые компоненты.

## Целевая архитектура

```
backend/app/
├── services/
│   └── workflow/
│       ├── __init__.py
│       ├── base.py              # BaseWorkflowStep
│       ├── steps/
│       │   ├── __init__.py
│       │   ├── story.py         # StoryStep
│       │   ├── description.py   # DescriptionStep
│       │   ├── prompt.py        # PromptStep
│       │   ├── image.py         # ImageStep
│       │   ├── scenario.py      # ScenarioStep
│       │   ├── video.py         # VideoStep
│       │   ├── audio.py         # AudioStep
│       │   └── adaptation.py    # AdaptationStep
│       ├── orchestrator.py      # WorkflowOrchestrator
│       └── state_machine.py     # FSM для переходов
├── api/
│   └── workflow.py              # Тонкий слой — только HTTP handlers
```

## Детальный план

### Phase 1: BaseWorkflowStep (2-3 часа)

**Файл:** `backend/app/services/workflow/base.py`

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.video import Video, StepType, WorkflowStatus
from app.models.workflow_step import WorkflowStep

class BaseWorkflowStep(ABC):
    """Базовый класс для всех workflow steps"""

    step_type: StepType  # Переопределяется в наследниках

    def __init__(self, db: Session, video: Video):
        self.db = db
        self.video = video
        self.step: Optional[WorkflowStep] = None

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Основной метод выполнения шага"""
        self.step = self._get_or_create_step()

        try:
            # 1. Генерация контента
            content = await self.generate(**kwargs)

            # 2. Сохранение
            self._save_content(content)

            # 3. Валидация (если нужна)
            validation = None
            if self.requires_validation:
                validation = await self._validate(content, kwargs.get('previous_data'))
            else:
                self.step.status = WorkflowStatus.AWAITING_APPROVAL

            self.db.commit()

            return {
                "step_id": self.step.id,
                "content": content,
                "validation": validation
            }

        except Exception as e:
            self._handle_failure(e)
            raise

    @abstractmethod
    async def generate(self, **kwargs) -> Dict[str, Any]:
        """Генерация контента — реализуется в наследниках"""
        pass

    @property
    def requires_validation(self) -> bool:
        """Нужна ли AI-валидация для этого шага"""
        return True

    @property
    @abstractmethod
    def content_field(self) -> str:
        """Имя поля в Video для сохранения контента"""
        pass

    def _get_or_create_step(self) -> WorkflowStep:
        # Существующая логика get_or_create_step
        pass

    def _save_content(self, content: Dict[str, Any]):
        self.step.content = content
        setattr(self.video, self.content_field, content)
        self.video.current_step = self.step_type

    async def _validate(self, content: Dict, previous_data: Dict = None):
        # Существующая логика validate_and_save
        pass

    def _handle_failure(self, error: Exception):
        self.step.status = WorkflowStatus.FAILED
        self.step.completed_at = datetime.utcnow()
        self.db.commit()
```

### Phase 2: Конкретные Step классы (3-4 часа)

**Файл:** `backend/app/services/workflow/steps/story.py`

```python
from app.services.workflow.base import BaseWorkflowStep
from app.models.video import StepType
from app.services.openai_service import openai_service

class StoryStep(BaseWorkflowStep):
    step_type = StepType.STORY
    content_field = "story_data"

    async def generate(
        self,
        theme: str = None,
        target_audience: str = None,
        mood: str = None,
        key_elements: str = None,
        duration: int = 5,
        platforms: list = None,
        additional_notes: str = None,
        content_variables: dict = None,
        **kwargs
    ) -> dict:
        return await openai_service.generate_story(
            theme=theme,
            target_audience=target_audience,
            mood=mood,
            key_elements=key_elements,
            duration=duration,
            platforms=platforms,
            additional_notes=additional_notes,
            content_variables=content_variables or self.video.content_variables
        )
```

**Файл:** `backend/app/services/workflow/steps/image.py`

```python
class ImageStep(BaseWorkflowStep):
    step_type = StepType.IMAGE
    content_field = "image_url"
    requires_validation = False  # Изображения не валидируем AI

    async def generate(self, prompt: str = None, prompt_data: dict = None, **kwargs) -> dict:
        # Определяем промпт
        prompt_str = prompt
        if prompt_data and not prompt_str:
            prompt_str = prompt_data.get("main_prompt", "")

        image_url = await kling_service.generate_image(
            prompt=prompt_str,
            aspect_ratio=self.video.project.aspect_ratio,
            negative_prompt=prompt_data.get("negative_prompt") if prompt_data else None
        )

        return {"image_url": image_url}

    def _save_content(self, content: dict):
        self.step.content = content
        self.video.image_url = content["image_url"]
        self.video.current_step = self.step_type
```

### Phase 3: State Machine (2-3 часа)

**Файл:** `backend/app/services/workflow/state_machine.py`

```python
from enum import Enum
from typing import Dict, Set
from app.models.video import WorkflowStatus

class InvalidTransitionError(Exception):
    pass

VALID_TRANSITIONS: Dict[WorkflowStatus, Set[WorkflowStatus]] = {
    WorkflowStatus.PENDING: {WorkflowStatus.IN_PROGRESS},
    WorkflowStatus.IN_PROGRESS: {WorkflowStatus.VALIDATING, WorkflowStatus.AWAITING_APPROVAL, WorkflowStatus.FAILED},
    WorkflowStatus.VALIDATING: {WorkflowStatus.AWAITING_APPROVAL, WorkflowStatus.VALIDATION_FAILED, WorkflowStatus.IN_PROGRESS},
    WorkflowStatus.VALIDATION_FAILED: {WorkflowStatus.PENDING, WorkflowStatus.IN_PROGRESS},
    WorkflowStatus.AWAITING_APPROVAL: {WorkflowStatus.APPROVED, WorkflowStatus.REJECTED},
    WorkflowStatus.APPROVED: {WorkflowStatus.COMPLETED},
    WorkflowStatus.REJECTED: {WorkflowStatus.PENDING},
    WorkflowStatus.COMPLETED: set(),  # Терминальное состояние
    WorkflowStatus.FAILED: {WorkflowStatus.PENDING},
}

def validate_transition(current: WorkflowStatus, new: WorkflowStatus) -> bool:
    """Проверяет валидность перехода"""
    return new in VALID_TRANSITIONS.get(current, set())

def transition_to(step: "WorkflowStep", new_status: WorkflowStatus):
    """Безопасный переход в новое состояние"""
    if not validate_transition(step.status, new_status):
        raise InvalidTransitionError(
            f"Cannot transition from {step.status.value} to {new_status.value}"
        )
    step.status = new_status
```

### Phase 4: Orchestrator (3-4 часа)

**Файл:** `backend/app/services/workflow/orchestrator.py`

```python
from typing import Dict, Type
from app.services.workflow.base import BaseWorkflowStep
from app.services.workflow.steps import *
from app.models.video import StepType

STEP_CLASSES: Dict[StepType, Type[BaseWorkflowStep]] = {
    StepType.STORY: StoryStep,
    StepType.DESCRIPTION: DescriptionStep,
    StepType.PROMPT: PromptStep,
    StepType.IMAGE: ImageStep,
    StepType.SCENARIO: ScenarioStep,
    StepType.VIDEO: VideoStep,
    StepType.AUDIO: AudioStep,
    StepType.ADAPTATION: AdaptationStep,
}

STEP_ORDER = [
    StepType.STORY,
    StepType.DESCRIPTION,
    StepType.PROMPT,
    StepType.IMAGE,
    StepType.SCENARIO,
    StepType.VIDEO,
    StepType.AUDIO,
    StepType.ADAPTATION,
]

class WorkflowOrchestrator:
    """Управляет выполнением workflow"""

    def __init__(self, db: Session, video: Video):
        self.db = db
        self.video = video

    async def execute_step(self, step_type: StepType, **kwargs) -> dict:
        """Выполняет конкретный шаг"""
        step_class = STEP_CLASSES[step_type]
        step = step_class(self.db, self.video)
        return await step.execute(**kwargs)

    async def approve_step(self, step_id: int, approved: bool, feedback: str = None) -> dict:
        """Одобряет/отклоняет шаг"""
        step = self.db.query(WorkflowStep).get(step_id)

        if approved:
            transition_to(step, WorkflowStatus.APPROVED)
            step.user_approved = True
            step.completed_at = datetime.utcnow()

            # Автоматически запускаем следующий шаг
            next_step_type = self._get_next_step(step.step_type)
            if next_step_type and self.video.workflow_mode == WorkflowMode.MANUAL:
                await self.execute_step(next_step_type)
        else:
            transition_to(step, WorkflowStatus.REJECTED)
            step.user_feedback = feedback

        self.db.commit()
        return {"step_id": step.id, "status": step.status.value}

    async def auto_generate(self) -> dict:
        """Автогенерация всех шагов до AUDIO"""
        results = []
        for step_type in STEP_ORDER:
            if step_type == StepType.AUDIO:
                break  # Останавливаемся перед audio для выбора варианта
            result = await self.execute_step(step_type)
            results.append(result)
        return {"steps": results}

    def _get_next_step(self, current: StepType) -> StepType | None:
        idx = STEP_ORDER.index(current)
        if idx + 1 < len(STEP_ORDER):
            return STEP_ORDER[idx + 1]
        return None
```

### Phase 5: Тонкий API слой (2 часа)

**Файл:** `backend/app/api/workflow.py` (новый, ~100 строк)

```python
from fastapi import APIRouter, Depends, HTTPException
from app.services.workflow.orchestrator import WorkflowOrchestrator
from app.core.deps import get_db, get_current_user

router = APIRouter()

@router.post("/generate-story")
async def generate_story(
    request: GenerateStoryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    video = get_video_or_404(db, request.video_id)
    verify_video_ownership(db, video, current_user)

    orchestrator = WorkflowOrchestrator(db, video)
    return await orchestrator.execute_step(
        StepType.STORY,
        theme=request.theme,
        target_audience=request.target_audience,
        mood=request.mood,
        key_elements=request.key_elements,
        duration=request.duration,
        platforms=request.platforms,
        additional_notes=request.additional_notes,
        content_variables=request.content_variables
    )

# Аналогично для остальных endpoints — каждый ~10 строк
```

## Чеклист

- [ ] Написать тесты для текущего workflow (Task 11)
- [ ] Создать `BaseWorkflowStep`
- [ ] Реализовать все Step классы
- [ ] Реализовать State Machine
- [ ] Реализовать Orchestrator
- [ ] Переписать API endpoints
- [ ] Прогнать тесты
- [ ] Удалить старый workflow.py

## Метрики успеха

| Метрика | До | После |
|---------|-----|-------|
| Строк в workflow.py | 1145 | ~100 |
| Дублирование | 8x | 0 |
| Тестовое покрытие | 0% | 80%+ |
| Cyclomatic complexity | Высокая | Низкая |

## Риски

1. **Регрессии** — митигация: сначала тесты (Task 11)
2. **Время** — митигация: инкрементальный рефакторинг
3. **Сложность** — митигация: code review на каждом этапе

---

**Статус:** Ожидает Task 11 (тесты)
**Ответственный:** TBD
