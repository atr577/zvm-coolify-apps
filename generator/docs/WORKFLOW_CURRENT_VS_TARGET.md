# Workflow: Текущее состояние vs Цель

**Связанные документы:**
- [TARGET_WORKFLOW.md](./TARGET_WORKFLOW.md) — **каноническое описание целевого workflow**
- [WORKFLOW_ANALYSIS.md](./WORKFLOW_ANALYSIS.md) — критический анализ и список issues
- [PLAN_BREAKPOINTS_SYSTEM.md](./PLAN_BREAKPOINTS_SYSTEM.md) — план исправления workflow_mode

---

## 1. Создание проекта

### Текущий flow

```
User                          Frontend                      Backend
  │                              │                             │
  ├─── Заполняет форму ─────────►│                             │
  │    - name                    │                             │
  │    - story_template          │                             │
  │    - platforms               │                             │
  │    - duration                │                             │
  │    - workspace (optional)    │                             │
  │                              │                             │
  │                              ├── POST /projects ──────────►│
  │                              │                             │
  │                              │      ┌─────────────────────┐│
  │                              │      │ ⚠️ ПРОБЛЕМА:        ││
  │                              │      │ Если workspace не   ││
  │                              │      │ указан — берёт      ││
  │                              │      │ первый молча        ││
  │                              │      └─────────────────────┘│
  │                              │                             │
  │◄─────── Project created ─────┤◄────────────────────────────┤
  │                              │                             │
```

### Целевой flow

```
User                          Frontend                      Backend
  │                              │                             │
  ├─── Заполняет форму ─────────►│                             │
  │    - name                    │                             │
  │    - story_template          │                             │
  │    - platforms               │                             │
  │    - duration                │                             │
  │    - workspace (REQUIRED) ◄──┼── Валидация ────────────────┤
  │                              │                             │
  │                              ├── POST /projects ──────────►│
  │                              │                             │
  │                              │   ✅ workspace_id required  │
  │                              │   ✅ system_prompts validated│
  │                              │                             │
  │◄─── Project created ─────────┤◄────────────────────────────┤
  │     + показать workspace     │                             │
```

---

## 2. Создание видео

### Текущий flow

```
User                          Frontend                      Backend
  │                              │                             │
  ├─── Click "New Video" ───────►│                             │
  │                              │                             │
  │                              ├── GET /ai/generate-variants─►│
  │                              │                             │
  │         ┌────────────────────┼─────────────────────────────┤
  │         │ 🔴 CRITICAL:       │                             │
  │         │ Endpoint НЕ        │    ❌ 404 Not Found         │
  │         │ существует!        │                             │
  │         └────────────────────┼─────────────────────────────┤
  │                              │                             │
  │    ∞ Loading spinner... ◄────┤   (никогда не завершается)  │
  │                              │                             │
```

### Целевой flow

```
User                          Frontend                      Backend
  │                              │                             │
  ├─── Click "New Video" ───────►│                             │
  │                              │                             │
  │                              ├── POST /workflow/variants ──►│
  │                              │    {project_id, count: 4}   │
  │                              │                             │
  │                              │◄── [{variant_1}, {variant_2}]│
  │                              │                             │
  │◄─── Показать 4 варианта ─────┤                             │
  │                              │                             │
  ├─── Выбрать вариант ─────────►│                             │
  │                              │                             │
  │                              ├── POST /videos ─────────────►│
  │                              │    {content_variables: ...}  │
  │                              │                             │
  │◄─── Video created ───────────┤◄────────────────────────────┤
```

---

## 3. Workflow генерации

> **Целевое описание:** См. [TARGET_WORKFLOW.md](./TARGET_WORKFLOW.md)
> - Discover: 7 шагов (Story → Description → Prompt → Image → Scenario → Video → Audio)
> - Remix: 3 шага (Image → Video → Audio)

### Текущий flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ТЕКУЩИЙ WORKFLOW                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────┐    ┌─────────────┐    ┌────────┐    ┌─────────┐               │
│  │ STORY   │───►│ DESCRIPTION │───►│ PROMPT │───►│  IMAGE  │               │
│  │ Step 1  │    │   Step 2    │    │ Step 3 │    │ Step 4  │               │
│  └─────────┘    └─────────────┘    └────────┘    └─────────┘               │
│       │                                               │                     │
│       │         ⚠️ Статусы запутаны:                  │                     │
│       │         Video.current_step = STORY            │                     │
│       │         Video.status = IN_PROGRESS            │                     │
│       │         (два enum, нет связи)                 │                     │
│       │                                               ▼                     │
│       │                                         ┌──────────┐                │
│       │                                         │ SCENARIO │                │
│       │                                         │  Step 5  │                │
│       │                                         └──────────┘                │
│       │                                               │                     │
│       │    ⚠️ Комментарии врут:                       │                     │
│       │    "Stage 5" написано над Image               │                     │
│       │                                               ▼                     │
│       │                                         ┌──────────┐                │
│       │                                         │  VIDEO   │                │
│       │                                         │  Step 6  │                │
│       │                                         └──────────┘                │
│       │                                               │                     │
│       │                                               ▼                     │
│       │         ┌─────────────────────────────────────────────────┐        │
│       │         │ ⚠️ ПРОБЛЕМА: Audio генерится ДО approve Video   │        │
│       │         │    В MANUAL mode это waste of compute           │        │
│       │         └─────────────────────────────────────────────────┘        │
│       │                                               │                     │
│       │                                               ▼                     │
│       │                                         ┌──────────┐                │
│       │                                         │  AUDIO   │                │
│       │                                         │  Step 7  │                │
│       │                                         └──────────┘                │
│       │                                               │                     │
│       │    ⚠️ generate_meta вызывается               │                     │
│       │       И в select_audio_variant               │                     │
│       │       И в отдельном endpoint                 ▼                     │
│       │                                         ┌────────────┐              │
│       │                                         │ ADAPTATION │              │
│       │                                         │   Step 8   │              │
│       │                                         └────────────┘              │
│       │                                               │                     │
│       │                                               ▼                     │
│       │                                         ┌────────────┐              │
│       │         ⚠️ Publishing вне workflow      │ PUBLISHING │              │
│       │            Отдельная модель             │   Step 9   │              │
│       │            Нет WorkflowStep             └────────────┘              │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ WorkflowStep.content = {} (пустой)                                  │   │
│  │ Все данные в Video model: story_data, image_url, video_url...      │   │
│  │ ⚠️ Нельзя отследить что было на каждом шаге                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Целевой flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ЦЕЛЕВОЙ WORKFLOW                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────┐    ┌─────────────┐    ┌────────┐    ┌─────────┐               │
│  │ STORY   │───►│ DESCRIPTION │───►│ PROMPT │───►│  IMAGE  │               │
│  │ Step 1  │    │   Step 2    │    │ Step 3 │    │ Step 4  │               │
│  └────┬────┘    └──────┬──────┘    └───┬────┘    └────┬────┘               │
│       │                │               │              │                     │
│       ▼                ▼               ▼              ▼                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ ✅ Единый статус: WorkflowStep.status                               │   │
│  │    PENDING → IN_PROGRESS → AWAITING_APPROVAL → APPROVED             │   │
│  │                                                                      │   │
│  │ ✅ Video.current_step только указывает ГДЕ мы                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                      │                      │
│                                                      ▼                      │
│                                                ┌──────────┐                 │
│                                                │ SCENARIO │                 │
│                                                │  Step 5  │                 │
│                                                └────┬─────┘                 │
│                                                     │                       │
│                                                     ▼                       │
│                                                ┌──────────┐                 │
│                                                │  VIDEO   │                 │
│                                                │  Step 6  │                 │
│                                                └────┬─────┘                 │
│                                                     │                       │
│  ┌──────────────────────────────────────────────────┼──────────────────┐   │
│  │ ✅ MANUAL mode: Audio только ПОСЛЕ approve Video │                  │   │
│  │ ✅ AUTO mode: Audio сразу после Video            │                  │   │
│  └──────────────────────────────────────────────────┼──────────────────┘   │
│                                                     ▼                       │
│                                                ┌──────────┐                 │
│                                                │  AUDIO   │                 │
│                                                │  Step 7  │                 │
│                                                └────┬─────┘                 │
│                                                     │                       │
│                                                     ▼                       │
│                                                ┌────────────┐               │
│                                                │ ADAPTATION │               │
│                                                │   Step 8   │               │
│                                                └─────┬──────┘               │
│                                                      │                      │
│  ┌───────────────────────────────────────────────────┼─────────────────┐   │
│  │ ✅ Publishing как WorkflowStep                    │                 │   │
│  │ ✅ Проходит через тот же approve flow            │                 │   │
│  └───────────────────────────────────────────────────┼─────────────────┘   │
│                                                      ▼                      │
│                                                ┌────────────┐               │
│                                                │ PUBLISHING │               │
│                                                │   Step 9   │               │
│                                                └────────────┘               │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ ✅ WorkflowStep.content = {полные данные шага}                      │   │
│  │ ✅ Video model хранит только ТЕКУЩЕЕ состояние                      │   │
│  │ ✅ Можно откатить на любой шаг                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Публикация

### Текущий flow

```
User                          Frontend                      Backend
  │                              │                             │
  ├─── Click "Publish" ─────────►│                             │
  │    (одна платформа)          │                             │
  │                              │                             │
  │                              ├── POST /publish/youtube ───►│
  │                              │                             │
  │                              │    ┌───────────────────────┐│
  │                              │    │ ✅ Проверяет existing ││
  │                              │    │    → update или insert││
  │                              │    │                       ││
  │                              │    │ ✅ Устанавливает      ││
  │                              │    │    thumbnail          ││
  │                              │    └───────────────────────┘│
  │                              │                             │
  │◄─── Published ───────────────┤◄────────────────────────────┤
  │                              │                             │
  │    ⚠️ Нужно повторить        │                             │
  │       для каждой платформы   │                             │
  │                              │                             │
  ├─── Click "Publish" ─────────►│                             │
  │    (Instagram)               ├── POST /publish/instagram ─►│
  │                              │                             │
  ├─── Click "Publish" ─────────►│                             │
  │    (TikTok)                  ├── POST /publish/tiktok ────►│
  │                              │                             │
```

### Целевой flow

```
User                          Frontend                      Backend
  │                              │                             │
  ├─── Click "Publish All" ─────►│                             │
  │    ☑ YouTube                 │                             │
  │    ☑ Instagram               │                             │
  │    ☑ TikTok                  │                             │
  │                              │                             │
  │                              ├── POST /publish/batch ─────►│
  │                              │    {platforms: [...]}       │
  │                              │                             │
  │                              │    ┌───────────────────────┐│
  │                              │    │ ✅ Параллельная       ││
  │                              │    │    публикация         ││
  │                              │    │                       ││
  │                              │    │ ✅ Partial success    ││
  │                              │    │    handling           ││
  │                              │    └───────────────────────┘│
  │                              │                             │
  │◄─── Results per platform ────┤◄────────────────────────────┤
  │     ✅ YouTube: published    │                             │
  │     ✅ Instagram: published  │                             │
  │     ❌ TikTok: rate limited  │                             │
```

---

## 5. Аналитика

### Текущий flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ТЕКУЩАЯ АНАЛИТИКА                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  User                          Frontend                      Backend        │
│    │                              │                             │           │
│    ├─── Open Analytics ──────────►│                             │           │
│    │                              │                             │           │
│    │                              ├── GET /metrics/leaderboard─►│           │
│    │                              │                             │           │
│    │       ┌──────────────────────┼─────────────────────────────┤           │
│    │       │ 🔴 CRITICAL:         │                             │           │
│    │       │ Нет проверки user!   │   Returns ALL videos       │           │
│    │       │ Видишь чужие видео   │   from ALL users           │           │
│    │       └──────────────────────┼─────────────────────────────┤           │
│    │                              │                             │           │
│    │                              │◄── [{video_id, views, ...}] │           │
│    │                              │                             │           │
│    │       ┌──────────────────────┼─────────────────────────────┤           │
│    │       │ ⚠️ N+1 queries:      │                             │           │
│    │       │ Для каждого video    │                             │           │
│    │       │ отдельный fetch      │                             │           │
│    │       └──────────────────────┼─────────────────────────────┤           │
│    │                              │                             │           │
│    │                              ├── GET /videos/1 ────────────►│           │
│    │                              ├── GET /videos/2 ────────────►│           │
│    │                              ├── GET /videos/3 ────────────►│           │
│    │                              │   ...N requests...          │           │
│    │                              │                             │           │
│    │◄─── Show leaderboard ────────┤                             │           │
│    │                              │                             │           │
│    │       ┌──────────────────────┼─────────────────────────────┤           │
│    │       │ ⚠️ Engagement rate   │                             │           │
│    │       │ ×100 дважды в коде   │                             │           │
│    │       └──────────────────────┘                             │           │
│    │                                                            │           │
│    ├─── Add manual metrics ──────►│                             │           │
│    │                              │                             │           │
│    │                              ├── POST /metrics/video/X ───►│           │
│    │                              │                             │           │
│    │       ┌──────────────────────┼─────────────────────────────┤           │
│    │       │ 🔴 CRITICAL:         │                             │           │
│    │       │ Нет проверки owner!  │   Accepts ANY video_id     │           │
│    │       │ Можно подделать      │   from ANY user            │           │
│    │       │ чужие метрики        │                             │           │
│    │       └──────────────────────┼─────────────────────────────┤           │
│    │                              │                             │           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Целевой flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ЦЕЛЕВАЯ АНАЛИТИКА                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  User                          Frontend                      Backend        │
│    │                              │                             │           │
│    ├─── Open Analytics ──────────►│                             │           │
│    │                              │                             │           │
│    │                              ├── GET /metrics/leaderboard─►│           │
│    │                              │    + Auth header            │           │
│    │                              │                             │           │
│    │                              │    ┌───────────────────────┐│           │
│    │                              │    │ ✅ Фильтр по          ││           │
│    │                              │    │    workspace_ids      ││           │
│    │                              │    │                       ││           │
│    │                              │    │ ✅ Include video      ││           │
│    │                              │    │    titles in response ││           │
│    │                              │    └───────────────────────┘│           │
│    │                              │                             │           │
│    │                              │◄── [{video_id, title,       │           │
│    │                              │      views, ...}]           │           │
│    │                              │     (1 запрос, всё сразу)   │           │
│    │                              │                             │           │
│    │◄─── Show MY leaderboard ─────┤                             │           │
│    │                              │                             │           │
│    ├─── Add manual metrics ──────►│                             │           │
│    │                              │                             │           │
│    │                              ├── POST /metrics/video/X ───►│           │
│    │                              │    + Auth header            │           │
│    │                              │                             │           │
│    │                              │    ┌───────────────────────┐│           │
│    │                              │    │ ✅ verify_ownership() ││           │
│    │                              │    │    перед сохранением  ││           │
│    │                              │    └───────────────────────┘│           │
│    │                              │                             │           │
│    │◄─── Metrics saved ───────────┤◄────────────────────────────┤           │
│    │                              │                             │           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Сводная таблица проблем

| Этап | Проблема | Severity | Целевое решение |
|------|----------|----------|-----------------|
| **Проект** | Silent workspace default | MEDIUM | Required field + confirmation |
| **Видео** | Variant endpoint не существует | CRITICAL | Создать POST /workflow/variants |
| **Workflow** | **workflow_mode не работает** | HIGH | Система breakpoints |
| **Workflow** | Статусы запутаны | MEDIUM | Один source of truth |
| **Workflow** | Audio до approve | HIGH | Gate by previous step |
| **Workflow** | Дубликат generate_meta | HIGH | Убрать из select_audio |
| **Workflow** | Publishing вне workflow | MEDIUM | Оставить отдельным flow |
| **Публикация** | Нет batch publish | LOW | POST /publish/batch |
| **Аналитика** | Нет auth в metrics | CRITICAL | verify_ownership() |
| **Аналитика** | Leaderboard без фильтра | CRITICAL | Filter by workspace |
| **Аналитика** | N+1 queries | MEDIUM | Include titles in response |
| **Аналитика** | Engagement ×100 дважды | HIGH | Fix calculation |

---

## 7. Приоритеты исправлений

```
WEEK 1: Security
├── [ ] Auth в metrics endpoints
├── [ ] Фильтр leaderboard по workspace
└── [ ] verify_ownership для всех metrics операций

WEEK 2: Broken Features
├── [ ] Создать variant generation endpoint
├── [ ] Fix engagement rate calculation
├── [ ] Убрать дубликат generate_meta
└── [ ] Починить workflow_mode (breakpoints) ← см. PLAN_BREAKPOINTS_SYSTEM.md

WEEK 3: Cleanup
├── [ ] Унифицировать статусы
├── [ ] N+1 fix в Analytics
└── [ ] Удалить deprecated поля

FUTURE: Enhancements
├── [ ] Batch publish
└── [ ] Rollback шагов
```

> **Целевая архитектура:** См. [TARGET_WORKFLOW.md](./TARGET_WORKFLOW.md)

---

## 8. Режимы работы: project_type и workflow_mode

### Фактическая реализация (по коду)

Система имеет **два параметра**, но они работают НЕ так, как можно ожидать:

---

### 8.1 project_type (на уровне Project)

Определяет **какие шаги** выполняются:

| Type | Путь | Описание |
|------|------|----------|
| **discover** | Story → Description → Prompt → Image → Scenario → Video → Audio | Полный workflow |
| **remix** | Template → Image → Video → Audio | Пропускает текстовую генерацию |

**Где задаётся:** `Project.project_type` в ProjectForm.tsx

**Код orchestrator.py:129-140:**
```python
is_remix = self.project.project_type == "remix"
if is_remix:
    return await self.run_remix_workflow()
else:
    return await self.run_discover_workflow()
```

---

### 8.2 workflow_mode (на уровне Video)

**⚠️ ВАЖНО: Работает НЕ так, как описано в UI**

| Mode | Что написано в UI | Что реально происходит |
|------|------------------|------------------------|
| **AUTO** | "Все шаги автоматически" | Orchestrator запускает все шаги подряд |
| **MANUAL** | "Approve каждого шага" | То же самое! Orchestrator НЕ проверяет mode |

**Где задаётся:**
- Discover: выбор в CreateVideo.tsx (AUTO/MANUAL selector)
- Remix: **НЕТ ВЫБОРА** — захардкожено `AUTO` (CreateVideo.tsx:17)

```tsx
// CreateVideo.tsx:17
const [workflowMode, setWorkflowMode] = useState<WorkflowMode>('AUTO')

// CreateVideo.tsx:104-106 — selector только для discover
{project.project_type !== 'remix' && (
  // показать AUTO/MANUAL selector
)}
```

**Где workflow_mode РЕАЛЬНО используется:**
- Только в `approval.py` при ручном approve шага
- НЕ в orchestrator при генерации

```python
# approval.py:159 — при IMAGE approval
if self.video.workflow_mode == WorkflowMode.AUTO:
    return {"continue_workflow": True}  # Продолжить автоматически

# approval.py:179 — при других approvals
if self.video.workflow_mode == WorkflowMode.MANUAL:
    # Создать next step с PENDING статусом
```

---

### 8.3 require_image_approval (LEGACY — будет удалено)

> **⚠️ DEPRECATED:** Будет заменено системой breakpoints.
> См. [PLAN_BREAKPOINTS_SYSTEM.md](./PLAN_BREAKPOINTS_SYSTEM.md)

**Текущее поведение (до внедрения breakpoints):**

| Флаг | Поведение |
|------|-----------|
| `true` | Orchestrator останавливается после IMAGE шага |
| `false` | Orchestrator продолжает до конца |

**Замена:**
- `require_image_approval=true` → `workflow_mode=MANUAL`
- После миграции поле будет удалено

**Код orchestrator.py:163-173 (текущий):**
```python
if self.project.require_image_approval:
    return WorkflowResult(
        paused_for_approval=True,
        next_action="approve_image"
    )
```

**Код после внедрения breakpoints:**
```python
if self._should_pause(StepType.IMAGE):
    return self._pause_result("Image generated")
```

---

### 8.4 Фактическая матрица поведения

```
                     require_image_approval
                      false           true
              ┌───────────────┬───────────────┐
              │   discover    │   discover    │
              │               │               │
  project     │ Всё подряд    │ Пауза после   │
    type      │ без остановок │ IMAGE         │
              │               │               │
   discover   │ workflow_mode │ workflow_mode │
              │ НЕ влияет!    │ влияет только │
              │               │ на approve    │
              ├───────────────┼───────────────┤
              │    remix      │    remix      │
              │               │               │
    remix     │ Всё подряд    │ Пауза после   │
              │ (всегда AUTO) │ IMAGE         │
              │               │               │
              │ Нет выбора    │ Нет выбора    │
              │ mode в UI     │ mode в UI     │
              └───────────────┴───────────────┘
```

---

### 8.5 Проблема: UI не соответствует реальности

**CreateVideo.tsx для Discover:**
```
┌─────────────────────────────────────────────────────────────────┐
│  Режим генерации:                                               │
│                                                                 │
│  ┌─────────────────────┐  ┌─────────────────────┐              │
│  │ ○ Auto              │  │ ○ Manual            │              │
│  │ Все шаги            │  │ Approve каждого     │  ← ЛОЖЬ!     │
│  │ автоматически       │  │ шага                │              │
│  └─────────────────────┘  └─────────────────────┘              │
│                                                                 │
│  ⚠️ На самом деле MANUAL не останавливает orchestrator!        │
└─────────────────────────────────────────────────────────────────┘
```

**CreateVideo.tsx для Remix:**
```
┌─────────────────────────────────────────────────────────────────┐
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Remix режим: Шаблон → Вариант → Image → Video            │   │
│  │ (без промежуточных шагов)                                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ⚠️ Нет выбора AUTO/MANUAL — всегда AUTO                       │
│  ⚠️ Единственная пауза — require_image_approval на проекте     │
└─────────────────────────────────────────────────────────────────┘
```

---

### 8.6 План исправления: Система Breakpoints

> **Полный план:** [PLAN_BREAKPOINTS_SYSTEM.md](./PLAN_BREAKPOINTS_SYSTEM.md)

**Решение:** Ввести систему breakpoints вместо `require_image_approval`.

| # | Проблема | Решение |
|---|----------|---------|
| 1 | MANUAL mode не работает | Добавить `_should_pause()` в orchestrator |
| 2 | Remix не имеет выбора | Показать selector для всех типов |
| 3 | `require_image_approval` костыль | Удалить, заменить на breakpoints |
| 4 | approval.py мёртвый код | Упростить логику |

**Целевое поведение:**
```
AUTO mode:   Story → Desc → Prompt → Image → Scenario → Video → Audio (без пауз)
MANUAL mode: Story ⏸ Desc ⏸ Prompt ⏸ Image ⏸ Scenario ⏸ Video ⏸ Audio (пауза на каждом)
```

