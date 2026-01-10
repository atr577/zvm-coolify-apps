# Task 27: Remix Workflow (Full Implementation)

**Приоритет:** P1 (HIGH)
**Оценка:** 18h
**Зависимости:** Task 22 (Data Model), Task 23 (Breakpoints)
**Блокирует:** Batch generation, Template Builder UI

> **Источник:** [TARGET_WORKFLOW.md](../../docs/TARGET_WORKFLOW.md) секции 3, 5

---

## Цель

Полная реализация Remix workflow:
- RemixProject с templates и placeholders
- PREPARE phase (заполнение шаблонов)
- 3-step workflow: IMAGE → VIDEO → AUDIO
- Поддержка AUTO/MANUAL modes

---

## Задачи

### 27.1 RemixProject модель (3h)

**Файл:** `backend/app/models/project.py`

```python
class Project(Base):
    # ... existing fields ...

    # Remix-specific fields
    source_video_ids = Column(JSON, nullable=True)  # List[int] - Discover videos used as basis
    prompt_template = Column(Text, nullable=True)   # Template with {placeholders}
    scenario_template = Column(JSON, nullable=True) # Template with {placeholders}
    placeholders = Column(JSON, nullable=True)      # List[str] - ["dress_color", "car_model"]
    placeholder_suggestions = Column(JSON, nullable=True)  # {dress_color: ["red", "blue"]}
```

**Файл:** `backend/app/schemas/project.py`

```python
class RemixProjectCreate(BaseModel):
    name: str
    project_type: Literal["remix"] = "remix"
    platforms: List[str]
    duration: int = 5

    # Remix required fields
    source_video_ids: List[int]
    prompt_template: str
    scenario_template: dict
    placeholders: List[str]
    placeholder_suggestions: Dict[str, List[str]]

    @validator('placeholder_suggestions')
    def validate_suggestions(cls, v, values):
        placeholders = values.get('placeholders', [])
        missing = set(placeholders) - set(v.keys())
        if missing:
            raise ValueError(f"Missing suggestions for: {missing}")
        empty = [p for p, vals in v.items() if not vals]
        if empty:
            raise ValueError(f"Empty suggestions for: {empty}")
        return v
```

---

### 27.2 RemixVideo модель (1h)

**Файл:** `backend/app/models/video.py`

```python
class Video(Base):
    # ... existing fields ...

    # Remix-specific
    content_variables = Column(JSON, nullable=True)  # {dress_color: "red", car_model: "BMW"}
```

**Файл:** `backend/app/schemas/video.py`

```python
class RemixVideoCreate(BaseModel):
    project_id: int
    workflow_mode: WorkflowMode = WorkflowMode.AUTO
    content_variables: Optional[Dict[str, str]] = None  # User can override
```

---

### 27.3 PREPARE phase (3h)

**Файл:** `backend/app/services/workflow/remix_prepare.py` (NEW)

```python
from typing import Dict, Any, Optional
from app.models import Project, Video

def prepare_remix(
    project: Project,
    video: Video,
    batch_index: Optional[int] = None
) -> None:
    """
    Fill templates for Remix steps (IMAGE, VIDEO).
    Modifies video in-place.
    """
    variables = dict(video.content_variables or {})

    # Auto-fill missing variables
    missing = set(project.placeholders) - set(variables.keys())
    for placeholder in missing:
        suggestions = project.placeholder_suggestions.get(placeholder, [])

        if batch_index is not None and suggestions:
            # Batch mode: round-robin for even coverage
            variables[placeholder] = suggestions[batch_index % len(suggestions)]
        elif suggestions:
            # Single mode: random or first
            variables[placeholder] = suggestions[0]
        else:
            raise ValueError(f"No suggestion for placeholder: {placeholder}")

    # Save auto-filled variables
    video.content_variables = variables

    # Fill templates
    video.prompt_data = {"main_prompt": fill_template(project.prompt_template, variables)}
    video.scenario_data = fill_template(project.scenario_template, variables)


def fill_template(template: str | dict, variables: Dict[str, str]) -> str | dict:
    """Replace {placeholders} with values."""
    if isinstance(template, str):
        result = template
        for key, value in variables.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result
    elif isinstance(template, dict):
        return {k: fill_template(v, variables) for k, v in template.items()}
    return template
```

---

### 27.4 Remix Orchestrator (4h)

**Файл:** `backend/app/services/workflow/orchestrator.py`

```python
# Add to REMIX_BREAKPOINTS (already in Task 23)
REMIX_BREAKPOINTS = [StepType.IMAGE, StepType.VIDEO, StepType.AUDIO]

async def run_remix_workflow(self) -> WorkflowResult:
    """Run remix workflow: PREPARE → IMAGE → VIDEO → AUDIO."""

    # PREPARE phase (sync, before workflow)
    from app.services.workflow.remix_prepare import prepare_remix
    prepare_remix(self.project, self.video)
    self.db.commit()

    # Step 1: IMAGE (using filled prompt_data)
    await self._generate_image()
    self.steps_completed += 1
    if self._should_pause(StepType.IMAGE):
        return self._pause_result("Image generated", StepType.IMAGE)

    # Step 2: VIDEO (using filled scenario_data)
    await self._generate_video()
    self.steps_completed += 1
    if self._should_pause(StepType.VIDEO):
        return self._pause_result("Video generated", StepType.VIDEO)

    # Step 3: AUDIO
    await self._generate_audio()
    self.steps_completed += 1
    if self._should_pause(StepType.AUDIO):
        return self._pause_result("Audio generated", StepType.AUDIO)

    return self._complete_workflow()
```

**Обновить `_generate_image`:**

```python
async def _generate_image(self):
    """Generate image from prompt_data."""
    # For Remix: prompt_data already filled by PREPARE
    # For Discover: prompt_data generated by previous step

    prompt = self.video.prompt_data.get("main_prompt", "")
    if not prompt:
        raise ValueError("No prompt_data available for image generation")

    # ... rest of image generation
```

---

### 27.5 API endpoints (3h)

**Файл:** `backend/app/api/projects.py`

```python
@router.post("/remix", response_model=ProjectResponse)
async def create_remix_project(
    body: RemixProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a Remix project with templates."""
    # Validate source videos exist and belong to user
    for video_id in body.source_video_ids:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(404, f"Source video {video_id} not found")
        verify_video_ownership(db, video, current_user)

    project = Project(
        user_id=current_user.id,
        workspace_id=body.workspace_id,
        project_type="remix",
        source_video_ids=body.source_video_ids,
        prompt_template=body.prompt_template,
        scenario_template=body.scenario_template,
        placeholders=body.placeholders,
        placeholder_suggestions=body.placeholder_suggestions,
        **body.dict(exclude={"source_video_ids", "prompt_template", "scenario_template", "placeholders", "placeholder_suggestions"})
    )
    db.add(project)
    db.commit()
    return project


@router.post("/remix/{project_id}/videos", response_model=VideoResponse)
async def create_remix_video(
    project_id: int,
    body: RemixVideoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a video in Remix project with optional variable overrides."""
    project = get_project_with_ownership(db, project_id, current_user)

    if project.project_type != "remix":
        raise HTTPException(400, "Project is not a remix project")

    video = Video(
        project_id=project_id,
        workflow_mode=body.workflow_mode,
        content_variables=body.content_variables or {}
    )
    db.add(video)
    db.commit()
    return video
```

---

### 27.6 Frontend types (2h)

**Файл:** `frontend/src/types/project.ts`

```typescript
export interface RemixProject extends Project {
  project_type: 'remix';
  source_video_ids: number[];
  prompt_template: string;
  scenario_template: Record<string, any>;
  placeholders: string[];
  placeholder_suggestions: Record<string, string[]>;
}

export interface CreateRemixProjectRequest {
  name: string;
  workspace_id: number;
  platforms: string[];
  duration: number;
  source_video_ids: number[];
  prompt_template: string;
  scenario_template: Record<string, any>;
  placeholders: string[];
  placeholder_suggestions: Record<string, string[]>;
}
```

**Файл:** `frontend/src/types/video.ts`

```typescript
export interface RemixVideo extends Video {
  content_variables: Record<string, string>;
}

export interface CreateRemixVideoRequest {
  project_id: number;
  workflow_mode: 'AUTO' | 'MANUAL';
  content_variables?: Record<string, string>;
}
```

---

### 27.7 Migration (1h)

```bash
alembic revision --autogenerate -m "add remix project fields"
alembic upgrade head
```

**Проверить миграцию добавляет:**
- projects.source_video_ids (JSON)
- projects.prompt_template (Text)
- projects.scenario_template (JSON)
- projects.placeholders (JSON)
- projects.placeholder_suggestions (JSON)
- videos.content_variables (JSON)

---

### 27.8 TBD: Template Builder UI (отдельная задача)

> **Из TARGET_WORKFLOW:** UI Flow (TBD): Как user попадает в Template Builder — отдельная задача.

Entry points (для будущей реализации):
- Analytics dashboard: "Create Remix from top performers"
- Video detail: "Use as template"
- Projects list: "New Remix Project"

**Действие:** Создать отдельную задачу после 27

---

### 27.9 TBD: Batch Generation API (отдельная задача)

> **Из TARGET_WORKFLOW:** Batch API (TBD): определить при имплементации.

Варианты:
- Batch endpoint: `POST /projects/{id}/generate-batch?count=10`
- Auto-combinations: генерировать все комбинации placeholders
- Отдельные вызовы: frontend создаёт N видео

**Действие:** Создать отдельную задачу после 27

---

## Acceptance Criteria

- [ ] RemixProject с templates и placeholders создаётся
- [ ] Валидация: все placeholders имеют suggestions
- [ ] PREPARE phase заполняет prompt_data и scenario_data
- [ ] Remix workflow: IMAGE → VIDEO → AUDIO работает
- [ ] AUTO mode: 3 шага без пауз
- [ ] MANUAL mode: пауза после каждого шага
- [ ] content_variables можно переопределить при создании video

---

## Тестирование

```python
def test_remix_project_validation():
    # Missing suggestions should fail
    with pytest.raises(ValidationError):
        RemixProjectCreate(
            name="Test",
            placeholders=["color", "car"],
            placeholder_suggestions={"color": ["red"]}  # missing "car"
        )

def test_prepare_remix_fills_templates():
    project = create_remix_project(
        prompt_template="A {color} dress in {car}",
        placeholders=["color", "car"],
        placeholder_suggestions={"color": ["red"], "car": ["BMW"]}
    )
    video = create_video(project_id=project.id)

    prepare_remix(project, video)

    assert video.prompt_data["main_prompt"] == "A red dress in BMW"
    assert video.content_variables == {"color": "red", "car": "BMW"}

def test_remix_workflow_auto():
    project = create_remix_project(project_type="remix")
    video = create_video(project_id=project.id, workflow_mode=WorkflowMode.AUTO)

    result = await orchestrator.run_remix_workflow()

    assert result.paused_for_approval == False
    assert video.status == WorkflowStatus.COMPLETED
    assert video.image_url is not None
    assert video.video_url is not None

def test_remix_workflow_manual():
    video = create_video(workflow_mode=WorkflowMode.MANUAL, project_type="remix")

    result = await orchestrator.run_remix_workflow()

    assert result.paused_for_approval == True
    assert video.current_step == StepType.IMAGE
```

---

## Checklist

- [ ] 27.1 RemixProject model fields
- [ ] 27.2 Video.content_variables field
- [ ] 27.3 PREPARE phase implementation
- [ ] 27.4 Remix orchestrator integration
- [ ] 27.5 API endpoints for remix
- [ ] 27.6 Frontend types
- [ ] 27.7 Alembic migration
- [ ] 27.8 TBD: Template Builder UI (separate task)
- [ ] 27.9 TBD: Batch Generation API (separate task)
- [ ] All tests pass
- [ ] Code review

---

**Создано:** 2026-01-10
**Статус:** TODO
