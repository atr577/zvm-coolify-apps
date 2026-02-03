---
id: SPEC-T26-PHASE3A
title: Pipeline Configure Section - UX Redesign Phase 3A
status: draft
created: 2026-02-03
target_sections: [Pipeline, Template Settings, Distribution]
---

# Technical Specification: Pipeline Configure Section (Phase 3A)

## Overview

Consolidate all pipeline configuration into a single unified **Configure** section on the Pipeline screen. Currently, settings are scattered across TemplateSettingsForm (~478 lines) and DashboardScreen (publishing config + pause toggle). Phase 3A creates a collapsible accordion-based interface with 5 steps (Input → Preprocessing → Image → Video → Distribution), reusing existing components wherever possible.

**Zero backend changes required** — all APIs already exist.

## Problem Statement

### Current State (Fragmented)

| Configuration | Location | File |
|---------------|----------|------|
| CSV upload + variants | PipelineScreen → Variants section | `PipelineScreen.tsx` |
| Video templates | PipelineScreen → Templates section | `PipelineScreen.tsx` |
| LLM model, preprocessing prompt, image prompt | TemplateSettingsForm | `TemplateSettingsForm.tsx` |
| Image model, aspect ratio | TemplateSettingsForm | `TemplateSettingsForm.tsx` |
| Video model, duration | TemplateSettingsForm | `TemplateSettingsForm.tsx` |
| Social accounts | TemplateSettingsForm | `TemplateSettingsForm.tsx` |
| Publishing schedule (days, times, depth) | DashboardScreen | `DashboardScreen.tsx` |
| Pause toggle | DashboardScreen | `DashboardScreen.tsx` |

### Issues

1. **Cognitive load** — users must navigate between 3 different screens to configure the pipeline
2. **No visual overview** — can't see "Input → Preproc → Image → Video → Distribution" status at a glance
3. **Redundant navigation** — settings page is separate from pipeline execution
4. **Poor discoverability** — new users don't know where to configure each step

### Target State (Unified)

**Single Configure section** on PipelineScreen with:
- Collapsed summary shows status of all 5 steps at a glance
- Expanded accordion shows detailed settings for each step
- Sticky save bar tracks changes across all steps
- Auto-expand when configuration is incomplete (no variants / no accounts)

## Solution Architecture

### Component Hierarchy

```
PipelineScreen (modified)
├── Configure Section (NEW)
│   ├── Summary Line (collapsed state) ── shows ✅/❌ status for each step
│   └── Accordion (expanded state) ── one step open at a time
│       ├── Step 1: Input (NEW wrapper)
│       │   ├── CsvUpload (reuse existing)
│       │   └── VariantsList (reuse existing)
│       ├── Step 2: Preprocessing (NEW)
│       │   ├── LLM model select
│       │   ├── Preprocessing prompt textarea
│       │   └── Placeholder hints (clickable CSV column tags)
│       ├── Step 3: Image (NEW)
│       │   ├── Image model select
│       │   ├── Aspect ratio select
│       │   ├── Image prompt template textarea
│       │   └── Placeholder hints
│       ├── Step 4: Video (NEW)
│       │   ├── Video model select
│       │   ├── Duration select
│       │   └── VideoTemplatesList (reuse existing)
│       └── Step 5: Distribution (NEW)
│           ├── Social account selects (per platform)
│           ├── PublishingConfigForm (reuse existing)
│           └── Pause toggle
├── Sticky Save Bar (NEW) ── appears when dirty state detected
└── Run Section (unchanged, below Configure)
    ├── GenerationPanel
    └── GenerationsList
```

### New Components to Create

| Component | File | Description |
|-----------|------|-------------|
| `ConfigureSection` | `ConfigureSection.tsx` | Main wrapper, manages accordion state + dirty tracking |
| `ConfigureSummaryLine` | `ConfigureSection.tsx` | Collapsed summary with step status icons |
| `ConfigureAccordion` | `ConfigureSection.tsx` | Accordion container (only 1 step open) |
| `InputStep` | `InputStep.tsx` | Wraps CsvUpload + VariantsList |
| `PreprocessingStep` | `PreprocessingStep.tsx` | LLM model + preprocessing prompt |
| `ImageStep` | `ImageStep.tsx` | Image model + aspect ratio + image prompt template |
| `VideoStep` | `VideoStep.tsx` | Video model + duration + VideoTemplatesList |
| `DistributionStep` | `DistributionStep.tsx` | Social accounts + PublishingConfigForm + pause toggle |
| `StickySaveBar` | `StickySaveBar.tsx` | Fixed at bottom, visible when dirty |

### Modified Components

| Component | File | Changes |
|-----------|------|---------|
| `PipelineScreen` | `PipelineScreen.tsx` | Add ConfigureSection, remove Variants/Templates sections, keep Run section |
| `TemplateSettingsForm` | `TemplateSettingsForm.tsx` | Remove LLM/Image/Video/Social sections, keep only: name, description, workspace |
| `DashboardScreen` | `DashboardScreen.tsx` | Remove PublishingConfigForm, keep only: PipelineFunnel + calendar/queue view + status |
| `PublishingConfigForm` | `PublishingConfigForm.tsx` | Remove save button (managed by StickySaveBar), expose dirty state + form data |

### Reused Components (No Changes)

- `CsvUpload.tsx` — reuse as-is in InputStep
- `VariantsList.tsx` — reuse as-is in InputStep
- `VideoTemplatesList.tsx` — reuse as-is in VideoStep
- `PublishingConfigForm.tsx` — reuse with props changes (remove internal save button)

## Data Structures

### ConfigureSection State

```typescript
interface ConfigureState {
  // Which accordion step is open (null = collapsed)
  activeStep: 1 | 2 | 3 | 4 | 5 | null

  // Settings data (mirrors TemplateSettings + PublishingConfig)
  settings: {
    // Input (readonly, from backend)
    variantsCount: number
    csvColumns: string[] | null

    // Preprocessing
    llm_model: LLMModel
    preprocessing_prompt: string

    // Image
    image_model: ImageModel
    image_aspect_ratio: AspectRatio
    image_prompt_template: string

    // Video
    video_model: VideoModel
    video_duration: string
    videoTemplatesCount: number

    // Distribution
    social_accounts: SocialAccount[]
    publishing_config: {
      enabled: boolean
      is_paused: boolean
      days: string[]
      preferred_times: string[]
      depth_days: number
    }
  }

  // Dirty tracking (per step)
  dirty: {
    preprocessing: boolean
    image: boolean
    video: boolean
    distribution: boolean
  }

  // Loading states
  loading: boolean
  saving: boolean
  error: string | null
}
```

### Step Status Calculation

Each step has a status for the summary line:

```typescript
type StepStatus = 'complete' | 'incomplete' | 'empty'

function getStepStatus(step: number, state: ConfigureState): StepStatus {
  switch (step) {
    case 1: // Input
      return state.settings.variantsCount > 0 ? 'complete' : 'empty'

    case 2: // Preprocessing
      return state.settings.llm_model && state.settings.preprocessing_prompt
        ? 'complete'
        : 'incomplete'

    case 3: // Image
      return state.settings.image_model && state.settings.image_prompt_template
        ? 'complete'
        : 'incomplete'

    case 4: // Video
      return state.settings.video_model && state.settings.videoTemplatesCount > 0
        ? 'complete'
        : 'incomplete'

    case 5: // Distribution
      return state.settings.social_accounts.length > 0 &&
             state.settings.publishing_config.days.length > 0 &&
             state.settings.publishing_config.preferred_times.length > 0
        ? 'complete'
        : 'empty'

    default:
      return 'incomplete'
  }
}
```

### Summary Line Format

When collapsed, show one-line status:

```
✅ Input: 47 vars · ✅ Preproc: GPT-4o-mini · ✅ Image: flux-pro · 9:16 · ✅ Video: veo3.1 · 2 tmpl · ❌ Distribution: no accounts
```

Icons:
- ✅ = complete
- ⚠️ = incomplete (partial config)
- ❌ = empty (no config)

## API Integration

### Data Loading (on mount)

Load all settings in parallel:

```typescript
async function loadConfigureData(projectId: number): Promise<ConfigureState['settings']> {
  const [
    settingsRes,
    projectRes,
    variantsRes,
    templatesRes,
    workspaceAccountsRes,
    publishingConfigRes,
  ] = await Promise.all([
    templateApi.getSettings(projectId),
    projectsApi.get(projectId),
    templateApi.listVariants(projectId, { limit: 1 }), // just for count
    templateApi.listVideoTemplates(projectId),
    socialAccountsApi.listByWorkspace(project.workspace_id),
    publishingScheduleApi.getConfig(projectId),
  ])

  return {
    variantsCount: variantsRes.data.total,
    csvColumns: settingsRes.data.csv_columns,
    llm_model: settingsRes.data.llm_model,
    preprocessing_prompt: settingsRes.data.preprocessing_prompt,
    image_model: settingsRes.data.image_model,
    image_aspect_ratio: settingsRes.data.image_aspect_ratio,
    image_prompt_template: settingsRes.data.image_prompt_template,
    video_model: settingsRes.data.video_model,
    video_duration: settingsRes.data.video_duration,
    videoTemplatesCount: templatesRes.data.length,
    social_accounts: projectRes.data.social_accounts,
    publishing_config: publishingConfigRes.data,
  }
}
```

### Data Saving (from StickySaveBar)

Save only dirty steps:

```typescript
async function saveConfigureData(
  projectId: number,
  state: ConfigureState
): Promise<void> {
  const promises: Promise<any>[] = []

  // Preprocessing or Image or Video changed → update template settings
  if (state.dirty.preprocessing || state.dirty.image || state.dirty.video) {
    promises.push(
      templateApi.updateSettings(projectId, {
        llm_model: state.settings.llm_model,
        preprocessing_prompt: state.settings.preprocessing_prompt,
        image_model: state.settings.image_model,
        image_aspect_ratio: state.settings.image_aspect_ratio,
        image_prompt_template: state.settings.image_prompt_template,
        video_model: state.settings.video_model,
        video_duration: state.settings.video_duration,
      })
    )
  }

  // Distribution changed → update publishing config
  if (state.dirty.distribution) {
    promises.push(
      publishingScheduleApi.updateConfig(projectId, {
        enabled: state.settings.publishing_config.days.length > 0,
        is_paused: state.settings.publishing_config.is_paused,
        days: state.settings.publishing_config.days,
        preferred_times: state.settings.publishing_config.preferred_times,
        depth_days: state.settings.publishing_config.depth_days,
      })
    )
  }

  await Promise.all(promises)
}
```

### Social Account Binding

Social accounts are bound/unbound via separate API calls (not part of bulk save):

```typescript
async function handleBindAccount(
  projectId: number,
  platform: string,
  accountId: number | null
) {
  const currentBound = state.settings.social_accounts.find(
    acc => acc.platform === platform && acc.is_active
  )

  if (currentBound) {
    await projectsApi.unbindSocialAccount(projectId, currentBound.id)
  }

  if (accountId) {
    const res = await projectsApi.bindSocialAccount(projectId, accountId)
    setState(prev => ({
      ...prev,
      settings: { ...prev.settings, social_accounts: res.data.social_accounts }
    }))
  }
}
```

## Implementation Plan

### Phase 1: Scaffolding (New Components)

**Subtasks:**

1. [ ] **Create `StickySaveBar.tsx`**
   - Props: `isDirty: boolean`, `onSave: () => Promise<void>`, `onDiscard: () => void`
   - Fixed position at bottom (z-index: 40)
   - Show/hide based on `isDirty`
   - Save button with loading spinner
   - Discard button (reset to original state)

2. [ ] **Create `ConfigureSection.tsx`** skeleton
   - State: `activeStep`, `settings`, `dirty`, `loading`, `saving`, `error`
   - Load data on mount (all APIs in parallel)
   - Render collapsed summary line OR expanded accordion
   - Dirty tracking: deep compare initial vs current state
   - Auto-expand logic: if `variantsCount === 0` → open step 1, if `social_accounts.length === 0` → open step 5

3. [ ] **Create `ConfigureSummaryLine.tsx`**
   - Props: `status: StepStatus[]`, `onClick: () => void`
   - Render one-line summary with icons
   - Clickable to expand accordion

4. [ ] **Create `ConfigureAccordion.tsx`**
   - Props: `activeStep`, `onStepChange`, `children: Step[]`
   - Render steps as accordion (only one open)
   - Each step header shows: icon + title + summary
   - Click header to toggle step

### Phase 2: Step Components (Reuse Existing)

**Subtasks:**

5. [ ] **Create `InputStep.tsx`**
   - Props: `projectId`, `isActive`, `onToggle`
   - Summary: `{variantsCount} variants`
   - Content: `<CsvUpload />` + `<VariantsList />`
   - Reuse existing components as-is
   - On CSV upload success → refresh variants count → mark step 1 as complete

6. [ ] **Create `PreprocessingStep.tsx`**
   - Props: `projectId`, `isActive`, `onToggle`, `value: { llm_model, preprocessing_prompt, csvColumns }`, `onChange`
   - Summary: `{llm_model}` (e.g., "GPT-4o-mini")
   - Content:
     - LLM model select (from `LLM_MODELS` constants)
     - Preprocessing prompt textarea (6 rows)
     - Placeholder hints (clickable CSV column tags from `csvColumns`)
   - On change → mark step dirty

7. [ ] **Create `ImageStep.tsx`**
   - Props: `projectId`, `isActive`, `onToggle`, `value: { image_model, image_aspect_ratio, image_prompt_template, csvColumns }`, `onChange`
   - Summary: `{image_model} · {aspect_ratio}` (e.g., "flux-pro · 9:16")
   - Content:
     - Image model select (from `IMAGE_MODELS` constants)
     - Aspect ratio select (from `ASPECT_RATIOS` constants)
     - Image prompt template textarea (6 rows)
     - Placeholder hints (CSV columns + `{preprocessed}`)
   - On change → mark step dirty

8. [ ] **Create `VideoStep.tsx`**
   - Props: `projectId`, `isActive`, `onToggle`, `value: { video_model, video_duration }`, `onChange`
   - Summary: `{video_model} · {templatesCount} templates` (e.g., "veo3.1 · 2 tmpl")
   - Content:
     - Video model select (from `VIDEO_MODELS` constants)
     - Duration select (from `getDurationOptions(video_model)`)
     - `<VideoTemplatesList projectId={projectId} />` (reuse existing)
   - On video model change → auto-adjust duration if invalid
   - On change → mark step dirty

9. [ ] **Create `DistributionStep.tsx`**
   - Props: `projectId`, `isActive`, `onToggle`, `value: { social_accounts, publishing_config, workspaceAccounts, timezone }`, `onChange`
   - Summary:
     - If configured: `YouTube + Instagram · Mon/Wed/Fri 18:00`
     - If not: `❌ no accounts`
   - Content:
     - **Social accounts section:**
       - 3 platform selects (instagram, tiktok, youtube)
       - Each select shows workspace accounts for that platform
       - On change → call `projectsApi.bindSocialAccount` / `unbindSocialAccount` immediately
       - "Connect new account" link → opens `/social-accounts` in new tab
     - **Publishing schedule section:**
       - Reuse `<PublishingConfigForm />` with modified props:
         - Remove internal save button (managed by StickySaveBar)
         - Expose `onChange` callback → mark step dirty
         - Pass `config`, `timezone`, `onChange`
     - **Pause toggle:**
       - Checkbox to toggle `is_paused`
       - On change → mark step dirty

### Phase 3: Integration (Modify Existing)

**Subtasks:**

10. [ ] **Modify `PipelineScreen.tsx`**
    - Remove Phase 3 notice banner
    - Remove Variants section (moved into ConfigureSection → InputStep)
    - Remove Templates section (moved into ConfigureSection → VideoStep)
    - Add `<ConfigureSection projectId={projectId} />` at top
    - Keep Generate section below (GenerationPanel + GenerationsList) — unchanged for now (Phase 3B)

11. [ ] **Modify `TemplateSettingsForm.tsx`**
    - Remove LLM Settings section (lines 290-346)
    - Remove Image Settings section (lines 348-389)
    - Remove Video Settings section (lines 391-436)
    - Remove Social Accounts section (lines 238-288)
    - Remove Available Placeholders section (lines 439-457)
    - Keep only: Project Info (name, description, workspace selector)
    - Rename to "Project Settings" (no longer "template-specific" settings)

12. [ ] **Modify `DashboardScreen.tsx`**
    - Remove PublishingConfigForm inline usage
    - Remove pause toggle inline usage
    - Keep: PipelineFunnel, Calendar/Queue view, status warnings, quick actions
    - Update "Run pipeline" button → navigate to `pipeline` screen with `section=run` (scroll to Run section)
    - Update "No schedule configured" message → link to `pipeline` screen with `section=distribution` (auto-expand distribution step)

13. [ ] **Modify `PublishingConfigForm.tsx`**
    - Remove internal save button (lines 174-196)
    - Add props: `onChange: (data: PublishingConfigUpdate) => void`, `showSaveButton: boolean = true`
    - On form field change → call `onChange` callback (parent tracks dirty state)
    - Keep save button only if `showSaveButton === true` (for backwards compatibility if used elsewhere)

### Phase 4: Testing & Polish

**Subtasks:**

14. [ ] **Manual testing: Full flow**
    - Create new template project
    - Upload CSV → verify auto-expand to Input step
    - Configure Preprocessing → verify dirty state → save → verify saved
    - Configure Image → verify placeholder hints show CSV columns + `{preprocessed}`
    - Configure Video → verify duration options change when model changes
    - Configure Distribution → verify social account binding works → verify publishing schedule saves
    - Verify sticky save bar appears/disappears correctly
    - Verify discard restores original state

15. [ ] **Edge cases**
    - No variants → auto-expand Input step
    - No social accounts → auto-expand Distribution step
    - Change video model → duration auto-adjusts
    - Delete all variants → Input step shows ❌
    - Unbind all social accounts → Distribution step shows ❌

16. [ ] **Build verification**
    - `cd frontend && npm run build` → verify no TypeScript errors
    - Verify no unused imports (TypeScript strict mode fails build)

## Edge Cases

| Case | Handling |
|------|----------|
| **No variants uploaded** | Auto-expand Input step on mount, show ❌ in summary |
| **No social accounts** | Auto-expand Distribution step on mount, show ❌ in summary |
| **User changes video model** | Auto-adjust duration to valid option for new model (use `getDefaultDuration`) |
| **User deletes all variants** | Input step status → ❌, summary line updates |
| **User unbinds all social accounts** | Distribution step status → ❌, summary line updates |
| **Save fails (network error)** | Show error in StickySaveBar, keep dirty state, allow retry |
| **User navigates away with unsaved changes** | No warning (future enhancement: add beforeunload handler) |
| **CSV upload while accordion expanded** | Refresh variants count, update summary line, keep Input step open |
| **Social account binding fails** | Show inline error, revert select to previous value |
| **Publishing config has invalid times** | PublishingConfigForm validation (existing) prevents save |
| **User clicks summary line when already expanded** | Collapse accordion (toggle behavior) |
| **User opens step 2 while step 1 is open** | Close step 1, open step 2 (only one open at a time) |
| **Multiple steps dirty** | Save all dirty steps in parallel (Promise.all) |
| **Workspace change in TemplateSettingsForm** | Reload social accounts for new workspace, update DistributionStep |

## Component Props Reference

### ConfigureSection

```typescript
interface ConfigureSectionProps {
  projectId: number
}
```

### ConfigureSummaryLine

```typescript
interface ConfigureSummaryLineProps {
  statuses: {
    input: { status: StepStatus; summary: string }
    preprocessing: { status: StepStatus; summary: string }
    image: { status: StepStatus; summary: string }
    video: { status: StepStatus; summary: string }
    distribution: { status: StepStatus; summary: string }
  }
  onClick: () => void
}
```

### Step Components (Common Pattern)

```typescript
interface StepProps<T> {
  projectId: number
  isActive: boolean
  onToggle: () => void
  value: T
  onChange: (newValue: T) => void
  // Step-specific props
  csvColumns?: string[]
  workspaceAccounts?: SocialAccount[]
  timezone?: string
}
```

### StickySaveBar

```typescript
interface StickySaveBarProps {
  isDirty: boolean
  onSave: () => Promise<void>
  onDiscard: () => void
}
```

## Acceptance Criteria

### Functional Requirements

- [ ] Configure section appears at top of PipelineScreen
- [ ] Collapsed summary shows status of all 5 steps (✅/⚠️/❌ icons)
- [ ] Click summary → expand accordion
- [ ] Accordion shows only one step open at a time
- [ ] Each step header shows: icon + title + summary
- [ ] Input step: CSV upload + variants list (reused components)
- [ ] Preprocessing step: LLM model + prompt + CSV column hints
- [ ] Image step: model + aspect ratio + prompt + column hints + `{preprocessed}` hint
- [ ] Video step: model + duration + templates list
- [ ] Distribution step: social accounts + publishing schedule + pause toggle
- [ ] Sticky save bar appears when any step is dirty
- [ ] Save button saves all dirty steps in parallel
- [ ] Discard button resets to original state
- [ ] Auto-expand Input step if no variants
- [ ] Auto-expand Distribution step if no social accounts
- [ ] Video model change → duration auto-adjusts
- [ ] Social account binding/unbinding works immediately

### UX Requirements

- [ ] Configure section collapsed by default (unless auto-expand triggered)
- [ ] Summary line readable at a glance (icons + concise text)
- [ ] Accordion animation smooth (CSS transition)
- [ ] Sticky save bar visible while scrolling
- [ ] No layout shift when expanding/collapsing
- [ ] Placeholder hints clickable (copy to clipboard)
- [ ] Social account selects show platform icons
- [ ] Publishing config inline (no modal)

### Technical Requirements

- [ ] Zero backend changes
- [ ] Reuse existing components (CsvUpload, VariantsList, VideoTemplatesList, PublishingConfigForm)
- [ ] TypeScript strict mode passes
- [ ] No unused imports
- [ ] `npm run build` succeeds
- [ ] Dirty tracking accurate (deep comparison)
- [ ] API calls parallel where possible (Promise.all)
- [ ] Error handling (network failures, validation errors)

### Cleanup Requirements

- [ ] TemplateSettingsForm reduced to Project Settings (name, description, workspace)
- [ ] DashboardScreen no longer has inline PublishingConfigForm
- [ ] No duplicate code (DRY principle)
- [ ] No dead code left behind
- [ ] PipelineScreen no longer has Variants/Templates sections

## Dependencies

### Existing Code

- `frontend/src/components/template/CsvUpload.tsx` — reuse as-is
- `frontend/src/components/template/VariantsList.tsx` — reuse as-is
- `frontend/src/components/template/VideoTemplatesList.tsx` — reuse as-is
- `frontend/src/components/template/PublishingConfigForm.tsx` — reuse with props changes
- `frontend/src/constants/models.ts` — model constants
- `frontend/src/services/api.ts` — API client
- `frontend/src/types/index.ts` — TypeScript types

### New Files

- `frontend/src/components/template/ConfigureSection.tsx` — main wrapper + state management
- `frontend/src/components/template/ConfigureSummaryLine.tsx` — collapsed summary
- `frontend/src/components/template/ConfigureAccordion.tsx` — accordion container
- `frontend/src/components/template/InputStep.tsx` — step 1
- `frontend/src/components/template/PreprocessingStep.tsx` — step 2
- `frontend/src/components/template/ImageStep.tsx` — step 3
- `frontend/src/components/template/VideoStep.tsx` — step 4
- `frontend/src/components/template/DistributionStep.tsx` — step 5
- `frontend/src/components/template/StickySaveBar.tsx` — save bar

### External Dependencies

- None (all libraries already in package.json)

## Testing Strategy

### Manual Tests

1. **New project flow:**
   - Create template project
   - Verify Configure collapsed, Input step auto-expanded (no variants)
   - Upload CSV
   - Verify Input step shows ✅, summary updates
   - Configure each step sequentially
   - Verify dirty state tracked correctly
   - Save → verify all settings persisted

2. **Existing project flow:**
   - Open existing template project with all settings configured
   - Verify Configure collapsed, summary shows all ✅
   - Expand → verify all settings loaded correctly
   - Change preprocessing prompt
   - Verify dirty state, save bar appears
   - Save → verify only preprocessing updated (check network tab)

3. **Edge cases:**
   - Delete all variants → verify Input step ❌
   - Unbind all social accounts → verify Distribution step ❌
   - Change video model → verify duration adjusts
   - Network error on save → verify error shown, retry works
   - Navigate to TemplateSettingsForm → verify simplified (no LLM/Image/Video sections)

### Build Verification

```bash
cd frontend && npm run build
```

Must pass without errors.

## Open Questions

- [x] Should Configure be collapsed or expanded by default? → **Collapsed by default, auto-expand if incomplete**
- [x] Should social account binding trigger save bar? → **No, immediate API call (no dirty state)**
- [x] Should we warn on unsaved changes when navigating away? → **Future enhancement (Phase 3B)**
- [x] Should we add keyboard shortcuts (Cmd+S to save)? → **Future enhancement**

## Notes

- This spec focuses on **moving** existing functionality, not **changing** it (except for better UX)
- Reuse existing components wherever possible — **don't rewrite working code**
- Zero backend changes — all APIs already exist and tested
- Phase 3B (next) will redesign the Run section (GenerationPanel + GenerationsList)
- Design principle: **one accordion step open at a time** (reduces cognitive load)
- Summary line uses **concise text + icons** (readable at a glance)
- Sticky save bar **only appears when dirty** (non-intrusive)

## Related Documents

- `docs/PRODUCT_OVERVIEW.md` — product context
- `docs/ARCHITECTURE.md` — system architecture
- `frontend/src/types/index.ts` — TypeScript types
- `frontend/src/constants/models.ts` — model constants
- `frontend/src/services/api.ts` — API client reference
