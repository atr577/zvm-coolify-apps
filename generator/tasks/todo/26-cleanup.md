# Task 26: Cleanup (Phase 6)

**Приоритет:** P3 (LOW)
**Оценка:** 5.5h
**Зависимости:** Task 25 (Publishing & Rollback)
**Блокирует:** Нет

> **Источник:** [IMPLEMENTATION_PLAN.md](../../docs/IMPLEMENTATION_PLAN.md) Phase 6

---

## Цель

Финальная очистка после успешной миграции:
- Удалить deprecated код
- Удалить feature flags
- Обновить документацию

---

## Pre-requisites

**Перед началом убедиться:**
- [ ] Phase 0-5 полностью завершены
- [ ] Все тесты проходят
- [ ] Production работает стабильно минимум 1 неделю
- [ ] Нет rollback на старый код

---

## Задачи

### 26.1 Удалить deprecated поля из Video (2h)

**Файл:** `backend/app/models/video.py`

```python
# УДАЛИТЬ:
image_prompt = Column(Text, nullable=True)      # → use prompt_data
adaptation_data = Column(JSON, nullable=True)   # → use publishing_meta
```

**Migration:**
```bash
alembic revision --autogenerate -m "remove deprecated video fields"
```

```python
# migration file
def upgrade():
    op.drop_column('videos', 'image_prompt')
    op.drop_column('videos', 'adaptation_data')

def downgrade():
    op.add_column('videos', sa.Column('image_prompt', sa.Text, nullable=True))
    op.add_column('videos', sa.Column('adaptation_data', sa.JSON, nullable=True))
```

**Также удалить использования:**
- Поиск: `grep -r "image_prompt" backend/`
- Поиск: `grep -r "adaptation_data" backend/`

---

### 26.2 Удалить старые API endpoints (1h)

**Файл:** `backend/app/api/workflow.py`

Удалить deprecated endpoints:
```python
# УДАЛИТЬ:
@router.post("/generate-story")
@router.post("/generate-description")
@router.post("/generate-prompt")
@router.post("/generate-image")
@router.post("/generate-scenario")
@router.post("/generate-video")
@router.post("/generate-audio")
@router.post("/approve-step")  # replaced by /{video_id}/{step}/approve
@router.post("/adapt-for-platforms")  # deprecated
```

**Оставить:**
```python
@router.post("/auto-generate-to-video")  # Main entry point
@router.post("/select-audio-variant")     # Keep for backward compat or migrate
@router.post("/generate-meta")            # Keep for manual regeneration
@router.patch("/update-meta")             # Keep
```

---

### 26.3 Удалить feature flags (30m)

**Файл:** `backend/app/core/config.py`

```python
# УДАЛИТЬ:
USE_VARIANT_MODEL: bool = False
USE_NEW_BREAKPOINTS: bool = False
USE_WORKFLOW_V2_API: bool = False
```

**Файл:** `backend/app/services/workflow/base.py`

Удалить условные проверки feature flags:
```python
# БЫЛО:
if settings.USE_VARIANT_MODEL:
    # new code
else:
    # old code

# СТАНЕТ:
# new code (без условия)
```

**Файл:** `.env.example`

Удалить упоминания feature flags.

---

### 26.4 Обновить документацию (2h)

**Файлы для обновления:**

1. **CLAUDE.md** - обновить описание workflow
2. **docs/TARGET_WORKFLOW.md** - пометить как "Implemented"
3. **docs/IMPLEMENTATION_PLAN.md** - пометить все phases как completed
4. **tasks/README.md** - переместить 20-26 в done/

**API Documentation:**
- Обновить OpenAPI descriptions
- Удалить deprecated endpoints из docs
- Добавить примеры для новых endpoints

**README.md (root):**
- Обновить секцию про workflow
- Добавить информацию про Variant model

---

## Verification

После cleanup:

```bash
# 1. Все тесты проходят
pytest

# 2. Нет упоминаний deprecated кода
grep -r "image_prompt" backend/  # should return nothing
grep -r "adaptation_data" backend/  # should return nothing
grep -r "USE_VARIANT_MODEL" backend/  # should return nothing
grep -r "USE_NEW_BREAKPOINTS" backend/  # should return nothing

# 3. API работает
curl http://localhost:8000/api/workflow/1/story/approve -X POST
# Should return 200 (not 404)

curl http://localhost:8000/api/workflow/generate-story -X POST
# Should return 404 (removed)

# 4. Frontend работает
npm run build  # no errors
```

---

## Acceptance Criteria

- [ ] Deprecated поля удалены из Video model
- [ ] Старые endpoints удалены
- [ ] Feature flags удалены
- [ ] Документация актуальна
- [ ] Все тесты проходят
- [ ] Production работает

---

## Rollback

**НЕТ ROLLBACK** - это финальный cleanup.

Если нужно откатить:
1. Git revert cleanup commits
2. Alembic downgrade для удалённых колонок
3. Восстановить feature flags

---

## Checklist

- [ ] 26.1 Remove deprecated Video fields + migration
- [ ] 26.2 Remove old API endpoints
- [ ] 26.3 Remove feature flags
- [ ] 26.4 Update documentation
- [ ] All tests pass
- [ ] Production verified
- [ ] Code review

---

## Post-Cleanup

После завершения:

1. **Архивировать документы:**
   - Переместить WORKFLOW_ANALYSIS.md в archive/
   - Переместить IMPLEMENTATION_PLAN.md в archive/

2. **Обновить tasks/:**
   - Переместить 20-26 в done/
   - Обновить README.md

3. **Celebrate!**

---

**Создано:** 2026-01-10
**Статус:** TODO
