---
id: T33
title: Local media storage for PiAPI/KLING generated files
status: todo
priority: high
created: 2026-01-10
updated: 2026-01-10
tags: [backend, storage, media-handling, piapi-kling]
depends_on: []
estimate: 8
actual: null
spec: null
branch: feature/T33-local-media
related_rca: null
---

# Description

URLs returned by PiAPI/KLING for generated images and videos have limited TTL and expire over time. This causes media displayed on video cards to break. Solution: download and store media locally upon generation, maintain local paths in the database.

# Acceptance Criteria

- [ ] ImageStep downloads generated image after KLING generation and saves to `data/generated/images/{video_id}_{timestamp}.png`
- [ ] VideoStep downloads generated video after KLING generation and saves to `data/generated/videos/{video_id}_{timestamp}.mp4`
- [ ] `Video.image_url` and `Video.video_url` store relative local paths (e.g., `images/video_123_1704880000.png`)
- [ ] Backend endpoint `GET /api/files/{type}/{filename}` serves static files (type: images | videos)
- [ ] Directories `data/generated/images/` and `data/generated/videos/` created automatically on app startup
- [ ] Tests cover download functionality, path storage, and file serving
- [ ] Frontend displays media from `/api/files/{type}/{filename}` instead of external URLs

# Checklist

- [ ] Create file service module for downloads and storage (`backend/app/services/file_service.py`)
- [ ] Add file endpoints to backend (`backend/app/api/files.py`)
- [ ] Modify ImageStep to download and store image locally
- [ ] Modify VideoStep to download and store video locally
- [ ] Update Video model to accept relative paths
- [ ] Add directory initialization on app startup
- [ ] Update frontend to use local file endpoints
- [ ] Write unit tests for file_service
- [ ] Write integration tests for workflow with local storage
- [ ] Test file serving endpoint

# Notes

- Use `httpx` for downloads (async)
- Filename format: `{video_id}_{unix_timestamp}.{ext}` ensures uniqueness
- Handle download failures gracefully (log, continue with original URL as fallback)
- Implement disk space checks if needed later
- Consider cleanup strategy for old files (future task)
