"""RejectionArchive model for rejected template generations."""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class RejectionArchive(Base):
    """
    Archive of rejected template generations.
    Created when moderator rejects a TemplateGeneration.
    """
    __tablename__ = "rejection_archive"

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
        unique=True  # One rejection per generation
    )

    # Rejection details
    reason = Column(String(255), nullable=False)  # Required reason
    comment = Column(Text, nullable=True)  # Optional comment

    # Who rejected
    rejected_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    rejected_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="rejection_archive")
    template_generation = relationship("TemplateGeneration", back_populates="rejection")
    rejected_by_user = relationship("User")

    __table_args__ = (
        Index('ix_rejection_project', 'project_id'),
    )
