"""
DescriptionStep - Generates scene description from story.

Step 2 in the workflow pipeline.
"""
from typing import Dict, Any, Optional

from app.models.video import StepType
from app.services.workflow.base import BaseWorkflowStep
from app.services.openai_service import openai_service
from app.services.prompt_builders import build_description_prompt, PromptData
from app.schemas.workflow import CustomPrompt


class DescriptionStep(BaseWorkflowStep):
    """
    Generates detailed scene description including:
    - scene_summary: brief overview
    - main_subject: primary focus
    - secondary_elements: supporting elements
    - environment: location, time, weather
    - visual_style: lighting, colors, mood
    - key_details: important visual elements
    """

    step_type = StepType.DESCRIPTION
    step_name = "description"
    content_field = "description_data"
    requires_validation = True

    def build_prompt(self, request: Any) -> PromptData:
        """Build description generation prompt from story data."""
        story_data = self.video.story_data or {}
        return build_description_prompt(
            story_data=story_data,
            system_prompt=self.project_prompts.get(self.step_name)
        )

    async def generate(
        self,
        request: Any,
        prompt: CustomPrompt
    ) -> Dict[str, Any]:
        """Generate description using OpenAI service."""
        story_data = self.video.story_data or {}
        return await openai_service.generate_description(
            story_data=story_data,
            custom_prompt=prompt
        )

    def _get_previous_data(self, request: Any) -> Optional[Dict[str, Any]]:
        """Return story_data for validation context."""
        return {"story_data": self.video.story_data}
