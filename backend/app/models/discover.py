"""Discover workflow models — iterative exploration of new video formats."""

from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, JSON, DateTime, UniqueConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.base import Base


# --- Enums ---

class DiscoverStage(str, enum.Enum):
    """Current stage of discovery workflow."""
    IMAGES = "images"
    VIDEOS = "videos"
    AUDIO = "audio"
    EXTRACTION = "extraction"
    COMPLETED = "completed"


class DiscoverStatus(str, enum.Enum):
    """Project-level status."""
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class RoundType(str, enum.Enum):
    """Type of exploration round."""
    IMAGE = "image"
    VIDEO = "video"


class RoundStatus(str, enum.Enum):
    """Round generation status."""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class ItemStatus(str, enum.Enum):
    """Status of individual generated item."""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class SelectionStatus(str, enum.Enum):
    """User selection status for an item."""
    UNREVIEWED = "unreviewed"
    SELECTED = "selected"
    REJECTED = "rejected"


# --- Models ---

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
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # User's creative concept
    concept = Column(Text, nullable=False)
    name = Column(String(255), nullable=False)

    # Stage tracking
    stage = Column(String(20), nullable=False, default=DiscoverStage.IMAGES.value)
    status = Column(String(20), nullable=False, default=DiscoverStatus.ACTIVE.value)

    # Current round number per stage
    current_image_round = Column(Integer, nullable=False, default=0)
    current_video_round = Column(Integer, nullable=False, default=0)

    # Generation settings
    image_model = Column(String(100), nullable=False, default="fal-ai/flux-pro/v1.1")
    video_model = Column(String(100), nullable=False, default="fal-ai/veo3/fast/image-to-video")
    image_aspect_ratio = Column(String(10), nullable=False, default="9:16")
    video_duration = Column(String(10), nullable=False, default="6s")

    # Finalist references (FKs use use_alter for circular dependency)
    finalist_image_item_id = Column(
        Integer,
        ForeignKey("discover_items.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )
    finalist_video_item_id = Column(
        Integer,
        ForeignKey("discover_items.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )

    # Audio selection
    audio_mode = Column(String(20), nullable=True)  # 'sound_fx' | 'music' | 'library' | 'none'
    selected_audio_variant_id = Column(
        Integer,
        ForeignKey("discover_audio_variants.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )

    # Merged video (video + confirmed audio)
    merged_video_path = Column(String(500), nullable=True)

    # Link to created Template project
    created_project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
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
        order_by="DiscoverRound.round_number",
    )
    extraction = relationship(
        "DiscoverExtraction",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan",
    )
    refinement = relationship(
        "DiscoverRefinement",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan",
    )
    audio_variants = relationship(
        "DiscoverAudioVariant",
        back_populates="project",
        cascade="all, delete-orphan",
        foreign_keys="DiscoverAudioVariant.project_id",
    )
    created_project = relationship("Project")


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
        index=True,
    )

    round_number = Column(Integer, nullable=False)
    round_type = Column(String(10), nullable=False)  # "image" or "video"

    # Generation status
    status = Column(String(20), nullable=False, default=RoundStatus.PENDING.value)
    error_message = Column(Text, nullable=True)

    # LLM prompts used (stored for auditability)
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
        order_by="DiscoverItem.position",
    )

    __table_args__ = (
        UniqueConstraint(
            "project_id", "round_number", "round_type",
            name="uq_discover_round",
        ),
    )


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
        index=True,
    )

    position = Column(Integer, nullable=False)  # Order within round (1..N)

    # The prompt used for this item
    prompt = Column(Text, nullable=False)

    # For video items: source image item
    source_image_item_id = Column(
        Integer,
        ForeignKey("discover_items.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Generation
    status = Column(String(20), nullable=False, default=ItemStatus.PENDING.value)
    fal_request_id = Column(String(100), nullable=True)
    result_url = Column(String(500), nullable=True)  # FAL CDN URL (public, used for downstream)
    local_path = Column(String(255), nullable=True)   # Downloaded local path (backup)
    error_message = Column(Text, nullable=True)

    # User selection
    selection = Column(
        String(20),
        nullable=False,
        default=SelectionStatus.UNREVIEWED.value,
    )

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    round = relationship("DiscoverRound", back_populates="items")
    source_image_item = relationship(
        "DiscoverItem",
        remote_side="DiscoverItem.id",
        foreign_keys=[source_image_item_id],
    )


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
        nullable=False,
    )

    # Winning prompts (snapshot from items)
    winning_image_prompt = Column(Text, nullable=False)
    winning_video_prompt = Column(Text, nullable=True)

    # LLM-extracted template prompts
    base_prompt = Column(Text, nullable=False)          # Image template with {slots}
    variation_prompt = Column(Text, nullable=False)
    video_template_prompt = Column(Text, nullable=True) # Video template with {slots}
    slot_names = Column(JSON, nullable=True)            # ["object", "angle"]
    slot_examples = Column(JSON, nullable=True)         # {"object": ["apple", "phone"]}

    # User-edited versions (null until user edits)
    edited_base_prompt = Column(Text, nullable=True)
    edited_variation_prompt = Column(Text, nullable=True)
    edited_video_template_prompt = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("DiscoverProject", back_populates="extraction")


class DiscoverRefinement(Base):
    """
    Prompt refinement data for a Discover project.
    Stores block-by-block analysis and the compiled refined prompt.
    One refinement per project (unique on project_id).
    """
    __tablename__ = "discover_refinements"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("discover_projects.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Original concept (snapshot from project)
    original_concept = Column(Text, nullable=False)

    # LLM-determined relevant blocks
    relevant_blocks = Column(JSON, nullable=False)  # ["subject", "action", ...]

    # Block data (JSON dict: block_name → {value, status, source, question, options})
    blocks = Column(JSON, nullable=False, default=dict)

    # Compiled prompt (English, assembled from blocks by LLM)
    refined_prompt = Column(Text, nullable=True)

    # Current completeness score (0-100)
    score = Column(Integer, nullable=False, default=0)

    # LLM audit trail
    analysis_prompt_used = Column(Text, nullable=True)
    analysis_response = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("DiscoverProject", back_populates="refinement")


class DiscoverAudioVariant(Base):
    """Audio variant generated during Discover audio selection step."""
    __tablename__ = "discover_audio_variants"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("discover_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Audio type
    audio_type = Column(String(20), nullable=False)  # 'sfx' | 'music' | 'library'

    # Generation details
    prompt = Column(Text, nullable=True)
    prompt_mode = Column(String(10), nullable=False, default="manual")  # 'manual' | 'auto'

    # Result — full generated audio
    status = Column(String(20), nullable=False, default="pending")  # pending|generating|completed|failed
    file_path = Column(String(500), nullable=True)
    file_url = Column(String(500), nullable=True)
    full_duration_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)

    # Hook detection (for music/library — auto-detected segments)
    detected_hooks = Column(JSON, nullable=True)  # [{start_ms, end_ms, energy, type}]

    # Selected hook (user picks one segment)
    hook_start_ms = Column(Integer, nullable=True)
    hook_end_ms = Column(Integer, nullable=True)
    trimmed_file_path = Column(String(500), nullable=True)

    # Final duration (after hook trim; for SFX = full_duration_ms)
    duration_ms = Column(Integer, nullable=True)

    # Library reference (if audio_type='library')
    library_item_id = Column(
        Integer,
        ForeignKey("audio_library.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    project = relationship(
        "DiscoverProject",
        back_populates="audio_variants",
        foreign_keys=[project_id],
    )
