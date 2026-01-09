from sqlalchemy import Column, Integer, String, Text, JSON, Boolean, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base
import enum


class StepType(str, enum.Enum):
    """Workflow step types"""
    STORY = "story"
    DESCRIPTION = "description"
    PROMPT = "prompt"
    IMAGE = "image"
    SCENARIO = "scenario"
    VIDEO = "video"
    AUDIO = "audio"  # Kling Sound - adds audio to video
    ADAPTATION = "adaptation"
    PUBLISHING = "publishing"


class WorkflowStatus(str, enum.Enum):
    """Workflow status types"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VALIDATING = "validating"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"
    VALIDATION_FAILED = "validation_failed"


class WorkflowMode(str, enum.Enum):
    """Workflow mode - manual (with checkpoints) or auto (runs all steps)"""
    MANUAL = "MANUAL"
    AUTO = "AUTO"


class Video(Base):
    """
    Video = Individual clip/reel with specific content
    Contains all workflow data for generating this specific video
    """
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String(255), nullable=False)

    # Workflow mode: manual (with checkpoints) or auto (runs all steps automatically)
    workflow_mode = Column(SQLEnum(WorkflowMode), default=WorkflowMode.AUTO, index=True)

    # AI-generated content variables (from 10 variants selection)
    content_variables = Column(JSON, nullable=True)

    # Workflow data (all 9 steps)
    story_data = Column(JSON, nullable=True)
    description_data = Column(JSON, nullable=True)
    prompt_data = Column(JSON, nullable=True)  # Structured prompt with main_prompt, negative_prompt, etc.
    image_prompt = Column(Text, nullable=True)  # Deprecated: use prompt_data instead
    image_url = Column(Text, nullable=True)
    scenario_data = Column(JSON, nullable=True)
    video_url = Column(Text, nullable=True)  # Silent video URL
    video_task_id = Column(String(255), nullable=True)  # KLING task ID for audio generation
    audio_variants = Column(JSON, nullable=True)  # List of 4 video URLs with different audio
    video_with_audio_url = Column(Text, nullable=True)  # Selected video with audio
    adaptation_data = Column(JSON, nullable=True)  # Deprecated: use publishing_meta
    publishing_meta = Column(JSON, nullable=True)  # {title, description, hashtags} per platform

    # State
    current_step = Column(SQLEnum(StepType), default=StepType.STORY)
    status = Column(SQLEnum(WorkflowStatus), default=WorkflowStatus.PENDING)

    # Author's subjective rating before posting (1-5)
    author_rating = Column(Integer, nullable=True)  # 1=низкий потенциал, 5=вирусный хит

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="videos")
    workflow_steps = relationship("WorkflowStep", back_populates="video", cascade="all, delete-orphan")
    publish_results = relationship("PublishResult", back_populates="video", cascade="all, delete-orphan")
    metrics = relationship("VideoMetrics", back_populates="video", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Video(id={self.id}, title='{self.title}', workflow_mode={self.workflow_mode})>"


class MetricsPeriod(str, enum.Enum):
    """Time periods for metrics snapshots"""
    MINUTES_30 = "30m"
    HOURS_6 = "6h"
    HOURS_24 = "24h"
    DAYS_7 = "7d"


class VideoMetrics(Base):
    """
    Performance metrics snapshot for a video at a specific time period.
    Tracks views, likes, comments, shares for each platform.
    """
    __tablename__ = "video_metrics"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)

    # Which platform and time period
    platform = Column(String(50), nullable=False)  # instagram, tiktok, youtube
    period = Column(SQLEnum(MetricsPeriod), nullable=False)  # 30m, 6h, 24h, 7d

    # Metrics
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)

    # Calculated engagement rate (likes + comments + shares) / views * 100
    engagement_rate = Column(Integer, nullable=True)  # stored as percentage * 100 (e.g., 5.5% = 550)

    # When this snapshot was recorded
    recorded_at = Column(DateTime, default=datetime.utcnow)

    # Was this auto-fetched or manually entered
    is_manual = Column(Boolean, default=True)

    # Relationships
    video = relationship("Video", back_populates="metrics")

    def __repr__(self):
        return f"<VideoMetrics(video_id={self.video_id}, platform='{self.platform}', period='{self.period.value}')>"
