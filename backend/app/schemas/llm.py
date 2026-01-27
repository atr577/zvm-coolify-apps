"""
LLM Response Schemas — Pydantic v2 models for validating OpenAI responses.

These schemas define what we EXPECT from the LLM, separate from API response schemas.
Server-side fields (id, created_at, etc.) are NOT included here.

All models use extra="allow" to accept additional fields the LLM may return.
"""

from pydantic import BaseModel, Field, ConfigDict, RootModel
from typing import Dict, Any, List, Optional


# ============================================================
# 1. Image Prompt Generation
# ============================================================

class LLMImagePromptResponse(BaseModel):
    """Expected response from generate_image_prompt().

    Prompt template: prompts/image_prompt.py
    """
    model_config = ConfigDict(extra="allow")

    main_prompt: str
    style_suffix: str
    negative_prompt: str
    recommended_aspect_ratio: str = Field(default="9:16")


# ============================================================
# 2. Scenario Generation (shared by 3 methods)
# ============================================================

class CameraMovement(BaseModel):
    """Camera movement descriptor within a scenario."""
    model_config = ConfigDict(extra="allow")

    type: str
    speed: str
    description: str


class KeyMoment(BaseModel):
    """Single timeline moment in a scenario."""
    model_config = ConfigDict(extra="allow")

    timestamp: str
    action: str


class LLMScenarioResponse(BaseModel):
    """Expected response from scenario generation methods.

    Used by:
    - generate_scenario()
    - generate_scenario_from_description()
    - generate_scenario_from_template() — adds image_prompt, negative_prompt

    Prompt template: prompts/scenario.py
    """
    model_config = ConfigDict(extra="allow")

    motion_prompt: str
    camera_movement: CameraMovement
    subject_action: str
    key_moments: List[KeyMoment]

    # Optional — only in generate_scenario_from_template()
    image_prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    atmosphere_change: Optional[str] = None


# ============================================================
# 3. Content Validation
# ============================================================

class CriteriaResult(BaseModel):
    """Validation score for a single criterion."""
    model_config = ConfigDict(extra="allow")

    score: int = Field(ge=0, le=100)
    comment: str


class LLMValidationResponse(BaseModel):
    """Expected response from validate_content().

    Prompt template: prompts/validation.py
    """
    model_config = ConfigDict(extra="allow")

    status: str  # "pass" | "pass_with_warnings" | "fail"
    score: int = Field(ge=0, le=100)
    criteria_results: Dict[str, CriteriaResult]
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


# ============================================================
# 4. Publishing Metadata
# ============================================================

class PlatformMeta(BaseModel):
    """Publishing metadata for a single platform."""
    model_config = ConfigDict(extra="allow")

    title: str
    description: str
    hashtags: str


class LLMPublishingMetaResponse(RootModel[Dict[str, PlatformMeta]]):
    """Expected response from generate_publishing_meta().

    Flat dict: {"instagram": {...}, "tiktok": {...}}
    Prompt enforces this format. Validation + retry if LLM wraps it.

    Usage:
        validated = LLMPublishingMetaResponse.model_validate(raw_dict)
        data = validated.root  # Dict[str, PlatformMeta]

    Prompt template: prompts/publishing.py
    """
    pass


# ============================================================
# 5. Content Variants
# ============================================================

class LLMContentVariant(BaseModel):
    """Single content variant from LLM — WITHOUT server-side id.

    Server adds `id` field in the API endpoint via enumerate().
    """
    model_config = ConfigDict(extra="allow")

    description: str
    content_variables: Dict[str, Any]  # Intentionally dynamic


class LLMContentVariantsResponse(BaseModel):
    """Expected response from generate_content_variants().

    Prompt template: prompts/variants.py
    """
    model_config = ConfigDict(extra="allow")

    variants: List[LLMContentVariant]
