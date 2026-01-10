"""
ScenarioStep - Generates video scenario from image.

Step 5 in the workflow pipeline (after Image generation).
"""
from typing import Dict, Any, Optional

from app.models.video import StepType
from app.services.workflow.base import BaseWorkflowStep
from app.services.openai_service import openai_service
from app.services.prompt_builders import build_scenario_prompt, PromptData
from app.schemas.workflow import CustomPrompt


class ScenarioStep(BaseWorkflowStep):
    """
    Generates video scenario including:
    - scene_direction: overall description
    - motion_prompt: prompt for video generation
    - camera_movement: type, speed, description
    - subject_motion: primary and secondary movements
    - atmosphere: particles, lighting changes
    - key_moments: timeline of actions
    - audio_suggestion: sound recommendation
    """

    step_type = StepType.SCENARIO
    step_name = "scenario"
    content_field = "scenario_data"
    requires_validation = True

    def build_prompt(self, request: Any) -> PromptData:
        """Build scenario generation prompt from image and description."""
        return build_scenario_prompt(
            image_url=self.video.image_url or "",
            description_data=self.video.description_data or {},
            story_data=self.video.story_data,
            duration=self.project.duration if self.project else 5,
            system_prompt=self.project_prompts.get(self.step_name)
        )

    async def generate(
        self,
        request: Any,
        prompt: CustomPrompt
    ) -> Dict[str, Any]:
        """Generate scenario using OpenAI service with vision."""
        return await openai_service.generate_scenario(
            image_url=self.video.image_url or "",
            description_data=self.video.description_data or {},
            story_data=self.video.story_data,
            duration=self.project.duration if self.project else 5,
            custom_prompt=prompt
        )

    def _get_previous_data(self, request: Any) -> Optional[Dict[str, Any]]:
        """Return context for validation."""
        return {
            "description_data": self.video.description_data,
            "image_url": self.video.image_url
        }
