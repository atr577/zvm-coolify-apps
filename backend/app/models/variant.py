"""Variant model for Template project type."""

from sqlalchemy import Column, Integer, ForeignKey, JSON, DateTime, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class Variant(Base):
    """Single variant row from CSV - arbitrary structure."""
    __tablename__ = "variants"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )

    row_number = Column(Integer, nullable=False)
    data = Column(JSON, nullable=False)  # Arbitrary columns: {"Место": "...", "Авто": "..."}

    # Usage tracking
    usage_count = Column(Integer, default=0, nullable=False)
    last_used_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="variants")
    generations = relationship("TemplateGeneration", back_populates="variant")

    # Index for "pick least used" query
    __table_args__ = (
        Index("ix_variants_project_usage", "project_id", "usage_count"),
    )
