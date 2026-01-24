---
id: T10
title: Migrate AI providers from PiAPI to OpenAI + fal.ai
status: todo
priority: high
created: 2026-01-23
updated: 2026-01-23
tags: [architecture, ai-services, refactoring]
depends_on: []
estimate: "25h"
actual: ""
spec: "docs/specs/SPEC-T10-ai-provider-migration.md"
branch: "feature/T10-ai-provider-migration"
related_rca: ""
---

# Task: Migrate AI providers from PiAPI to OpenAI + fal.ai

## Description

Currently all AI services go through a single PiAPI proxy client (`backend/app/services/piapi_client.py`). Migrating to direct SDKs for simpler architecture and better control.

**New architecture:**

| Function | Was (PiAPI) | Becomes | Model ID |
|----------|-------------|---------|----------|
| **LLM** | gpt-4o-mini via PiAPI | OpenAI SDK | `gpt-4o-mini` |
| **Image** | qwen-image / nano-banana | fal.ai | `fal-ai/nano-banana-pro` |
| **Video** | kling-2.5 | fal.ai | `fal-ai/veo3.1/image-to-video` |
| **Music** | suno | fal.ai | `fal-ai/lyria2` |
| **Audio merge** | Kling Sound API | ffmpeg local | — |

**PiAPI удаляется полностью.**

## Key Decisions

1. **Async approach:** `fal.queue.submit()` + polling (не `subscribe()`)
   - Сохраняем `request_id` в TaskTracker для resume после падения
   - Аналогично текущему подходу с `external_task_id`

2. **Audio merge:** Veo 3.1 не поддерживает Kling Sound API
   - Генерим музыку через Lyria 2 отдельно
   - Мержим video + audio через ffmpeg локально
   - ffmpeg уже используется в `media_processor.py`

3. **Сохраняем:**
   - Response caching (`_save_to_cache`)
   - Mock mode (`settings.MOCK_MODE`)
   - Retry logic с exponential backoff
   - TaskTracker для resume

## Acceptance Criteria

- [ ] OpenAI SDK для всех LLM calls (generate_json, generate_text, validate_content)
- [ ] fal.ai SDK для image (nano-banana-pro)
- [ ] fal.ai SDK для video (veo3.1 image-to-video)
- [ ] fal.ai SDK для music (lyria2)
- [ ] ffmpeg merge для video + audio
- [ ] TaskTracker работает с fal.ai request_id
- [ ] `.env` обновлён: `OPENAI_API_KEY`, `FAL_KEY`
- [ ] `piapi_client.py` удалён
- [ ] Full workflow tested: SCENARIO → IMAGE → VIDEO → AUDIO → merge
- [ ] Tests passing: `pytest backend/`

## Checklist

### Phase 1: Setup
- [ ] Install deps: `openai`, `fal-ai`
- [ ] Add env vars to `.env.example` and `config.py`
- [ ] Verify ffmpeg in Dockerfile

### Phase 2: OpenAI Service
- [ ] Create `backend/app/services/openai_client.py` (direct OpenAI SDK)
- [ ] Update `openai_service.py` to use new client
- [ ] Test: generate_json, generate_text, validate_content

### Phase 3: fal.ai Client — Base Infrastructure
- [ ] Create `backend/app/services/fal_client.py` with base class
- [ ] Implement `_submit_task()` generic method
- [ ] Implement `_poll_status()` with configurable timeout/interval
- [ ] Implement retry logic with exponential backoff (3 attempts)
- [ ] Implement rate limit handling (429 → retry after delay)
- [ ] Preserve response caching (`_save_to_cache` pattern, seed in key)
- [ ] Support MOCK_MODE for testing

### Phase 3b: fal.ai Client — Image
- [ ] Implement `submit_image()` (nano-banana-pro)
- [ ] Implement `poll_image()` with 2 min timeout
- [ ] Implement `generate_image()` high-level method
- [ ] Test: generate image via fal_client directly

### Phase 3c: fal.ai Client — Video
- [ ] Implement `submit_video()` (veo3.1 image-to-video)
- [ ] Implement `poll_video()` with 10 min timeout
- [ ] Implement `generate_video()` with generate_audio param
- [ ] Integrate with TaskTracker (save request_id for resume)
- [ ] Test: generate video from image via fal_client

### Phase 3d: fal.ai Client — Music
- [ ] Implement `submit_music()` (lyria2)
- [ ] Implement `poll_music()` with 5 min timeout
- [ ] Implement `generate_music()` high-level method
- [ ] Implement Lyria2 queue (semaphore max 2 concurrent)
- [ ] Test: generate music via fal_client directly

### Phase 4: Media Service
- [ ] Rename `kling_service.py` → `media_service.py`
- [ ] Update `generate_image()` → use fal_client
- [ ] Update `generate_video()` → use fal_client
- [ ] Test: media_service generates image + video

### Phase 4b: Audio Workflow
- [ ] Update `music_generator.py` → use fal_client.generate_music()
- [ ] Update `workflow.py` → audio mode selection (builtin vs custom)
- [ ] Test ffmpeg merge: Lyria2 WAV + Veo3.1 video → MP4 with audio
- [ ] Update `workflow.py` imports (kling_service → media_service)

### Phase 5: Cleanup
- [ ] Find all imports of `piapi_client`
- [ ] Delete `piapi_client.py`
- [ ] Delete `aimlapi_client.py` (if exists)
- [ ] Update `models_config.py` (remove PiAPI model configs)

### Phase 6: Testing
- [ ] Unit tests for new clients
- [ ] Integration test: full workflow
- [ ] Test resume after simulated crash (stop polling mid-generation)
- [ ] Test rate limit (429) handling
- [ ] Manual test: generate real video with both audio modes

## Files to Modify

| File | Action |
|------|--------|
| `backend/requirements.txt` | Add `openai`, `fal-ai` |
| `backend/app/core/config.py` | Add `OPENAI_API_KEY`, `FAL_KEY`, model IDs |
| `backend/.env.example` | Add new env vars |
| `backend/app/services/openai_client.py` | **NEW** - OpenAI SDK wrapper |
| `backend/app/services/fal_client.py` | **NEW** - fal.ai SDK wrapper |
| `backend/app/services/openai_service.py` | Update imports |
| `backend/app/services/kling_service.py` | Rename to `media_service.py`, use fal_client |
| `backend/app/api/workflow.py` | Update imports, audio workflow |
| `backend/app/core/music_generator.py` | Use fal_client for Lyria2 |
| `backend/app/core/models_config.py` | Update model configs for fal.ai |
| `backend/Dockerfile` | Verify ffmpeg installed |
| `backend/tests/test_openai_client.py` | **NEW** - unit tests |
| `backend/tests/test_fal_client.py` | **NEW** - unit tests |

### Files to Delete

| File | Reason |
|------|--------|
| `backend/app/services/piapi_client.py` | → `.bak` for rollback |
| `backend/app/services/aimlapi_client.py` | Unused |
| `backend/app/services/providers/kling/image_generator.py` | Merged into media_service |
| `backend/app/services/providers/kling/video_generator.py` | Merged into media_service |
| `backend/app/services/providers/kling/__init__.py` | Directory removed |
| `backend/tests/test_services/test_piapi_client.py` | Obsolete |

## Notes

**fal.ai API pattern:**
```python
import fal_client

# Submit task
handler = await fal_client.submit_async("fal-ai/veo3.1/image-to-video", input={...})
request_id = handler.request_id  # save to TaskTracker

# Poll status
status = await fal_client.status_async("fal-ai/veo3.1/image-to-video", request_id)

# Get result when done
result = await fal_client.result_async("fal-ai/veo3.1/image-to-video", request_id)
```

**Required API Keys:**
- `OPENAI_API_KEY` — OpenAI direct
- `FAL_KEY` — fal.ai

**Risk:** High — affects critical generation path. Migrate one service at a time, test after each.
