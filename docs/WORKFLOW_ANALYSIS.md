# Критический анализ Workflow

Анализ полного пайплайна: создание проекта → генерация видео → публикация → аналитика.

**Дата:** 2026-01-10

**Связанные документы:**
- [TARGET_WORKFLOW.md](./TARGET_WORKFLOW.md) — **каноническое описание целевого workflow**
- [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) — план миграции
- [PLAN_BREAKPOINTS_SYSTEM.md](./PLAN_BREAKPOINTS_SYSTEM.md) — план исправления workflow_mode

---

## Содержание

1. [Critical Issues](#1-critical-issues)
2. [High Priority Issues](#2-high-priority-issues)
3. [Структурные проблемы](#3-структурные-проблемы)
4. [UX проблемы](#4-ux-проблемы)
5. [Missing Features](#5-missing-features)
6. [Анализ по этапам](#6-анализ-по-этапам)
7. [План исправлений](#7-план-исправлений)

---

## 1. Critical Issues

### 1.1 Metrics API без авторизации

**Файл:** `backend/app/api/metrics.py:36-89`

**Проблема:** Endpoints для метрик не проверяют принадлежность видео пользователю.

```python
# metrics.py:36 - НЕТ current_user проверки
@router.post("/video/{video_id}", response_model=VideoMetricsResponse)
async def add_video_metrics(video_id: int, ...):
    # Любой user может добавить метрики к ЛЮБОМУ video_id
```

**Уязвимые endpoints:**
- `POST /metrics/video/{video_id}` — добавление метрик
- `POST /metrics/video/{video_id}/rating` — установка рейтинга
- `GET /metrics/leaderboard` — просмотр всех видео

**Импакт:**
- Подделка метрик (накрутка views/likes)
- Манипуляция leaderboard
- Просмотр чужих видео и метрик

**Сравнение:** `publishing.py` правильно проверяет workspace:
```python
# publishing.py:29 - ПРАВИЛЬНО
def verify_video_ownership(db, video, current_user):
    workspace_ids = get_user_workspace_ids(db, current_user.id)
    if video.project.workspace_id not in workspace_ids:
        raise HTTPException(status_code=403)
```

---

### 1.2 Leaderboard показывает ВСЕ видео

**Файл:** `frontend/src/pages/Analytics.tsx:30`

**Проблема:** Leaderboard API возвращает видео всех пользователей.

```typescript
// Analytics.tsx:30-33
const { data: leaderboard } = useQuery(
  ['leaderboard', period, sortBy],
  () => metricsApi.getLeaderboard(period, sortBy, 20)  // Нет фильтра по user/workspace
)
```

**Импакт:** Privacy violation — пользователи видят контент и метрики конкурентов.

---

## 2. High Priority Issues

### 2.1 Engagement rate умножается на 100 дважды

**Файл:** `backend/app/api/metrics.py:28-33`

```python
# metrics.py:32
rate = ((likes + comments + shares) / views) * 100 * 100  # ×100 дважды!

# metrics.py:151 - потом делит обратно
engagement_rate = metric.engagement_rate / 100 if metric.engagement_rate else 0
```

**Правильно:** `* 10000` один раз, или `* 100` и хранить как float.

---

### 2.2 Дубликат вызова generate_meta

**Файл:** `backend/app/api/workflow.py`

```python
# workflow.py:265 - в select_audio_variant
meta = await openai_service.generate_publishing_meta(...)
video.publishing_meta = meta

# workflow.py:288 - отдельный endpoint
@router.post("/generate-meta")
async def generate_publishing_meta(...):
    meta = await openai_service.generate_publishing_meta(...)
```

**Импакт:** Лишние API вызовы, потенциальные race conditions.

---

### 2.3 Audio генерируется до approve video

**Проблема:** В MANUAL mode audio generation не гейтится approval предыдущего шага.

**Импакт:** Потраченные ресурсы на audio для rejected видео.

---

### 2.4 workflow_mode не работает

**Файл:** `backend/app/services/workflow/orchestrator.py`

**Проблема:** UI показывает выбор AUTO/MANUAL, но orchestrator игнорирует этот флаг.

```python
# orchestrator.py — MANUAL режим не проверяется!
async def run_discover_workflow(self):
    await self._generate_story()
    await self._generate_description()  # Нет паузы между шагами
    # ... все шаги подряд
```

**Импакт:**
- UI врёт пользователю про MANUAL mode
- Единственная пауза — hardcoded `require_image_approval`
- Remix не имеет выбора режима вообще

**Детали:** См. [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) Phase 3
**План исправления:** См. [PLAN_BREAKPOINTS_SYSTEM.md](./PLAN_BREAKPOINTS_SYSTEM.md)

---

## 3. Структурные проблемы

### 3.1 Путаница статусов Video

**Файл:** `backend/app/models/video.py:72-74`

```python
current_step = Column(SQLEnum(StepType))      # STORY, DESCRIPTION, IMAGE...
status = Column(SQLEnum(WorkflowStatus))       # PENDING, IN_PROGRESS, COMPLETED...
```

**Проблема:** Два независимых enum без чёткой связи.

**Frontend проверяет хрупко:**
```typescript
// VideoDetail.tsx - проверка через lowercase string
const statusLower = video.status?.toLowerCase() || ''
const isInProgress = ['pending', 'in_progress'].includes(statusLower)
```

---

### 3.2 Deprecated поля сосуществуют с новыми

**Файл:** `backend/app/models/video.py:60-70`

```python
# Deprecated
image_prompt = Column(Text)           # → использовать prompt_data
adaptation_data = Column(JSON)        # → использовать publishing_meta

# Current
prompt_data = Column(JSON)
publishing_meta = Column(JSON)
```

**Проблема:** Код использует и старые и новые поля непоследовательно.

---

### 3.3 Нумерация шагов не соответствует коду

**Старая документация (9 шагов):**
```
Stage 1: Story
Stage 2: Description
Stage 3: Prompt
Stage 4: Image
Stage 5: Scenario
Stage 6: Video
Stage 7: Audio
Stage 8: Adaptation  ← DEPRECATED
Stage 9: Publishing  ← Не WorkflowStep
```

**Актуальное (см. [TARGET_WORKFLOW.md](./TARGET_WORKFLOW.md)):**
- Discover: 7 шагов (Story → Description → Prompt → Image → Scenario → Video → Audio)
- Remix: 3 шага (Image → Video → Audio)
- ADAPTATION deprecated, PUBLISHING — отдельный flow

---

### 3.4 Publishing вне системы workflow

**Проблема:**
- `PublishResult` — отдельная модель, не связана с `WorkflowStep`
- Publishing не проходит через approve flow
- Нет единого UI паттерна для всех шагов

---

### 3.5 WorkflowStep.content не используется

**Файл:** `backend/app/services/workflow/base.py`

```python
# Данные сохраняются в Video model
setattr(self.video, self.content_field, content)  # video.story_data, video.image_url, etc.

# WorkflowStep.content остаётся пустым или дублирует
self.step.content = content_with_meta
```

**Импакт:** Нельзя отследить что именно было сгенерировано на каждом шаге.

---

## 4. UX проблемы

### 4.1 N+1 queries в Analytics

**Файл:** `frontend/src/pages/Analytics.tsx:42-48`

```typescript
// Для каждого video в leaderboard делает отдельный fetch
for (const item of leaderboard) {
  const video = await videosApi.get(item.video_id)  // N запросов!
}
```

**Решение:** Включить title в leaderboard response или batch fetch.

---

### 4.2 Inconsistent refetch intervals

| Компонент | Интервал |
|-----------|----------|
| VideoDetail (video) | 5 секунд |
| VideoDetail (metrics) | 60 секунд |
| Analytics | 60 секунд |

**Импакт:** Пользователь видит разные данные на разных страницах.

---

## 5. Missing Features

### 5.1 Нет rollback шагов
Нельзя откатить workflow на предыдущий шаг и переделать.

### 5.2 Нет batch publish
Нельзя опубликовать на все платформы одним действием.

### 5.3 Нет scheduling
Нельзя запланировать публикацию на определённое время.

### 5.4 Нет cost tracking
Не видно сколько потрачено на API calls (OpenAI, KLING, etc).

### 5.5 Нет draft management
Нельзя сохранить незаконченный workflow и вернуться позже.

### 5.6 Нет variant comparison
Нельзя сравнить performance разных content variants.

### 5.7 Нет A/B testing
Нельзя протестировать один контент на разных платформах и сравнить.

### 5.8 Нет team collaboration
Нельзя назначить approval конкретному пользователю.

---

## 6. Анализ по этапам

### 6.1 Создание проекта

**Файлы:**
- `backend/app/api/projects.py:29-68`
- `backend/app/schemas/project.py:20-56`

**Проблемы:**
1. **Silent workspace default** — если workspace не указан, берётся первый без уведомления
2. **Нет валидации system_prompts** — можно передать невалидные промпты
3. **Нет дублирования проектов** — нельзя создать копию существующего

---

### 6.2 Создание видео

**Файлы:**
- `backend/app/api/videos.py:27-52`
- `frontend/src/pages/CreateVideo.tsx`

**Проблемы:**
1. **Variant endpoint не существует** — CRITICAL
2. **workflow_mode нельзя изменить** — застреваешь с выбранным режимом
3. **Нет связи video → variant** — не знаем какой вариант выбрал пользователь

---

### 6.3 Workflow генерации

**Файлы:**
- `backend/app/api/workflow.py`
- `backend/app/services/workflow/`

**Проблемы:**
1. **Статусы запутаны** — current_step vs status
2. **Нумерация шагов врёт** — комментарии не соответствуют коду
3. **WorkflowStep.content пустой** — данные только в Video model
4. **Audio до approve** — в MANUAL mode

---

### 6.4 Публикация

**Файлы:**
- `backend/app/api/publishing.py`
- `backend/app/services/social_service.py`

**Статус:** Относительно чистый код после рефакторинга.

**Проблемы:**
1. **Вне workflow системы** — отдельная модель PublishResult
2. **Metrics scheduling сразу** — метрики могут быть пустыми первые 30 минут

---

### 6.5 Аналитика

**Файлы:**
- `backend/app/api/metrics.py`
- `frontend/src/pages/Analytics.tsx`

**Проблемы:**
1. **CRITICAL: Нет авторизации** — любой видит/меняет любые метрики
2. **Engagement rate ×100 дважды**
3. **Leaderboard без фильтра по user**
4. **N+1 queries**
5. **Rating default bug** — unrated = 3, искажает "surprise hits"

---

## 7. План исправлений

### Phase 1: Security (CRITICAL)

| # | Задача | Файл | Effort |
|---|--------|------|--------|
| 1 | Добавить auth в metrics endpoints | `metrics.py` | 2h |
| 2 | Фильтровать leaderboard по workspace | `metrics.py` + `Analytics.tsx` | 2h |
| 3 | Проверять ownership при fetch metrics | `metrics.py` | 1h |

### Phase 2: Broken Features

| # | Задача | Файл | Effort |
|---|--------|------|--------|
| 4 | Починить или удалить variant generation | `CreateVideo.tsx` + backend | 4h |
| 5 | Исправить engagement rate calculation | `metrics.py` | 30m |
| 6 | Убрать дубликат generate_meta | `workflow.py` | 30m |
| 7 | **Починить workflow_mode (breakpoints)** | См. [PLAN_BREAKPOINTS_SYSTEM.md](./PLAN_BREAKPOINTS_SYSTEM.md) | 4h |

### Phase 3: Cleanup

| # | Задача | Файл | Effort |
|---|--------|------|--------|
| 8 | Удалить deprecated поля или мигрировать | `video.py` + миграции | 4h |
| 9 | Унифицировать статусы | `video.py` + frontend | 4h |
| 10 | Исправить нумерацию шагов в комментариях | `workflow.py` | 30m |

### Phase 4: UX Improvements

| # | Задача | Файл | Effort |
|---|--------|------|--------|
| 11 | Batch fetch в Analytics | `Analytics.tsx` | 2h |
| 12 | Унифицировать refetch intervals | Frontend | 1h |
| 13 | Добавить error states в CreateVideo | `CreateVideo.tsx` | 1h |

---

## Appendix: Полный список issues

| Severity | Issue | Location |
|----------|-------|----------|
| CRITICAL | Metrics endpoints без auth | `metrics.py:36-89` |
| CRITICAL | Leaderboard показывает все видео | `Analytics.tsx:30` |
| HIGH | Engagement rate ×100 дважды | `metrics.py:32` |
| HIGH | Дубликат generate_meta | `workflow.py:265,288` |
| HIGH | Audio до approve video | `workflow.py` |
| HIGH | workflow_mode не работает | `orchestrator.py` |
| HIGH | Missing Remix fields в Project | `project.py` |
| MEDIUM | Путаница статусов | `video.py:72-74` |
| MEDIUM | Deprecated поля | `video.py:60-70` |
| MEDIUM | Нумерация шагов | `workflow.py` comments |
| MEDIUM | N+1 queries | `Analytics.tsx:42-48` |
| MEDIUM | Metrics scheduling timing | `publishing.py:88` |
| MEDIUM | WorkflowModeSelector скрыт для Remix | `CreateVideo.tsx:105` |
| MEDIUM | require_image_approval checkbox | `ProjectForm.tsx:248-262` |
| LOW | Rating default bug | `Analytics.tsx:341` |
| LOW | Preview prompt не используется | `workflow.py:40` |
| LOW | Inconsistent refetch | Frontend |
