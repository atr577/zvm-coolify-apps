"""TemplateSettings model for Template project type."""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, DateTime, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.base import Base


class AspectRatio(str, enum.Enum):
    """Supported aspect ratios for image generation."""
    PORTRAIT = "9:16"
    LANDSCAPE = "16:9"
    SQUARE = "1:1"


class LLMModel(str, enum.Enum):
    """Supported LLM models."""
    GPT4O_MINI = "gpt-4o-mini"
    GPT4O = "gpt-4o"


class ImageModel(str, enum.Enum):
    """Supported image generation models."""
    NANO_BANANA = "fal-ai/nano-banana-pro"
    FLUX_PRO_ULTRA = "fal-ai/flux-pro/v1.1-ultra"
    FLUX_PRO = "fal-ai/flux-pro/v1.1"
    IDEOGRAM_V3 = "fal-ai/ideogram/v3"
    IMAGEN3 = "fal-ai/imagen3"


class VideoModel(str, enum.Enum):
    """Supported video generation models (image-to-video, no audio)."""
    VEO3_FAST = "fal-ai/veo3/fast/image-to-video"
    VEO3 = "fal-ai/veo3/image-to-video"
    VEO31 = "fal-ai/veo3.1/reference-to-video"
    KLING_V21_STANDARD = "fal-ai/kling-video/v2.1/standard/image-to-video"
    KLING_V21_PRO = "fal-ai/kling-video/v2.1/pro/image-to-video"
    MINIMAX = "fal-ai/minimax/video-01"


class TemplateSettings(Base):
    """Per-project settings for Template project type."""
    __tablename__ = "template_settings"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )

    # LLM Prompts (required)
    preprocessing_prompt = Column(Text, nullable=False)
    preprocessing_system_prompt = Column(Text, nullable=True)  # System prompt for preprocessing LLM call
    image_prompt_template = Column(Text, nullable=False)

    # LLM Model
    llm_model = Column(String(50), nullable=False, default=LLMModel.GPT4O_MINI.value)

    # Generation Models
    image_model = Column(String(100), nullable=False, default=ImageModel.NANO_BANANA.value)
    video_model = Column(String(100), nullable=False, default=VideoModel.VEO3_FAST.value)

    # Image Settings
    image_aspect_ratio = Column(String(10), nullable=False, default=AspectRatio.PORTRAIT.value)

    # Video Settings
    video_duration = Column(String(10), nullable=False, default="5")  # Kling: "5"/"10", Veo: "4s"/"6s"/"8s"

    # CSV Metadata (detected on import)
    csv_columns = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="template_settings")
