# UI/UX Consistency Audit

**Date:** 2026-02-06
**Scope:** Discover (T36) + Template (T37) — full frontend audit
**Files audited:** 41 components, ~9,400 lines
**Method:** 5 parallel code audits (Discover UI, Template UI, Shared UI, Routing, State Management)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Codebase Overview](#2-codebase-overview)
3. [Design System Baseline](#3-design-system-baseline)
4. [Discover Workflow Audit](#4-discover-workflow-audit)
5. [Template Workflow Audit](#5-template-workflow-audit)
6. [Routing & Navigation Audit](#6-routing--navigation-audit)
7. [State Management Audit](#7-state-management-audit)
8. [Cross-Cutting Issues](#8-cross-cutting-issues)
9. [Recommendations & Action Plan](#9-recommendations--action-plan)

---

## 1. Executive Summary

| Area | Files | Lines | Score |
|------|-------|-------|-------|
| Discover | 8 components | ~2,486 | 7.2/10 |
| Template | 33 components | ~6,915 | 7.5/10 |
| Shared UI | Layout + utils | ~500 | Baseline |
| Routing | App + Layout | — | 6/10 |
| State management | Hooks + Context | — | 7/10 |

**Overall: 7/10** — mostly consistent with isolated pockets of inconsistency.

**What's good:** Grid layouts, status colors, icons, auth flow, card patterns, polling.
**What needs work:** Button color system, textarea styles, error handling, routing model, empty/loading states.

**Decomposition imbalance:** Discover under-decomposed (8 files, monolithic page), Template over-decomposed (33 files, wrapper-components with 10-33 lines). Target: ~15-20 files per workflow with meaningful responsibility per component.

---

## 2. Codebase Overview

### File Inventory

#### Discover Components
| File | Lines | Purpose |
|------|-------|---------|
| `pages/DiscoverPage.tsx` | 754 | Master orchestrator — all stages, nav, state |
| `components/discover/PromptRefinement.tsx` | 448 | Stage 1: Interactive prompt blocks |
| `components/discover/AudioSelection.tsx` | 517 | Stage 4: SFX/Music/Library tabs |
| `components/discover/ItemGrid.tsx` | 224 | Reusable grid — images/videos with selection |
| `components/discover/ExtractionView.tsx` | 184 | Stage 5: Prompt extraction + template creation |
| `components/discover/RoundView.tsx` | 130 | Round header + item grid wrapper |
| `components/discover/DiscoverProjectForm.tsx` | 130 | Modal form for new project |
| `components/discover/CreateTemplateModal.tsx` | 99 | Modal for Discover → Template conversion |

#### Template Components
| File | Lines | Purpose |
|------|-------|---------|
| `components/template/ConfigureSection.tsx` | 723 | 6-step accordion pipeline config |
| `components/template/ReviewScreen.tsx` | 430 | Moderation queue with filtering + focused view |
| `components/template/BatchProgress.tsx` | 409 | Active/history batch display + progress bars |
| `components/template/ModerationQueue.tsx` | 361 | Alternate moderation UI |
| `components/template/GenerationPanel.tsx` | 275 | Mode selector + run button |
| `components/template/TemplateProjectView.tsx` | 252 | Screen router + URL management |
| `components/template/ReviewActions.tsx` | 176 | Approve/Reject/Redo buttons + inline forms |
| `components/template/ReviewFocusedView.tsx` | 132 | Focused item view (video + metadata) |
| `components/template/DistributionStep.tsx` | 120 | Social accounts + publishing schedule |
| `components/template/InputStep.tsx` | 100+ | CSV upload + variant generation |
| `components/template/ReviewFilmstrip.tsx` | 88 | Thumbnail navigator + keyboard nav |
| `components/template/VideoStep.tsx` | 80 | Model/duration select + templates |
| `components/template/ImageStep.tsx` | 80 | Model/aspect/prompt selects |
| `components/template/PreprocessingStep.tsx` | 76 | LLM model + prompt |
| `components/template/StickySaveBar.tsx` | 58 | Floating save/cancel bar |
| `components/template/GenerateScreen.tsx` | 33 | Compose GenerationPanel + BatchProgress |
| `components/template/DetailsScreen.tsx` | 10 | Wrapper for ConfigureSection |

#### Shared
| File | Lines | Purpose |
|------|-------|---------|
| `components/Layout.tsx` | ~100 | Navbar + content wrapper |
| `components/ProgressBar.tsx` | ~80 | Multi-step progress visualization |
| `components/ProjectCard.tsx` | ~60 | Expandable project card |
| `services/api.ts` | 262 | Axios API client (~30 endpoints) |
| `types/index.ts` | 740 | Full type definitions |
| `utils/video.ts` | ~80 | Media URL helpers |
| `constants/models.ts` | ~60 | Model/aspect ratio options |

---

## 3. Design System Baseline

### Stack
- **Framework:** React 18.2 + TypeScript
- **Styling:** Tailwind CSS 3.4.1 (no component library — all custom)
- **Icons:** Lucide React 0.309.0 (exclusive)
- **HTTP:** Axios 1.6.5
- **Routing:** React Router 6.21.0
- **State:** useState/useCallback/useEffect (no Redux/Zustand active)
- **Build:** Vite

### Color Palette
| Token | Value | Usage |
|-------|-------|-------|
| `primary-600` | `#0284c7` | Primary actions (defined in tailwind config) |
| `primary-500` | `#0ea5e9` | Highlights |
| `green-600` | default | Success, advancement, approve |
| `red-500` | default | Error, reject, destructive |
| `amber-500` | default | Warning, finalist, retry/regenerate |
| `purple-600` | default | Generation actions (Discover), audio selection |
| `blue-600` | default | Generation actions (Template), info |
| `gray-*` | default | Neutral text, borders, backgrounds |

### Established Patterns (consistent, don't touch)
- **Card:** `bg-white rounded-lg border p-6`
- **Form input:** `border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500`
- **Status colors:** green=success, red=error, amber=warning, gray=neutral
- **Loading spinner:** `<Loader2 className="animate-spin" />`
- **Icons:** Lucide only, `h-4 w-4` to `h-6 w-6`
- **Responsive grids:** `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`
- **Accordion:** ChevronDown (open) / ChevronRight (closed)
- **Hover overlay:** `opacity-0 group-hover:opacity-100 transition`

---

## 4. Discover Workflow Audit

### Stage Flow
```
Refine → Images → Videos → Audio → Extraction → Completed
```

### Stage-by-Stage Breakdown

#### Stage 1: Prompt Refinement
- **Component:** `PromptRefinement.tsx`
- **Layout:** Score progress bar + block cards in sequence
- **Block statuses:** confirmed (green), needs_input (yellow), auto_generated (gray), auto_filled (blue)
- **Actions:** Accept, Edit (inline), Re-analyze (confirmation modal), Compile Prompt
- **Final screen:** Prompt editor (textarea) + "Generate Images" button (green)

#### Stage 2: Image Exploration
- **Components:** `RoundView.tsx` → `ItemGrid.tsx`
- **Grid:** `grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5`
- **Item card:** 9:16 aspect, position number, selection badge, finalist badge
- **Hover overlay:** Select (✓), Crown (👑), Reject (✗) buttons
- **Selection rings:** amber=finalist, green=selected, red=rejected
- **Action bar (sticky bottom):**
  - LEFT: Back to Refine
  - RIGHT: Model selector, Item count, Regenerate (amber), Next Round (purple), Advance to Video (green)
- **Feedback:** textarea above button bar

#### Stage 3: Video Exploration
- **Same components** as images with video-specific additions
- **Finalist reference panel:** amber-50 bg, shows image finalist thumbnail
- **Grid:** `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` (larger cards)
- **Action bar:** same pattern, "Select Audio" replaces "Advance to Video"

#### Stage 4: Audio Selection
- **Component:** `AudioSelection.tsx`
- **Layout:** Split — left (video preview, sticky) + right (audio controls)
- **Tabs:** SFX | Music | Library
- **Generate panel:** Auto/Manual prompt toggle, Generate button (purple)
- **Variant grid:** 3-column, active=purple border
- **Hook grid:** 4-column, energy badges (high=red, medium=yellow, low=green)
- **Action bar:**
  - LEFT: Back to Videos
  - RIGHT: Skip Audio, Confirm & Continue (green)

#### Stage 5-6: Extraction → Completed
- **Final Result card:** purple-50 (extraction) or green-50 (completed)
- **Content:** video preview + side-by-side prompts (image, video, audio)
- **Actions:** Save edits, Re-extract, Create Template Project

### Discover Issues Found

| # | Issue | Severity | Details |
|---|-------|----------|---------|
| D1 | "Generate Images" button is green | MEDIUM | Should be purple (generation) not green (advancement) |
| D2 | Textarea padding inconsistent | LOW | `p-2` vs `px-3 py-2` across stages |
| D3 | Textarea focus ring color varies | LOW | blue-500 (Refine) vs purple-500 (Feedback, Audio) |
| D4 | Audio variant padding ≠ hook padding | LOW | p-2.5 vs p-2 |
| D5 | Selection ring scale inconsistent | LOW | amber-400, green-500, red-400 |
| D6 | Progress bar missing extraction stage | LOW | Maps to "completed" |
| D7 | PromptRefinement editor is inline, not modal | LOW | Unlike CreateTemplateModal pattern |
| D8 | Rejected items use opacity-60 on whole card | LOW | Makes content hard to see |
| D9 | Under-decomposed: DiscoverPage.tsx is 754-line monolith | MEDIUM | All state, handlers, rendering for 6 stages in one file. Logic should be extracted into hooks (`useDiscoverPolling`, `useDiscoverSelections`, `useDiscoverGeneration`) while keeping components as-is |

---

## 5. Template Workflow Audit

### Screen Flow
```
Dashboard → Generate → Review → Details (tabs, not routes)
```

### Screen-by-Screen Breakdown

#### Dashboard Screen
- **Component:** `DashboardScreen.tsx`
- **Content:** Pipeline funnel stats
- **Minimal state** — driven by parent props

#### Generate Screen
- **Components:** `GenerationPanel.tsx` + `BatchProgress.tsx`
- **GenerationPanel:** Mode selector (fill_schedule / least_used / specific) + Run button
  - Run button: `bg-blue-600` — blue, not purple or green
  - Mode pills: radio buttons + conditional inputs
- **BatchProgress:** Active batches (progress bars) + History (accordions)
  - Progress bar colors: green (completed), red (failed), blue+pulse (in-progress)
  - History accordion: status icon + batch count + moderation badges + timestamp
  - Failed items: dedicated component with retry button

#### Review Screen
- **Components:** `ReviewScreen.tsx` + `ReviewFocusedView.tsx` + `ReviewActions.tsx` + `ReviewFilmstrip.tsx`
- **Filter tabs:** all | pending | approved | rejected
  - Tab styling: `bg-gray-100 rounded-lg p-1`, active=`bg-white shadow-sm`
- **Focused view:** 2-column (video preview + metadata/actions)
- **Actions:** Approve (green), Reject (red outline → inline form), Redo (blue outline → inline form)
- **Filmstrip:** Horizontal thumbnails with border-color by status
  - Keyboard nav: ArrowLeft/Right

#### Details Screen
- **Component:** `ConfigureSection.tsx` (723 lines)
- **6-step accordion:** Preprocessing → Variants → Image → Video → Music → Distribution
- **Step number badge:** gray pill with number
- **Sticky save bar:** appears when changes unsaved
- **Music step:** 3 mode pills (No Music / Saved Hook / Generate from Prompt)
  - Active pill: `bg-purple-50 border-purple-300 text-purple-700`

### Template Issues Found

| # | Issue | Severity | Details |
|---|-------|----------|---------|
| T1 | Run button is blue-600 | MEDIUM | Discover uses purple for generation |
| T2 | ModerationQueue uses modal, ReviewActions uses inline forms | MEDIUM | Two moderation UIs with different interaction patterns |
| T3 | Some errors shown via `alert()` | MEDIUM | Should be UI alerts, not browser native |
| T4 | Spinner sizes vary (w-5, w-6, h-6) | LOW | No standardized sizes |
| T5 | Empty states inconsistent | LOW | CheckCircle vs text-only vs AlertCircle |
| T6 | Spacing in headers varies | LOW | `mb-4` vs `mb-2` for titles |
| T7 | Audio player width `w-full h-8` | LOW | No responsive handling on mobile |
| T8 | Button border-radius: `rounded` vs `rounded-lg` | LOW | Minor inconsistency |
| T9 | Over-decomposed: 33 files, many are trivial wrappers | MEDIUM | `DetailsScreen.tsx` (10 lines), `GenerateScreen.tsx` (33 lines) add indirection without value. Small step components (76-80 lines each) could be inlined into ConfigureSection. 5 Review sub-components could be 2-3. Target: ~18 meaningful files |

---

## 6. Routing & Navigation Audit

### Route Map
```
/login                               → Login (public)
/register                            → Register (public)
/                                    → Dashboard (protected)
/project/:id/edit                    → Project settings
/project/:projectId/create-video     → Video creation wizard
/video/:id                           → Video detail + workflow
/analytics                           → Analytics
/social-accounts                     → Social accounts config
/workspaces                          → Workspace list
/workspaces/:id                      → Workspace detail
/discover/:id                        → Discover project
(no template route)                  → Template via sidebar + ?screen=
```

### Navigation Patterns

| Aspect | Discover | Template | Remix |
|--------|----------|----------|-------|
| **Routing** | `/discover/:id` | Sidebar + `?screen=` | Sidebar |
| **Back button** | "← Back to Dashboard" | No (tabs only) | "← Back" |
| **Stage nav** | Internal state | URL params `?screen=` | Internal state |
| **Deep link** | Yes (`/discover/123`) | No (need sidebar click) | No |
| **History entries** | No (stages don't push) | No (tabs don't push) | — |

### Auth Flow
- `ProtectedRoute` checks `isAuthenticated` from `AuthContext`
- Token in localStorage, added to Axios headers
- Unauthenticated → redirect to `/login`

### Issues Found

| # | Issue | Severity | Details |
|---|-------|----------|---------|
| R1 | No 404 page | HIGH | Invalid URL → blank page |
| R2 | No Error Boundary | HIGH | Component crash → white screen |
| R3 | Template has no dedicated URL | MEDIUM | Can't share/bookmark template project |
| R4 | URL param naming: `:id` vs `:projectId` | LOW | Inconsistent across routes |
| R5 | Back navigation pattern differs | LOW | Explicit button vs no button vs tabs |
| R6 | No breadcrumbs anywhere | LOW | Nested routes lack context |

---

## 7. State Management Audit

### Architecture
- **Global:** AuthContext only (no Redux/Zustand active)
- **Per-page:** useState + useCallback + useEffect
- **Data fetching:** Manual Axios + useState (no React Query in main flows)
- **Polling:** setInterval with 3000ms in both workflows

### Pattern Comparison

| Aspect | Discover | Template |
|--------|----------|----------|
| **State location** | Monolithic (all in DiscoverPage) | Distributed (per screen) |
| **Props drilling** | Heavy (3+ levels) | Minimal (local state) |
| **Selections** | Local pending → batch submit | Local Sets → immediate submit |
| **Polling trigger** | Any round generating | Any generation in-progress |
| **Polling scope** | Full project object | Only generations list |
| **Error pattern** | `setError()` → UI alert | `setError()` + `alert()` mix |
| **Form state** | Inline inputs in parent | Props-driven child components |
| **URL state** | None | `?screen=` param |

### Issues Found

| # | Issue | Severity | Details |
|---|-------|----------|---------|
| S1 | Error handling inconsistent | MEDIUM | UI alerts vs browser `alert()` |
| S2 | No shared polling hook | LOW | Discover + BatchProgress duplicate logic |
| S3 | No optimistic updates | LOW | Approve/reject waits for API response |
| S4 | Decomposition imbalance | MEDIUM | Discover under-decomposed (monolith 754 lines), Template over-decomposed (33 files, trivial wrappers). See D9, T9 |

---

## 8. Cross-Cutting Issues

### HIGH Priority

| # | Issue | Impact | Effort |
|---|-------|--------|--------|
| **C1** | No 404 page or Error Boundary | User sees blank on bad URL or crash | Medium |
| **C2** | Button color system is chaotic | Confusing UX — same action, different colors | Low |
| **C3** | Error handling: `alert()` vs UI alerts | Jarring UX, no dismiss/retry | Medium |

### MEDIUM Priority

| # | Issue | Impact | Effort |
|---|-------|--------|--------|
| **C4** | Textarea styles vary (padding, border, focus ring) | Visual inconsistency | Low |
| **C5** | Modal vs inline form pattern unclear | UX confusion in moderation | Medium |
| **C6** | Template has no direct URL | Can't share/bookmark | High |
| **C7** | Loading spinner sizes not standardized | Minor visual noise | Low |
| **C8** | Empty states have different patterns | Inconsistent feel | Low |
| **C9** | Decomposition imbalance | Maintenance cost, cognitive overhead | High |

Discover (8 files) — under-decomposed. DiscoverPage.tsx at 754 lines is a monolith holding all state, handlers, and rendering for 6 stages. Need to extract hooks, not components.

Template (33 files) — over-decomposed. Trivial wrappers (`DetailsScreen` 10 lines, `GenerateScreen` 33 lines), micro-components (`PreprocessingStep` 76 lines = one select + textarea). Adds navigation overhead for developers without proportional benefit. Need to inline wrappers and merge small pieces.

### LOW Priority

| # | Issue | Impact | Effort |
|---|-------|--------|--------|
| **C10** | URL param naming (`:id` vs `:projectId`) | Developer confusion | Low |
| **C11** | Discover progress bar skips extraction | Minor UX gap | Low |
| **C12** | Audio variant/hook card padding differs | Subtle visual inconsistency | Low |
| **C13** | Selection ring colors not on same scale | Subtle | Low |
| **C14** | Back navigation pattern inconsistent | Minor UX | Low |

---

## 9. Recommendations & Action Plan

### Phase 1: Quick Wins (Low effort, High/Medium impact)

#### 1.1 Button Color System
**Define and apply consistently:**

| Action Type | Color | Usage |
|-------------|-------|-------|
| **Generate / Run** | `bg-purple-600` | Start generation, next round, run batch |
| **Advance / Confirm** | `bg-green-600` | Advance stage, confirm, approve |
| **Destructive / Redo** | `bg-amber-50 border-amber-200` | Regenerate, retry, redo |
| **Cancel / Back** | `border-gray-200 text-gray-600` | Back, skip, cancel, discard |
| **Reject / Delete** | `bg-red-600` or `border-red-200` | Reject, delete |

**Files to change:**
- `DiscoverPage.tsx` — "Generate Images" green → purple
- `GenerationPanel.tsx` — Run button blue → purple
- Verify all other buttons match

#### 1.2 Textarea Standardization
**Standard:** `px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500`

**Files to change:**
- `PromptRefinement.tsx` — `p-2` → `px-3 py-2`, blue → purple focus
- `AudioSelection.tsx` — border gray-200 → gray-300
- All textareas across project

#### 1.3 Spinner Size Standardization
| Context | Size | Usage |
|---------|------|-------|
| Page load | `h-8 w-8` | Full page loading |
| Section load | `h-6 w-6` | Panel/section loading |
| Inline/button | `h-4 w-4` | Inside buttons, next to text |

#### 1.4 Empty State Standardization
**Pattern:** Icon + heading + subtext
```tsx
<div className="text-center py-12">
  <Icon className="h-8 w-8 text-gray-300 mx-auto mb-3" />
  <p className="text-sm font-medium text-gray-500">Heading</p>
  <p className="text-xs text-gray-400 mt-1">Subtext with action hint</p>
</div>
```

### Phase 2: Medium Effort (Medium impact)

#### 2.1 Error Handling Unification
- Replace all `alert()` calls with UI alert component
- Create shared `ErrorAlert` component: red-50 bg, AlertCircle icon, dismiss button, optional retry
- Apply in: `ReviewScreen.tsx`, `GenerationPanel.tsx`, `ConfigureSection.tsx`

#### 2.2 404 Page + Error Boundary
- Add catch-all route: `<Route path="*" element={<NotFoundPage />} />`
- Add React Error Boundary wrapping `<Layout>` children
- Consistent "something went wrong" UI with retry/home button

#### 2.3 Modal vs Inline Decision
**Rule:** Use inline forms for quick actions (approve/reject with reason). Use modals for multi-step or destructive flows (create project, delete, re-analyze).
- Audit `ModerationQueue.tsx` modal — consider converting to inline (matches ReviewActions pattern)
- Or vice versa — pick one and apply consistently

### Phase 3: Larger Changes (Higher effort)

#### 3.1 Decomposition Rebalance

Both workflows need to converge toward a healthy middle ground (~15-20 files each with meaningful responsibility).

**Discover — extract logic, keep components:**
- DiscoverPage.tsx (754 lines) → ~400 line orchestrator + hooks
- Extract: `useDiscoverPolling()`, `useDiscoverSelections()`, `useDiscoverGeneration()`
- Components stay as-is (8 components is fine — the problem is the monolithic page, not missing components)

**Template — inline trivial wrappers, merge small components:**

| Current | Action | Rationale |
|---------|--------|-----------|
| `DetailsScreen.tsx` (10 lines) | Inline into TemplateProjectView | Pure wrapper, adds indirection |
| `GenerateScreen.tsx` (33 lines) | Inline into TemplateProjectView | Just `<Panel /> + <BatchProgress />` |
| `PreprocessingStep.tsx` (76 lines) | Inline into ConfigureSection | Select + textarea, not worth a file |
| `ImageStep.tsx` (80 lines) | Inline into ConfigureSection | Two selects |
| `VideoStep.tsx` (80 lines) | Inline into ConfigureSection | Two selects + list |
| `ReviewMetadata.tsx` | Merge into ReviewFocusedView | Part of the same screen |
| `ReviewFilmstrip.tsx` (88 lines) | Keep or merge into ReviewScreen | Borderline — has keyboard nav logic |

**Result:** Template goes from 33 → ~18-20 files. Each file has clear, non-trivial responsibility.

#### 3.2 Template Dedicated URL (Optional)
- Add `/template/:id` route
- Or `/project/:id` universal route that detects project type
- Would enable deep linking and sharing

#### 3.3 Shared Polling Hook
```typescript
function usePolling(fetchFn: () => Promise<void>, shouldPoll: boolean, interval = 3000) {
  useEffect(() => {
    if (!shouldPoll) return
    const id = setInterval(fetchFn, interval)
    return () => clearInterval(id)
  }, [shouldPoll, fetchFn, interval])
}
```
- Apply in `DiscoverPage.tsx` and `BatchProgress.tsx`

---

## Appendix: Consistency Scorecard

| Aspect | Discover | Template | Cross |
|--------|----------|----------|-------|
| Button colors | 6/10 | 7/10 | 5/10 |
| Spacing & padding | 7/10 | 8/10 | 7/10 |
| Responsive grids | 9/10 | 8/10 | 9/10 |
| Color semantics | 6/10 | 7/10 | 6/10 |
| Loading states | 8/10 | 7/10 | 7/10 |
| Error states | 9/10 | 6/10 | 6/10 |
| Modal/dialog | 7/10 | 6/10 | 6/10 |
| Empty states | 7/10 | 7/10 | 6/10 |
| Navigation | 8/10 | 7/10 | 6/10 |
| State management | 7/10 | 8/10 | 7/10 |
| Component architecture | 5/10 | 5/10 | 5/10 |
| **Average** | **7.2** | **6.9** | **6.4** |
