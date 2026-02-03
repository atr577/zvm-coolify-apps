---
id: SPEC-T28
title: Template Project Tab Restructuring
status: draft
created: 2026-02-03
task: T28
target_sections: [Template Projects, Pipeline]
---

# Technical Specification: Template Project Tab Restructuring

## Overview

Restructure template project view tabs to separate pipeline configuration from generation execution and provide a dedicated Details tab for project settings. Current Pipeline tab mixes configuration (5 accordion steps), batch launching (GenerationPanel), and full generation history (GenerationsList), which creates cognitive overload.

**Current:** Dashboard / Review / Pipeline (Configure + Run + History)
**Target:** Dashboard / Generate / Review / Details

## Problem

### Current Structure Issues

1. **Cognitive Overload:** Pipeline tab tries to do too much — configure settings, launch batches, and review full history
2. **Unclear Workflow:** Users must scroll past configuration accordion every time they want to start a batch
3. **Hidden Settings:** Project settings (name, description, workspace) live on a separate `/project/{id}/edit` page
4. **History vs Action:** Full GenerationsList shows all past generations, making it hard to focus on current batch progress

### User Mental Model

```
Configure (once) → Generate (repeatedly) → Review (moderation) → Dashboard (publishing)
```

Current tab structure doesn't match this flow.

## Solution

### New Tab Structure

#### 1. Dashboard (unchanged)
- Publishing calendar
- Performance metrics
- Quick actions

#### 2. Generate (new — replaces Pipeline → Run)
- **GenerationPanel** — variant selection + Run button (stays as-is)
- **BatchProgress** — compact active batch progress (replaces full GenerationsList)
  - Show only batches with in-progress generations
  - Compact progress bars: "7/10 completed, 1 failed, 2 in progress"
  - Retry failed generations inline
  - Completed generations → go to Review tab
  - No individual generation cards, no pagination

#### 3. Review (unchanged)
- Moderation queue
- Approve/reject interface

#### 4. Details (new — combines Configure + Settings)
- **ConfigureSection** — 5 accordion steps (moves from Pipeline)
- **Project Settings** — name, description, workspace (inline, not separate page)
- Single StickySaveBar for all changes

## Architecture

### Component Diagram

```
TemplateProjectView
├── DashboardScreen (no changes)
├── GenerateScreen (NEW)
│   ├── GenerationPanel (existing, no changes)
│   └── BatchProgress (NEW)
├── ReviewScreen (no changes)
└── DetailsScreen (NEW)
    ├── ConfigureSection (existing, moved from PipelineScreen)
    └── ProjectSettingsInline (NEW)
```

### Changes Required

| Component | File | Change Type |
|-----------|------|-------------|
| TemplateProjectView | `frontend/src/components/template/TemplateProjectView.tsx` | Modify |
| GenerateScreen | `frontend/src/components/template/GenerateScreen.tsx` | Add |
| BatchProgress | `frontend/src/components/template/BatchProgress.tsx` | Add |
| DetailsScreen | `frontend/src/components/template/DetailsScreen.tsx` | Add |
| ProjectSettingsInline | `frontend/src/components/template/ProjectSettingsInline.tsx` | Add |
| PipelineScreen | `frontend/src/components/template/PipelineScreen.tsx` | Delete |
| TemplateSettingsForm | `frontend/src/components/template/TemplateSettingsForm.tsx` | Modify |
| App routing | `frontend/src/App.tsx` | Modify |

## Data Structures

### Active Batch Tracking

No new backend structures needed. Frontend uses existing `Generation` type and groups by `batch_id`.

```typescript
interface ActiveBatch {
  batch_id: string
  generations: Generation[]
  created_at: string
  total: number
  completed: number
  failed: number
  in_progress: number
}
```

Derived from `listGenerations` response, filtered to batches with at least one generation in `['pending', 'preprocessing', 'generating_image', 'generating_video']` status.

### Project Settings State

```typescript
interface ProjectSettingsState {
  name: string
  description: string
  workspace_id: number | undefined
}
```

Integrated into DetailsScreen local state, saved via StickySaveBar alongside ConfigureSection changes.

## Implementation Steps

### Step 1: Create BatchProgress Component

**File:** `frontend/src/components/template/BatchProgress.tsx`

**Features:**
- Fetch generations using existing `templateApi.listGenerations(projectId, { limit: 50 })`
- Filter and group by `batch_id` (reuse `groupByBatch` logic from GenerationsList)
- Show only batches with `isActive = generations.some(g => ['pending', 'preprocessing', 'generating_image', 'generating_video'].includes(g.status))`
- Compact UI: progress bar, status counts
- Retry button for failed generations
- Poll every 3 seconds while active batches exist
- When all batches complete → show "No active batches" + link to Review tab

**UI Layout:**
```
┌─────────────────────────────────────────────┐
│ Batch — 10 videos                           │
│ ████████░░ 7/10 completed, 1 failed, 2 in progress │
│ [Retry Failed]                              │
└─────────────────────────────────────────────┘
```

### Step 2: Create GenerateScreen Component

**File:** `frontend/src/components/template/GenerateScreen.tsx`

**Structure:**
- Left column (1/3): GenerationPanel (existing, import as-is)
- Right column (2/3): BatchProgress (new)
- Pass `onBatchStarted` callback to refresh BatchProgress

### Step 3: Create ProjectSettingsInline Component

**File:** `frontend/src/components/template/ProjectSettingsInline.tsx`

**Features:**
- Form fields: name (required), description (optional), workspace (select, if multiple workspaces)
- Load via `projectsApi.get(projectId)` and `workspacesApi.list()`
- Return edited state to parent (DetailsScreen)
- No Save button — parent handles via StickySaveBar

**Structure:**
```tsx
export function ProjectSettingsInline({
  projectId,
  editedSettings,
  onSettingsChange,
}: {
  projectId: number
  editedSettings: { name: string; description: string; workspace_id?: number }
  onSettingsChange: (settings: { name: string; description: string; workspace_id?: number }) => void
}) {
  // Load workspaces, render form
}
```

### Step 4: Create DetailsScreen Component

**File:** `frontend/src/components/template/DetailsScreen.tsx`

**Features:**
- Combine ConfigureSection (existing, import) + ProjectSettingsInline (new)
- Manage unified dirty state for both
- Single StickySaveBar that saves:
  - ConfigureSection changes (via `templateApi.updateSettings` + `publishingScheduleApi.updateConfig`)
  - Project settings changes (via `projectsApi.update`)
- Layout: ConfigureSection first, then ProjectSettingsInline below

**State Management:**
```typescript
const [configDirty, setConfigDirty] = useState(false)
const [settingsDirty, setSettingsDirty] = useState(false)
const isDirty = configDirty || settingsDirty

const handleSave = async () => {
  // Save configure changes if dirty
  // Save project settings if dirty
}
```

### Step 5: Update TemplateProjectView

**File:** `frontend/src/components/template/TemplateProjectView.tsx`

**Changes:**

1. Update `ScreenType`:
```typescript
type ScreenType = 'dashboard' | 'generate' | 'review' | 'details'
```

2. Update `VALID_SCREENS`:
```typescript
const VALID_SCREENS: ScreenType[] = ['dashboard', 'generate', 'review', 'details']
```

3. Update `TAB_TO_SCREEN` (backward compatibility):
```typescript
const TAB_TO_SCREEN: Record<string, ScreenType> = {
  pipeline: 'generate',  // OLD pipeline → generate
  generate: 'generate',
  variants: 'generate',
  templates: 'details',
  moderation: 'review',
  publishing: 'dashboard',
}
```

4. Update tab buttons (replace "Pipeline" with "Generate" and "Details"):
```tsx
<button onClick={() => handleNavigate('generate')}>Generate</button>
<button onClick={() => handleNavigate('details')}>Details</button>
```

5. Update screen rendering:
```tsx
{currentScreen === 'generate' && (
  <GenerateScreen
    projectId={projectId}
    generationsRefresh={generationsRefresh}
    onBatchStarted={handleBatchStarted}
  />
)}

{currentScreen === 'details' && (
  <DetailsScreen projectId={projectId} />
)}
```

6. Update smart default logic (if needed):
```typescript
// No variants → details (setup)
if (statsData.variants_count === 0) {
  defaultScreen = 'details'
}
```

### Step 6: Update TemplateSettingsForm

**File:** `frontend/src/components/template/TemplateSettingsForm.tsx`

**Change:** Update link text to point to new Details tab:
```tsx
<p className="text-sm text-gray-500">
  Pipeline configuration (models, prompts, templates, social accounts, schedule) has moved to{' '}
  <button
    type="button"
    onClick={() => navigate(`/?project=${projectId}&screen=details`)}
    className="text-primary-600 hover:underline"
  >
    Details tab
  </button>
  .
</p>
```

### Step 7: Update App Routing

**File:** `frontend/src/App.tsx`

**Change:** Redirect `/project/:id/edit` to `/?project={id}&screen=details`:

```tsx
<Route
  path="/project/:id/edit"
  element={<Navigate to="/" replace />}
/>
```

Update `PrivateRoute` wrapper (if used) to handle query params:
```tsx
// In MainLayout or wherever project edit route is handled
useEffect(() => {
  const projectId = params.id
  if (location.pathname === `/project/${projectId}/edit`) {
    navigate(`/?project=${projectId}&screen=details`, { replace: true })
  }
}, [location.pathname, params.id])
```

### Step 8: Delete PipelineScreen

**File:** `frontend/src/components/template/PipelineScreen.tsx`

**Action:** Delete file (no longer needed).

## Data Flow

### Generate Tab Flow

```
User clicks "Run — N videos"
    ↓
GenerationPanel → templateApi.startBatchGeneration()
    ↓
onBatchStarted callback → BatchProgress refreshes
    ↓
BatchProgress polls templateApi.listGenerations() every 3s
    ↓
Filters generations by batch_id + active status
    ↓
Displays progress bars + Retry buttons
    ↓
When all batches complete → "Go to Review" link
```

### Details Tab Flow

```
Load DetailsScreen
    ↓
Fetch projectsApi.get(projectId) + templateApi.getSettings() + publishingScheduleApi.getConfig()
    ↓
Render ConfigureSection + ProjectSettingsInline
    ↓
User edits fields → mark dirty
    ↓
Click Save → StickySaveBar calls:
    - templateApi.updateSettings() (if config dirty)
    - publishingScheduleApi.updateConfig() (if config dirty)
    - projectsApi.update() (if settings dirty)
    ↓
Reset dirty state
```

## URL Routing Changes

### Old → New Mapping

| Old URL | New URL | Action |
|---------|---------|--------|
| `?screen=pipeline` | `?screen=generate` | Auto-redirect (backward compat) |
| `?tab=pipeline` | `?screen=generate` | Auto-redirect (backward compat) |
| `?tab=templates` | `?screen=details` | Auto-redirect |
| `/project/{id}/edit` | `/?project={id}&screen=details` | Redirect |

### Implementation

**In TemplateProjectView:**
```typescript
const getScreenFromUrl = (): ScreenType | null => {
  const screenParam = searchParams.get('screen')
  if (screenParam && VALID_SCREENS.includes(screenParam as ScreenType)) {
    return screenParam as ScreenType
  }
  // Backward compatibility: old ?tab= params
  const tabParam = searchParams.get('tab')
  if (tabParam && tabParam in TAB_TO_SCREEN) {
    return TAB_TO_SCREEN[tabParam]
  }
  // Legacy ?screen=pipeline → generate
  if (screenParam === 'pipeline') {
    return 'generate'
  }
  return null
}
```

## Edge Cases

| Case | Handling |
|------|----------|
| No active batches | BatchProgress shows "No active batches. Recent completions have been moved to Review." + link to Review tab |
| All generations in batch failed | Show "All failed" badge + Retry All button |
| Batch with mixed success/failure | Show "7/10 completed, 3 failed" + Retry Failed button |
| User navigates away during batch | Polling stops (component unmounted), resumes if user returns to Generate tab |
| Old URL `?screen=pipeline` | Auto-redirect to `?screen=generate` on mount |
| Settings form in Details has validation error | Prevent Save until valid (e.g., project name required) |
| ConfigureSection + ProjectSettings both dirty | Single Save button saves both atomically, rollback both on error |
| No workspace selector needed (single workspace) | Hide workspace field in ProjectSettingsInline |

## Testing

### Manual Tests

- [ ] Navigate to Generate tab → see GenerationPanel + BatchProgress
- [ ] Start batch → BatchProgress updates with progress bar
- [ ] Batch completes → BatchProgress shows "No active batches"
- [ ] Navigate to Details → see ConfigureSection + Project Settings
- [ ] Edit project name in Details → Save → verify name updated
- [ ] Edit preprocessing prompt + project description → Save → both save correctly
- [ ] Old URL `/?project=X&screen=pipeline` → redirects to `?screen=generate`
- [ ] Old route `/project/X/edit` → redirects to `/?project=X&screen=details`
- [ ] BatchProgress polling: start batch, navigate away, return → polling resumes
- [ ] Failed generation → Retry button works in BatchProgress
- [ ] All generations fail → Retry All button appears
- [ ] No active batches → message + Review link shown

### Build Verification

- [ ] `npm run build` passes (no TypeScript errors)
- [ ] `npm run dev` works, all tabs render
- [ ] No console errors on tab navigation

## Dependencies

### Existing (reuse)
- `templateApi.listGenerations()` — for BatchProgress data
- `templateApi.startBatchGeneration()` — already in GenerationPanel
- `templateApi.retryGeneration()` — for Retry button
- `projectsApi.get()`, `projectsApi.update()` — for project settings
- `workspacesApi.list()` — for workspace selector
- `ConfigureSection` component — move to DetailsScreen
- `GenerationPanel` component — move to GenerateScreen
- `StickySaveBar` component — reuse in DetailsScreen
- `groupByBatch()` logic from GenerationsList — adapt for BatchProgress

### New
- No new backend endpoints required
- No new API methods required

## Migration Path

### For Users

1. Existing bookmarks/links with `?screen=pipeline` will auto-redirect to `?screen=generate`
2. Settings gear icon (currently → `/project/{id}/edit`) will navigate to `?screen=details`
3. No data migration required (all backend stays the same)

### For Developers

1. Update any internal links from `?screen=pipeline` to `?screen=generate`
2. Remove PipelineScreen component imports
3. Update tests/docs that reference "Pipeline" tab

## Open Questions

- [x] Should BatchProgress show completed batches from last 24h? **Answer: No, only active batches. Completed → Review.**
- [x] Limit for `listGenerations` in BatchProgress? **Answer: 50 (enough to cover recent batches, paginated in Review if needed).**
- [x] Should Details tab have sub-sections (tabs within tab)? **Answer: No, single scrollable page with accordion + settings.**

---

**Status:** Ready for review
**Estimated Effort:** ~4 hours (3 new components + refactor + testing)
**Risk:** Low (no backend changes, clean component split)
