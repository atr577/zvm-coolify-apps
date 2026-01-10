---
id: T10
title: "Рефакторинг workflow.py"
status: todo
priority: high
created: 2026-01-10
updated: 2026-01-10
tags: ['workflow']
depends_on: []
estimate: "3-5 дней"
branch: ""
---

# Task 10: Рефакторинг workflow.py

## Текущее состояние (2026-01-09)

| Метрика | Значение |
|---------|----------|
| Строк в workflow.py | **1308** |
| Дублирование | 8x повторяющийся паттерн |
| Тестовое покрытие | ~71% (общее) |

### Что уже сделано

1. **prompt_builders.py** (400 строк) — вынесены все билдеры промптов:
   - `build_story_prompt()`
   - `build_description_prompt()`
   - `build_image_prompt_prompt()`
   - `build_scenario_prompt()`
   - `build_adaptation_prompt()`
   - `DEFAULT_SYSTEM_PROMPTS` — дефолтные системные промпты

2. **get_effective_prompt()** — хелпер для работы с project.system_prompts

3. **Добавлены фичи**, увеличившие размер файла:
   - Prompt preview/edit в MANUAL mode
   - audio_mode проверка (skip audio if 'none')
   - Интеграция с project.system_prompts

## Проблема

Файл `workflow.py` содержит **1308 строк** с массивным дублированием:

```python
# Этот паттерн повторяется 8+ раз:
@router.post("/generate-{step}")
async def generate_{step}(request, db, current_user):
    video = db.query(Video).filter(Video.id == request.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    verify_video_ownership(db, video, current_user)

    # Get system_prompt from project
    project = video.project
    project_prompts = project.system_prompts if project and project.system_prompts else {}

    # Build original prompt for tracking
    original_prompt_data = build_xxx_prompt(..., system_prompt=project_prompts.get("xxx"))

    # Get effective prompt
    effective_prompt = get_effective_prompt(video, "xxx", original_prompt_data, request.custom_prompt)

    step = get_or_create_step(db, video.id, StepType.XXX)

    try:
        xxx_data = await openai_service.generate_xxx(..., custom_prompt=effective_prompt)
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

### approve_step — 290+ строк вложенных if/elif

```python
if request.approved:
    if step.step_type == StepType.VIDEO:
        # Check audio_mode
        if project.audio_mode == "none":
            # 15 строк skip audio
        else:
            # 25 строк generate audio
    elif step.step_type == StepType.ADAPTATION:
        # 15 строк
    else:
        if video.workflow_mode == WorkflowMode.MANUAL:
            # next_step_map + create next step
```

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
│       └── transitions.py       # Step transitions logic
├── api/
│   └── workflow.py              # Тонкий слой — только HTTP handlers (~150 строк)
```

## План рефакторинга

### Phase 1: BaseWorkflowStep (2-3 часа)

Создать базовый класс с общей логикой:
- `execute()` — основной flow
- `_get_or_create_step()`
- `_save_content()`
- `_validate()`
- `_handle_failure()`
- `_get_effective_prompt()` — работа с project.system_prompts

```python
class BaseWorkflowStep(ABC):
    step_type: StepType
    content_field: str
    requires_validation: bool = True

    async def execute(self, request, custom_prompt=None) -> dict:
        self.step = self._get_or_create_step()
        effective_prompt = self._get_effective_prompt(request, custom_prompt)

        try:
            content = await self.generate(request, effective_prompt)
            self._save_content(content)
            validation = await self._validate(content) if self.requires_validation else None
            return self._build_response(content, validation)
        except Exception as e:
            self._handle_failure(e)
            raise
```

### Phase 2: Step классы (3-4 часа)

8 классов, каждый ~30-50 строк:

| Step | Особенности |
|------|-------------|
| StoryStep | content_variables, story_template |
| DescriptionStep | Зависит от story_data |
| PromptStep | Зависит от description_data |
| ImageStep | requires_validation=False, KLING API |
| ScenarioStep | Vision API, image_url |
| VideoStep | KLING video, camera_control |
| AudioStep | audio_mode check, skip logic |
| AdaptationStep | platforms, full_context |

### Phase 3: Transitions (2 часа)

Вынести логику переходов между шагами:

```python
NEXT_STEP_MAP = {
    StepType.STORY: StepType.DESCRIPTION,
    StepType.DESCRIPTION: StepType.PROMPT,
    StepType.PROMPT: StepType.IMAGE,
    StepType.IMAGE: StepType.SCENARIO,
    StepType.SCENARIO: StepType.VIDEO,
    StepType.VIDEO: StepType.AUDIO,
    StepType.AUDIO: StepType.ADAPTATION,
    StepType.ADAPTATION: StepType.PUBLISHING,
}

def get_next_step(current: StepType) -> StepType | None
def should_auto_proceed(step: WorkflowStep, video: Video) -> bool
def handle_approval(step: WorkflowStep, video: Video) -> StepType | None
```

### Phase 4: Orchestrator (2-3 часа)

Координация выполнения:

```python
class WorkflowOrchestrator:
    def __init__(self, db: Session, video: Video):
        self.db = db
        self.video = video

    async def execute_step(self, step_type: StepType, request) -> dict
    async def approve_step(self, step_id: int, approved: bool, feedback: str = None) -> dict
    async def auto_generate(self) -> dict  # Full AUTO mode
```

### Phase 5: Тонкий API слой (2 часа)

Каждый endpoint — 10-15 строк:

```python
@router.post("/generate-story")
async def generate_story(request: GenerateStoryRequest, db: Session, current_user: User):
    video = get_video_or_404(db, request.video_id)
    verify_video_ownership(db, video, current_user)

    orchestrator = WorkflowOrchestrator(db, video)
    return await orchestrator.execute_step(StepType.STORY, request)
```

## Чеклист

- [x] Вынести prompt_builders.py
- [x] Добавить DEFAULT_SYSTEM_PROMPTS
- [x] Интегрировать project.system_prompts
- [ ] Создать `BaseWorkflowStep`
- [ ] Реализовать StoryStep
- [ ] Реализовать DescriptionStep
- [ ] Реализовать PromptStep
- [ ] Реализовать ImageStep
- [ ] Реализовать ScenarioStep
- [ ] Реализовать VideoStep (с audio_mode logic)
- [ ] Реализовать AudioStep
- [ ] Реализовать AdaptationStep
- [ ] Реализовать transitions.py
- [ ] Реализовать Orchestrator
- [ ] Переписать API endpoints
- [ ] Прогнать тесты
- [ ] Code review

## Метрики успеха

| Метрика | Сейчас | Цель |
|---------|--------|------|
| Строк в workflow.py | 1308 | ~150 |
| Дублирование | 8x | 0 |
| Строк в step классах | 0 | ~40 каждый |
| Тестовое покрытие workflow | ~70% | 85%+ |

## Риски и митигация

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Регрессии | Средняя | Инкрементальный рефакторинг, тесты на каждом этапе |
| Время | Средняя | Можно делать по 1-2 step класса за раз |
| Сложность AudioStep | Высокая | Особое внимание к audio_mode logic |

## Порядок работы

1. **Сначала** — BaseWorkflowStep + StoryStep (самый простой)
2. Протестировать что StoryStep работает через API
3. Добавлять остальные steps по одному
4. В конце — Orchestrator и тонкий API слой
5. Удалить старый код

---

**Статус:** Ready to start
**Обновлено:** 2026-01-09
