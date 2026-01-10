from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, Text, DateTime, Enum as SQLEnum, JSON, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base
from enum import Enum


class AttemptStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class StepAttempt(Base):
    """
    StepAttempt = One generation attempt for a workflow step.
    Can have multiple variants per attempt.
    """
    __tablename__ = "step_attempts"

    id = Column(Integer, primary_key=True, index=True)
    step_id = Column(Integer, ForeignKey("workflow_steps.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_number = Column(Integer, default=1)
    status = Column(SQLEnum(AttemptStatus), default=AttemptStatus.PENDING)
    parent_variant_id = Column(Integer, ForeignKey("variants.id", use_alter=True), nullable=True)
    feedback = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    step = relationship("WorkflowStep", back_populates="attempts")
    variants = relationship("Variant", back_populates="attempt", foreign_keys="Variant.attempt_id")
    parent_variant = relationship("Variant", foreign_keys=[parent_variant_id], post_update=True)

    def __repr__(self):
        return f"<StepAttempt(id={self.id}, step_id={self.step_id}, attempt={self.attempt_number}, status={self.status})>"


class Variant(Base):
    """
    Variant = One generated variant within an attempt.
    User can select one variant per step.
    """
    __tablename__ = "variants"

    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("step_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    variant_number = Column(Integer, default=1)
    content = Column(JSON, nullable=False)
    is_selected = Column(Boolean, default=False)

    # Relationships
    attempt = relationship("StepAttempt", back_populates="variants", foreign_keys=[attempt_id])

    def __repr__(self):
        return f"<Variant(id={self.id}, attempt_id={self.attempt_id}, variant={self.variant_number}, selected={self.is_selected})>"
