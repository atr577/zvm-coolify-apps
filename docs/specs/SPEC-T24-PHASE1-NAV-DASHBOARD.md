---
id: SPEC-T24
title: "Phase 1: Template Project UX Redesign — Navigation + Dashboard"
status: draft
created: 2026-02-03
task: T24
target_sections: [Screen 1: Dashboard, Smart Default Screen, Navigation]
---

# Technical Specification: Phase 1 — Navigation + Dashboard

## Overview

Replace the current 5-tab template project navigation (generate, variants, templates, moderation, publishing) with a 3-screen JTBD-oriented structure (Dashboard, Review, Pipeline). Phase 1 implements the navigation structure, fully builds the Dashboard screen, and provides stub placeholders for Review and Pipeline screens (to be implemented in Phase 2 and 3).

**Key deliverables:**
- 3-screen navigation with URL routing (`?screen=dashboard|review|pipeline`)
- Smart default screen logic (determines which screen to show based on project state)
- Dashboard screen: Pipeline Funnel (4 counters), Schedule/Queue views, Pause toggle, Status messages, Onboarding
- Backend: `GET /api/projects/{id}/pipeline-stats` endpoint + `is_paused` field in PublishingConfig
- Review + Pipeline screens as stubs (preserving current functionality as fallback)

## Architecture

### Component Hierarchy

```
TemplateProjectView (refactored)
├─ Screen Router (useState: currentScreen)
│  ├─ Smart Default Screen Logic (on mount)
│  └─ URL Sync (?screen=...)
│
├─ DashboardScreen (NEW - fully implemented)
│  ├─ PipelineFunnel (NEW)
│  │  ├─ FunnelCounter: Generating
│  │  ├─ FunnelCounter: Review
│  │  ├─ FunnelCounter: Approved
│  │  └─ FunnelCounter: Schedule
│  │
│  ├─ StatusMessagesSection (NEW)
│  │  ├─ Next publish time
│  │  ├─ Warnings (empty slots, no platforms)
│  │  └─ Quick Action buttons
│  │
│  ├─ PauseToggle (NEW)
│  │  └─ Updates is_paused field
│  │
│  └─ ScheduleSection (reuses existing)
│     ├─ Calendar/Queue Toggle
│     ├─ PublishingScheduleView (EXISTING)
│     └─ PublishingQueueView (EXISTING)
│
├─ ReviewScreen (STUB - Phase 2)
│  ├─ Placeholder message
│  ├─ Pending count badge
│  └─ Fallback: render ModerationQueue (preserve functionality)
│
└─ PipelineScreen (STUB - Phase 3)
   ├─ Placeholder message
   └─ Fallback: render existing tabs (Generate, Variants, Templates)
```

### Changes Required

| Component | File | Change Type | Description |
|-----------|------|-------------|-------------|
| TemplateProjectView | `frontend/src/pages/TemplateProjectView.tsx` | Modify | Replace 5 tabs with 3 screens, add smart default logic |
| DashboardScreen | `frontend/src/components/template/DashboardScreen.tsx` | Add | New screen component |
| PipelineFunnel | `frontend/src/components/template/PipelineFunnel.tsx` | Add | Funnel visualization with 4 counters |
| ReviewScreen | `frontend/src/components/template/ReviewScreen.tsx` | Add | Stub component (Phase 2 placeholder) |
| PipelineScreen | `frontend/src/components/template/PipelineScreen.tsx` | Add | Stub component (Phase 3 placeholder) |
| PublishingConfig | `backend/app/models/publishing_config.py` | Modify | Add `is_paused` field |
| publishing_schedule.py | `backend/app/api/publishing_schedule.py` | Modify | Add pipeline-stats endpoint |
| projects.py | `backend/app/api/projects.py` | Modify | Add pipeline-stats endpoint (or in publishing_schedule.py) |
| PublishingTab | `frontend/src/components/template/PublishingTab.tsx` | Reuse | Components moved to Dashboard, file may be deprecated |
| api.ts | `frontend/src/services/api.ts` | Modify | Add types + API client for pipeline-stats, pause toggle |

## Data Structures

### Backend: Database Changes

**Migration: Add `is_paused` field to `publishing_configs` table**

```python
# alembic/versions/YYYYMMDD_add_is_paused_to_publishing_config.py

def upgrade():
    op.add_column(
        'publishing_configs',
        sa.Column('is_paused', sa.Boolean(), nullable=False, server_default='false')
    )

def downgrade():
    op.drop_column('publishing_configs', 'is_paused')
```

**Updated SQLAlchemy Model:**

```python
# backend/app/models/publishing_config.py

class PublishingConfig(Base):
    __tablename__ = "publishing_configs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), unique=True, nullable=False)

    enabled = Column(Boolean, nullable=False, default=False)
    is_paused = Column(Boolean, nullable=False, default=False)  # NEW

    days = Column(JSON, nullable=False, default=list)
    preferred_times = Column(JSON, nullable=False, default=list)
    depth_days = Column(Integer, nullable=False, default=7)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="publishing_config")
```

### Backend: API Contracts

#### 1. GET /api/projects/{id}/pipeline-stats

**Purpose:** Return counts for Pipeline Funnel visualization.

**Request:** None (URL param: `project_id`)

**Response:**
```json
{
  "generating_count": 3,        // TemplateGenerations with status='processing'
  "review_count": 5,             // TemplateGenerations pending moderation
  "approved_count": 12,          // ApprovedGenerations (queue items)
  "scheduled_count": 12,         // Slots filled in schedule
  "total_schedule_slots": 14     // Total slots in depth_days
}
```

**Implementation Logic:**
```python
# backend/app/api/projects.py or publishing_schedule.py

@router.get("/projects/{project_id}/pipeline-stats")
async def get_pipeline_stats(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = get_template_project(db, project_id, current_user)

    # Generating count: status='processing'
    generating_count = db.query(TemplateGeneration).filter(
        TemplateGeneration.project_id == project_id,
        TemplateGeneration.status == 'processing'
    ).count()

    # Review count: status in pending moderation states
    review_count = db.query(TemplateGeneration).filter(
        TemplateGeneration.project_id == project_id,
        TemplateGeneration.status.in_(['completed', 'pending_review'])  # adjust based on your status flow
    ).count()

    # Approved count: items in queue
    approved_count = db.query(ApprovedGeneration).filter(
        ApprovedGeneration.project_id == project_id,
        ApprovedGeneration.status == 'approved'
    ).count()

    # Schedule counts: compute from schedule
    config = get_or_create_config(db, project_id)
    slots = calculate_schedule_slots(config, project.timezone or 'UTC', config.depth_days)
    total_slots = len(slots)

    # Scheduled count: slots with items
    queue_items = db.query(ApprovedGeneration).filter(
        ApprovedGeneration.project_id == project_id,
        ApprovedGeneration.status == 'approved'
    ).order_by(ApprovedGeneration.position).limit(total_slots).all()
    scheduled_count = len(queue_items)

    return {
        "generating_count": generating_count,
        "review_count": review_count,
        "approved_count": approved_count,
        "scheduled_count": scheduled_count,
        "total_schedule_slots": total_slots
    }
```

#### 2. PATCH /api/projects/{id}/publishing-config (Update existing endpoint)

**Purpose:** Update `is_paused` field (plus existing fields).

**Request:**
```json
{
  "enabled": true,
  "is_paused": false,      // NEW
  "days": ["mon", "wed", "fri"],
  "preferred_times": ["18:00"],
  "depth_days": 14
}
```

**Response:** (existing `PublishingConfigResponse` schema + `is_paused`)

**Schema Update:**
```python
# backend/app/schemas/publishing.py

class PublishingConfigBase(BaseModel):
    enabled: bool = False
    is_paused: bool = False  # NEW
    days: List[str] = Field(default_factory=list)
    preferred_times: List[str] = Field(default_factory=lambda: ["18:00"])
    depth_days: int = Field(default=7, ge=1, le=30)
```

### Frontend: Types

**New Types:**

```typescript
// frontend/src/types/index.ts (or inline in api.ts)

export type ScreenType = 'dashboard' | 'review' | 'pipeline'

export interface PipelineStats {
  generating_count: number
  review_count: number
  approved_count: number
  scheduled_count: number
  total_schedule_slots: number
}

// Update existing PublishingConfigResponse to include is_paused
export interface PublishingConfigResponse {
  id: number
  project_id: number
  enabled: boolean
  is_paused: boolean  // NEW
  days: string[]
  preferred_times: string[]
  depth_days: number
  created_at?: string
  updated_at?: string
}
```

**API Client:**

```typescript
// frontend/src/services/api.ts

export const projectApi = {
  // ... existing methods

  async getPipelineStats(projectId: number): Promise<PipelineStats> {
    const response = await axiosInstance.get(`/projects/${projectId}/pipeline-stats`)
    return response.data
  }
}

export const publishingScheduleApi = {
  // ... existing methods (getConfig, updateConfig, getQueue, getSchedule, etc.)

  async updateConfig(projectId: number, config: Partial<PublishingConfigResponse>) {
    const response = await axiosInstance.put(`/projects/${projectId}/publishing-config`, config)
    return response
  }
}
```

## Implementation Steps

### Backend (Estimated: 3-4h)

1. [ ] **Migration: Add `is_paused` field**
   - Create migration file: `alembic revision --autogenerate -m "add_is_paused_to_publishing_config"`
   - Update `PublishingConfig` model in `backend/app/models/publishing_config.py`
   - Apply migration: `alembic upgrade head`

2. [ ] **Update Pydantic Schemas**
   - Add `is_paused` to `PublishingConfigBase` in `backend/app/schemas/publishing.py`
   - Verify in `PublishingConfigResponse`, `PublishingConfigUpdate`, `PublishingConfigCreate`

3. [ ] **Implement `GET /api/projects/{id}/pipeline-stats`**
   - Location: `backend/app/api/publishing_schedule.py` (or `projects.py`)
   - Add route with logic as described above
   - Test with various project states (no data, pending review, approved queue)

4. [ ] **Update `PUT /api/projects/{id}/publishing-config`**
   - Already exists, just ensure `is_paused` is handled
   - Verify response includes `is_paused`

5. [ ] **Run tests**
   - `cd backend && .venv/bin/pytest`
   - Fix any failures

### Frontend (Estimated: 15-18h)

#### Part 1: New Components (8h)

1. [ ] **Create `PipelineFunnel.tsx`**

```tsx
// frontend/src/components/template/PipelineFunnel.tsx

import { useState, useEffect } from 'react'
import { Loader2, PlayCircle, Eye, CheckCircle, Calendar } from 'lucide-react'
import { projectApi, type PipelineStats } from '@/services/api'

interface PipelineFunnelProps {
  projectId: number
  onNavigate: (target: 'review' | 'pipeline' | 'queue' | 'calendar') => void
}

export function PipelineFunnel({ projectId, onNavigate }: PipelineFunnelProps) {
  const [stats, setStats] = useState<PipelineStats | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchStats = async () => {
    try {
      const data = await projectApi.getPipelineStats(projectId)
      setStats(data)
    } catch (err) {
      console.error('Failed to load pipeline stats:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStats()
    // Auto-refresh every 30s
    const interval = setInterval(fetchStats, 30000)
    return () => clearInterval(interval)
  }, [projectId])

  if (loading) {
    return <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 animate-spin text-gray-400" /></div>
  }

  if (!stats) return null

  const counters = [
    { label: 'Generating', count: stats.generating_count, icon: PlayCircle, onClick: () => onNavigate('pipeline') },
    { label: 'Review', count: stats.review_count, icon: Eye, onClick: () => onNavigate('review'), highlight: stats.review_count > 0 },
    { label: 'Approved', count: stats.approved_count, icon: CheckCircle, onClick: () => onNavigate('queue') },
    { label: 'Schedule', count: `${stats.scheduled_count}/${stats.total_schedule_slots}`, icon: Calendar, onClick: () => onNavigate('calendar') }
  ]

  return (
    <div className="bg-white rounded-lg border p-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">Pipeline Status</h3>
      <div className="grid grid-cols-4 gap-4">
        {counters.map((c, idx) => (
          <button
            key={c.label}
            onClick={c.onClick}
            className={`flex flex-col items-center p-4 rounded-lg border transition-all ${
              c.highlight ? 'bg-purple-50 border-purple-300 hover:bg-purple-100' : 'hover:bg-gray-50 border-gray-200'
            }`}
          >
            <c.icon className={`w-6 h-6 mb-2 ${c.highlight ? 'text-purple-600' : 'text-gray-400'}`} />
            <div className={`text-2xl font-bold ${c.highlight ? 'text-purple-700' : 'text-gray-900'}`}>
              {c.count}
            </div>
            <div className="text-xs text-gray-500 mt-1">{c.label}</div>
          </button>
        ))}
      </div>
    </div>
  )
}
```

2. [ ] **Create `DashboardScreen.tsx`**

```tsx
// frontend/src/components/template/DashboardScreen.tsx

import { useState } from 'react'
import { AlertCircle, PlayCircle } from 'lucide-react'
import { PipelineFunnel } from './PipelineFunnel'
import { PublishingScheduleView } from './PublishingScheduleView'
import { PublishingQueueView } from './PublishingQueueView'
import { publishingScheduleApi, type PublishingScheduleResponse, type PublishingConfigResponse } from '@/services/api'

interface DashboardScreenProps {
  projectId: number
  projectTimezone?: string
  onNavigate: (screen: 'review' | 'pipeline', options?: { section?: string }) => void
  config: PublishingConfigResponse | null
  schedule: PublishingScheduleResponse | null
  onRefresh: () => void
  onUpdateConfig: (updates: Partial<PublishingConfigResponse>) => Promise<void>
}

export function DashboardScreen({
  projectId,
  projectTimezone,
  onNavigate,
  config,
  schedule,
  onRefresh,
  onUpdateConfig
}: DashboardScreenProps) {
  const [view, setView] = useState<'calendar' | 'queue'>('calendar')
  const [isPauseToggling, setIsPauseToggling] = useState(false)

  const handleFunnelNavigate = (target: 'review' | 'pipeline' | 'queue' | 'calendar') => {
    if (target === 'review') {
      onNavigate('review')
    } else if (target === 'pipeline') {
      onNavigate('pipeline', { section: 'run' })
    } else if (target === 'queue') {
      setView('queue')
      // Scroll to schedule section
      document.getElementById('schedule-section')?.scrollIntoView({ behavior: 'smooth' })
    } else if (target === 'calendar') {
      setView('calendar')
      document.getElementById('schedule-section')?.scrollIntoView({ behavior: 'smooth' })
    }
  }

  const handlePauseToggle = async () => {
    if (!config) return
    try {
      setIsPauseToggling(true)
      await onUpdateConfig({ is_paused: !config.is_paused })
    } catch (err) {
      console.error('Failed to toggle pause:', err)
      alert('Failed to update pause status')
    } finally {
      setIsPauseToggling(false)
    }
  }

  const isConfigured = config && config.days.length > 0 && config.preferred_times.length > 0

  // Onboarding state: no variants or templates
  const showOnboarding = false // TODO: check project.variants.length === 0 || project.templates.length === 0

  if (showOnboarding) {
    return (
      <div className="space-y-6">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-yellow-600 mt-0.5" />
            <div>
              <h3 className="font-medium text-yellow-900 mb-2">Pipeline not configured</h3>
              <p className="text-sm text-yellow-800 mb-4">
                Set up your pipeline to start generating videos.
              </p>
              <button
                onClick={() => onNavigate('pipeline')}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition"
              >
                → Open Pipeline Setup
              </button>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg border p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-2">Schedule</h3>
          <p className="text-sm text-gray-500">
            No schedule configured. Configure days and times in Pipeline → Distribution.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Pipeline Funnel */}
      <PipelineFunnel projectId={projectId} onNavigate={handleFunnelNavigate} />

      {/* Status + Quick Actions */}
      <div className="bg-white rounded-lg border p-6">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            {config?.is_paused && (
              <div className="flex items-center gap-2 text-yellow-700 bg-yellow-50 px-3 py-2 rounded">
                <AlertCircle className="w-4 h-4" />
                <span className="text-sm font-medium">Publishing paused</span>
              </div>
            )}
            {schedule && schedule.slots.length > 0 && (
              <p className="text-sm text-gray-600">
                Next publish: {new Date(schedule.slots[0]?.scheduled_at).toLocaleString()}
              </p>
            )}
            {schedule && schedule.warnings.map((w, idx) => (
              <p key={idx} className="text-sm text-yellow-600">⚠️ {w.message}</p>
            ))}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => onNavigate('review')}
              className="px-4 py-2 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition"
            >
              → Review videos
            </button>
            <button
              onClick={() => onNavigate('pipeline', { section: 'run' })}
              className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition"
            >
              → Run pipeline
            </button>
          </div>
        </div>
      </div>

      {/* Schedule Section */}
      <div id="schedule-section">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-gray-900">Schedule</h3>
          <div className="flex items-center gap-4">
            {/* Pause Toggle */}
            {isConfigured && (
              <label className="flex items-center gap-2 cursor-pointer">
                <span className="text-sm text-gray-600">Pause</span>
                <button
                  onClick={handlePauseToggle}
                  disabled={isPauseToggling}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${
                    config?.is_paused ? 'bg-yellow-500' : 'bg-gray-300'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${
                      config?.is_paused ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </label>
            )}

            {/* Calendar/Queue Toggle */}
            <div className="flex border rounded-lg overflow-hidden">
              <button
                onClick={() => setView('calendar')}
                className={`px-4 py-1 text-sm transition ${
                  view === 'calendar' ? 'bg-purple-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'
                }`}
              >
                Calendar
              </button>
              <button
                onClick={() => setView('queue')}
                className={`px-4 py-1 text-sm transition ${
                  view === 'queue' ? 'bg-purple-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'
                }`}
              >
                Queue
              </button>
            </div>
          </div>
        </div>

        {view === 'calendar' && schedule && <PublishingScheduleView schedule={schedule} onRefresh={onRefresh} />}
        {view === 'queue' && <PublishingQueueView projectId={projectId} onRefresh={onRefresh} />}
      </div>
    </div>
  )
}
```

3. [ ] **Create `ReviewScreen.tsx` (stub)**

```tsx
// frontend/src/components/template/ReviewScreen.tsx

import { AlertCircle } from 'lucide-react'
import { ModerationQueue } from './ModerationQueue'  // Preserve existing functionality
import { RejectionArchive } from './RejectionArchive'

interface ReviewScreenProps {
  projectId: number
  pendingCount: number
  onNavigate: (screen: 'dashboard' | 'pipeline') => void
}

export function ReviewScreen({ projectId, pendingCount, onNavigate }: ReviewScreenProps) {
  // Phase 1: Stub with fallback to existing moderation components
  const showStub = true // Change to false when Phase 2 is ready

  if (showStub) {
    return (
      <div className="space-y-6">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 text-center">
          <AlertCircle className="w-8 h-8 text-blue-600 mx-auto mb-3" />
          <h3 className="text-lg font-medium text-blue-900 mb-2">
            Review interface coming in Phase 2
          </h3>
          <p className="text-sm text-blue-700 mb-4">
            The new focused review experience is under development. For now, you can use the legacy moderation queue below.
          </p>
          {pendingCount > 0 && (
            <p className="text-sm font-medium text-blue-900">
              {pendingCount} videos pending review
            </p>
          )}
        </div>

        {/* Fallback: render existing moderation components */}
        <div className="opacity-75">
          <h4 className="text-sm font-medium text-gray-500 mb-3">(Legacy Moderation Queue)</h4>
          <ModerationQueue projectId={projectId} />
          <div className="mt-6">
            <RejectionArchive projectId={projectId} />
          </div>
        </div>
      </div>
    )
  }

  // Phase 2: Full implementation will go here
  return <div>Phase 2 Review Screen</div>
}
```

4. [ ] **Create `PipelineScreen.tsx` (stub)**

```tsx
// frontend/src/components/template/PipelineScreen.tsx

import { AlertCircle } from 'lucide-react'
import { GenerationPanel } from './GenerationPanel'  // Preserve existing functionality
import { GenerationsList } from './GenerationsList'
import { CsvUpload } from './CsvUpload'
import { VariantsList } from './VariantsList'
import { VideoTemplatesList } from './VideoTemplatesList'

interface PipelineScreenProps {
  projectId: number
  onNavigate: (screen: 'dashboard' | 'review') => void
  // ... other props for fallback components
}

export function PipelineScreen({ projectId, onNavigate, ...fallbackProps }: PipelineScreenProps) {
  // Phase 1: Stub with fallback to existing tabs
  const showStub = true // Change to false when Phase 3 is ready

  if (showStub) {
    return (
      <div className="space-y-6">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 text-center">
          <AlertCircle className="w-8 h-8 text-blue-600 mx-auto mb-3" />
          <h3 className="text-lg font-medium text-blue-900 mb-2">
            Pipeline configuration coming in Phase 3
          </h3>
          <p className="text-sm text-blue-700 mb-4">
            The new unified pipeline view is under development. For now, you can use the legacy tabs below.
          </p>
        </div>

        {/* Fallback: render existing tab content */}
        <div className="opacity-75">
          <h4 className="text-sm font-medium text-gray-500 mb-3">(Legacy Tabs)</h4>

          {/* Render existing components in a simplified layout */}
          <div className="space-y-6">
            <div>
              <h5 className="font-medium mb-2">Generate</h5>
              <GenerationPanel {...fallbackProps} />
              <GenerationsList {...fallbackProps} />
            </div>

            <div>
              <h5 className="font-medium mb-2">Variants</h5>
              <CsvUpload {...fallbackProps} />
              <VariantsList {...fallbackProps} />
            </div>

            <div>
              <h5 className="font-medium mb-2">Templates</h5>
              <VideoTemplatesList {...fallbackProps} />
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Phase 3: Full implementation will go here
  return <div>Phase 3 Pipeline Screen</div>
}
```

#### Part 2: Refactor TemplateProjectView (6h)

5. [ ] **Refactor `TemplateProjectView.tsx`**

Key changes:
- Replace `TabType` with `ScreenType`
- Replace tab state with screen state
- Add smart default screen logic
- Add URL sync (`?screen=...`)
- Render DashboardScreen, ReviewScreen, PipelineScreen instead of tabs
- Add screen badge for review count

```tsx
// frontend/src/pages/TemplateProjectView.tsx (refactored)

import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { DashboardScreen } from '@/components/template/DashboardScreen'
import { ReviewScreen } from '@/components/template/ReviewScreen'
import { PipelineScreen } from '@/components/template/PipelineScreen'
import { publishingScheduleApi, projectApi, type PipelineStats } from '@/services/api'

type ScreenType = 'dashboard' | 'review' | 'pipeline'

interface TemplateProjectViewProps {
  projectId: number
  projectName: string
  projectTimezone?: string
}

export function TemplateProjectView({ projectId, projectName, projectTimezone }: TemplateProjectViewProps) {
  const [searchParams, setSearchParams] = useSearchParams()
  const [currentScreen, setCurrentScreen] = useState<ScreenType>('dashboard')
  const [config, setConfig] = useState(null)
  const [schedule, setSchedule] = useState(null)
  const [stats, setStats] = useState<PipelineStats | null>(null)

  // Smart default screen logic
  useEffect(() => {
    const determineDefaultScreen = async () => {
      try {
        const statsData = await projectApi.getPipelineStats(projectId)
        setStats(statsData)

        // Smart logic (matches UX spec)
        let defaultScreen: ScreenType = 'dashboard'

        // TODO: Add check for variants/templates count
        // if (no variants or no templates) → 'pipeline'

        if (statsData.review_count > 0) {
          defaultScreen = 'review'
        } else if (statsData.generating_count > 0) {
          defaultScreen = 'pipeline'
        }

        // URL param overrides smart default
        const urlScreen = searchParams.get('screen') as ScreenType | null
        if (urlScreen && ['dashboard', 'review', 'pipeline'].includes(urlScreen)) {
          setCurrentScreen(urlScreen)
        } else {
          setCurrentScreen(defaultScreen)
          setSearchParams({ screen: defaultScreen })
        }
      } catch (err) {
        console.error('Failed to determine default screen:', err)
      }
    }

    determineDefaultScreen()
  }, [projectId])

  // Fetch config + schedule
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [configRes, scheduleRes] = await Promise.all([
          publishingScheduleApi.getConfig(projectId),
          publishingScheduleApi.getSchedule(projectId)
        ])
        setConfig(configRes.data)
        setSchedule(scheduleRes.data)
      } catch (err) {
        console.error('Failed to load data:', err)
      }
    }
    fetchData()
  }, [projectId])

  const handleNavigate = (screen: ScreenType, options?: { section?: string }) => {
    setCurrentScreen(screen)
    setSearchParams({ screen })
    // TODO: handle options.section for scroll/focus
  }

  const handleRefresh = () => {
    // Re-fetch config + schedule
    // ... (same logic as above)
  }

  const handleUpdateConfig = async (updates: Partial<PublishingConfigResponse>) => {
    await publishingScheduleApi.updateConfig(projectId, updates)
    handleRefresh()
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">{projectName}</h1>
        <button>⚙️ Settings</button>
      </div>

      {/* Screen Switcher */}
      <div className="flex gap-2 border-b mb-6">
        <button
          onClick={() => handleNavigate('dashboard')}
          className={`px-4 py-2 border-b-2 transition ${
            currentScreen === 'dashboard'
              ? 'border-purple-600 text-purple-600 font-medium'
              : 'border-transparent text-gray-600 hover:text-gray-900'
          }`}
        >
          Dashboard
        </button>
        <button
          onClick={() => handleNavigate('review')}
          className={`px-4 py-2 border-b-2 transition ${
            currentScreen === 'review'
              ? 'border-purple-600 text-purple-600 font-medium'
              : 'border-transparent text-gray-600 hover:text-gray-900'
          }`}
        >
          Review
          {stats && stats.review_count > 0 && (
            <span className="ml-2 px-2 py-0.5 text-xs bg-purple-100 text-purple-700 rounded-full">
              {stats.review_count}
            </span>
          )}
        </button>
        <button
          onClick={() => handleNavigate('pipeline')}
          className={`px-4 py-2 border-b-2 transition ${
            currentScreen === 'pipeline'
              ? 'border-purple-600 text-purple-600 font-medium'
              : 'border-transparent text-gray-600 hover:text-gray-900'
          }`}
        >
          Pipeline
        </button>
      </div>

      {/* Screen Content */}
      {currentScreen === 'dashboard' && (
        <DashboardScreen
          projectId={projectId}
          projectTimezone={projectTimezone}
          onNavigate={handleNavigate}
          config={config}
          schedule={schedule}
          onRefresh={handleRefresh}
          onUpdateConfig={handleUpdateConfig}
        />
      )}

      {currentScreen === 'review' && (
        <ReviewScreen
          projectId={projectId}
          pendingCount={stats?.review_count || 0}
          onNavigate={handleNavigate}
        />
      )}

      {currentScreen === 'pipeline' && (
        <PipelineScreen
          projectId={projectId}
          onNavigate={handleNavigate}
          // ... pass fallback props
        />
      )}
    </div>
  )
}
```

#### Part 3: API Client + Types (1h)

6. [ ] **Update `api.ts`**
   - Add `getPipelineStats` to `projectApi`
   - Add `is_paused` to `PublishingConfigResponse` type
   - Ensure `updateConfig` accepts `is_paused`

7. [ ] **Update `types/index.ts`**
   - Add `ScreenType` type
   - Add `PipelineStats` interface
   - Update `PublishingConfigResponse` with `is_paused`

#### Part 4: Build + Testing (3h)

8. [ ] **Frontend build verification**
   - `cd frontend && npm run build`
   - Fix TypeScript errors, unused imports

9. [ ] **Manual E2E Testing**
   - Create/open template project → verify default screen logic
   - Navigate between screens → verify URL sync
   - Dashboard: verify funnel counters, pause toggle, calendar/queue
   - Review/Pipeline: verify stubs render with fallback content
   - Verify review badge count

10. [ ] **Backend tests**
    - `cd backend && .venv/bin/pytest`
    - Add test for pipeline-stats endpoint
    - Add test for `is_paused` field update

## Edge Cases

| Case | Handling |
|------|----------|
| Project with no variants/templates | Dashboard shows onboarding state, smart default → Pipeline |
| Project with no schedule configured | Calendar view shows "not configured" message |
| Pause toggle while no distribution | Toggle disabled, tooltip: "Configure distribution first" |
| Pipeline stats endpoint error | Funnel shows "—" or loading state, retry button |
| Review count = 0 | Review screen shows "All caught up" message |
| URL param `?screen=invalid` | Fallback to smart default screen |
| User manually navigates to Review (URL) | Overrides smart default, respects user intent |

## Testing

### Manual Tests

- [ ] **Dashboard rendering:**
  - [ ] Pipeline funnel displays correct counts
  - [ ] Funnel counters are clickable (navigate/scroll)
  - [ ] Pause toggle works (visual + persists)
  - [ ] Calendar/Queue toggle works
  - [ ] Status messages appear correctly
  - [ ] Onboarding state for new projects

- [ ] **Navigation:**
  - [ ] 3-screen switcher visible
  - [ ] Review badge shows pending count
  - [ ] URL updates on screen change (`?screen=...`)
  - [ ] Reload preserves screen from URL

- [ ] **Smart default screen:**
  - [ ] New project (no data) → Pipeline
  - [ ] Pending moderation → Review
  - [ ] Otherwise → Dashboard

- [ ] **Review/Pipeline stubs:**
  - [ ] Placeholder text visible
  - [ ] Fallback content renders (legacy tabs)

### Build Verification

- [ ] Backend: `cd backend && .venv/bin/pytest` passes
- [ ] Frontend: `cd frontend && npm run build` passes
- [ ] No TypeScript errors
- [ ] No unused imports

## Dependencies

**Existing:**
- `PublishingScheduleView` — reused in Dashboard
- `PublishingQueueView` — reused in Dashboard
- `PublishingTab` — deprecated after migration (components extracted)
- `ModerationQueue`, `RejectionArchive` — reused in Review stub fallback
- `GenerationPanel`, `GenerationsList`, `CsvUpload`, `VariantsList`, `VideoTemplatesList` — reused in Pipeline stub fallback

**New:**
- None (all frontend dependencies are React + existing lucide-react icons)

## Open Questions

- [ ] **Smart default logic for "no variants/templates" check:** Need to fetch project.variants and project.templates counts. Should this be part of `pipeline-stats` response or separate endpoint?
  - **Decision:** Add to `pipeline-stats` response: `{ ..., variants_count: N, templates_count: M }`

- [ ] **Pause toggle logic in APScheduler:** Does the scheduler already check a flag before publishing? If not, where to add this check?
  - **Decision:** Add check in publishing job (separate from this task, track in T25 or separate bug fix)

- [ ] **Review stub: Should we render existing ModerationQueue or just show message?**
  - **Decision:** Render existing ModerationQueue as fallback (user can still work) + show message that new UI is coming

- [ ] **Pipeline stub: Same question — render existing tabs or just show message?**
  - **Decision:** Render existing tabs (Generate, Variants, Templates) as fallback + show message

## Notes

**Phase sequencing:**
- Phase 1 (this spec): Structure + Dashboard
- Phase 2 (T25): Review screen (focused review, filmstrip, metadata editing)
- Phase 3 (T26): Pipeline screen (Configure steps, Run section, tests)
- Phase 4 (T27): Polish (create modal simplification, settings cleanup)

**No functionality loss:**
- Stub screens preserve existing components as fallback
- Users can continue working with legacy UI while new screens are built

**Backward compatibility:**
- URL param `?tab=generate` should redirect to `?screen=pipeline` (add fallback logic)
- Old deeplinks remain valid (or show migration notice)

**Performance:**
- Pipeline stats auto-refresh every 30s (avoid overloading backend)
- Use debounce for pause toggle (prevent rapid clicks)

---

**File:** `docs/specs/SPEC-T24-PHASE1-NAV-DASHBOARD.md`

**Status:** Draft (awaiting approval)
