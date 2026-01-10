"""
OpenAI Service - now powered by PiAPI
Handles all text generation and content validation
"""

from app.services.piapi_client import piapi_client, PiAPIError
from app.core.config import settings
from app.schemas.workflow import CustomPrompt
from app.services.prompts import (
    STORY_SYSTEM_PROMPT, build_story_prompt, build_story_from_template_prompt,
    DESCRIPTION_SYSTEM_PROMPT, build_description_prompt,
    IMAGE_PROMPT_SYSTEM_PROMPT, build_image_prompt_prompt,
    SCENARIO_SYSTEM_PROMPT, build_scenario_prompt,
    VALIDATION_SYSTEM_PROMPT, build_validation_prompt,
    ADAPTATION_SYSTEM_PROMPT, build_adaptation_prompt,
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

    async def generate_story(
        self,
        theme: str = None,
        target_audience: str = None,
        mood: str = None,
        key_elements: str = None,
        duration: int = 5,
        platforms: List[str] = None,
        additional_notes: str = None,
        content_variables: Dict[str, Any] = None,
        custom_prompt: Optional[CustomPrompt] = None
    ) -> Dict[str, Any]:
        """Generate story/concept for viral video."""
        if self.mock_mode:
            logger.info("MOCK MODE: Returning mock story data")
            from app.services.mock_data import MOCK_STORY
            await asyncio.sleep(1)
            return MOCK_STORY

        prompt = build_story_prompt(
            theme=theme,
            target_audience=target_audience,
            mood=mood,
            key_elements=key_elements,
            duration=duration,
            platforms=platforms,
            additional_notes=additional_notes,
            content_variables=content_variables
        )

        try:
            if custom_prompt:
                result = await self.client.generate_json(
                    prompt=custom_prompt.user_prompt,
                    system_prompt=custom_prompt.system_prompt,
                    temperature=0.8
                )
            else:
                result = await self.client.generate_json(
                    prompt=prompt,
                    system_prompt=STORY_SYSTEM_PROMPT,
                    temperature=0.8
                )
            logger.info("Story generated successfully")
            return result
        except PiAPIError as e:
            logger.error(f"Failed to generate story: {e}")
            raise

    async def generate_description(
        self,
        story_data: Dict[str, Any],
        custom_prompt: Optional[CustomPrompt] = None
    ) -> Dict[str, Any]:
        """Generate detailed visual description from story."""
        if self.mock_mode:
            logger.info("MOCK MODE: Returning mock description data")
            from app.services.mock_data import MOCK_DESCRIPTION
            await asyncio.sleep(1)
            return MOCK_DESCRIPTION

        prompt = build_description_prompt(story_data)
        filled_template = story_data.get('filled_template', '')

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
                    system_prompt=DESCRIPTION_SYSTEM_PROMPT,
                    temperature=0.7
                )

            if filled_template:
                result["filled_template"] = filled_template
            logger.info("Description generated successfully")
            return result
        except PiAPIError as e:
            logger.error(f"Failed to generate description: {e}")
            raise

    async def generate_image_prompt(
        self,
        description_data: Dict[str, Any],
        custom_prompt: Optional[CustomPrompt] = None
    ) -> Dict[str, Any]:
        """Create structured prompt for image generation."""
        if self.mock_mode:
            logger.info("MOCK MODE: Returning mock prompt data")
            from app.services.mock_data import MOCK_PROMPT
            await asyncio.sleep(1)
            return MOCK_PROMPT

        prompt = build_image_prompt_prompt(description_data)

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

    async def adapt_for_platforms(
        self,
        content_data: Dict[str, Any],
        platforms: List[str],
        custom_prompt: Optional[CustomPrompt] = None
    ) -> Dict[str, Dict[str, str]]:
        """Adapt content for different platforms."""
        if self.mock_mode:
            logger.info("MOCK MODE: Returning mock adaptations")
            from app.services.mock_data import MOCK_ADAPTATIONS
            await asyncio.sleep(1)
            return {p: MOCK_ADAPTATIONS[p] for p in platforms if p in MOCK_ADAPTATIONS}

        prompt = build_adaptation_prompt(content_data, platforms)

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
                    system_prompt=ADAPTATION_SYSTEM_PROMPT,
                    temperature=0.6
                )

            # Extract platform data from response
            platform_data = self._extract_platform_data(result, platforms)
            logger.info(f"Platform adaptation completed for: {', '.join(platform_data.keys())}")
            return platform_data

        except PiAPIError as e:
            logger.error(f"Failed to adapt for platforms: {e}")
            raise

    async def generate_publishing_meta(
        self,
        prompt_or_template: str,
        platforms: List[str],
        image_url: Optional[str] = None
    ) -> Dict[str, Dict[str, str]]:
        """Generate publishing metadata for platforms."""
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

        prompt = build_publishing_meta_prompt(prompt_or_template, platforms)

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

    async def generate_story_from_template(
        self,
        story_template: str,
        content_variables: dict,
        duration: int,
        platforms: list,
        system_prompt: str = None
    ) -> dict:
        """Generate story by combining template with content variables."""
        if self.mock_mode:
            return {
                "concept": "Story based on template with specific content variables",
                "hook": "Captivating opening moment",
                "hook_type": "visual",
                "climax": "Satisfying payoff moment",
                "tone": "comedic",
                "pacing": "medium",
                "emotional_trigger": "curiosity",
                "duration": duration
            }

        # Fill template with content_variables
        filled_template = story_template
        if content_variables:
            for key, value in content_variables.items():
                if isinstance(value, dict):
                    value_str = ", ".join(f"{k}: {v}" for k, v in value.items())
                else:
                    value_str = str(value)
                filled_template = filled_template.replace(f"{{{key}}}", value_str)

        prompt = build_story_from_template_prompt(filled_template, duration)

        try:
            result = await self.client.generate_json(
                prompt=prompt,
                model=self.model,
                system_prompt=system_prompt
            )
            result["filled_template"] = filled_template
            logger.info("Generated story from template")
            return result

        except PiAPIError as e:
            logger.error(f"Failed to generate story from template: {e}")
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
