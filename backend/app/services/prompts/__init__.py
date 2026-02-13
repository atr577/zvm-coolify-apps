"""
Prompt templates for AI generation services.

4-step workflow uses:
- scenario.py: SCENARIO step (generate scenario from template)
- image_prompt.py: IMAGE step prompts (not used directly, scenario_data has image_prompt)
- validation.py: Content validation
- variants.py: Generate content variants
- publishing.py: Publishing metadata
"""
from .image_prompt import IMAGE_PROMPT_SYSTEM_PROMPT, build_image_prompt_prompt
from .scenario import SCENARIO_SYSTEM_PROMPT, build_scenario_prompt, build_scenario_from_template_prompt
from .validation import VALIDATION_SYSTEM_PROMPT, VALIDATION_CRITERIA, build_validation_prompt
from .publishing import (
    build_publishing_meta_prompt,
    build_custom_title_prompt,
    build_custom_description_prompt,
    build_custom_hashtags_prompt,
)
from .variants import build_variants_prompt
from .music_prompt import LYRIA2_MUSIC_PROMPT, SUNO_MUSIC_PROMPT, SAFETY_REWRITE_PROMPT, UNSAFE_WORDS_MAP
from .feedback import FEEDBACK_SYSTEM_PROMPT, build_feedback_modification_prompt

__all__ = [
    "IMAGE_PROMPT_SYSTEM_PROMPT", "build_image_prompt_prompt",
    "SCENARIO_SYSTEM_PROMPT", "build_scenario_prompt", "build_scenario_from_template_prompt",
    "VALIDATION_SYSTEM_PROMPT", "VALIDATION_CRITERIA", "build_validation_prompt",
    "build_publishing_meta_prompt",
    "build_custom_title_prompt",
    "build_custom_description_prompt",
    "build_custom_hashtags_prompt",
    "build_variants_prompt",
    "LYRIA2_MUSIC_PROMPT", "SUNO_MUSIC_PROMPT", "SAFETY_REWRITE_PROMPT", "UNSAFE_WORDS_MAP",
    "FEEDBACK_SYSTEM_PROMPT", "build_feedback_modification_prompt",
]
