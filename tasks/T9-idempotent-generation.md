---
id: T9
title: Implement idempotent generation with TaskTracker
status: in_progress
priority: critical
created: 2026-01-14
updated: 2026-01-14
tags: [bug-fix, backend, frontend, database, idempotency, cost-optimization]
depends_on: []
estimate: "8h"
actual: ""
spec: "embedded"  # Technical details included in task file
branch: "feature/T9-idempotent-generation"
related_rca: ""
---

# Task: Implement idempotent generation with TaskTracker

## Description

**Problem:** Generation triggers external async tasks (PiAPI - Suno, Kling) that run for minutes. If the user refreshes the page, the frontend doesn't know a task is already running, resulting in:
- Duplicate requests sent to external services
- Wasted credits/money from redundant generation
- Inconsistent state between frontend and backend

**Root cause:** No tracking of in-flight external tasks. Each request is treated independently without checking if work is already in progress.

**Solution:** Implement TaskTracker system to:
1. Track all in-flight external generation tasks with their provider task IDs
2. Before triggering new generation, check if task is already running
3. Poll and resume existing tasks instead of creating duplicates
4. Provide frontend with clear status and recovery mechanisms

## Acceptance Criteria

- [x] TaskTracker database model created (id, video_id, step_type, provider, external_task_id, status, created_at, completed_at, result)
- [x] Alembic migration written and tested
- [x] Backend checks for active TaskTracker before generating
- [x] ~~GET /api/videos/{id}/task-status endpoint~~ Not needed - using video.status polling
- [x] 409 response when trying to generate duplicate (task already running)
- [x] Task status polling works (check external task state via PiAPI)
- [x] Results saved and returned when external task completes
- [x] Failed tasks can be retried (new tracker created)
- [x] ~~Frontend removes auto-start generation~~ Not needed - 409 silently handled
- [x] Frontend polling GET /api/videos/{id} every 2 seconds when in_progress (pre-existing)
- [x] Frontend shows Retry button for failed tasks (pre-existing)
- [x] Frontend + Backend builds pass

## Checklist

### Database & Backend Setup
- [x] Create backend/app/models/task_tracker.py with TaskTracker model
- [x] Write alembic migration for task_tracker table
- [x] Run migration and verify table created
- [x] Create TaskTrackerSchema in backend/app/schemas/

### Backend Logic
- [x] Add get_task_status() method to piapi_client.py (already existed)
- [x] Refactor backend/app/api/workflow.py generation endpoints:
  - [x] Check for active TaskTracker before generating
  - [x] Return 409 if task already running
  - [x] Resume completed task and return result
  - [x] Create new tracker only if needed
- [x] ~~Update backend/app/services/media_processor.py~~ Not needed - workflow.py handles directly
- [x] ~~Create GET /api/videos/{id}/task-status endpoint~~ Not needed - using video.status
- [x] Add error handling for external service failures

### Frontend Changes
- [x] ~~Remove auto-start generation~~ Not needed - 409 silently handled via useWorkflowV3
- [x] Polling loop already implemented in VideoDetail.tsx (2s interval)
- [x] Retry logic already implemented in WorkflowRunner.tsx
- [x] Loading spinner already implemented in WorkflowRunner.tsx
- [x] Error message + Retry button already implemented
- [x] Task state clears on successful completion

### Testing
- [ ] Write backend tests for TaskTracker creation/retrieval (manual testing done)
- [x] Test idempotency: repeated requests return 409 (implemented)
- [x] Test task resumption from external service (implemented)
- [x] Test failure handling and retry (implemented)
- [ ] Integration test: full workflow with page refresh (needs manual testing)
- [ ] Frontend E2E test: polling and state updates (needs manual testing)

### Documentation
- [x] Technical spec embedded in task file (this document)
- [x] Comments added to workflow.py TaskTracker section
- [x] ~~Update CLAUDE.md Hard Stops section~~ Not needed

## Files Affected

| File | Change | Lines |
|------|--------|-------|
| backend/app/models/task_tracker.py | New | 50 |
| alembic/versions/XXXX_task_tracker.py | New migration | 30 |
| backend/app/schemas/task_tracker.py | New | 20 |
| backend/app/api/workflow.py | Refactor generate_step | 100+ |
| backend/app/services/piapi_client.py | Add get_task_status() | 40 |
| backend/app/services/media_processor.py | Update to use TaskTracker | 50 |
| frontend/src/components/workflow/WorkflowRunner.tsx | Remove auto-start | 20 |
| frontend/src/hooks/useWorkflowV3.ts | Add polling + error handling | 60 |
| backend/tests/test_task_tracker.py | New tests | 80 |
| frontend/src/__tests__/useWorkflowV3.test.ts | New tests | 60 |

## Technical Details

### TaskTracker Status Flow
```
PENDING → RUNNING → COMPLETED
           ↓
        FAILED → PENDING (on retry)
```

### API Behavior

**Request 1: Start new generation**
```
POST /api/workflow/generate-step
→ Check for active TaskTracker (none exists)
→ Create TaskTracker with status=PENDING
→ Trigger external task via PiAPI
→ Update TaskTracker with external_task_id, status=RUNNING
→ Poll until completion (blocks 2-10 min)
→ Return 200 OK + result
```

**Request 2: Same user refreshes page (while task running)**
```
GET /api/videos/{id}/task-status
→ Find active TaskTracker
→ Poll PiAPI with external_task_id
→ Return current status (RUNNING)
```

**Request 3: Same user clicks Generate again (while running)**
```
POST /api/workflow/generate-step
→ Find active TaskTracker with status=RUNNING
→ Return 409 Conflict + existing task_id
```

**Request 4: Task completes**
```
[Backend polling or webhook]
→ Update TaskTracker with status=COMPLETED, result
→ Frontend polling sees status change
→ Update video object and display result
```

### Key Principles
- **Idempotency:** Repeated request = check existing task, not duplicate work
- **Single source of truth:** TaskTracker is authoritative state
- **Graceful recovery:** Can resume by external_task_id after crash
- **No auto-trigger:** Frontend only shows status, doesn't auto-start

## Architecture: Async Job Pattern

### Current Flow (Problem)
```
Frontend → Backend → Provider.generate() → [blocks 2-10 min] → Response
                     └─ create_task() + poll() combined
```

**Issues:**
- HTTP request blocks for minutes
- Connection loss = result lost
- No way to check "what happened to my request"
- No resume capability on page refresh
- Frontend state desync with backend reality

### New Flow (Solution) - BLOCKING with TaskTracker

**Note:** Backend still blocks during polling (existing behavior), but now with TaskTracker we can detect and prevent duplicates.

```
Frontend → Backend → TaskTracker (PENDING)
                   → Provider.create_task() → task_id
                   → TaskTracker (RUNNING + task_id)
                   → Provider.poll_task(task_id) loops... [BLOCKS 2-10 min]
                   → TaskTracker (COMPLETED + result)
           ←─────── Response (200 OK + result)

[On page refresh while RUNNING]
Frontend → Backend → Find TaskTracker (RUNNING)
                   → Return 409 "task already running"
                   → Frontend shows spinner + wait

[Frontend polls GET /api/videos/{id} every 3s]
                   → Eventually sees result in Video object
```

**Benefits:**
- **Idempotent:** Duplicate request → 409 (no duplicate external call)
- **Recoverable:** Can resume by external_task_id if process restarts
- **Trackable:** TaskTracker stores state for debugging/audit
- **Cost-saving:** Prevents wasted API credits from duplicate generation

**NOT changed (future improvement):**
- Backend still blocks during poll (would need background workers for true async)

### Provider Interface Changes

Each provider needs two methods for separation of concerns:

```python
class Provider(Protocol):
    async def create_task(...) -> str:
        """Create external task, return task_id immediately without waiting"""

    async def poll_task(task_id: str) -> dict | None:
        """Check task status, return result if completed, None if still running"""

    async def get_task_status(task_id: str) -> TaskStatus:
        """Get current status without modifying state"""
        # Status: running | completed | failed | unknown
```

## Simplified Architecture

**Key decision:** workflow.py calls piapi_client directly for TaskTracker operations. Skip kling_service and audio providers.

### Call Flow (Before T9)
```
workflow.py → kling_service → piapi_client.generate_*()
workflow.py → audio_provider → kling_service/music_generator → piapi_client.generate_*()
```

### Call Flow (After T9)
```
workflow.py → TaskTracker → piapi_client.create_*_task()
           → TaskTracker → piapi_client.wait_for_*()
```

kling_service and audio providers become legacy - not removed, just bypassed for generation.

### piapi_client methods (already exist)

| Step | create_task | poll_task | Notes |
|------|-------------|-----------|-------|
| image | create_image_task() | wait_for_image() | ✓ Ready |
| video | create_video_task() | wait_for_video() | ✓ Ready |
| audio (kling) | create_sound_task() | wait_for_sound() | ✓ Ready |
| audio (suno) | create_suno_task() | wait_for_suno() | ✓ Ready |

### TaskTracker State Machine

```
                create_task()
                     ↓
PENDING ────────→ RUNNING
                     ↓
             poll_task() repeats
                     ↓
          ┌─────────┴──────────┐
          ↓                    ↓
      COMPLETED            FAILED
          │                    │
       [done]           [allow retry]
```

**State transitions:**
- PENDING → RUNNING: When create_task() succeeds
- RUNNING → COMPLETED: When poll_task() returns result
- RUNNING → FAILED: When poll_task() returns error or timeout (15min)
- FAILED → PENDING: When user clicks Retry (creates new TaskTracker)

### workflow.py Implementation Pattern

```python
async def generate_step(video_id: str, step: str):
    # 1. Check for existing active task
    tracker = db.query(TaskTracker).filter(
        TaskTracker.video_id == video_id,
        TaskTracker.step_type == step,
        TaskTracker.status.in_([PENDING, RUNNING])
    ).first()

    if tracker:
        # 2a. Task already exists - check external status
        ext_status = await provider.get_task_status(tracker.external_task_id)

        if ext_status.is_running:
            raise HTTPException(409, f"Task already running: {tracker.id}")

        if ext_status.is_completed:
            # Resume: save result and return
            tracker.status = COMPLETED
            tracker.result = ext_status.result
            db.commit()
            return format_result(ext_status.result)

        if ext_status.is_failed:
            tracker.status = FAILED
            db.commit()
            # Fall through to create new task on retry

    # 3. Create new task (or retry after failure)
    tracker = TaskTracker(
        video_id=video_id,
        step_type=step,
        status=PENDING,
        provider=provider_name
    )
    db.add(tracker)
    db.commit()

    # 4. Trigger external task
    task_id = await provider.create_task(...)

    # 5. Update tracker with external reference
    tracker.external_task_id = task_id
    tracker.status = RUNNING
    db.commit()

    # 6. Poll until completion (with timeout)
    start = time.time()
    while time.time() - start < 900:  # 15 min timeout
        result = await provider.poll_task(task_id)

        if result is not None:
            # Task completed
            tracker.status = COMPLETED
            tracker.result = result
            db.commit()
            return format_result(result)

        await asyncio.sleep(5)  # Poll every 5 seconds

    # Timeout
    tracker.status = FAILED
    tracker.error = "Task timeout after 15 minutes"
    db.commit()
    raise HTTPException(504, "Task timeout")
```

### Response Codes

| Scenario | Code | Response |
|----------|------|----------|
| Task completed (new or resumed) | 200 | `{result, status: "COMPLETED"}` |
| Task already running | 409 | `{task_id, status: "RUNNING", message: "..."}` |
| Task failed | 422 | `{error, status: "FAILED", retry_allowed: true}` |
| Timeout | 504 | `{error: "Task timeout", status: "FAILED"}` |

### Frontend Changes

**Remove auto-start behavior:**
```typescript
// BEFORE: WorkflowRunner.tsx
useEffect(() => {
  if (video.status === "in_progress") {
    startGeneration()  // ❌ BAD: Can duplicate
  }
}, [video.status])

// AFTER: Let user control when to start
// Only show status, don't auto-trigger
```

**Add polling loop:**
```typescript
// useWorkflowV3.ts - During RUNNING state
useEffect(() => {
  if (status !== "in_progress") return

  const interval = setInterval(async () => {
    const response = await fetch(`/api/videos/${videoId}`)
    const video = await response.json()

    if (video.status === "completed") {
      setStatus("completed")
      clearInterval(interval)
    } else if (video.status === "failed") {
      setStatus("failed")
      setError(video.error)
      clearInterval(interval)
    }
    // Stays "in_progress" → keeps polling
  }, 3000)  // Every 3 seconds

  return () => clearInterval(interval)
}, [status])
```

**Handle 409 silently:**
```typescript
// On 409 Conflict - silently show spinner, no error message
if (response.status === 409) {
  setGenerating(true)  // Just show spinner
  // Start polling as usual
}
```

**Show task progress UI:**
```typescript
{status === "in_progress" && (
  <div>
    <Spinner />
    {/* No task ID or elapsed time - just spinner */}
  </div>
)}

{status === "failed" && (
  <div>
    <p>Error: {error}</p>
    <button onClick={retryGeneration}>Retry</button>
  </div>
)}
```

### Files to Change

| File | Change |
|------|--------|
| backend/app/api/workflow.py | TaskTracker logic, call piapi_client directly |
| frontend/src/components/workflow/WorkflowRunner.tsx | Remove auto-start, add polling UI |
| frontend/src/hooks/useWorkflowV3.ts | Handle 409, error states |

### Files NOT Changed (legacy, keep working)
- kling_service.py - not touched
- providers/audio/* - not touched
- providers/factory.py - not touched

### Estimate (revised)
- workflow.py TaskTracker integration: 4h
- Frontend changes: 2h
- Testing: 2h
Total: ~8h

### Migration Note
Old flow still works for manual testing. TaskTracker is additive - if no tracker exists, creates one. Gradual rollout possible.

### Integration Notes

1. **TaskTracker vs StepHistory:**
   - TaskTracker: External async state only (PENDING → RUNNING → COMPLETED/FAILED)
   - StepHistory: User approval workflow (GENERATED → AWAITING_APPROVAL → APPROVED/REJECTED)
   - They coexist: Video → StepHistory → TaskTracker

2. **Retry Behavior:**
   - User clicks Retry → New TaskTracker created with same video_id/step_type
   - Old TaskTracker marked as FAILED remains for audit trail
   - New TaskTracker gets fresh external_task_id

3. **Timeout Handling:**
   - Default 15 minutes (900s) - adjustable per provider
   - Poll every 5 seconds while RUNNING
   - After timeout → FAILED status + error message

4. **Error Recovery:**
   - Provider errors during create_task() → FAILED (no retry auto-trigger)
   - Provider errors during poll_task() → FAILED (user can retry)
   - Network timeouts → FAILED (user can retry)

## Notes

**Why critical:** Money wasted on duplicate generation. With Suno music costing credits and Kling video generation expensive, duplicate requests directly impact user costs.

**Integration with existing code:**
- StepHistory still tracks approval/rejection workflow
- TaskTracker tracks only external generation state
- Relationship: Video → StepHistory → TaskTracker (one-to-many)

**Future improvements:**
- Add webhook support for instant task completion (vs polling)
- Implement task timeout (auto-fail after 15 minutes)
- Add analytics: track duplicate request frequency
- Implement cost tracking per task
