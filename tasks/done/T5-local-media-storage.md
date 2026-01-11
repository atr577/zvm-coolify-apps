---
id: T5
title: Local Media Storage - Download & Serve Generated Files
status: done
priority: high
created: 2026-01-11
updated: 2026-01-11
tags: [storage, media, backend, optimization]
depends_on: []
estimate: 6
actual: 0
spec: docs/specs/LOCAL_MEDIA.md
branch: feature/T5-local-media
related_rca: []
---

# Description

Currently, generated images and videos are stored on PiAPI CDN with temporary URLs that expire. This task implements local media storage to ensure persistent access to generated files and reduce dependency on external CDN availability.

The feature will:
1. Download media files after generation (IMAGE, VIDEO, AUDIO steps)
2. Store files locally with deterministic naming
3. Update Video model to track both CDN and local URLs
4. Create API endpoint to serve local files
5. Update workflow to handle download failures gracefully

## Acceptance Criteria

- [x] Video model has `local_image_url`, `local_video_url`, `local_audio_url` fields
- [x] New API endpoint `/api/files/{type}/{filename}` serves local files with proper Content-Type headers
- [x] Download service (`media_downloader.py`) with retry logic and failure handling
- [x] Workflow orchestrator triggers downloads after each generation step
- [x] Local files named deterministically: `{video_id}_{step}_{timestamp}.{ext}`
- [x] Storage directories created automatically: `data/media/images/`, `data/media/videos/`, `data/media/audio/`
- [x] Frontend prefers local URLs over CDN URLs when available
- [x] All tests passing: `pytest` + `npm run build`
- [x] Graceful fallback to CDN URL if download fails

## Checklist

### Backend: Database & Models
- [ ] Add migration: `local_image_url`, `local_video_url`, `local_audio_url` to `Video` model
- [ ] Update `Video` model schema with new fields
- [ ] Create alembic migration for schema change

### Backend: Storage Service
- [ ] Create `backend/app/services/media_downloader.py`
  - [ ] `async def download_media(url: str, video_id: str, step: str, file_type: str) -> str`
  - [ ] Retry logic (3 attempts with exponential backoff)
  - [ ] Handle network errors and timeouts gracefully
  - [ ] Return local path on success, None on failure
  - [ ] Create directories if they don't exist
  - [ ] Use httpx for async downloads

### Backend: API Endpoint
- [ ] Create `GET /api/files/{file_type}/{filename}` endpoint in `app/api/files.py`
  - [ ] Serve files from `data/media/` directory
  - [ ] Set correct Content-Type (image/*, video/*, audio/*)
  - [ ] Validate filename to prevent directory traversal
  - [ ] Return 404 if file not found
  - [ ] Add optional `Cache-Control` headers for browser caching

### Backend: Workflow Integration
- [ ] Update `orchestrator_v2.py` to call `download_media()` after each generation
- [ ] Store local URLs in Video model after successful download
- [ ] Log download attempts and results
- [ ] Keep CDN URL as fallback if download fails

### Backend: Configuration
- [ ] Add `MEDIA_STORAGE_PATH` to `config.py` (default: `data/media/`)
- [ ] Add `MEDIA_DOWNLOAD_TIMEOUT` to config (default: 30 seconds)
- [ ] Add `MEDIA_DOWNLOAD_RETRIES` to config (default: 3)

### Frontend: API Layer
- [ ] Create `mediaApi.getLocalFileUrl(type, filename): string` in `src/services/api.ts`
- [ ] Construct local file URLs: `/api/files/{type}/{filename}`

### Frontend: Hook Updates
- [ ] Update `useVideoWorkflow.ts` to prefer local URLs
- [ ] When rendering video/image/audio: use `local_*_url` if available, fallback to CDN

### Frontend: Components
- [ ] Update `VideoDetail.tsx` to use local URLs
- [ ] Update `CompletedVideoView.tsx` to display local files
- [ ] Update any preview components to use local URLs when available

### Testing
- [ ] Unit tests: `test_media_downloader.py`
  - [ ] Successful download
  - [ ] Retry on network error
  - [ ] Return None on max retries
  - [ ] Directory creation
- [ ] Integration tests: `test_workflow_with_local_media.py`
  - [ ] Full workflow generates and downloads media
  - [ ] Local URLs stored in DB
  - [ ] API endpoint serves files correctly
- [ ] API tests: `/api/files/{type}/{filename}` endpoint
  - [ ] Returns 200 with correct Content-Type for existing files
  - [ ] Returns 404 for non-existent files
  - [ ] Prevents directory traversal attacks
- [ ] Frontend build: `npm run build` passes
- [ ] Manual E2E: Generate video, verify local files exist and are served

## Notes

### Design Decisions

1. **File Naming:** `{video_id}_{step}_{unix_timestamp}.{ext}`
   - Example: `vid_abc123_IMAGE_1704873600.png`
   - Ensures uniqueness and allows tracking of retries

2. **Failure Handling:** Download failures are non-blocking
   - Workflow continues with CDN URL as fallback
   - Failed downloads logged for monitoring
   - Retry happens automatically on next workflow attempt

3. **Directory Structure:**
   ```
   data/media/
   ├── images/          # .png, .jpg, etc.
   ├── videos/          # .mp4, etc.
   └── audio/           # .mp3, .wav, etc.
   ```

4. **API Security:** Prevent directory traversal
   - Validate filename format: `^[a-zA-Z0-9_-]+\.[a-zA-Z0-9]+$`
   - Only allow files from `data/media/` subdirectories

### Future Enhancements

- S3 storage backend with local cache
- Batch download with progress tracking
- Media cleanup (archive old files after N days)
- CDN prefix configuration for different deployment environments

### Dependencies

- `httpx` (already in requirements.txt)
- No new external dependencies needed

### File Locations

**Backend:**
- `backend/app/services/media_downloader.py` (new)
- `backend/app/api/files.py` (new)
- `backend/app/models/video.py` (update)
- `backend/app/services/workflow/orchestrator_v2.py` (update)
- `backend/alembic/versions/XXXX_add_local_media_urls.py` (new)
- `backend/tests/test_media_downloader.py` (new)
- `backend/tests/test_workflow_with_local_media.py` (new)

**Frontend:**
- `frontend/src/services/api.ts` (update)
- `frontend/src/hooks/useVideoWorkflow.ts` (update)
- `frontend/src/pages/VideoDetail.tsx` (update)
- `frontend/src/components/video/CompletedVideoView.tsx` (update)

**Data:**
- `data/media/images/` (created automatically)
- `data/media/videos/` (created automatically)
- `data/media/audio/` (created automatically)

