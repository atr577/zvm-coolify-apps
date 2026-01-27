---
id: SPEC-T13
title: Привязка социальных аккаунтов к проектам
status: draft
created: 2026-01-27
task: T13
target_sections: [Projects, Publishing, Social Accounts]
---

# Technical Specification: Привязка социальных аккаунтов к проектам

## Overview

Реализация жёсткой привязки социальных аккаунтов к проектам на уровне базы данных и API. Проект = тиражируемая концепция видео для канала. Пользователь подключает социальные аккаунты через OAuth, затем выбирает их для каждого проекта. Публикация видео проекта происходит только в привязанные аккаунты.

**Ключевые решения:**
- Связь Project ↔ SocialAccount many:many (таблица `project_social_accounts` уже существует)
- Поле `platforms` на Project остаётся как fallback для publishing meta если аккаунты не привязаны
- UI ограничена одним аккаунтом на платформу, но backend поддерживает N (архитектурная гибкость)
- **Автомиграция без подтверждения** — при публикации автоматически привязываем аккаунт к проекту (если не привязан). Zero friction.
- **Workspace-level доступ** — все участники workspace видят все подключённые аккаунты, могут привязывать к проектам и публиковать. Подключить/удалить OAuth — только свой.
- **Единая логика публикации** — один UI flow без Phase 1/Phase 2. Если привязан → залочен, если нет → dropdown или OAuth.
- **Publishing meta при bind/unbind — ничего не делать** — пользователь сам нажимает "Regenerate meta" если нужно
- **Показ аккаунта при публикации** — UI показывает @username + аватарку привязанного аккаунта, залочен (смена только в настройках)
- **Авто-синхронизация platforms чекбоксов** — привязка аккаунта Instagram → чекбокс "Instagram" автоматически включается

## Architecture

### Component Diagram

```
┌────────────────┐           ┌──────────────────┐
│   Project      │◄─────────►│ SocialAccount    │
│                │           │                  │
│ - platforms[]  │  M:N      │ - platform       │
│   (fallback)   │           │ - username       │
└────────┬───────┘           │ - access_token   │
         │                   └──────────────────┘
         │
         │ 1:N
         ▼
┌────────────────┐
│   Video        │
│                │
│ - publishing   │
│   _meta        │
└────────────────┘
```

### Data Flow

**Current (T12):**
```
Project.platforms → _generate_publishing_meta() → video.publishing_meta
User picks account manually → publish to platform
```

**New (T13):**
```
Project.social_accounts → derive platforms → _generate_publishing_meta()
                       ↓
                       └─→ publish to project's bound accounts
```

### Workspace-level Access Rights

| Действие | Кто может | Проверка |
|----------|-----------|----------|
| Подключить аккаунт (OAuth) | Только сам пользователь | user_id |
| Видеть аккаунты в workspace | Все участники workspace | workspace membership |
| Привязать аккаунт к проекту | Все участники workspace | workspace membership |
| Отвязать аккаунт от проекта | Все участники workspace | workspace membership |
| Публиковать через привязанный | Все участники workspace | workspace membership |
| Автомиграция при публикации | Все участники workspace | workspace membership |
| Удалить аккаунт (OAuth disconnect) | Только владелец аккаунта | user_id |

**Endpoints для разных контекстов:**
| Endpoint | Возвращает | Используется в |
|----------|-----------|----------------|
| `GET /api/social-accounts/` | Мои аккаунты | Настройки, OAuth manage |
| `GET /api/workspaces/{id}/social-accounts` | Все аккаунты workspace | ProjectForm, привязка |

### Changes Required

| Component | File | Change Type |
|-----------|------|-------------|
| Backend API | `api/projects.py` | Add 3 new endpoints |
| Backend API | `api/workspaces.py` | Add workspace social accounts endpoint |
| Backend Schema | `schemas/project.py` | Modify ProjectResponse |
| Backend Logic | `api/workflow.py` | Update platform derivation |
| Backend Logic | `api/videos.py` | Update platform derivation |
| Backend Logic | `api/publishing.py` | Use bound accounts + workspace access |
| Backend Logic | `services/workflow/prompt_preview.py` | Fix platform derivation |
| Frontend Component | `ProjectForm.tsx` | Add social accounts section |
| Frontend Component | `PublishingSettings.tsx` | Show bound account (locked) |
| Frontend API | `services/api.ts` | Add new endpoints |
| Frontend Types | `types/index.ts` | Add social_accounts to Project |

## Data Structures

### Existing Structures (No Changes)

**Table `project_social_accounts`** (already exists):
```sql
CREATE TABLE project_social_accounts (
  project_id INTEGER NOT NULL,
  social_account_id INTEGER NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (project_id, social_account_id),
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
  FOREIGN KEY (social_account_id) REFERENCES social_accounts(id) ON DELETE CASCADE
);
```

**Relationship** (already exists in `models/project.py`):
```python
social_accounts = relationship(
    "SocialAccount",
    secondary=project_social_accounts,
    back_populates="projects"
)
```

### Storage

- **Where:** PostgreSQL (existing tables)
- **Migration:** NOT NEEDED (table already exists since initial schema)
- **Backend models:** Already defined in `models/project.py` and `models/user.py`

## API Changes

### New Endpoints

```
POST   /api/projects/{project_id}/social-accounts    # Bind account to project
DELETE /api/projects/{project_id}/social-accounts/{account_id}  # Unbind account
GET    /api/projects/{project_id}/social-accounts    # List bound accounts (optional - can use GET /api/projects/{id})
GET    /api/workspaces/{workspace_id}/social-accounts  # List all accounts in workspace
```

### Request/Response

#### POST /api/projects/{project_id}/social-accounts

**Request:**
```json
{
  "social_account_id": 1
}
```

**Response:**
```json
{
  "id": 1,
  "name": "Girls & Cars",
  "platforms": ["instagram", "youtube"],
  "social_accounts": [
    {
      "id": 1,
      "platform": "instagram",
      "username": "myaccount",
      "display_name": "My Account",
      "profile_picture": "https://...",
      "is_active": true,
      "created_at": "2026-01-27T12:00:00Z",
      "is_token_expired": false
    }
  ],
  ...
}
```

**Validation:**
- Account must exist in workspace (any workspace member can bind any workspace account)
- Account must not be already bound to this project
- Return 404 if project or account not found
- Return 403 if project not accessible to user (workspace access check)

#### DELETE /api/projects/{project_id}/social-accounts/{account_id}

**Response:**
```json
{
  "message": "Social account unbound successfully"
}
```

**Validation:**
- Account must be bound to this project
- Return 404 if binding not found

#### GET /api/projects/{project_id}

**Updated Response:** (ProjectResponse now includes `social_accounts`)
```json
{
  "id": 1,
  "name": "Girls & Cars",
  "platforms": ["instagram", "youtube"],  // Fallback if no accounts bound
  "social_accounts": [
    {
      "id": 1,
      "platform": "instagram",
      "username": "myaccount",
      "display_name": "My Account",
      "profile_picture": "https://...",
      "is_active": true,
      "created_at": "2026-01-27T12:00:00Z",
      "is_token_expired": false
    }
  ],
  ...
}
```

#### GET /api/workspaces/{workspace_id}/social-accounts

**Response:** (List of all accounts in workspace)
```json
[
  {
    "id": 1,
    "platform": "instagram",
    "username": "brand1",
    "display_name": "Brand 1",
    "profile_picture": "https://...",
    "is_active": true,
    "created_at": "2026-01-27T12:00:00Z",
    "is_token_expired": false,
    "user_id": 10  // Owner of this account
  },
  {
    "id": 2,
    "platform": "youtube",
    "username": "brand_channel",
    "display_name": "Brand Channel",
    "profile_picture": "https://...",
    "is_active": true,
    "created_at": "2026-01-27T12:00:00Z",
    "is_token_expired": false,
    "user_id": 11  // Different user in same workspace
  }
]
```

**Validation:**
- User must have workspace access (workspace membership check)
- Returns all accounts of all users in workspace
- Used in ProjectForm for account selection

### Schema Changes

**`schemas/project.py`:**

```python
# Add to ProjectResponse
class ProjectResponse(ProjectBase):
    id: int
    workspace_id: Optional[int] = None
    social_accounts: List[SocialAccountResponse] = []  # NEW
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

**New request schema:**

```python
# New in schemas/project.py
class BindSocialAccountRequest(BaseModel):
    social_account_id: int
```

## Backend Logic Changes

### 1. Platform Derivation Helper

**Location:** `api/projects.py` (or new `services/project_service.py`)

```python
def get_project_platforms(project: Project) -> List[str]:
    """
    Derive platforms from bound social accounts with fallback to project.platforms.

    Returns:
        List of platform names (e.g., ["instagram", "youtube"])

    Behavior:
        - is_active=False accounts are excluded (disconnected accounts)
        - Empty social_accounts → fallback to project.platforms
        - Empty platforms → graceful skip (no publishing meta generated)
    """
    if project.social_accounts:
        # Derive from bound accounts (unique platforms, only active)
        active_platforms = list(set(
            acc.platform for acc in project.social_accounts
            if acc.is_active
        ))
        if active_platforms:
            return active_platforms
        # All accounts inactive → fallback to project.platforms

    # Fallback to project.platforms
    return project.platforms or []
```

### 2. Workflow Integration

**File:** `api/workflow.py` (`_generate_publishing_meta`)

**Current:**
```python
if not project or not project.platforms:
    logger.info(f"Skipping publishing_meta: no project or platforms for video {video.id}")
    return

publishing_meta = await openai_service.generate_publishing_meta(
    platforms=project.platforms,
    scenario_data=scenario_data,
    fallback_text=scenario_data.get("image_prompt", project.story_template or "")
)
```

**Updated:**
```python
platforms = get_project_platforms(project)  # NEW helper
if not platforms:
    logger.info(f"Skipping publishing_meta: no platforms for video {video.id}")
    return

publishing_meta = await openai_service.generate_publishing_meta(
    platforms=platforms,  # Use derived platforms
    scenario_data=scenario_data,
    fallback_text=scenario_data.get("image_prompt", project.story_template or "")
)
```

### 3. Regenerate Publishing Meta

**File:** `api/videos.py` (regenerate_publishing_meta endpoint)

Same change as workflow.py:
```python
platforms = get_project_platforms(project)
if not platforms:
    raise HTTPException(status_code=400, detail="No platforms configured for this project")

publishing_meta = await openai_service.generate_publishing_meta(
    platforms=platforms,
    scenario_data=scenario_data,
    fallback_text=scenario_data.get("image_prompt", project.story_template or "")
)
```

### 4. Publishing Flow (Workspace-level Access)

**File:** `api/publishing.py`

**Current:** Endpoints accept `social_account_id` as query parameter or body.

**New (T13):** `social_account_id` ВСЕГДА передаётся. Фронтенд решает откуда взять (из привязки или dropdown). Auto-bind если не привязан.

```python
# In publish_to_instagram, publish_to_tiktok, publish_to_youtube
# After fetching social_account, add MANDATORY validation:

project = video.project
if not project:
    raise HTTPException(
        status_code=400,
        detail="Video has no associated project"
    )

# 1. Validate workspace access (FIRST - before anything)
if not has_workspace_access(current_user, project.workspace_id):
    raise HTTPException(
        status_code=403,
        detail="No access to this project's workspace"
    )

# 2. Validate account belongs to workspace
# (account.user_id must be in workspace members)
account_workspace = get_user_workspace(social_account.user_id)
if account_workspace != project.workspace_id:
    raise HTTPException(
        status_code=403,
        detail="Social account not in project workspace"
    )

# 3. Check token expiration
if social_account.is_token_expired:
    raise HTTPException(
        status_code=400,
        detail="Token expired. Please reconnect your account."
    )

# 4. AUTO-BIND if not bound (without confirmation)
bound_account_ids = {acc.id for acc in project.social_accounts if acc.is_active}
if social_account.id not in bound_account_ids:
    project.social_accounts.append(social_account)
    db.commit()
    logger.info(f"Auto-bound social account {social_account.id} to project {project.id}")

# Continue with publishing...
```

**Key changes:**
- Workspace access check (не owner check)
- Account must belong to workspace (не текущему пользователю)
- Auto-bind без подтверждения (zero friction)
- Логируем автомиграцию

## UI Changes

### 1. Project Form - Social Accounts Section

**Location:** `frontend/src/components/ProjectForm.tsx`

**New Section** (after platforms, before audio settings):

```tsx
{/* Social Accounts Section */}
<div>
  <label className="block text-sm font-medium text-gray-700 mb-2">
    Социальные аккаунты
  </label>
  <p className="text-xs text-gray-500 mb-3">
    Привяжите аккаунты к проекту. Видео будут публиковаться в эти аккаунты.
  </p>

  {/* List of available accounts grouped by platform */}
  <div className="space-y-3">
    {['instagram', 'tiktok', 'youtube'].map(platform => (
      <PlatformAccountSelector
        key={platform}
        platform={platform}
        availableAccounts={socialAccounts?.filter(a => a.platform === platform)}
        selectedAccountId={formData.social_account_bindings?.[platform]}
        onSelect={(accountId) => bindAccount(platform, accountId)}
      />
    ))}
  </div>

  {/* Connect new account button */}
  <button
    type="button"
    onClick={() => {
      // Open OAuth in new tab
      // User authorizes → OAuth redirects back → user closes tab → returns here
      // ProjectForm refetches accounts on mount/visibility change
      window.open('/oauth/<platform>', '_blank')
    }}
    className="mt-3 text-sm text-primary-600 hover:text-primary-700"
  >
    + Подключить новый аккаунт
  </button>
  <p className="text-xs text-gray-500 mt-1">
    Откроется в новой вкладке. После подключения закройте её и вернитесь сюда.
  </p>
</div>
```

**Auto-sync platforms checkboxes:**
When user binds account (e.g., Instagram):
- Automatically enable "Instagram" checkbox in platforms section
- When unbinding last Instagram account → do NOT auto-disable checkbox (preserve meta generation preference)
- User can manually enable/disable checkboxes independently of bound accounts

**New Component:** `PlatformAccountSelector.tsx`

```tsx
interface Props {
  platform: string
  availableAccounts: SocialAccount[]
  selectedAccountId?: number
  onSelect: (accountId: number | null) => void
}

export default function PlatformAccountSelector({
  platform, availableAccounts, selectedAccountId, onSelect
}: Props) {
  // Filter only active accounts
  const activeAccounts = availableAccounts?.filter(acc => acc.is_active) || []

  if (activeAccounts.length === 0) {
    return (
      <div className="flex items-center justify-between p-3 border rounded bg-gray-50">
        <span className="text-gray-600">{getPlatformLabel(platform)}</span>
        <span className="text-xs text-gray-500">Нет подключённых аккаунтов</span>
      </div>
    )
  }

  return (
    <div className="border rounded p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="font-medium">{getPlatformLabel(platform)}</span>
      </div>
      <select
        value={selectedAccountId || ''}
        onChange={(e) => onSelect(e.target.value ? Number(e.target.value) : null)}
        className="w-full px-3 py-2 border rounded"
      >
        <option value="">Не выбрано</option>
        {activeAccounts.map(acc => (
          <option key={acc.id} value={acc.id} disabled={acc.is_token_expired}>
            @{acc.username || acc.display_name}
            {acc.is_token_expired && ' (expired - reconnect)'}
          </option>
        ))}
      </select>
      {/* Warning if selected account has expired token */}
      {selectedAccountId && activeAccounts.find(a => a.id === selectedAccountId)?.is_token_expired && (
        <p className="text-xs text-red-600 mt-2">
          ⚠️ Token expired. Please reconnect this account.
        </p>
      )}
    </div>
  )
}
```

### 2. Publishing Settings - Unified Logic

**Location:** `frontend/src/components/PublishingSettings.tsx` (or `CompletedVideoView.tsx`)

**Единая логика (три состояния):**

| Состояние | UI | Что происходит |
|---|---|---|
| Аккаунт привязан, токен ок | "@brand1" (залочен) + кнопка Publish | `social_account_id` берётся из привязки |
| Аккаунт привязан, токен expired | "@brand1" (серый) + "Reconnect" | Блок публикации |
| Нет привязки, есть аккаунты в workspace | Dropdown "выберите" | Выбрал → автомиграция → публикация |
| Нет аккаунтов вообще | "Подключите аккаунт" + кнопка OAuth | Блок публикации |

**Implementation:**

```tsx
// For each platform (Instagram example)
const boundAccount = project.social_accounts?.find(acc => acc.platform === 'instagram')
const workspaceAccounts = workspaceAccountsQuery.data?.filter(acc => acc.platform === 'instagram') || []

{/* State 1: Bound account, token OK */}
{boundAccount && !boundAccount.is_token_expired && (
  <div className="flex items-center gap-3">
    <img src={boundAccount.profile_picture} className="w-6 h-6 rounded-full" />
    <span className="text-sm text-gray-700">@{boundAccount.username}</span>
    <LockIcon className="w-4 h-4 text-gray-400" title="Смена аккаунта в настройках проекта" />
    <button onClick={() => publish(boundAccount.id)}>Publish to Instagram</button>
  </div>
)}

{/* State 2: Bound account, token expired */}
{boundAccount && boundAccount.is_token_expired && (
  <div className="flex items-center gap-3">
    <img src={boundAccount.profile_picture} className="w-6 h-6 rounded-full opacity-50" />
    <span className="text-sm text-gray-400">@{boundAccount.username}</span>
    <span className="text-xs text-red-600">Token expired</span>
    <button onClick={() => window.open('/oauth/instagram/reconnect')}>Reconnect</button>
  </div>
)}

{/* State 3: No binding, workspace has accounts */}
{!boundAccount && workspaceAccounts.length > 0 && (
  <div className="flex items-center gap-3">
    <select
      value={selectedAccountId || ''}
      onChange={(e) => setSelectedAccountId(Number(e.target.value))}
      className="px-3 py-2 border rounded"
    >
      <option value="">Выберите аккаунт</option>
      {workspaceAccounts.map(acc => (
        <option key={acc.id} value={acc.id} disabled={acc.is_token_expired}>
          @{acc.username || acc.display_name}
          {acc.is_token_expired && ' (expired)'}
        </option>
      ))}
    </select>
    <button
      onClick={() => publish(selectedAccountId)}
      disabled={!selectedAccountId}
    >
      Publish to Instagram
    </button>
    <p className="text-xs text-gray-500">Выбранный аккаунт автоматически привяжется к проекту</p>
  </div>
)}

{/* State 4: No accounts in workspace */}
{!boundAccount && workspaceAccounts.length === 0 && (
  <div className="flex items-center gap-3">
    <span className="text-sm text-gray-500">Нет подключённых Instagram аккаунтов</span>
    <button onClick={() => window.open('/oauth/instagram', '_blank')}>Подключить аккаунт</button>
  </div>
)}
```

**Key points:**
- Смена аккаунта при публикации — нельзя (если привязан)
- Для смены — настройки проекта
- Автомиграция без подтверждения (backend автоматически привяжет)
- `social_account_id` ВСЕГДА передаётся в запросе (из привязки или dropdown)

### 3. Types Update

**File:** `frontend/src/types/index.ts`

```typescript
// Add to Project interface
export interface Project {
  id: number
  workspace_id: number
  name: string
  platforms: string[]
  social_accounts: SocialAccount[]  // NEW
  // ... rest unchanged
}

// Add SocialAccount interface (if not already present)
export interface SocialAccount {
  id: number
  platform: string
  platform_user_id: string
  username: string | null
  display_name: string | null
  profile_picture: string | null
  is_active: boolean
  created_at: string
  is_token_expired: boolean
}
```

### 4. API Client

**File:** `frontend/src/services/api.ts`

```typescript
// Add to projectsApi
export const projectsApi = {
  // ... existing methods

  bindSocialAccount: (projectId: number, accountId: number) =>
    api.post<Project>(`/api/projects/${projectId}/social-accounts`, {
      social_account_id: accountId
    }),

  unbindSocialAccount: (projectId: number, accountId: number) =>
    api.delete(`/api/projects/${projectId}/social-accounts/${accountId}`),
}

// Add to workspacesApi (or create if not exists)
export const workspacesApi = {
  getSocialAccounts: (workspaceId: number) =>
    api.get<SocialAccount[]>(`/api/workspaces/${workspaceId}/social-accounts`),
}
```

## Implementation Steps

1. [ ] **Backend API Endpoints** (2.5h)
   - Add POST/DELETE endpoints in `api/projects.py`
   - Add `GET /api/workspaces/{id}/social-accounts` endpoint (новый)
   - Add `BindSocialAccountRequest` schema in `schemas/project.py`
   - Implement validation (workspace membership, duplicates)
   - Update `ProjectResponse` to include `social_accounts`

2. [ ] **Platform Derivation Helper** (1h)
   - Create `get_project_platforms()` helper in `api/projects.py`
   - Unit test fallback logic
   - Update `services/workflow/prompt_preview.py:83` — заменить `self.project.platforms` на `get_project_platforms(self.project)`

3. [ ] **Workflow Integration** (2h)
   - Update `_generate_publishing_meta()` in `api/workflow.py`
   - Update `regenerate_publishing_meta` in `api/videos.py`
   - Use `joinedload(Project.social_accounts)` in GET project endpoints (eager loading)
   - Test both discover and remix projects

4. [ ] **Publishing Workspace Access** (2h)
   - Implement workspace-level validation in `api/publishing.py`
   - Check workspace access (НЕ owner check)
   - Validate account belongs to workspace
   - Auto-bind without confirmation + log
   - Check `is_token_expired` → 400 if expired
   - Use `joinedload(Project.social_accounts)` for eager loading
   - Test all 3 platforms (instagram, tiktok, youtube)
   - Test workspace-level access (member can publish via any workspace account)

5. [ ] **Frontend Types** (0.5h)
   - Update `types/index.ts`: add `social_accounts` to Project
   - Update API client in `services/api.ts`

6. [ ] **Frontend Components** (5h)
   - Create `PlatformAccountSelector.tsx` component
   - Update `ProjectForm.tsx`: add social accounts section
   - Fetch workspace's social accounts (`GET /api/workspaces/{id}/social-accounts`) on form mount
   - Handle bind/unbind on form submission
   - Show `is_active=false` accounts as "disconnected" (grey, not selectable)
   - Show warning badge on expired tokens
   - OAuth flow: "Connect new account" button → new tab → user closes tab → refetch accounts
   - **Auto-sync platforms checkboxes:** bind Instagram → enable "Instagram" checkbox automatically

7. [ ] **Frontend Publishing - Unified Logic** (2h)
   - Update `PublishingSettings.tsx` or `CompletedVideoView.tsx`: единая логика (3 состояния)
   - **State 1:** Bound account, token OK → @username (locked) + Publish button
   - **State 2:** Bound account, token expired → @username (grey) + Reconnect button
   - **State 3:** No binding, workspace has accounts → Dropdown + Publish (auto-bind на backend)
   - **State 4:** No accounts → "Подключите аккаунт" + OAuth button
   - Fetch workspace accounts for dropdown (`GET /api/workspaces/{id}/social-accounts`)
   - `social_account_id` всегда передаётся (из привязки или dropdown)
   - Смена аккаунта только в настройках проекта

8. [ ] **Testing** (2h)
   - Backend: pytest for bind/unbind endpoints
   - Backend: test platform derivation with/without bound accounts
   - Frontend: `npm run build` without errors
   - E2E: bind account to project → generate video → publish

9. [ ] **Edge Cases & Error Handling** (1h)
   - Account deleted while bound to project (CASCADE deletes binding)
   - Project deleted (CASCADE removes bindings)
   - Token expired: warning badge in UI, 400 error on publish
   - One account used in multiple projects (allowed)
   - is_active=false accounts excluded from platform derivation
   - Empty social_accounts + empty platforms → graceful skip

## Error Handling

| Ситуация | HTTP | Сообщение |
|----------|------|-----------|
| Аккаунт не найден | 404 | Social account not found |
| Аккаунт не в workspace (при bind) | 403 | Social account not in workspace |
| Аккаунт уже привязан к проекту | 409 | Account already bound to project |
| Проект не найден | 404 | Project not found |
| **Публикация в не привязанный аккаунт** | 200 | Auto-binds account + logs + continues (zero friction) |
| Нет workspace access при публикации | 403 | No access to this project's workspace |
| Аккаунт не в workspace (при publish) | 403 | Social account not in project workspace |
| Token expired при публикации | 400 | Token expired. Please reconnect your account. |
| Попытка удалить чужой аккаунт (OAuth) | 403 | Can only delete your own accounts |
| Попытка подключить чужой аккаунт (OAuth) | 403 | Can only connect your own accounts |

## Edge Cases

| Case | Handling |
|------|----------|
| **No accounts bound** | Use `project.platforms` for publishing meta generation. Publishing uses dropdown (workspace accounts) → auto-bind. |
| **Account token expired** | `is_token_expired=true` → show warning badge in UI, block publishing with 400 error + reconnect prompt |
| **Account deleted** | CASCADE delete from `project_social_accounts` (already configured). `video.social_account_id` remains (nullable FK). |
| **Project deleted** | CASCADE delete bindings via `ondelete='CASCADE'` |
| **One account → N projects** | Allowed by design (one account can serve multiple concepts) |
| **User tries to bind account not in workspace** | 403 Forbidden at bind endpoint (validate account.user_id in workspace members) |
| **Duplicate binding** | Check existence before insert, return 409 Conflict |
| **Publishing to unbound account** | Auto-bind account to project (if account in workspace) → log event → continue publish. Zero friction. |
| **Publishing: account not in workspace** | 403 Forbidden (validate account belongs to workspace) |
| **Publishing: no workspace access** | 403 Forbidden (validate workspace access for project) |
| **Workspace-level access** | Any workspace member can see/bind/publish via any workspace account. Validation: workspace membership, NOT account ownership. |
| **OAuth: подключить чужой аккаунт** | Impossible — OAuth returns token to current user only. |
| **OAuth: удалить чужой аккаунт** | 403 Forbidden (validate user_id == current_user.id) |
| **is_active=False accounts** | Excluded from `get_project_platforms()`. Shown as "disconnected" in UI (grey, not selectable). |
| **social_accounts=[] + platforms=[]** | Allow project creation. Publishing meta generation gracefully skipped (no platforms). |
| **Race condition: delete during publish** | Publishing endpoint checks account existence at start. CASCADE handles DB consistency. |
| **OAuth from ProjectForm** | "Connect new account" → opens OAuth in new tab → user authorizes → closes tab → returns to ProjectForm → refetch accounts list |
| **Auto-sync platforms checkboxes** | Bind Instagram account → "Instagram" checkbox auto-enabled. Unbind last account → checkbox NOT auto-disabled. |
| **Workspace with multiple users' accounts** | All members see all accounts. ProjectForm shows owner info (user_id) for clarity. |
| **Publishing screen без привязки** | Dropdown с workspace accounts. Выбрал → автомиграция на backend → публикация. |
| **Смена аккаунта при публикации** | Нельзя (если привязан) — только в настройках проекта. |

## State Combinations

**Platform derivation behavior:**

| social_accounts | project.platforms | Derived Platforms | Publishing Meta | Auto-bind on Publish |
|-----------------|-------------------|-------------------|-----------------|----------------------|
| `[]` | `[]` | `[]` | Not generated (graceful skip) | Yes — first account binds |
| `[]` | `["instagram"]` | `["instagram"]` | Generated for instagram | Yes — first account binds |
| `[instagram_acc]` | `[]` | `["instagram"]` | Generated for instagram | No (already bound) |
| `[inactive_instagram]` | `["instagram"]` | `["instagram"]` | Fallback to platforms (inactive excluded) | Yes — active account auto-binds |
| `[instagram, tiktok]` | `["youtube"]` | `["instagram", "tiktok"]` | Derived from active accounts | No (already bound) |
| `[instagram, inactive_tiktok]` | `[]` | `["instagram"]` | Only active accounts used | Yes if publishing to TikTok with new account |

**Key rules:**
1. Active accounts take priority over `project.platforms`
2. Inactive accounts (`is_active=false`) are excluded
3. If all accounts inactive → fallback to `project.platforms`
4. If both empty → graceful skip (no meta generation)

## Testing

### Manual Tests

- [ ] Create project, bind Instagram account → platforms derived correctly
- [ ] Bind Instagram account → "Instagram" checkbox auto-enabled in platforms
- [ ] Unbind last Instagram account → checkbox NOT auto-disabled
- [ ] Generate video → publishing meta uses derived platforms
- [ ] Unbind account → platforms fallback to `project.platforms`
- [ ] Try to bind account not in workspace → 403 error
- [ ] Delete social account → binding removed automatically
- [ ] Delete project → bindings removed automatically
- [ ] One account → bind to 2 projects → both work independently
- [ ] **Publishing screen state 1:** Bound account, token OK → @username (locked) + Publish button
- [ ] **Publishing screen state 2:** Bound account, expired token → @username (grey) + Reconnect button
- [ ] **Publishing screen state 3:** No binding, workspace has accounts → dropdown + Publish (auto-bind)
- [ ] **Publishing screen state 4:** No accounts → "Подключите аккаунт" + OAuth button
- [ ] Publish with unbound account from dropdown → auto-binds account + continues publish (zero friction)
- [ ] Workspace member sees all workspace accounts in ProjectForm
- [ ] Workspace member binds other user's account to project → success (workspace-level)
- [ ] Workspace member publishes via other user's bound account → success (workspace-level)
- [ ] Publish with account not in workspace → 403 error
- [ ] Publish with expired token → 400 error with "Reconnect" prompt
- [ ] Project with only inactive accounts → fallback to project.platforms
- [ ] OAuth from ProjectForm → new tab → user closes → workspace accounts refetched
- [ ] `GET /api/workspaces/{id}/social-accounts` returns all accounts (all users in workspace)
- [ ] prompt_preview.py uses `get_project_platforms()` correctly

### Build Verification

```bash
# Backend
cd backend && .venv/bin/pytest tests/

# Frontend
cd frontend && npm run build
```

### Unit Tests (Backend)

**File:** `backend/tests/test_projects.py`

```python
def test_bind_social_account(client, db, user, social_account, project):
    """Test binding social account to project"""
    response = client.post(
        f"/api/projects/{project.id}/social-accounts",
        json={"social_account_id": social_account.id},
        headers=auth_headers(user)
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["social_accounts"]) == 1
    assert data["social_accounts"][0]["id"] == social_account.id

def test_bind_account_not_owned(client, db, user, other_user_account, project):
    """Test binding account not owned by user"""
    response = client.post(
        f"/api/projects/{project.id}/social-accounts",
        json={"social_account_id": other_user_account.id},
        headers=auth_headers(user)
    )
    assert response.status_code == 403

def test_unbind_social_account(client, db, user, social_account, project):
    """Test unbinding social account from project"""
    # Bind first
    project.social_accounts.append(social_account)
    db.commit()

    # Unbind
    response = client.delete(
        f"/api/projects/{project.id}/social-accounts/{social_account.id}",
        headers=auth_headers(user)
    )
    assert response.status_code == 200

    # Verify removed
    db.refresh(project)
    assert len(project.social_accounts) == 0

def test_get_project_platforms_with_bindings(db, project, instagram_account, youtube_account):
    """Test platform derivation from bound accounts"""
    project.social_accounts = [instagram_account, youtube_account]
    db.commit()

    platforms = get_project_platforms(project)
    assert set(platforms) == {"instagram", "youtube"}

def test_get_project_platforms_fallback(db, project):
    """Test platform fallback when no accounts bound"""
    project.platforms = ["instagram", "tiktok"]
    project.social_accounts = []
    db.commit()

    platforms = get_project_platforms(project)
    assert platforms == ["instagram", "tiktok"]
```

## Dependencies

### Existing
- SQLAlchemy relationships (already defined)
- FastAPI dependency injection (`get_current_user`, `get_db`)
- React Query for data fetching
- Zustand for local state (if needed)

### New
- None (all dependencies already in place)

## Open Questions

- [x] **Migration needed?** → NO, table exists since initial schema
- [x] **Phase 1 vs Phase 2 for publishing?** → Phase 1: auto-migration (auto-bind on first publish), Phase 2: auto-select
- [x] **Re-generate publishing meta when account bound/unbound?** → Manual only (Phase 1). User clicks "Regenerate meta" button.
- [x] **Auto-bind or 403 on unbound publish?** → Auto-bind (zero friction for existing projects)
- [x] **Workspace-level access?** → Yes. Any workspace member can publish via project's bound accounts.
- [x] **Auto-sync platforms checkboxes?** → Yes. Bind account → enable checkbox. Unbind last account → do NOT disable.
- [x] **OAuth from ProjectForm?** → New tab. User closes tab after auth → returns → refetch accounts.

## Follow-up Tasks (Not in T13)

- [ ] **Show bound account avatars on project card** — display icons/avatars of bound accounts on project list/grid view
- [ ] **Allow unbinding account from project card** — quick unbind without opening project form

## Scope (T13)

**В этом таске:**
- ✅ Bind/unbind API endpoints
- ✅ `GET /api/workspaces/{id}/social-accounts` endpoint
- ✅ Platform derivation with fallback
- ✅ UI for binding accounts in project form (workspace accounts)
- ✅ **Единая логика публикации (3 состояния): залочен / dropdown / OAuth**
- ✅ **Auto-bind without confirmation (zero friction)**
- ✅ **Workspace-level access: all members see/bind/publish via any workspace account**
- ✅ Token expiration check (400 error)
- ✅ Eager loading (joinedload) for performance
- ✅ **Auto-sync platforms checkboxes when binding/unbinding accounts**
- ✅ **OAuth from ProjectForm in new tab**
- ✅ **Fix prompt_preview.py** — use `get_project_platforms()`
- ❌ Auto-regenerate publishing meta (manual button only)

**Future improvements:**
- Publish to multiple accounts at once (batch publishing)
- Show account avatars on project cards
- Quick unbind from project card
- Auto-regenerate publishing meta on bind/unbind (if needed)

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Breaking existing projects without bound accounts | High | Use `platforms` fallback (graceful degradation), no migration needed |
| Token expiration during publishing | Medium | Check `is_token_expired` → 400 error with "Reconnect" prompt. Warning badge in UI. |
| User confusion (platforms vs accounts) | Medium | Clear UI labels: "Социальные аккаунты" section with explanation text |
| Account deleted during publishing | Low | Publishing endpoint checks existence at start. CASCADE handles DB consistency. |
| All accounts inactive | Low | Fallback to `project.platforms`. UI shows all as "disconnected" (grey). |

## Definition of Done

- [ ] Backend API endpoints implemented and tested
- [ ] Platform derivation works with fallback
- [ ] UI allows binding/unbinding accounts
- [ ] Publishing validates bound accounts
- [ ] `pytest` passes (all tests green)
- [ ] `npm run build` passes (no TypeScript errors)
- [ ] Manual E2E test: bind account → generate → publish
- [ ] No breaking changes for existing projects
- [ ] Documentation updated (if needed)

---

**Estimated effort:** 14.5h (updated with new features)
**Actual effort:** TBD
**Status:** Draft → Ready for Review

**Changelog:**
- 2026-01-27: Initial draft
- 2026-01-27: Updated with 6 new decisions from discussion:
  1. Auto-migration (auto-bind on first publish instead of 403)
  2. Show bound account on publish screen (@username + avatar)
  3. OAuth from ProjectForm in new tab (no return_url needed)
  4. Workspace-level access (any workspace member can publish via bound accounts)
  5. Auto-sync platforms checkboxes (bind account → enable checkbox)
  6. Follow-up tasks added (avatars on project card - not in T13)
- 2026-01-27: **Final update (round 2):**
  1. Убрано деление Phase 1/Phase 2 — единая логика публикации (3 состояния)
  2. Автомиграция без подтверждения (zero friction)
  3. Workspace-level доступ (вариант Б): все участники видят/привязывают/публикуют через любые аккаунты workspace
  4. Добавлен endpoint `GET /api/workspaces/{id}/social-accounts`
  5. Обновлена таблица прав workspace
  6. Обновлён publishing flow: workspace validation (не owner validation)
  7. Добавлен шаг: fix prompt_preview.py → use `get_project_platforms()`
  8. Обновлены UI Changes: единая логика экрана публикации (залочен / dropdown / OAuth)
  9. Обновлены Error Handling, Edge Cases, Manual Tests для workspace-level access
