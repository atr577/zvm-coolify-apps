# Task 21: Fix Broken Features (Phase 1)

**Приоритет:** P1 (HIGH)
**Оценка:** 5h (было 6h, 21.4 перенесён в Task 23)
**Зависимости:** Task 20 (Security)
**Блокирует:** Phase 2+

> **Источник:** [IMPLEMENTATION_PLAN.md](../../docs/IMPLEMENTATION_PLAN.md) Phase 1
> **Детали багов:** [WORKFLOW_ANALYSIS.md](../../docs/WORKFLOW_ANALYSIS.md) секция 2

---

## Задачи

### 21.1 ~~Variant endpoint 404~~ (SKIP)

**Статус:** FALSE POSITIVE — endpoint существует

По результатам аудита (AUDIT_REPORT_2026_01_10.md):
- Endpoint EXISTS: `POST /api/ai/generate-variants`
- File: `backend/app/api/ai_generation.py:31-76`

**Действие:** Пропустить

---

### 21.2 Engagement rate ×100 bug (30m)

**Файл:** `backend/app/api/metrics.py:28-33`

**Проблема:**
```python
# Текущий код - умножает на 100 дважды
rate = ((likes + comments + shares) / views) * 100 * 100  # ×10000!
```

**Исправление:**
```python
def calculate_engagement_rate(views: int, likes: int, comments: int, shares: int) -> Optional[float]:
    """Calculate engagement rate as percentage (e.g., 5.5 = 5.5%)"""
    if views == 0:
        return None
    rate = ((likes + comments + shares) / views) * 100
    return round(rate, 2)  # Return as float with 2 decimal places
```

**Также проверить:**
- Line 151: деление на 100 при отображении
- Line 270: avg_engagement calculation
- Убедиться что везде консистентно

---

### 21.3 Дубликат generate_meta (30m)

**Проблема:** `generate_publishing_meta` вызывается в 3 местах:
1. `workflow.py:265` — в select_audio_variant ✅ (оставить)
2. `workflow.py:289-312` — отдельный endpoint ✅ (оставить для ручной регенерации)
3. `orchestrator.py:399` → `_generate_publishing_meta()` — когда audio_skipped ❌ (дубликат)

**Решение:**
1. Оставить вызов в `select_audio_variant` (основной путь)
2. Оставить endpoint `/generate-meta` для ручной регенерации
3. Удалить вызов из orchestrator (line 399) — meta должна генериться только при выборе audio

**Изменения в orchestrator.py (line 396-408):**
```python
# БЫЛО:
if audio_result.get("status") == "skipped":
    await self._generate_publishing_meta()  # УДАЛИТЬ эту строку
    return WorkflowResult(...)

# СТАНЕТ:
if audio_result.get("status") == "skipped":
    # Meta will be generated manually via /generate-meta endpoint
    return WorkflowResult(
        video_id=self.video.id,
        steps_completed=self.steps_completed,
        message=f"Video completed. Audio skipped. Generate meta manually.",
        mode=mode,
        total_time_seconds=self._elapsed_time(),
        audio_skipped=True,
        next_action="generate_meta"  # Указываем что нужно сгенерить meta
    )
```

**Также удалить метод `_generate_publishing_meta` (lines 420-450) если он больше не используется.**

---

### 21.4 Audio до approve video (SKIP → Task 23)

**Статус:** ПЕРЕНЕСЕНО в Task 23 (Breakpoints System)

**Причина:** Task 23 реализует полную систему breakpoints, которая включает:
- `_should_pause()` метод для всех step types
- Pause перед VIDEO и AUDIO в MANUAL режиме
- `resume_workflow()` для продолжения после approve

Делать частичный fix здесь создаст конфликт с Task 23.

**Действие:** Пропустить, реализовать в рамках Task 23

---

## Acceptance Criteria

- [ ] Engagement rate показывает корректные проценты (5.5%, не 550%)
- [ ] publishing_meta генерится один раз (при select_audio_variant)
- [ ] ~~В MANUAL mode audio НЕ генерится до approve VIDEO~~ → Task 23

---

## Тестирование

```python
# Test engagement rate
def test_engagement_rate():
    rate = calculate_engagement_rate(views=1000, likes=30, comments=15, shares=5)
    assert rate == 5.0  # (30+15+5)/1000 * 100 = 5%

# Test MANUAL mode pauses at video
def test_manual_mode_pauses_at_video():
    video = create_video(workflow_mode=WorkflowMode.MANUAL)
    result = await orchestrator.run_discover_workflow()
    # Should pause at VIDEO step
    assert video.current_step == StepType.VIDEO
    assert video.status == WorkflowStatus.AWAITING_APPROVAL
    assert video.audio_variants is None  # Audio not generated yet
```

---

## Rollback

Git revert отдельных commits если нужно.

---

## Checklist

- [ ] ~~21.1 Variant endpoint~~ (SKIP - false positive)
- [ ] 21.2 Fix engagement rate calculation
- [ ] 21.3 Remove duplicate generate_meta from orchestrator
- [ ] ~~21.4 Gate audio~~ (SKIP → Task 23)
- [ ] Тесты пройдены
- [ ] Code review

---

**Создано:** 2026-01-10
**Статус:** TODO
