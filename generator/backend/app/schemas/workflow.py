from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class GenerateStoryRequest(BaseModel):
    video_id: int
    theme: Optional[str] = None  # Тема/ниша: авто, мода, lifestyle, tech и т.д.
    target_audience: Optional[str] = None  # Целевая аудитория
    mood: Optional[str] = None  # Настроение: драматично, весело, мотивационно, эпично
    key_elements: Optional[str] = None  # Обязательные элементы
    duration: int = Field(default=5, ge=5, le=10)  # Длительность видео
    platforms: Optional[List[str]] = None  # Целевые платформы
    additional_notes: Optional[str] = None  # Дополнительные указания
    content_variables: Optional[Dict[str, Any]] = None  # Переменные контента (animal, environment, etc.)


class GenerateDescriptionRequest(BaseModel):
    video_id: int
    story_data: Dict[str, Any]  # Данные сюжета из предыдущего этапа


class GeneratePromptRequest(BaseModel):
    video_id: int
    description_data: Dict[str, Any]  # Данные описания


class GenerateImageRequest(BaseModel):
    video_id: int
    prompt: Optional[str] = None  # Simple string prompt
    prompt_data: Optional[Dict[str, Any]] = None  # Or structured prompt with main_prompt, negative_prompt, etc.
    aspect_ratio: str = Field(default="9:16", pattern="^(16:9|9:16|1:1)$")  # Default vertical for Reels/TikTok/Shorts
    mode: str = Field(default="std", pattern="^(std|pro)$")


class GenerateScenarioRequest(BaseModel):
    video_id: int
    image_url: str
    description_data: Dict[str, Any]


class GenerateVideoRequest(BaseModel):
    video_id: int
    image_url: str
    scenario_data: Dict[str, Any]
    duration: int = Field(default=5, ge=5, le=10)
    mode: str = Field(default="std", pattern="^(std|pro)$")
    version: str = Field(default="2.5", pattern="^(1\\.5|1\\.6|2\\.1|2\\.5|2\\.6)$")


class GenerateAudioRequest(BaseModel):
    video_id: int


class SelectAudioVariantRequest(BaseModel):
    video_id: int
    variant_index: int = Field(..., ge=0, le=3)  # 0-3 for 4 variants


class AdaptForPlatformsRequest(BaseModel):
    video_id: int
    platforms: List[str] = Field(..., min_items=1)  # ["instagram", "tiktok", "youtube"]
    scenario_data: Dict[str, Any]


class ApprovalRequest(BaseModel):
    step_id: int
    approved: bool
    feedback: Optional[str] = None
    regenerate: bool = False  # Если true, регенерировать контент


class AutoGenerateRequest(BaseModel):
    video_id: int
