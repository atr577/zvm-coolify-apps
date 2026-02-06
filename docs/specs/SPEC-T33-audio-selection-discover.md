# SPEC-T33: Audio Selection for Discover

**Task:** T33 — Audio Selection for Discover
**Created:** 2026-02-06
**Status:** Final

---

## 1. Overview

After video finalist selection in Discover, add an **audio selection step** before template creation. Users choose one of three audio options:

1. **Sound FX** — generate synchronized audio from video via MMAudio V2 (fal.ai)
2. **Music** — generate music track via existing Lyria2 pipeline
3. **Library** — select from previously generated audio in workspace

Or skip audio entirely ("No audio").

The selected audio is previewed with the video on the client, then merged server-side after confirmation. The result is inherited by the Template project.

---

## 2. Resolved Decisions

| # | Question | Decision |
|---|----------|----------|
| 1 | Library scope | **Per-workspace** |
| 2 | Audio preview UX | **Inline** audio player + hook cards (no waveform V1) |
| 3 | Kling fallback for SFX | **No** — MMAudio V2 only |
| 4 | Library pagination | **Page-based** (20 items/page) |
| 5 | Prompt input | **Separate** — SFX: free text / auto, Music: free text / auto |
| 6 | SFX input modes | **Manual prompt** OR **Auto** (model decides from video) |
| 7 | Music input modes | **Manual prompt** OR **Auto** (from concept+image+video context) |
| 8 | Hook selection | **User picks hook** from detected segments after music generation |
| 9 | Preview | **Client-side** (`<video>` + `<audio>` sync). Server merge only after confirm |
| 10 | Per-video SFX in batches | **V1.1** — V1 batches support only music/library modes |
| 11 | Auto-library indexing | **Only Discover-generated audio** — not batch audio |

---

## 3. Stage Flow Change

### Current
```
images → videos → extraction → completed
                     ↓
              Create Template
```

### New
```
images → videos → audio → extraction → completed
                    ↓
         (SFX / Music / Library / Skip)
                    ↓
         [Music: Hook Selection]
                    ↓
         Preview (client-side sync)
                    ↓
         Confirm → server merge → extraction → template
```

New stage `audio` inserted between `videos` and `extraction`.

### Audio Sub-Flow by Type

**Sound FX:**
```
Toggle: [Auto] / [Manual]
  → Auto: Generate (MMAudio analyzes video, no prompt)
  → Manual: type prompt → Generate
→ Variants list (max 3)
→ Select variant → Client preview (video+audio) → Confirm
```

**Music:**
```
Toggle: [Auto] / [Manual]
  → Auto: LLM builds prompt from context → Lyria2 (30s)
  → Manual: type prompt → Lyria2 (30s)
→ Hook Detection (auto) → Hook Selection (user picks segment)
→ Client preview (video + trimmed hook) → Confirm
```

**Library:**
```
Browse/filter → Select track
→ Hook Selection (if track longer than video)
→ Client preview → Confirm
```

**Skip:**
```
"No audio" button → extraction (no audio attached)
```

---

## 4. Database Schema

### 4.1 New Table: `audio_library`

Per-workspace audio library.

```python
class AudioLibrary(Base):
    __tablename__ = "audio_library"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)

    # Source tracking
    source_type = Column(String(20), nullable=False)  # 'sfx' | 'music'
    source_discover_project_id = Column(Integer, ForeignKey("discover_projects.id", ondelete="SET NULL"), nullable=True)

    # Audio file
    file_path = Column(String(500), nullable=False)     # local path: audio/lib_{id}.wav
    file_url = Column(String(500), nullable=True)        # fal CDN URL (original)
    duration_ms = Column(Integer, nullable=False)         # duration in ms

    # Metadata
    prompt = Column(Text, nullable=True)                  # generation prompt (manual or auto-generated)
    mood = Column(String(20), nullable=True)              # energetic|calm|dramatic|playful|dark|neutral

    # Usage stats
    use_count = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index("ix_audio_library_workspace_mood", "workspace_id", "mood"),
        Index("ix_audio_library_workspace_created", "workspace_id", "created_at"),
    )
```

### 4.2 New Table: `discover_audio_variants`

Audio variants generated during Discover audio step.

```python
class DiscoverAudioVariant(Base):
    __tablename__ = "discover_audio_variants"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("discover_projects.id", ondelete="CASCADE"), nullable=False, index=True)

    # Audio type
    audio_type = Column(String(20), nullable=False)  # 'sfx' | 'music' | 'library'

    # Generation details
    prompt = Column(Text, nullable=True)               # prompt used (manual input or LLM-generated for auto)
    prompt_mode = Column(String(10), nullable=False, default="manual")  # 'manual' | 'auto'

    # Result — full generated audio
    status = Column(String(20), nullable=False, default="pending")  # pending|generating|completed|failed
    file_path = Column(String(500), nullable=True)      # full track local path
    file_url = Column(String(500), nullable=True)        # full track URL
    full_duration_ms = Column(Integer, nullable=True)    # full track duration
    error_message = Column(Text, nullable=True)

    # Hook detection (for music/library — auto-detected segments)
    detected_hooks = Column(JSON, nullable=True)         # [{start_ms, end_ms, energy, type}]

    # Selected hook (user picks one segment)
    hook_start_ms = Column(Integer, nullable=True)
    hook_end_ms = Column(Integer, nullable=True)
    trimmed_file_path = Column(String(500), nullable=True)  # trimmed audio file

    # Final duration (after hook trim; for SFX = full_duration_ms)
    duration_ms = Column(Integer, nullable=True)

    # Library reference (if audio_type='library')
    library_item_id = Column(Integer, ForeignKey("audio_library.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
```

### 4.3 Modify: `discover_projects`

Add fields:
```python
# Audio selection
audio_mode = Column(String(20), nullable=True)  # 'sound_fx' | 'music' | 'library' | 'none' | null
selected_audio_variant_id = Column(Integer, ForeignKey("discover_audio_variants.id", ondelete="SET NULL"), nullable=True)
```

Add relationship:
```python
audio_variants = relationship(
    "DiscoverAudioVariant",
    back_populates="project",
    cascade="all, delete-orphan",
    foreign_keys="DiscoverAudioVariant.project_id",
)
```

Update `DiscoverStage` enum:
```python
class DiscoverStage(str, enum.Enum):
    IMAGES = "images"
    VIDEOS = "videos"
    AUDIO = "audio"        # NEW
    EXTRACTION = "extraction"
    COMPLETED = "completed"
```

### 4.4 Modify: `projects` (Template)

Existing `audio_mode` field reused with new values from Discover:

```python
# audio_mode values after T33:
# 'auto'      — existing default (Kling/scene audio)
# 'sound_fx'  — from Discover, per-video MMAudio (V1.1)
# 'music'     — from Discover, single library track per batch
# 'library'   — from Discover, single library track per batch
# 'none'      — no audio
```

Add field:
```python
audio_source_id = Column(Integer, ForeignKey("audio_library.id", ondelete="SET NULL"), nullable=True)
```

Note: `sfx_prompt` deferred to V1.1 (per-video SFX in batches).

---

## 5. API Endpoints

### 5.1 Discover Audio (new)

#### `POST /api/discover/{project_id}/advance-audio`
Advance from `videos` → `audio` stage. Sets video finalist.

Request:
```json
{ "finalist_video_item_id": 42 }
```

#### `POST /api/discover/{project_id}/audio/generate-sfx`
Generate Sound FX via MMAudio V2.

Request:
```json
{
  "mode": "manual",
  "prompt": "shredder crunch, metal grinding"
}
```
- `mode: "auto"` — prompt ignored, MMAudio analyzes video frames
- `mode: "manual"` — prompt required

Response: `DiscoverAudioVariantResponse` (status=generating, poll via project refresh)

#### `POST /api/discover/{project_id}/audio/generate-music`
Generate music via Lyria2.

Request:
```json
{
  "mode": "auto"
}
```
- `mode: "auto"` — LLM builds prompt from project context → Lyria2
- `mode: "manual"` — user prompt → Lyria2

After generation completes: hook detection runs automatically.
Auto-generated prompt stored in `prompt` field for transparency.

Response: `DiscoverAudioVariantResponse`

#### `POST /api/discover/{project_id}/audio/select-hook`
Select a hook segment from detected hooks. Trims audio.

Request:
```json
{
  "variant_id": 7,
  "hook_start_ms": 5200,
  "hook_end_ms": 11200
}
```
Response: `DiscoverAudioVariantResponse` (with trimmed_file_path)

#### `POST /api/discover/{project_id}/audio/select-library`
Select track from library.

Request:
```json
{ "library_item_id": 15 }
```
Creates a variant with `audio_type='library'`. Hook detection runs if track > video duration.

Response: `DiscoverAudioVariantResponse`

#### `POST /api/discover/{project_id}/audio/confirm`
Confirm selection. Merges video+audio server-side (FFmpeg). Advances to extraction.

Request:
```json
{ "variant_id": 7 }
```
Validates: variant completed + hook selected (music/library) or SFX ready.
Action: FFmpeg merge → save merged video → advance stage to extraction.

Response: `DiscoverProjectResponse` (stage=extraction)

#### `POST /api/discover/{project_id}/audio/skip`
Skip audio entirely. Advances to extraction with `audio_mode='none'`.

Response: `DiscoverProjectResponse` (stage=extraction)

#### `POST /api/discover/{project_id}/audio/rollback`
Rollback from `audio` → `videos` stage. Deletes all audio variants, resets `audio_mode` and `selected_audio_variant_id`.

Response: `{ "message": "Rolled back to videos stage" }`

### 5.2 Audio Library (new)

#### `GET /api/audio-library`
Search/list audio library for current workspace.

Query params:
- `workspace_id` (required)
- `mood` (optional)
- `source_type` (optional): sfx | music
- `min_duration_ms` (optional) — when called from Discover audio step, auto-set to finalist video duration to filter out tracks shorter than the video
- `max_duration_ms` (optional)
- `sort` (optional): newest (default), duration, most_used
- `page` (default 1), `page_size` (default 20)

Response:
```json
{
  "items": [AudioLibraryItem],
  "total": 45,
  "page": 1,
  "page_size": 20
}
```

---

## 6. Service Layer

### 6.1 MMAudio V2 Integration

Add methods to existing `FalClient` (like image/video/music):

```python
# In fal_client.py:
async def submit_mmaudio(self, video_url: str, prompt: str | None = None) -> str
async def poll_mmaudio(self, request_id: str) -> str
async def generate_mmaudio(self, video_url: str, prompt: str | None = None) -> str
```

Pattern: same submit+poll as other models. No new file needed.
- Model: `fal-ai/mmaudio-v2`
- Timeout: 120s
- Max 2 retries

### 6.2 Audio Library Service

New file: `backend/app/services/audio_library_service.py`

```python
class AudioLibraryService:
    async def search(workspace_id, filters, sort, page, page_size) -> PaginatedResult
    async def add_from_variant(workspace_id, variant, discover_project_id) -> AudioLibrary
    async def get_item(item_id) -> AudioLibrary
    async def increment_use_count(item_id)
```

### 6.3 Discover Audio Methods

Extend `DiscoverService` with:

```python
async def advance_to_audio(db, project_id, user_id, finalist_video_item_id) -> DiscoverProject
async def generate_sfx(db, project_id, user_id, mode, prompt=None) -> DiscoverAudioVariant
async def generate_music(db, project_id, user_id, mode, prompt=None) -> DiscoverAudioVariant
async def select_hook(db, project_id, user_id, variant_id, hook_start_ms, hook_end_ms) -> DiscoverAudioVariant
async def select_from_library(db, project_id, user_id, library_item_id) -> DiscoverAudioVariant
async def confirm_audio(db, project_id, user_id, variant_id) -> DiscoverProject
async def skip_audio(db, project_id, user_id) -> DiscoverProject
async def rollback_from_audio(db, project_id, user_id) -> DiscoverProject
```

**Auto music prompt generation:**
```python
async def _build_auto_music_prompt(self, project: DiscoverProject) -> str:
    """Build music prompt from project context (concept + refined_prompt + video prompt)."""
    # Uses existing MusicGenerator.generate_prompt() pattern
    # but with Discover context instead of Video model
```

**Hook detection (inline, runs after music/library completion):**
```python
async def _detect_hooks(self, variant: DiscoverAudioVariant, video_duration_ms: int):
    """Run HookAnalyzer on audio, store detected hooks.

    Inline execution with 5s timeout.
    Fallback: if detection fails or times out, return single hook covering full track.
    """
    # 1. Download audio to temp file
    # 2. hook_analyzer.find_hooks(path, video=None, hook_duration=video_duration_ms/1000)
    #    - 5s timeout via asyncio.wait_for
    #    - On timeout/error: fallback hook = [{start_ms: 0, end_ms: full_duration_ms, energy: 'medium', type: 'full'}]
    # 3. Store as JSON in variant.detected_hooks
```

**Confirm merge:**
```python
async def _merge_audio_video(self, variant: DiscoverAudioVariant, project: DiscoverProject):
    """FFmpeg merge of finalist video + selected audio."""
    # Uses existing media_processor.merge_video_audio()
    # Audio source: trimmed_file_path (music/library) or file_path (sfx)
```

---

## 7. Frontend

### 7.1 New Component: `AudioSelection.tsx`

Located: `frontend/src/components/discover/AudioSelection.tsx`

**Layout:**

```
┌─────────────────────────────────────────────────┐
│  Audio Selection                    [Skip Audio] │
│                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │ Sound FX │ │  Music   │ │ Library  │        │
│  └──────────┘ └──────────┘ └──────────┘        │
│                                                  │
│  ┌────────────────────────────────────────┐     │
│  │  (●) Auto   ( ) Manual                │     │
│  │                                        │     │
│  │  [Generate]  (1/3 variants)           │     │
│  └────────────────────────────────────────┘     │
│                                                  │
│  Variants:                                       │
│  ┌─ ▶ ── "auto-generated prompt..." ── 0:06 ─┐ │
│  │                              [Select]       │ │
│  └─────────────────────────────────────────────┘ │
│                                                  │
│  [Music only: Hook Selection]                    │
│  ┌─────────────────────────────────────────┐    │
│  │  Hook 1: 0:05–0:11 (high energy) [▶][✓]│    │
│  │  Hook 2: 0:12–0:18 (medium)      [▶]   │    │
│  │  Hook 3: 0:20–0:26 (medium)      [▶]   │    │
│  └─────────────────────────────────────────┘    │
│                                                  │
│  Preview:                                        │
│  ┌─────────────────────────────────────────┐    │
│  │  ▶ [video + audio playing together]     │    │
│  │     [Confirm & Create Template]         │    │
│  └─────────────────────────────────────────┘    │
└──────────────────────────────────────────────────┘
```

**Tabs:**
1. **Sound FX** — toggle Auto/Manual + Generate. Max 3 variants.
2. **Music** — toggle Auto/Manual + Generate. Max 3 variants. Hook selection after generation.
3. **Library** — paginated list with play buttons. Hook selection if needed.

**Variant cards:**
- `<audio>` play/pause button
- Prompt text (or "Auto-generated: {llm_prompt}")
- Duration label
- "Select" → SFX: go to preview; Music: open hook selection

**Hook selection (music/library):**
- List of detected hooks: start–end time, energy level, type
- Play button per hook (seeks `<audio>` to start, stops at end)
- "Use this hook" → `POST /audio/select-hook` → go to preview

**Preview:**
- `<video>` + `<audio>` elements, synchronized via JS (`play`/`pause`/`seeked` events)
- "Confirm & Create Template" → `POST /audio/confirm` (server merge + extraction)

### 7.2 Stage Flow Update

In `DiscoverPage.tsx`:
- Add `audio` to `STAGE_LABELS` and progress bar
- Progress bar: `Refine → Images → Videos → Audio → Done`
- When `project.stage === 'audio'` → render `<AudioSelection>`
- "Create Template" button on video stage → now calls `advance-audio` (not `finalize`)
- Add rollback button: "Back to Videos" when in audio stage
- Audio variants included in project response → polling works for generation status

### 7.3 New Types

```typescript
export type AudioType = 'sfx' | 'music' | 'library'
export type AudioMood = 'energetic' | 'calm' | 'dramatic' | 'playful' | 'dark' | 'neutral'

export interface AudioHook {
  start_ms: number
  end_ms: number
  energy: string     // 'high' | 'medium'
  type: string       // 'hook' | 'intro' | 'verse' | 'full'
}

export interface DiscoverAudioVariant {
  id: number
  audio_type: AudioType
  prompt: string | null          // manual input or auto-generated (always stored)
  prompt_mode: 'manual' | 'auto'
  status: 'pending' | 'generating' | 'completed' | 'failed'
  file_url: string | null         // full track URL
  full_duration_ms: number | null
  duration_ms: number | null      // after hook trim
  detected_hooks: AudioHook[] | null
  hook_start_ms: number | null
  hook_end_ms: number | null
  error_message: string | null
  library_item_id: number | null
  created_at: string
}

export interface AudioLibraryItem {
  id: number
  source_type: 'sfx' | 'music'
  duration_ms: number
  prompt: string | null
  mood: string | null
  use_count: number
  created_at: string
}

export interface AudioLibrarySearchResponse {
  items: AudioLibraryItem[]
  total: number
  page: number
  page_size: number
}
```

Update `DiscoverProject`:
```typescript
export type DiscoverStage = 'images' | 'videos' | 'audio' | 'extraction' | 'completed'

// Add to DiscoverProject:
audio_mode: string | null           // 'sound_fx' | 'music' | 'library' | 'none'
audio_variants: DiscoverAudioVariant[]
selected_audio_variant_id: number | null
```

---

## 8. Template Integration

### 8.1 Template Creation from Discover

| Discover audio_mode | Template audio_mode | Template behavior |
|---------------------|--------------------|--------------------|
| `sound_fx` | `sound_fx` | V1: uses trimmed SFX as single track. V1.1: per-video MMAudio |
| `music` | `music` | Single library track for entire batch (hook-trimmed) |
| `library` | `library` | Single library track for entire batch |
| `none` | `none` | No audio |

`create_template_project` updated:
- Copy `audio_mode` from Discover
- Copy `audio_source_id` (library item ref) for music/library
- For `sound_fx` V1: store the single SFX as library item, use as `audio_source_id`

### 8.2 Batch Generation (Template)

| audio_mode | V1 Behavior |
|------------|-------------|
| `sound_fx` | Use stored SFX track (single), merge with each video |
| `music` / `library` | Use `audio_source_id` → download once, merge with each video |
| `generate` (existing) | Existing Lyria2 pipeline, unchanged |
| `auto` (existing) | Existing behavior, unchanged |
| `none` | Skip audio step |

V1.1: `sound_fx` will support per-video MMAudio calls with stored prompt.

### 8.3 Auto-Library Indexing

After successful audio generation **in Discover only** — added to library **immediately when generation completes** (status=completed), not at confirm time. This avoids circular dependency with Template `audio_source_id` which needs a library reference at creation.

- SFX: save to library when MMAudio generation completes
- Music: save full track to library when Lyria2 generation completes
- Metadata: prompt, mood (LLM-classified), duration
- `use_count` incremented only when used in a Template (at confirm/template-creation time)

---

## 9. File Structure

```
backend/app/
  models/
    audio_library.py          # NEW: AudioLibrary model
    discover.py               # MODIFY: add DiscoverAudioVariant, AUDIO stage, audio fields
  schemas/
    audio_library.py          # NEW: AudioLibrary schemas
    discover.py               # MODIFY: add audio variant schemas
  api/
    audio_library.py          # NEW: library search endpoint
    discover.py               # MODIFY: add audio endpoints
  services/
    audio_library_service.py  # NEW: library CRUD + search
    fal_client.py             # MODIFY: add MMAudio V2 methods
    discover_service.py       # MODIFY: add audio methods + rollback
  core/
    hook_analyzer.py          # EXISTING: reuse for hook detection

frontend/src/
  components/discover/
    AudioSelection.tsx         # NEW: main audio selection component
  pages/
    DiscoverPage.tsx           # MODIFY: add audio stage + progress bar
  types/index.ts               # MODIFY: add audio types
  services/api.ts              # MODIFY: add audio API calls
```

---

## 10. Implementation Order

| # | Subtask | Estimate | Dependencies |
|---|---------|----------|--------------|
| 1 | DB schema + migrations (`audio_library`, `discover_audio_variants`, project fields) | 3h | — |
| 2 | MMAudio V2 methods in FalClient | 3h | — |
| 3 | Audio library service + API endpoint | 3h | 1 |
| 4 | Discover audio service methods + API endpoints | 5h | 1, 2 |
| 5 | Frontend: AudioSelection component (tabs, generate, hooks, preview) | 8h | 4 |
| 6 | Frontend: DiscoverPage integration (stage, progress bar, rollback) | 3h | 5 |
| 7 | Template creation inheritance (audio_mode, audio_source_id) | 2h | 4 |
| 8 | Auto-library indexing on confirm | 2h | 3, 4 |
| 9 | Testing + polish | 3h | all |

**Total: ~32h** (down from 42h after V1.1 deferral)

Subtasks 1 and 2 can run in parallel.

---

## 11. Variant Limits & Error Handling

- **Sound FX:** Max 3 **completed** variants per session (failed variants don't count toward limit)
- **Music:** Max 3 **completed** variants per session (failed variants don't count toward limit)
- **Library:** Unlimited browsing
- **Prompt validation:** 1–500 characters for manual mode. Empty prompt in manual mode → 400 error. Auto mode ignores prompt field.
- **Generation timeout:** MMAudio 120s, Lyria2 180s
- **On failure:** Show error → offer retry (1x) → "Try different prompt" or "Choose from library"
- **Confirm merge fail:** If FFmpeg merge fails → show error, keep variant selected, allow re-confirm
- **Rollback:** "Back to Videos" deletes all audio variants, resets stage

---

## 12. Not in Scope (V1)

- Mixing SFX + Music together
- Waveform visualization (V1 uses simple `<audio>` + hook cards)
- BPM detection
- Per-video SFX in Template batches (V1.1)
- Cost estimation UI for SFX batches (V1.1)
- Kling video-to-audio fallback
- Custom hook duration (always matches video duration)
