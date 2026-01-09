"""
AdaptationStep - Adapts content for different platforms.

Step 8 in the workflow pipeline (after Audio).
"""
from typing import Dict, Any, Optional, List

from app.models.video import StepType
from app.services.workflow.base import BaseWorkflowStep
from app.services.openai_service import openai_service
from app.services.prompt_builders import build_adaptation_prompt, PromptData
from app.schemas.workflow import CustomPrompt


class AdaptationStep(BaseWorkflowStep):
    """
    Generates platform-specific adaptations including:
    - instagram: caption, hashtags, first_comment, cta
    - tiktok: caption, hashtags, sounds_suggestion
    - youtube: title, description, tags, thumbnail_text
    """

    step_type = StepType.ADAPTATION
    step_name = "adaptation"
    content_field = "adaptation_data"
    requires_validation = True

    def build_prompt(self, request: Any) -> PromptData:
        """Build adaptation prompt from full context."""
        full_context = self._build_full_context()
        platforms = self._get_platforms()

        return build_adaptation_prompt(
            full_context=full_context,
            platforms=platforms,
            system_prompt=self.project_prompts.get(self.step_name)
        )

    async def generate(
        self,
        request: Any,
        prompt: CustomPrompt
    ) -> Dict[str, Any]:
        """Generate platform adaptations using OpenAI service."""
        full_context = self._build_full_context()
        platforms = self._get_platforms()

        return await openai_service.adapt_for_platforms(
            content_data=full_context,
            platforms=platforms,
            custom_prompt=prompt
        )

    def _get_previous_data(self, request: Any) -> Optional[Dict[str, Any]]:
        """Return scenario_data for validation context."""
        return {
            "scenario_data": self.video.scenario_data,
            "platforms": self._get_platforms()
        }

    def _build_full_context(self) -> Dict[str, Any]:
        """Build full context dict from video data."""
        return {
            "story": self.video.story_data or {},
            "description": self.video.description_data or {},
            "scenario": self.video.scenario_data or {}
        }

    def _get_platforms(self) -> List[str]:
        """Get target platforms from project."""
        if self.project and self.project.platforms:
            return self.project.platforms
        return ["instagram", "tiktok", "youtube"]
