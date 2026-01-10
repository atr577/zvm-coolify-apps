"""
PromptStep - Generates image prompt from description.

Step 3 in the workflow pipeline.
"""
from typing import Dict, Any, Optional

from app.models.video import StepType
from app.services.workflow.base import BaseWorkflowStep
from app.services.openai_service import openai_service
from app.services.prompt_builders import build_image_prompt_prompt, PromptData
from app.schemas.workflow import CustomPrompt


class PromptStep(BaseWorkflowStep):
    """
    Generates image generation prompt including:
    - main_prompt: detailed image prompt in English
    - style_suffix: style modifiers
    - negative_prompt: what to avoid
    - recommended_aspect_ratio: best ratio for this scene
    """

    step_type = StepType.PROMPT
    step_name = "prompt"
    content_field = "prompt_data"
    requires_validation = True

    def build_prompt(self, request: Any) -> PromptData:
        """Build image prompt generation prompt from description data."""
        description_data = self.video.description_data or {}
        return build_image_prompt_prompt(
            description_data=description_data,
            system_prompt=self.project_prompts.get(self.step_name)
        )

    async def generate(
        self,
        request: Any,
        prompt: CustomPrompt
    ) -> Dict[str, Any]:
        """Generate image prompt using OpenAI service."""
        description_data = self.video.description_data or {}
        result = await openai_service.generate_image_prompt(
            description_data=description_data,
            custom_prompt=prompt
        )

        # Also save main_prompt to video.image_prompt for convenience
        if result and result.get("main_prompt"):
            self.video.image_prompt = result["main_prompt"]

        return result

    def _get_previous_data(self, request: Any) -> Optional[Dict[str, Any]]:
        """Return description_data for validation context."""
        return {"description_data": self.video.description_data}
