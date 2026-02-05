---
id: SPEC-T31
title: Discover — iterative exploration of new video formats
status: draft
created: 2026-02-04
task: T31
target_sections: []
---

# Technical Specification: Discover — Iterative Exploration

## Overview

Discover is a new workflow (separate `discover_*` tables, NOT a project type extension) that enables structured iterative exploration of video formats through 3 stages: concept input, image refinement (multiple rounds), video refinement, and template extraction. Each round narrows the search space based on user selections and feedback. On completion, creates a standard Template project with extracted base_prompt + variation_prompt.

## Architecture

### Workflow Diagram

```
User enters concept
      |
      v
[Stage: IMAGES]
  Round 1 (WIDE): LLM generates ~10 image prompts -> FAL generates images
      |
  User selects 2-3 favorites + optional feedback
      |
  Round 2 (NARROWING): LLM analyzes selections -> 10 refined prompts -> images
      |
  ... repeat until 1 finalist selected ...
      |
      v
[Stage: VIDEOS]
  Round 1: Finalist image -> ~6 video variations (motion params) -> FAL generates videos
      |
  User selects favorites + feedback
      |
  ... repeat until 1 finalist video ...
      |
      v
[Stage: EXTRACTION]
  LLM extracts: base_prompt (with {slots}) + variation_prompt
      |
  User edits extracted prompts
      |
  Creates Template project
      |
      v
[DONE]
```

### Changes Required

| Component | File | Change Type |
|-----------|------|-------------|
| DiscoverProject model | `backend/app/models/discover.py` | Add |
| DiscoverRound model | `backend/app/models/discover.py` | Add |
| DiscoverItem model | `backend/app/models/discover.py` | Add |
| DiscoverExtraction model | `backend/app/models/discover.py` | Add |
| Models __init__ | `backend/app/models/__init__.py` | Modify |
| Discover schemas | `backend/app/schemas/discover.py` | Add |
| Discover API router | `backend/app/api/discover.py` | Add |
| Discover service | `backend/app/services/discover_service.py` | Add |
| Discover prompts | `backend/app/services/prompts/discover.py` | Add |
| Main app router | `backend/app/main.py` | Modify |
| Alembic migration | `backend/alembic/versions/xxx_add_discover_tables.py` | Add |
| Frontend types | `frontend/src/types/index.ts` | Modify |
| Frontend API client | `frontend/src/services/api.ts` | Modify |
| Frontend Discover page | `frontend/src/pages/DiscoverPage.tsx` | Add |
| Frontend Discover components | `frontend/src/components/discover/` | Add |
| Project creation flow | `frontend/src/pages/` or components | Modify |
| Template Settings (lineage) | `backend/app/models/template_settings.py` | Modify |

---

## Data Structures

### 1. DiscoverProject

```python
# backend/app/models/discover.py

import enum
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base


class DiscoverStage(str, enum.Enum):
    """Current stage of discovery."""
    IMAGES = "images"
    VIDEOS = "videos"
    EXTRACTION = "extraction"
    COMPLETED = "completed"


class DiscoverStatus(str, enum.Enum):
    """Project-level status."""
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class DiscoverProject(Base):
    """
    Discover workflow project.
    Lives in separate tables, NOT part of Project model.
    On completion, creates a standard Template project.
    """
    __tablename__ = "discover_projects"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # User's creative concept
    concept = Column(Text, nullable=False)
    name = Column(String(255), nullable=False)

    # Stage tracking
    stage = Column(
        String(20),
        nullable=False,
        default=DiscoverStage.IMAGES.value
    )
    status = Column(
        String(20),
        nullable=False,
        default=DiscoverStatus.ACTIVE.value
    )

    # Current round number per stage
    current_image_round = Column(Integer, nullable=False, default=0)
    current_video_round = Column(Integer, nullable=False, default=0)

    # Generation settings (user can adjust)
    image_model = Column(String(100), nullable=False, default="fal-ai/flux-pro/v1.1")
    video_model = Column(String(100), nullable=False, default="fal-ai/veo3/fast/image-to-video")
    image_aspect_ratio = Column(String(10), nullable=False, default="9:16")
    video_duration = Column(String(10), nullable=False, default="6s")

    # Finalist references (set when user selects final winner)
    # FKs added via migration after discover_items table created
    finalist_image_item_id = Column(
        Integer,
        ForeignKey("discover_items.id", ondelete="SET NULL", use_alter=True),
        nullable=True
    )
    finalist_video_item_id = Column(
        Integer,
        ForeignKey("discover_items.id", ondelete="SET NULL", use_alter=True),
        nullable=True
    )

    # Link to created Template project
    created_project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True
    )

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    workspace = relationship("Workspace")
    user = relationship("User")
    rounds = relationship(
        "DiscoverRound",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="DiscoverRound.round_number"
    )
    extraction = relationship(
        "DiscoverExtraction",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan"
    )
    created_project = relationship("Project")
```

### 2. DiscoverRound

```python
class RoundType(str, enum.Enum):
    """Type of round."""
    IMAGE = "image"
    VIDEO = "video"


class RoundStatus(str, enum.Enum):
    """Round generation status."""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class DiscoverRound(Base):
    """
    One round of exploration.
    Contains prompts used and generated items.
    """
    __tablename__ = "discover_rounds"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("discover_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    round_number = Column(Integer, nullable=False)  # 1, 2, 3...
    round_type = Column(String(10), nullable=False)  # "image" or "video"

    __table_args__ = (
        UniqueConstraint('project_id', 'round_number', 'round_type', name='uq_discover_round'),
    )

    # Generation status
    status = Column(
        String(20),
        nullable=False,
        default=RoundStatus.PENDING.value
    )
    error_message = Column(Text, nullable=True)

    # LLM prompts used for this round (stored for auditability)
    system_prompt_used = Column(Text, nullable=True)
    user_prompt_used = Column(Text, nullable=True)

    # LLM-generated prompts for items (JSON array of strings)
    generated_prompts = Column(JSON, nullable=True)

    # User feedback for this round (submitted with selection)
    feedback_text = Column(Text, nullable=True)

    # Counts for quick access
    total_items = Column(Integer, nullable=False, default=0)
    selected_count = Column(Integer, nullable=False, default=0)
    rejected_count = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    project = relationship("DiscoverProject", back_populates="rounds")
    items = relationship(
        "DiscoverItem",
        back_populates="round",
        cascade="all, delete-orphan",
        order_by="DiscoverItem.position"
    )
```

### 3. DiscoverItem

```python
class ItemStatus(str, enum.Enum):
    """Status of individual generated item."""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class SelectionStatus(str, enum.Enum):
    """User selection status."""
    UNREVIEWED = "unreviewed"
    SELECTED = "selected"
    REJECTED = "rejected"


class DiscoverItem(Base):
    """
    Single generated item (image or video) within a round.
    Tracks generation result and user selection.
    """
    __tablename__ = "discover_items"

    id = Column(Integer, primary_key=True, index=True)
    round_id = Column(
        Integer,
        ForeignKey("discover_rounds.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    position = Column(Integer, nullable=False)  # Order within round (1..N)

    # The prompt used for this item
    prompt = Column(Text, nullable=False)

    # For video items: source image item
    source_image_item_id = Column(
        Integer,
        ForeignKey("discover_items.id", ondelete="SET NULL"),
        nullable=True
    )

    # Generation
    status = Column(
        String(20),
        nullable=False,
        default=ItemStatus.PENDING.value
    )
    fal_request_id = Column(String(100), nullable=True)
    result_url = Column(String(500), nullable=True)  # Image URL or video URL
    local_path = Column(String(255), nullable=True)  # Downloaded path
    error_message = Column(Text, nullable=True)

    # User selection
    selection = Column(
        String(20),
        nullable=False,
        default=SelectionStatus.UNREVIEWED.value
    )

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    round = relationship("DiscoverRound", back_populates="items")
    source_image_item = relationship(
        "DiscoverItem",
        remote_side=[id],
        foreign_keys=[source_image_item_id]
    )
```

### 4. DiscoverExtraction

```python
class DiscoverExtraction(Base):
    """
    Extracted template from winning image+video combo.
    User can edit before creating Template project.
    """
    __tablename__ = "discover_extractions"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("discover_projects.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )

    # Winning prompts (snapshot from items)
    winning_image_prompt = Column(Text, nullable=False)
    winning_video_prompt = Column(Text, nullable=True)

    # LLM-extracted template prompts
    base_prompt = Column(Text, nullable=False)        # With {slots}
    variation_prompt = Column(Text, nullable=False)    # LLM instructions for variants
    slot_names = Column(JSON, nullable=True)           # ["object", "angle", "lighting"]
    slot_examples = Column(JSON, nullable=True)        # {"object": ["apple", "phone", ...]}

    # User-edited versions (null until user edits)
    edited_base_prompt = Column(Text, nullable=True)
    edited_variation_prompt = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("DiscoverProject", back_populates="extraction")
```

### 5. Template Lineage (modify existing)

Add to `TemplateSettings` model:

```python
# In backend/app/models/template_settings.py
source_discover_id = Column(
    Integer,
    ForeignKey("discover_projects.id", ondelete="SET NULL"),
    nullable=True
)
```

### Storage

- **Where:** PostgreSQL (4 new tables)
- **Tables:** `discover_projects`, `discover_rounds`, `discover_items`, `discover_extractions`
- **Migration:** Single alembic migration creating all 4 tables + adding `source_discover_id` to `template_settings`

### Alembic Migration Plan

```python
# alembic/versions/xxxx_add_discover_tables.py

def upgrade():
    # 1. discover_projects
    op.create_table('discover_projects', ...)

    # 2. discover_rounds
    op.create_table('discover_rounds', ...)

    # 3. discover_items
    op.create_table('discover_items', ...)

    # 4. discover_extractions
    op.create_table('discover_extractions', ...)

    # 5. Add source_discover_id to template_settings
    op.add_column('template_settings',
        sa.Column('source_discover_id', sa.Integer(),
                  sa.ForeignKey('discover_projects.id', ondelete='SET NULL'),
                  nullable=True)
    )

def downgrade():
    op.drop_column('template_settings', 'source_discover_id')
    op.drop_table('discover_extractions')
    op.drop_table('discover_items')
    op.drop_table('discover_rounds')
    op.drop_table('discover_projects')
```

---

## API Changes

13 endpoints prefixed with `/api/discover`. Router registered in `main.py`:

```python
app.include_router(discover.router, prefix="/api/discover", tags=["discover"])
```

### Endpoints

#### 1. Create Discover Project

```
POST /api/discover
```

Request:
```json
{
  "concept": "Industrial hydraulic crusher destroying various objects, close-up, dramatic lighting",
  "name": "Crusher Videos",
  "workspace_id": 1,
  "image_model": "fal-ai/flux-pro/v1.1",
  "video_model": "fal-ai/veo3/fast/image-to-video",
  "image_aspect_ratio": "9:16",
  "video_duration": "6s"
}
```

Response:
```json
{
  "id": 1,
  "concept": "Industrial hydraulic crusher...",
  "name": "Crusher Videos",
  "stage": "images",
  "status": "active",
  "current_image_round": 0,
  "current_video_round": 0,
  "rounds": [],
  "created_at": "2026-02-04T12:00:00"
}
```

#### 2. Get Discover Project

```
GET /api/discover/{id}
```

Response: Full project with all rounds, items, and extraction.

```json
{
  "id": 1,
  "concept": "Industrial hydraulic crusher...",
  "name": "Crusher Videos",
  "stage": "images",
  "status": "active",
  "current_image_round": 2,
  "current_video_round": 0,
  "image_model": "fal-ai/flux-pro/v1.1",
  "video_model": "fal-ai/veo3/fast/image-to-video",
  "image_aspect_ratio": "9:16",
  "video_duration": "6s",
  "finalist_image_item_id": null,
  "finalist_video_item_id": null,
  "created_project_id": null,
  "rounds": [
    {
      "id": 1,
      "round_number": 1,
      "round_type": "image",
      "status": "completed",
      "feedback_text": null,
      "total_items": 10,
      "selected_count": 3,
      "rejected_count": 7,
      "items": [
        {
          "id": 1,
          "position": 1,
          "prompt": "Close-up of industrial hydraulic crusher...",
          "status": "completed",
          "result_url": "/api/files/images/discover_1_r1_1.jpg",
          "local_path": "images/discover_1_r1_1.jpg",
          "selection": "selected"
        }
      ]
    }
  ],
  "extraction": null,
  "created_at": "2026-02-04T12:00:00"
}
```

#### 3. List Discover Projects

```
GET /api/discover?status=active
```

Response:
```json
{
  "projects": [...],
  "total": 5
}
```

#### 4. Generate Next Round

```
POST /api/discover/{id}/rounds
```

Request (for round 1, no body required):
```json
{}
```

Request (for round 2+, after selection):
```json
{
  "feedback": "I want more dramatic angles and darker lighting"
}
```

Response:
```json
{
  "round": {
    "id": 2,
    "round_number": 2,
    "round_type": "image",
    "status": "generating",
    "items": []
  }
}
```

The round generation runs as a background task. Items are populated as they complete. Frontend polls `GET /api/discover/{id}` to track progress.

#### 5. Submit Selection

```
POST /api/discover/{id}/rounds/{round_id}/select
```

Request:
```json
{
  "selections": {
    "1": "selected",
    "2": "rejected",
    "3": "selected",
    "4": "rejected",
    "5": "rejected",
    "6": "rejected",
    "7": "selected",
    "8": "rejected",
    "9": "rejected",
    "10": "rejected"
  },
  "feedback": "More close-up, less wide angle"
}
```

- Keys: item IDs (string for JSON compat)
- Values: `"selected"` or `"rejected"`
- Items not included stay `"unreviewed"` (treated as rejected for narrowing)

Response:
```json
{
  "round_id": 1,
  "selected_count": 3,
  "rejected_count": 7,
  "can_advance_to_video": false,
  "can_generate_next_round": true
}
```

Business rules:
- If exactly 1 item selected and user confirms -> can advance to video stage
- If 2+ items selected -> must generate next narrowing round
- `feedback` is optional text stored on the round

#### 6. Advance to Video Stage

```
POST /api/discover/{id}/advance
```

Request:
```json
{
  "finalist_image_item_id": 15
}
```

Preconditions:
- Stage must be `images`
- Exactly 1 image item must be selected as finalist

Response:
```json
{
  "stage": "videos",
  "finalist_image_item_id": 15
}
```

#### 7. Rollback to Previous Round

```
POST /api/discover/{id}/rollback
```

Removes the last completed round and resets selections. Allows the user to go back if an unlucky narrowing happened.

Request: no body.

Response:
```json
{
  "rolled_back_round_id": 3,
  "current_round": 2,
  "stage": "images"
}
```

Business rules:
- Cannot rollback round 1 (it's the initial wide round)
- If in video stage and rolling back, goes back to images stage
- Rolled-back round items are deleted (media files cleaned up)

#### 8. Advance to Extraction (set video finalist)

```
POST /api/discover/{id}/advance-extraction
```

Request:
```json
{
  "finalist_video_item_id": 42
}
```

Preconditions:
- Stage must be `videos`
- Exactly 1 video item must be selected as finalist
- Finalist video must have `status = "completed"`

Response:
```json
{
  "stage": "extraction",
  "finalist_video_item_id": 42
}
```

Sets `finalist_video_item_id` on the project and advances stage to `extraction`.

#### 9. Extract Template

```
POST /api/discover/{id}/extract
```

Preconditions:
- Stage must be `videos`
- Finalist video item must be selected

Response:
```json
{
  "extraction": {
    "id": 1,
    "winning_image_prompt": "Close-up of industrial hydraulic crusher pressing down on a ripe watermelon...",
    "winning_video_prompt": "Slow dramatic press downward...",
    "base_prompt": "Close-up of industrial hydraulic crusher pressing down on a {object}, dramatic side lighting, ultra-detailed, cinematic composition, 9:16 vertical format",
    "variation_prompt": "Vary {object}: use fruits (watermelon, pineapple), electronics (old phone, laptop), glass objects (wine glass, snow globe). Keep fixed: close-up angle, dramatic side lighting, crusher visible from left. Optionally vary: lighting color temperature (warm amber vs cool blue), surface texture beneath object.",
    "slot_names": ["object"],
    "slot_examples": {
      "object": ["watermelon", "old phone", "wine glass", "pineapple", "laptop"]
    }
  }
}
```

#### 10. Update Extraction (edit prompts)

```
PUT /api/discover/{id}/extraction
```

Request:
```json
{
  "edited_base_prompt": "Close-up of industrial hydraulic crusher pressing down on a {object}, {lighting} lighting, ultra-detailed...",
  "edited_variation_prompt": "Vary {object}: ..."
}
```

Response: updated extraction object.

#### 11. Create Template from Extraction

```
POST /api/discover/{id}/create-template
```

Request:
```json
{
  "name": "Crusher Template",
  "platforms": ["youtube", "instagram"],
  "video_template_prompt": "Slow dramatic crushing motion, object deforms under extreme pressure"
}
```

Creates:
1. `Project` (type=template)
2. `TemplateSettings` with:
   - `preprocessing_prompt` derived from variation_prompt
   - `image_prompt_template` from base_prompt
   - `source_discover_id` link
   - models copied from discover project
3. `VideoTemplate` with the video prompt

Response:
```json
{
  "project_id": 42,
  "project_name": "Crusher Template",
  "message": "Template project created from Discover"
}
```

Side effects:
- Sets `discover_project.created_project_id = 42`
- Sets `discover_project.stage = "completed"`
- Sets `discover_project.status = "completed"`

#### 12. Delete/Archive Discover Project

```
DELETE /api/discover/{id}
```

Soft-archive: sets `status = "archived"`. Does not delete data.

Response: 204 No Content.

#### 13. Retry Failed Items

```
POST /api/discover/{id}/rounds/{round_id}/retry
```

Retries all failed items in a round (re-submits to FAL).

Response:
```json
{
  "retried_count": 2,
  "round_status": "generating"
}
```

---

## LLM Prompts

All prompts stored in `backend/app/services/prompts/discover.py`.

**Important:** System prompts containing `{count}` are Python format strings. Must call `.format(count=N)` before passing to LLM. Example: `DISCOVER_IMAGE_WIDE_SYSTEM.format(count=10)`.

### 1. Image Prompt Generation (Round 1 -- Wide)

```python
DISCOVER_IMAGE_WIDE_SYSTEM = """You are a creative director for short-form viral video content.
Your job is to generate diverse, visually striking image prompts based on a user's concept.

RULES:
1. Generate exactly {count} image prompts, each unique and diverse
2. Each prompt should be a complete, detailed image description in ENGLISH
3. Vary these dimensions across prompts:
   - Camera angle (close-up, wide, bird's eye, low angle, dutch angle)
   - Lighting (dramatic side light, soft natural, neon, golden hour, high contrast)
   - Composition (centered, rule of thirds, symmetrical, dynamic diagonal)
   - Style (photorealistic, cinematic, hyper-detailed, editorial)
   - Object/subject variation within the concept
4. Every prompt must be suitable for image-to-video (clear subject, implied motion potential)
5. Include aspect ratio composition hints (vertical 9:16 by default)
6. Keep each prompt 50-120 words
7. Do NOT include text overlays, watermarks, or UI elements in prompts

Return JSON:
{
  "prompts": [
    "prompt text 1",
    "prompt text 2",
    ...
  ]
}"""


def build_discover_wide_prompt(concept: str, count: int = 10) -> str:
    return f"""USER CONCEPT:
{concept}

Generate {count} diverse image prompts exploring this concept from different angles, styles, and compositions.
Each prompt should be a standalone image description that could work as the first frame of a short viral video.
Make them VERY different from each other — explore the creative space widely."""
```

### 2. Narrowing Prompt (Round 2+)

```python
DISCOVER_IMAGE_NARROW_SYSTEM = """You are a creative director refining image prompts based on user preferences.
The user has selected favorites and rejected others from a previous round. Your job is to generate NEW prompts
that are closer to what the user likes, while still introducing creative variation.

ANALYSIS APPROACH:
1. Study what the SELECTED prompts have in common (angle, lighting, style, composition, subject treatment)
2. Study what the REJECTED prompts had that the user didn't like
3. Generate new prompts that match the preferred patterns but explore new variations within that space
4. If user provided text feedback, prioritize those directions

RULES:
1. Generate exactly {count} new prompts
2. Each prompt 50-120 words, in ENGLISH
3. 70% of prompts should be close to selected preferences
4. 30% of prompts should push boundaries slightly (creative exploration within the preferred direction)
5. Do NOT repeat any of the previous prompts verbatim
6. Keep the core concept but refine style, angle, lighting per user taste

Return JSON:
{
  "prompts": [
    "prompt text 1",
    ...
  ],
  "analysis": "Brief analysis of what the user seems to prefer (1-2 sentences)"
}"""


def build_discover_narrow_prompt(
    concept: str,
    selected_prompts: list[str],
    rejected_prompts: list[str],
    feedback: str | None = None,
    count: int = 10
) -> str:
    feedback_section = ""
    if feedback:
        feedback_section = f"""
USER FEEDBACK (prioritize this):
{feedback}
"""

    return f"""ORIGINAL CONCEPT:
{concept}

SELECTED (user liked these):
{chr(10).join(f'- {p}' for p in selected_prompts)}

REJECTED (user did NOT like these):
{chr(10).join(f'- {p}' for p in rejected_prompts)}
{feedback_section}
Generate {count} NEW image prompts that are closer to the user's preferences while maintaining creative diversity.
Do not repeat previous prompts. Refine the direction based on selection patterns and feedback."""
```

### 3. Video Prompt Generation

```python
DISCOVER_VIDEO_SYSTEM = """You are a motion director for short-form viral videos.
Given a winning image prompt, generate diverse VIDEO MOTION prompts that describe how the scene should animate.

RULES:
1. Generate exactly {count} motion prompt variations
2. Each motion prompt should be 20-60 words in ENGLISH
3. Vary these dimensions:
   - Camera movement (static, slow zoom in, dolly out, pan, orbit, tracking)
   - Subject motion (subtle, dramatic, explosive, gentle)
   - Speed (slow-mo, real-time, time-lapse)
   - Mood (suspenseful build, sudden action, smooth flow)
4. All motion prompts must be compatible with the given image as the starting frame
5. Think about what makes a 5-8 second clip go VIRAL

Return JSON:
{
  "prompts": [
    "motion prompt 1",
    ...
  ]
}"""


def build_discover_video_prompt(
    image_prompt: str,
    count: int = 6,
    selected_prompts: list[str] | None = None,
    rejected_prompts: list[str] | None = None,
    feedback: str | None = None
) -> str:
    context = f"""WINNING IMAGE (first frame):
{image_prompt}

Generate {count} different motion/video prompts for this image."""

    if selected_prompts:
        context += f"""

PREVIOUSLY SELECTED MOTION STYLES:
{chr(10).join(f'- {p}' for p in selected_prompts)}

PREVIOUSLY REJECTED MOTION STYLES:
{chr(10).join(f'- {p}' for p in (rejected_prompts or []))}"""

    if feedback:
        context += f"""

USER FEEDBACK:
{feedback}"""

    return context
```

### 4. Extraction Prompt

```python
DISCOVER_EXTRACTION_SYSTEM = """You are a template engineer for AI video generation.
Given a winning image prompt (and optionally a video prompt), extract a REUSABLE TEMPLATE.

Your job:
1. Identify the FIXED elements (always present): lighting style, camera angle, composition, quality keywords
2. Identify the VARIABLE elements (what changes between videos): the main subject/object, colors, specific details
3. Create a base_prompt with {slot_name} placeholders for variable elements
4. Create a variation_prompt that instructs an LLM how to fill those slots

RULES:
- Use descriptive slot names: {object}, {material}, {color_scheme}, {environment}
- Keep 1-3 slots (not more, templates should be focused)
- The base_prompt must produce good results when any reasonable value fills the slots
- The variation_prompt must explain: what values work, what to vary, what to keep fixed
- Write everything in ENGLISH

Return JSON:
{
  "base_prompt": "template with {slot} placeholders",
  "variation_prompt": "Instructions for generating variants...",
  "slot_names": ["slot1", "slot2"],
  "slot_examples": {
    "slot1": ["example1", "example2", "example3", "example4", "example5"],
    "slot2": ["example1", "example2", "example3"]
  }
}"""


def build_discover_extraction_prompt(
    winning_image_prompt: str,
    winning_video_prompt: str | None = None
) -> str:
    video_section = ""
    if winning_video_prompt:
        video_section = f"""

WINNING VIDEO/MOTION PROMPT:
{winning_video_prompt}"""

    return f"""WINNING IMAGE PROMPT:
{winning_image_prompt}
{video_section}

Extract a reusable template from this winning prompt.
Identify what should stay fixed (the "recipe") and what should vary (the "ingredients")."""
```

---

## Service Architecture

### DiscoverService

```python
# backend/app/services/discover_service.py

class DiscoverService:
    """Orchestrates the Discover workflow."""

    def __init__(self):
        self.openai = OpenAIClient()
        self.fal = FalClient()

    # --- Project CRUD ---

    async def create_project(
        self, db: Session, user_id: int, workspace_id: int,
        concept: str, name: str, **kwargs
    ) -> DiscoverProject:
        """Create a new Discover project."""
        ...

    async def get_project(
        self, db: Session, project_id: int, user_id: int
    ) -> DiscoverProject:
        """Get project with access check. Eager-load rounds + items."""
        ...

    async def list_projects(
        self, db: Session, user_id: int, workspace_id: int,
        status: str | None = None
    ) -> list[DiscoverProject]:
        ...

    async def archive_project(
        self, db: Session, project_id: int, user_id: int
    ) -> None:
        ...

    # --- Round Generation ---

    async def generate_round(
        self, db: Session, project_id: int, user_id: int,
        feedback: str | None = None
    ) -> DiscoverRound:
        """
        Generate the next round of exploration.

        Flow:
        1. Determine round type (image or video) based on current stage
        2. Gather context (concept, previous selections, feedback)
        3. Call LLM to generate prompts
        4. Create DiscoverRound + DiscoverItem records (status=pending)
        5. Start background task to generate media via FAL
        6. Return round (frontend polls for completion)
        """
        ...

    async def _generate_image_round(
        self, db: Session, project: DiscoverProject,
        feedback: str | None = None
    ) -> DiscoverRound:
        """Generate image round (wide or narrowing)."""
        round_number = project.current_image_round + 1

        if round_number == 1:
            # Wide: use concept only
            prompts = await self._llm_generate_wide_prompts(project.concept)
        else:
            # Narrowing: gather selections from previous rounds
            selected, rejected = self._gather_selections(db, project, "image")
            prompts = await self._llm_generate_narrow_prompts(
                project.concept, selected, rejected, feedback
            )

        # Create round + items
        round = DiscoverRound(
            project_id=project.id,
            round_number=round_number,
            round_type="image",
            status="generating",
            generated_prompts=prompts,
            total_items=len(prompts),
        )
        db.add(round)
        db.flush()

        items = []
        for i, prompt in enumerate(prompts):
            item = DiscoverItem(
                round_id=round.id,
                position=i + 1,
                prompt=prompt,
                status="pending",
            )
            db.add(item)
            items.append(item)

        project.current_image_round = round_number
        db.commit()

        # Start background generation
        asyncio.create_task(
            self._generate_items_background(project.id, round.id, "image")
        )

        return round

    async def _generate_items_background(
        self, project_id: int, round_id: int, item_type: str
    ):
        """Background task: generate all items in a round via FAL."""
        from app.db.base import SessionLocal
        db = SessionLocal()
        try:
            round = db.query(DiscoverRound).filter(
                DiscoverRound.id == round_id
            ).first()
            items = db.query(DiscoverItem).filter(
                DiscoverItem.round_id == round_id
            ).order_by(DiscoverItem.position).all()

            project = db.query(DiscoverProject).filter(
                DiscoverProject.id == project_id
            ).first()

            completed = 0
            failed = 0

            for item in items:
                try:
                    item.status = "generating"
                    db.commit()

                    if item_type == "image":
                        url = await self.fal.generate_image(
                            prompt=item.prompt,
                            aspect_ratio=project.image_aspect_ratio,
                            model=project.image_model,
                        )
                        local_path = await self._download_discover_media(
                            url, project_id, round_id, item.position, "image"
                        )
                    else:  # video
                        source_item = db.query(DiscoverItem).filter(
                            DiscoverItem.id == item.source_image_item_id
                        ).first()
                        url = await self.fal.generate_video(
                            image_url=source_item.result_url,
                            prompt=item.prompt,
                            duration=project.video_duration,
                            generate_audio=False,
                            model=project.video_model,
                        )
                        local_path = await self._download_discover_media(
                            url, project_id, round_id, item.position, "video"
                        )

                    item.result_url = url
                    item.local_path = local_path
                    item.status = "completed"
                    item.completed_at = datetime.utcnow()
                    completed += 1

                except Exception as e:
                    item.status = "failed"
                    item.error_message = str(e)[:500]
                    failed += 1
                    logger.error(f"Discover item {item.id} failed: {e}")

                db.commit()

            # Update round status
            if failed == len(items):
                round.status = "failed"
            else:
                round.status = "completed"
            round.completed_at = datetime.utcnow()
            db.commit()

        finally:
            db.close()

    # --- Selection ---

    async def submit_selection(
        self, db: Session, project_id: int, round_id: int,
        selections: dict[str, str], feedback: str | None = None
    ) -> dict:
        """Submit user selections for a round."""
        round = db.query(DiscoverRound).filter(
            DiscoverRound.id == round_id,
            DiscoverRound.project_id == project_id,
        ).first()

        items = db.query(DiscoverItem).filter(
            DiscoverItem.round_id == round_id
        ).all()

        selected_count = 0
        rejected_count = 0

        for item in items:
            sel = selections.get(str(item.id), "unreviewed")
            item.selection = sel
            if sel == "selected":
                selected_count += 1
            elif sel == "rejected":
                rejected_count += 1

        round.selected_count = selected_count
        round.rejected_count = rejected_count
        round.feedback_text = feedback
        db.commit()

        return {
            "round_id": round_id,
            "selected_count": selected_count,
            "rejected_count": rejected_count,
            "can_advance_to_video": selected_count == 1 and round.round_type == "image",
            "can_generate_next_round": selected_count >= 1,
        }

    # --- Stage Advancement ---

    async def advance_to_video(
        self, db: Session, project_id: int, finalist_item_id: int
    ) -> DiscoverProject:
        """Advance from images to videos stage.

        Important: Re-downloads the finalist image to ensure local copy exists.
        FAL CDN URLs expire — video generation needs the image available.
        Uses result_url (FAL CDN) for video generation, local_path as backup.
        """
        ...
        # Ensure finalist image is downloaded locally
        finalist_item = db.query(DiscoverItem).filter(
            DiscoverItem.id == finalist_item_id
        ).first()
        if finalist_item.result_url and not finalist_item.local_path:
            finalist_item.local_path = await self._download_discover_media(
                finalist_item.result_url, project_id, 0, 0, "image"
            )

        project.stage = DiscoverStage.VIDEOS.value
        project.finalist_image_item_id = finalist_item_id
        db.commit()
        return project

    # --- Rollback ---

    async def rollback(
        self, db: Session, project_id: int
    ) -> dict:
        """Roll back last round. Delete items + media."""
        ...

    # --- Extraction ---

    async def extract_template(
        self, db: Session, project_id: int
    ) -> DiscoverExtraction:
        """Extract base_prompt + variation_prompt from winning combo."""
        project = ...  # load
        finalist_image = db.query(DiscoverItem).filter(
            DiscoverItem.id == project.finalist_image_item_id
        ).first()
        finalist_video = db.query(DiscoverItem).filter(
            DiscoverItem.id == project.finalist_video_item_id
        ).first() if project.finalist_video_item_id else None

        # Call LLM
        result = await self.openai.generate_json(
            prompt=build_discover_extraction_prompt(
                finalist_image.prompt,
                finalist_video.prompt if finalist_video else None
            ),
            system_prompt=DISCOVER_EXTRACTION_SYSTEM,
            model="gpt-4o",
            temperature=0.5,
        )

        extraction = DiscoverExtraction(
            project_id=project.id,
            winning_image_prompt=finalist_image.prompt,
            winning_video_prompt=finalist_video.prompt if finalist_video else None,
            base_prompt=result["base_prompt"],
            variation_prompt=result["variation_prompt"],
            slot_names=result.get("slot_names"),
            slot_examples=result.get("slot_examples"),
        )
        db.add(extraction)
        project.stage = DiscoverStage.EXTRACTION.value
        db.commit()
        return extraction

    # --- Template Creation ---

    async def create_template_project(
        self, db: Session, project_id: int, user_id: int,
        name: str, platforms: list[str],
        video_template_prompt: str
    ) -> int:
        """Create Template project from extraction."""
        project = ...  # load discover project
        extraction = project.extraction

        # Use edited versions if available, otherwise originals
        base_prompt = extraction.edited_base_prompt or extraction.base_prompt
        variation_prompt = extraction.edited_variation_prompt or extraction.variation_prompt

        # Create Project
        template_project = Project(
            user_id=user_id,
            workspace_id=project.workspace_id,
            name=name,
            project_type="template",
            story_template="",
            platforms=platforms,
            duration=10,
            aspect_ratio=project.image_aspect_ratio,
        )
        db.add(template_project)
        db.flush()

        # Create TemplateSettings
        # variation_prompt becomes preprocessing_prompt
        # base_prompt becomes image_prompt_template
        settings = TemplateSettings(
            project_id=template_project.id,
            preprocessing_prompt=variation_prompt,
            image_prompt_template=base_prompt,
            llm_model="gpt-4o-mini",
            image_model=project.image_model,
            video_model=project.video_model,
            image_aspect_ratio=project.image_aspect_ratio,
            video_duration=project.video_duration,
            source_discover_id=project.id,
        )
        db.add(settings)

        # Create VideoTemplate
        vt = VideoTemplate(
            project_id=template_project.id,
            name="Default",
            prompt=video_template_prompt,
            is_default=True,
        )
        db.add(vt)

        # Update discover project
        project.created_project_id = template_project.id
        project.stage = DiscoverStage.COMPLETED.value
        project.status = DiscoverStatus.COMPLETED.value
        db.commit()

        return template_project.id

    # --- Helpers ---

    async def _download_discover_media(
        self, url: str, project_id: int, round_id: int,
        position: int, media_type: str
    ) -> str:
        """Download FAL result to local storage with discover-specific naming."""
        import aiohttp, os
        ext = "jpg" if media_type == "image" else "mp4"
        filename = f"discover_{project_id}_r{round_id}_{position}.{ext}"
        folder = "images" if media_type == "image" else "videos"
        local_dir = os.path.join("media", folder)
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, filename)

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                with open(local_path, "wb") as f:
                    f.write(await resp.read())

        return os.path.join(folder, filename)

    def _gather_selections(
        self, db: Session, project: DiscoverProject, round_type: str
    ) -> tuple[list[str], list[str]]:
        """Gather all selected/rejected prompts across rounds for narrowing."""
        rounds = db.query(DiscoverRound).filter(
            DiscoverRound.project_id == project.id,
            DiscoverRound.round_type == round_type,
        ).order_by(DiscoverRound.round_number).all()

        selected = []
        rejected = []
        for r in rounds:
            items = db.query(DiscoverItem).filter(
                DiscoverItem.round_id == r.id
            ).all()
            for item in items:
                if item.selection == "selected":
                    selected.append(item.prompt)
                else:
                    rejected.append(item.prompt)

        # Context window management: if too many accumulated prompts,
        # keep only last 3 rounds of rejected (selected always kept in full).
        # This prevents exceeding LLM context window after 5+ rounds.
        MAX_REJECTED = 30  # ~30 rejected prompts ≈ 3 rounds
        if len(rejected) > MAX_REJECTED:
            rejected = rejected[-MAX_REJECTED:]

        return selected, rejected
```

### Integration with Existing Services

| Existing Service | How Discover Uses It |
|-----------------|---------------------|
| `OpenAIClient` (singleton `openai_client`) | `generate_json()` for prompt generation and extraction |
| `FalClient` (singleton `fal_client_instance`) | `generate_image()` and `generate_video()` for media |
| `download_image`, `download_video` | Download FAL results to local storage |
| `get_current_user` dependency | Auth for all endpoints |
| `user_has_workspace_access` | Workspace access verification |

### Singleton Pattern

```python
# Bottom of discover_service.py
_service: DiscoverService | None = None

def get_discover_service() -> DiscoverService:
    global _service
    if _service is None:
        _service = DiscoverService()
    return _service
```

---

## Pydantic Schemas

```python
# backend/app/schemas/discover.py

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, List, Any
from datetime import datetime


# --- Create ---

class DiscoverProjectCreate(BaseModel):
    concept: str = Field(..., min_length=10, max_length=2000)
    name: str = Field(..., min_length=1, max_length=255)
    workspace_id: int  # Required. Frontend sends current workspace. Backend verifies access.
    image_model: str = "fal-ai/flux-pro/v1.1"
    video_model: str = "fal-ai/veo3/fast/image-to-video"
    image_aspect_ratio: str = "9:16"
    video_duration: str = "6s"


# --- Responses ---

class DiscoverItemResponse(BaseModel):
    id: int
    position: int
    prompt: str
    source_image_item_id: Optional[int] = None
    status: str
    result_url: Optional[str] = None
    local_path: Optional[str] = None
    error_message: Optional[str] = None
    selection: str
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DiscoverRoundResponse(BaseModel):
    id: int
    round_number: int
    round_type: str
    status: str
    error_message: Optional[str] = None
    feedback_text: Optional[str] = None
    total_items: int
    selected_count: int
    rejected_count: int
    items: List[DiscoverItemResponse] = []
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DiscoverExtractionResponse(BaseModel):
    id: int
    winning_image_prompt: str
    winning_video_prompt: Optional[str] = None
    base_prompt: str
    variation_prompt: str
    slot_names: Optional[List[str]] = None
    slot_examples: Optional[Dict[str, List[str]]] = None
    edited_base_prompt: Optional[str] = None
    edited_variation_prompt: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DiscoverProjectResponse(BaseModel):
    id: int
    concept: str
    name: str
    stage: str
    status: str
    current_image_round: int
    current_video_round: int
    image_model: str
    video_model: str
    image_aspect_ratio: str
    video_duration: str
    finalist_image_item_id: Optional[int] = None
    finalist_video_item_id: Optional[int] = None
    created_project_id: Optional[int] = None
    rounds: List[DiscoverRoundResponse] = []
    extraction: Optional[DiscoverExtractionResponse] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DiscoverProjectListResponse(BaseModel):
    projects: List[DiscoverProjectResponse]
    total: int


# --- Requests ---

class GenerateRoundRequest(BaseModel):
    feedback: Optional[str] = None


class SelectionValue(str, Enum):
    SELECTED = "selected"
    REJECTED = "rejected"


class SelectionRequest(BaseModel):
    selections: Dict[str, SelectionValue]  # item_id -> "selected" | "rejected"
    feedback: Optional[str] = None


class SelectionResponse(BaseModel):
    round_id: int
    selected_count: int
    rejected_count: int
    can_advance_to_video: bool
    can_generate_next_round: bool


class AdvanceRequest(BaseModel):
    finalist_image_item_id: int


class AdvanceExtractionRequest(BaseModel):
    finalist_video_item_id: int


class ExtractionUpdateRequest(BaseModel):
    edited_base_prompt: Optional[str] = None
    edited_variation_prompt: Optional[str] = None


class CreateTemplateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    platforms: List[str] = ["youtube"]
    video_template_prompt: str
```

---

## Frontend

### TypeScript Types

Add to `frontend/src/types/index.ts`:

```typescript
// --- Discover Types ---

export type DiscoverStage = 'images' | 'videos' | 'extraction' | 'completed'
export type DiscoverStatus = 'active' | 'completed' | 'archived'
export type DiscoverRoundType = 'image' | 'video'
export type DiscoverRoundStatus = 'pending' | 'generating' | 'completed' | 'failed'
export type DiscoverItemStatus = 'pending' | 'generating' | 'completed' | 'failed'
export type DiscoverSelectionStatus = 'unreviewed' | 'selected' | 'rejected'

export interface DiscoverItem {
  id: number
  position: number
  prompt: string
  source_image_item_id: number | null
  status: DiscoverItemStatus
  result_url: string | null
  local_path: string | null
  error_message: string | null
  selection: DiscoverSelectionStatus
  created_at: string
  completed_at: string | null
}

export interface DiscoverRound {
  id: number
  round_number: number
  round_type: DiscoverRoundType
  status: DiscoverRoundStatus
  error_message: string | null
  feedback_text: string | null
  total_items: number
  selected_count: number
  rejected_count: number
  items: DiscoverItem[]
  created_at: string
  completed_at: string | null
}

export interface DiscoverExtraction {
  id: number
  winning_image_prompt: string
  winning_video_prompt: string | null
  base_prompt: string
  variation_prompt: string
  slot_names: string[] | null
  slot_examples: Record<string, string[]> | null
  edited_base_prompt: string | null
  edited_variation_prompt: string | null
  created_at: string
  updated_at: string
}

export interface DiscoverProject {
  id: number
  concept: string
  name: string
  stage: DiscoverStage
  status: DiscoverStatus
  current_image_round: number
  current_video_round: number
  image_model: string
  video_model: string
  image_aspect_ratio: string
  video_duration: string
  finalist_image_item_id: number | null
  finalist_video_item_id: number | null
  created_project_id: number | null
  rounds: DiscoverRound[]
  extraction: DiscoverExtraction | null
  created_at: string
  updated_at: string
}
```

### API Client

Add to `frontend/src/services/api.ts`:

```typescript
// Discover API
export const discoverApi = {
  // Projects
  create: (data: {
    concept: string
    name: string
    workspace_id?: number
    image_model?: string
    video_model?: string
    image_aspect_ratio?: string
    video_duration?: string
  }) => api.post<DiscoverProject>('/api/discover', data),

  get: (id: number) =>
    api.get<DiscoverProject>(`/api/discover/${id}`),

  list: (params?: { status?: string }) =>
    api.get<{ projects: DiscoverProject[]; total: number }>('/api/discover', { params }),

  archive: (id: number) =>
    api.delete(`/api/discover/${id}`),

  // Rounds
  generateRound: (id: number, feedback?: string) =>
    api.post<{ round: DiscoverRound }>(`/api/discover/${id}/rounds`, { feedback }),

  submitSelection: (id: number, roundId: number, data: {
    selections: Record<string, string>
    feedback?: string
  }) => api.post<{
    round_id: number
    selected_count: number
    rejected_count: number
    can_advance_to_video: boolean
    can_generate_next_round: boolean
  }>(`/api/discover/${id}/rounds/${roundId}/select`, data),

  retryRound: (id: number, roundId: number) =>
    api.post<{ retried_count: number }>(`/api/discover/${id}/rounds/${roundId}/retry`),

  // Stage management
  advanceToVideo: (id: number, finalistImageItemId: number) =>
    api.post<DiscoverProject>(`/api/discover/${id}/advance`, {
      finalist_image_item_id: finalistImageItemId
    }),

  advanceToExtraction: (id: number, finalistVideoItemId: number) =>
    api.post<DiscoverProject>(`/api/discover/${id}/advance-extraction`, {
      finalist_video_item_id: finalistVideoItemId
    }),

  rollback: (id: number) =>
    api.post<{ rolled_back_round_id: number; current_round: number; stage: string }>(
      `/api/discover/${id}/rollback`
    ),

  // Extraction
  extract: (id: number) =>
    api.post<{ extraction: DiscoverExtraction }>(`/api/discover/${id}/extract`),

  updateExtraction: (id: number, data: {
    edited_base_prompt?: string
    edited_variation_prompt?: string
  }) => api.put<DiscoverExtraction>(`/api/discover/${id}/extraction`, data),

  createTemplate: (id: number, data: {
    name: string
    platforms: string[]
    video_template_prompt: string
  }) => api.post<{ project_id: number; project_name: string }>(
    `/api/discover/${id}/create-template`, data
  ),
}
```

### Component Tree

```
DiscoverPage (route: /discover/:id)
  |
  +-- DiscoverHeader (name, concept, stage indicator, settings)
  |
  +-- StageProgress (images -> videos -> extraction -> done)
  |
  +-- [Stage: IMAGES / VIDEOS]
  |   |
  |   +-- RoundHistory (collapsed previous rounds)
  |   |
  |   +-- CurrentRound
  |       |
  |       +-- RoundStatus (generating spinner / completed)
  |       |
  |       +-- ItemGrid (card grid with images/videos)
  |       |   |
  |       |   +-- ItemCard (media + select/reject buttons)
  |       |       - Thumbnail/video preview
  |       |       - Prompt text (expandable)
  |       |       - Select (thumbs up) / Reject (thumbs down)
  |       |       - Retry button (if failed)
  |       |
  |       +-- FeedbackInput (optional text area)
  |       |
  |       +-- RoundActions
  |           - "Generate next round" (if 2+ selected)
  |           - "Use as finalist" (if 1 selected)
  |           - "Go back" (rollback)
  |
  +-- [Stage: EXTRACTION]
  |   |
  |   +-- ExtractionReview
  |       |
  |       +-- WinningCombo (show winning image + video)
  |       |
  |       +-- PromptEditor
  |       |   - base_prompt (editable textarea, {slots} highlighted)
  |       |   - variation_prompt (editable textarea)
  |       |   - Slot examples display
  |       |
  |       +-- CreateTemplateForm
  |           - Template name
  |           - Platforms
  |           - Video template prompt
  |           - "Create Template" button
  |
  +-- [Stage: COMPLETED]
      |
      +-- CompletionSummary
          - Link to created Template project
          - Summary of exploration (rounds, selections)
```

### Key Screens

1. **ConceptInput** -- Initial form with concept textarea, name, model selectors. Lives in project creation flow or as first screen of DiscoverPage when `current_image_round == 0`.

2. **ImageRefinement / VideoRefinement** -- Main exploration screen. Card grid with selection UI. Polling for generation status. Round history in collapsible sections.

3. **ExtractionReview** -- Shows winning image+video, extracted prompts with editable fields, slot visualization, and "Create Template" form.

### State Management

- **Server state (React Query):** `useQuery(['discover', id])` for project data. Auto-refetch with `refetchInterval` when round is generating.
- **Local selection state (useState):** Selections tracked locally until submitted. `Record<number, 'selected' | 'rejected'>`.
- **No Zustand store needed** -- Discover state is simple enough for React Query + local state.

### Polling Strategy

When a round is in `generating` status:
```typescript
const { data } = useQuery(
  ['discover', id],
  () => discoverApi.get(id),
  {
    refetchInterval: (data) => {
      const activeRound = data?.rounds.find(r => r.status === 'generating');
      return activeRound ? 3000 : false; // Poll every 3s while generating
    }
  }
);
```

### Routes

```
/discover              -- List of discover projects (or inline in dashboard)
/discover/new          -- Create new discover project
/discover/:id          -- Main discover workflow page
```

---

## Error Handling

### FAL Failures

| Scenario | Handling |
|----------|----------|
| Single item fails | Mark item as `failed`, continue others. Show failed card with retry button. |
| All items in round fail | Mark round as `failed`. User can retry entire round. |
| Content policy rejection | Mark item as `failed` with clear error. No retry (different prompt needed). |
| Timeout | Mark as `failed`. User can retry. |

### LLM Failures

| Scenario | Handling |
|----------|----------|
| Prompt generation fails | Return error, don't create round. User retries "Generate round" action. |
| Invalid JSON from LLM | Retry once with validation error context (existing pattern from `generate_validated_json`). |
| Extraction fails | Return error, user can retry extraction. |

### Partial Results

- Round generation is item-by-item. Completed items are visible immediately (frontend polls).
- If some items fail, round still shows completed items. User can select from what's available.
- Retry endpoint allows re-generating only failed items.

### Rollback Safety

- Rollback deletes the last round's items and media files.
- Cannot rollback to before round 1.
- If rolling back from video stage, resets to image stage and clears finalist.

---

## Implementation Steps

### Phase 1: Backend Foundation (data model + basic API)

1. [ ] Create `backend/app/models/discover.py` with all 4 models
2. [ ] Update `backend/app/models/__init__.py` to export new models
3. [ ] Add `source_discover_id` to `TemplateSettings` model
4. [ ] Create Alembic migration for all new tables
5. [ ] Create `backend/app/schemas/discover.py` with all Pydantic schemas
6. [ ] Create `backend/app/api/discover.py` with router skeleton (all endpoints)
7. [ ] Register router in `backend/app/main.py`

### Phase 2: LLM Prompts + Service Core

8. [ ] Create `backend/app/services/prompts/discover.py` with all prompt templates
9. [ ] Create `backend/app/services/discover_service.py` with full service
10. [ ] Implement round generation (LLM prompt gen + FAL background task)
11. [ ] Implement selection submission
12. [ ] Implement stage advancement
13. [ ] Implement rollback
14. [ ] Implement extraction (LLM)
15. [ ] Implement template creation

### Phase 3: API Endpoints Implementation

16. [ ] Wire up all endpoint handlers to service methods
17. [ ] Add workspace access checks to all endpoints
18. [ ] Add retry endpoint for failed items

### Phase 4: Frontend Core

19. [ ] Add TypeScript types to `frontend/src/types/index.ts`
20. [ ] Add API client methods to `frontend/src/services/api.ts`
21. [ ] Create `DiscoverPage.tsx` with stage router
22. [ ] Create `ItemGrid` + `ItemCard` components (selection UI)
23. [ ] Create `RoundActions` + `FeedbackInput` components
24. [ ] Implement polling for generation status

### Phase 5: Frontend Screens

25. [ ] Create ConceptInput form (project creation)
26. [ ] Create ImageRefinement screen (round history + current round)
27. [ ] Create VideoRefinement screen
28. [ ] Create ExtractionReview screen (prompt editor + template creation form)
29. [ ] Create CompletionSummary screen
30. [ ] Add Discover to project creation flow / navigation

### Phase 6: Polish + Testing

31. [ ] Test full flow: concept -> image rounds -> video rounds -> extraction -> template
32. [ ] Test rollback
33. [ ] Test retry on failures
34. [ ] Test extraction editing
35. [ ] `pytest` passes
36. [ ] `npm run build` passes

### Dependencies

```
Phase 1 ──> Phase 2 ──> Phase 3 ──> Phase 4 ──> Phase 5 ──> Phase 6
                                        |
                                        └──> Phase 4 (can start frontend types/api early)
```

---

## Edge Cases

| Case | Handling |
|------|----------|
| User selects 0 items | Validation error: at least 1 selection required to proceed |
| User selects all items | Allowed, but narrowing will be less effective (LLM has no rejection signal) |
| All FAL generations fail in a round | Round marked as `failed`, user can retry or go back |
| LLM generates duplicate prompts | Deduplicate before creating items |
| User tries to advance with 3+ selections | Show UI guidance: "Select exactly 1 to advance, or generate another round to narrow down" |
| Rollback on round 1 | Blocked with error: "Cannot rollback the first round" |
| Create template without extraction | Blocked: extraction must exist |
| Concept too short/vague | LLM handles gracefully; 10-char minimum on concept |
| User refreshes mid-generation | Frontend resumes polling from current state (all state is server-side) |
| Video generation from failed image | Blocked: can only advance to video with completed finalist image |
| Extract without video finalist | Blocked: must call advance-extraction with finalist_video_item_id first |
| FAL URL expired for finalist image | advance_to_video re-downloads finalist to local storage as safeguard |
| Narrowing with 5+ rounds of history | Only last 30 rejected prompts sent to LLM to stay within context window |
| Concurrent round generation | Blocked: only 1 active (generating) round per project at a time |

---

## Testing

### Manual Tests

- [ ] Create discover project with concept
- [ ] Generate first image round (10 images)
- [ ] Select 3 images, reject 7, add feedback
- [ ] Generate second narrowing round
- [ ] Verify narrowed results match preferences
- [ ] Select 1 finalist, advance to videos
- [ ] Generate video variations from finalist
- [ ] Select winning video
- [ ] Extract template prompts
- [ ] Edit extracted prompts
- [ ] Create Template project from extraction
- [ ] Verify Template project has correct settings and `source_discover_id`
- [ ] Test rollback at image stage
- [ ] Test rollback at video stage (returns to images)
- [ ] Test retry on failed items
- [ ] Test archiving discover project

### Build Verification

- [ ] `cd backend && .venv/bin/pytest` passes
- [ ] `cd frontend && npm run build` passes

---

## Dependencies

- **Existing (reuse):** `OpenAIClient`, `FalClient`, `download_image`, `download_video`, `get_current_user`, `user_has_workspace_access`, `Project`, `TemplateSettings`, `VideoTemplate`
- **New:** No new external dependencies

---

## Open Questions

- [ ] How many items per round? Spec assumes ~10 for images, ~6 for videos. Tunable in future.
- [ ] Should video round support narrowing (multiple rounds) or just one round of variations? Spec supports multiple rounds.
- [ ] Should we store the full LLM narrowing analysis for debugging? Currently stored as part of round metadata.
- [ ] Media cleanup policy for archived discover projects -- when to delete generated images/videos?
