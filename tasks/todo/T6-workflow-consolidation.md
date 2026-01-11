# T6: Workflow Consolidation - Полный рефакторинг

**Status:** todo
**Priority:** P0
**Created:** 2026-01-11
**Updated:** 2026-01-11
**Estimate:** 2-3 дня
**Type:** Epic (зонтичная задача)

## Подзадачи

| # | Задача | Estimate | Depends on | Status |
|---|--------|----------|------------|--------|
| T6.1 | [DB Migration](T6.1-db-migration.md) | 2ч | — | todo |
| T6.2 | [Backend Services](T6.2-backend-services.md) | 4ч | T6.1 | todo |
| T6.3 | [Backend API](T6.3-backend-api.md) | 3ч | T6.2 | todo |
| T6.4 | [Frontend](T6.4-frontend.md) | 4ч | T6.3 | todo |

```
T6.1 (БД) → T6.2 (Services) → T6.3 (API) → T6.4 (Frontend)
   2ч           4ч               3ч            4ч
```

**Каждая подзадача:**
- Отдельный коммит
- Тестируется независимо
- Можно откатить отдельно

---

## Проблема

1. Три дублирующих API: workflow.py, workflow_v2.py, workflow_v3.py
2. Два orchestrator: orchestrator.py, orchestrator_v2.py
3. Две модели данных: WorkflowStep (3 таблицы) vs StepHistory (1 таблица)
4. 7-шаговый flow устарел, нужен 4-шаговый
5. Discover и Remix имели разное количество шагов

## Цель

**Унифицированный workflow с 4 шагами для ОБОИХ типов проектов:**

```
SCENARIO → IMAGE → VIDEO → AUDIO
```

Отличие только в логике SCENARIO step:
- **Discover:** LLM генерирует креативно (много свободы)
- **Remix:** LLM заполняет переменные в шаблоне (мало свободы)

## Целевая архитектура

```
Frontend (api.ts)
       │
       ▼
app/api/workflow.py (единственный)
       │
       ▼
app/services/workflow/orchestrator.py (функции)
       │
       ├── strategies/
       │   ├── base.py (BaseStrategy + dispatch)
       │   ├── discover.py (DiscoverStrategy)
       │   └── remix.py (RemixStrategy)
       │
       └── steps/
           ├── image.py (generate)
           ├── video.py (generate)
           └── audio.py (generate)
       │
       ▼
app/models/step_history.py (StepHistory)
       │
       ▼
Discover: SCENARIO → IMAGE → VIDEO → [AUDIO]
Remix:    SCENARIO → IMAGE → VIDEO → [AUDIO]
          └── отличие только в логике SCENARIO (через Strategy)
```

---

## Подготовка

### Удалить T1-T4

T6 заменяет задачи T1-T4 (они написаны под старую архитектуру):

- [ ] Удалить `tasks/todo/T1-discover-auto-flow.md`
- [ ] Удалить `tasks/todo/T2-discover-manual-flow.md`
- [ ] Удалить `tasks/todo/T3-remix-auto-flow.md`
- [ ] Удалить `tasks/todo/T4-remix-manual-flow.md`

### T5 (Local Media) — отдельная задача

После T6: интегрировать `download_media()` в новый orchestrator.

```python
# orchestrator.py — после генерации
result = await strategy.generate(step, video, video.project)

# Скачать медиа локально (T5)
if step in ['image', 'video', 'audio']:
    await download_media(result['url'], video.id, step)
```

---

## Принятые решения

| # | Вопрос | Решение |
|---|--------|---------|
| 1 | Модели WorkflowStep/StepAttempt/Variant | Удалить полностью |
| 2 | Застрявшие видео | Удалить (6 видео: 4, 5, 8, 9, 10, 11) |
| 3 | Варианты для MANUAL | image: 3, остальные: 1 |
| 4 | Audio варианты | 1 вариант |
| 5 | Scope рефакторинга | Полный (services/workflow/) |

### Конфиг вариантов (MANUAL mode)

```python
# В orchestrator.py
DEFAULT_VARIANTS = {
    'scenario': 1,
    'image': 3,
    'video': 1,
    'audio': 1,
}
# AUTO mode всегда 1 вариант
```

---

## Архитектурные решения

### StepHistory: расширенная модель

```python
class StepHistory:
    id: int
    video_id: int
    step_type: str  # scenario, image, video, audio

    # Content
    content: JSON
    is_selected: bool = False

    # Status tracking
    status: str = "pending"  # pending, success, failed
    error_message: str | None = None

    # Metrics
    generation_time_seconds: float | None = None

    # Lineage (для regenerate с feedback)
    parent_id: int | None = None  # FK → StepHistory (от какого варианта сгенерирован)
    feedback: str | None = None   # feedback при regenerate

    created_at: datetime
```

### История вариантов: выбор из любого

**Принцип:** Храним ВСЕ сгенерированные варианты. User может выбрать любой из истории.

**Сценарий:**
```
Round 1: IMAGE_1 → VIDEO_1 (не нравится)
Round 2: IMAGE_2 → VIDEO_2 (не нравится)
Round 3: IMAGE_3 → VIDEO_3 (не нравится)
Round 4: IMAGE_4 → VIDEO_4 (не нравится)
→ User выбирает IMAGE_2 → генерирует VIDEO_5 от него
→ Или выбирает VIDEO_2 напрямую
```

**Lineage через parent_id:**
```
SCENARIO_1 ← selected
    └── IMAGE_1
    └── IMAGE_2 ← selected
            └── VIDEO_1
            └── VIDEO_2 ← selected
            └── VIDEO_3
            └── VIDEO_4
                    └── AUDIO_1 ← selected
```

**Логика выбора:**
1. `GET /workflow/{video_id}/history/{step}` — все варианты для шага
2. UI показывает галерею всех вариантов
3. User выбирает любой → `POST /workflow/{video_id}/select/{variant_id}`
4. Снимаем `is_selected` со всех вариантов этого step_type
5. Ставим `is_selected = True` на выбранный
6. `Video.current_step` = следующий шаг (или текущий, если хочет regenerate)

**Не нужен rollback endpoint** — просто выбор из истории.

### SCENARIO step: разная логика

**Discover:** Structured output с thinking
```python
async def generate_scenario_discover(video, project):
    response = await llm.generate_json(
        schema={
            "thinking": {
                "concept": str,
                "visual_description": str,
            },
            "scenario_data": {
                "prompt": str,
                "negative_prompt": str,
                "camera_movement": str,
                "subject_motion": str,
                ...
            }
        }
    )
    # Сохраняем всё в content (и thinking, и scenario_data)
    return response
```

**Remix:** Простой call, заполнение шаблона
```python
async def generate_scenario_remix(video, project):
    # LLM выбирает значения для {переменных}
    variables = await llm.generate_json(
        prompt=f"Выбери значения для: {project.placeholders}",
        suggestions=project.placeholder_suggestions
    )
    # Заполняем шаблон
    scenario_data = fill_template(project.story_template, variables)
    return scenario_data
```

### Retry policy

```python
RETRY_CONFIG = {
    'max_retries': 3,
    'backoff': 'exponential',  # 1s, 2s, 4s
    'retry_on': ['timeout', 'rate_limit', '5xx'],
}

# После исчерпания retry:
# Video.status = FAILED
# StepHistory.status = "failed"
# StepHistory.error_message = "API timeout after 3 retries"
# User видит кнопку [Retry] → новый attempt
```

### Дополнительные решения

| # | Вопрос | Решение |
|---|--------|---------|
| 1 | Миграция данных | Удалить ВСЕ видео (чистый старт) |
| 2 | Polling для генерации | Polling (GET каждые N сек), позже можно SSE |
| 3 | React Query cache | setQueryData + invalidate в background |
| 4 | Error states в UI | Failed + error message + Retry + Auto-retry (3 попытки) |
| 5 | Concurrent requests | UI disable + Backend lock (reject if IN_PROGRESS) |
| 6 | API breaking changes | Нет внешних клиентов → удаляем без версионирования |
| 7 | Логирование | Dev: DEBUG (full payloads), Prod: INFO (start/end/timing) |

### React Query: инвалидация кеша

```typescript
// После mutation (select, generate)
onSuccess: (response) => {
  // 1. Мгновенно обновить UI
  queryClient.setQueryData(['video', videoId], response.data)

  // 2. В фоне перезапросить для консистентности
  queryClient.invalidateQueries(['video', videoId])
}
```

### Concurrent protection

```python
# Backend: reject if already in progress
async def generate_step(video_id: int, step: str):
    video = get_video(video_id)
    if video.status == WorkflowStatus.IN_PROGRESS:
        raise HTTPException(409, "Generation already in progress")

    video.status = WorkflowStatus.IN_PROGRESS
    db.commit()
    # ... generate
```

```typescript
// Frontend: disable button
<Button
  disabled={isGenerating}
  onClick={generate}
>
  {isGenerating ? 'Generating...' : 'Generate'}
</Button>
```

### Логирование

```python
# config.py
LOG_LEVEL: str = "DEBUG"  # dev: DEBUG, prod: INFO

# workflow/orchestrator.py
logger.info(f"Step {step} started for video {video_id}")
logger.info(f"Step {step} completed in {time:.1f}s, StepHistory.id={sh.id}")
logger.error(f"Step {step} failed: {error}")

if settings.LOG_LEVEL == "DEBUG":
    logger.debug(f"Request: {payload}")
    logger.debug(f"Response: {response}")
```

---

## Фаза 1: Подготовка БД

### 1.1 Расширить StepHistory

```sql
-- Добавить новые поля в step_history
ALTER TABLE step_history ADD COLUMN status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE step_history ADD COLUMN error_message TEXT;
ALTER TABLE step_history ADD COLUMN generation_time_seconds FLOAT;
ALTER TABLE step_history ADD COLUMN parent_id INTEGER REFERENCES step_history(id);
ALTER TABLE step_history ADD COLUMN feedback TEXT;
```

- [ ] Создать alembic миграцию для расширения StepHistory

### 1.2 Удалить ВСЕ видео (чистый старт)

```sql
-- Удалить ВСЕ видео и связанные данные
DELETE FROM step_history;
DELETE FROM video_metrics;
DELETE FROM publish_results;
DELETE FROM validation_results;
DELETE FROM variants;
DELETE FROM step_attempts;
DELETE FROM workflow_steps;
DELETE FROM videos;

-- Удалить старые таблицы
DROP TABLE IF EXISTS variants;
DROP TABLE IF EXISTS step_attempts;
DROP TABLE IF EXISTS validation_results;
DROP TABLE IF EXISTS workflow_steps;
```

- [ ] Создать alembic миграцию для удаления старых таблиц

### 1.3 Удалить модели

- [ ] Удалить `app/models/workflow_step.py`
- [ ] Удалить `app/models/step_attempt.py`
- [ ] Удалить `app/models/validation_result.py`

### 1.4 Обновить models/__init__.py

```python
# Удалить:
from app.models.workflow_step import WorkflowStep
from app.models.step_attempt import StepAttempt, Variant, AttemptStatus
from app.models.validation_result import ValidationResult

# Удалить из __all__:
"WorkflowStep", "StepAttempt", "Variant", "AttemptStatus", "ValidationResult"
```

### 1.5 Обновить Video модель

```python
# Удалить из app/models/video.py:
workflow_steps = relationship("WorkflowStep", ...)
```

---

## Фаза 2: Рефакторинг services/workflow/

### 2.1 Удалить файлы

- [ ] Удалить `app/services/workflow/orchestrator.py` (v1)
- [ ] Удалить `app/services/workflow/orchestrator_v2.py`
- [ ] Удалить `app/services/workflow/base.py` (BaseWorkflowStep)
- [ ] Удалить `app/services/workflow/approval.py`

### 2.2 Удалить старые step файлы

- [ ] Удалить `app/services/workflow/steps/story.py`
- [ ] Удалить `app/services/workflow/steps/description.py`
- [ ] Удалить `app/services/workflow/steps/prompt.py`
- [ ] Удалить `app/services/workflow/steps/adaptation.py`

### 2.3 Удалить старые prompt файлы

- [ ] Удалить `app/services/prompts/story.py`
- [ ] Удалить `app/services/prompts/description.py`
- [ ] Удалить `app/services/prompts/adaptation.py`
- [ ] Проверить `app/services/prompts/variants.py` — нужен ли?

### 2.4 Обновить steps/__init__.py

```python
# Было:
from app.services.workflow.steps.story import StoryStep
from app.services.workflow.steps.description import DescriptionStep
from app.services.workflow.steps.prompt import PromptStep
from app.services.workflow.steps.scenario import ScenarioStep
from app.services.workflow.steps.adaptation import AdaptationStep
...

# Станет:
from app.services.workflow.steps.scenario import ScenarioStep
from app.services.workflow.steps.image import ImageStep
from app.services.workflow.steps.video import VideoStep
from app.services.workflow.steps.audio import AudioStep
```

- [ ] Убрать StoryStep, DescriptionStep, PromptStep, AdaptationStep

### 2.5 Удалить feature flag из config.py

```python
# Удалить из app/core/config.py:
USE_VARIANT_MODEL: bool = False  # Feature flag: use StepAttempt/Variant hierarchy
```

- [ ] Удалить USE_VARIANT_MODEL из Settings
- [ ] Добавить LOG_LEVEL в Settings (default: "INFO")

### 2.6 Удалить scenario.py из steps/

Логика SCENARIO теперь в `strategies/discover.py` и `strategies/remix.py`.

- [ ] Удалить `app/services/workflow/steps/scenario.py`

### 2.7 Создать strategies/

**Структура:**
```
app/services/workflow/
├── orchestrator.py
├── strategies/
│   ├── __init__.py
│   ├── base.py
│   ├── discover.py
│   └── remix.py
└── steps/
    ├── image.py
    ├── video.py
    └── audio.py
```

**app/services/workflow/strategies/base.py:**
```python
from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    """Base strategy for project types."""

    # Dispatcher - вызывается из orchestrator
    async def generate(self, step: str, video, project) -> dict:
        """Dispatch to step-specific method."""
        method = getattr(self, f"generate_{step}")
        return await method(video, project)

    # Обязательный - переопределяют все
    @abstractmethod
    async def generate_scenario(self, video, project) -> dict:
        raise NotImplementedError

    # Опциональные - есть default, можно переопределить
    async def generate_image(self, video, project) -> dict:
        from app.services.workflow.steps import image
        return await image.generate(video)

    async def generate_video(self, video, project) -> dict:
        from app.services.workflow.steps import video as video_step
        return await video_step.generate(video)

    async def generate_audio(self, video, project) -> dict:
        from app.services.workflow.steps import audio
        return await audio.generate(video)
```

**app/services/workflow/strategies/discover.py:**
```python
from .base import BaseStrategy

class DiscoverStrategy(BaseStrategy):
    """Discover: LLM креативит с нуля."""

    async def generate_scenario(self, video, project) -> dict:
        # Structured output с thinking
        response = await llm.generate_json(
            schema={
                "thinking": {"concept": str, "visual_description": str},
                "scenario_data": {"prompt": str, "negative_prompt": str, ...}
            }
        )
        return response
```

**app/services/workflow/strategies/remix.py:**
```python
from .base import BaseStrategy

class RemixStrategy(BaseStrategy):
    """Remix: LLM заполняет {переменные} в шаблоне."""

    async def generate_scenario(self, video, project) -> dict:
        # Выбор значений для переменных
        variables = await llm.generate_json(
            prompt=f"Выбери значения для: {project.placeholders}",
            suggestions=project.placeholder_suggestions
        )
        scenario_data = fill_template(project.story_template, variables)
        return {"variables": variables, "scenario_data": scenario_data}
```

**app/services/workflow/strategies/__init__.py:**
```python
from .discover import DiscoverStrategy
from .remix import RemixStrategy

STRATEGIES = {
    'discover': DiscoverStrategy(),
    'remix': RemixStrategy(),
}

def get_strategy(project_type: str) -> BaseStrategy:
    return STRATEGIES.get(project_type, DiscoverStrategy())
```

- [ ] Создать `strategies/base.py`
- [ ] Создать `strategies/discover.py`
- [ ] Создать `strategies/remix.py`
- [ ] Создать `strategies/__init__.py`

### 2.8 Создать новый orchestrator

**app/services/workflow/orchestrator.py:**
```python
from app.services.workflow.strategies import get_strategy

# Шаги workflow
WORKFLOW_STEPS = ['scenario', 'image', 'video', 'audio']

# Количество вариантов по умолчанию (MANUAL mode)
DEFAULT_VARIANTS = {
    'scenario': 1,
    'image': 3,
    'video': 1,
    'audio': 1,
}

async def run_auto(video_id: int) -> dict:
    """AUTO mode: все шаги без пауз."""
    video = get_video(video_id)
    steps = get_steps_for_project(video.project)

    for step in steps:
        await generate_step(video_id, step)

    video.status = WorkflowStatus.COMPLETED
    db.commit()
    return {"status": "completed"}

async def generate_step(video_id: int, step: str, feedback: str = None) -> dict:
    """Генерация шага с concurrent protection."""
    video = get_video(video_id)
    strategy = get_strategy(video.project.project_type)

    # Concurrent protection
    if video.status == WorkflowStatus.IN_PROGRESS:
        raise HTTPException(409, "Generation already in progress")

    video.status = WorkflowStatus.IN_PROGRESS
    db.commit()

    try:
        start = time.time()
        logger.info(f"Step {step} started for video {video_id}")

        # Количество вариантов
        count = 1 if video.workflow_mode == 'AUTO' else DEFAULT_VARIANTS.get(step, 1)

        # Генерация
        variants = []
        for _ in range(count):
            content = await strategy.generate(step, video, video.project)
            sh = StepHistory(video_id=video.id, step_type=step, content=content)
            db.add(sh)
            variants.append(sh)

        elapsed = time.time() - start
        logger.info(f"Step {step} completed in {elapsed:.1f}s")

        # AUTO: auto-select первый, продолжить
        if video.workflow_mode == 'AUTO':
            variants[0].is_selected = True
            video.current_step = get_next_step(step, video.project)
        else:
            # MANUAL: пауза
            video.status = WorkflowStatus.AWAITING_APPROVAL

        db.commit()
        return {"variants": variants, "status": video.status}

    except Exception as e:
        logger.error(f"Step {step} failed: {e}")
        video.status = WorkflowStatus.FAILED
        db.commit()
        raise

async def select_variant(video_id: int, variant_id: int) -> dict:
    """Выбрать вариант и продолжить к следующему шагу."""
    video = get_video(video_id)

    # Снять выбор со всех вариантов этого шага
    step_type = get_variant(variant_id).step_type
    for sh in video.step_history:
        if sh.step_type == step_type:
            sh.is_selected = False

    # Выбрать новый
    variant = get_variant(variant_id)
    variant.is_selected = True

    # Автоматически продолжить к следующему шагу
    next_step = get_next_step(step_type, video.project)
    if next_step:
        video.current_step = next_step
        db.commit()
        return await generate_step(video_id, next_step)
    else:
        # Последний шаг — завершаем
        video.status = WorkflowStatus.COMPLETED
        db.commit()
        return {"status": "completed"}

def get_steps_for_project(project) -> list:
    """4 шага для всех типов, audio опционален."""
    steps = ['scenario', 'image', 'video']
    if project.audio_mode != 'none':
        steps.append('audio')
    return steps

def get_next_step(current: str, project) -> str | None:
    """Следующий шаг или None если последний."""
    steps = get_steps_for_project(project)
    idx = steps.index(current)
    return steps[idx + 1] if idx + 1 < len(steps) else None
```

- [ ] Создать `orchestrator.py` с функциями
- [ ] `run_auto()` — AUTO mode
- [ ] `generate_step()` — генерация с variants
- [ ] `select_variant()` — выбор + auto-continue
- [ ] Concurrent protection
- [ ] Logging

### 2.9 Обновить steps/ (убрать наследование)

**app/services/workflow/steps/image.py:**
```python
# Убрать класс, оставить функцию
async def generate(video) -> dict:
    """Generate image using KLING."""
    scenario = get_selected_scenario(video)
    result = await kling.generate_image(scenario['prompt'])
    return {"image_url": result.url}
```

**app/services/workflow/steps/video.py:**
```python
async def generate(video) -> dict:
    """Generate video from image using KLING."""
    image = get_selected_image(video)
    result = await kling.generate_video(image['image_url'])
    return {"video_url": result.url}
```

**app/services/workflow/steps/audio.py:**
```python
async def generate(video) -> dict:
    """Add audio to video using KLING."""
    video_url = get_selected_video(video)
    result = await kling.add_audio(video_url)
    return {"video_with_audio_url": result.url}
```

- [ ] Переписать `image.py` как функцию
- [ ] Переписать `video.py` как функцию
- [ ] Переписать `audio.py` как функцию

### 2.10 Обновить __init__.py

```python
# app/services/workflow/__init__.py
from app.services.workflow import orchestrator
from app.services.workflow.strategies import get_strategy

__all__ = ["orchestrator", "get_strategy"]
```

---

## Фаза 3: Рефакторинг API

### 3.1 Удалить дубликаты

- [ ] Удалить `app/api/workflow_v2.py`
- [ ] Удалить `app/api/workflow_v3.py`

### 3.2 Обновить main.py

```python
# Удалить:
from app.api import workflow_v2, workflow_v3
app.include_router(workflow_v2.router, ...)
app.include_router(workflow_v3.router, ...)
```

### 3.3 Переписать workflow.py

**Удалить endpoints:**
- [ ] POST /generate-story
- [ ] POST /generate-description
- [ ] POST /generate-prompt
- [ ] POST /auto-generate-to-video
- [ ] POST /approve-step
- [ ] POST /{video_id}/{step_type}/approve-and-continue

**Добавить endpoints:**
- [ ] POST /{video_id}/run — запустить AUTO
- [ ] POST /{video_id}/generate/{step} — сгенерировать шаг (с optional feedback)
- [ ] GET /{video_id}/history/{step} — ВСЕ варианты для шага (из всей истории)
- [ ] POST /{video_id}/select/{variant_id} — выбрать любой вариант из истории

**Оставить endpoints:**
- [ ] POST /preview-prompt
- [ ] POST /generate-scenario (переименовать логику)
- [ ] POST /generate-image
- [ ] POST /generate-video
- [ ] POST /generate-audio
- [ ] POST /select-audio-variant
- [ ] POST /generate-meta
- [ ] PATCH /update-meta

### 3.4 Обновить schemas

**app/schemas/video.py:**
- [ ] Удалить WorkflowStepResponse
- [ ] Удалить workflow_steps из VideoResponse

**app/schemas/workflow.py:**
- [ ] Обновить StepTypeEnum: оставить только `SCENARIO`, `IMAGE`, `VIDEO`, `AUDIO`
- [ ] Удалить GenerateStoryRequest, GenerateDescriptionRequest, GeneratePromptRequest
- [ ] Удалить AdaptForPlatformsRequest

**app/schemas/__init__.py:**
- [ ] Убрать WorkflowStepResponse из экспорта
- [ ] Убрать старые Request schemas

---

## Фаза 4: Frontend

### 4.1 api.ts

```typescript
// Удалить:
startWorkflow, approveStepV2, rejectStep, retryStep, rollbackToStep

// Добавить/изменить:
runWorkflow: (videoId) => api.post(`/api/workflow/${videoId}/run`)
generateStep: (videoId, step, feedback?) => api.post(`/api/workflow/${videoId}/generate/${step}`, { feedback })
getHistory: (videoId, step) => api.get(`/api/workflow/${videoId}/history/${step}`)  // ВСЕ варианты
selectVariant: (videoId, variantId) => api.post(`/api/workflow/${videoId}/select/${variantId}`)
```

- [ ] Обновить workflowApi

### 4.2 useVideoWorkflow.ts

- [ ] Заменить startWorkflow на runWorkflow
- [ ] Обновить mutations
- [ ] Удалить approve/reject логику
- [ ] Добавить React Query cache invalidation:

```typescript
const generateMutation = useMutation({
  mutationFn: (step) => workflowApi.generateStep(videoId, step),
  onSuccess: (response) => {
    // Мгновенно обновить UI
    queryClient.setQueryData(['video', videoId], response.data)
    // В фоне перезапросить для консистентности
    queryClient.invalidateQueries(['video', videoId])
  }
})

const selectMutation = useMutation({
  mutationFn: (variantId) => workflowApi.selectVariant(videoId, variantId),
  onSuccess: (response) => {
    queryClient.setQueryData(['video', videoId], response.data)
    queryClient.invalidateQueries(['video', videoId])
  }
})
```

- [ ] Добавить polling для генерации:

```typescript
const { data: video } = useQuery({
  queryKey: ['video', videoId],
  queryFn: () => videoApi.getById(videoId),
  refetchInterval: video?.status === 'in_progress' ? 3000 : false  // 3 сек если генерится
})
```

### 4.3 InProgressView.tsx

```typescript
// Унифицированные шаги для ВСЕХ типов проектов
const WORKFLOW_STEPS = ['scenario', 'image', 'video', 'audio']

// audio фильтруется если audio_mode === 'none'
const getStepsForProject = (project) => {
  return project.audio_mode === 'none'
    ? WORKFLOW_STEPS.filter(s => s !== 'audio')
    : WORKFLOW_STEPS
}
```

- [ ] Удалить DISCOVER_STEPS и REMIX_STEPS
- [ ] Использовать единый WORKFLOW_STEPS
- [ ] Обновить AutoProgressView
- [ ] Добавить UI для error states + auto-retry:

```typescript
// FailedStepCard
function FailedStepCard({ step, error, onRetry, retryCount }) {
  const [autoRetrying, setAutoRetrying] = useState(retryCount < 3)

  useEffect(() => {
    if (autoRetrying && retryCount < 3) {
      const timer = setTimeout(() => onRetry(), 2000)  // auto-retry через 2 сек
      return () => clearTimeout(timer)
    }
  }, [autoRetrying, retryCount])

  return (
    <div className="bg-red-50 p-4 rounded">
      <p className="text-red-700">Failed: {error}</p>
      <p className="text-sm text-gray-500">Attempt {retryCount}/3</p>
      {retryCount < 3 ? (
        <p>Auto-retrying...</p>
      ) : (
        <Button onClick={onRetry}>Retry manually</Button>
      )}
    </div>
  )
}
```

- [ ] Disable кнопки во время генерации:

```typescript
<Button
  disabled={generateMutation.isPending}
  onClick={() => generateMutation.mutate(step)}
>
  {generateMutation.isPending ? 'Generating...' : 'Generate'}
</Button>
```

### 4.4 Обновить types

**src/types/index.ts:**
- [ ] Обновить StepType: оставить только `scenario`, `image`, `video`, `audio`
- [ ] Удалить interface WorkflowStep
- [ ] Удалить interface StepAttempt
- [ ] Удалить interface Variant
- [ ] Удалить interface WorkflowStepWithVariants
- [ ] Удалить StoryData, DescriptionData, PromptResponseData (deprecated)
- [ ] Обновить SystemPrompts: убрать story, description, prompt, adaptation

### 4.5 Удалить дубликаты hooks

- [ ] Удалить `src/hooks/useWorkflowV3.ts`

### 4.6 Галерея вариантов (новый компонент)

**src/components/workflow/VariantGallery.tsx:**
```tsx
// Показывает ВСЕ варианты для шага из истории
// User может выбрать любой вариант

interface Props {
  videoId: number
  step: StepType
  variants: StepHistory[]
  selectedId: number | null
  onSelect: (variantId: number) => void
}

// UI:
// ┌─────────────────────────────────┐
// │ IMAGE (4 варианта)              │
// │ ┌───┐ ┌───┐ ┌───┐ ┌───┐        │
// │ │ 1 │ │ 2 │ │ 3 │ │ 4 │        │
// │ └───┘ └─✓─┘ └───┘ └───┘        │
// │         ↑ selected              │
// │ [Regenerate with feedback]      │
// └─────────────────────────────────┘
```

- [ ] Создать VariantGallery.tsx
- [ ] Показывать все варианты из getHistory()
- [ ] Выделять selected вариант
- [ ] Кнопка "Regenerate" с optional feedback input
- [ ] Удалить `src/components/workflow/StepReview.tsx` (заменён на VariantGallery)

### 4.7 Удалить legacy компоненты

- [ ] Удалить `src/components/VideoWorkflowView.tsx` (не используется)
- [ ] Удалить `src/components/StepCard.tsx` (не используется)

### 4.8 Рефакторинг StepsList

**Проблема:**
- `StepsList.tsx` принимает `WorkflowStep[]` — удаляем модель
- `StepsListV3.tsx` работает с `Video` напрямую — но разная логика для Discover/Remix

**Решение:**
1. Удалить `StepsList.tsx`
2. Переименовать `StepsListV3.tsx` → `StepsList.tsx`
3. Обновить `buildStepsFromVideo()`: убрать ветвление, всегда 4 шага

```typescript
// Было (StepsListV3):
if (!isRemix) {
  // Discover: scenario → image → video → audio
} else {
  // Remix: image → video → audio (без scenario)
}

// Станет:
// Всегда 4 шага для всех типов проектов
const steps = ['scenario', 'image', 'video']
if (includeAudio) steps.push('audio')
```

- [ ] Удалить `src/components/video/StepsList.tsx`
- [ ] Переименовать `StepsListV3.tsx` → `StepsList.tsx`
- [ ] Обновить `buildStepsFromVideo()`: унифицировать 4 шага
- [ ] Обновить `InProgressView.tsx`: передавать `video` вместо `steps`
- [ ] Обновить `src/components/video/index.ts`: убрать StepsListV3 из экспорта

### 4.9 Другие компоненты

- [ ] VideoDetail.tsx — убрать зависимости от workflow_steps

---

## Фаза 5: Тесты и скрипты

### 5.1 Удалить тесты

- [ ] Удалить `tests/test_discover_auto.py`
- [ ] Удалить `tests/test_models/test_video.py` (TestWorkflowStepModel)

### 5.2 Обновить тесты

- [ ] `tests/conftest.py` — убрать фикстуры WorkflowStep
- [ ] `tests/test_workflow.py` — переписать на StepHistory

### 5.3 Удалить скрипты и утилиты

- [ ] Удалить `scripts/migrate_to_variants.py`
- [ ] Удалить `check_steps.py` (утилита для workflow_steps)

### 5.4 Обновить alembic

- [ ] `alembic/env.py` — убрать импорты старых моделей

### 5.5 Обновить create_db.py

- [ ] Убрать импорты WorkflowStep, ValidationResult

---

## Фаза 6: Финальная проверка

### Автотесты
- [ ] `cd backend && venv/bin/pytest`
- [ ] `cd frontend && npm run build`

### E2E: Discover AUTO
- [ ] Создать Discover проект → Video AUTO → Run → 4 шага (SCENARIO → IMAGE → VIDEO → AUDIO) → Completed

### E2E: Discover AUTO (без audio)
- [ ] audio_mode=none → 3 шага (SCENARIO → IMAGE → VIDEO) → Completed

### E2E: Remix AUTO
- [ ] Создать Remix проект с story_template → Video AUTO → Run → 4 шага → Completed
- [ ] Проверить что SCENARIO заполняет переменные из шаблона

### E2E: Discover MANUAL
- [ ] Generate SCENARIO (1 вариант) → Select (auto-continue)
- [ ] Generate IMAGE (3 варианта) → Select (auto-continue)
- [ ] Generate VIDEO (1 вариант) → Select (auto-continue)
- [ ] Generate AUDIO (1 вариант) → Select → Completed

### E2E: Выбор из истории
- [ ] Generate IMAGE_1 → Generate VIDEO_1 → не нравится
- [ ] Generate IMAGE_2 → Generate VIDEO_2 → не нравится
- [ ] Открыть галерею IMAGE → выбрать IMAGE_1
- [ ] Generate VIDEO_3 (от IMAGE_1) → Select
- [ ] Проверить parent_id: VIDEO_3.parent_id = IMAGE_1.id

### E2E: Remix MANUAL
- [ ] Generate SCENARIO (заполняет шаблон) → Select (auto-continue)
- [ ] Generate IMAGE (3 варианта) → Select (auto-continue)
- [ ] Generate VIDEO → Select (auto-continue)
- [ ] Generate AUDIO → Select → Completed

---

## Definition of Done

- [ ] T1-T4 удалены
- [ ] Один `workflow.py` с новыми endpoints
- [ ] `orchestrator.py` с функциями (run_auto, generate_step, select_variant)
- [ ] `strategies/` с DiscoverStrategy и RemixStrategy
- [ ] Удалены все дубликаты (v2, v3, orchestrator_v2)
- [ ] Удалены модели: WorkflowStep, StepAttempt, Variant, ValidationResult
- [ ] Удалены таблицы из БД
- [ ] Frontend на новом API
- [ ] **Discover и Remix: одинаковые 4 шага**
- [ ] SCENARIO step работает по-разному для Discover/Remix (через Strategy)
- [ ] AUTO и MANUAL работают
- [ ] Select = auto-continue (1 клик)
- [ ] Все тесты проходят
- [ ] E2E пройдены

---

## Порядок выполнения

```
Фаза 1: БД (миграция, удаление моделей)
    ↓
Фаза 2: services/workflow/ (рефакторинг)
    ↓
Фаза 3: API (удаление v2/v3, переписать workflow.py)
    ↓
Фаза 4: Frontend
    ↓
Фаза 5: Тесты
    ↓
Фаза 6: E2E
```

---

## Риски

| Риск | Митигация |
|------|-----------|
| Сломать работающий функционал | Делать пофазно, тестировать после каждой |
| Большой объём изменений | Коммитить после каждой фазы |
| Пропустить зависимость | grep по кодовой базе перед удалением |
