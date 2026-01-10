# Task 23: Breakpoints System (Phase 3)

**Приоритет:** P1 (HIGH)
**Оценка:** 6h
**Зависимости:** Task 22 (Data Model)
**Блокирует:** Phase 4

> **Источник:** [IMPLEMENTATION_PLAN.md](../../docs/IMPLEMENTATION_PLAN.md) Phase 3
> **Детальный план:** [PLAN_BREAKPOINTS_SYSTEM.md](../../docs/PLAN_BREAKPOINTS_SYSTEM.md)

---

## Цель

Сделать `workflow_mode` (AUTO/MANUAL) реально работающим:
- **AUTO**: все шаги без остановок
- **MANUAL**: остановка после каждого breakpoint для approve

---

## Задачи

### 23.1 Добавить `_should_pause()` (2h)

**Файл:** `backend/app/services/workflow/orchestrator.py`

```python
from app.models.video import StepType, WorkflowMode

# Breakpoints для каждого типа проекта
DISCOVER_BREAKPOINTS = [
    StepType.STORY,
    StepType.DESCRIPTION,
    StepType.PROMPT,
    StepType.IMAGE,
    StepType.SCENARIO,
    StepType.VIDEO,
    StepType.AUDIO,
]

REMIX_BREAKPOINTS = [
    StepType.IMAGE,
    StepType.VIDEO,
    StepType.AUDIO,
]

class WorkflowOrchestrator:
    def __init__(self, ...):
        # ... existing ...
        self.is_remix = self.project.project_type == "remix"

    def _should_pause(self, step_type: StepType) -> bool:
        """Check if workflow should pause at this step."""
        if self.video.workflow_mode == WorkflowMode.AUTO:
            return False  # AUTO never pauses

        breakpoints = REMIX_BREAKPOINTS if self.is_remix else DISCOVER_BREAKPOINTS
        return step_type in breakpoints

    def _pause_result(self, message: str, current_step: StepType) -> WorkflowResult:
        """Create a pause result for MANUAL mode."""
        self.video.status = WorkflowStatus.AWAITING_APPROVAL
        self.video.current_step = current_step
        self.db.commit()

        return WorkflowResult(
            video_id=self.video.id,
            steps_completed=self.steps_completed,
            message=message,
            mode="remix" if self.is_remix else "discover",
            total_time_seconds=self._elapsed_time(),
            paused_for_approval=True,
            next_action=f"approve_{current_step.value.lower()}"
        )
```

---

### 23.2 Интегрировать в workflow loop (2h)

**Файл:** `backend/app/services/workflow/orchestrator.py`

```python
async def run_discover_workflow(self) -> WorkflowResult:
    """Run discover workflow with breakpoint checks."""

    # Step 1: Story
    await self._generate_story()
    self.steps_completed += 1
    if self._should_pause(StepType.STORY):
        return self._pause_result("Story generated", StepType.STORY)

    # Step 2: Description
    await self._generate_description()
    self.steps_completed += 1
    if self._should_pause(StepType.DESCRIPTION):
        return self._pause_result("Description generated", StepType.DESCRIPTION)

    # Step 3: Prompt
    await self._generate_prompt()
    self.steps_completed += 1
    if self._should_pause(StepType.PROMPT):
        return self._pause_result("Prompt generated", StepType.PROMPT)

    # Step 4: Image
    await self._generate_image()
    self.steps_completed += 1
    if self._should_pause(StepType.IMAGE):
        return self._pause_result("Image generated", StepType.IMAGE)

    # Step 5: Scenario
    await self._generate_scenario()
    self.steps_completed += 1
    if self._should_pause(StepType.SCENARIO):
        return self._pause_result("Scenario generated", StepType.SCENARIO)

    # Step 6: Video
    await self._generate_video()
    self.steps_completed += 1
    if self._should_pause(StepType.VIDEO):
        return self._pause_result("Video generated", StepType.VIDEO)

    # Step 7: Audio
    audio_result = await self._generate_audio()
    self.steps_completed += 1
    if self._should_pause(StepType.AUDIO):
        return self._pause_result("Audio generated", StepType.AUDIO)

    # Complete
    return self._complete_workflow()

async def run_remix_workflow(self) -> WorkflowResult:
    """Run remix workflow with breakpoint checks."""

    # Remix: Image → Video → Audio
    await self._generate_image()
    self.steps_completed += 1
    if self._should_pause(StepType.IMAGE):
        return self._pause_result("Image generated", StepType.IMAGE)

    await self._generate_video()
    self.steps_completed += 1
    if self._should_pause(StepType.VIDEO):
        return self._pause_result("Video generated", StepType.VIDEO)

    audio_result = await self._generate_audio()
    self.steps_completed += 1
    if self._should_pause(StepType.AUDIO):
        return self._pause_result("Audio generated", StepType.AUDIO)

    return self._complete_workflow()
```

---

### 23.3 Удалить require_image_approval (1h)

**Шаг 1: Backend model**

**Файл:** `backend/app/models/project.py`
```python
# УДАЛИТЬ:
# require_image_approval = Column(Integer, nullable=False, default=0)
```

**Файл:** `backend/app/schemas/project.py`
```python
# УДАЛИТЬ из ProjectCreate и ProjectUpdate:
# require_image_approval: Optional[bool] = False
```

**Шаг 2: Migration**
```bash
alembic revision --autogenerate -m "remove require_image_approval"
alembic upgrade head
```

**Шаг 3: Удалить использования**
- `orchestrator.py`: убрать `if self.project.require_image_approval`
- `approval.py`: убрать специальную логику для require_image_approval

---

### 23.4 Показать mode selector для Remix (1h)

**Файл:** `frontend/src/pages/CreateVideo.tsx`

```tsx
// БЫЛО (line 105):
{project.project_type !== 'remix' && (
  <WorkflowModeSelector ... />
)}

// СТАНЕТ:
<WorkflowModeSelector
  value={workflowMode}
  onChange={setWorkflowMode}
  disabled={isGenerating}
/>
```

**Файл:** `frontend/src/components/ProjectForm.tsx`

```tsx
// УДАЛИТЬ секцию require_image_approval (lines 248-262)
```

---

## Feature Flag

**Файл:** `backend/app/core/config.py`

```python
USE_NEW_BREAKPOINTS: bool = False
```

**Использование:**
```python
def _should_pause(self, step_type: StepType) -> bool:
    if not settings.USE_NEW_BREAKPOINTS:
        # Old behavior: only pause at image if require_image_approval
        return (step_type == StepType.IMAGE and
                self.project.require_image_approval)

    # New behavior: breakpoints system
    if self.video.workflow_mode == WorkflowMode.AUTO:
        return False
    breakpoints = REMIX_BREAKPOINTS if self.is_remix else DISCOVER_BREAKPOINTS
    return step_type in breakpoints
```

---

## Acceptance Criteria

- [ ] Discover + AUTO: проходит все 7 шагов без остановок
- [ ] Discover + MANUAL: останавливается после каждого шага
- [ ] Remix + AUTO: проходит все 3 шага без остановок
- [ ] Remix + MANUAL: останавливается после Image, Video, Audio
- [ ] require_image_approval удалён из кода и БД
- [ ] Frontend показывает mode selector для всех типов проектов

---

## Тестирование

```python
@pytest.mark.asyncio
async def test_discover_auto_no_pause():
    video = create_video(workflow_mode=WorkflowMode.AUTO)
    result = await orchestrator.run_discover_workflow()

    assert result.paused_for_approval == False
    assert video.status == WorkflowStatus.COMPLETED

@pytest.mark.asyncio
async def test_discover_manual_pauses():
    video = create_video(workflow_mode=WorkflowMode.MANUAL)

    # First run - should pause at STORY
    result = await orchestrator.run_discover_workflow()
    assert result.paused_for_approval == True
    assert video.current_step == StepType.STORY

    # Approve and continue - should pause at DESCRIPTION
    await approve_step(video, StepType.STORY)
    result = await orchestrator.run_discover_workflow()
    assert result.paused_for_approval == True
    assert video.current_step == StepType.DESCRIPTION

@pytest.mark.asyncio
async def test_remix_manual_breakpoints():
    video = create_video(
        workflow_mode=WorkflowMode.MANUAL,
        project_type="remix"
    )

    result = await orchestrator.run_remix_workflow()
    # Should pause at IMAGE (first remix breakpoint)
    assert video.current_step == StepType.IMAGE
```

---

## Rollback

1. Set `USE_NEW_BREAKPOINTS=false`
2. Frontend: revert CreateVideo.tsx changes

---

## Checklist

- [ ] 23.1 `_should_pause()` method added
- [ ] 23.2 Breakpoint checks in workflow loops
- [ ] 23.3 require_image_approval removed (model, schema, migration)
- [ ] 23.4 Mode selector shown for Remix
- [ ] Feature flag works
- [ ] All 4 test scenarios pass
- [ ] Code review

---

**Создано:** 2026-01-10
**Статус:** TODO
