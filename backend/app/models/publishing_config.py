"""PublishingConfig model for scheduled publishing."""

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class PublishingConfig(Base):
    """
    Publishing configuration for Template projects.
    1:1 relationship with Project.
    Defines schedule rules (days, time) for automatic publishing.
    """
    __tablename__ = "publishing_configs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )

    # Schedule enabled
    enabled = Column(Boolean, nullable=False, default=False)

    # Publishing paused (temporary halt without disabling config)
    is_paused = Column(Boolean, nullable=False, default=False)

    # Days of week: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    days = Column(JSON, nullable=False, default=list)

    # Preferred times for publishing (list of HH:MM format strings)
    # Example: ["09:00", "18:00"] for twice a day
    preferred_times = Column(JSON, nullable=False, default=list)

    # How many days ahead to show in schedule view
    depth_days = Column(Integer, nullable=False, default=7)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="publishing_config")

    def __repr__(self):
        return f"<PublishingConfig(project_id={self.project_id}, enabled={self.enabled}, days={self.days})>"
