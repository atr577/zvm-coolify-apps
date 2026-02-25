# UX/Usability Audit

**Date:** 2026-02-06
**Scope:** Discover, Template, Dashboard, Navigation — user perspective
**Method:** Code-based flow analysis (4 parallel audits)
**Companion:** `UI_UX_AUDIT_2026-02-06.md` (visual/code consistency)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Critical Issues](#2-critical-issues)
3. [Discover Workflow UX](#3-discover-workflow-ux)
4. [Template Workflow UX](#4-template-workflow-ux)
5. [Dashboard & Navigation UX](#5-dashboard--navigation-ux)
6. [URL State & Deep Linking](#6-url-state--deep-linking)
7. [Full Issue Registry](#7-full-issue-registry)
8. [Recommendations](#8-recommendations)

---

## 1. Executive Summary

### Severity Distribution

| Severity | Count | Where |
|----------|-------|-------|
| CRITICAL | 15 | Audio stage (3), Discover flow (4), Template config (3), Dashboard (5) |
| MAJOR | 29 | Across all workflows + URL state |
| MINOR | 17 | Across all workflows |

### Biggest Pain Points

| # | Problem | Impact |
|---|---------|--------|
| 1 | **Audio stage is overwhelming** | Users face 3 tabs, mode toggles, variant cards, hook grids, unexplained terminology — all at once |
| 2 | **No onboarding anywhere** | New user sees 6-step config or 9 prompt blocks with zero guidance |
| 3 | **No validation before generation** | Users can save incomplete config, then get cryptic generation failures |
| 4 | **No undo for approve/reject** | Wrong decision = stuck with bad schedule slot |
| 5 | **No bulk moderation** | Reviewing 50 items = 50 individual clicks |
| 6 | **Three navigation models** | Discover = full page, Template = sidebar tabs, Remix = sidebar grid — confusing mental model |
| 7 | **Discover→Template bridge is unclear** | Users don't see connection between completed Discover and created Template |
| 8 | **URL state almost empty** | Refresh loses model selection, review position, audio tab, config step. Can't share links, can't use back button in Discover |

### Stage Health Map

| Stage | Task Clarity | Cognitive Load | Feedback | Error Recovery | Dead Ends |
|-------|-------------|----------------|----------|----------------|-----------|
| **Discover: Refine** | Good | PROBLEM | Mixed | Good | CRITICAL |
| **Discover: Images** | Good | Good | Excellent | Good | CRITICAL |
| **Discover: Videos** | Good | Good | Excellent | Good | CRITICAL |
| **Discover: Audio** | PROBLEM | CRITICAL | Good | Mixed | PROBLEM |
| **Discover: Extraction** | Good | Good | Good | Good | OK |
| **Template: Configure** | POOR | PROBLEM | OK | PROBLEM | CRITICAL |
| **Template: Generate** | Good | Good | OK | OK | OK |
| **Template: Review** | Good | Good | PROBLEM | CRITICAL | OK |
| **Dashboard** | POOR | OK | PROBLEM | N/A | CRITICAL |

---

## 2. Critical Issues

### CRIT-1: Audio Stage Cognitive Overload
**Where:** Discover → Audio Selection
**Problem:** Too many interactive elements competing for attention:
- Video preview (sticky left)
- 3 tabs (SFX, Music, Library) — not explained
- Auto/Manual mode toggle — not explained
- Generate button
- 3 variant cards (small, hard to distinguish)
- Hook selection grid (4 columns of tiny buttons)
- Energy badges (red/yellow/green) — not explained
- 3 action buttons at bottom (Back, Skip, Confirm)

**User doesn't know:** Where to click first. What SFX vs Music means. What a "hook" is. Why they need to select one.

### CRIT-2: No Onboarding / First-Time Guidance
**Where:** Everywhere
**Problem:**
- New Discover user sees 9 prompt blocks with no explanation of purpose or order
- New Template user sees 6-step accordion with no intro or workflow explanation
- New Dashboard user sees "Select a project" with no projects to select
- Project types (Discover/Template/Remix) not explained in context

### CRIT-3: Can Advance Without Selecting Finalist
**Where:** Discover → Images, Videos
**Problem:** User can click "Advance to Video" or "Select Audio" without having selected a finalist. No validation, no warning. Leads to broken downstream state or confusion.

### CRIT-4: Score < 80% Blocks Compilation Without Guidance
**Where:** Discover → Refine
**Problem:** "Compile Prompt" disabled at <80% score. User stuck with no indication of which blocks to improve. No "these blocks need work" highlight.

### CRIT-5: No Undo for Approve/Reject
**Where:** Template → Review
**Problem:** Once approved, video locked into schedule slot. Once rejected, goes to archive. No undo, no "un-approve", no 30-second grace period.

### CRIT-6: No Bulk Moderation
**Where:** Template → Review
**Problem:** Reviewing 50 items requires 50 individual approve clicks. No "select all → approve", no keyboard shortcut for batch operations.

### CRIT-7: No Validation Before Save/Generate
**Where:** Template → Configure
**Problem:** User can Save with incomplete steps (no variants, no templates). Generation fails later with cryptic errors. No blocking validation: "Complete steps 2 and 4 before generating."

### CRIT-8: Three Different Navigation Models
**Where:** Dashboard
**Problem:**
- Discover: click sidebar → navigates to `/discover/:id` (full page, leaves Dashboard)
- Template: click sidebar → stays on Dashboard, shows tabs (Dashboard/Generate/Review/Details)
- Remix: click sidebar → stays on Dashboard, shows video grid

User has no consistent mental model. Clicking sidebar items does different things depending on project type.

### CRIT-9: Discover→Template Bridge is Broken
**Where:** Discover Completed → Template Created
**Problem:** After Discover completion, "Create Template" navigates to `/?project=${id}`. User lands on Dashboard with new Template in sidebar. No explanation that this Template is derived from Discover. User thinks they have two unrelated projects.

### CRIT-10: Empty Dashboard for New Users
**Where:** Dashboard
**Problem:** New user after login sees "Select a project and create first video" — circular (no projects exist). No welcome, no workflow explanation, no clear CTA.

### CRIT-11: Audio Generation Limit Hidden
**Where:** Discover → Audio
**Problem:** Max 3 SFX + 3 Music variants. User doesn't see this limit until Generate button becomes disabled. No "3/3 generated" counter.

### CRIT-12: All Audio Generations Fail = Dead End
**Where:** Discover → Audio
**Problem:** If all 3 variants fail, no retry button visible. "Skip Audio" exists but isn't highlighted as the way forward. User stuck.

### CRIT-13: Sidebar Not Responsive
**Where:** Dashboard
**Problem:** Fixed `w-64` sidebar. On 13" laptop (1280px), leaves only ~700px for content. No mobile collapse, no hamburger menu.

### CRIT-14: Music Config Unclear Consequences
**Where:** Template → Configure → Step 5
**Problem:** Three options (No Music / Saved Hook / Generate from Prompt). User doesn't understand:
- What "Saved Hook" means
- That "No Music" means ALL videos will be silent
- That "Generate from Prompt" creates a new track PER BATCH

---

## 3. Discover Workflow UX

### Stage 1: Prompt Refinement

**What works:**
- Score progress bar with color coding (red/yellow/green)
- Block status icons help prioritize
- Re-analyze with confirmation dialog

**Problems:**

| # | Issue | Severity | Details |
|---|-------|----------|---------|
| D-UX1 | 9 blocks at once is overwhelming | MAJOR | No grouping, no progressive disclosure. User sees all 9 blocks simultaneously |
| D-UX2 | Block interaction has 4+ patterns | MAJOR | confirmed/auto-filled/needs_input/editing each have different UI. Hard to learn |
| D-UX3 | Score <80% blocks with no guidance | CRITICAL | Disabled button, no hint which blocks to improve |
| D-UX4 | No progress indicator | MINOR | No "5/9 blocks confirmed" counter |
| D-UX5 | No explanation of block purpose | MINOR | Why "camera" matters? Why "lighting"? |
| D-UX6 | No draft save | MINOR | Leaving page loses all refinement progress |

**Recommendations:**
- Group blocks into categories (Scene, Technical, Style) with collapsible sections
- When score <80%, highlight blocks needing work: "Improve Action and Moment blocks to reach 80%"
- Add "X/Y blocks confirmed" counter at top
- Unify block interaction: all blocks show value + Accept/Edit, regardless of status

### Stage 2-3: Images & Videos

**What works:**
- Clean grid layout with responsive columns
- Selection state (green/red/gold rings) is immediately clear
- Hover-only action buttons reduce clutter
- Feedback textarea is optional and contextual
- Round collapse keeps history manageable

**Problems:**

| # | Issue | Severity | Details |
|---|-------|----------|---------|
| D-UX7 | Can advance without finalist | CRITICAL | No validation. User proceeds with broken state |
| D-UX8 | No comparison view | MAJOR | Can't view two images/videos side by side |
| D-UX9 | No zoom/enlarge | MAJOR | Small thumbnails, no lightbox for closer inspection |
| D-UX10 | Prompt only on hover | MAJOR | Not obvious prompts exist. Click to toggle, but no affordance |
| D-UX11 | All items fail = no clear path | MAJOR | "Retry failed items" exists but not highlighted |
| D-UX12 | Changing finalist not obvious | MAJOR | Must click crown on new item. No "change finalist" button |
| D-UX13 | "Back to Refine" is scary | MINOR | Warning: "All rounds will be deleted" — users afraid to go back |
| D-UX14 | No sort/filter | MINOR | Can't filter by selected/rejected or sort by quality |
| D-UX15 | Videos autoplay muted | MINOR | User might think video has no sound (it doesn't yet) |

**Recommendations:**
- Add validation: "Select a finalist to continue" with disabled advance button
- Add lightbox modal: click image → full-screen preview with prompt, select/reject/crown buttons
- Add "Side-by-side compare" mode (select 2 items → show side by side)
- When all items fail: show highlighted "Retry" CTA in center of grid area
- Add finalist change: show current finalist with "Change" button, or allow re-crowning

### Stage 4: Audio Selection

**The weakest stage. Completely different UX pattern from Images/Videos.**

| # | Issue | Severity | Details |
|---|-------|----------|---------|
| D-UX16 | Tabs (SFX/Music/Library) unexplained | CRITICAL | User doesn't know what each is for |
| D-UX17 | Cognitive overload | CRITICAL | Too many elements: tabs + mode + variants + hooks + buttons |
| D-UX18 | "Hook" not explained | CRITICAL | Technical term, no tooltip or intro |
| D-UX19 | Generation limit hidden | CRITICAL | Max 3 variants, no counter, button just disables |
| D-UX20 | All fail = dead end | CRITICAL | No retry, "Skip Audio" not highlighted |
| D-UX21 | Can't compare audio variants | MAJOR | Must play each sequentially. No A/B comparison |
| D-UX22 | Two-step selection not obvious | MAJOR | Select variant THEN select hook — not explained |
| D-UX23 | Three bottom buttons confusing | MAJOR | Back / Skip / Confirm — which is primary? |
| D-UX24 | No audio preview before commit | MAJOR | Play button requires explicit click, no auto-preview |
| D-UX25 | Variant cards too small | MINOR | 3 columns, hard to distinguish |
| D-UX26 | Energy badges unexplained | MINOR | Red/yellow/green means high/medium/low — but why? |

**Recommendations:**
- Simplify: show ONE mode by default (e.g., Music). Add "Try SFX" / "Use Library" as secondary buttons
- Add intro text: "Pick background audio for your video. Generate up to 3 variants, then select the best section (hook)."
- Add tooltip on "Hook": "A hook is a catchy 5-10 second section. The AI detected N hooks in this track."
- Show "1/3 generated" counter next to Generate button
- When all fail: show centered message "Audio generation failed. [Try Again] or [Skip Audio →]"
- Merge Back/Skip into one secondary action. Make "Confirm & Continue" the only primary button

### Stage 5-6: Extraction & Completed

**What works:**
- Auto-extraction on page load
- Clear result display with video + prompts
- Green success state is celebratory

**Problems:**

| # | Issue | Severity | Details |
|---|-------|----------|---------|
| D-UX27 | Extraction UI inconsistent with rest | MINOR | Different layout, no sticky action bar, inline buttons |
| D-UX28 | Slot notation `{brace}` unexplained | MINOR | Users don't understand template variables |
| D-UX29 | No guidance after completion | MINOR | "What do I do with this template?" not answered |

### Cross-Stage Issues

| # | Issue | Severity | Details |
|---|-------|----------|---------|
| D-UX30 | Progress bar missing Audio + Extraction | MAJOR | Shows 5 stages, but Audio maps to nothing and Extraction maps to Completed |
| D-UX31 | No time estimates during generation | MAJOR | User doesn't know: 10 seconds or 10 minutes? |
| D-UX32 | Different back/forward patterns per stage | MAJOR | "Back to Refine" / "Back to Videos" / none — inconsistent |
| D-UX33 | Can't jump to previous stage easily | MINOR | Must use back buttons sequentially, no progress bar click |
| D-UX34 | No stage transition celebration | MINOR | Advancing stage is anticlimactic — no toast/animation |

---

## 4. Template Workflow UX

### Configure Section

| # | Issue | Severity | Details |
|---|-------|----------|---------|
| T-UX1 | No intro explaining the 6-step pipeline | CRITICAL | User sees steps but doesn't know WHY each exists |
| T-UX2 | Can save incomplete config | CRITICAL | No validation. Generation fails later with cryptic errors |
| T-UX3 | Step dependencies not shown | MAJOR | Step 4 requires Step 3, but user can open any step |
| T-UX4 | Collapsed step summaries insufficient | MAJOR | "gpt-4" tells user nothing. "5 vars" — is that enough? |
| T-UX5 | Music modes unclear | CRITICAL | "Saved Hook" / "Generate from Prompt" — consequences not explained |
| T-UX6 | Distribution step: account binding is instant | MAJOR | Toggles save immediately unlike rest of form (dirty state mismatch) |
| T-UX7 | No "recommended settings" or defaults | MAJOR | User must fill every field manually |
| T-UX8 | No quick-start for "just want to try" | MAJOR | No minimal viable config path |
| T-UX9 | Technical step names | MINOR | "Preprocessing" means nothing to most users |
| T-UX10 | No help tooltips on fields | MINOR | What is "preprocessing_prompt"? What is "variant_generation_prompt"? |

**Recommendations:**
- Add intro banner: "Configure your video pipeline. Complete all steps, then generate."
- Add step descriptions in collapsed headers:
  - "Preprocessing — AI cleans and enriches your CSV data"
  - "Variants — Your input data rows"
  - "Image — How images are generated from data"
  - "Video — Motion and transitions applied to images"
  - "Music — Background audio (optional)"
  - "Distribution — Where and when videos publish"
- Block Save/Generate if required steps incomplete. Show: "Complete steps 2 and 4 to enable generation"
- Add "Use Recommended" button that auto-fills sensible defaults

### Generation

| # | Issue | Severity | Details |
|---|-------|----------|---------|
| T-UX11 | Mode names unclear | MAJOR | "Fill schedule" / "Least used, top N" / "Specific variants" — jargon |
| T-UX12 | No time estimate | MAJOR | "Run — 10 videos" gives no ETA |
| T-UX13 | No batch error summary | MAJOR | Failures hidden in collapsed accordion |
| T-UX14 | No bulk retry for failed items | MAJOR | Must retry each individually |

**Recommendations:**
- Rename modes with descriptions:
  - "Fill schedule (recommended)" — "Generate enough videos to fill your publishing calendar"
  - "Top variants" — "Generate from your least-used data to keep variety"
  - "Pick specific" — "Choose exactly which data rows to use"
- After clicking Run: "Generating 10 videos... ~2-3 min each. ETA: 30 min"
- After batch completes with failures: sticky bar "8 generated, 2 failed [Show Errors]"

### Review / Moderation

| # | Issue | Severity | Details |
|---|-------|----------|---------|
| T-UX15 | No undo for approve/reject | CRITICAL | Locked decision, no grace period |
| T-UX16 | No bulk operations | CRITICAL | 50 items = 50 clicks |
| T-UX17 | Badge counts don't update in real-time | MAJOR | "Review: 5" stays after approving 3 |
| T-UX18 | Filmstrip shows items outside current filter | MAJOR | Click filtered-out thumbnail → nothing happens |
| T-UX19 | No preset rejection reasons | MAJOR | Free-form typing each time ("bad lighting", "wrong pose") |
| T-UX20 | Metadata errors block approval | MAJOR | User doesn't understand why approve fails |
| T-UX21 | Schedule slot not shown on approve | MAJOR | User doesn't know WHEN video will publish |
| T-UX22 | No batch redo | MAJOR | Can't regenerate top 5 rejected at once |
| T-UX23 | "All caught up!" is misleading | MINOR | After filtering to "approved", shows "All caught up!" — confusing |

**Recommendations:**
- Add undo toast: "Approved. [Undo — 30s]"
- Add "Select All" checkbox → "Approve Selected (5)" button
- Add keyboard shortcuts: Enter=approve, R=reject, Space=next
- Filmstrip should respect current filter
- Show schedule slot: "Approve → publishes Thu 14:00 (Slot 3 of 15)"
- Add preset rejection reasons as chips: "Bad quality" / "Wrong style" / "Off-brand" / Custom

---

## 5. Dashboard & Navigation UX

### First-Time Experience

| # | Issue | Severity | Details |
|---|-------|----------|---------|
| N-UX1 | Empty state is circular | CRITICAL | "Select a project" when no projects exist |
| N-UX2 | No workflow explanation | CRITICAL | User doesn't know Discover vs Template vs Remix |
| N-UX3 | No onboarding flow | MAJOR | No tutorial, no tooltips, no "Getting Started" |

**Recommendations:**
- Empty state should show:
  ```
  Welcome to REGGY!

  Create your first project:

  [Discover] — Full creative exploration (concept → template)
  [Template] — Batch generation from CSV data
  [Remix] — Quick video generation from templates
  ```

### Navigation & Mental Model

| # | Issue | Severity | Details |
|---|-------|----------|---------|
| N-UX4 | Three navigation models | CRITICAL | Discover=page, Template=tabs, Remix=grid |
| N-UX5 | Discover→Template bridge broken | CRITICAL | No visible connection between derived projects |
| N-UX6 | Clicking sidebar does different things | MAJOR | Discover navigates away, Template/Remix stays |
| N-UX7 | No breadcrumbs | MAJOR | User gets lost in nested views |
| N-UX8 | No active nav indicator | MAJOR | Navbar doesn't show current page |
| N-UX9 | No "What's generating" global view | MAJOR | Must click into each project to see status |
| N-UX10 | Moderation queue hidden | MAJOR | No dashboard-level badge for "5 items need review" |
| N-UX11 | No search/filter for projects | MINOR | 20+ projects = scrolling |
| N-UX12 | No recent projects sorting | MINOR | Projects in creation order, not by activity |

**Recommendations:**
- Unify sidebar: All projects with type badges (Discover/Template/Remix)
- Add breadcrumbs: "Dashboard > Project Name > Current View"
- Add active state to navbar links
- Add global status widget: "3 generating, 5 need review, 2 failed"

### Responsive

| # | Issue | Severity | Details |
|---|-------|----------|---------|
| N-UX13 | Sidebar fixed width, no collapse | CRITICAL | Unusable on 13" laptops |
| N-UX14 | Modal forms overflow on small screens | MAJOR | Scroll inside form even with 1 field |
| N-UX15 | Navbar wraps on mobile | MAJOR | 6+ items don't fit |

---

## 6. URL State & Deep Linking

### Current State: ~5% of UI state lives in URL

**What IS in URL today (works):**

| Param | Scope | Example |
|-------|-------|---------|
| Route `:id` | Discover, Video, Project | `/discover/123` |
| `?project=` | Dashboard sidebar | `/?project=5` |
| `?filter=` | Dashboard video list | `/?filter=in_progress` |
| `?screen=` | Template screens | `/?project=5&screen=review` |

**Everything else is lost on refresh.**

### What is NOT in URL (lost on refresh/share)

#### Discover — HIGH impact

| State | Stored in | On refresh | Shareable? |
|-------|-----------|------------|------------|
| Selected image model | `useState` | Resets to first model | No |
| Selected video model | `useState` | Resets to first model | No |
| Item count (1-7) | `useState` | Resets to 4 | No |
| Feedback textarea | `useState` | Cleared | No |
| Image finalist ID | `useState` | Cleared (visual crown lost) | No |
| Video finalist ID | `useState` | Cleared | No |
| Collapsed rounds | `useState(Set)` | All expand | No |
| Pending selections | `useState` | Cleared (unsubmitted choices lost) | No |

#### Template Review — HIGH impact

| State | Stored in | On refresh | Shareable? |
|-------|-----------|------------|------------|
| Current filter (all/pending/approved/rejected) | `useState` | Resets to "pending" | No |
| Current item index (e.g. item #47) | `useState` | Resets to #0 | No |
| Rejection archive open/closed | `useState` | Closed | No |

#### Audio Selection — MEDIUM impact

| State | Stored in | On refresh | Shareable? |
|-------|-----------|------------|------------|
| Active tab (sfx/music/library) | `useState` | Resets to "sfx" | No |
| Prompt mode (auto/manual) | `useState` | Resets to "auto" | No |
| Manual prompt text | `useState` | Cleared | No |
| Selected variant ID | `useState` | Auto-selects first | No |
| Selected hook | `useState` | Cleared | No |

#### Configure — MEDIUM impact

| State | Stored in | On refresh | Shareable? |
|-------|-----------|------------|------------|
| Active step (1-6) | `useState` | All collapse (auto-open logic partial) | No |

### Browser History Behavior

| Action | Creates history entry? | Back button works? |
|--------|----------------------|-------------------|
| Discover: advance stage (Images→Videos) | **No** | Back exits Discover entirely |
| Discover: generate round | **No** | — |
| Template: switch screen tab | **Yes** | Back returns to previous tab |
| Template: change review filter | **No** | — |
| Dashboard: change filter | **Yes** | Back returns to previous filter |
| Dashboard: select project | **Yes** | Back deselects project |

**Critical gap:** Discover stage transitions don't create history entries. User at audio stage presses Back → leaves Discover completely instead of returning to videos.

### Deep Linking Capability

| Target | Possible? | URL needed |
|--------|-----------|-----------|
| Discover project (current stage) | Partial | `/discover/123` — lands at whatever stage backend says |
| Discover at specific stage | **No** | Would need `?stage=videos` |
| Discover with specific model | **No** | Would need `?imageModel=flux-pro` |
| Template on Review screen | **Yes** | `/?project=5&screen=review` |
| Review at specific item | **No** | Would need `&itemIndex=47` |
| Review with specific filter | **No** | Would need `&reviewFilter=approved` |
| Configure with step open | **No** | Would need `&step=4` |
| Audio on specific tab | **No** | Would need `?audioTab=library` |
| Specific generation/batch | **No** | Would need `&generationId=999` |

### User Scenarios Broken by Missing URL State

**Scenario 1: Discover session resume**
User works 30 min on Discover, selects Flux Pro model + 6 variants, writes feedback. Takes break, refreshes → model resets, count resets to 4, feedback gone. Must re-configure.

**Scenario 2: Moderation handoff**
Reviewer A at item #47 filtered by "approved". Sends URL to Reviewer B. B opens URL → sees "pending" filter at item #0. Must manually find their place.

**Scenario 3: Discover back button**
User at audio stage, presses browser Back → exits to Dashboard instead of returning to video stage. No way to navigate backwards within Discover workflow.

### Issues

| # | Issue | Severity | Details |
|---|-------|----------|---------|
| URL-1 | Discover stage not in URL | CRITICAL | Can't bookmark, share, or use back button within workflow |
| URL-2 | Review filter/index not in URL | MAJOR | Can't share review state, can't resume position |
| URL-3 | Model/count selections not in URL | MAJOR | Lost on refresh during active Discover session |
| URL-4 | Audio tab/variant/hook not in URL | MAJOR | Lost on refresh during audio selection |
| URL-5 | Discover stage transitions don't create history | MAJOR | Back button exits workflow instead of going to previous stage |
| URL-6 | Configure active step not in URL | MINOR | Lost on refresh, but auto-open logic partially compensates |
| URL-7 | Finalist selection not in URL | MINOR | Visual state lost but backend stores finalist |

### Recommended URL Params

```
Discover:
  /discover/:id
    ?imageModel=<model-id>
    ?videoModel=<model-id>
    ?itemCount=<1-7>
    (stage derived from backend, not URL — correct approach)

Review:
  /?project=<id>&screen=review
    &reviewFilter=all|pending|approved|rejected
    &itemIndex=<number>

Audio:
  /discover/:id  (when stage=audio)
    ?audioTab=sfx|music|library
    ?variantId=<id>

Configure:
  /?project=<id>&screen=details
    &step=<1-6>
```

**Note:** Not everything needs to be in URL. Transient state (feedback text, manual prompt, playing audio) is fine as component state. Focus on **navigational state** that the user expects to persist across refresh and sharing.

---

## 7. Full Issue Registry

### All Issues Sorted by Severity

#### CRITICAL (14)

| ID | Area | Problem |
|----|------|---------|
| CRIT-1 | Discover Audio | Cognitive overload — too many elements, no explanation |
| CRIT-2 | All | No onboarding or first-time guidance anywhere |
| CRIT-3 | Discover Img/Vid | Can advance without selecting finalist |
| CRIT-4 | Discover Refine | Score <80% blocks with no guidance on what to fix |
| CRIT-5 | Template Review | No undo for approve/reject decisions |
| CRIT-6 | Template Review | No bulk moderation (50 items = 50 clicks) |
| CRIT-7 | Template Config | Can save incomplete config, generation fails later |
| CRIT-8 | Dashboard | Three different navigation models |
| CRIT-9 | Dashboard | Discover→Template bridge unclear |
| CRIT-10 | Dashboard | Empty state for new users is useless |
| CRIT-11 | Discover Audio | Generation limit (3) hidden until button disables |
| CRIT-12 | Discover Audio | All generations fail = dead end |
| CRIT-13 | Dashboard | Sidebar not responsive |
| CRIT-14 | Template Config | Music mode consequences unclear |

#### MAJOR (25)

| ID | Area | Problem |
|----|------|---------|
| D-UX1 | Discover Refine | 9 blocks at once is overwhelming |
| D-UX2 | Discover Refine | Block interaction has 4+ different patterns |
| D-UX8 | Discover Img/Vid | No side-by-side comparison view |
| D-UX9 | Discover Img/Vid | No zoom/enlarge (lightbox) |
| D-UX10 | Discover Img/Vid | Prompt only visible on hover — not discoverable |
| D-UX11 | Discover Img/Vid | All items fail = unclear recovery path |
| D-UX12 | Discover Img/Vid | Changing finalist is not obvious |
| D-UX21 | Discover Audio | Can't compare audio variants (A/B) |
| D-UX22 | Discover Audio | Two-step selection (variant → hook) not explained |
| D-UX23 | Discover Audio | Three bottom buttons — unclear primary |
| D-UX30 | Discover Cross | Progress bar missing Audio + Extraction stages |
| D-UX31 | Discover Cross | No time estimates during generation |
| D-UX32 | Discover Cross | Different back/forward patterns per stage |
| T-UX3 | Template Config | Step dependencies not shown |
| T-UX4 | Template Config | Collapsed summaries don't explain enough |
| T-UX6 | Template Config | Distribution toggle saves instantly (dirty state mismatch) |
| T-UX7 | Template Config | No recommended settings or smart defaults |
| T-UX8 | Template Config | No quick-start path |
| T-UX11 | Template Generate | Mode names are jargon |
| T-UX12 | Template Generate | No time estimates |
| T-UX13 | Template Generate | Batch errors hidden in collapsed section |
| T-UX14 | Template Generate | No bulk retry |
| T-UX17 | Template Review | Badge counts don't update after actions |
| T-UX18 | Template Review | Filmstrip shows items outside current filter |
| T-UX19 | Template Review | No preset rejection reasons |

#### MINOR (15)

| ID | Area | Problem |
|----|------|---------|
| D-UX4 | Refine | No "X/9 blocks confirmed" counter |
| D-UX5 | Refine | No explanation of block purpose |
| D-UX6 | Refine | No draft save |
| D-UX13 | Images | "Back to Refine" warning is scary |
| D-UX14 | Images | No sort/filter |
| D-UX15 | Videos | Muted autoplay confusing |
| D-UX25 | Audio | Variant cards too small |
| D-UX26 | Audio | Energy badges unexplained |
| D-UX27 | Extraction | UI inconsistent with rest |
| D-UX28 | Extraction | Slot notation unexplained |
| D-UX29 | Completed | No guidance after completion |
| D-UX33 | Cross | Can't jump stages via progress bar |
| D-UX34 | Cross | No stage transition celebration |
| T-UX9 | Config | Technical step names |
| T-UX23 | Review | "All caught up!" misleading after filtering |

---

## 8. Recommendations

### Priority Matrix

| Priority | Theme | Issues Addressed | Effort |
|----------|-------|-----------------|--------|
| **P0** | Validation & dead ends | CRIT-3, CRIT-4, CRIT-7, CRIT-11, CRIT-12 | Medium |
| **P1** | Audio stage redesign | CRIT-1, CRIT-11, CRIT-12, D-UX16-26 | High |
| **P2** | Onboarding & guidance | CRIT-2, CRIT-10, T-UX1, N-UX1-3 | Medium |
| **P3** | Review efficiency | CRIT-5, CRIT-6, T-UX15-22 | Medium |
| **P4** | Navigation unification | CRIT-8, CRIT-9, N-UX4-10 | High |
| **P4.5** | URL state persistence | URL-1 to URL-7 | Medium |
| **P5** | Comparison & inspection | D-UX8, D-UX9, D-UX10 | Medium |
| **P6** | Responsive & polish | CRIT-13, N-UX13-15, minor issues | Medium |

### P0: Validation & Dead Ends (do first — prevents user frustration)

**Discover:**
1. Disable "Advance to Video" / "Select Audio" unless finalist selected. Show tooltip: "Select a finalist to continue"
2. When score <80%: highlight blocks needing work. "Improve [Action] and [Moment] to reach 80%"
3. Audio: show "1/3 generated" counter. When all fail: centered CTA "Audio generation failed. [Try Again] or [Skip Audio →]"

**Template:**
4. Block Generate if required steps incomplete. Show: "Complete Variants and Video steps before generating"
5. Add field-level validation: required fields marked with asterisk, inline error messages

### P1: Audio Stage Redesign

**Current:** 3 tabs + mode toggle + variant grid + hook grid + 3 buttons = overwhelming
**Proposed:** Guided 3-step flow within audio stage:

```
Step 1: Choose type
  "What audio do you want?"
  [Background Music] [Sound Effects] [Skip Audio →]

Step 2: Generate & preview
  [Auto-generate] or [Describe what you want: ________]
  Generated variants (2 columns, larger cards):
    [Variant 1 ▶ Play] ← selected
    [Variant 2 ▶ Play]
    [Variant 3 ▶ Play]
  "2/3 generated. [Generate more]"

Step 3: Pick the best section (if hooks detected)
  "We found 3 catchy sections. Pick one:"
  [0:00-0:15 ▶ HIGH energy] ← selected
  [0:15-0:30 ▶ MEDIUM energy]
  [0:30-0:45 ▶ LOW energy]

  [← Back] [Continue →]
```

### P2: Onboarding & Guidance

1. **Empty Dashboard:** Replace "Select a project" with:
   ```
   Welcome to REGGY!
   Create your first project:
   [Discover] Full creative exploration → reusable template
   [Template] Batch generation from CSV data
   ```

2. **Configure intro banner:**
   ```
   Set up your video pipeline in 6 steps.
   Required: Variants (#2) and Video (#4). Others are optional.
   ```

3. **Collapsed step descriptions:**
   - "Preprocessing — AI enriches your CSV data"
   - "Variants — Your input data (5 rows uploaded)"
   - "Image — Generates images from data (model: flux-pro)"

4. **Generation mode labels:**
   - "Fill schedule (recommended)" — fills your publishing calendar
   - "Top variants" — generates from least-used data for variety
   - "Pick specific" — choose exact data rows

### P3: Review Efficiency

1. **Bulk approve:** "Select All" checkbox → "Approve Selected (5)" button
2. **Undo toast:** "Approved. [Undo — 30s]" after each action
3. **Preset rejection reasons:** Chips: "Bad quality" / "Wrong style" / "Off-brand" / Custom
4. **Keyboard shortcuts:** Enter=approve, R=reject, →=next, ←=prev
5. **Filmstrip filter sync:** Only show items matching current filter
6. **Schedule slot preview:** "Approve → publishes Thu 14:00"

### P4: Navigation Unification

1. **Unify sidebar:** All projects with type badges, sorted by recent activity
2. **Breadcrumbs:** "Dashboard > Project Name > Stage/Screen"
3. **Active nav indicator:** Highlight current page in navbar
4. **Discover→Template link:** After Discover completion, show "This template was created from [Discover Project X]"
5. **Global status:** Mini widget in navbar: "3 generating, 5 need review"

### P4.5: URL State Persistence

**Focus on navigational state (not transient input):**

1. **Review filter + position:** `&reviewFilter=approved&itemIndex=47` — enables resume and handoff
2. **Discover model/count:** `?imageModel=flux-pro&itemCount=6` — survives refresh
3. **Audio tab:** `?audioTab=library` — survives refresh
4. **Configure step:** `&step=4` — direct link to specific setup step
5. **Discover stage history:** Stage transitions should push history entries so Back button returns to previous stage (not exits Discover)

**Not needed in URL (transient):** feedback text, manual audio prompt, playing state, pending unsubmitted selections.

### P5: Comparison & Inspection (Images/Videos)

1. **Lightbox:** Click image → full-screen preview with prompt, select/reject/crown
2. **Side-by-side compare:** Select 2 items → split view
3. **Prompt visibility:** Always show truncated prompt below thumbnail, expand on click
4. **Time estimates:** "Generating 4 images... ~30 seconds" based on model + count

---

## Appendix: Issue Count by Area

| Area | Critical | Major | Minor | Total |
|------|----------|-------|-------|-------|
| Discover Refine | 1 | 2 | 3 | 6 |
| Discover Images/Videos | 1 | 5 | 3 | 9 |
| Discover Audio | 4 | 4 | 2 | 10 |
| Discover Extraction/Completed | 0 | 0 | 3 | 3 |
| Discover Cross-stage | 0 | 3 | 2 | 5 |
| Template Configure | 3 | 5 | 2 | 10 |
| Template Generate | 0 | 4 | 0 | 4 |
| Template Review | 2 | 6 | 1 | 9 |
| Dashboard & Navigation | 3 | 4 | 2 | 9 |
| URL State & Deep Linking | 1 | 4 | 2 | 7 |
| **Total** | **15** | **37** | **20** | **72** |
