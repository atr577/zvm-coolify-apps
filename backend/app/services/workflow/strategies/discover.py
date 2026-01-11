"""Discover strategy for creative video generation."""
from typing import Any, Dict
import logging

from app.services.workflow.strategies.base import BaseStrategy
from app.services.openai_service import openai_service

logger = logging.getLogger(__name__)


class DiscoverStrategy(BaseStrategy):
    """
    Discover strategy: LLM generates creatively from story_template.

    Flow:
    1. Uses project.story_template + video.content_variables
    2. LLM generates scenario with image_prompt, motion_prompt, camera_movement
    3. Returns structured scenario_data for image generation
    """

    async def generate_scenario(self, video, project) -> Dict[str, Any]:
        """
        Generate scenario creatively from template.

        Uses story_template + content_variables to generate:
        - image_prompt: for image generation
        - motion_prompt: for video generation
        - camera_movement: camera motion settings
        - key_moments: timeline of actions
        """
        logger.info(f"DiscoverStrategy.generate_scenario for video {video.id}")

        # Get content variables (selected by user from variants)
        content_variables = video.content_variables or {}

        # Generate scenario using LLM
        scenario_data = await openai_service.generate_scenario_from_template(
            story_template=project.story_template,
            content_variables=content_variables,
            duration=project.duration,
            aspect_ratio=project.aspect_ratio
        )

        logger.debug(f"Generated scenario: {scenario_data}")

        return {
            "scenario_data": scenario_data,
            "image_prompt": scenario_data.get("image_prompt"),
            "negative_prompt": scenario_data.get("negative_prompt"),
            "motion_prompt": scenario_data.get("motion_prompt"),
            "camera_movement": scenario_data.get("camera_movement"),
        }
