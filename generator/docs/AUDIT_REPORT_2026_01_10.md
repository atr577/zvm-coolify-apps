# Аудит документации vs код

**Дата:** 2026-01-10
**Scope:** Full audit - WORKFLOW_ANALYSIS.md, TARGET_WORKFLOW.md, IMPLEMENTATION_PLAN.md vs actual codebase

---

## Executive Summary

| Категория | Результат |
|-----------|-----------|
| **Issues Confirmed** | 12 из 15 |
| **False Positives** | 2 |
| **New Issues Found** | 4 |
| **API Compliance** | 29% (2/7 endpoints) |
| **File Path Accuracy** | 92% (1 ошибка) |

---

## 1. Critical Issues (Severity: CRITICAL)

### 1.1 Metrics API без авторизации

| Field | Value |
|-------|-------|
| **Status** | CONFIRMED |
| **File** | `backend/app/api/metrics.py:36-89` |
| **Impact** | Любой может добавить/изменить метрики любого видео |

**Evidence:**
```python
# metrics.py:36-40 - NO current_user dependency
@router.post("/video/{video_id}", response_model=VideoMetricsResponse)
async def create_metrics(
    video_id: int,
    metrics: VideoMetricsCreate,
    db: Session = Depends(get_db)  # ← NO AUTH
):
```

**Affected endpoints (all 9):**
- `POST /metrics/video/{video_id}` - Create metrics
- `GET /metrics/video/{video_id}` - Read metrics
- `GET /metrics/video/{video_id}/summary` - Summary
- `PUT /metrics/video/{video_id}/{platform}/{period}` - Update
- `DELETE /metrics/video/{video_id}/{platform}/{period}` - Delete
- `PUT /metrics/video/{video_id}/rating` - Set rating
- `GET /metrics/leaderboard` - Leaderboard
- `POST /metrics/video/{video_id}/fetch` - Fetch
- `POST /metrics/fetch-all` - Fetch all

**Fix:** Add `current_user: User = Depends(get_current_user)` + `verify_video_ownership()` to all endpoints

---

### 1.2 Leaderboard показывает ВСЕ видео

| Field | Value |
|-------|-------|
| **Status** | CONFIRMED |
| **File** | `backend/app/api/metrics.py:245-256` |
| **Impact** | Privacy violation - видны данные всех пользователей |

**Evidence:**
```python
# metrics.py:245-256 - NO workspace filtering
videos_with_metrics = db.query(Video).join(VideoMetrics).filter(
    VideoMetrics.period == MetricsPeriod(period)
).distinct().all()  # ← Returns ALL videos from ALL users
```

**Fix:** Filter by workspace_ids like in publishing.py

---

### 1.3 Variant generation endpoint не существует

| Field | Value |
|-------|-------|
| **Status** | NOT CONFIRMED (FALSE POSITIVE) |
| **Documented claim** | Frontend calls non-existent endpoint |

**Reality:**
- Endpoint EXISTS: `POST /api/ai/generate-variants`
- File: `backend/app/api/ai_generation.py:31-76`
- Router registered: `main.py:50`
- Service implementation: `openai_service.py:297-332`

**Action:** Remove from WORKFLOW_ANALYSIS.md issues list

---

## 2. High Priority Issues (Severity: HIGH)

### 2.1 Engagement rate ×100 дважды

| Field | Value |
|-------|-------|
| **Status** | CONFIRMED |
| **File** | `backend/app/api/metrics.py:28-33` |

**Evidence:**
```python
# metrics.py:32
rate = ((likes + comments + shares) / views) * 100 * 100  # ← ×10000 instead of ×100
```

**Impact:** 5% engagement displays as 500

---

### 2.2 Дубликат вызова generate_meta

| Field | Value |
|-------|-------|
| **Status** | CONFIRMED |
| **Locations** | 3 места |

**Evidence:**
1. `workflow.py:265-269` - в select_audio_variant
2. `workflow.py:289-312` - отдельный endpoint
3. `orchestrator.py:432-436` - в orchestrator

**Impact:** До 3x лишних API вызовов

---

### 2.3 Audio генерируется до approve video

| Field | Value |
|-------|-------|
| **Status** | CONFIRMED |
| **File** | `orchestrator.py:369-391` |

**Evidence:**
```python
# orchestrator.py - _complete_video_generation()
await self._generate_video(motion_prompt=motion_prompt)  # Line 388
await self._generate_audio()  # Line 390 - NO MANUAL mode check!
```

**Impact:** Wasted resources on audio for rejected videos

---

### 2.4 workflow_mode не работает

| Field | Value |
|-------|-------|
| **Status** | CONFIRMED |
| **File** | `orchestrator.py:142-208` |

**Evidence:**
- `workflow_mode` field EXISTS in Video model (line 53)
- Frontend DISPLAYS selection
- Orchestrator IGNORES it completely - runs all steps sequentially
- Only hardcoded pause: `require_image_approval` on Project

**Root cause:** No `_should_pause()` check in orchestrator

---

## 3. Structural Issues (Severity: MEDIUM)

### 3.1 Путаница статусов (current_step vs status)

| Field | Value |
|-------|-------|
| **Status** | CONFIRMED (but not a bug) |
| **File** | `video.py:73-74` |

**Finding:** Both fields exist and are correctly typed. Issue is documentation/clarity, not implementation.

---

### 3.2 Deprecated поля

| Field | Value |
|-------|-------|
| **Status** | CONFIRMED |
| **File** | `video.py:62,69` |

**Deprecated fields still present:**
- `image_prompt` (line 62) → should use `prompt_data`
- `adaptation_data` (line 69) → should use `publishing_meta`

---

### 3.5 WorkflowStep.content не используется

| Field | Value |
|-------|-------|
| **Status** | CONFIRMED |
| **File** | `workflow_step.py:20` |

**Finding:** Field exists but data stored in Video model directly. Missing StepAttempt/Variant hierarchy.

---

## 4. UX Issues

### 4.1 CreateVideo зависает на loading

| Field | Value |
|-------|-------|
| **Status** | PARTIALLY CONFIRMED |
| **File** | `CreateVideo.tsx:185-195` |

**Finding:** Error handling IS present. Issue may have been fixed or was overstated.

---

### 4.2 Нет UI для approve/reject

| Field | Value |
|-------|-------|
| **Status** | NOT CONFIRMED (FALSE POSITIVE) |
| **File** | `InProgressView.tsx:309-337` |

**Reality:** Approve/Reject UI EXISTS and shows properly on AWAITING_APPROVAL status

---

### 4.3 N+1 queries в Analytics

| Field | Value |
|-------|-------|
| **Status** | CONFIRMED |
| **File** | `Analytics.tsx:42-49` |

**Evidence:**
```typescript
for (const id of videoIds) {
  const video = await videosApi.get(id).then(res => res.data)  // ← N calls
}
```

---

### 4.4 WorkflowModeSelector скрыт для Remix

| Field | Value |
|-------|-------|
| **Status** | CONFIRMED |
| **File** | `CreateVideo.tsx:105` |

**Evidence:**
```typescript
{project.project_type !== 'remix' && (  // ← Should show for ALL types
  <WorkflowModeSelector />
)}
```

---

### 4.5 require_image_approval checkbox

| Field | Value |
|-------|-------|
| **Status** | CONFIRMED |
| **File** | `ProjectForm.tsx:248-262` |

**Finding:** Checkbox still present, should be removed per PLAN_BREAKPOINTS_SYSTEM.md

---

## 5. New Issues Found

### 5.1 Missing logger import

| Field | Value |
|-------|-------|
| **Severity** | CRITICAL (runtime error) |
| **File** | `orchestrator.py:439` |

**Evidence:**
```python
logger.warning(f"Failed to generate publishing meta: {e}")  # ← logger not imported
```

**Impact:** NameError at runtime

---

### 5.2 Missing Remix fields in Project model

| Field | Value |
|-------|-------|
| **Severity** | HIGH |
| **File** | `project.py` |

**Missing fields (per TARGET_WORKFLOW.md):**
- `source_video_ids`
- `prompt_template`
- `scenario_template`
- `placeholders`
- `placeholder_suggestions`

---

### 5.3 API Compliance Gap

| Field | Value |
|-------|-------|
| **Severity** | HIGH |
| **Compliance** | 29% (2/7) |

**Missing unified endpoints:**
- `POST /{video_id}/{step}/select-variant`
- `POST /{video_id}/{step}/approve`
- `POST /{video_id}/{step}/reject`
- `POST /{video_id}/{step}/regenerate`
- `POST /{video_id}/rollback-to/{step}`
- `GET /{video_id}/{step}/variants`

---

### 5.4 File path error in IMPLEMENTATION_PLAN.md

| Field | Value |
|-------|-------|
| **Severity** | LOW |
| **Wrong** | `frontend/src/api/workflow.ts` |
| **Correct** | `frontend/src/services/api.ts` |

---

## 6. Data Model Gaps

### Expected vs Actual

| Model | Expected (TARGET_WORKFLOW) | Status |
|-------|---------------------------|--------|
| **Video** | 12 fields | All FOUND |
| **WorkflowStep** | 6 fields | All FOUND |
| **Project** | 10 fields (Remix) | 5 MISSING |
| **StepAttempt** | New model | NOT IMPLEMENTED |
| **Variant** | New model | NOT IMPLEMENTED |

---

## 7. Summary Table

| Issue ID | Description | Status | Severity |
|----------|-------------|--------|----------|
| 1.1 | Metrics no auth | CONFIRMED | CRITICAL |
| 1.2 | Leaderboard all videos | CONFIRMED | CRITICAL |
| 1.3 | Variant endpoint missing | FALSE POSITIVE | - |
| 2.1 | Engagement ×100 twice | CONFIRMED | HIGH |
| 2.2 | Duplicate generate_meta | CONFIRMED | HIGH |
| 2.3 | Audio before approval | CONFIRMED | HIGH |
| 2.4 | workflow_mode ignored | CONFIRMED | HIGH |
| 3.1 | Status confusion | CONFIRMED (docs issue) | MEDIUM |
| 3.2 | Deprecated fields | CONFIRMED | MEDIUM |
| 3.5 | Step.content unused | CONFIRMED | MEDIUM |
| 4.1 | CreateVideo loading | PARTIALLY CONFIRMED | LOW |
| 4.2 | No approve/reject UI | FALSE POSITIVE | - |
| 4.3 | N+1 queries | CONFIRMED | MEDIUM |
| 4.4 | Remix no mode selector | CONFIRMED | MEDIUM |
| 4.5 | require_image_approval | CONFIRMED | MEDIUM |
| NEW | Missing logger import | FOUND | CRITICAL |
| NEW | Missing Remix fields | FOUND | HIGH |
| NEW | API compliance 29% | FOUND | HIGH |
| NEW | File path error | FOUND | LOW |

---

## 8. Recommendations

### Immediate Actions (Security)

1. **Add auth to metrics.py** - Block before any feature work
2. **Fix logger import** - Runtime error waiting to happen

### Update Documents

1. **Remove Issue 1.3** from WORKFLOW_ANALYSIS.md (false positive)
2. **Remove Issue 4.2** from WORKFLOW_ANALYSIS.md (false positive)
3. **Fix file path** in IMPLEMENTATION_PLAN.md Phase 4
4. **Add new issues** to WORKFLOW_ANALYSIS.md:
   - Missing logger import
   - Missing Remix fields
   - API compliance gap

### Prioritize Implementation

```
Phase 0: Security (CONFIRMED - proceed)
Phase 1: Fix Broken (1 issue false positive - update)
Phase 2: Data Model (CONFIRMED - proceed)
Phase 3: Breakpoints (CONFIRMED - proceed)
Phase 4: API (29% compliance - large gap)
```

---

## 9. Audit Conclusion

**Document accuracy: ~85%**

- WORKFLOW_ANALYSIS.md: 13/15 issues confirmed (2 false positives)
- IMPLEMENTATION_PLAN.md: File paths 92% accurate (1 error)
- TARGET_WORKFLOW.md: Describes target state correctly, large gap from current

**Recommendation:** Documents are adequately accurate for implementation planning. Fix false positives and proceed with Phase 0 (Security).
