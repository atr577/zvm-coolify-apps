# API Reference

**Версия:** 4.0
**Дата:** 2026-02-05

**Full API docs:** http://localhost:8000/docs (Swagger UI)

---

## Authentication

All endpoints except `/api/auth/login` require JWT token:
```
Authorization: Bearer <access_token>
```

---

## Endpoints

### Auth `/api/auth`

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/login` | Login, returns JWT |
| POST | `/register` | Register with invite token |
| GET | `/me` | Current user info |
| POST | `/setup` | Initial admin setup |

### Workspaces `/api/workspaces`

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | List user's workspaces |
| POST | `/` | Create workspace |
| GET | `/{id}` | Get workspace details |
| PATCH | `/{id}` | Update workspace |
| DELETE | `/{id}` | Delete workspace |
| GET | `/{id}/invites` | List workspace invites |
| POST | `/{id}/invites` | Create invite (owner only) |
| DELETE | `/{id}/invites/{invite_id}` | Delete invite |

### Projects `/api/projects`

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | List projects (filtered by workspace) |
| POST | `/` | Create project |
| GET | `/{id}` | Get project |
| PATCH | `/{id}` | Update project |
| DELETE | `/{id}` | Delete project |
| POST | `/{id}/social-accounts` | Bind social account |
| DELETE | `/{id}/social-accounts/{account_id}` | Unbind social account |

### Videos `/api/videos`

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | List videos |
| POST | `/` | Create video |
| GET | `/{id}` | Get video with workflow state |
| PATCH | `/{id}` | Update video |
| DELETE | `/{id}` | Delete video |

### Workflow `/api/workflow`

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/{video_id}/run-auto` | Run full workflow (AUTO mode) |
| POST | `/{video_id}/generate/{step}` | Generate single step (MANUAL) |
| GET | `/{video_id}/variants/{step}` | Get step variants |
| POST | `/{video_id}/switch/{variant_id}` | Preview variant |
| POST | `/{video_id}/approve/{variant_id}` | Approve and continue |
| POST | `/{video_id}/goto/{step}` | Navigate back to step |
| PATCH | `/{video_id}/update/{step}` | Edit step content |

### Template `/api/template`

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/projects/{id}/settings` | Get template settings |
| PUT | `/projects/{id}/settings` | Update template settings |
| GET | `/projects/{id}/templates` | List video templates |
| POST | `/projects/{id}/templates` | Create video template |
| PATCH | `/templates/{id}` | Update template |
| DELETE | `/templates/{id}` | Delete template |
| GET | `/projects/{id}/variants` | List variants (limit 500) |
| POST | `/projects/{id}/variants` | Create variant |
| POST | `/projects/{id}/variants/csv` | Upload CSV variants |
| DELETE | `/variants/{id}` | Delete variant |
| GET | `/projects/{id}/generations` | List generations |
| POST | `/projects/{id}/generations` | Start single generation |
| POST | `/projects/{id}/generate/batch` | Start batch generation |
| GET | `/generations/{id}` | Get generation status |

#### LLM Variant Generation

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/projects/{id}/variants/generate-prompt` | Generate variant prompt from pipeline |
| POST | `/projects/{id}/variants/generate` | Generate variants preview (not saved) |
| POST | `/projects/{id}/variants/save-generated` | Save previewed variants |

#### Batch Generation

```
POST /api/template/projects/{id}/generate/batch
```

Request:
```json
{
  "mode": "least_used | specific | fill_schedule",
  "count": 10,              // for least_used mode
  "variant_ids": [1, 2, 3], // for specific mode
  "video_template_id": null  // null = use default
}
```

Response:
```json
{
  "batch_id": "uuid",
  "count": 10,
  "generations": [...]
}
```

Modes:
- `least_used` — top N вариантов по usage_count ASC
- `specific` — конкретные variant_ids
- `fill_schedule` — авто-рассчитывает (slots - approved - review - generating)

#### Generation Pipeline

Status flow:
```
pending → preprocessing → generating_image → generating_video → generating_audio → merging_audio → completed
                                                                                              ↓
                                                                                            failed
```

New statuses for music:
- `generating_audio` — Lyria2 generating music track
- `merging_audio` — MediaProcessor merging hook with video

### Discover `/api/discover`

**New in v4.0** — Iterative exploration workflow for discovering new video formats.

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/` | Create discover project |
| GET | `/` | List discover projects |
| GET | `/{id}` | Get project with all rounds |
| DELETE | `/{id}` | Archive project |
| POST | `/{id}/rounds` | Generate next round |
| POST | `/{id}/rounds/{round_id}/select` | Submit selections |
| POST | `/{id}/rounds/{round_id}/retry` | Retry failed items |
| POST | `/{id}/advance` | Advance to video stage |
| POST | `/{id}/advance-extraction` | Advance to extraction |
| POST | `/{id}/rollback` | Roll back last round |
| POST | `/{id}/extract` | Extract template prompts |
| PUT | `/{id}/extraction` | Edit extracted prompts |
| POST | `/{id}/create-template` | Create Template project |

#### Create Discover Project

```
POST /api/discover
```

Request:
```json
{
  "concept": "Industrial hydraulic crusher destroying various objects",
  "name": "Crusher Videos",
  "workspace_id": 1,
  "image_model": "fal-ai/flux-pro/v1.1",
  "video_model": "fal-ai/veo3/fast/image-to-video",
  "image_aspect_ratio": "9:16",
  "video_duration": "6s"
}
```

#### Generate Round

```
POST /api/discover/{id}/rounds
```

Request:
```json
{
  "feedback": "I want more dramatic angles",
  "count": 7  // optional, 1-7
}
```

#### Submit Selection

```
POST /api/discover/{id}/rounds/{round_id}/select
```

Request:
```json
{
  "selections": {
    "1": "selected",
    "2": "rejected",
    "3": "selected"
  },
  "feedback": "More close-up shots"
}
```

### Moderation `/api/projects/{id}/moderation-*`

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/projects/{id}/moderation-queue` | Get pending generations for review |
| POST | `/projects/{id}/moderation-queue/{gen_id}/pre-generate-metadata` | Get/cache publishing metadata |
| POST | `/projects/{id}/moderation-queue/{gen_id}/approve` | Approve with metadata |
| POST | `/projects/{id}/moderation-queue/{gen_id}/reject` | Reject with reason |
| POST | `/projects/{id}/moderation-queue/{gen_id}/regenerate` | Regenerate with optional feedback |
| GET | `/projects/{id}/rejection-archive` | List rejected generations |

#### Metadata flow

1. При создании видео мета генерируется автоматически (кешируется в `publishing_metadata`)
2. `pre-generate-metadata` — возвращает кеш если есть, иначе генерирует и кеширует
3. `approve` — использует: user-edited metadata > cached > generate on-the-fly

### Publishing Schedule `/api/projects/{id}/publishing-*`

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/projects/{id}/publishing-config` | Get schedule config |
| PUT | `/projects/{id}/publishing-config` | Update schedule config |
| GET | `/projects/{id}/publishing-queue` | Get queue items |
| PUT | `/projects/{id}/publishing-queue/{item_id}` | Update queue item metadata |
| DELETE | `/projects/{id}/publishing-queue/{item_id}` | Remove from queue |
| GET | `/projects/{id}/publishing-schedule` | Get computed schedule with slots |

### OAuth `/api/oauth`

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/connect/{platform}` | Get OAuth redirect URL |
| GET | `/{platform}/callback` | OAuth callback handler |

Platforms: `youtube`, `instagram`, `tiktok`

**YouTube Multi-Channel Support:**
- OAuth returns ALL channels associated with the Google account
- Each channel is stored as a separate SocialAccount
- `display_name` format: `"email - channel_name (@handle)"`

### Social Accounts `/api/social-accounts`

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | List connected accounts |
| GET | `/workspace/{id}` | List accounts for workspace |
| DELETE | `/{id}` | Disconnect account |
| POST | `/{id}/refresh` | Refresh OAuth tokens |

### Publish `/api/publish`

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/{video_id}/{platform}` | Publish to platform |
| GET | `/{video_id}/status` | Get publish status |

### Metrics `/api/metrics`

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/videos/{id}` | Get video metrics |
| GET | `/leaderboard` | Top performing videos |
| POST | `/videos/{id}/refresh` | Force refresh metrics |

### Files `/api/files`

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/{path}` | Serve media file |

---

## Common Patterns

### Pagination

```
GET /api/videos?skip=0&limit=20
```

### Filtering

```
GET /api/projects?workspace_id=1&project_type=template
GET /api/videos?project_id=5&status=completed
```

### Error Responses

| Code | Meaning |
|------|---------|
| 400 | Bad request (validation error) |
| 401 | Unauthorized (missing/invalid token) |
| 403 | Forbidden (no permission) |
| 404 | Not found |
| 409 | Conflict (duplicate approve/reject) |
| 422 | Validation error (FastAPI) |
| 503 | Service unavailable (AI service failure) |

### Template Generation Pipeline

```
preprocessing → image_prompt → image → video → audio → merge
```

Each generation goes through these steps:
1. LLM preprocessing of variant data
2. LLM generates image prompt
3. fal.ai generates image
4. fal.ai generates video
5. Lyria2 generates music track (once per batch)
6. MediaProcessor merges hook with video
7. LLM generates publishing metadata (cached)

### Moderation Flow

```
completed → [review] → approved → [queue] → published
                    → rejected (archive)
                    → regenerate → new generation
```

### Discover Flow

```
concept → [images stage] → [videos stage] → extraction → template
             ↓                 ↓
          rounds            rounds
         (narrow)          (narrow)
```
