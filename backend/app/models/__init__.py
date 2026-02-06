from app.models.user import User, SocialAccount, UserRole, SocialPlatform
from app.models.project import Project, project_social_accounts, PublishResult
from app.models.video import Video, StepType, WorkflowStatus
from app.models.step_history import StepHistory, STEP_TO_VIDEO_FIELD, DISCOVER_STEPS, REMIX_STEPS, STEP_DEPENDENCIES
from app.models.task_tracker import TaskTracker, TaskStatus

# Template project type models
from app.models.template_settings import (
    TemplateSettings,
    AspectRatio,
    LLMModel,
    ImageModel,
    VideoModel,
)
from app.models.video_template import VideoTemplate
from app.models.variant import Variant
from app.models.template_generation import TemplateGeneration, GenerationStatus
from app.models.approved_generation import ApprovedGeneration
from app.models.rejection_archive import RejectionArchive
from app.models.publishing_config import PublishingConfig

# Discover workflow models
from app.models.discover import (
    DiscoverProject,
    DiscoverRound,
    DiscoverItem,
    DiscoverExtraction,
    DiscoverAudioVariant,
    DiscoverStage,
    DiscoverStatus,
    RoundType,
    RoundStatus,
    ItemStatus,
    SelectionStatus,
)

# Audio library
from app.models.audio_library import AudioLibrary

__all__ = [
    "User",
    "SocialAccount",
    "UserRole",
    "SocialPlatform",
    "Project",
    "project_social_accounts",
    "PublishResult",
    "Video",
    "StepType",
    "WorkflowStatus",
    "StepHistory",
    "STEP_TO_VIDEO_FIELD",
    "DISCOVER_STEPS",
    "REMIX_STEPS",
    "STEP_DEPENDENCIES",
    "TaskTracker",
    "TaskStatus",
    # Template project type
    "TemplateSettings",
    "AspectRatio",
    "LLMModel",
    "ImageModel",
    "VideoModel",
    "VideoTemplate",
    "Variant",
    "TemplateGeneration",
    "GenerationStatus",
    "ApprovedGeneration",
    "RejectionArchive",
    "PublishingConfig",
    # Discover workflow
    "DiscoverProject",
    "DiscoverRound",
    "DiscoverItem",
    "DiscoverExtraction",
    "DiscoverAudioVariant",
    "DiscoverStage",
    "DiscoverStatus",
    "RoundType",
    "RoundStatus",
    "ItemStatus",
    "SelectionStatus",
    # Audio library
    "AudioLibrary",
]
