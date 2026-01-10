"""
Prompt preview builder for workflow steps.
Extracted from workflow.py API endpoint.
"""
from typing import Dict, Any, Optional
from fastapi import HTTPException

from app.models.video import Video
from app.schemas.workflow import StepTypeEnum
from app.services.prompt_builders import (
    build_story_prompt,
    build_description_prompt,
    build_image_prompt_prompt,
    build_scenario_prompt,
    build_adaptation_prompt,
    PromptData
)


class PromptPreviewBuilder:
    """Builds prompt previews for different step types."""

    def __init__(self, video: Video, project_prompts: Dict[str, str]):
        self.video = video
        self.project = video.project
        self.project_prompts = project_prompts

    def build(self, step_type: StepTypeEnum, context: Dict[str, Any]) -> PromptData:
        """Build prompt data for the given step type."""
        builders = {
            StepTypeEnum.STORY: self._build_story,
            StepTypeEnum.DESCRIPTION: self._build_description,
            StepTypeEnum.PROMPT: self._build_prompt,
            StepTypeEnum.SCENARIO: self._build_scenario,
            StepTypeEnum.ADAPTATION: self._build_adaptation,
        }

        builder = builders.get(step_type)
        if not builder:
            raise HTTPException(status_code=400, detail=f"Unknown step type: {step_type}")

        return builder(context)

    def _build_story(self, context: Dict[str, Any]) -> PromptData:
        return build_story_prompt(
            theme=context.get("theme"),
            target_audience=context.get("target_audience"),
            mood=context.get("mood"),
            key_elements=context.get("key_elements"),
            duration=context.get("duration", 5),
            platforms=context.get("platforms"),
            additional_notes=context.get("additional_notes"),
            content_variables=context.get("content_variables") or self.video.content_variables,
            system_prompt=self.project_prompts.get("story")
        )

    def _build_description(self, context: Dict[str, Any]) -> PromptData:
        story_data = context.get("story_data") or self.video.story_data
        if not story_data:
            raise HTTPException(status_code=400, detail="story_data required for description prompt")
        return build_description_prompt(story_data, system_prompt=self.project_prompts.get("description"))

    def _build_prompt(self, context: Dict[str, Any]) -> PromptData:
        description_data = context.get("description_data") or self.video.description_data
        if not description_data:
            raise HTTPException(status_code=400, detail="description_data required for prompt generation")
        return build_image_prompt_prompt(description_data, system_prompt=self.project_prompts.get("prompt"))

    def _build_scenario(self, context: Dict[str, Any]) -> PromptData:
        image_url = context.get("image_url") or self.video.image_url
        description_data = context.get("description_data") or self.video.description_data
        if not image_url or not description_data:
            raise HTTPException(status_code=400, detail="image_url and description_data required for scenario")
        return build_scenario_prompt(
            image_url=image_url,
            description_data=description_data,
            story_data=self.video.story_data,
            duration=self.project.duration if self.project else 5,
            system_prompt=self.project_prompts.get("scenario")
        )

    def _build_adaptation(self, context: Dict[str, Any]) -> PromptData:
        platforms = context.get("platforms") or (self.project.platforms if self.project else ["instagram"])
        full_context = {
            "story": self.video.story_data,
            "scenario": context.get("scenario_data") or self.video.scenario_data
        }
        return build_adaptation_prompt(full_context, platforms, system_prompt=self.project_prompts.get("adaptation"))
