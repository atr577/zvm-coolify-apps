"""Pydantic schemas for Template project type."""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# --- Enums ---

class AspectRatioEnum(str, Enum):
    PORTRAIT = "9:16"
    LANDSCAPE = "16:9"
    SQUARE = "1:1"


class LLMModelEnum(str, Enum):
    GPT4O_MINI = "gpt-4o-mini"
    GPT4O = "gpt-4o"


class ImageModelEnum(str, Enum):
    NANO_BANANA = "fal-ai/nano-banana-pro"
    FLUX_PRO_ULTRA = "fal-ai/flux-pro/v1.1-ultra"
    FLUX_PRO = "fal-ai/flux-pro/v1.1"
    IDEOGRAM_V3 = "fal-ai/ideogram/v3"
    IMAGEN3 = "fal-ai/imagen3"


class VideoModelEnum(str, Enum):
    VEO3_FAST = "fal-ai/veo3/fast/image-to-video"
    VEO3 = "fal-ai/veo3/image-to-video"
    VEO31 = "fal-ai/veo3.1/reference-to-video"
    KLING_V21_STANDARD = "fal-ai/kling-video/v2.1/standard/image-to-video"
    KLING_V21_PRO = "fal-ai/kling-video/v2.1/pro/image-to-video"
    MINIMAX = "fal-ai/minimax/video-01"


class GenerationStatusEnum(str, Enum):
    PENDING = "pending"
    PREPROCESSING = "preprocessing"
    GENERATING_IMAGE = "generating_image"
    GENERATING_VIDEO = "generating_video"
    COMPLETED = "completed"
    FAILED = "failed"


# --- TemplateSettings Schemas ---

class TemplateSettingsBase(BaseModel):
    preprocessing_prompt: str
    image_prompt_template: str
    llm_model: LLMModelEnum = LLMModelEnum.GPT4O_MINI
    image_model: ImageModelEnum = ImageModelEnum.NANO_BANANA
    video_model: VideoModelEnum = VideoModelEnum.VEO3_FAST
    image_aspect_ratio: AspectRatioEnum = AspectRatioEnum.PORTRAIT
    video_duration: str = "5"  # Kling: "5"/"10", Veo: "4s"/"6s"/"8s"


class TemplateSettingsCreate(TemplateSettingsBase):
    pass


class TemplateSettingsUpdate(BaseModel):
    preprocessing_prompt: Optional[str] = None
    image_prompt_template: Optional[str] = None
    llm_model: Optional[LLMModelEnum] = None
    image_model: Optional[ImageModelEnum] = None
    video_model: Optional[VideoModelEnum] = None
    image_aspect_ratio: Optional[AspectRatioEnum] = None
    video_duration: Optional[str] = None
    variant_generation_prompt: Optional[str] = None


class TemplateSettingsResponse(BaseModel):
    id: int
    project_id: int
    preprocessing_prompt: str
    image_prompt_template: str
    llm_model: str
    image_model: str
    video_model: str
    image_aspect_ratio: str
    video_duration: str
    variant_generation_prompt: Optional[str] = None
    csv_columns: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- VideoTemplate Schemas ---

class VideoTemplateBase(BaseModel):
    name: str = Field(..., max_length=100)
    prompt: str
    is_default: bool = False


class VideoTemplateCreate(VideoTemplateBase):
    pass


class VideoTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    prompt: Optional[str] = None
    is_default: Optional[bool] = None


class VideoTemplateResponse(BaseModel):
    id: int
    project_id: int
    name: str
    prompt: str
    is_default: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Variant Schemas ---

class VariantBase(BaseModel):
    row_number: int
    data: Dict[str, Any]


class VariantCreate(VariantBase):
    pass


class VariantUpdate(BaseModel):
    data: Optional[Dict[str, Any]] = None


class VariantResponse(BaseModel):
    id: int
    project_id: int
    row_number: int
    data: Dict[str, Any]
    usage_count: int
    last_used_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VariantListResponse(BaseModel):
    variants: List[VariantResponse]
    total: int
    csv_columns: Optional[List[str]] = None


# --- Variant Generation Schemas ---

class GenerateVariantPromptResponse(BaseModel):
    prompt: str


class GenerateVariantsRequest(BaseModel):
    count: int = Field(ge=1, le=50, default=10)


class GenerateVariantsPreviewResponse(BaseModel):
    variants: List[Dict[str, Any]]
    columns: List[str]


class SaveGeneratedVariantsRequest(BaseModel):
    variants: List[Dict[str, Any]]


class SaveGeneratedVariantsResponse(BaseModel):
    variants_created: int
    duplicates_skipped: int


# --- CSV Upload Schema ---

class CSVUploadResponse(BaseModel):
    variants_created: int
    csv_columns: List[str]
    preview: List[Dict[str, Any]]  # First 5 rows


# --- Generation Schemas ---

class GenerateRequest(BaseModel):
    variant_id: Optional[int] = None  # null = auto-select least used
    video_template_id: Optional[int] = None  # null = use default


class BatchModeEnum(str, Enum):
    ALL_UNUSED = "all_unused"
    LEAST_USED = "least_used"
    SPECIFIC = "specific"


class BatchGenerateRequest(BaseModel):
    mode: BatchModeEnum
    count: Optional[int] = Field(None, ge=1, le=100)  # for least_used mode
    variant_ids: Optional[List[int]] = None  # for specific mode
    video_template_id: Optional[int] = None  # null = use default


class GenerationResponse(BaseModel):
    id: int
    project_id: int
    variant_id: Optional[int] = None
    video_template_id: Optional[int] = None
    batch_id: Optional[str] = None

    # Models used (snapshot from generation time)
    llm_model: str
    image_model: str
    video_model: str

    # Results
    preprocessing_result: Optional[Dict[str, Any]] = None
    image_prompt: Optional[str] = None
    video_prompt: Optional[str] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    image_path: Optional[str] = None
    video_path: Optional[str] = None

    # Status
    status: GenerationStatusEnum
    failed_at_step: Optional[str] = None
    error_message: Optional[str] = None

    # Variant data (enriched from variant relationship in endpoint)
    variant_data: Optional[Dict[str, Any]] = None

    # Timestamps
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class GenerationListResponse(BaseModel):
    generations: List[GenerationResponse]
    total: int


class BatchGenerateResponse(BaseModel):
    batch_id: str
    count: int
    generations: List[GenerationResponse]


# --- Template Project Creation (extended from base project) ---

class TemplateProjectCreate(BaseModel):
    """Schema for creating a template project with all required fields."""
    name: str
    description: Optional[str] = None

    # TemplateSettings fields (required)
    preprocessing_prompt: str
    image_prompt_template: str
    llm_model: LLMModelEnum = LLMModelEnum.GPT4O_MINI
    image_model: ImageModelEnum = ImageModelEnum.NANO_BANANA
    video_model: VideoModelEnum = VideoModelEnum.VEO3_FAST
    image_aspect_ratio: AspectRatioEnum = AspectRatioEnum.PORTRAIT
    video_duration: str = "5"

    # First VideoTemplate (required)
    video_template_name: str = Field(..., max_length=100)
    video_template_prompt: str

    # Optional project settings
    platforms: List[str] = ["youtube"]
    workspace_id: Optional[int] = None
    social_account_ids: Optional[List[int]] = None
