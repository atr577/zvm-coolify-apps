# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

REGGY - automated platform for creating short viral videos for Instagram Reels, TikTok, and YouTube Shorts using AI (GPT-5 + KLING v2.1 via AIMLAPI).

**Core workflow:** 8-stage pipeline with AI self-validation and user checkpoints at each stage:
Story → Description → Prompt → Image → Scenario → Video → Adaptation → Publishing

## ⚠️ CRITICAL: Working with Shell & autoenv

**Problem:** The system has `autoenv` installed which intercepts shell commands and prompts for .env file approval, blocking automated execution.

**Solution:** ALWAYS use one of these approaches when running shell commands:

### Approach 1: Direct venv/bin execution (RECOMMENDED)
```bash
# Instead of: cd backend && source venv/bin/activate && python ...
# Use direct path:
cd /path/to/backend && venv/bin/python -m uvicorn app.main:app --reload

# Examples:
backend/venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
backend/venv/bin/alembic upgrade head
backend/venv/bin/python -c "from app.main import app; print('OK')"
```

### Approach 2: Unset autoenv environment variable
```bash
unset AUTOENV_ENV_FILENAME && cd backend && source venv/bin/activate && uvicorn app.main:app --reload
```

### Approach 3: Background processes
```bash
# Use run_in_background parameter in Bash tool
# Backend will start without blocking on autoenv prompts
```

**NEVER use:**
- `cd backend && source venv/bin/activate && command` (will block on autoenv)
- Just `cd backend` without unsetting autoenv first

## Tool Usage

### Notifications
**ALWAYS** call terminal-notifier after completing long-running tasks (builds, tests, generation, installations, etc.):

```bash
terminal-notifier -title "Claude Code" -message "message goes here"
```

Use for:
- Build/compilation completed
- Tests finished (passed or failed)
- Video/image generation done
- npm/pip install completed
- Any task taking more than 10-15 seconds

Examples:
- `terminal-notifier -title "Claude Code" -message "Build completed successfully"`
- `terminal-notifier -title "Claude Code" -message "Tests: 15 passed, 2 failed"`
- `terminal-notifier -title "Claude Code" -message "Video generation finished"`
- `terminal-notifier -title "Claude Code" -message "Dependencies installed"`

## Development Commands

### Backend (FastAPI)

```bash
# Setup
cd backend
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# Run development server (RECOMMENDED WAY)
backend/venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Alternative: disable autoenv first
unset AUTOENV_ENV_FILENAME && cd backend && source venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run with Celery worker (for background tasks)
celery -A app.core.celery_app worker --loglevel=info

# Database migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Frontend (React + TypeScript)

```bash
cd frontend

# Setup
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Lint
npm run lint
```

### Full Stack Launch

```bash
# From project root
./start.sh   # Launches both backend and frontend
./stop.sh    # Stops all services
```

## Architecture

### AI Service Layer (Critical)

**Unified AIMLAPI Client** (`backend/app/services/aimlapi_client.py`):
- Single client for both GPT-5.2 and KLING v2.1-master
- Implements retry logic with exponential backoff (3 attempts)
- Handles rate limiting (429) and timeouts
- Async polling for KLING video generation (up to 15 min)

**OpenAI Service** (`backend/app/services/openai_service.py`):
- All text generation uses `aimlapi_client.generate_json()` for structured output
- Validation happens via `validate_content()` after each generation step
- Returns JSON schemas defined in business logic (story schema, description schema, etc.)

**KLING Service** (`backend/app/services/kling_service.py`):
- `generate_image()` - actually uses text-to-video with 5s duration (KLING limitation)
- `generate_video_from_image()` - image-to-video with motion control
- Returns URLs to hosted media

### Workflow State Machine

**Database models** (`backend/app/models/project.py`):
- `Project` - tracks overall workflow state and generated content
- `WorkflowStep` - individual stage (STORY, DESCRIPTION, PROMPT, etc.)
- `ValidationResult` - AI self-validation results for each step

**Status flow:**
```
PENDING → IN_PROGRESS → VALIDATING → AWAITING_APPROVAL → APPROVED → COMPLETED
                             ↓
                    VALIDATION_FAILED (retry up to 3x)
```

**Critical pattern in workflow endpoints** (`backend/app/api/workflow.py`):
1. Create WorkflowStep with status=IN_PROGRESS
2. Call AI service (GPT or KLING)
3. Call `validate_and_save()` helper - runs AI validation
4. Set status to AWAITING_APPROVAL if validation passes
5. User approves/rejects via `/approve-step` endpoint

### Configuration

**All API keys via AIMLAPI** (`backend/.env`):
```
AIMLAPI_KEY=<your-key>           # Single key for GPT + KLING
GPT_MODEL=gpt-5.2
KLING_MODEL=v2.1-master
```

**Settings class** (`backend/app/core/config.py`):
- Uses pydantic-settings
- Required: `AIMLAPI_KEY`, `SECRET_KEY`
- Optional: social media OAuth tokens (Instagram, TikTok, YouTube)

## Key Implementation Details

### Story Generation - Structured Input

**Unlike typical chatbots, story generation uses structured form** (`frontend/src/components/StoryForm.tsx`):
- Theme/niche (text)
- Target audience (text)
- Mood (dropdown: inspirational, funny, motivational, etc.)
- Key elements (text)
- Duration (5 or 10 seconds)
- Platforms (multi-select: instagram, tiktok, youtube)
- Additional notes (textarea)

Backend endpoint (`POST /api/workflow/generate-story`) receives `GenerateStoryRequest` schema with all these fields.

### KLING Image Generation Caveat

**KLING API primarily does video, not static images:**
- `generate_image()` in `kling_service.py` actually calls `generate_video_from_text()` with duration=5
- Returns video URL (can extract first frame client-side if needed)
- For true static images, consider adding DALL-E integration via AIMLAPI

### Validation System

**Every generation step has automated validation:**
- `openai_service.validate_content(content, step_type, previous_data)`
- Returns structured validation with:
  - `status`: "pass" | "pass_with_warnings" | "fail"
  - `score`: 0-100
  - `criteria_results`: per-criterion breakdown
  - `warnings`, `errors`, `recommendations`

**If validation fails:**
- Step status → VALIDATING
- Increment `validation_attempts`
- After 3 failures → VALIDATION_FAILED
- User can edit and retry

### Social Media Publishing

**Not fully implemented - OAuth flows required:**
- Instagram: needs Business Account + access token
- TikTok: OAuth 2.0 flow
- YouTube: OAuth 2.0 flow

Endpoints exist in `backend/app/api/publishing.py` but tokens must be configured in `.env`.

## Common Gotchas

### 1. AIMLAPI vs OpenAI SDK
- **DO NOT** use `openai` package - it's removed from requirements.txt
- All GPT calls go through `aimlapi_client.chat_completion()` (OpenAI-compatible endpoint)
- Use `httpx` for HTTP requests, not `requests` in AI services

### 2. Async Everywhere
- All AI service methods are `async def`
- Workflow endpoints use `async def`
- Use `await` for all service calls
- KLING video generation uses `asyncio.sleep()` for polling

### 3. Database Sessions
- Use `Depends(get_db)` in FastAPI endpoints
- Always `db.commit()` after modifications
- Use `db.refresh(obj)` after commit to get updated state

### 4. CORS Configuration
- Frontend runs on `:3000`, backend on `:8000`
- `CORS_ORIGINS` in config allows both
- Change for production deployment

### 5. File Storage
- Currently local: `data/uploads/` and `data/generated/`
- URLs stored in DB are from AIMLAPI (hosted)
- For production, implement S3 storage

## Testing Strategy

**No test suite currently exists.** When adding tests:

```bash
# Backend tests
cd backend
pytest tests/

# Run specific test
pytest tests/test_workflow.py::test_generate_story

# Frontend tests
cd frontend
npm run test
```

## API Documentation

After starting backend, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

**Key endpoint groups:**
- `/api/projects` - CRUD for projects
- `/api/workflow` - 8 generation stages + validation + approval
- `/api/publish` - Social media publishing (requires OAuth)



## Future Development Areas

1. **WebSocket support** - Real-time progress updates during generation
2. **S3 integration** - Replace local file storage
3. **OAuth flows** - Complete social media authentication
4. **Cost tracking** - Track AIMLAPI spend per project
5. **Batch processing** - Queue multiple videos
6. **Analytics** - Track viral performance post-publish
7. **DALL-E integration** - For true static image generation

## Session Context

See `session-2026-01-07-001.md` for detailed development history including:
- Why AIMLAPI was chosen over other providers
- Evolution of story input from free-text to structured form
- Technical decisions and trade-offs
- Known limitations and workarounds
