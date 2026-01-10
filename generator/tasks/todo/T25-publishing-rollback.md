---
id: T25
title: "Publishing & Rollback (Phase 5)"
status: todo
priority: medium
created: 2026-01-10
updated: 2026-01-10
tags: []
depends_on: ['T24']
estimate: "5.5h"
branch: ""
---

# Task 25: Publishing & Rollback (Phase 5)

> **Источник:** [IMPLEMENTATION_PLAN.md](../../docs/IMPLEMENTATION_PLAN.md) Phase 5
> **Спецификация:** [TARGET_WORKFLOW.md](../../docs/TARGET_WORKFLOW.md) секция 13

---

## Цель

- Запретить rollback после публикации
- Добавить auto-retry логику для publishing
- Обработка permanent errors

---

## Задачи

### 25.1 is_published проверка в rollback (30m)

**Файл:** `backend/app/api/workflow_v2.py`

Уже добавлено в Task 24.6, но нужно убедиться что работает:

```python
@router.post("/{video_id}/rollback-to/{target_step}")
async def rollback_to_step(...):
    if video.is_published:
        raise HTTPException(
            status_code=400,
            detail="Cannot rollback published video. Use update-meta instead."
        )
```

---

### 25.2 Auto-retry логика (2h)

**Файл:** `backend/app/services/social_service.py`

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class RetryablePublishError(Exception):
    """Error that can be retried."""
    pass

class PermanentPublishError(Exception):
    """Error that should not be retried."""
    pass

PERMANENT_ERROR_CODES = [
    "NO_AUTH",
    "BANNED",
    "CONTENT_REJECTED",
    "ACCOUNT_SUSPENDED",
    "INVALID_TOKEN",
]

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type(RetryablePublishError)
)
async def publish_with_retry(
    platform: str,
    video_url: str,
    meta: dict,
    credentials: dict
) -> PublishResult:
    """Publish with automatic retry for transient errors."""
    try:
        result = await _do_publish(platform, video_url, meta, credentials)
        return result
    except Exception as e:
        error_code = extract_error_code(e)

        if error_code in PERMANENT_ERROR_CODES:
            raise PermanentPublishError(f"Permanent error: {error_code}")

        # Transient error - retry
        raise RetryablePublishError(str(e))
```

---

### 25.3 Permanent error handling (1h)

**Файл:** `backend/app/api/publishing.py`

```python
from app.services.social_service import PermanentPublishError, publish_with_retry

@router.post("/{platform}")
async def publish_to_platform(
    platform: str,
    request: PublishRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    video = get_video_with_ownership(db, request.video_id, current_user)

    try:
        result = await publish_with_retry(
            platform=platform,
            video_url=video.video_with_audio_url,
            meta=video.publishing_meta.get(platform, {}),
            credentials=get_platform_credentials(current_user, platform)
        )

        # Success - mark as published
        video.is_published = True
        save_publish_result(db, video.id, platform, result)
        db.commit()

        return {"status": "published", "url": result.url}

    except PermanentPublishError as e:
        # Don't retry, save error
        save_publish_result(db, video.id, platform, error=str(e))
        db.commit()

        raise HTTPException(
            status_code=400,
            detail={
                "error": "permanent_error",
                "message": str(e),
                "action": "Check account status or content policy"
            }
        )
```

---

### 25.4 Update meta endpoint (1h)

**Файл:** `backend/app/api/publishing.py`

```python
class UpdateMetaRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    hashtags: Optional[List[str]] = None

@router.put("/{video_id}/{platform}/meta")
async def update_published_meta(
    video_id: int,
    platform: str,
    body: UpdateMetaRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update metadata for already published video."""
    video = get_video_with_ownership(db, video_id, current_user)

    if not video.is_published:
        raise HTTPException(
            status_code=400,
            detail="Video not published yet"
        )

    # Get publish result for this platform
    publish_result = db.query(PublishResult).filter(
        PublishResult.video_id == video_id,
        PublishResult.platform == platform,
        PublishResult.status == "success"
    ).first()

    if not publish_result:
        raise HTTPException(
            status_code=404,
            detail=f"No successful publish found for {platform}"
        )

    # Call platform API to update
    try:
        await update_platform_meta(
            platform=platform,
            post_id=publish_result.platform_post_id,
            meta=body.dict(exclude_none=True),
            credentials=get_platform_credentials(current_user, platform)
        )

        # Update local meta
        if video.publishing_meta and platform in video.publishing_meta:
            video.publishing_meta[platform].update(body.dict(exclude_none=True))
            db.commit()

        return {"status": "updated"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

### 25.5 Миграция is_published для старых видео (1h)

**Файл:** `backend/scripts/migrate_is_published.py` (NEW)

```python
"""
Set is_published=True for videos that have successful PublishResult.

Run: python -m scripts.migrate_is_published
"""
from app.core.database import SessionLocal
from app.models import Video, PublishResult

def migrate_is_published():
    db = SessionLocal()
    try:
        # Find videos with successful publish
        published_video_ids = db.query(PublishResult.video_id).filter(
            PublishResult.status == "success"
        ).distinct().all()

        video_ids = [v[0] for v in published_video_ids]

        # Update videos
        updated = db.query(Video).filter(
            Video.id.in_(video_ids),
            Video.is_published == False
        ).update({"is_published": True}, synchronize_session=False)

        db.commit()
        print(f"Updated {updated} videos to is_published=True")

    finally:
        db.close()

if __name__ == "__main__":
    migrate_is_published()
```

---

## Acceptance Criteria

- [ ] Rollback возвращает 400 для опубликованных видео
- [ ] Publishing автоматически retry при transient errors
- [ ] Permanent errors (NO_AUTH, BANNED) останавливают retry
- [ ] Можно обновить meta после публикации
- [ ] Старые видео с PublishResult имеют is_published=True

---

## Тестирование

```python
@pytest.mark.asyncio
async def test_rollback_blocked_after_publish():
    video.is_published = True
    db.commit()

    response = await client.post(f"/workflow/{video.id}/rollback-to/image")
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_publish_retry_on_transient_error():
    with patch("social_service._do_publish") as mock:
        # Fail twice, succeed on third
        mock.side_effect = [
            RetryablePublishError("timeout"),
            RetryablePublishError("rate limit"),
            PublishResult(url="https://...")
        ]

        result = await publish_with_retry(...)
        assert result.url == "https://..."
        assert mock.call_count == 3

@pytest.mark.asyncio
async def test_publish_stops_on_permanent_error():
    with patch("social_service._do_publish") as mock:
        mock.side_effect = Exception("NO_AUTH: Invalid token")

        with pytest.raises(PermanentPublishError):
            await publish_with_retry(...)

        # Should not retry
        assert mock.call_count == 1

@pytest.mark.asyncio
async def test_update_meta_after_publish():
    video.is_published = True
    create_publish_result(video, platform="instagram")

    response = await client.put(
        f"/publish/{video.id}/instagram/meta",
        json={"title": "New Title"}
    )
    assert response.status_code == 200
```

---

## Checklist

- [ ] 25.1 is_published check in rollback
- [ ] 25.2 Auto-retry with tenacity
- [ ] 25.3 Permanent error handling
- [ ] 25.4 Update meta endpoint
- [ ] 25.5 Migration script for existing data
- [ ] All tests pass
- [ ] Code review

---

**Создано:** 2026-01-10
**Статус:** TODO
