"""ApprovedGeneration model for publishing queue."""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, DateTime, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class ApprovedGeneration(Base):
    """
    Approved template generation ready for publishing.
    Created when moderator approves a TemplateGeneration.
    Used by ScheduledPublisher (T21) to publish videos.
    """
    __tablename__ = "approved_generations"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )
    template_generation_id = Column(
        Integer,
        ForeignKey("template_generations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True  # One approval per generation
    )

    # Queue position (FIFO ordering)
    position = Column(Integer, nullable=False)

    # When approved
    approved_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Publishing metadata for each platform
    # Format: {"instagram": {"title": "...", "description": "...", "hashtags": "..."}, ...}
    publishing_metadata = Column(JSON, nullable=True)

    # Publishing status
    # approved -> publishing -> published/partially_published/failed
    status = Column(String(30), nullable=False, default="approved")

    # Per-platform publish status
    # Format: {"instagram": "published", "tiktok": "failed"}
    platform_statuses = Column(JSON, nullable=True)

    # Retry tracking
    retry_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)

    # Scheduled slot that triggered this publish (e.g. 2026-02-10 18:00 UTC)
    scheduled_for = Column(DateTime, nullable=True)

    # When published (at least one platform succeeded)
    published_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="approved_generations")
    template_generation = relationship("TemplateGeneration", back_populates="approved_generation")

    __table_args__ = (
        Index('ix_approved_gen_project_status', 'project_id', 'status'),
        Index('ix_approved_gen_position', 'project_id', 'position'),
    )
