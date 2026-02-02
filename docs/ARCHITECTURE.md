# Архитектура REGGY

**Версия:** 2.1
**Дата:** 2026-02-02

---

## Структура проекта

```
REGGY/
├── .claude/                 # Claude Code config
│   ├── CLAUDE.md            # Project instructions
│   ├── e2e-creds.json       # E2E test credentials (gitignored)
│   └── create-e2e-user.sql  # SQL for creating test user
├── tasks/                   # Task management
│   ├── todo/                # Active tasks
│   └── done/                # Completed tasks
├── docs/                    # Documentation
│   ├── specs/               # Task specifications
│   └── ...
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── api/             # Route handlers
│   │   ├── core/            # Config, security, scheduler
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Business logic & AI clients
│   │   │   └── prompts/     # AI prompt templates
│   │   ├── providers/       # Audio/video provider implementations
│   │   ├── utils/           # Utility functions (urls, etc.)
│   │   └── db/              # Database setup
│   ├── alembic/             # Migrations
│   └── data/media/          # Local media storage
├── frontend/                # React + TypeScript + Vite
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/           # Route pages
│   │   ├── services/        # API client
│   │   ├── contexts/        # React contexts
│   │   ├── hooks/           # Custom hooks
│   │   ├── stores/          # Zustand stores
│   │   └── types/           # TypeScript types
│   └── nginx.conf           # Production nginx config
└── docker-compose.yml       # Production deployment
```

---

## Технологический стек

### Backend

| Категория | Технология |
|-----------|------------|
| Framework | FastAPI (async) |
| ORM | SQLAlchemy 2.0 + Alembic |
| Database | PostgreSQL |
| Auth | JWT (python-jose) + bcrypt |
| HTTP Client | httpx (async) |
| Scheduler | APScheduler |
| Validation | Pydantic 2.x |

### Frontend

| Категория | Технология |
|-----------|------------|
| Framework | React 18 + TypeScript |
| Build | Vite |
| Styling | Tailwind CSS |
| Server State | React Query |
| Client State | Zustand |
| HTTP Client | Axios |
| Routing | React Router 6 |

### AI Services (fal.ai)

| Задача | Модели |
|--------|--------|
| Image | flux-pro, nano-banana-pro |
| Video | veo3.1, kling v2.1 |
| Music | lyria2 |
| LLM | OpenAI gpt-4o-mini, gpt-4o |

### Production

| Компонент | Технология |
|-----------|------------|
| Deploy | Coolify |
| Reverse Proxy | Traefik |
| Containers | Docker Compose |
| Volumes | postgres_data, media_data |

---

## Backend Services

### AI Clients

| Service | File | Purpose |
|---------|------|---------|
| `fal_client` | `services/fal_client.py` | fal.ai SDK: submit + poll for image/video/music |
| `openai_client` | `services/openai_client.py` | OpenAI API: text/JSON generation with validation |
| `media_service` | `services/media_service.py` | High-level wrapper over fal_client |

### Business Logic

| Service | File | Purpose |
|---------|------|---------|
| `media_downloader` | `services/media_downloader.py` | Download & store media locally |
| `metrics_fetcher` | `services/metrics_fetcher.py` | Fetch metrics from social platforms |
| `music_generator` | `core/music_generator.py` | Generate music prompts + tracks |
| `template_generation_service` | `services/template_generation_service.py` | Template project batch generation |
| `placeholder_service` | `services/placeholder_service.py` | CSV parsing + placeholder extraction |

### Prompt Templates

Located in `backend/app/services/prompts/`:

| File | Purpose |
|------|---------|
| `scenario.py` | Scenario generation (Discover) |
| `image_prompt.py` | Image prompt generation |
| `validation.py` | Content validation |
| `variants.py` | Content variants |
| `publishing.py` | Publishing metadata |

---

## Data Models

### Core Entities

```
User ─────────┬──────── Workspace
              │              │
              │              ├── WorkspaceMember
              │              │
              └──────── Project ─────── Video
                             │              │
                             │              └── StepHistory
                             │
                             └── SocialAccount (M2M)
```

### User Management

| Model | Purpose |
|-------|---------|
| `User` | Email/password auth, roles (admin/user) |
| `Workspace` | Project isolation, team collaboration |
| `WorkspaceMember` | User-workspace link (owner/member) |
| `Invite` | Registration tokens |
| `SocialAccount` | OAuth credentials (YouTube/Instagram/TikTok) |

### Content

| Model | Purpose |
|-------|---------|
| `Project` | Video template (discover/remix/template types) |
| `Video` | Generated video instance |
| `StepHistory` | Workflow step variants and history |
| `VideoMetrics` | Platform metrics (views, likes, etc.) |
| `PublishResult` | Publishing status per platform |

### Template-specific

| Model | Purpose |
|-------|---------|
| `VideoTemplate` | Template with image/video prompts |
| `TemplateSettings` | Generation settings for template project |
| `TemplateGeneration` | Batch generation job |
| `Variant` | Generated variant from template |
| `PublishingConfig` | Schedule settings (days, times, depth) |
| `ApprovedGeneration` | Publishing queue item (approved videos) |

---

## Data Flow

### Discover Workflow

```
1. User creates Project (type=discover)
   └── story_template = creative concept

2. User creates Video
   └── workflow_mode = AUTO | MANUAL

3. Workflow executes:
   SCENARIO: LLM generates image_prompt + motion_prompt
      ↓
   IMAGE: fal.ai generates image from prompt
      ↓
   VIDEO: fal.ai generates video from image + motion
      ↓
   AUDIO: fal.ai Lyria2 generates music

4. Video completed → publishing_meta generated
```

### Template Workflow

```
1. User creates Project (type=template)
   └── TemplateSettings (models, duration, prompts)
   └── VideoTemplate[] (image_prompt, video_prompt per variant)

2. User uploads CSV or creates Variants manually

3. User starts TemplateGeneration
   └── For each Variant:
       IMAGE → VIDEO → AUDIO (parallel where possible)

4. User moderates (approve/regenerate/reject)
   └── Approved → ApprovedGeneration (publishing queue)

5. Scheduler publishes at configured slots
   └── PublishingConfig: days, times, timezone
   └── FIFO queue assignment to slots
```

---

## Authentication Flow

```
1. Login: POST /api/auth/login
   └── Returns: access_token (JWT)

2. All requests: Authorization: Bearer <token>

3. Token contains: user_id, workspace_id, role

4. Dependencies:
   - get_current_user → User
   - get_current_workspace → Workspace
```

### OAuth Flow (Social Accounts)

```
1. GET /api/oauth/{platform}/authorize
   └── Returns: redirect URL to platform

2. User authorizes on platform

3. Platform redirects to /api/oauth/{platform}/callback
   └── Creates/updates SocialAccount with tokens

4. Tokens used for publishing
```

---

## File Storage

### Local Storage (Development & Production)

```
backend/data/media/
├── images/          # Generated images
├── videos/          # Generated videos (no audio)
├── audio/           # Generated music tracks
└── final/           # Videos with audio
```

### URL Pattern

```
/api/files/{path}  →  backend/data/media/{path}
```

nginx proxies `/api/` to backend, including file serving.

---

## Background Jobs

### APScheduler

| Job | Schedule | Purpose |
|-----|----------|---------|
| `fetch_video_metrics` | Every 6 hours | Update metrics from social platforms |
| `cleanup_old_media` | Daily | Remove orphaned media files |
| `publish_scheduled` | Every minute | Publish videos at scheduled slots |

Jobs stored in PostgreSQL, survive restarts.

---

## Key Patterns

### Async Everywhere

All AI service methods are async:
```python
async def generate_image(prompt: str) -> str:
    result = await fal_client.submit_and_poll(...)
    return result.url
```

### fal.ai Submit + Poll

```python
# Submit job
request_id = await fal_client.submit(model, params)

# Poll until complete
while True:
    status = await fal_client.get_status(request_id)
    if status.completed:
        return status.result
    await asyncio.sleep(poll_interval)
```

### Database Sessions

```python
@router.get("/items")
async def get_items(db: Session = Depends(get_db)):
    return db.query(Item).all()
```

### URL-based State (Frontend)

Every UI state has a URL:
```
/workspaces/:id     # Selected workspace
/projects/:id/edit  # Project editing
/videos/:id         # Video detail
```
