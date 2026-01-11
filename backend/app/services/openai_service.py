"""
OpenAI Service - now powered by PiAPI
Handles text generation for 4-step workflow (SCENARIO → IMAGE → VIDEO → AUDIO)
"""

from app.services.piapi_client import piapi_client, PiAPIError
from app.core.config import settings
from app.schemas.workflow import CustomPrompt
from app.services.prompts import (
    IMAGE_PROMPT_SYSTEM_PROMPT, build_image_prompt_prompt,
    SCENARIO_SYSTEM_PROMPT, build_scenario_prompt, build_scenario_from_template_prompt,
    VALIDATION_SYSTEM_PROMPT, build_validation_prompt,
    build_publishing_meta_prompt,
    build_variants_prompt,
)
from typing import Dict, Any, List, Optional
import logging
import asyncio

logger = logging.getLogger(__name__)


class OpenAIService:
    def __init__(self):
        self.client = piapi_client
        self.model = settings.LLM_MODEL or settings.GPT_MODEL  # Legacy fallback
        self.mock_mode = settings.MOCK_MODE

    async def generate_image_prompt(
        self,
        description_data: Dict[str, Any],
        custom_prompt: Optional[CustomPrompt] = None,
        scenario_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create structured prompt for image generation.

        Args:
            description_data: Visual description of the scene
            custom_prompt: Optional custom prompt override
            scenario_data: Optional scenario data to make image animation-ready
        """
        if self.mock_mode:
            logger.info("MOCK MODE: Returning mock prompt data")
            from app.services.mock_data import MOCK_PROMPT
            await asyncio.sleep(1)
            return MOCK_PROMPT

        prompt = build_image_prompt_prompt(description_data, scenario_data)

        try:
            if custom_prompt:
                result = await self.client.generate_json(
                    prompt=custom_prompt.user_prompt,
                    system_prompt=custom_prompt.system_prompt,
                    temperature=0.6
                )
            else:
                result = await self.client.generate_json(
                    prompt=prompt,
                    system_prompt=IMAGE_PROMPT_SYSTEM_PROMPT,
                    temperature=0.6
                )
            logger.info("Image prompt generated successfully")
            return result
        except PiAPIError as e:
            logger.error(f"Failed to generate image prompt: {e}")
            raise

    async def generate_scenario(
        self,
        image_url: str,
        description_data: Dict[str, Any],
        story_data: Dict[str, Any] = None,
        duration: int = 5,
        custom_prompt: Optional[CustomPrompt] = None
    ) -> Dict[str, Any]:
        """Create motion scenario for video generation."""
        if self.mock_mode:
            logger.info("MOCK MODE: Returning mock scenario data")
            from app.services.mock_data import MOCK_SCENARIO
            await asyncio.sleep(1)
            return MOCK_SCENARIO

        prompt = build_scenario_prompt(description_data, story_data, duration)

        try:
            if custom_prompt:
                result = await self.client.generate_json(
                    prompt=custom_prompt.user_prompt,
                    system_prompt=custom_prompt.system_prompt,
                    temperature=0.7
                )
            else:
                result = await self.client.generate_json(
                    prompt=prompt,
                    system_prompt=SCENARIO_SYSTEM_PROMPT,
                    temperature=0.7
                )
            logger.info("Scenario generated successfully")
            return result
        except PiAPIError as e:
            logger.error(f"Failed to generate scenario: {e}")
            raise

    async def generate_scenario_from_description(
        self,
        description_data: Dict[str, Any],
        story_data: Dict[str, Any] = None,
        duration: int = 5,
        custom_prompt: Optional[CustomPrompt] = None
    ) -> Dict[str, Any]:
        """Create motion scenario from description only (no image required).

        This is used when scenario is generated BEFORE the image,
        allowing the image prompt to be tailored for the planned animation.
        """
        if self.mock_mode:
            logger.info("MOCK MODE: Returning mock scenario data")
            from app.services.mock_data import MOCK_SCENARIO
            await asyncio.sleep(1)
            return MOCK_SCENARIO

        prompt = build_scenario_prompt(description_data, story_data, duration)

        try:
            if custom_prompt:
                result = await self.client.generate_json(
                    prompt=custom_prompt.user_prompt,
                    system_prompt=custom_prompt.system_prompt,
                    temperature=0.7
                )
            else:
                result = await self.client.generate_json(
                    prompt=prompt,
                    system_prompt=SCENARIO_SYSTEM_PROMPT,
                    temperature=0.7
                )
            logger.info("Scenario from description generated successfully")
            return result
        except PiAPIError as e:
            logger.error(f"Failed to generate scenario from description: {e}")
            raise

    async def generate_scenario_from_template(
        self,
        story_template: str,
        content_variables: Dict[str, Any],
        duration: int = 5,
        aspect_ratio: str = "9:16",
        feedback: Optional[str] = None,
        previous_scenario: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate scenario with image_prompt from story_template + content_variables.

        This is the main SCENARIO step - generates:
        - image_prompt (for image generation)
        - motion_prompt (for video generation)
        - camera_movement
        - key_moments

        Args:
            story_template: The concept/idea for the video
            content_variables: Hard constraints (actor, vehicle, location, etc.)
            duration: Video duration in seconds
            aspect_ratio: Video aspect ratio (e.g., "9:16", "16:9", "1:1")
            feedback: Optional user feedback for regeneration
            previous_scenario: Previous scenario to improve upon
        """
        if self.mock_mode:
            logger.info("MOCK MODE: Returning mock scenario from template")
            await asyncio.sleep(1)
            return {
                "image_prompt": "A redhead woman in elegant dress standing next to Ford Mustang in mountain landscape, cinematic lighting, vertical 9:16",
                "negative_prompt": "blurry, low quality, distorted",
                "motion_prompt": "Woman turns gracefully, wind blows through her hair, soft movements",
                "camera_movement": {
                    "type": "dolly_in",
                    "speed": "slow",
                    "description": "Плавный наезд камеры"
                },
                "subject_action": "Девушка поворачивается к камере",
                "key_moments": [
                    {"timestamp": "0.0-1.5s", "action": "Девушка стоит у машины"},
                    {"timestamp": "1.5-3.0s", "action": "Поворачивается"},
                    {"timestamp": "3.0-5.0s", "action": "Улыбается в камеру"}
                ]
            }

        prompt = build_scenario_from_template_prompt(
            story_template=story_template,
            content_variables=content_variables,
            duration=duration,
            aspect_ratio=aspect_ratio,
            feedback=feedback,
            previous_scenario=previous_scenario
        )

        try:
            result = await self.client.generate_json(
                prompt=prompt,
                system_prompt=SCENARIO_SYSTEM_PROMPT,
                temperature=0.7
            )
            logger.info("Scenario from template generated successfully")
            return result
        except PiAPIError as e:
            logger.error(f"Failed to generate scenario from template: {e}")
            raise

    async def refine_prompt(
        self,
        current_prompt: str,
        feedback: str,
        prompt_type: str = "image"
    ) -> str:
        """Refine a prompt based on user feedback.

        Args:
            current_prompt: The current prompt text
            feedback: User's feedback/instructions for improvement
            prompt_type: Type of prompt - "image" or "motion"

        Returns:
            Refined prompt string
        """
        if self.mock_mode:
            logger.info("MOCK MODE: Returning mock refined prompt")
            await asyncio.sleep(0.5)
            return f"{current_prompt} [refined with: {feedback}]"

        if prompt_type == "image":
            system = "You are an expert at writing image generation prompts. Refine the prompt based on user feedback while keeping the core subject and style."
        else:
            system = "You are an expert at writing motion/video prompts. Refine the prompt based on user feedback while keeping the core action."

        user_prompt = f"""Current prompt:
{current_prompt}

User feedback:
{feedback}

Create an improved prompt that incorporates the feedback. Keep the same format and language (English). Return ONLY the new prompt text, nothing else."""

        try:
            result = await self.client.generate_text(
                prompt=user_prompt,
                system_prompt=system,
                temperature=0.7
            )
            logger.info(f"Prompt refined successfully: {prompt_type}")
            return result.strip()
        except PiAPIError as e:
            logger.error(f"Failed to refine prompt: {e}")
            raise

    async def validate_content(
        self,
        content: Dict[str, Any],
        step_type: str,
        previous_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Validate generated content."""
        if self.mock_mode:
            logger.info("MOCK MODE: Returning mock validation result")
            from app.services.mock_data import MOCK_VALIDATION_RESULT
            await asyncio.sleep(0.5)
            return MOCK_VALIDATION_RESULT

        prompt = build_validation_prompt(content, step_type, previous_data)

        try:
            result = await self.client.generate_json(
                prompt=prompt,
                system_prompt=VALIDATION_SYSTEM_PROMPT,
                temperature=0.3
            )
            logger.info(f"Validation completed for {step_type}: {result.get('status')}")
            return result
        except PiAPIError as e:
            logger.error(f"Failed to validate content: {e}")
            raise

    async def generate_publishing_meta(
        self,
        platforms: List[str],
        scenario_data: Optional[Dict[str, Any]] = None,
        fallback_text: Optional[str] = None
    ) -> Dict[str, Dict[str, str]]:
        """Generate publishing metadata for platforms.

        Args:
            platforms: List of platforms to generate for
            scenario_data: Scenario data with story_template, content_variables, image_prompt
            fallback_text: Fallback text if scenario_data not available
        """
        if self.mock_mode:
            logger.info("MOCK MODE: Returning mock publishing meta")
            await asyncio.sleep(0.5)
            return {
                platform: {
                    "title": f"Mock title for {platform}",
                    "description": f"Mock description for {platform}",
                    "hashtags": f"#mock #{platform} #shorts"
                }
                for platform in platforms
            }

        prompt = build_publishing_meta_prompt(
            prompt_or_template=fallback_text or "",
            platforms=platforms,
            scenario_data=scenario_data
        )

        try:
            result = await self.client.generate_json(
                prompt=prompt,
                system_prompt="You are an SMM expert. Create viral titles and descriptions in English.",
                temperature=0.7
            )

            platform_data = self._extract_platform_data(result, platforms)
            # Fill missing platforms with defaults
            for platform in platforms:
                if platform not in platform_data:
                    platform_data[platform] = {
                        "title": "Untitled",
                        "description": "",
                        "hashtags": ""
                    }

            logger.info(f"Publishing meta generated for: {', '.join(platform_data.keys())}")
            return platform_data

        except PiAPIError as e:
            logger.error(f"Failed to generate publishing meta: {e}")
            raise

    async def generate_content_variants(
        self,
        story_template: str,
        count: int = 4,
        exclude: List[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Generate N content variants from story template."""
        if self.mock_mode:
            logger.info(f"MOCK MODE: Returning {count} mock content variants")
            await asyncio.sleep(1)
            return [
                {
                    "id": i,
                    "description": f"Mock вариант #{i} для шаблона",
                    "content_variables": {
                        "mock_entity": {
                            "type": f"entity_{i}",
                            "style": "default",
                            "note": "This is mock data"
                        }
                    }
                }
                for i in range(1, count + 1)
            ]

        prompt = build_variants_prompt(story_template, count, exclude)

        try:
            result = await self.client.generate_json(prompt=prompt, model=self.model)
            variants = self._extract_list_from_response(result)
            logger.info(f"Generated {len(variants)} content variants")
            return variants

        except PiAPIError as e:
            logger.error(f"Failed to generate content variants: {e}")
            raise

    # Helper methods

    def _extract_platform_data(
        self,
        result: Dict[str, Any],
        platforms: List[str]
    ) -> Dict[str, Dict[str, str]]:
        """Extract platform data from AI response."""
        platform_data = result
        if isinstance(result, dict):
            has_platform_keys = any(p in result for p in platforms)
            if not has_platform_keys:
                for key in ["platforms", "adaptations", "data", "result"]:
                    if key in result and isinstance(result[key], dict):
                        platform_data = result[key]
                        break

        return {p: platform_data[p] for p in platforms if p in platform_data}

    def _extract_list_from_response(self, result: Any) -> List[Dict[str, Any]]:
        """Extract list from AI response."""
        if isinstance(result, list):
            return result
        elif isinstance(result, dict):
            return (
                result.get("variants") or
                result.get("concepts") or
                result.get("items") or
                result.get("data") or
                list(result.values())[0] if result else []
            )
        return []


# Singleton instance
openai_service = OpenAIService()
