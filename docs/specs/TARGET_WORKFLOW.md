# Целевой Workflow

Каноническое описание целевой архитектуры workflow системы.

**Версия:** 2.0
**Обновлено:** 2026-01-11

---

## 1. Обзор

### Унифицированный workflow: 4 шага

```
SCENARIO → IMAGE → VIDEO → AUDIO
```

Оба типа проектов используют одинаковые 4 шага. Отличается только логика SCENARIO.

### Типы проектов

| Тип | Описание | SCENARIO |
|-----|----------|----------|
| **discover** | Творческий поиск: идея → видео | LLM генерирует креативно (много свободы) |
| **remix** | Масштабирование: шаблон → N видео | LLM заполняет переменные в шаблоне (мало свободы) |

### Режимы выполнения

| Mode | Поведение |
|------|-----------|
| **AUTO** | Все шаги выполняются без пауз, 1 вариант, auto-approve |
| **MANUAL** | Пауза после каждого шага для approve/reject, N вариантов |

### Матрица комбинаций

Все комбинации project_type × workflow_mode **валидны**:

| Комбинация | Use Case |
|------------|----------|
| Discover + MANUAL | Творческий поиск с контролем на каждом шаге |
| Discover + AUTO | Быстрый прототип идеи без пауз |
| Remix + MANUAL | Контроль качества при тиражировании |
| Remix + AUTO | Batch generation (100 видео без участия user) |

---

## 2. Discover Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DISCOVER WORKFLOW (4 шага)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐                 │
│  │ SCENARIO │──►│  IMAGE   │──►│  VIDEO   │──►│  AUDIO   │                 │
│  │  Step 1  │   │  Step 2  │   │  Step 3  │   │  Step 4  │                 │
│  │   LLM    │   │ ImageGen │   │ VideoGen │   │ AudioGen │                 │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘                 │
│       │               │               │               │                     │
│       ▼               ▼               ▼               ▼                     │
│  scenario_data    image_url       video_url    video_with_audio_url        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Шаги Discover

| # | Step | Service | Input | Output |
|---|------|---------|-------|--------|
| 1 | SCENARIO | LLM | story template (концепция) + creative inputs | scenario_data (включает prompt) |
| 2 | IMAGE | ImageGen | scenario_data.prompt | image_url |
| 3 | VIDEO | VideoGen | image_url + scenario_data | video_url |
| 4 | AUDIO | AudioGen | video_url | video_with_audio_url |

### SCENARIO в Discover

LLM получает **концепцию** (story template) и **creative inputs**, генерирует полный сценарий с высокой степенью свободы.

**Вход:**
```python
story_template: "Девушка в машине, атмосферно"  # концепция
creative_inputs: {
  theme: "luxury lifestyle",
  mood: "mysterious",
  target_audience: "gen-z",
  key_elements: ["golden hour", "city lights"],
  additional_notes: "viral potential"
}
```

**LLM генерирует (много свободы):**
```python
scenario_data: {
  # Для IMAGE
  prompt: "A woman in red dress sitting in BMW M4, golden hour...",
  negative_prompt: "...",

  # Для VIDEO
  camera_movement: "slow zoom in",
  subject_motion: "turns head, slight smile",
  duration: 5,

  # Метаданные
  concept: "Mysterious woman in luxury car at sunset",
  hook: "First 2 seconds: close-up of eyes in rearview mirror"
}
```

**Варианты:** В MANUAL mode LLM генерирует N вариантов scenario_data, user выбирает лучший.

---

## 3. Remix Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          REMIX WORKFLOW (4 шага)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐                 │
│  │ SCENARIO │──►│  IMAGE   │──►│  VIDEO   │──►│  AUDIO   │                 │
│  │  Step 1  │   │  Step 2  │   │  Step 3  │   │  Step 4  │                 │
│  │   LLM    │   │ ImageGen │   │ VideoGen │   │ AudioGen │                 │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘                 │
│       │               │               │               │                     │
│       ▼               ▼               ▼               ▼                     │
│  scenario_data    image_url       video_url    video_with_audio_url        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Шаги Remix

| # | Step | Service | Input | Output |
|---|------|---------|-------|--------|
| 1 | SCENARIO | LLM | story template (с {переменными}) | scenario_data (заполненный) |
| 2 | IMAGE | ImageGen | scenario_data.prompt | image_url |
| 3 | VIDEO | VideoGen | image_url + scenario_data | video_url |
| 4 | AUDIO | AudioGen | video_url | video_with_audio_url |

### SCENARIO в Remix

LLM получает **жёсткий шаблон** с {переменными}, генерирует значения переменных с низкой степенью свободы.

**Вход:**
```python
story_template: {
  prompt: "A woman in {dress_color} dress sitting in {car_model}, {lighting}",
  camera_movement: "{camera_style}",
  subject_motion: "exits car elegantly"
}
placeholders: ["dress_color", "car_model", "lighting", "camera_style"]
placeholder_suggestions: {
  dress_color: ["red", "black", "white"],
  car_model: ["BMW M4", "Mercedes AMG", "Porsche 911"],
  lighting: ["golden hour", "neon city lights", "studio lighting"],
  camera_style: ["slow zoom in", "static front", "tracking shot"]
}
```

**LLM генерирует (мало свободы):**
```python
# LLM выбирает из suggestions или генерирует похожее
generated_variables: {
  dress_color: "red",
  car_model: "BMW M4",
  lighting: "golden hour",
  camera_style: "slow zoom in"
}

# Результат: заполненный шаблон
scenario_data: {
  prompt: "A woman in red dress sitting in BMW M4, golden hour",
  camera_movement: "slow zoom in",
  subject_motion: "exits car elegantly"
}
```

**Варианты:** В MANUAL mode LLM генерирует N вариантов (разные комбинации переменных).

### Концепция Remix

**Discover** = эксперименты, поиск "формулы" (prompt + scenario + style)
**Remix** = масштабирование найденной формулы с вариациями

```
Discover: 100 экспериментов → находим что работает (метрики + субъективно)
    │
    ▼
Template Builder: собираем шаблон из лучших элементов
    │
    ▼
Remix: генерим 10-100 видео по шаблону с вариациями
    │
    ▼
Analytics: собираем метрики → уточняем формулу → повторяем
```

### Template Builder (LLM + Analytics)

> **UI Flow (TBD):** Как user попадает в Template Builder — отдельная задача.
> Возможные entry points:
> - Analytics dashboard: "Create Remix from top performers"
> - Video detail: "Use as template"
> - Projects list: "New Remix Project"

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TEMPLATE BUILDER                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                      ANALYTICS ENGINE                               │     │
│  │                                                                     │     │
│  │  Discover Videos (published):                                       │     │
│  │  ├─ Video A: 10K views, 2% engagement                              │     │
│  │  ├─ Video B: 50K views, 8% engagement  ← best performer            │     │
│  │  └─ Video C: 5K views, 1% engagement                               │     │
│  │                                                                     │     │
│  │  Insights:                                                          │     │
│  │  ├─ Video B: prompt structure → high engagement                    │     │
│  │  ├─ Video B: camera angle → good retention                         │     │
│  │  └─ Video A: color palette → interesting (test in remix)           │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                              │                                               │
│                              ▼                                               │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                      LLM TEMPLATE ASSEMBLER                         │     │
│  │                                                                     │     │
│  │  "Based on Video B (best metrics), I suggest this template:"       │     │
│  │                                                                     │     │
│  │  prompt_template: "A woman in {dress_color} dress sitting in       │     │
│  │                    {car_model}, looking at camera, golden hour"    │     │
│  │  scenario_template: {camera: "static front", motion: "exits car"}  │     │
│  │                                                                     │     │
│  │  Suggested placeholders:                                            │     │
│  │  ├─ {dress_color} — A/B test colors                                │     │
│  │  ├─ {car_model} — vary car brands                                  │     │
│  │  └─ Keep fixed: pose, camera, lighting (proven to work)            │     │
│  │                                                                     │     │
│  │  Source videos: [Video B] or [Video A + Video B]                   │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                              │                                               │
│                              ▼                                               │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                        USER REVIEW                                  │     │
│  │                                                                     │     │
│  │  [View template]  [Edit]  [Accept]  [Try different source]         │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Remix Project Structure

```python
class RemixProject:
    # Source
    source_video_ids: List[int]         # Discover videos used as basis

    # Story template (жёсткая канва с {переменными})
    story_template: JSON                # → SCENARIO step заполняет и генерирует scenario_data

    # Defined placeholders
    placeholders: List[str]             # ["dress_color", "car_model"]
    placeholder_suggestions: JSON       # {dress_color: ["red", "blue", "black"]}
    # ⚠️ REQUIRED: каждый placeholder должен иметь suggestions (валидация при создании)
```

**Источники suggestions:**
- **Template Builder** → LLM анализирует source videos + метрики, предлагает suggestions, user редактирует
- **Manual creation** → user вводит placeholders и suggestions вручную

### Auto-fill переменных в SCENARIO

SCENARIO step автоматически заполняет недостающие переменные.

**Выбор значения:**
- **Batch generation** → Round-robin (равномерное покрытие всех комбинаций)
- **Single video** → LLM выбирает лучшее для контекста

```python
def generate_scenario_remix(project: RemixProject, video: Video, batch_index: int = None):
    """SCENARIO step for Remix: LLM fills template variables."""
    variables = dict(video.content_variables or {})

    # Auto-fill missing variables
    missing = set(project.placeholders) - set(variables.keys())
    for placeholder in missing:
        suggestions = project.placeholder_suggestions.get(placeholder, [])

        if batch_index is not None and suggestions:
            # Batch mode: round-robin
            variables[placeholder] = suggestions[batch_index % len(suggestions)]
        elif suggestions:
            # Single mode: LLM выбирает
            variables[placeholder] = llm_choose_best(placeholder, suggestions, project)
        else:
            # Fallback: LLM генерирует
            variables[placeholder] = llm_generate_value(placeholder, project)

    # Fill template → scenario_data
    video.scenario_data = fill_template(project.story_template, variables)
    video.content_variables = variables  # сохранить для истории
```

### Remix Scaling

```
Remix Project: "Luxury Car Girl"
├─ placeholders: [dress_color, car_model]
├─ placeholder_suggestions:
│    dress_color: [red, blue, black, white]
│    car_model: [BMW M4, Mercedes AMG, Porsche 911]
│
└─ Generate batch:
     Video 1: {dress_color: red, car_model: BMW M4}
     Video 2: {dress_color: red, car_model: Mercedes AMG}
     Video 3: {dress_color: blue, car_model: BMW M4}
     ...
     Video 12: {dress_color: white, car_model: Porsche 911}

→ Publish all → Collect metrics → Find best combination → Refine template
```

> **Batch API (TBD):** Способ создания множества видео (batch endpoint, auto-combinations, или отдельные вызовы) — определить при имплементации.

---

## 4. Структуры данных

### scenario_data (главная структура)

Единая структура, создаваемая на шаге SCENARIO. Содержит всё необходимое для последующих шагов.

```json
{
  // Для IMAGE step
  "prompt": "A woman in red dress sitting in BMW M4, golden hour lighting",
  "negative_prompt": "blurry, low quality, distorted",
  "style_suffix": "cinematic, professional photography",
  "aspect_ratio": "9:16",

  // Для VIDEO step
  "camera_movement": "slow zoom in",
  "camera_speed": "slow",
  "subject_motion": "turns head, slight smile",
  "duration": 5,

  // Метаданные (для аналитики и publishing)
  "concept": "Mysterious woman in luxury car at sunset",
  "hook": "Close-up of eyes in rearview mirror",
  "tone": "mysterious",
  "emotional_trigger": "curiosity"
}
```

### Устаревшие структуры (deprecated)

> **Note:** Следующие структуры сохранены для обратной совместимости, но не используются в новых видео.

<details>
<summary>story_data, description_data, prompt_data (deprecated)</summary>

#### story_data
```json
{
  "concept": "Краткое описание идеи видео",
  "hook": "Первые 2 секунды — захват внимания",
  "hook_type": "question | statement | visual | sound",
  "climax": "Кульминационный момент",
  "tone": "comedic | dramatic | inspirational | educational",
  "pacing": "fast | medium | slow",
  "emotional_trigger": "curiosity | surprise | joy | nostalgia",
  "duration": 5
}
```

#### description_data
```json
{
  "scene": "Детальное описание визуальной сцены",
  "setting": "Место действия",
  "lighting": "Тип освещения",
  "color_palette": ["#hex1", "#hex2"],
  "mood": "Атмосфера",
  "key_elements": ["элемент1", "элемент2"],
  "camera_suggestion": "Предложение по ракурсу"
}
```

#### prompt_data
```json
{
  "main_prompt": "Основной промпт для генерации изображения",
  "negative_prompt": "Что исключить из генерации",
  "style_suffix": "Стилистические указания",
  "aspect_ratio": "9:16"
}
```

</details>

### audio_variants[]
```json
[
  {
    "variant_id": 1,
    "url": "https://...",
    "music_style": "upbeat | calm | dramatic",
    "duration": 5
  }
]
```

### publishing_meta
```json
{
  "youtube": {
    "title": "Заголовок для YouTube",
    "description": "Описание",
    "tags": ["tag1", "tag2"]
  },
  "instagram": {
    "caption": "Текст поста",
    "hashtags": ["#tag1", "#tag2"]
  },
  "tiktok": {
    "caption": "Текст",
    "hashtags": ["#tag1"]
  }
}
```

---

## 5. Конфигурация

### Общие поля Project

| Параметр | Тип | Описание |
|----------|-----|----------|
| `name` | string | Название проекта |
| `project_type` | enum | `discover` \| `remix` |
| `platforms` | string[] | Целевые платформы |
| `duration` | int | 5 \| 10 секунд |
| `aspect_ratio` | string | `9:16` \| `16:9` \| `1:1` |
| `variants_config` | json | Сколько вариантов на шаг (MANUAL mode) |

### Discover Project

| Параметр | Тип | Описание |
|----------|-----|----------|
| `system_prompts` | json | Кастомные system prompts для LLM шагов |

**Note:** Discover не использует templates — LLM генерирует креативно на основе `Video.creative_inputs`.

### Remix Project

| Параметр | Тип | Описание |
|----------|-----|----------|
| `source_video_ids` | int[] | Discover videos как источник шаблона |
| `story_template` | json | Шаблон scenario_data с `{placeholders}` |
| `placeholders` | string[] | Список плейсхолдеров: `["dress_color", "car_model"]` |
| `placeholder_suggestions` | json | Предложенные значения: `{dress_color: ["red", "blue"]}` |

### variants_config

Определяет сколько вариантов генерируется за один attempt.
**Применяется только в MANUAL mode. В AUTO всегда 1 вариант.**

```json
{
  "SCENARIO": 1,
  "IMAGE": 3,
  "VIDEO": 1,
  "AUDIO": 1
}
```

**AUTO mode data consistency:**
```
AUTO mode всё равно создаёт полную иерархию:
  WorkflowStep
    └── StepAttempt
          └── Variant (1 шт, auto-selected, auto-approved)

Причины:
- Консистентная модель данных
- Возможность переключить Video в MANUAL и видеть историю
- Единый код path для обоих режимов
```

| Mode | Поведение |
|------|-----------|
| AUTO | 1 вариант, автоматический approve, без пауз |
| MANUAL | N вариантов согласно config, пауза для выбора |

### Уровень Video

| Параметр | Тип | Описание |
|----------|-----|----------|
| `workflow_mode` | enum | `AUTO` \| `MANUAL` |
| `creative_inputs` | json | **Discover:** свободные параметры (theme, mood, etc.) |
| `content_variables` | json | **Remix:** значения для `{placeholders}` |

---

## 6. State Machine

### Video.status

```
                         ┌─────────────────────────────────┐
                         │            (approve)            │
                         ▼                                 │
┌─────────┐    ┌─────────────┐    ┌───────────────────────┴───┐    ┌───────────┐
│ PENDING │───►│ IN_PROGRESS │───►│ AWAITING_APPROVAL         │───►│ COMPLETED │
└─────────┘    └─────────────┘    │ (MANUAL: после каждого    │    └───────────┘
                    ▲      │      │  шага ждёт approve)       │
                    │      │      └───────────────────────────┘
                    │      │                 │
                    │      │                 │ (regenerate)
                    │      ▼                 │
                    │ ┌────────┐             │
                    │ │ FAILED │             │
                    │ └────────┘             │
                    │      │                 │
                    │      └────(retry)──────┤
                    └────────────────────────┘
```

### Переходы статусов

| Из | В | Условие |
|----|---|---------|
| PENDING | IN_PROGRESS | Вызван `/auto-generate-to-video` |
| IN_PROGRESS | AWAITING_APPROVAL | MANUAL mode + шаг завершён |
| IN_PROGRESS | COMPLETED | AUTO mode + все шаги завершены |
| IN_PROGRESS | FAILED | Ошибка генерации (после всех retry) |
| AWAITING_APPROVAL | IN_PROGRESS | User: approve (→ next step) или regenerate |
| AWAITING_APPROVAL | COMPLETED | User: approve последнего шага (AUDIO) |
| FAILED | IN_PROGRESS | User вызвал retry |

### Пример: Discover + MANUAL mode

```
Время   Событие                      Video.status          Video.current_step
─────   ───────                      ────────────          ──────────────────
t0      Start                        PENDING               null
t1      Generate starts              IN_PROGRESS           SCENARIO
t2      SCENARIO готов               AWAITING_APPROVAL     SCENARIO      ← ждём user
t3      User: Approve                IN_PROGRESS           IMAGE         ← сразу генерит
t4      IMAGE готов                  AWAITING_APPROVAL     IMAGE         ← ждём user
t5      User: Approve                IN_PROGRESS           VIDEO         ← сразу генерит
t6      VIDEO готов                  AWAITING_APPROVAL     VIDEO         ← ждём user
t7      User: Approve                IN_PROGRESS           AUDIO         ← сразу генерит
t8      AUDIO готов                  AWAITING_APPROVAL     AUDIO
t9      User: select variant         COMPLETED             AUDIO
```

**Паттерн:**
1. Шаг завершён → `AWAITING_APPROVAL`, `current_step` = этот шаг
2. User approve → `IN_PROGRESS`, `current_step` = следующий шаг (генерация стартует сразу)
3. Повтор до AUDIO → select variant → COMPLETED

### WorkflowStep.status

| Status | Описание |
|--------|----------|
| PENDING | Шаг создан, ожидает выполнения |
| IN_PROGRESS | Генерация идёт |
| AWAITING_APPROVAL | Варианты готовы, ждёт решения user |
| APPROVED | User финализировал шаг |
| FAILED | Ошибка генерации (retry исчерпаны) |

### StepAttempt.status

| Status | Описание |
|--------|----------|
| PENDING | Генерация началась |
| SUCCESS | Генерация успешна, варианты готовы |
| FAILED | Ошибка генерации |

**Выбор варианта** отслеживается через:
- `WorkflowStep.selected_variant_id` — текущий выбранный вариант
- `Variant.is_selected` — флаг на самом варианте

---

## 7. Breakpoints (MANUAL mode)

### Унифицированный workflow (4 шага)
```
SCENARIO ──⏸──► IMAGE ──⏸──► VIDEO ──⏸──► AUDIO
```

Одинаковый для Discover и Remix. Отличие только в логике SCENARIO step.

### Логика
```python
WORKFLOW_STEPS = [SCENARIO, IMAGE, VIDEO, AUDIO]

def should_pause(step_type: StepType, video: Video, project: Project) -> bool:
    if video.workflow_mode == WorkflowMode.AUTO:
        return False
    return step_type in WORKFLOW_STEPS
```

---

## 8. WorkflowStep, Attempts и Variants

### Иерархия

```
WorkflowStep (один на шаг: SCENARIO, IMAGE, VIDEO, AUDIO)
  │
  └── StepAttempt (одна попытка генерации)
        │
        └── Variant (один результат, может быть N штук)
```

**WorkflowStep** — шаг в workflow (SCENARIO, IMAGE, VIDEO, AUDIO)
**StepAttempt** — одна попытка генерации (один API call)
**Variant** — один результат внутри attempt (1 или N в зависимости от настроек)

### Модели

```python
class WorkflowStep:
    id: int
    video_id: int
    step_type: StepType
    status: StepStatus              # PENDING, IN_PROGRESS, AWAITING_APPROVAL, APPROVED, FAILED
    selected_variant_id: int | None # Текущий выбранный вариант
    created_at: datetime

class StepAttempt:
    id: int
    step_id: int                    # FK → WorkflowStep
    attempt_number: int             # 1, 2, 3...
    status: AttemptStatus           # PENDING, SUCCESS, FAILED

    # Lineage: на основе чего сгенерировано
    parent_variant_id: int | None   # Какой вариант взят за основу
    feedback: str | None            # Feedback для улучшения

    started_at: datetime
    completed_at: datetime
    error_message: str | None

class Variant:
    id: int
    attempt_id: int                 # FK → StepAttempt
    variant_number: int             # 1, 2, 3... внутри attempt
    content: JSON                   # {url: "...", metadata: {...}}
    is_selected: bool               # Выбран ли этот вариант
```

### Пример: итеративная доработка IMAGE

```
WorkflowStep #4 (IMAGE):
  status: APPROVED
  selected_variant_id: 5

StepAttempt #1:
  parent_variant_id: null
  feedback: null
  variants:
    ┌───────────┬─────────────────────────┬─────────────┐
    │ variant   │ content                 │ is_selected │
    ├───────────┼─────────────────────────┼─────────────┤
    │ 1         │ {url: "img1.jpg"}       │ false       │
    │ 2         │ {url: "img2.jpg"}       │ false       │ ← был selected
    │ 3         │ {url: "img3.jpg"}       │ false       │
    └───────────┴─────────────────────────┴─────────────┘

StepAttempt #2:
  parent_variant_id: 2              ← На основе img2
  feedback: "сделай ярче"
  variants:
    ┌───────────┬─────────────────────────┬─────────────┐
    │ variant   │ content                 │ is_selected │
    ├───────────┼─────────────────────────┼─────────────┤
    │ 4         │ {url: "img4.jpg"}       │ false       │
    │ 5         │ {url: "img5.jpg"}       │ true        │ ← финальный
    │ 6         │ {url: "img6.jpg"}       │ false       │
    └───────────┴─────────────────────────┴─────────────┘

→ Video.image_url = "img5.jpg"
```

### Workflow внутри шага

```
┌─────────────────────────────────────────────────────────────────┐
│                        IMAGE STEP                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Generate (attempt 1)                                           │
│       ↓                                                         │
│  ┌───────┐ ┌───────┐ ┌───────┐                                 │
│  │ var 1 │ │ var 2 │ │ var 3 │   ← 3 варианта                  │
│  └───────┘ └───────┘ └───────┘                                 │
│                 ↓                                               │
│           [Select]                                              │
│                 ↓                                               │
│  ┌─────────────────────────────────┐                           │
│  │ Selected: var 2                 │                           │
│  │                                 │                           │
│  │ [Approve]  [Refine with feedback]                           │
│  └─────────────────────────────────┘                           │
│                 │                                               │
│     ┌───────────┴───────────┐                                   │
│     ↓                       ↓                                   │
│  [Approve]            [Refine: "сделай ярче"]                   │
│     │                       │                                   │
│     │                       ↓                                   │
│     │              Generate (attempt 2, based on var 2)         │
│     │                       ↓                                   │
│     │              ┌───────┐ ┌───────┐ ┌───────┐               │
│     │              │ var 4 │ │ var 5 │ │ var 6 │               │
│     │              └───────┘ └───────┘ └───────┘               │
│     │                            ↓                              │
│     │                      [Select var 5]                       │
│     │                            ↓                              │
│     │                       [Approve]                           │
│     ↓                            ↓                              │
│  ┌──────────────────────────────────────┐                      │
│  │           STEP APPROVED              │                      │
│  │     Video.image_url = selected       │                      │
│  └──────────────────────────────────────┘                      │
│                      ↓                                          │
└──────────────────────┼──────────────────────────────────────────┘
                       ↓
                 SCENARIO STEP
```

---

## 9. Rollback

### Когда нужен

User прошёл несколько шагов, но хочет вернуться и изменить предыдущий:

```
STORY → DESCRIPTION → PROMPT → IMAGE → SCENARIO → VIDEO
                                                     ↓
                                            "не нравится видео,
                                             хочу другую картинку"
                                                     ↓
                                            ROLLBACK to IMAGE
```

### API

```
POST /workflow/rollback-to/{step_type}
Body: { video_id: int }

Response: {
  video_id: int,
  rolled_back_to: "IMAGE",
  deleted_steps: ["SCENARIO", "VIDEO"],
  status: "awaiting_approval"
}
```

### Логика rollback

```python
def rollback_to(video_id: int, target_step: StepType):
    video = get_video(video_id)

    # 1. Определить шаги для удаления (все ПОСЛЕ target)
    steps_to_delete = get_steps_after(target_step)
    # Например: target=IMAGE → delete [SCENARIO, VIDEO, AUDIO]

    # 2. Удалить WorkflowSteps (attempts и variants каскадно)
    delete_steps(video_id, steps_to_delete)

    # 3. Очистить данные в Video
    for step in steps_to_delete:
        clear_video_field(video, step)  # scenario_data=None, video_url=None...

    # 4. Target step → AWAITING_APPROVAL (сбросить для пересмотра)
    target = get_step(video_id, target_step)
    target.status = AWAITING_APPROVAL
    # selected_variant_id сохраняется — это "текущий выбор"

    # 5. Обновить Video
    video.current_step = target_step
    video.status = AWAITING_APPROVAL
```

**После rollback user может:**
- Выбрать другой вариант из предыдущих attempts
- Regenerate с feedback
- Approve текущий selected_variant и продолжить

### Пример полного сценария

**Исходная ситуация:**
- Discover + MANUAL mode
- 2 итерации STORY (reject → approve)
- 3 итерации IMAGE (reject → reject → approve)
- Дошёл до VIDEO, не нравится

**После rollback to IMAGE:**

```
Video:
  current_step: IMAGE
  status: AWAITING_APPROVAL
  image_url: "attempt3.jpg"      ← пока текущая
  scenario_data: NULL            ← очищено
  video_url: NULL                ← очищено

WorkflowSteps:
  STORY       → APPROVED
  DESCRIPTION → APPROVED
  PROMPT      → APPROVED
  IMAGE       → AWAITING_APPROVAL  ← сброшен для пересмотра
                selected_variant_id: 7 (текущий выбор)
  SCENARIO    → DELETED
  VIDEO       → DELETED

IMAGE StepAttempts (сохранились!):
  attempt 1: SUCCESS  [variant 1, 2, 3]   ← можно выбрать
  attempt 2: SUCCESS  [variant 4, 5, 6]   ← можно выбрать
  attempt 3: SUCCESS  [variant 7, 8, 9]   ← variant 7 текущий
```

**User выбирает вариант из attempt1:**
```
# 1. Получить все варианты шага
GET /workflow/step/{image_step_id}/variants
→ Показывает все варианты из всех attempts

# 2. Выбрать вариант (например, variant_id=1 из attempt1)
POST /workflow/select-variant { step_id: image_step_id, variant_id: 1 }

# 3. Approve и продолжить
POST /workflow/approve-step { step_id: image_step_id }
POST /workflow/auto-generate-to-video { video_id: ... }

→ Video.image_url = "attempt1_variant1.jpg"
→ Продолжить: SCENARIO → VIDEO → AUDIO (с новой картинкой)
```

**Финальная история:**
```
STORY:      2 attempts (выбран variant из attempt 2)
IMAGE:      3 attempts (после rollback выбран variant 1 из attempt 1)
SCENARIO:   1 attempt (создан после rollback)
VIDEO:      1 attempt (создан после rollback)
AUDIO:      1 attempt (финальный)
```

---

## 10. Concurrency Protection

Защита от race conditions при параллельных запросах (два таба, двойной клик).

**Принцип:** Первый запрос выигрывает, остальные отклоняются.

### Video-level Protection

Защита от параллельных вызовов `/auto-generate-to-video` для одного video:

```python
def auto_generate_to_video(video_id: int):
    video = db.query(Video).filter(id=video_id).with_for_update().first()

    # Можно запустить только из определённых статусов
    if video.status == VideoStatus.IN_PROGRESS:
        raise HTTPException(409, "Generation already in progress")

    if video.status == VideoStatus.COMPLETED:
        raise HTTPException(409, "Video already completed")

    # OK: PENDING или AWAITING_APPROVAL
    video.status = VideoStatus.IN_PROGRESS
    db.commit()

    # Запуск background job
    start_generation_job(video_id)
```

### Step-level Protection

Защита операций над конкретным шагом:

```python
def approve_step(step_id: int):
    step = db.query(WorkflowStep).filter(id=step_id).with_for_update().first()

    # Проверка: можно ли approve из текущего статуса?
    if step.status != StepStatus.AWAITING_APPROVAL:
        raise HTTPException(409, f"Cannot approve: step is {step.status}")

    step.status = StepStatus.APPROVED
    db.commit()
```

### Валидные переходы

**Video:**

| Из | Действие | В |
|----|----------|---|
| PENDING | auto-generate | IN_PROGRESS |
| AWAITING_APPROVAL | auto-generate (continue) | IN_PROGRESS |
| IN_PROGRESS | — | ничего (ждать завершения) |
| COMPLETED | — | ничего (workflow завершён) |
| FAILED | retry | IN_PROGRESS |

**WorkflowStep:**

| Из | Действие | В |
|----|----------|---|
| AWAITING_APPROVAL | approve | APPROVED |
| AWAITING_APPROVAL | regenerate | IN_PROGRESS |
| AWAITING_APPROVAL | select-variant | AWAITING_APPROVAL |
| FAILED | retry | IN_PROGRESS |
| IN_PROGRESS | — | ничего (ждать завершения) |

**При конфликте:** `409 Conflict` — frontend показывает "Action already in progress, please refresh".

---

## 11. Error Handling

### Retry Policy

| Service | Max Retries | Backoff | Timeout |
|---------|-------------|---------|---------|
| LLM | 3 | exponential (1s, 2s, 4s) | 30s |
| ImageGen | 2 | exponential (2s, 4s) | 60s |
| VideoGen | 2 | exponential (5s, 10s) | 15min |
| AudioGen | 2 | exponential (2s, 4s) | 60s |

### Generation Timeout

**Backend контролирует timeout.** Если генерация занимает слишком долго:

```python
STEP_TIMEOUT = {
    "STORY": 2 * 60,        # 2 мин
    "DESCRIPTION": 2 * 60,
    "PROMPT": 2 * 60,
    "IMAGE": 5 * 60,        # 5 мин
    "SCENARIO": 2 * 60,
    "VIDEO": 20 * 60,       # 20 мин (VideoGen медленный)
    "AUDIO": 5 * 60,
}

# Background job проверяет
if step.started_at + STEP_TIMEOUT[step.step_type] < now():
    step.status = FAILED
    step.error_message = "Generation timeout"
    video.status = FAILED
```

**Frontend:** просто polling до terminal status (COMPLETED, FAILED, AWAITING_APPROVAL).
Нет client-side timeout — backend гарантирует завершение.

### При ошибке

1. Retry согласно policy
2. Если все retry исчерпаны:
   - `WorkflowStep.status = FAILED`
   - `WorkflowStep.error_message = "..."`
   - `Video.status = FAILED`
3. User может:
   - Retry: `POST /workflow/retry-step` — повтор с теми же параметрами
   - Regenerate: `POST /workflow/regenerate-with-feedback` — новая попытка с изменениями

### При Reject (MANUAL mode)

Reject — это **действие**, не состояние. User может:

1. **Regenerate** — создать новый attempt:
   ```
   POST /workflow/regenerate-with-feedback
   → WorkflowStep.status = IN_PROGRESS
   → Video.status = IN_PROGRESS
   ```

2. **Выбрать другой вариант** — из текущего или предыдущих attempts:
   ```
   POST /workflow/select-variant (другой variant_id)
   → Статусы не меняются, просто selected_variant_id обновляется
   ```

---

## 12. AUDIO Step Details

AUDIO — последний шаг workflow. Использует **унифицированную модель variants** (см. секцию 8).

### Генерация вариантов
- Генерируется **N вариантов** согласно `variants_config.AUDIO` (по умолчанию 3)
- Варианты сохраняются как `Variant` записи в `StepAttempt`
- Каждый вариант: `{url, music_style, duration}`

### Workflow внутри шага

```
Generate (attempt 1)
     ↓
┌──────────┐ ┌──────────┐ ┌──────────┐
│ variant 1│ │ variant 2│ │ variant 3│  ← N вариантов
│  upbeat  │ │   calm   │ │ dramatic │
└──────────┘ └──────────┘ └──────────┘
        ↓
  [Select variant 2]
        ↓
┌─────────────────────────────────────┐
│ Selected: variant 2 (calm)          │
│                                     │
│ [Approve]  [Refine with feedback]   │
└─────────────────────────────────────┘
        │
   ┌────┴────┐
   ↓         ↓
[Approve] [Refine: "более энергично"]
   │         │
   │         ↓
   │    Generate (attempt 2)
   │         ↓
   │    ┌──────────┐ ┌──────────┐ ┌──────────┐
   │    │ variant 4│ │ variant 5│ │ variant 6│
   │    └──────────┘ └──────────┘ └──────────┘
   │              ↓
   │        [Select → Approve]
   ↓              ↓
┌─────────────────────────────────────┐
│           WORKFLOW COMPLETED        │
│  Video.video_with_audio_url = url   │
│  Generate publishing_meta           │
└─────────────────────────────────────┘
```

### Финализация
После approve AUDIO шага:
1. `Video.video_with_audio_url` = URL выбранного варианта
2. **LLM генерирует `publishing_meta`** (titles, descriptions, hashtags для каждой платформы)
3. `Video.status = COMPLETED`

```python
def generate_publishing_meta(video: Video) -> PublishingMeta:
    """LLM генерирует viral-optimized meta для всех платформ."""
    return llm.generate_json(
        prompt="Generate viral titles, descriptions, hashtags",
        context={
            "story": video.story_data,
            "description": video.description_data,
            "platforms": video.project.platforms,  # ["youtube", "instagram", "tiktok"]
        },
        schema=PublishingMetaSchema
    )
```

---

## 13. Publishing Flow

Publishing — **отдельный процесс** после завершения workflow.

### Ключевые правила

1. **N платформ** — YouTube, Instagram, TikTok (можно расширять)
2. **Публикация на каждую платформу независима**
3. **После первой успешной публикации → rollback запрещён**
4. **После публикации можно только обновлять meta**
5. **Auto-retry до успеха**, кроме permanent errors

### Permanent Errors (публикация невозможна)

| Ошибка | Описание |
|--------|----------|
| `NO_AUTH` | Нет авторизации на платформе |
| `ACCOUNT_BANNED` | Аккаунт заблокирован |
| `CONTENT_REJECTED` | Платформа отклонила контент (нарушение правил) |

Все остальные ошибки (network, rate limit, server error) → auto-retry.

### Video.is_published

```python
class Video:
    is_published: bool = False  # True после первой успешной публикации

def publish_to_platform(video_id: int, platform: str):
    result = attempt_publish(video_id, platform)

    if result.status == SUCCESS:
        video.is_published = True  # Блокирует rollback

    return result

def rollback_to(video_id: int, target_step: StepType):
    video = get_video(video_id)

    if video.is_published:
        raise HTTPException(400, "Cannot rollback: video already published")

    # ... стандартная логика rollback
```

### Publishing Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        PUBLISHING FLOW                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Video.status = COMPLETED, is_published = False                 │
│        │                                                        │
│        ▼                                                        │
│  POST /publish/{video_id}                                       │
│  Body: { platform: "youtube" }   ← одна платформа за раз       │
│        │                                                        │
│        ▼                                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Retry loop (до успеха или permanent error):            │   │
│  │    1. Попытка публикации                                │   │
│  │    2. Если transient error → wait → retry               │   │
│  │    3. Если permanent error → FAILED, stop               │   │
│  │    4. Если success → is_published = True                │   │
│  └─────────────────────────────────────────────────────────┘   │
│        │                                                        │
│        ▼                                                        │
│  PublishResult: {                                               │
│    platform: "youtube",                                         │
│    status: "success" | "failed",                                │
│    post_id: "abc123",           # если success                  │
│    url: "https://...",          # если success                  │
│    error_code: "NO_AUTH",       # если failed                   │
│    error_message: "..."         # если failed                   │
│  }                                                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Update Meta (после публикации)

```
PUT /publish/{video_id}/{platform}/meta
Body: {
  title: "New title",
  description: "Updated description",
  tags: ["new", "tags"]
}
```

Обновляет meta на платформе (если платформа поддерживает).

### Metrics Collection

После успешной публикации автоматически создаются задачи сбора метрик:
- 30 минут после публикации
- 1 час
- 24 часа
- 7 дней

---

## 14. API Contract

### Модель выполнения: Async + Polling

Все операции генерации выполняются **асинхронно**:

```
Frontend                                        Backend
   │                                               │
   ├─── POST /workflow/auto-generate-to-video ────►│
   │◄─── 202 Accepted ─────────────────────────────┤  ← Сразу возвращает
   │                                               │
   │                                               │  Background job:
   │                                               │  ├─► SCENARIO генерация
   │                                               │  ├─► IMAGE генерация
   │                                               │  └─► ... (или пауза на MANUAL)
   │                                               │
   ├─── GET /videos/{id} ─────────────────────────►│  ← Polling каждые 3 сек
   │◄─── {status: "in_progress", ...} ─────────────┤
   │                                               │
   ├─── GET /videos/{id} ─────────────────────────►│
   │◄─── {status: "awaiting_approval",             │  ← Готово для approve
   │      current_step: "SCENARIO"} ───────────────┤
   │                                               │
   ├─── POST /workflow/{id}/SCENARIO/approve ─────►│
   │◄─── 200 OK ───────────────────────────────────┤
   │                                               │
   ├─── POST /workflow/auto-generate-to-video ────►│  ← Продолжить workflow
   │◄─── 202 Accepted ─────────────────────────────┤
   │         ...                                   │
```

**Почему async:**
- VideoGen может занять до 15 минут
- Нет риска timeout
- User может закрыть браузер и вернуться
- Масштабируемость (background workers)

### Запуск генерации
```
POST /workflow/auto-generate-to-video
Body: { video_id: int }

Response (202 Accepted): {
  video_id: int,
  status: "in_progress",
  message: "Generation started",
  poll_url: "/videos/{video_id}"
}
```

### Проверка статуса (polling)
```
GET /videos/{video_id}

Response: {
  video_id: int,
  status: "pending" | "in_progress" | "awaiting_approval" | "completed" | "failed",
  current_step: "SCENARIO" | "IMAGE" | "VIDEO" | "AUDIO",
  steps_completed: ["SCENARIO", "IMAGE", ...],

  # Данные шагов (для просмотра)
  scenario_data?: {...},
  image_url?: "...",
  video_url?: "...",
  video_with_audio_url?: "...",

  # Для AWAITING_APPROVAL — информация для UI
  current_step_variants_count: int,  # Сколько вариантов доступно
  selected_variant_id?: int          # Текущий выбранный (если есть)
}
```

### URL Convention

Все операции над шагами используют унифицированный паттерн:

```
/workflow/{video_id}/{step_type}/action
```

**step_type:** `SCENARIO`, `IMAGE`, `VIDEO`, `AUDIO`

---

### Выбор варианта

Выбор варианта как "текущего" для preview. **Content НЕ копируется в Video** — только отмечается selected.

```
POST /workflow/{video_id}/{step_type}/select-variant
Body: {
  variant_id: int    # Для шагов с 1 вариантом — всегда 1
}

Response: {
  step_type: "IMAGE",
  variant_id: int,
  variant_content: {...},
  status: "selected",
  available_actions: ["approve", "refine"]
}
```

**Паттерн использования:**
- Шаг с 1 вариантом (STORY, DESCRIPTION, etc.): UI показывает "Approve/Reject", под капотом `select-variant`
- Шаг с N вариантами (IMAGE, AUDIO): UI показывает выбор из N, потом `select-variant`

---

### Approve шага (финализация)

Финализация шага. **Content копируется в Video** при approve.

```
POST /workflow/{video_id}/{step_type}/approve

Response: {
  step_type: "IMAGE",
  status: "approved",
  next_step?: StepType,        # null если это последний шаг
  video_status: "in_progress" | "completed"
}
```

**При approve происходит:**
1. `WorkflowStep.status = APPROVED`
2. `Video.{field} = selected_variant.content` (копирование данных)
3. Если AUDIO: `Video.status = COMPLETED`, генерация `publishing_meta`

После approve (если не AUDIO): frontend вызывает `/auto-generate-to-video` для продолжения.

---

### Reject шага (опционально)

Reject — действие для аналитики, статус не меняется.

```
POST /workflow/{video_id}/{step_type}/reject
Body: { reason?: string }

Response: {
  step_type: "IMAGE",
  available_actions: ["regenerate", "select_other_variant"],
  previous_variants_count: int
}
```

---

### Regenerate с feedback

Новый attempt на основе выбранного варианта + feedback.

```
POST /workflow/{video_id}/{step_type}/regenerate
Body: {
  variant_id: int,           # На основе какого варианта
  feedback?: string          # Опциональный feedback
}

Response: {
  step_type: "IMAGE",
  attempt_id: int,
  status: "in_progress"
}
```

---

### Retry failed шага

Повтор после ошибки (без feedback).

```
POST /workflow/{video_id}/{step_type}/retry

Response: {
  step_type: "IMAGE",
  attempt_id: int,
  status: "in_progress"
}
```

---

### Получить варианты шага

```
GET /workflow/{video_id}/{step_type}/variants

Response: {
  step_type: "IMAGE",
  current_attempt: {
    attempt_id: int,
    variants: [
      {
        variant_id: int,
        variant_number: int,
        content: {...},
        is_selected: bool
      }
    ]
  },
  previous_attempts: [
    {
      attempt_id: int,
      attempt_number: int,
      feedback: string | null,
      variants: [...]
    }
  ]
}
```

---

### Rollback

```
POST /workflow/{video_id}/rollback-to/{step_type}

Response: {
  video_id: int,
  rolled_back_to: "IMAGE",
  deleted_steps: ["SCENARIO", "VIDEO"],
  status: "awaiting_approval"
}
```

После rollback user может:
- Выбрать другой вариант: `GET .../variants` → `POST .../select-variant`
- Regenerate с feedback
- Approve текущий и продолжить

---

## 15. Frontend Integration

### Polling Strategy

```typescript
async function pollVideoStatus(videoId: number) {
  const POLL_INTERVAL = 3000; // 3 секунды

  while (true) {
    const video = await api.get(`/videos/${videoId}`);

    switch (video.status) {
      case 'pending':
        // Ещё не начали — ждём
        break;

      case 'in_progress':
        // Показать прогресс: video.current_step, video.steps_completed
        updateProgressUI(video);
        break;

      case 'awaiting_approval':
        // Показать результат шага и кнопки approve/reject
        showApprovalUI(video);
        return; // Остановить polling

      case 'completed':
        // Готово — показать финальное видео
        showCompletedUI(video);
        return;

      case 'failed':
        // Показать ошибку и кнопку retry
        showErrorUI(video);
        return;
    }

    await sleep(POLL_INTERVAL);
  }
}
```

### Lifecycle страницы

```
1. User создаёт Video → POST /videos → video_id
2. User выбирает workflow_mode (AUTO/MANUAL)
3. User нажимает "Generate" → POST /workflow/auto-generate-to-video
4. Начинается polling → показываем прогресс
5. При AWAITING_APPROVAL (current_step = "IMAGE"):
   a. GET /workflow/{video_id}/IMAGE/variants → получить варианты
   b. Показать UI (1 вариант → Approve/Reject, N вариантов → выбор)
6. User выбирает вариант → POST /workflow/{video_id}/IMAGE/select-variant
7. User actions:
   - Approve → POST /workflow/{video_id}/IMAGE/approve → POST /workflow/auto-generate-to-video
   - Refine → POST /workflow/{video_id}/IMAGE/regenerate → polling
   - Reject → POST /workflow/{video_id}/IMAGE/reject
8. Повторяем polling
9. При COMPLETED → показываем финальное видео + publish options
```

### UI паттерны по типу шага

```typescript
function renderStepUI(videoId: number, stepType: string, variants: Variant[]) {
  if (variants.length === 1) {
    // Single variant: simplified UI
    return (
      <SingleVariantApproval
        content={variants[0].content}
        onApprove={() => {
          selectVariant(videoId, stepType, variants[0].id);
          approveStep(videoId, stepType);
        }}
        onReject={() => rejectStep(videoId, stepType)}
        onRefine={(feedback) => regenerate(videoId, stepType, variants[0].id, feedback)}
      />
    );
  } else {
    // Multiple variants: selection UI
    return (
      <MultiVariantSelector
        variants={variants}
        onSelect={(variantId) => selectVariant(videoId, stepType, variantId)}
        selectedVariantId={selectedVariantId}
      />
    );
  }
}

// API helpers
const selectVariant = (videoId, stepType, variantId) =>
  api.post(`/workflow/${videoId}/${stepType}/select-variant`, { variant_id: variantId });

const approveStep = (videoId, stepType) =>
  api.post(`/workflow/${videoId}/${stepType}/approve`);

const regenerate = (videoId, stepType, variantId, feedback) =>
  api.post(`/workflow/${videoId}/${stepType}/regenerate`, { variant_id: variantId, feedback });
```

### Возврат на страницу

User может закрыть браузер и вернуться — статус сохранён:
- `IN_PROGRESS` → продолжить polling
- `AWAITING_APPROVAL` → показать approve UI
- `COMPLETED` → показать результат

### WebSocket (future)
```
WS /ws/video/{video_id}
Events: step_started, step_completed, step_failed, workflow_completed
```

---

## 16. Validation (future)

> **Note:** AI-валидация отложена. В текущей версии валидация ограничена проверкой структуры данных.

---

## 17. Checklist валидации целевого состояния

### Базовые сценарии

| Сценарий | Ожидаемый результат |
|----------|---------------------|
| Discover + AUTO | 4 шага (SCENARIO → IMAGE → VIDEO → AUDIO) без пауз → COMPLETED |
| Discover + MANUAL | Пауза после каждого из 4 шагов |
| Remix + AUTO | 4 шага (SCENARIO → IMAGE → VIDEO → AUDIO) без пауз → COMPLETED |
| Remix + MANUAL | Пауза после каждого из 4 шагов |

### SCENARIO step

| Сценарий | Ожидаемый результат |
|----------|---------------------|
| Discover SCENARIO | LLM генерирует scenario_data креативно из story_template + creative_inputs |
| Remix SCENARIO | LLM заполняет {переменные} в story_template → scenario_data |
| Discover vs Remix | Одинаковый output (scenario_data), разный process |

### Unified Variant Model

| Сценарий | Ожидаемый результат |
|----------|---------------------|
| Шаг с 1 вариантом | UI: Approve/Reject, API: `/{video_id}/{step}/select-variant` → `approve` |
| Шаг с N вариантами | UI: выбор из N, API: `select-variant` → `approve` |
| Select → Refine | `select-variant` → `regenerate` → новые N вариантов |
| Итеративная доработка | 3+ attempts с feedback, history сохраняется |

### Error Handling

| Сценарий | Ожидаемый результат |
|----------|---------------------|
| Ошибка на шаге | Auto-retry → при исчерпании → FAILED |
| Timeout на шаге | Backend ставит FAILED после STEP_TIMEOUT |
| Reject в MANUAL | Можно `regenerate` или выбрать из предыдущих вариантов |
| `retry` | Новый attempt без feedback |

### Rollback

| Сценарий | Ожидаемый результат |
|----------|---------------------|
| Rollback to step | Удаляются шаги после target, variants сохраняются |
| Rollback после публикации | **Запрещён** (is_published = true) |
| Выбор другого варианта после rollback | `select-variant` из любого attempt → продолжение |

### Финализация и Publishing

| Сценарий | Ожидаемый результат |
|----------|---------------------|
| AUDIO approve | video_with_audio_url, LLM генерит publishing_meta, status=COMPLETED |
| Первая публикация | is_published = true, rollback заблокирован |
| Publishing failure (transient) | Auto-retry до успеха |
| Publishing failure (permanent) | NO_AUTH/BANNED → FAILED, stop |
| Metrics | Сбор через 30m, 1h, 24h, 7d |
