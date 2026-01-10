---
id: T20
title: "Security Fix (Phase 0)"
status: todo
priority: critical
created: 2026-01-10
updated: 2026-01-10
tags: ['bugfix']
depends_on: []
estimate: "5h"
branch: ""
---

# Task 20: Security Fix (Phase 0)

> **Источник:** [IMPLEMENTATION_PLAN.md](../../docs/IMPLEMENTATION_PLAN.md) Phase 0
> **Детали багов:** [WORKFLOW_ANALYSIS.md](../../docs/WORKFLOW_ANALYSIS.md) секция 1

---

## Проблема

Metrics API не проверяет авторизацию и ownership. Любой пользователь может:
- Читать метрики чужих видео
- Добавлять/изменять метрики чужих видео
- Видеть все видео в leaderboard

---

## Задачи

### 20.1 Auth в metrics endpoints (2h)

**Файл:** `backend/app/api/metrics.py:36-89`

**Что делать:**
1. Добавить `current_user: User = Depends(get_current_user)` во все endpoints
2. Добавить `verify_video_ownership(db, video, current_user)` проверку

**Затронутые endpoints:**
- `POST /metrics/video/{video_id}` (line 36)
- `GET /metrics/video/{video_id}` (line 92)
- `GET /metrics/video/{video_id}/summary` (line 110)
- `PUT /metrics/video/{video_id}/{platform}/{period}` (line 165)
- `DELETE /metrics/video/{video_id}/{platform}/{period}` (line 203)
- `PUT /metrics/video/{video_id}/rating` (line 225)
- `POST /metrics/video/{video_id}/fetch` (line 380)
- `POST /metrics/fetch-all` (line 440)

**Пример (из publishing.py):**
```python
from app.core.deps import get_current_user
from app.models.user import User

def verify_video_ownership(db: Session, video: Video, current_user: User):
    workspace_ids = get_user_workspace_ids(db, current_user.id)
    if video.project.workspace_id not in workspace_ids:
        raise HTTPException(status_code=403, detail="Access denied")

@router.post("/video/{video_id}")
async def create_metrics(
    video_id: int,
    metrics: VideoMetricsCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # ADD THIS
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    verify_video_ownership(db, video, current_user)  # ADD THIS
    # ... rest of the code
```

---

### 20.2 Фильтр leaderboard по workspace (2h)

**Файлы:**
- `backend/app/api/metrics.py:245-256`
- `frontend/src/pages/Analytics.tsx`

**Backend изменения:**
```python
@router.get("/leaderboard")
async def get_metrics_leaderboard(
    period: str = "7d",
    sort_by: str = "views",
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # ADD
):
    # Get user's workspace IDs
    workspace_ids = get_user_workspace_ids(db, current_user.id)

    # Filter videos by workspace
    videos_with_metrics = db.query(Video).join(VideoMetrics).join(
        Project, Video.project_id == Project.id
    ).filter(
        VideoMetrics.period == MetricsPeriod(period),
        Project.workspace_id.in_(workspace_ids)  # ADD FILTER
    ).distinct().all()
```

**Frontend изменения:**
- Убедиться что передаётся auth token в запросе

---

### 20.3 Ownership check при добавлении метрик (1h)

**Файл:** `backend/app/api/metrics.py:36`

Добавить проверку что video принадлежит workspace пользователя перед любой операцией записи.

---

## Acceptance Criteria

- [ ] Нельзя добавить метрики к чужому video → 403
- [ ] Нельзя прочитать метрики чужого video → 403
- [ ] Leaderboard показывает только видео из своих workspaces
- [ ] Все 9 endpoints в metrics.py защищены

---

## Тестирование

```bash
# 1. Попытка доступа без токена
curl -X GET http://localhost:8000/api/metrics/video/1
# Expected: 401 Unauthorized

# 2. Попытка доступа к чужому видео
curl -X GET http://localhost:8000/api/metrics/video/999 \
  -H "Authorization: Bearer <token>"
# Expected: 403 Forbidden (если video не в workspace)

# 3. Leaderboard возвращает только свои видео
curl -X GET http://localhost:8000/api/metrics/leaderboard \
  -H "Authorization: Bearer <token>"
# Expected: только видео из workspaces пользователя
```

---

## Rollback

Нет rollback — это security fix, откатывать нельзя.

---

## Checklist

- [ ] 20.1 Добавить auth во все metrics endpoints
- [ ] 20.2 Фильтр leaderboard по workspace
- [ ] 20.3 Ownership check при записи
- [ ] Тесты пройдены
- [ ] Code review

---

**Создано:** 2026-01-10
**Статус:** TODO
