from sqlalchemy import Column, Integer, Text, JSON, Boolean, Float, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base
from app.models.video import StepType, WorkflowStatus


class WorkflowStep(Base):
    """
    WorkflowStep = Individual step in video generation workflow
    Now linked to Video instead of Project
    """
    __tablename__ = "workflow_steps"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)

    step_type = Column(SQLEnum(StepType), nullable=False)
    status = Column(SQLEnum(WorkflowStatus), default=WorkflowStatus.PENDING)
    content = Column(JSON, nullable=True)

    # User feedback
    user_approved = Column(Boolean, nullable=True)
    user_feedback = Column(Text, nullable=True)

    # Validation
    validation_attempts = Column(Integer, default=0)
    max_validation_attempts = Column(Integer, default=3)

    # Debug info
    prompt_used = Column(Text, nullable=True)
    generation_time_seconds = Column(Float, nullable=True)

    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    video = relationship("Video", back_populates="workflow_steps")
    validations = relationship("ValidationResult", back_populates="step", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<WorkflowStep(id={self.id}, video_id={self.video_id}, step_type={self.step_type}, status={self.status})>"
