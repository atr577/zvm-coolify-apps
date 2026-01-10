# Task 21: Fix Broken Features (Phase 1)

**Приоритет:** P1 (HIGH)
**Оценка:** 6h
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
1. `workflow.py:265-269` — в select_audio_variant
2. `workflow.py:289-312` — отдельный endpoint
3. `orchestrator.py:432-436` — в orchestrator

**Решение:**
1. Оставить вызов ТОЛЬКО в `select_audio_variant` (при выборе аудио)
2. Удалить дубликат из orchestrator (line 432-436)
3. Endpoint `/generate-meta` оставить для ручной регенерации

**Изменения в orchestrator.py:**
```python
# УДАЛИТЬ блок 432-440:
# try:
#     meta = await openai_service.generate_publishing_meta(...)
#     self.video.publishing_meta = meta
# except Exception as e:
#     logger.warning(...)
#     self.video.publishing_meta = {}
```

---

### 21.4 Audio до approve video (1h)

**Файл:** `backend/app/services/workflow/orchestrator.py`

**Проблема:** В `_complete_video_generation()` audio генерируется сразу после video без проверки workflow_mode:
```python
await self._generate_video(motion_prompt=motion_prompt)  # Line 388
await self._generate_audio()  # Line 390 - сразу, без паузы!
```

**Исправление:**
```python
async def _complete_video_generation(self, mode: str, ...):
    # ... generate video ...
    await self._generate_video(motion_prompt=motion_prompt)
    self.steps_completed += 1

    # Check if should pause for video approval in MANUAL mode
    if self.video.workflow_mode == WorkflowMode.MANUAL:
        self.video.status = WorkflowStatus.AWAITING_APPROVAL
        self.video.current_step = StepType.VIDEO
        self.db.commit()
        return WorkflowResult(
            video_id=self.video.id,
            steps_completed=self.steps_completed,
            message="Video generated, awaiting approval",
            mode=mode,
            total_time_seconds=self._elapsed_time(),
            paused_for_approval=True,
            next_action="approve_video"
        )

    # AUTO mode: continue to audio
    audio_result = await self._generate_audio()
    # ...
```

---

## Acceptance Criteria

- [ ] Engagement rate показывает корректные проценты (5.5%, не 550%)
- [ ] publishing_meta генерится один раз (при select_audio_variant)
- [ ] В MANUAL mode audio НЕ генерится до approve VIDEO

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
- [ ] 21.4 Gate audio generation by video approval in MANUAL mode
- [ ] Тесты пройдены
- [ ] Code review

---

**Создано:** 2026-01-10
**Статус:** TODO
