"""
Prompt templates for AI generation services.
Extracted from openai_service.py for better maintainability.
"""

from .story import STORY_SYSTEM_PROMPT, build_story_prompt, build_story_from_template_prompt
from .description import DESCRIPTION_SYSTEM_PROMPT, build_description_prompt
from .image_prompt import IMAGE_PROMPT_SYSTEM_PROMPT, build_image_prompt_prompt
from .scenario import SCENARIO_SYSTEM_PROMPT, build_scenario_prompt
from .validation import VALIDATION_SYSTEM_PROMPT, VALIDATION_CRITERIA, build_validation_prompt
from .adaptation import ADAPTATION_SYSTEM_PROMPT, build_adaptation_prompt
from .publishing import build_publishing_meta_prompt
from .variants import build_variants_prompt

__all__ = [
    "STORY_SYSTEM_PROMPT", "build_story_prompt",
    "DESCRIPTION_SYSTEM_PROMPT", "build_description_prompt",
    "IMAGE_PROMPT_SYSTEM_PROMPT", "build_image_prompt_prompt",
    "SCENARIO_SYSTEM_PROMPT", "build_scenario_prompt",
    "VALIDATION_SYSTEM_PROMPT", "VALIDATION_CRITERIA", "build_validation_prompt",
    "ADAPTATION_SYSTEM_PROMPT", "build_adaptation_prompt",
    "build_publishing_meta_prompt",
    "build_variants_prompt",
]
