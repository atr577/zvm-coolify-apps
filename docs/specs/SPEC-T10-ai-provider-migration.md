---
id: SPEC-T10
title: AI Provider Migration (PiAPI → OpenAI + fal.ai)
status: draft
created: 2026-01-23
task: T10
target_sections: [Services Layer, AI Integration, Error Handling]
---

# Technical Specification: AI Provider Migration

## Overview

Migrating from unified PiAPI proxy to direct SDK integrations with OpenAI and fal.ai. This removes the single-provider dependency and provides better control over individual AI services.

**Current:** All AI calls → `piapi_client.py` → PiAPI proxy → providers
**Target:** Business services → specialized clients → direct SDKs

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     SERVICES (Business Logic)                    │
│  openai_service.py          media_service.py                    │
│  - generate_scenario()      - generate_image()                  │
│  - validate_content()       - generate_video()                  │
│  - generate_json()          - generate_music()                  │
│                                                                  │
└────────────┬──────────────────────────────┬────────────────────┘
             │                              │
             ▼                              ▼
┌─────────────────────────┐   ┌────────────────────────────────┐
│   CLIENTS (Providers)   │   │    CLIENTS (Providers)         │
│  openai_client.py       │   │  fal_client.py                 │
│  - chat_completion()    │   │  - submit_image()              │
│  - generate_json()      │   │  - submit_video()              │
│  - retry logic          │   │  - submit_music()              │
│  - error handling       │   │  - poll_status()               │
│  - caching             │   │  - retry + resume              │
└─────────────────────────┘   └────────────────────────────────┘
             │                              │
             ▼                              ▼
┌─────────────────────────┐   ┌────────────────────────────────┐
│     OpenAI SDK          │   │      fal.ai SDK                │
│  (openai package)       │   │  (fal_client package)          │
└─────────────────────────┘   └────────────────────────────────┘
```

### Layer Responsibilities

| Layer | Purpose | Dependencies |
|-------|---------|--------------|
| **Services** | Business logic, workflow orchestration | Clients only |
| **Clients** | Provider-specific wrappers, retry, cache, error handling | External SDKs |
| **SDKs** | Direct API communication | HTTP clients |

## Data Structures

### OpenAI Client

```python
# openai_client.py

class OpenAIClient:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.LLM_MODEL
        self.client = openai.AsyncOpenAI(api_key=self.api_key)
        self.cache_enabled = settings.CACHE_API_RESPONSES
        self.cache_dir = Path(settings.API_CACHE_DIR)

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        response_format: Optional[Dict[str, str]] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """Direct OpenAI chat completion with retry logic."""
        pass

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """Generate structured JSON response."""
        pass

    async def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """Simple text generation."""
        pass
```

### fal.ai Client

```python
# fal_client.py

class FalClient:
    def __init__(self):
        self.api_key = settings.FAL_KEY
        self.cache_enabled = settings.CACHE_API_RESPONSES
        self.cache_dir = Path(settings.API_CACHE_DIR)
        fal_client.api_key = self.api_key

    # ============ Image Generation ============

    async def submit_image(
        self,
        prompt: str,
        aspect_ratio: str = "9:16",
        negative_prompt: Optional[str] = None,
        model: Optional[str] = None
    ) -> str:
        """Submit image generation task, returns request_id."""
        pass

    async def poll_image(
        self,
        request_id: str,
        max_wait_time: int = 120,
        poll_interval: int = 3
    ) -> str:
        """Poll image generation until complete, returns image URL."""
        pass

    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "9:16",
        negative_prompt: Optional[str] = None
    ) -> str:
        """High-level: submit + poll, returns image URL."""
        pass

    # ============ Video Generation ============

    async def submit_video(
        self,
        image_url: str,
        prompt: str,
        duration: int = 5,
        model: Optional[str] = None
    ) -> str:
        """Submit video generation task, returns request_id."""
        pass

    async def poll_video(
        self,
        request_id: str,
        max_wait_time: int = 600,
        poll_interval: int = 10
    ) -> str:
        """Poll video generation until complete, returns video URL."""
        pass

    async def generate_video(
        self,
        image_url: str,
        prompt: str,
        duration: int = 5
    ) -> str:
        """High-level: submit + poll, returns video URL."""
        pass

    # ============ Music Generation ============

    async def submit_music(
        self,
        prompt: str,
        duration: int = 10,
        model: Optional[str] = None
    ) -> str:
        """Submit music generation task, returns request_id."""
        pass

    async def poll_music(
        self,
        request_id: str,
        max_wait_time: int = 300,
        poll_interval: int = 10
    ) -> str:
        """Poll music generation until complete, returns audio URL."""
        pass

    async def generate_music(
        self,
        prompt: str,
        duration: int = 10
    ) -> str:
        """High-level: submit + poll, returns audio URL."""
        pass
```

### Request/Response Schemas

#### OpenAI Chat Completion Response

```json
{
  "choices": [
    {
      "message": {
        "content": "{\"key\": \"value\"}",
        "role": "assistant"
      },
      "finish_reason": "stop"
    }
  ],
  "model": "gpt-4o-mini",
  "usage": {
    "prompt_tokens": 50,
    "completion_tokens": 30,
    "total_tokens": 80
  }
}
```

#### fal.ai Submit Response

```json
{
  "request_id": "fal-123456789",
  "status": "IN_QUEUE"
}
```

#### fal.ai Status Response

```json
{
  "status": "COMPLETED",
  "result": {
    "images": [
      {"url": "https://fal.media/files/..."}
    ]
  }
}
```

### fal.ai Model-Specific Schemas

#### Nano Banana Pro (Image)

```python
# Input
{
    "prompt": str,              # required, 3-50000 chars
    "aspect_ratio": str,        # 21:9, 16:9, 9:16, 1:1, etc. Default: "1:1"
    "resolution": str,          # 1K, 2K, 4K. Default: "1K"
    "output_format": str,       # jpeg, png, webp. Default: "png"
    "num_images": int,          # 1-4. Default: 1
    "seed": Optional[int]
}

# Output
{
    "images": [
        {
            "url": str,
            "content_type": str,
            "file_name": str,
            "file_size": int,
            "width": int,
            "height": int
        }
    ],
    "description": str
}

# Pricing: $0.15/image, 4K = 2x, web search = +$0.015
# Timeout: 3600s request, 600s startup
```

#### Veo 3.1 (Video)

```python
# Input
{
    "prompt": str,              # required - animation description
    "image_url": str,           # required - 720p+ resolution
    "aspect_ratio": str,        # auto, 16:9, 9:16. Default: "auto"
    "duration": str,            # 4s, 6s, 8s. Default: "8s"
    "resolution": str,          # 720p, 1080p, 4k. Default: "720p"
    "generate_audio": bool,     # Enable built-in audio. Default: true
    "negative_prompt": Optional[str],
    "seed": Optional[int]
}

# Output
{
    "video": {
        "url": str,
        "content_type": str,
        "file_name": str,
        "file_size": int
    }
}

# Pricing: $0.20/sec (no audio), $0.40/sec (with audio) at 720p/1080p
#          $0.40/sec (no audio), $0.60/sec (with audio) at 4k
# Timeout: 3600s request, 600s startup
# Max concurrency: 16
```

#### Lyria2 (Music)

```python
# Input
{
    "prompt": str,              # required, max 2000 chars
    "negative_prompt": str,     # Default: "low quality"
    "seed": Optional[int]
}

# Output
{
    "audio": {
        "url": str,             # WAV file
        "content_type": str,
        "file_name": str,
        "file_size": int
    }
}

# Constraints:
# - Max duration: 30 seconds
# - Format: 48kHz WAV
# - Max concurrency: 2 (queue if exceeded)
# Timeout: 3600s request, 600s startup
```

### Concurrency Control (Lyria 2)

fal.ai Lyria 2 имеет лимит **max 2 concurrent requests**.

**Решение:** Очередь на уровне `fal_client.py`

```python
# fal_client.py
import asyncio

class FalClient:
    def __init__(self):
        # Semaphore для Lyria 2 (max 2 concurrent)
        self._lyria_semaphore = asyncio.Semaphore(2)

    async def generate_music(self, prompt: str, **kwargs) -> str:
        async with self._lyria_semaphore:
            # Только 2 запроса одновременно, остальные ждут
            request_id = await self.submit_music(prompt, **kwargs)
            return await self.poll_music(request_id)
```

**Поведение:**
- Запросы 1-2: выполняются сразу
- Запросы 3+: ждут в очереди пока освободится слот
- Timeout очереди: наследуется от общего request timeout

## Storage

### Environment Variables

```bash
# .env
OPENAI_API_KEY=sk-proj-...
FAL_KEY=...

# Model configurations
LLM_MODEL=gpt-4o-mini
IMAGE_MODEL=fal-ai/nano-banana-pro
VIDEO_MODEL=fal-ai/veo3.1/image-to-video
MUSIC_MODEL=fal-ai/lyria2
```

### TaskTracker Integration

```python
# TaskTracker stores fal.ai request_id for resume
TaskTracker(
    video_id=123,
    step_type="image",
    provider="fal-ai",
    external_task_id="fal-123456789",  # fal.ai request_id
    status=TaskStatus.RUNNING
)
```

## API Changes

### Config Updates

```python
# backend/app/core/config.py

class Settings(BaseSettings):
    # NEW: Direct provider keys
    OPENAI_API_KEY: str = ""
    FAL_KEY: str = ""

    # DEPRECATED: Remove PiAPI
    # PIAPI_KEY: str = ""
    # PIAPI_LLM_URL: str = ""
    # PIAPI_TASK_URL: str = ""

    # Model IDs
    LLM_MODEL: str = "gpt-4o-mini"
    IMAGE_MODEL: str = "fal-ai/nano-banana-pro"
    VIDEO_MODEL: str = "fal-ai/veo3.1/image-to-video"
    MUSIC_MODEL: str = "fal-ai/lyria2"
```

### Service Method Signatures (Unchanged)

Services maintain existing signatures for backward compatibility:

```python
# openai_service.py - NO CHANGES to public API
async def generate_scenario(...) -> Dict[str, Any]
async def validate_content(...) -> Dict[str, Any]
async def generate_json(...) -> Dict[str, Any]

# media_service.py (formerly kling_service.py)
async def generate_image(...) -> str
async def generate_video(...) -> str
async def generate_music(...) -> str
```

## Implementation Steps

### Phase 1: Setup (1h)

1. [ ] Install dependencies: `openai`, `fal-client` in requirements.txt
2. [ ] Add env vars to `.env.example`: `OPENAI_API_KEY`, `FAL_KEY`
3. [ ] Update `config.py`: remove PiAPI vars, add new provider vars
4. [ ] Verify ffmpeg in Dockerfile (already present in media_processor.py)

### Phase 2: OpenAI Client (3h)

1. [ ] Create `backend/app/services/openai_client.py`
   - Implement `chat_completion()` with OpenAI SDK
   - Implement `generate_json()` with structured output
   - Implement `generate_text()` helper
   - Add retry logic (3 attempts, exponential backoff)
   - Add response caching (preserve existing pattern)
   - Add mock mode support

2. [ ] Update `openai_service.py`
   - Replace `from app.services.piapi_client import piapi_client` with `from app.services.openai_client import openai_client`
   - Update `self.client = piapi_client` to `self.client = openai_client`
   - No changes to method signatures

3. [ ] Test OpenAI integration
   - Unit test: `test_openai_client.py`
   - Integration test: Generate scenario via workflow API

### Phase 3: fal.ai Client (5h)

1. [ ] Create `backend/app/services/fal_client.py`
   - Implement image generation (`submit_image`, `poll_image`, `generate_image`)
   - Implement video generation (`submit_video`, `poll_video`, `generate_video`)
   - Implement music generation (`submit_music`, `poll_music`, `generate_music`)
   - Add retry logic with exponential backoff
   - Add polling with configurable intervals
   - Add response caching

2. [ ] Integrate with TaskTracker
   - Save `request_id` to `TaskTracker.external_task_id`
   - Support resume: if `external_task_id` exists, skip submit and poll directly
   - Update status: PENDING → RUNNING → COMPLETED/FAILED

3. [ ] Error handling
   - Rate limiting (429): wait + retry
   - Timeout: mark as FAILED after max_wait_time
   - Provider errors: extract error message, mark as FAILED

### Phase 4: Media Service (4h)

1. [ ] Rename `kling_service.py` → `media_service.py`
   - Update imports: `from app.services.fal_client import fal_client`
   - Replace `self.client = piapi_client` with `self.client = fal_client`

2. [ ] Update `generate_image()`
   - Call `fal_client.generate_image()` with nano-banana-pro
   - Preserve negative_prompt and style_suffix logic

3. [ ] Update `generate_video()`
   - Call `fal_client.generate_video()` with veo3.1
   - Remove `return_task_id` parameter (always save to TaskTracker)
   - Save `request_id` to TaskTracker before polling

4. [ ] Audio workflow (preserve existing 2 modes)

   **Mode 1: Quick (Veo 3.1 built-in audio)**
   ```
   Image → Veo 3.1 (generate_audio=true) → Video with audio
   ```
   - Single API call, no user choice
   - Good for fast prototyping

   **Mode 2: Custom (Lyria2 + ffmpeg)**
   ```
   Image → Veo 3.1 (generate_audio=false) → Silent video
                                                 ↓
   Prompt → Lyria2 → Music variants              ↓
                         ↓                       ↓
               User selects track                ↓
                         ↓                       ↓
                    ffmpeg merge ←───────────────┘
                         ↓
                 Video with selected audio
   ```
   - Multiple audio options for user selection
   - Higher quality control

   **Implementation:**
   - Update `music_generator.py` to call `fal_client.generate_music()` with Lyria 2
   - ffmpeg merge already exists in `media_processor.py` — reuse it

5. [ ] Update workflow.py imports
   - Replace `from app.services.kling_service import kling_service` with `from app.services.media_service import media_service`

### Phase 5: Cleanup (2h)

1. [ ] Find all imports of `piapi_client`:
   ```bash
   grep -r "from app.services.piapi_client" backend/app/
   grep -r "import piapi_client" backend/app/
   ```

2. [ ] Delete deprecated files:
   - `backend/app/services/piapi_client.py` → move to `piapi_client.py.bak`
   - `backend/app/services/aimlapi_client.py`
   - `backend/app/services/providers/kling/image_generator.py`
   - `backend/app/services/providers/kling/video_generator.py`
   - `backend/app/services/providers/kling/__init__.py`
   - `backend/tests/test_services/test_piapi_client.py`

3. [ ] Update additional files:
   - `backend/app/core/music_generator.py` — use fal_client for Lyria2
   - `backend/app/core/models_config.py` — update model configs for fal.ai

3. [ ] Update tests:
   - Remove `piapi_client` mocks
   - Add `openai_client` and `fal_client` mocks

4. [ ] Update documentation:
   - README.md: new env vars
   - CLAUDE.md: update architecture section

### Phase 6: Testing (5h)

1. [ ] Unit tests
   - `test_openai_client.py`: chat_completion, generate_json, retry logic
   - `test_fal_client.py`: submit/poll for image/video/music, caching
   - `test_media_service.py`: generate_image, generate_video, audio merge

2. [ ] Integration tests
   - Full workflow: SCENARIO → IMAGE → VIDEO → AUDIO
   - TaskTracker: verify request_id saved and resumed
   - Cache: verify responses cached correctly

3. [ ] Manual testing
   - Generate real video with audio via workflow API
   - Test retry on rate limit (429)
   - Test resume after simulated crash (stop polling mid-generation)

4. [ ] Build verification
   - `cd backend && venv/bin/pytest`
   - `cd frontend && npm run build`

## Edge Cases

| Case | Handling |
|------|----------|
| **fal.ai rate limit (429)** | Retry after delay from `Retry-After` header, max 3 attempts |
| **Polling timeout** | Mark task as FAILED after max_wait_time, log error |
| **Resume after crash** | Check `TaskTracker.external_task_id`, if exists → skip submit, poll directly |
| **Cache hit in mock mode** | Load from cache_dir if available, else generate mock response |
| **OpenAI JSON parsing error** | Retry generation with clearer instructions in system prompt |
| **ffmpeg merge failure** | Log error, return video without audio, mark task as FAILED |
| **Invalid model ID** | Raise `ValueError` at config load time with clear error message |
| **Missing API key** | Raise `ConfigError` at startup with instructions |

## Error Handling Strategy

### Retry Logic

```python
# Exponential backoff with max 3 attempts
for attempt in range(3):
    try:
        response = await make_request()
        return response
    except RateLimitError as e:
        retry_after = e.retry_after or 2 ** attempt
        if attempt < 2:
            await asyncio.sleep(retry_after)
            continue
        raise
    except TransientError as e:
        if attempt < 2:
            await asyncio.sleep(2 ** attempt)
            continue
        raise
```

### Polling Pattern

```python
# fal.ai polling with timeout
elapsed = 0
while elapsed < max_wait_time:
    status = await fal_client.status_async(model, request_id)

    if status.status == "COMPLETED":
        return status.result
    elif status.status == "FAILED":
        raise ProviderError(status.error)

    await asyncio.sleep(poll_interval)
    elapsed += poll_interval

raise TimeoutError(f"Generation timed out after {max_wait_time}s")
```

### TaskTracker Integration

```python
# Save request_id before polling
tracker = TaskTracker(
    video_id=video.id,
    step_type="video",
    provider="fal-ai",
    status=TaskStatus.RUNNING
)
db.add(tracker)
db.commit()

# Submit task
request_id = await fal_client.submit_video(...)
tracker.external_task_id = request_id
tracker.started_at = datetime.utcnow()
db.commit()

# Poll with resume support
try:
    video_url = await fal_client.poll_video(request_id)
    tracker.status = TaskStatus.COMPLETED
    tracker.result = {"video_url": video_url}
    tracker.completed_at = datetime.utcnow()
except Exception as e:
    tracker.status = TaskStatus.FAILED
    tracker.error_message = str(e)
finally:
    db.commit()
```

## Caching Strategy

### OpenAI Response Caching

```python
# Cache key: hash(method + url + params)
cache_key = hashlib.sha256(
    f"chat_completion:{model}:{messages}".encode()
).hexdigest()[:16]

# Cache structure
data/api_cache/
  llm/
    abc123.json  # {"timestamp": "...", "request": {...}, "response": {...}}
```

### fal.ai Response Caching

```python
# Cache final results only (not intermediate polling)
# IMPORTANT: include seed in cache key for reproducibility
cache_key = hashlib.sha256(
    f"{model}:{prompt}:{seed}:{params}".encode()  # seed included
).hexdigest()[:16]

# Different seed = different cache entry
# prompt="cat", seed=42  → cache_abc123.json
# prompt="cat", seed=99  → cache_def456.json (different!)

data/api_cache/
  image/
    def456.json
  video/
    ghi789.json
  music/
    jkl012.json
```

### Mock Mode

When `settings.MOCK_MODE = True`:
1. Check cache for matching request
2. If found → return cached response
3. If not found → return hardcoded mock from `mock_data.py`

## Migration Plan

### Order of Changes

```
1. Setup (deps, env vars, config)
   ↓
2. OpenAI client + service update
   ↓ (test LLM calls)
3. fal.ai client (all methods)
   ↓
4. Media service update (image, video, music)
   ↓ (test full workflow)
5. Cleanup (delete old code)
   ↓
6. Tests (unit + integration)
   ↓
7. Manual verification
```

### Testing After Each Phase

| Phase | Test |
|-------|------|
| Setup | `python -c "from app.core.config import settings; print(settings.OPENAI_API_KEY[:10])"` |
| OpenAI | `pytest backend/tests/test_openai_client.py` |
| fal.ai | `pytest backend/tests/test_fal_client.py` |
| Media service | Generate image via API: `POST /api/workflow/generate-image` |
| Full workflow | Generate full video: SCENARIO → IMAGE → VIDEO → AUDIO |

### Rollback Procedure

If migration fails:

1. **Restore piapi_client.py**
   ```bash
   mv backend/app/services/piapi_client.py.bak backend/app/services/piapi_client.py
   ```

2. **Revert service changes**
   ```bash
   git checkout backend/app/services/openai_service.py
   git checkout backend/app/services/kling_service.py
   ```

3. **Restore env vars**
   ```bash
   # .env
   PIAPI_KEY=...
   # Remove OPENAI_API_KEY, FAL_KEY
   ```

4. **Run tests**
   ```bash
   pytest backend/
   ```

**Rollback criteria:**
- Critical bugs in production
- >20% regression in generation quality
- API cost exceeds budget by >50%

## Dependencies

### Existing

- `httpx` - HTTP client (already used in piapi_client)
- `asyncio` - Async operations
- `pydantic` - Config management
- `sqlalchemy` - Database ORM
- `ffmpeg` - Audio/video processing (in media_processor.py)

### New

```txt
# requirements.txt
openai==1.58.1
fal-client==0.5.5
```

### Version Compatibility

| Package | Version | Python | Notes |
|---------|---------|--------|-------|
| openai | 1.58.1 | >=3.8 | Latest stable, async support |
| fal-client | 0.5.5 | >=3.8 | Official fal.ai SDK |

## Performance Considerations

### Request Latency

| Operation | Current (PiAPI) | New (Direct) | Change |
|-----------|----------------|--------------|--------|
| LLM call | ~2-3s | ~1-2s | -33% (no proxy) |
| Image gen | ~30-60s | ~20-40s | -33% (direct API) |
| Video gen | ~5-10min | ~3-8min | -20% (Veo 3.1 faster) |
| Music gen | ~2-4min | ~1-2min | -50% (Lyria 2 faster) |

### Cost Comparison

| Operation | PiAPI | Direct | Savings |
|-----------|-------|--------|---------|
| gpt-4o-mini (1M tokens) | $0.15 | $0.15 | $0 |
| nano-banana-pro (image) | $0.105 | $0.08 | -24% |
| veo3.1 (5s video) | $0.30 | $0.25 | -17% |
| lyria2 (music) | $0.20 | $0.15 | -25% |

**Overall:** ~20% cost reduction + better latency.

## Open Questions

- [x] **Audio merge:** Veo 3.1 doesn't support Kling Sound API
  - **Decision:** Generate music separately via Lyria 2, merge locally with ffmpeg

- [x] **Retry strategy:** Same as PiAPI (3 attempts)?
  - **Decision:** Yes, preserve existing retry logic (exponential backoff, 3 attempts)

- [x] **Cache format:** Preserve PiAPI cache structure?
  - **Decision:** Yes, preserve existing cache structure for backward compatibility

- [ ] **Model switching:** Allow user to select models (gpt-4o vs gpt-4o-mini)?
  - **Defer to future task:** Start with fixed models from config, add UI later

- [ ] **Cost tracking:** Log API costs per generation?
  - **Defer to future task:** Add cost tracking in separate metrics system

## Success Criteria

- [ ] All tests passing: `pytest backend/`
- [ ] Full workflow works: SCENARIO → IMAGE → VIDEO → AUDIO
- [ ] TaskTracker correctly stores fal.ai request_ids
- [ ] Resume works: can poll existing request_id after crash
- [ ] Cache works: duplicate requests use cached responses
- [ ] Mock mode works: can run workflow without API keys
- [ ] Error handling: rate limits, timeouts, provider errors handled gracefully
- [ ] Performance: latency improved by 20-30%
- [ ] Cost: per-generation cost reduced by ~20%
- [ ] No regressions: existing workflows continue to work

---

**Ready for review.**
