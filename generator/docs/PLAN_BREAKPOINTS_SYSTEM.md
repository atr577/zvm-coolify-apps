# План: Система Breakpoints для Workflow

**Связанные документы:**
- [TARGET_WORKFLOW.md](./TARGET_WORKFLOW.md) — **каноническое описание целевого workflow**
- [WORKFLOW_ANALYSIS.md](./WORKFLOW_ANALYSIS.md) — полный список issues (Issue #2.4)
- [WORKFLOW_CURRENT_VS_TARGET.md](./WORKFLOW_CURRENT_VS_TARGET.md) — детали текущей реализации (секция 8)

---

## Цель
Сделать AUTO/MANUAL режимы однозначными:
- **AUTO**: все шаги выполняются без остановок
- **MANUAL**: остановка на каждом breakpoint для approve

## Текущие проблемы
1. `workflow_mode` игнорируется в orchestrator
2. Единственная точка паузы — `require_image_approval` (hardcoded)
3. Remix не имеет выбора режима
4. approval.py содержит мёртвый код

---

## Архитектура

### Breakpoints
Определяем точки остановки для MANUAL режима:

```python
# Discover workflow breakpoints
DISCOVER_BREAKPOINTS = [
    StepType.STORY,       # После генерации истории
    StepType.DESCRIPTION, # После описания сцены
    StepType.PROMPT,      # После промпта изображения
    StepType.IMAGE,       # После генерации картинки
    StepType.SCENARIO,    # После сценария
    StepType.VIDEO,       # После генерации видео
    StepType.AUDIO,       # После аудио (выбор варианта)
]

# Remix workflow breakpoints
REMIX_BREAKPOINTS = [
    StepType.IMAGE,       # После генерации картинки
    StepType.VIDEO,       # После генерации видео
    StepType.AUDIO,       # После аудио
]
```

### Логика паузы
```python
async def _should_pause(self, step_type: StepType) -> bool:
    """Check if workflow should pause at this step."""
    if self.video.workflow_mode == WorkflowMode.AUTO:
        return False  # AUTO никогда не останавливается

    breakpoints = REMIX_BREAKPOINTS if self.is_remix else DISCOVER_BREAKPOINTS
    return step_type in breakpoints
```

---

## Файлы для изменения

### 1. `backend/app/services/workflow/orchestrator.py`
**Основные изменения:**

```python
# Добавить в начало файла
DISCOVER_BREAKPOINTS = [StepType.STORY, StepType.DESCRIPTION, ...]
REMIX_BREAKPOINTS = [StepType.IMAGE, StepType.VIDEO, StepType.AUDIO]

class WorkflowOrchestrator:
    def __init__(self, ...):
        ...
        self.is_remix = self.project.project_type == "remix"

    def _should_pause(self, step_type: StepType) -> bool:
        if self.video.workflow_mode == WorkflowMode.AUTO:
            return False
        breakpoints = REMIX_BREAKPOINTS if self.is_remix else DISCOVER_BREAKPOINTS
        return step_type in breakpoints

    async def run_discover_workflow(self) -> WorkflowResult:
        # Step 1: Story
        await self._generate_story()
        if self._should_pause(StepType.STORY):
            return self._pause_result("Story generated", StepType.DESCRIPTION)

        # Step 2: Description
        await self._generate_description()
        if self._should_pause(StepType.DESCRIPTION):
            return self._pause_result("Description generated", StepType.PROMPT)

        # ... и так далее для каждого шага

    def _pause_result(self, message: str, next_step: StepType) -> WorkflowResult:
        self.video.status = WorkflowStatus.AWAITING_APPROVAL
        self.db.commit()
        return WorkflowResult(
            video_id=self.video.id,
            steps_completed=self.steps_completed,
            message=message,
            mode="remix" if self.is_remix else "discover",
            total_time_seconds=self._elapsed_time(),
            paused_for_approval=True,
            next_action=f"approve_{self.video.current_step.value.lower()}"
        )
```

### 2. `backend/app/models/project.py`
**Удалить поле:**
```python
# УДАЛИТЬ:
require_image_approval = Column(Boolean, default=False)
```

### 3. `frontend/src/pages/CreateVideo.tsx`
**Показать selector для Remix тоже:**
```tsx
// БЫЛО:
{project.project_type !== 'remix' && (
  <WorkflowModeSelector ... />
)}

// СТАНЕТ:
<WorkflowModeSelector ... />  // Для всех типов проектов
```

### 4. `frontend/src/components/ProjectForm.tsx`
**Удалить checkbox:**
```tsx
// УДАЛИТЬ секцию с require_image_approval (строки 248-262)
```

### 5. `backend/app/services/workflow/approval.py`
**Упростить:**
```python
# УДАЛИТЬ специальную логику _handle_image_approval для AUTO mode
# Оставить только переход к следующему шагу

def _handle_image_approval(self) -> Dict[str, Any] | None:
    # Просто переход к следующему шагу
    return self._handle_default_approval()
```

### 6. `backend/app/schemas/project.py`
**Удалить поле:**
```python
# УДАЛИТЬ из ProjectCreate и ProjectUpdate:
require_image_approval: Optional[bool] = False
```

---

## Миграция базы данных

```bash
# Создать миграцию для удаления require_image_approval
alembic revision --autogenerate -m "remove require_image_approval field"
alembic upgrade head
```

---

## Порядок изменений

1. **Backend orchestrator** — добавить breakpoints и _should_pause()
2. **Backend approval.py** — упростить, убрать AUTO/MANUAL специфику
3. **Backend schemas** — удалить require_image_approval
4. **Backend models** — удалить require_image_approval
5. **Frontend CreateVideo** — показать selector для Remix
6. **Frontend ProjectForm** — удалить checkbox
7. **Миграция БД** — удалить колонку

---

## Проверка

1. **Discover + AUTO**: создать видео → должно пройти все шаги без остановок
2. **Discover + MANUAL**: создать видео → должно останавливаться после каждого шага
3. **Remix + AUTO**: создать видео → Image → Video → Audio без остановок
4. **Remix + MANUAL**: создать видео → остановка после Image, Video, Audio

---

## Риски

- **Существующие проекты с require_image_approval=True** — миграция (см. ниже)
- **Тесты** — обновить если есть тесты на require_image_approval

---

## Deprecated шаги

| Шаг | Статус | Причина |
|-----|--------|---------|
| **ADAPTATION** | Deprecated | Функционал merged с audio selection |
| **PUBLISHING** | Не WorkflowStep | Отдельный flow после завершения workflow |

**Действие:** Не включать в BREAKPOINTS списки.

---

## Frontend интеграция

### После approve в MANUAL mode

```
Frontend                              Backend
   │                                     │
   ├─── POST /approve-step ─────────────►│
   │    {step_id, approved: true}        │
   │                                     │
   │◄─── {status: "approved"} ───────────┤
   │                                     │
   ├─── POST /auto-generate-to-video ───►│  ← Продолжить workflow
   │                                     │
   │◄─── {paused_for_approval: true/false}│
   │                                     │
```

**Изменение:** Убрать флаг `continue_workflow` — frontend всегда вызывает `/auto-generate-to-video` после approve.

### UI для MANUAL mode

```tsx
// VideoDetail.tsx — показать approve/reject кнопки
{video.status === 'AWAITING_APPROVAL' && (
  <ApproveRejectButtons
    onApprove={() => approveMutation.mutate()}
    onReject={() => rejectMutation.mutate()}
  />
)}
```

---

## Audio variants

Audio — последний breakpoint. После него:

1. Показать варианты аудио пользователю
2. Пользователь выбирает вариант
3. `POST /workflow/select-audio-variant`
4. `video.status = COMPLETED`

```
AUDIO шаг
    │
    ▼
paused_for_approval=True (MANUAL) или сразу варианты (AUTO)
    │
    ▼
Frontend показывает audio_variants
    │
    ▼
User выбирает
    │
    ▼
POST /select-audio-variant
    │
    ▼
video.status = COMPLETED
```

---

## Миграция данных

### Проекты с require_image_approval=True

```sql
-- Вариант 1: Установить MANUAL на все новые видео этих проектов
-- (реализовать в коде при создании видео)

-- Вариант 2: Добавить default_workflow_mode на Project
ALTER TABLE projects ADD COLUMN default_workflow_mode VARCHAR(10) DEFAULT 'AUTO';

UPDATE projects
SET default_workflow_mode = 'MANUAL'
WHERE require_image_approval = TRUE;
```

### Существующие видео

```sql
-- Видео без workflow_mode обрабатывать как AUTO
UPDATE videos
SET workflow_mode = 'AUTO'
WHERE workflow_mode IS NULL;
```

### После миграции

```sql
-- Удалить колонку (после проверки)
ALTER TABLE projects DROP COLUMN require_image_approval;
```

---

## Чеклист внедрения

- [ ] Добавить BREAKPOINTS константы в orchestrator.py
- [ ] Добавить `_should_pause()` метод
- [ ] Обновить `run_discover_workflow()` с проверками паузы
- [ ] Обновить `run_remix_workflow()` с проверками паузы
- [ ] Упростить approval.py (убрать AUTO/MANUAL специфику)
- [ ] Показать selector для Remix в CreateVideo.tsx
- [ ] Убрать checkbox require_image_approval из ProjectForm.tsx
- [ ] Удалить require_image_approval из schemas
- [ ] Миграция БД: default_workflow_mode
- [ ] Миграция БД: удалить require_image_approval
- [ ] Тесты: Discover + AUTO
- [ ] Тесты: Discover + MANUAL
- [ ] Тесты: Remix + AUTO
- [ ] Тесты: Remix + MANUAL
