"""TemplateGeneration model for Template project type."""

from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, JSON, DateTime, Enum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.base import Base


class GenerationStatus(str, enum.Enum):
    """Status of a template generation run."""
    PENDING = "pending"
    PREPROCESSING = "preprocessing"
    GENERATING_IMAGE = "generating_image"
    GENERATING_VIDEO = "generating_video"
    GENERATING_AUDIO = "generating_audio"
    MERGING_AUDIO = "merging_audio"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TemplateGeneration(Base):
    """Single generation run for Template project type."""
    __tablename__ = "template_generations"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )
    variant_id = Column(
        Integer,
        ForeignKey("variants.id", ondelete="SET NULL"),
        nullable=True
    )
    video_template_id = Column(
        Integer,
        ForeignKey("video_templates.id", ondelete="SET NULL"),
        nullable=True
    )

    # Models used (snapshot for display on cards)
    llm_model = Column(String(50), nullable=False)
    image_model = Column(String(100), nullable=False)
    video_model = Column(String(100), nullable=False)

    # Pipeline results
    preprocessing_result = Column(JSON, nullable=True)
    image_prompt = Column(Text, nullable=True)
    video_prompt = Column(Text, nullable=True)  # Copy from VideoTemplate at generation time
    image_url = Column(String(500), nullable=True)
    video_url = Column(String(500), nullable=True)

    # Local media paths (downloaded from fal.ai)
    image_path = Column(String(255), nullable=True)
    video_path = Column(String(255), nullable=True)
    audio_path = Column(String(255), nullable=True)  # Trimmed hook audio
    video_with_audio_path = Column(String(255), nullable=True)  # Final merged video

    # fal.ai request IDs (for resume/retry)
    fal_image_request_id = Column(String(100), nullable=True)
    fal_video_request_id = Column(String(100), nullable=True)

    # Status (supports retry from failed step)
    status = Column(String(20), nullable=False, default=GenerationStatus.PENDING.value)
    failed_at_step = Column(String(20), nullable=True)  # preprocessing, image_prompt, image, video
    error_message = Column(Text, nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)

    # Pre-generated publishing metadata (cached at completion)
    publishing_metadata = Column(JSON, nullable=True)

    # Batch tracking
    batch_id = Column(String(36), nullable=True, index=True)

    # Moderation flags
    regenerated = Column(Boolean, default=False, nullable=False)  # True if this was replaced by regeneration

    # Cost tracking (populated later)
    llm_tokens_used = Column(Integer, nullable=True)
    image_cost = Column(Float, nullable=True)
    video_cost = Column(Float, nullable=True)

    # User ratings (0-5 scale)
    image_rating = Column(Integer, nullable=True)
    image_comment = Column(Text, nullable=True)
    video_rating = Column(Integer, nullable=True)
    video_comment = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    project = relationship("Project", back_populates="template_generations")
    variant = relationship("Variant", back_populates="generations")
    video_template = relationship("VideoTemplate", back_populates="generations")

    # Moderation relationships (one-to-one, either approved or rejected)
    approved_generation = relationship("ApprovedGeneration", back_populates="template_generation", uselist=False)
    rejection = relationship("RejectionArchive", back_populates="template_generation", uselist=False)
