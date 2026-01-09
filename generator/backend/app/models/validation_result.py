from sqlalchemy import Column, Integer, Float, JSON, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base
import enum


class ValidationStatus(str, enum.Enum):
    """Validation result status"""
    PASS = "pass"
    PASS_WITH_WARNINGS = "pass_with_warnings"
    FAIL = "fail"


class ValidationResult(Base):
    """
    ValidationResult = AI validation result for a workflow step
    """
    __tablename__ = "validation_results"

    id = Column(Integer, primary_key=True, index=True)
    step_id = Column(Integer, ForeignKey("workflow_steps.id", ondelete="CASCADE"), nullable=False, index=True)

    status = Column(SQLEnum(ValidationStatus), nullable=False)
    score = Column(Float, nullable=True)  # 0-100

    criteria_results = Column(JSON, nullable=True)
    warnings = Column(JSON, nullable=True)
    errors = Column(JSON, nullable=True)
    recommendations = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    step = relationship("WorkflowStep", back_populates="validations")

    def __repr__(self):
        return f"<ValidationResult(id={self.id}, step_id={self.step_id}, status={self.status}, score={self.score})>"
