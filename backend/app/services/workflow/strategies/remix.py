"""Remix strategy for template-based video generation."""
from typing import Any, Dict
import logging

from app.services.workflow.strategies.base import BaseStrategy
from app.services.openai_service import openai_service

logger = logging.getLogger(__name__)


class RemixStrategy(BaseStrategy):
    """
    Remix strategy: LLM fills template placeholders.

    Flow:
    1. Uses project.scenario_template with {placeholders}
    2. LLM selects values for placeholders from suggestions
    3. Fills template to create scenario_data
    """

    async def generate_scenario(self, video, project) -> Dict[str, Any]:
        """
        Generate scenario by filling template placeholders.

        Uses:
        - project.scenario_template: template with {placeholders}
        - project.placeholders: list of placeholder names
        - project.placeholder_suggestions: suggested values for each
        - video.content_variables: pre-selected variables (if any)
        """
        logger.info(f"RemixStrategy.generate_scenario for video {video.id}")

        # If content_variables already set (from pre-workflow selection), use them
        if video.content_variables:
            content_variables = video.content_variables
            logger.debug(f"Using pre-selected content_variables: {content_variables}")
        else:
            # Generate variables from placeholders
            content_variables = await self._generate_variables(project)
            logger.debug(f"Generated content_variables: {content_variables}")

        # Generate scenario using the same template approach as Discover
        # but with Remix-specific template
        scenario_data = await openai_service.generate_scenario_from_template(
            story_template=project.story_template,
            content_variables=content_variables,
            duration=project.duration,
            aspect_ratio=project.aspect_ratio
        )

        logger.debug(f"Generated scenario: {scenario_data}")

        return {
            "scenario_data": scenario_data,
            "content_variables": content_variables,
            "image_prompt": scenario_data.get("image_prompt"),
            "negative_prompt": scenario_data.get("negative_prompt"),
            "motion_prompt": scenario_data.get("motion_prompt"),
            "camera_movement": scenario_data.get("camera_movement"),
        }

    async def _generate_variables(self, project) -> Dict[str, Any]:
        """Generate content variables from placeholder suggestions."""
        if not project.placeholders:
            return {}

        # Use LLM to select creative values for placeholders
        variables = await openai_service.generate_content_variants(
            story_template=project.story_template,
            count=1  # Generate single variant for this video
        )

        if variables and len(variables) > 0:
            return variables[0].get("content_variables", {})

        return {}
