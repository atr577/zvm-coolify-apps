# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

<!-- PROJECT: RE | VERSION: 2.5 -->

## Workflow (MANDATORY)

**Ключевой принцип:** Каждый этап заканчивается Summary + OK от пользователя.

### Feature Flow
```
IDEA → TASK → [SPEC] → REVIEW → CODE → TEST → COMMIT → MERGE → DONE
         ↓       ↓        ↓                              ↓
      summary summary  FINAL OK                       User OK
       + OK    + OK
```

| Step | Action | Agent | Output |
|------|--------|-------|--------|
| 1. IDEA | User describes feature | — | — |
| 2. TASK | Create task file | `task-manager` | Summary → OK |
| 3. SPEC | Create technical spec (if needed) | `spec-writer` | Summary → OK |
| 4. validate | Check task/spec quality | `task-validator` / `spec-validator` | Pass/Fail |
| 5. REVIEW | Final summary before code | `review` | **Final OK** |
| 6. CODE | Implementation | manual | — |
| 7. TEST | `pytest` + `npm run build` | manual | — |
| 8. COMMIT | Git commit | manual | — |
| 9. MERGE | Merge to main | manual | **User OK** |
| 10. DONE | Move task to done/ | `task-manager` | — |

### Bug Flow
```
BUG → RCA → TASK → [SPEC] → REVIEW → FIX → TEST → COMMIT → MERGE → DONE
        ↓      ↓       ↓        ↓                            ↓
     summary summary summary  FINAL OK                    User OK
      + OK    + OK    + OK
```

### Agents

| Agent | Purpose |
|-------|---------|
| `task-manager` | Create and manage task files |
| `task-validator` | Validate task file quality |
| `spec-writer` | Create technical specifications |
| `spec-validator` | Validate spec quality |
| `review` | Final summary and approval before CODE |
| `rca-manager` | Root cause analysis for bugs |

**Agents location:** `.claude/agents/`

**NEVER skip Summary + OK. NEVER start CODE without REVIEW approval.**

---

### Summary Format (MANDATORY)

**КРИТИЧНО:** Каждый Summary ОБЯЗАН начинаться с продуктовой ценности. Без этого summary не считается complete.

| # | Секция | Описание | Обязательно |
|---|--------|----------|-------------|
| 1 | **Для пользователя** | Что изменилось в UX/функционале, бизнес-ценность | ✅ YES |
| 2 | **Техническое** | Файлы, модели, API, миграции | ✅ YES |
| 3 | **Ветка/статус** | Где код, что дальше, "Мержить?" | ✅ YES |

**Правило:** Если не можешь объяснить ценность для пользователя — возможно делаешь не то.

**Пример:**

```
**Для пользователя:**
- Картинки и видео теперь сохраняются локально и не пропадают через время

**Техническое:**
| Что | Детали |
|-----|--------|
| Models | StepAttempt, Variant |
| API | /api/files/{type}/{filename} |
| Migration | alembic + script |

**Ветка:** `feature/T33-local-media`
**Мержить?**
```

---

### Skip Evaluation

SPEC опционален. Claude оценивает и предлагает:

**SPEC нужен если:**
- Новые структуры данных
- API изменения
- Сложная логика (>50 строк)
- 3+ файлов затронуто

**SPEC не нужен если:**
- Локальное изменение (1-2 файла)
- Понятный scope
- Нет архитектурных решений

---

### На "НЕТ" — Итерация

```
User: "Нет, не так"
Claude: "Что именно не так?
- [вопрос 1]?
- [вопрос 2]?"
→ обсуждение
→ обновление документа
→ новый Summary
→ OK?
```

Цикл повторяется пока не получен OK.

---

### Validator Fail Protocol

При ошибке валидации — стоп и обсуждение:

```
❌ Validation failed

Проблемы:
1. [проблема] — исправление: [как]
2. [проблема] — исправление: [как]

Вопросы для автоисправления:
- [вопрос]?

Исправить автоматически? (да / нет / обсудить)
```

---

## Hard Stops

**NEVER:**
- Write code without task file in `tasks/`
- Fix bugs without RCA (use `rca-manager`)
- Skip Summary + OK at any stage
- **Write Summary without product/user value** (что изменилось для пользователя)
- Start CODE without REVIEW approval
- **Merge to main without explicit user approval** (always ask "Мержить?")
- Merge to main without tests passing
- Commit secrets or .env files

**Build verification:**
- Backend: `cd backend && venv/bin/pytest`
- Frontend: `cd frontend && npm run build`
- Max 1 retry on failure, then stop and report

---

## Architecture Principles

**Один источник правды:**
- НИКОГДА не создавать v2, v3, v4 файлов — переписывать оригинал
- Если нужен "новый подход" — сначала удалить старый код, потом писать новый
- Один API endpoint, одна модель, один сервис для каждой функции

**Удалять сразу:**
- При создании нового кода — удалять старый в том же PR
- Не оставлять "на всякий случай" или "для обратной совместимости"
- Мёртвый код = tech debt = будущие баги

**Архитектура ДО кода:**
- Обсудить структуру данных и API до написания кода
- Если задача затрагивает 3+ файлов — нужен SPEC
- При сомнениях — спросить, не угадывать

**Признаки проблемы:**
- Файлы с суффиксами `_v2`, `_v3`, `_new`, `_old` — удалить дубликаты
- Несколько моделей для одной сущности — оставить одну
- Код который "возможно понадобится" — удалить

---

## Project Structure

```
.
├── .claude/agents/     # Agent definitions
├── tasks/              # Task management
│   ├── todo/           # status: todo
│   └── done/           # status: done
├── docs/
│   ├── specs/          # SPEC-*.md (technical specs)
│   └── rca/            # RCA-*.md (root cause analysis)
├── backend/            # FastAPI application
└── frontend/           # React application
```

---

## Git

- Feature: `feature/T<id>-<slug>`
- Bug fix: `fix/T<id>-<slug>`
- Base: `main`

---

## Project Overview

REGGY - automated platform for creating short viral videos for Instagram Reels, TikTok, and YouTube Shorts using AI (GPT + KLING via PiAPI).

**Core workflow:** 8-stage pipeline with AI self-validation and user checkpoints at each stage:
Story → Description → Prompt → Image → Scenario → Video → Audio → Adaptation

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

**PiAPI Client** (`backend/app/services/piapi_client.py`):
- Single client for GPT + KLING via PiAPI provider
- Implements retry logic with exponential backoff (3 attempts)
- Handles rate limiting (429) and timeouts
- Async polling for KLING video generation (up to 15 min)

**OpenAI Service** (`backend/app/services/openai_service.py`):
- All text generation uses `piapi_client.generate_json()` for structured output
- Validation happens via `validate_content()` after each generation step

**KLING Service** (`backend/app/services/kling_service.py`):
- `generate_image()` - uses text-to-video with 5s duration (KLING limitation)
- `generate_video_from_image()` - image-to-video with motion control

### Workflow State Machine

**Database models:**
- `Video` (`backend/app/models/video.py`) - tracks workflow state and generated content
- `WorkflowStep` - individual stage (STORY, DESCRIPTION, PROMPT, etc.)
- `ValidationResult` - AI self-validation results for each step

**Status flow:**
```
PENDING → IN_PROGRESS → VALIDATING → AWAITING_APPROVAL → APPROVED → COMPLETED
                             ↓
                    VALIDATION_FAILED (retry up to 3x)
```

### Configuration

**API keys via PiAPI** (`backend/.env`):
```
PIAPI_KEY=<your-key>             # Single key for GPT + KLING
LLM_MODEL=gpt-4o-mini            # gpt-4o-mini, gpt-4o, claude-3-7-sonnet-20250219
VIDEO_MODEL=kling-2.5            # kling-1.5, kling-2.1, kling-2.5, kling-2.6
```

**Settings class** (`backend/app/core/config.py`):
- Uses pydantic-settings
- Required: `PIAPI_KEY`, `SECRET_KEY`
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

### 1. PiAPI vs OpenAI SDK
- **DO NOT** use `openai` package directly
- All GPT calls go through `piapi_client` (OpenAI-compatible endpoint)
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
- URLs stored in DB are from PiAPI (hosted)
- For production, implement S3 storage

## Testing

```bash
# Run all backend tests
backend/venv/bin/pytest

# Run specific test file
backend/venv/bin/pytest tests/test_workflow.py

# Run specific test function
backend/venv/bin/pytest tests/test_workflow.py::test_generate_story

# Skip slow/integration tests
backend/venv/bin/pytest -m "not slow"
backend/venv/bin/pytest -m "not integration"
```

Test markers defined in `backend/pytest.ini`:
- `slow` - Long-running tests
- `integration` - Tests requiring external services

## API Documentation

After starting backend, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

**Key endpoint groups:**
- `/api/auth` - Registration, login, JWT tokens
- `/api/workspaces` - Workspace management
- `/api/projects` - Project templates (CRUD)
- `/api/videos` - Individual video generation
- `/api/workflow` - 8 generation stages + validation + approval
- `/api/publish` - Social media publishing (requires OAuth)
- `/api/metrics` - Analytics and performance tracking

---

## Key Documents

| Document | Purpose |
|----------|---------|
| `docs/specs/TARGET_WORKFLOW.md` | Master spec for workflow architecture |
| `docs/specs/ARCHITECTURE.md` | System architecture overview |

---

**Updated:** 2026-01-11 | **Version:** 2.5
