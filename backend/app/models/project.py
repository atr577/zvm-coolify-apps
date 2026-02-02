from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey, Table, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base


# Association table for Project <-> SocialAccount many-to-many
project_social_accounts = Table(
    'project_social_accounts',
    Base.metadata,
    Column('project_id', Integer, ForeignKey('projects.id', ondelete='CASCADE'), primary_key=True),
    Column('social_account_id', Integer, ForeignKey('social_accounts.id', ondelete='CASCADE'), primary_key=True),
    Column('created_at', DateTime, default=datetime.utcnow)
)


class Project(Base):
    """
    Project = Template/Container for multiple videos
    Stores shared configuration and story template
    Принадлежит workspace и может использовать SocialAccounts для публикации
    """
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Templates
    story_template = Column(Text, nullable=False)  # Image prompt template with {placeholders}
    motion_template = Column(Text, nullable=True)  # Motion prompt template with {placeholders} (for remix)

    # Settings
    platforms = Column(JSON, nullable=False)  # ["instagram", "tiktok", "youtube"]
    duration = Column(Integer, nullable=False)  # 5, 10, 15 seconds
    aspect_ratio = Column(String(10), nullable=False, default="9:16")  # 9:16 (vertical), 16:9 (horizontal), 1:1 (square)

    # Audio mode: none, scene, music, voiceover, auto
    audio_mode = Column(String(20), nullable=False, default="auto")

    # Audio provider: kling (default), ai_music (requires OPENAI_API_KEY)
    audio_provider = Column(String(20), nullable=True)  # None = use default for audio_mode

    # Project type: discover (full workflow) or remix (skip to image generation)
    project_type = Column(String(20), nullable=False, default="discover")

    # Remix-specific fields
    source_video_ids = Column(JSON, nullable=True)  # List[int] - Discover videos used as basis
    scenario_template = Column(JSON, nullable=True)  # Template with {placeholders} for video motion
    placeholders = Column(JSON, nullable=True)  # List[str] - ["dress_color", "car_model"]
    placeholder_suggestions = Column(JSON, nullable=True)  # {dress_color: ["red", "blue"], ...}

    # Workflow control: pause after image generation for approval (saves tokens during dev)
    require_image_approval = Column(Integer, nullable=False, default=0)  # 0=False, 1=True (SQLite boolean)

    # Timezone for scheduled publishing (IANA timezone, e.g., "Europe/Moscow")
    timezone = Column(String(50), nullable=False, default="UTC")

    # System prompts for each workflow step (optional overrides)
    # JSON: {"story": "...", "description": "...", "prompt": "...", "scenario": "...", "adaptation": "..."}
    system_prompts = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    workspace = relationship("Workspace", back_populates="projects")
    videos = relationship("Video", back_populates="project", cascade="all, delete-orphan")
    social_accounts = relationship(
        "SocialAccount",
        secondary=project_social_accounts,
        back_populates="projects"
    )

    # Template project type relationships
    template_settings = relationship(
        "TemplateSettings",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan"
    )
    video_templates = relationship(
        "VideoTemplate",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    variants = relationship(
        "Variant",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    template_generations = relationship(
        "TemplateGeneration",
        back_populates="project",
        cascade="all, delete-orphan"
    )

    # Moderation relationships
    approved_generations = relationship(
        "ApprovedGeneration",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    rejection_archive = relationship(
        "RejectionArchive",
        back_populates="project",
        cascade="all, delete-orphan"
    )

    # Publishing config (1:1 for scheduled publishing)
    publishing_config = relationship(
        "PublishingConfig",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}', workspace_id={self.workspace_id})>"


class PublishResult(Base):
    """
    Tracks publishing results for each platform
    """
    __tablename__ = "publish_results"
    __table_args__ = (
        # Index for Video.is_published hybrid_property query
        Index('ix_publish_results_video_status', 'video_id', 'status'),
    )

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(String(50), nullable=False)  # instagram, tiktok, youtube

    # Status: pending, publishing, published, failed
    status = Column(String(50), default="pending")

    # Result data
    post_id = Column(String(255), nullable=True)  # ID on the platform
    post_url = Column(String(512), nullable=True)  # URL to the published post
    error_message = Column(Text, nullable=True)

    # Metadata sent
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    hashtags = Column(JSON, nullable=True)

    # Timestamps
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    video = relationship("Video", back_populates="publish_results")

    def __repr__(self):
        return f"<PublishResult(id={self.id}, video_id={self.video_id}, platform='{self.platform}', status='{self.status}')>"
