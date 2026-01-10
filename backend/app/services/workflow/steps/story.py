"""
StoryStep - Generates the story/concept for a video.

Step 1 in the workflow pipeline.
"""
from typing import Dict, Any

from app.models.video import StepType
from app.services.workflow.base import BaseWorkflowStep
from app.services.openai_service import openai_service
from app.services.prompt_builders import build_story_prompt, PromptData
from app.schemas.workflow import GenerateStoryRequest, CustomPrompt


class StoryStep(BaseWorkflowStep):
    """
    Generates story concept including:
    - concept: what happens in the video
    - hook: first 3 seconds hook
    - hook_type: visual/text/audio
    - climax: payoff/ending
    - tone, pacing, emotional_trigger
    """

    step_type = StepType.STORY
    step_name = "story"
    content_field = "story_data"
    requires_validation = True

    def build_prompt(self, request: GenerateStoryRequest) -> PromptData:
        """Build story generation prompt."""
        content_variables = request.content_variables or self.video.content_variables

        return build_story_prompt(
            theme=request.theme,
            target_audience=request.target_audience,
            mood=request.mood,
            key_elements=request.key_elements,
            duration=request.duration,
            platforms=request.platforms,
            additional_notes=request.additional_notes,
            content_variables=content_variables,
            system_prompt=self.project_prompts.get(self.step_name)
        )

    async def generate(
        self,
        request: GenerateStoryRequest,
        prompt: CustomPrompt
    ) -> Dict[str, Any]:
        """Generate story using OpenAI service."""
        content_variables = request.content_variables or self.video.content_variables

        return await openai_service.generate_story(
            theme=request.theme,
            target_audience=request.target_audience,
            mood=request.mood,
            key_elements=request.key_elements,
            duration=request.duration,
            platforms=request.platforms,
            additional_notes=request.additional_notes,
            content_variables=content_variables,
            custom_prompt=prompt
        )
