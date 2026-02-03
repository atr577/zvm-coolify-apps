---
id: SPEC-T27
title: Phase 3B - Pipeline Run Section Redesign
status: draft
created: 2026-02-03
task: T27
target_sections: [Pipeline → Run]
---

# Technical Specification: Phase 3B - Pipeline Run Section Redesign

## Overview

Redesign the Run section of the Pipeline screen to support batch generation with variant selection modes and remove rating functionality. This completes the Pipeline UX redesign (Phase 3A handled Configure, this is Phase 3B for Run).

**Key changes:**
- Replace single-variant dropdown with 3 radio modes: "All unused", "Least used (top N)", "Specific variants"
- Add batch generation API endpoint (`POST /projects/:id/generate/batch`)
- Group generation history by batch (collapsible batches)
- Remove ratings entirely (image_rating, video_rating, comments)
- Keep existing preview functionality (image opens in tab, video inline play)

## Architecture

### Component Diagram

```
GenerationPanel (redesigned)
  ↓
  ├─ Variant selection UI (radio buttons + inputs)
  ├─ Template selector (unchanged)
  └─ Run button with count ("Run — 23 videos")

POST /generate/batch
  ↓
  Creates N TemplateGeneration records with shared batch_id
  ↓
  Async task processes sequentially
  ↓
  Returns batch metadata

GenerationsList (redesigned)
  ↓
  ├─ Batch groups (collapsible)
  │   └─ Individual generations (no ratings)
  ├─ Polling (3s interval for in-progress batches)
  └─ Pagination (Previous/Next)
```

### Changes Required

| Component | File | Change Type |
|-----------|------|-------------|
| Backend Model | `backend/app/models/template_generation.py` | Add `batch_id` field |
| Backend Migration | `backend/alembic/versions/add_batch_id_to_template_generations.py` | Add migration |
| Backend Schemas | `backend/app/schemas/template.py` | Remove rating fields, add batch schemas |
| Backend API | `backend/app/api/template.py` | Add batch endpoint, remove rating endpoint, update list endpoint |
| Frontend Types | `frontend/src/types/index.ts` | Remove rating fields, add batch types |
| Frontend Panel | `frontend/src/components/template/GenerationPanel.tsx` | Batch variant selection UI |
| Frontend List | `frontend/src/components/template/GenerationsList.tsx` | Remove ratings, add batch grouping |
| Frontend API | `frontend/src/services/api.ts` | Add batch endpoint, remove rating endpoint |

## Data Structures

### New Field: batch_id

```python
# backend/app/models/template_generation.py
class TemplateGeneration(Base):
    # ...existing fields...

    # NEW: Batch identifier (UUID string)
    batch_id = Column(String(36), nullable=True, index=True)

    # KEEP (no migration needed, just remove from API):
    # image_rating, image_comment, video_rating, video_comment
```

**Migration notes:**
- Add `batch_id` column (nullable, indexed)
- No default value (NULL for existing records)
- Existing generations without batch_id shown as individual items

### Storage

- **Where:** PostgreSQL `template_generations` table
- **Column:** `batch_id VARCHAR(36)` (nullable, indexed)
- **Format:** UUID v4 string (e.g., `"a1b2c3d4-e5f6-7890-abcd-ef1234567890"`)
- **Migration:** Alembic migration file

## API Changes

### New Endpoint: Batch Generation

```
POST /api/projects/{project_id}/generate/batch
```

**Request schema:**

```python
class BatchGenerateRequest(BaseModel):
    mode: Literal["all_unused", "least_used", "specific"]
    count: Optional[int] = None  # Required for mode="least_used"
    variant_ids: Optional[List[int]] = None  # Required for mode="specific"
    video_template_id: Optional[int] = None  # null = use default
```

**Response schema:**

```python
class BatchGenerateResponse(BaseModel):
    batch_id: str  # UUID
    count: int  # Number of generations created
    generations: List[GenerationResponse]  # Full generation objects
```

**Implementation logic:**

1. Validate request based on mode
   - `all_unused`: count unused variants (`usage_count = 0`)
   - `least_used`: validate `count > 0`, get top N by `usage_count ASC`
   - `specific`: validate `variant_ids` not empty, verify all exist
2. Get or auto-select video template (same as single generation)
3. Generate batch_id (`str(uuid.uuid4())`)
4. Create N `TemplateGeneration` records with shared `batch_id`
5. Update `usage_count` and `last_used_at` for selected variants
6. Start single async task that processes all generations sequentially
7. Return batch metadata

**Error handling:**
- 400 if no variants match mode (e.g., all_unused but all used)
- 400 if count > available variants (for least_used mode)
- 404 if any variant_id not found (for specific mode)
- 400 if no video template available

### Removed Endpoint: Rating Update

```
DELETE /api/projects/{project_id}/generations/{generation_id}/rating
```

**Reason:** Ratings removed from app per UX spec (Q5).

**Migration:** Keep DB columns (`image_rating`, etc.) for historical data, but remove from API response.

### Modified Endpoint: List Generations

```
GET /api/projects/{project_id}/generations
```

**Query parameters:**
- `offset: int = 0`
- `limit: int = 20`
- `group_by_batch: bool = True`  # NEW: Enable batch grouping

**Response (when group_by_batch=True):**

```python
class BatchGroup(BaseModel):
    batch_id: Optional[str] = None  # None for non-batched generations
    count: int  # Number of generations in batch
    completed_count: int  # Number with status=completed
    status: Literal["pending", "in_progress", "completed", "failed"]
    created_at: datetime
    generations: List[GenerationResponse]

class GenerationListBatchedResponse(BaseModel):
    batches: List[BatchGroup]
    total_generations: int  # Total across all batches
```

**Batch status logic:**
- `pending`: all generations pending
- `in_progress`: at least one generating_image/video, none failed
- `completed`: all generations completed
- `failed`: at least one failed

**Fallback:** When `group_by_batch=False`, return flat list (existing behavior).

## UI Changes

### GenerationPanel Component

**Current:**

```tsx
<select value={selectedVariantId}>
  <option value="">Auto-select (least used)</option>
  {variants.map(v => <option value={v.id}>...</option>)}
</select>
<button>Generate Video</button>
```

**New:**

```tsx
<div className="variant-selection">
  <label>Select variants:</label>

  <div className="radio-group">
    <label>
      <input type="radio" value="all_unused" checked={mode === "all_unused"} />
      All unused ({unusedCount})
    </label>

    <label>
      <input type="radio" value="least_used" checked={mode === "least_used"} />
      Least used (top
      <input type="number" value={count} min={1} max={variantsCount} disabled={mode !== "least_used"} />
      )
    </label>

    <label>
      <input type="radio" value="specific" checked={mode === "specific"} />
      Specific variants...
    </label>
  </div>

  {mode === "specific" && (
    <div className="variant-checkboxes">
      {variants.map(v => (
        <label key={v.id}>
          <input type="checkbox" checked={selectedVariantIds.includes(v.id)} />
          #{v.row_number} - {previewVariantData(v.data)}
        </label>
      ))}
    </div>
  )}
</div>

<select value={selectedTemplateId}>
  {/* unchanged */}
</select>

<button disabled={videoCount === 0}>
  Run — {videoCount} video{videoCount !== 1 ? 's' : ''}
</button>
```

**State changes:**

```tsx
const [mode, setMode] = useState<"all_unused" | "least_used" | "specific">("all_unused")
const [count, setCount] = useState(10)
const [selectedVariantIds, setSelectedVariantIds] = useState<number[]>([])

const unusedCount = variants.filter(v => v.usage_count === 0).length
const videoCount = mode === "all_unused" ? unusedCount : mode === "least_used" ? count : selectedVariantIds.length
```

**API call:**

```tsx
const handleRun = async () => {
  await templateApi.startBatchGeneration(projectId, {
    mode,
    count: mode === "least_used" ? count : undefined,
    variant_ids: mode === "specific" ? selectedVariantIds : undefined,
    video_template_id: selectedTemplateId,
  })
  // Refresh list
}
```

### GenerationsList Component

**Removed:**

- `RatingInput` component (entire component deleted)
- `handleRatingUpdate` function
- `savingRatings` state
- `debounceTimeouts` ref
- All rating-related JSX (stars, comment inputs)

**Added:**

- Batch grouping UI
- Batch header with status badge and summary
- Collapsible batch sections

**New structure:**

```tsx
{batches.map(batch => (
  <div key={batch.batch_id || `single-${batch.generations[0].id}`} className="batch-group">
    {/* Batch header (collapsible) */}
    <div className="batch-header" onClick={() => toggleBatch(batch.batch_id)}>
      <span className="batch-status-badge">{batch.status}</span>
      <span className="batch-summary">
        {batch.batch_id
          ? `Batch: ${batch.completed_count}/${batch.count} ✅`
          : `Generation #${batch.generations[0].id}`
        }
      </span>
      <span className="batch-date">{formatDate(batch.created_at)}</span>
      <ChevronIcon direction={expandedBatches.has(batch.batch_id) ? "down" : "right"} />
    </div>

    {/* Batch body (expanded) */}
    {expandedBatches.has(batch.batch_id) && (
      <div className="batch-generations">
        {batch.generations.map(gen => (
          <GenerationCard key={gen.id} generation={gen} />
        ))}
      </div>
    )}
  </div>
))}
```

**GenerationCard (no ratings):**

```tsx
<div className="generation-card">
  {/* Status badge, variant data, error message (unchanged) */}

  {/* Image preview (clickable link) */}
  {gen.image_path && (
    <a href={`/api/files/${gen.image_path}`} target="_blank">
      <img src={`/api/files/${gen.image_path}`} />
    </a>
  )}

  {/* Video preview (inline VideoPreview component) */}
  {gen.video_path && (
    <VideoPreview videoUrl={`/api/files/${gen.video_path}`} />
  )}

  {/* Action buttons (retry, delete) - unchanged */}
</div>
```

**Polling logic:** Check if any batch has status `in_progress`, poll every 3s.

## Implementation Steps

1. **Backend: Database migration**
   - [ ] Create migration: add `batch_id` column to `template_generations`
   - [ ] Apply migration: `alembic upgrade head`

2. **Backend: Update schemas**
   - [ ] Remove `image_rating`, `image_comment`, `video_rating`, `video_comment` from `GenerationResponse`
   - [ ] Add `BatchGenerateRequest`, `BatchGenerateResponse`, `BatchGroup`, `GenerationListBatchedResponse`

3. **Backend: Batch generation endpoint**
   - [ ] Implement `POST /projects/{project_id}/generate/batch`
   - [ ] Validate mode-specific params (count, variant_ids)
   - [ ] Query variants based on mode
   - [ ] Generate batch_id (UUID)
   - [ ] Create N generation records with batch_id
   - [ ] Start async task (sequential processing)
   - [ ] Return batch metadata

4. **Backend: Update list endpoint**
   - [ ] Add `group_by_batch` query param
   - [ ] Implement batch grouping logic (GROUP BY batch_id)
   - [ ] Calculate batch status (all pending → pending, etc.)
   - [ ] Return `GenerationListBatchedResponse` when grouped

5. **Backend: Remove rating endpoint**
   - [ ] Delete `PATCH /projects/{project_id}/generations/{generation_id}/rating` route
   - [ ] Keep DB columns (no schema change)

6. **Frontend: Update types**
   - [ ] Remove `image_rating`, `image_comment`, `video_rating`, `video_comment` from `Generation` type
   - [ ] Add `BatchGenerateRequest`, `BatchGenerateResponse`, `BatchGroup` types
   - [ ] Remove `GenerationRatingUpdate` type

7. **Frontend: Update API client**
   - [ ] Add `startBatchGeneration(projectId, request)` function
   - [ ] Remove `updateGenerationRating()` function

8. **Frontend: Redesign GenerationPanel**
   - [ ] Replace single variant dropdown with radio group UI
   - [ ] Add state: `mode`, `count`, `selectedVariantIds`
   - [ ] Calculate `unusedCount` and `videoCount`
   - [ ] Render specific variants checkboxes when `mode === "specific"`
   - [ ] Update Run button text: `"Run — {videoCount} videos"`
   - [ ] Call `startBatchGeneration()` instead of `startGeneration()`

9. **Frontend: Redesign GenerationsList**
   - [ ] Remove `RatingInput` component entirely
   - [ ] Remove rating-related state and handlers
   - [ ] Fetch batched list (`group_by_batch=true`)
   - [ ] Render batch groups with collapsible headers
   - [ ] Render individual generations (no ratings)
   - [ ] Keep polling logic (check batch status instead of generation status)
   - [ ] Keep pagination (Previous/Next)

10. **Testing**
    - [ ] Backend: Test batch generation (all 3 modes)
    - [ ] Backend: Test batch listing with grouping
    - [ ] Backend: Verify rating endpoint removed
    - [ ] Frontend: Test variant selection UI (radio + checkboxes)
    - [ ] Frontend: Test batch generation flow
    - [ ] Frontend: Test batch grouping and expansion
    - [ ] Frontend: Verify no rating UI elements
    - [ ] Build: `npm run build` passes
    - [ ] Build: `pytest` passes

## Edge Cases

| Case | Handling |
|------|----------|
| All variants used (all_unused mode) | Return 400: "No unused variants available" |
| count > available variants (least_used) | Return 400: "Not enough variants (requested N, available M)" |
| Empty variant_ids (specific mode) | Return 400: "No variants selected" |
| Non-existent variant_id (specific) | Return 404: "Variant ID X not found" |
| No video template available | Return 400: "No video template configured" |
| Batch processing: one generation fails | Continue with next, mark batch status as "failed" at end |
| Empty batch (0 variants) | Disable Run button, show message "No variants selected" |
| Legacy generations (no batch_id) | Render as individual items, not in a batch group |
| Batch partially complete | Show "N/M ✅" in batch header, status = "in_progress" |
| Poll interval with no in-progress | Stop polling (no API calls) |

## Testing

### Manual Tests

#### Batch Generation
- [ ] Create template project with 50 variants
- [ ] Select "All unused (50)" → click Run → verify 50 generations created with shared batch_id
- [ ] Select "Least used (top 10)" → verify 10 generations created
- [ ] Select "Specific variants" → check 5 variants → verify 5 generations created
- [ ] Verify batch appears in History with collapsible header
- [ ] Verify batch status updates as generations complete

#### UI Validation
- [ ] Verify Run button shows correct count ("Run — 23 videos")
- [ ] Verify Run button disabled when count = 0
- [ ] Verify specific variants UI shows checkboxes
- [ ] Verify batch header shows "10/10 ✅" when complete
- [ ] Verify batch header shows "7/10 ⚠️" when in-progress
- [ ] Verify batch expands/collapses on header click

#### No Ratings
- [ ] Verify no rating stars visible on generation cards
- [ ] Verify no comment inputs visible
- [ ] Verify no "Saving..." indicator
- [ ] Verify completed generations show only image/video previews and action buttons

#### Backward Compatibility
- [ ] Verify existing generations (without batch_id) render as individual items
- [ ] Verify single generation endpoint still works (not removed)
- [ ] Verify existing polling logic works with batched response

### Build Verification

- [ ] `cd backend && .venv/bin/pytest` — all tests pass
- [ ] `cd frontend && npm run build` — no TypeScript errors
- [ ] No unused imports (build fails if found)

## Dependencies

### Existing (reused)
- `VideoPreview` component (video inline play)
- `templateApi.listGenerations()` (modified to support batching)
- Polling mechanism (3s interval, check batch status)
- Pagination (Previous/Next)

### New (created)
- Batch generation API endpoint
- Batch grouping UI components
- Variant selection radio UI

## Open Questions

- [ ] **Q1:** Should batch header show individual generation statuses (e.g., "7 completed, 2 in-progress, 1 failed")?
  - **A:** Start simple with overall batch status. Detailed breakdown can be added later if needed.

- [ ] **Q2:** Should we support batch cancellation (cancel all pending generations in a batch)?
  - **A:** Not in scope for Phase 3B. Can add later as separate feature.

- [ ] **Q3:** Should batch processing be parallel (up to N concurrent) or strictly sequential?
  - **A:** Sequential to avoid rate limits. Parallel processing can be opt-in later.

- [ ] **Q4:** Pagination strategy for batched view — paginate batches or generations?
  - **A:** Paginate batches (each batch is one item). Load all generations in a batch when expanded.

## Notes

### Why Remove Ratings?

Per UX spec (SPEC-UX-TEMPLATE-REDESIGN.md, Q5): Ratings removed from the app entirely. Focus shifts to approve/reject workflow in Review screen (Phase 2).

### Why Keep DB Columns?

Historical data preservation. Removing columns requires migration and loses existing ratings. Keeping them is harmless (just excluded from API).

### Sequential vs Parallel Processing

Batch processing is **sequential** (one generation at a time) to:
1. Avoid fal.ai rate limits
2. Simplify error handling (one failure doesn't block others)
3. Reduce memory/CPU load

Future enhancement: Add `parallel: boolean` option for faster processing.

### Batch ID Format

Using UUID v4 string (36 chars including hyphens) for uniqueness and readability. Example: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`.

### Polling Optimization

Poll only if any batch has status `in_progress`. Stop polling when all batches are `completed` or `failed`.
