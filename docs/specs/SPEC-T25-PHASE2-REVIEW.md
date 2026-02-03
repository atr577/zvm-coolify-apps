---
id: SPEC-T25
title: Phase 2 - Review Screen (Focused Review)
status: draft
created: 2026-02-03
task: T25
target_sections: [Screen 2: Review]
---

# Technical Specification: Review Screen - Focused Review

## Overview

Replace the current scrolling list (ModerationQueue stub) with a focused one-at-a-time review experience. User reviews a single video in focus with large preview, variant data, action buttons (Reject/Redo/Approve), and filmstrip navigation. Metadata (title/description/hashtags) is pre-generated and editable before approval. Target slot is calculated and shown before approval action.

## Architecture

### Component Hierarchy

```
ReviewScreen (full rewrite)
├── FilterTabs (All/Pending/Approved/Rejected)
├── Counter ("3 of 8")
├── ReviewFocusedView (new)
│   ├── VideoPreview (existing, 9:16)
│   ├── VariantDataPanel (new)
│   ├── TargetSlotInfo (new)
│   ├── ReviewActions (new - inline Reject/Redo/Approve)
│   └── ReviewMetadata (new - editable title/description/hashtags)
├── ReviewFilmstrip (new - horizontal thumbnails with colored borders)
└── RejectionArchive (existing, collapsible)
```

### Changes Required

| Component | File | Change Type |
|-----------|------|-------------|
| ReviewScreen | `frontend/src/components/template/ReviewScreen.tsx` | Full rewrite (replace stub) |
| ReviewFocusedView | `frontend/src/components/template/ReviewFocusedView.tsx` | Add |
| ReviewFilmstrip | `frontend/src/components/template/ReviewFilmstrip.tsx` | Add |
| ReviewActions | `frontend/src/components/template/ReviewActions.tsx` | Add |
| ReviewMetadata | `frontend/src/components/template/ReviewMetadata.tsx` | Add |
| Pre-generate endpoint | `backend/app/api/moderation.py` | Add endpoint |
| Approve endpoint | `backend/app/api/moderation.py` | Modify to accept optional metadata body |
| Moderation schemas | `backend/app/schemas/moderation.py` | Add PreGenerateMetadataResponse, ApproveRequest |
| API client | `frontend/src/services/api.ts` | Add preGenerateMetadata, update approve signature |

## Data Structures

### Backend Changes

#### New Endpoint: Pre-generate Metadata

```python
# Endpoint: POST /api/projects/{id}/moderation-queue/{gen_id}/pre-generate-metadata
# No body required
# Response:
{
  "metadata": {
    "youtube": {
      "title": "...",
      "description": "...",
      "hashtags": "..."
    },
    "instagram": { ... },
    "tiktok": { ... }
  }
}
```

**Implementation:**
- Call `openai_service.generate_publishing_meta()` with generation context
- Return metadata WITHOUT creating ApprovedGeneration
- Reuse existing `openai_service.generate_publishing_meta()` function

#### Modified Endpoint: Approve

```python
# Endpoint: POST /api/projects/{id}/moderation-queue/{gen_id}/approve
# Body (OPTIONAL):
{
  "publishing_metadata": {
    "youtube": {
      "title": "...",
      "description": "...",
      "hashtags": "..."
    },
    ...
  }
}

# Response: unchanged (ApproveResponse)
```

**Implementation:**
- Accept optional `ApproveRequest` body with `publishing_metadata` field
- If metadata in body → use it (user edited)
- If no body / no metadata → generate via LLM (backward compatible)
- Rest of approve logic unchanged

#### New Schemas

```python
# backend/app/schemas/moderation.py

class PreGenerateMetadataResponse(BaseModel):
    """Response for pre-generate metadata."""
    metadata: Dict[str, PlatformMetadata]

class ApproveRequest(BaseModel):
    """Optional request body for approve."""
    publishing_metadata: Optional[Dict[str, PlatformMetadata]] = None
```

### Frontend Changes

#### Local Status Tracking

Since API returns only "pending" items, frontend tracks local state:

```typescript
interface ReviewScreenState {
  items: ModerationQueueItem[]          // All queue items from API
  currentIndex: number                  // Current position in filtered list
  filter: 'all' | 'pending' | 'approved' | 'rejected'

  // Local tracking (session state)
  approvedIds: Set<number>              // IDs approved in this session
  rejectedIds: Set<number>              // IDs rejected in this session
  redoIds: Set<number>                  // IDs sent for regeneration

  // Metadata state
  metadata: Record<string, PlatformMetadata> | null  // Pre-generated for current item
  metadataLoading: boolean
  metadataEdited: Record<string, PlatformMetadata> | null  // User edits
}
```

#### Filter Logic

```typescript
const getItemStatus = (itemId: number) => {
  if (approvedIds.has(itemId)) return 'approved'
  if (rejectedIds.has(itemId)) return 'rejected'
  if (redoIds.has(itemId)) return 'redo'
  return 'pending'
}

const filteredItems = items.filter(item => {
  const status = getItemStatus(item.id)
  if (filter === 'all') return true
  if (filter === 'pending') return status === 'pending'
  if (filter === 'approved') return status === 'approved'
  if (filter === 'rejected') return status === 'rejected'
  return true
})
```

#### Target Slot Calculation

```typescript
// Load schedule + count local approved items
const schedule = await publishingScheduleApi.getSchedule(projectId)
const filledSlots = schedule.slots.filter(s => s.item).length
const localApprovedCount = approvedIds.size

const nextSlotIndex = filledSlots + localApprovedCount
const nextSlot = schedule.slots[nextSlotIndex] || null

// Display:
// - If nextSlot exists: "→ Mon 3 Feb, 18:00" (slot X of Y)
// - If null: "All slots filled. Video will queue for next available slot."
```

## API Changes

### Backend Endpoints

#### 1. Add Pre-generate Metadata

**Endpoint:** `POST /api/projects/{project_id}/moderation-queue/{generation_id}/pre-generate-metadata`

**Location:** `backend/app/api/moderation.py`

```python
@router.post(
    "/projects/{project_id}/moderation-queue/{generation_id}/pre-generate-metadata",
    response_model=PreGenerateMetadataResponse,
    tags=["moderation"]
)
async def pre_generate_metadata(
    project_id: int,
    generation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Pre-generate publishing metadata for a generation WITHOUT approving it.

    Returns metadata that user can edit before calling approve.
    """
    project = get_template_project(db, project_id, current_user)
    generation = get_generation_for_moderation(db, project_id, generation_id)

    # Build context
    scenario_data = {
        "preprocessing_result": generation.preprocessing_result,
        "image_prompt": generation.image_prompt,
        "video_prompt": generation.video_prompt,
    }

    try:
        publishing_metadata = await openai_service.generate_publishing_meta(
            platforms=project.platforms or ["youtube"],
            scenario_data=scenario_data,
            fallback_text=generation.image_prompt[:500] if generation.image_prompt else None
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Metadata generation failed: {str(e)}. Please retry."
        )

    return PreGenerateMetadataResponse(metadata=publishing_metadata)
```

#### 2. Modify Approve Endpoint

**Endpoint:** `POST /api/projects/{project_id}/moderation-queue/{generation_id}/approve`

**Changes:**
- Accept optional `ApproveRequest` body
- Use body metadata if provided, otherwise generate

```python
# Change signature from:
async def approve_generation(
    project_id: int,
    generation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

# To:
async def approve_generation(
    project_id: int,
    generation_id: int,
    request: Optional[ApproveRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

# In body, replace metadata generation:
# If metadata provided in request, use it
if request and request.publishing_metadata:
    publishing_metadata = request.publishing_metadata
else:
    # Generate metadata via LLM (existing code)
    scenario_data = { ... }
    try:
        publishing_metadata = await openai_service.generate_publishing_meta(...)
    except Exception as e:
        raise HTTPException(status_code=503, ...)
```

### Frontend API Client

**Location:** `frontend/src/services/api.ts`

```typescript
// Add to moderationApi:
export const moderationApi = {
  // ... existing methods ...

  // Pre-generate metadata (new)
  preGenerateMetadata: (projectId: number, generationId: number) =>
    api.post<{ metadata: Record<string, PlatformMetadata> }>(
      `/api/projects/${projectId}/moderation-queue/${generationId}/pre-generate-metadata`
    ),

  // Approve (update signature to accept optional metadata)
  approve: (
    projectId: number,
    generationId: number,
    metadata?: Record<string, PlatformMetadata>
  ) =>
    api.post<ApproveResponse>(
      `/api/projects/${projectId}/moderation-queue/${generationId}/approve`,
      metadata ? { publishing_metadata: metadata } : {}
    ),
}

// Add type:
export interface PlatformMetadata {
  title: string
  description: string
  hashtags?: string
}
```

## UI Changes

### ReviewScreen Component (Full Rewrite)

**File:** `frontend/src/components/template/ReviewScreen.tsx`

**Key State:**

```typescript
const [items, setItems] = useState<ModerationQueueItem[]>([])
const [currentIndex, setCurrentIndex] = useState(0)
const [filter, setFilter] = useState<'all' | 'pending' | 'approved' | 'rejected'>('pending')
const [approvedIds, setApprovedIds] = useState<Set<number>>(new Set())
const [rejectedIds, setRejectedIds] = useState<Set<number>>(new Set())
const [redoIds, setRedoIds] = useState<Set<number>>(new Set())
const [metadata, setMetadata] = useState<Record<string, PlatformMetadata> | null>(null)
const [metadataEdited, setMetadataEdited] = useState<Record<string, PlatformMetadata> | null>(null)
const [schedule, setSchedule] = useState<PublishingScheduleResponse | null>(null)
```

**Lifecycle:**

1. **Mount:** Fetch queue + schedule, set currentIndex to 0, filter to 'pending'
2. **Pre-generate metadata:** When currentItem changes, load metadata (debounced or on-demand)
3. **Action handlers:**
   - **Approve:** Send edited metadata, add to approvedIds, advance to next pending
   - **Reject:** Add to rejectedIds, advance to next pending
   - **Redo:** Add to redoIds, advance to next pending
4. **Navigation:** Filmstrip click or keyboard ←→ changes currentIndex
5. **Filter change:** Re-filter items, adjust currentIndex if needed

**Empty State:**

```tsx
{filteredItems.length === 0 && (
  <div className="text-center py-12">
    <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
    <h3 className="text-lg font-medium text-gray-900 mb-2">All caught up!</h3>
    <p className="text-gray-600 mb-4">No videos pending review.</p>
    <div className="flex gap-3 justify-center">
      <Link to={`/projects/${projectId}/pipeline`}>
        <Button>→ Run pipeline</Button>
      </Link>
      <Link to={`/projects/${projectId}/dashboard`}>
        <Button variant="secondary">→ Dashboard</Button>
      </Link>
    </div>
  </div>
)}
```

### ReviewFocusedView Component (New)

**File:** `frontend/src/components/template/ReviewFocusedView.tsx`

**Props:**

```typescript
interface ReviewFocusedViewProps {
  item: ModerationQueueItem
  targetSlot: ScheduleSlot | null
  metadata: Record<string, PlatformMetadata> | null
  metadataLoading: boolean
  onMetadataChange: (metadata: Record<string, PlatformMetadata>) => void
  onApprove: () => void
  onReject: (reason: string, comment?: string) => void
  onRedo: (feedback?: string) => void
}
```

**Layout:**

```tsx
<div className="grid grid-cols-2 gap-6">
  {/* Left: Video Preview */}
  <div>
    <VideoPreview
      videoUrl={item.video_url}
      thumbnailUrl={item.image_url}
      aspectRatio="9/16"
      className="max-w-md mx-auto"
    />
    <a
      href={item.image_url}
      target="_blank"
      rel="noopener noreferrer"
      className="text-sm text-blue-600 hover:underline mt-2 block text-center"
    >
      View source image →
    </a>
  </div>

  {/* Right: Data + Actions + Metadata */}
  <div className="space-y-6">
    <VariantDataPanel variant={item.variant} template={item.video_template} />
    <TargetSlotInfo slot={targetSlot} />
    <ReviewActions
      onApprove={onApprove}
      onReject={onReject}
      onRedo={onRedo}
      targetSlot={targetSlot}
    />
    <ReviewMetadata
      metadata={metadata}
      loading={metadataLoading}
      onChange={onMetadataChange}
    />
  </div>
</div>
```

### ReviewFilmstrip Component (New)

**File:** `frontend/src/components/template/ReviewFilmstrip.tsx`

**Props:**

```typescript
interface ReviewFilmstripProps {
  items: ModerationQueueItem[]
  currentIndex: number
  statusMap: Map<number, 'pending' | 'approved' | 'rejected'>
  onNavigate: (index: number) => void
}
```

**Layout:**

```tsx
<div className="overflow-x-auto">
  <div className="flex gap-2 pb-2">
    {items.map((item, index) => {
      const status = statusMap.get(item.id) || 'pending'
      const borderColor =
        status === 'approved' ? 'border-green-500' :
        status === 'rejected' ? 'border-red-500' :
        'border-gray-300'

      return (
        <div
          key={item.id}
          onClick={() => onNavigate(index)}
          className={`
            flex-shrink-0 w-20 h-32 cursor-pointer rounded overflow-hidden
            border-2 ${borderColor}
            ${index === currentIndex ? 'ring-2 ring-purple-600' : ''}
          `}
        >
          <img
            src={item.image_url || undefined}
            alt={`Thumbnail ${index + 1}`}
            className="w-full h-full object-cover"
          />
        </div>
      )
    })}
  </div>
</div>
```

**Keyboard Navigation:**

```typescript
useEffect(() => {
  const handleKeyboard = (e: KeyboardEvent) => {
    if (e.key === 'ArrowLeft' && currentIndex > 0) {
      onNavigate(currentIndex - 1)
    } else if (e.key === 'ArrowRight' && currentIndex < items.length - 1) {
      onNavigate(currentIndex + 1)
    }
  }
  window.addEventListener('keydown', handleKeyboard)
  return () => window.removeEventListener('keydown', handleKeyboard)
}, [currentIndex, items.length, onNavigate])
```

### ReviewActions Component (New)

**File:** `frontend/src/components/template/ReviewActions.tsx`

**Props:**

```typescript
interface ReviewActionsProps {
  onApprove: () => void
  onReject: (reason: string, comment?: string) => void
  onRedo: (feedback?: string) => void
  targetSlot: ScheduleSlot | null
  disabled?: boolean
}
```

**Features:**

- Inline forms for Reject/Redo (expand on button click, not modals)
- Approve button shows target slot info: "✓ Approve → Wed 18h"
- Single click approve (no confirmation modal)

```tsx
const [rejectOpen, setRejectOpen] = useState(false)
const [redoOpen, setRedoOpen] = useState(false)

<div className="space-y-3">
  <div className="flex gap-3">
    <Button onClick={() => setRejectOpen(!rejectOpen)} variant="outline">
      ✗ Reject
    </Button>
    <Button onClick={() => setRedoOpen(!redoOpen)} variant="outline">
      ↻ Redo
    </Button>
    <Button onClick={onApprove} variant="primary" className="flex-1">
      ✓ Approve → {targetSlot ? formatSlotTime(targetSlot.scheduled_at) : 'Queue'}
    </Button>
  </div>

  {rejectOpen && (
    <RejectForm onSubmit={onReject} onCancel={() => setRejectOpen(false)} />
  )}

  {redoOpen && (
    <RedoForm onSubmit={onRedo} onCancel={() => setRedoOpen(false)} />
  )}
</div>
```

### ReviewMetadata Component (New)

**File:** `frontend/src/components/template/ReviewMetadata.tsx`

**Props:**

```typescript
interface ReviewMetadataProps {
  metadata: Record<string, PlatformMetadata> | null
  loading: boolean
  onChange: (metadata: Record<string, PlatformMetadata>) => void
}
```

**Layout:**

```tsx
<div className="border rounded-lg p-4">
  <h4 className="font-medium mb-3">Publishing Metadata</h4>

  {loading && <Loader2 className="w-5 h-5 animate-spin" />}

  {metadata && Object.entries(metadata).map(([platform, data]) => (
    <div key={platform} className="space-y-2 mb-4">
      <h5 className="text-sm font-medium text-gray-700 capitalize">{platform}</h5>
      <input
        type="text"
        value={data.title}
        onChange={(e) => onChange({
          ...metadata,
          [platform]: { ...data, title: e.target.value }
        })}
        placeholder="Title"
        className="w-full px-3 py-2 border rounded"
      />
      <textarea
        value={data.description}
        onChange={(e) => onChange({
          ...metadata,
          [platform]: { ...data, description: e.target.value }
        })}
        placeholder="Description"
        rows={3}
        className="w-full px-3 py-2 border rounded"
      />
      <input
        type="text"
        value={data.hashtags || ''}
        onChange={(e) => onChange({
          ...metadata,
          [platform]: { ...data, hashtags: e.target.value }
        })}
        placeholder="Hashtags"
        className="w-full px-3 py-2 border rounded"
      />
    </div>
  ))}
</div>
```

## Implementation Steps

1. **Backend - Pre-generate Metadata Endpoint**
   - Add `PreGenerateMetadataResponse` schema to `moderation.py`
   - Implement `/pre-generate-metadata` endpoint
   - Test with existing generation

2. **Backend - Modify Approve Endpoint**
   - Add `ApproveRequest` schema with optional `publishing_metadata`
   - Update approve handler to accept optional body
   - Add conditional logic: use body metadata if provided, else generate
   - Ensure backward compatibility (no body = auto-generate)

3. **Frontend - API Client**
   - Add `preGenerateMetadata` method to `moderationApi`
   - Update `approve` method signature to accept optional metadata
   - Add `PlatformMetadata` type

4. **Frontend - ReviewMetadata Component**
   - Create editable fields for title/description/hashtags per platform
   - Handle loading state
   - Emit changes via onChange callback

5. **Frontend - ReviewActions Component**
   - Create inline Reject/Redo forms (no modals)
   - Approve button with target slot display
   - Wire up action handlers

6. **Frontend - ReviewFilmstrip Component**
   - Horizontal scroll container with thumbnails
   - Color-coded borders (green/red/gray)
   - Click + keyboard navigation

7. **Frontend - ReviewFocusedView Component**
   - Compose VideoPreview + VariantDataPanel + TargetSlotInfo + ReviewActions + ReviewMetadata
   - 2-column layout (video left, data+actions right)

8. **Frontend - ReviewScreen Full Rewrite**
   - Replace stub with full focused review logic
   - Implement filter tabs + counter
   - Local status tracking (approvedIds, rejectedIds, redoIds)
   - Auto-navigate to first pending on mount
   - Pre-generate metadata for current item
   - Handle approve/reject/redo with auto-advance
   - Target slot calculation
   - Integrate RejectionArchive (collapsible)

9. **Testing**
   - Test pre-generate metadata endpoint
   - Test approve with edited metadata
   - Test approve without body (auto-generate)
   - Test filter switching
   - Test keyboard navigation
   - Test auto-advance on actions
   - Test empty state

## Edge Cases

| Case | Handling |
|------|----------|
| Pre-generate metadata fails (503) | Show error, allow retry button |
| Approve with edited metadata fails | Show error, keep metadata state, allow retry |
| All items approved in session | Show "All caught up" empty state |
| Filter change leaves currentIndex out of bounds | Set currentIndex = 0 or max valid index |
| Keyboard navigation at boundaries | Disable left at index 0, right at last index |
| Schedule has no empty slots | Show "All slots filled. Will queue for next available." |
| User reloads page mid-session | Local state (approvedIds) is lost, refetch queue shows updated state |
| Filmstrip with 50+ items | Horizontal scroll, no pagination needed |
| Metadata pre-generation slow | Show loading spinner in metadata section |

## Testing

### Manual Tests

- [ ] Open Review screen with pending items → shows first item, filter=Pending
- [ ] Click "Pre-generate" or auto-load metadata → metadata appears in editable fields
- [ ] Edit metadata title → change is reflected in state
- [ ] Click Approve → item approved with edited metadata, advances to next pending
- [ ] Click Reject → inline form appears, submit → item removed, advances to next
- [ ] Click Redo → inline form appears, submit → item removed, advances to next
- [ ] Click filmstrip thumbnail → navigates to that item
- [ ] Press ← key → navigates to previous item (if not at start)
- [ ] Press → key → navigates to next item (if not at end)
- [ ] Switch filter to "All" → shows all items including approved/rejected (color-coded)
- [ ] Switch filter to "Approved" → shows only locally approved items (green borders)
- [ ] Approve last pending item → shows "All caught up" empty state
- [ ] Target slot displays correct schedule time before approve
- [ ] Target slot updates after each approve (next slot in queue)

### Build Verification

- [ ] Backend: `cd backend && .venv/bin/pytest tests/` (if tests exist)
- [ ] Frontend: `cd frontend && npm run build` (no TypeScript errors)

## Dependencies

### Existing

- `openai_service.generate_publishing_meta()` - metadata generation
- `ModerationQueue` component (not deleted, kept as fallback)
- `RejectionArchive` component (reused, collapsible)
- `VideoPreview` component (reused for 9:16 preview)
- `publishingScheduleApi.getSchedule()` - slot calculation
- `moderationApi.getQueue()` - queue fetch
- `moderationApi.approve()` - approve action (signature updated)
- `moderationApi.reject()` - reject action
- `moderationApi.regenerate()` - redo action

### New

- No new external dependencies

## Open Questions

None. All design decisions from UX spec are resolved:
- Q6: Auto-navigate to first unreviewed → Implemented
- Q8: Metadata pre-generation → Option 1 chosen (pre-generate endpoint + editable fields)
- Q17: Redo lifecycle → Implemented (item leaves Pending, auto-advance, regenerated appears at end)

## Out of Scope

- Keyboard shortcuts beyond ←→ navigation (e.g., hotkeys for approve/reject)
- Drag-and-drop reordering in filmstrip
- Batch approve/reject
- Real-time updates (polling queue every N seconds)
- Delete old ModerationQueue component (keep for now as reference)
- Multi-platform metadata templates (each platform has separate fields)
