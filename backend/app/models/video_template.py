"""VideoTemplate model for Template project type."""

from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class VideoTemplate(Base):
    """Video prompt template - can have multiple per project."""
    __tablename__ = "video_templates"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )

    name = Column(String(100), nullable=False)
    prompt = Column(Text, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)  # Soft delete

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="video_templates")
    generations = relationship("TemplateGeneration", back_populates="video_template")
