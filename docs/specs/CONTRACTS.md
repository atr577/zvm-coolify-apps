# Contracts: API, Models, Frontend

**Дата:** 2026-01-10
**Источник:** TARGET_WORKFLOW.md (L1156-1506)

---

## 1. URL Convention

Все операции над workflow используют паттерн:

```
/api/workflow/{video_id}/{step_type}/{action}
```

**step_type:** `story`, `description`, `prompt`, `image`, `scenario`, `video`, `audio`

---

## 2. API Endpoints

### 2.1 Запуск Workflow

```
POST /api/workflow/{video_id}/start

Response 202:
{
  "video_id": int,
  "status": "in_progress",
  "current_step": "story" | "image",  // story для Discover, image для Remix
  "message": "Workflow started"
}
```

**Логика:**
- Discover: начинает с STORY
- Remix: вызывает PREPARE, начинает с IMAGE
- Устанавливает `video.status = IN_PROGRESS`

---

### 2.2 Получить статус (Polling)

```
GET /api/videos/{video_id}

Response 200:
{
  "id": int,
  "status": "pending" | "in_progress" | "awaiting_approval" | "completed" | "failed",
  "current_step": "story" | ... | "audio",
  "workflow_mode": "AUTO" | "MANUAL",

  // Данные шагов
  "story_data": {...} | null,
  "description_data": {...} | null,
  "prompt_data": {...} | null,
  "image_url": "..." | null,
  "scenario_data": {...} | null,
  "video_url": "..." | null,
  "audio_variants": [...] | null,
  "video_with_audio_url": "..." | null,

  // Для UI
  "project": {...},
  "workflow_steps": [...]
}
```

---

### 2.3 Получить варианты шага

```
GET /api/workflow/{video_id}/{step_type}/variants

Response 200:
{
  "step_type": "image",
  "step_id": int,
  "current_attempt": {
    "attempt_id": int,
    "attempt_number": int,
    "variants": [
      {
        "id": int,
        "variant_number": int,
        "content": {...},  // {url: "..."} для image/video, {text: "..."} для text steps
        "is_selected": bool
      }
    ]
  },
  "previous_attempts": [...]  // история
}
```

---

### 2.4 Выбрать вариант

```
POST /api/workflow/{video_id}/{step_type}/select

Body:
{
  "variant_id": int
}

Response 200:
{
  "step_type": "image",
  "variant_id": int,
  "status": "selected"
}
```

**Логика:**
- Устанавливает `WorkflowStep.selected_variant_id`
- Устанавливает `Variant.is_selected = true` (сбрасывает у других)
- НЕ копирует в Video — только при approve

---

### 2.5 Approve шага

```
POST /api/workflow/{video_id}/{step_type}/approve

Response 200:
{
  "step_type": "image",
  "status": "approved",
  "next_step": "scenario" | "video" | null,  // null если последний шаг
  "auto_continue": true | false,  // frontend должен вызвать /start
  "video_status": "in_progress" | "completed"
}
```

**Логика:**
1. `WorkflowStep.status = APPROVED`
2. Копировать `selected_variant.content` → `Video.{field}`
3. Если не последний шаг:
   - `Video.current_step = next_step`
   - `Video.status = IN_PROGRESS`
   - `auto_continue = true`
4. Если последний (AUDIO):
   - `Video.status = COMPLETED`
   - Генерировать `publishing_meta`

---

### 2.6 Regenerate с feedback

```
POST /api/workflow/{video_id}/{step_type}/regenerate

Body:
{
  "variant_id": int,      // на основе какого
  "feedback": "string"    // optional
}

Response 202:
{
  "step_type": "image",
  "attempt_id": int,
  "status": "in_progress"
}
```

**Логика:**
- Создаёт новый `StepAttempt` с `parent_variant_id` и `feedback`
- `WorkflowStep.status = IN_PROGRESS`
- `Video.status = IN_PROGRESS`
- Запускает генерацию

---

### 2.7 Retry failed

```
POST /api/workflow/{video_id}/{step_type}/retry

Response 202:
{
  "step_type": "image",
  "attempt_id": int,
  "status": "in_progress"
}
```

---

### 2.8 Rollback

```
POST /api/workflow/{video_id}/rollback/{target_step}

Response 200:
{
  "video_id": int,
  "rolled_back_to": "image",
  "deleted_steps": ["scenario", "video", "audio"],
  "status": "awaiting_approval"
}
```

**Логика:**
- Удалить WorkflowSteps после target (каскадно attempts/variants)
- Очистить поля Video (scenario_data=null, video_url=null, etc.)
- `target_step.status = AWAITING_APPROVAL`
- `Video.current_step = target_step`
- `Video.status = AWAITING_APPROVAL`

---

### 2.9 Reject шага (для аналитики)

```
POST /api/workflow/{video_id}/{step_type}/reject

Body:
{
  "reason": "string"    // optional
}

Response 200:
{
  "step_type": "image",
  "status": "rejected",
  "available_actions": ["regenerate", "select_other_variant"],
  "previous_variants_count": int
}
```

**Логика:**
- Reject — **действие**, не состояние (step.status остаётся AWAITING_APPROVAL)
- Записывается для аналитики (какие варианты отклоняются)
- После reject user может: regenerate или выбрать другой вариант

---

## 3. Model Contracts

### 3.1 Video

```python
class Video:
    # Identity
    id: int
    project_id: int
    title: str

    # Workflow control
    workflow_mode: WorkflowMode  # AUTO | MANUAL
    status: WorkflowStatus       # PENDING | IN_PROGRESS | AWAITING_APPROVAL | COMPLETED | FAILED
    current_step: StepType       # STORY | DESCRIPTION | ... | AUDIO

    # Content (Discover)
    creative_inputs: JSON        # {theme, mood, target_audience, ...}

    # Content (Remix)
    content_variables: JSON      # {dress_color: "red", car_model: "BMW"}

    # Step outputs (заполняются при approve)
    story_data: JSON
    description_data: JSON
    prompt_data: JSON
    image_url: str
    scenario_data: JSON
    video_url: str
    audio_variants: JSON         # legacy, migrate to Variant
    video_with_audio_url: str
    publishing_meta: JSON

    # Publishing
    is_published: bool
```

**Кто меняет status:**
| Действие | Новый status | Кто меняет |
|----------|--------------|------------|
| /start | IN_PROGRESS | Backend |
| Шаг завершён (MANUAL) | AWAITING_APPROVAL | Backend |
| /approve | IN_PROGRESS или COMPLETED | Backend |
| Ошибка генерации | FAILED | Backend |
| /retry | IN_PROGRESS | Backend |

---

### 3.2 WorkflowStep

```python
class WorkflowStep:
    id: int
    video_id: int
    step_type: StepType
    status: WorkflowStatus       # PENDING | IN_PROGRESS | AWAITING_APPROVAL | APPROVED | FAILED
    selected_variant_id: int | None
    created_at: datetime
```

---

### 3.3 StepAttempt

```python
class StepAttempt:
    id: int
    step_id: int                 # FK → WorkflowStep
    attempt_number: int          # 1, 2, 3...
    status: AttemptStatus        # PENDING | SUCCESS | FAILED

    parent_variant_id: int | None  # lineage
    feedback: str | None

    started_at: datetime
    completed_at: datetime | None
    error_message: str | None
```

---

### 3.4 Variant

```python
class Variant:
    id: int
    attempt_id: int              # FK → StepAttempt
    variant_number: int          # 1, 2, 3 внутри attempt
    content: JSON                # {url: "..."} или {data: {...}}
    is_selected: bool
```

---

### 3.5 Project (Remix fields)

```python
class Project:
    # ... existing fields ...

    # Remix-specific (required for project_type="remix")
    prompt_template: str              # "A woman in {dress_color}..."  (alias: story_template)
    scenario_template: JSON           # {motion_prompt: "...", camera: "..."}
    placeholders: List[str]           # ["dress_color", "car_model"]
    placeholder_suggestions: JSON     # {dress_color: ["red", "blue"]}
    source_video_ids: List[int]       # optional
```

**Валидация при создании Remix:**
```python
if project_type == "remix":
    assert prompt_template is not None
    assert scenario_template is not None
    assert placeholders is not None
    assert all(p in placeholder_suggestions for p in placeholders)
    assert all(len(v) > 0 for v in placeholder_suggestions.values())
```

---

## 4. Frontend Contract

### 4.1 Polling Loop

```typescript
async function pollVideo(videoId: number) {
  const INTERVAL = 3000

  while (true) {
    const video = await api.get(`/videos/${videoId}`)

    switch (video.status) {
      case 'pending':
        // ждём старта
        break

      case 'in_progress':
        // показываем прогресс
        updateProgress(video.current_step)
        break

      case 'awaiting_approval':
        // показываем UI для approve
        showApprovalUI(video)
        return  // stop polling

      case 'completed':
        showCompleted(video)
        return

      case 'failed':
        showError(video)
        return
    }

    await sleep(INTERVAL)
  }
}
```

---

### 4.2 Approval Flow

```typescript
async function handleApprove(videoId: number, stepType: string) {
  const response = await api.post(`/workflow/${videoId}/${stepType}/approve`)

  if (response.auto_continue) {
    // автоматически продолжаем workflow
    await api.post(`/workflow/${videoId}/start`)
    startPolling(videoId)
  } else {
    // последний шаг — показываем результат
    showCompleted(response)
  }
}
```

---

### 4.3 Variants UI

```typescript
async function showApprovalUI(video: Video) {
  const stepType = video.current_step

  // Получить варианты
  const variants = await api.get(`/workflow/${video.id}/${stepType}/variants`)

  if (variants.current_attempt.variants.length === 1) {
    // Один вариант — простой UI
    showSingleVariantUI(variants.current_attempt.variants[0])
  } else {
    // Несколько вариантов — UI выбора
    showMultiVariantUI(variants.current_attempt.variants)
  }
}

async function selectAndApprove(videoId: number, stepType: string, variantId: number) {
  await api.post(`/workflow/${videoId}/${stepType}/select`, { variant_id: variantId })
  await handleApprove(videoId, stepType)
}
```

---

## 5. Step Data Contract

### 5.1 Discover Steps

| Step | Input | Output Field | Output Schema |
|------|-------|--------------|---------------|
| STORY | creative_inputs | story_data | {concept, hook, tone, pacing, ...} |
| DESCRIPTION | story_data | description_data | {scene, setting, lighting, ...} |
| PROMPT | description_data | prompt_data | {main_prompt, negative_prompt, ...} |
| IMAGE | prompt_data | image_url | string (URL) |
| SCENARIO | story_data + image_url | scenario_data | {camera_movement, subject_motion, ...} |
| VIDEO | image_url + scenario_data | video_url | string (URL) |
| AUDIO | video_url | video_with_audio_url | string (URL) |

### 5.2 Remix Steps

| Step | Input | Output Field |
|------|-------|--------------|
| PREPARE | content_variables + templates | prompt_data + scenario_data |
| IMAGE | prompt_data (filled) | image_url |
| VIDEO | image_url + scenario_data (filled) | video_url |
| AUDIO | video_url | video_with_audio_url |

---

## 6. Variants Config

```python
DEFAULT_VARIANTS_CONFIG = {
    "STORY": 1,
    "DESCRIPTION": 1,
    "PROMPT": 1,
    "IMAGE": 3,      # MANUAL: 3 варианта
    "SCENARIO": 1,
    "VIDEO": 1,
    "AUDIO": 3       # MANUAL: 3 варианта
}
```

**AUTO mode:** всегда 1 вариант, auto-select, auto-approve
**MANUAL mode:** N вариантов согласно config, user выбирает

---

## 7. Error Responses

```
400 Bad Request — невалидные данные
404 Not Found — video/step не найден
409 Conflict — операция невозможна в текущем состоянии
500 Internal Server Error — ошибка сервера
```

**409 примеры:**
- Approve когда step.status != AWAITING_APPROVAL
- Start когда video.status == IN_PROGRESS
- Rollback когда video.is_published == true

---

## 8. Concurrency Protection

Защита от race conditions (два таба, двойной клик). **Первый запрос выигрывает.**

### Video-level

```python
def start_workflow(video_id: int):
    video = db.query(Video).filter(id=video_id).with_for_update().first()

    if video.status == VideoStatus.IN_PROGRESS:
        raise HTTPException(409, "Generation already in progress")

    if video.status == VideoStatus.COMPLETED:
        raise HTTPException(409, "Video already completed")

    # OK: PENDING или AWAITING_APPROVAL
    video.status = VideoStatus.IN_PROGRESS
    db.commit()
```

### Step-level

```python
def approve_step(video_id: int, step_type: str):
    step = db.query(WorkflowStep).filter(...).with_for_update().first()

    if step.status != StepStatus.AWAITING_APPROVAL:
        raise HTTPException(409, f"Cannot approve: step is {step.status}")

    step.status = StepStatus.APPROVED
    db.commit()
```

### Валидные переходы

**Video:**
| Из | Действие | В |
|----|----------|---|
| PENDING | /start | IN_PROGRESS |
| AWAITING_APPROVAL | /start (continue) | IN_PROGRESS |
| IN_PROGRESS | — | 409 (ждать) |
| COMPLETED | — | 409 |
| FAILED | /retry | IN_PROGRESS |

**WorkflowStep:**
| Из | Действие | В |
|----|----------|---|
| AWAITING_APPROVAL | /approve | APPROVED |
| AWAITING_APPROVAL | /regenerate | IN_PROGRESS |
| AWAITING_APPROVAL | /select | AWAITING_APPROVAL |
| FAILED | /retry | IN_PROGRESS |
| IN_PROGRESS | — | 409 (ждать) |

**Frontend:** При 409 показать "Action already in progress, please refresh"
