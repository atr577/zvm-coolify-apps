# Implementation Plan: Workflow Migration

**Цель:** Мигрировать с текущего состояния на TARGET_WORKFLOW.md

**Связанные документы:**
- [WORKFLOW_ANALYSIS.md](./WORKFLOW_ANALYSIS.md) — текущее состояние + известные баги
- [TARGET_WORKFLOW.md](./TARGET_WORKFLOW.md) — целевая архитектура

---

## Принципы

1. **Security first** — критические уязвимости до любых фич
2. **Fix before build** — починить сломанное до новых фич
3. **Feature flags** — постепенный rollout, возможность отката
4. **Tests first** — покрыть тестами перед рефакторингом

---

## Phase 0: Security (CRITICAL)

> **Источник:** [WORKFLOW_ANALYSIS.md](./WORKFLOW_ANALYSIS.md) секция 1

**Блокер:** Нельзя начинать миграцию пока есть security holes.

| # | Задача | Файл | Effort | Детали |
|---|--------|------|--------|--------|
| 0.1 | Auth в metrics endpoints | `backend/app/api/metrics.py:36-89` | 2h | Добавить `current_user` + `verify_ownership()` |
| 0.2 | Фильтр leaderboard по workspace | `metrics.py` + `Analytics.tsx` | 2h | Передавать workspace_ids в query |
| 0.3 | Ownership check при добавлении метрик | `metrics.py:36` | 1h | `verify_video_ownership()` как в publishing.py |

**Acceptance criteria:**
- [ ] Нельзя добавить метрики к чужому video
- [ ] Leaderboard показывает только свои видео
- [ ] 403 при попытке доступа к чужим данным

**Rollback:** Нет (security fix, не откатываем)

---

## Phase 1: Fix Broken Features

> **Источник:** [WORKFLOW_ANALYSIS.md](./WORKFLOW_ANALYSIS.md) секция 2

**Цель:** Починить что сломано сейчас.

| # | Задача | Файл | Effort | Детали |
|---|--------|------|--------|--------|
| 1.1 | Variant endpoint 404 | `CreateVideo.tsx:26` | 4h | Удалить или создать endpoint |
| 1.2 | Engagement rate ×100 bug | `metrics.py:32` | 30m | Убрать двойное умножение |
| 1.3 | Дубликат generate_meta | `workflow.py:265,288` | 30m | Оставить только в одном месте |
| 1.4 | Audio до approve video | `workflow.py` | 1h | Gate by previous step status |

**Acceptance criteria:**
- [ ] CreateVideo не зависает
- [ ] Engagement rate корректный
- [ ] publishing_meta генерится один раз
- [ ] Audio не генерится до approve VIDEO

**Rollback:** Git revert отдельных commits

---

## Phase 2: Data Model (Variant Hierarchy)

> **Источник:** [TARGET_WORKFLOW.md](./TARGET_WORKFLOW.md) секция 8

**Цель:** Создать StepAttempt → Variant иерархию.

### 2.1 Создание моделей

| # | Задача | Файл | Effort |
|---|--------|------|--------|
| 2.1.1 | Создать StepAttempt model | `backend/app/models/step_attempt.py` | 2h |
| 2.1.2 | Создать Variant model | `backend/app/models/variant.py` | 2h |
| 2.1.3 | Добавить WorkflowStep.selected_variant_id | `backend/app/models/workflow_step.py` | 30m |
| 2.1.4 | Добавить Video.is_published | `backend/app/models/video.py` | 30m |
| 2.1.5 | Alembic migration | `backend/alembic/versions/` | 1h |

**Модели:**

```python
# step_attempt.py
class StepAttempt(Base):
    __tablename__ = "step_attempts"

    id = Column(Integer, primary_key=True)
    step_id = Column(Integer, ForeignKey("workflow_steps.id"))
    attempt_number = Column(Integer, default=1)
    status = Column(SQLEnum(AttemptStatus))  # PENDING, SUCCESS, FAILED
    parent_variant_id = Column(Integer, ForeignKey("variants.id"), nullable=True)
    feedback = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

# variant.py
class Variant(Base):
    __tablename__ = "variants"

    id = Column(Integer, primary_key=True)
    attempt_id = Column(Integer, ForeignKey("step_attempts.id"))
    variant_number = Column(Integer, default=1)
    content = Column(JSON)
    is_selected = Column(Boolean, default=False)
```

### 2.2 Feature Flag

```python
# backend/app/core/config.py
USE_VARIANT_MODEL = env.bool("USE_VARIANT_MODEL", False)

# backend/app/services/workflow/base.py
if settings.USE_VARIANT_MODEL:
    # Новый код: создаём StepAttempt + Variant
    attempt = create_attempt(step)
    variant = create_variant(attempt, content)
else:
    # Старый код: пишем в Video напрямую
    setattr(self.video, self.content_field, content)
```

### 2.3 Миграция существующих данных

```python
# migration script
def migrate_existing_data():
    for video in db.query(Video).all():
        for step in video.workflow_steps:
            # Создать attempt
            attempt = StepAttempt(
                step_id=step.id,
                attempt_number=1,
                status=AttemptStatus.SUCCESS
            )
            db.add(attempt)

            # Создать variant из данных Video
            content = get_video_content_for_step(video, step.step_type)
            if content:
                variant = Variant(
                    attempt_id=attempt.id,
                    variant_number=1,
                    content=content,
                    is_selected=True
                )
                db.add(variant)
                step.selected_variant_id = variant.id

    db.commit()
```

**Effort:** 8h total

**Acceptance criteria:**
- [ ] Модели созданы и migration прошла
- [ ] Feature flag работает
- [ ] Старые данные мигрированы
- [ ] Новые генерации создают Variant записи

**Rollback:**
1. `USE_VARIANT_MODEL=false`
2. При необходимости: rollback migration

---

## Phase 3: Breakpoints System

> **Источник:** [TARGET_WORKFLOW.md](./TARGET_WORKFLOW.md) секция 7

**Цель:** workflow_mode работает корректно.

| # | Задача | Файл | Effort |
|---|--------|------|--------|
| 3.1 | Добавить `_should_pause()` | `orchestrator.py` | 2h |
| 3.2 | Интегрировать в workflow loop | `orchestrator.py` | 2h |
| 3.3 | Удалить require_image_approval | `models/project.py` + migration | 1h |
| 3.4 | Показать mode selector для Remix | `CreateVideo.tsx` | 1h |

**Код:**

```python
# orchestrator.py
def _should_pause(self, step_type: StepType) -> bool:
    if self.video.workflow_mode == WorkflowMode.AUTO:
        return False

    if self.project.project_type == "remix":
        return step_type in [StepType.IMAGE, StepType.VIDEO, StepType.AUDIO]
    else:
        return True  # Все шаги в Discover

async def run_step(self, step_type: StepType):
    # ... generate content ...

    if self._should_pause(step_type):
        self.video.status = VideoStatus.AWAITING_APPROVAL
        return WorkflowResult(paused=True, step=step_type)

    # AUTO: continue to next step
```

**Effort:** 6h total

**Acceptance criteria:**
- [ ] MANUAL mode паузит после каждого шага
- [ ] AUTO mode идёт до конца без пауз
- [ ] Remix показывает выбор режима
- [ ] require_image_approval удалён

**Rollback:** Feature flag `USE_NEW_BREAKPOINTS`

---

## Phase 4: API Unification

> **Источник:** [TARGET_WORKFLOW.md](./TARGET_WORKFLOW.md) секция 14

**Цель:** Унифицированный API pattern.

| # | Задача | Файл | Effort |
|---|--------|------|--------|
| 4.1 | Создать новый router | `backend/app/api/workflow_v2.py` | 4h |
| 4.2 | Endpoint: select-variant | `workflow_v2.py` | 1h |
| 4.3 | Endpoint: approve | `workflow_v2.py` | 1h |
| 4.4 | Endpoint: regenerate | `workflow_v2.py` | 1h |
| 4.5 | Endpoint: variants (GET) | `workflow_v2.py` | 1h |
| 4.6 | Endpoint: rollback-to | `workflow_v2.py` | 2h |
| 4.7 | Обновить frontend | `frontend/src/api/workflow.ts` | 4h |
| 4.8 | Deprecate старые endpoints | `workflow.py` | 30m |

**API Pattern:**

```python
# workflow_v2.py
router = APIRouter(prefix="/workflow")

@router.post("/{video_id}/{step_type}/select-variant")
async def select_variant(video_id: int, step_type: StepType, body: SelectVariantRequest):
    ...

@router.post("/{video_id}/{step_type}/approve")
async def approve_step(video_id: int, step_type: StepType):
    ...

@router.post("/{video_id}/{step_type}/regenerate")
async def regenerate(video_id: int, step_type: StepType, body: RegenerateRequest):
    ...

@router.get("/{video_id}/{step_type}/variants")
async def get_variants(video_id: int, step_type: StepType):
    ...

@router.post("/{video_id}/rollback-to/{target_step}")
async def rollback_to(video_id: int, target_step: StepType):
    ...
```

**Effort:** 14h total

**Acceptance criteria:**
- [ ] Новые endpoints работают
- [ ] Frontend использует новые endpoints
- [ ] Старые endpoints помечены deprecated

**Rollback:** Оставить старые endpoints, откатить frontend

---

## Phase 5: Publishing & Rollback

> **Источник:** [TARGET_WORKFLOW.md](./TARGET_WORKFLOW.md) секция 13

| # | Задача | Файл | Effort |
|---|--------|------|--------|
| 5.1 | is_published проверка в rollback | `workflow_v2.py` | 30m |
| 5.2 | Auto-retry логика | `publishing.py` | 2h |
| 5.3 | Permanent error handling | `publishing.py` | 1h |
| 5.4 | Update meta endpoint | `publishing.py` | 1h |
| 5.5 | Миграция is_published для старых видео | migration script | 1h |

**Effort:** 5.5h total

**Acceptance criteria:**
- [ ] Rollback запрещён после публикации
- [ ] Publishing retry до успеха
- [ ] NO_AUTH/BANNED останавливают retry
- [ ] Можно обновить meta после публикации

---

## Phase 6: Cleanup

| # | Задача | Файл | Effort |
|---|--------|------|--------|
| 6.1 | Удалить deprecated поля | `video.py` + migration | 2h |
| 6.2 | Удалить старые API endpoints | `workflow.py` | 1h |
| 6.3 | Удалить feature flags | `config.py` | 30m |
| 6.4 | Обновить документацию | docs/ | 2h |

**Effort:** 5.5h total

---

## Summary

| Phase | Описание | Effort | Depends On |
|-------|----------|--------|------------|
| 0 | Security | 5h | - |
| 1 | Fix Broken | 6h | Phase 0 |
| 2 | Data Model | 8h | Phase 1 |
| 3 | Breakpoints | 6h | Phase 2 |
| 4 | API Unification | 14h | Phase 2, 3 |
| 5 | Publishing & Rollback | 5.5h | Phase 4 |
| 6 | Cleanup | 5.5h | Phase 5 |

**Total:** ~50h

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Data loss при миграции | Backup + dry-run + transaction |
| Два источника правды | Feature flag + чёткий контракт |
| Breaking API changes | Версионирование + deprecation period |
| Regression в workflow | Тесты перед рефакторингом |
| Rollback после публикации | is_published + audit log |

---

## Feature Flags

```bash
# .env
USE_VARIANT_MODEL=false      # Phase 2: включить после миграции
USE_NEW_BREAKPOINTS=false    # Phase 3: включить после тестов
USE_WORKFLOW_V2_API=false    # Phase 4: включить после frontend update
```

---

## Checklist

### Pre-migration
- [ ] Backup production database
- [ ] Write tests for current behavior
- [ ] Review WORKFLOW_ANALYSIS.md issues

### Phase 0
- [ ] 0.1 Auth в metrics
- [ ] 0.2 Leaderboard filter
- [ ] 0.3 Ownership check

### Phase 1
- [ ] 1.1 Variant endpoint
- [ ] 1.2 Engagement rate
- [ ] 1.3 generate_meta дубликат
- [ ] 1.4 Audio gating

### Phase 2
- [ ] 2.1 Models created
- [ ] 2.2 Feature flag works
- [ ] 2.3 Data migrated

### Phase 3
- [ ] 3.1-3.4 Breakpoints working

### Phase 4
- [ ] 4.1-4.8 New API + frontend

### Phase 5
- [ ] 5.1-5.5 Publishing + rollback

### Phase 6
- [ ] 6.1-6.4 Cleanup done

---

> **Детали по текущим багам:** [WORKFLOW_ANALYSIS.md](./WORKFLOW_ANALYSIS.md)
> **Целевая архитектура:** [TARGET_WORKFLOW.md](./TARGET_WORKFLOW.md)
