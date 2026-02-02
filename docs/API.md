# API Reference

**Версия:** 2.0
**Дата:** 2026-01-30

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
| GET | `/projects/{id}/variants` | List variants |
| POST | `/projects/{id}/variants` | Create variant |
| POST | `/projects/{id}/variants/csv` | Upload CSV variants |
| DELETE | `/variants/{id}` | Delete variant |
| GET | `/projects/{id}/generations` | List generations |
| POST | `/projects/{id}/generations` | Start generation |
| GET | `/generations/{id}` | Get generation status |
| POST | `/generations/{id}/cancel` | Cancel generation |

### OAuth `/api/oauth`

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/{platform}/authorize` | Get OAuth redirect URL |
| GET | `/{platform}/callback` | OAuth callback handler |

Platforms: `youtube`, `instagram`, `tiktok`

### Social Accounts `/api/social-accounts`

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | List connected accounts |
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
| 409 | Conflict (invalid state transition) |
| 500 | Server error |

### Workflow States

Video status flow:
```
pending → in_progress → completed
                ↓
              failed
```

Step status flow:
```
pending → in_progress → awaiting_approval → approved
                              ↓
                          regenerate → in_progress
```

---

## WebSocket (Future)

Currently using polling for real-time updates. WebSocket planned for:
- Generation progress
- Metrics updates
