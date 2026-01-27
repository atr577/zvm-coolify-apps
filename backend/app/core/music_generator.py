"""
Music Generator - AI music generation from video context.

Generates music prompts based on video scenario and creates
full tracks using Lyria2 via fal.ai.

Provider: fal-ai/lyria2
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.models_config import MUSIC_MODEL_CONFIGS
from app.services.openai_client import openai_client
from app.services.media_service import media_service
from app.services.prompts.music_prompt import LYRIA2_MUSIC_PROMPT, UNSAFE_WORDS_MAP

logger = logging.getLogger(__name__)


def _get_system_prompt() -> str:
    """Get system prompt for current music model from MUSIC_MODEL_CONFIGS."""
    model = settings.MUSIC_MODEL or "fal-ai/lyria2"
    config = MUSIC_MODEL_CONFIGS.get(model, {})
    return config.get("system_prompt", LYRIA2_MUSIC_PROMPT)


def sanitize_prompt(prompt: str) -> str:
    """Replace unsafe words with safe synonyms before sending to fal.ai.

    Case-insensitive word boundary replacement.
    Called AFTER GPT generates the prompt, BEFORE sending to fal.ai.
    """
    result = prompt
    for unsafe, safe in UNSAFE_WORDS_MAP.items():
        result = re.sub(rf'\b{re.escape(unsafe)}\b', safe, result, flags=re.IGNORECASE)
    return result


class MusicGenerator:
    """Generates AI music from video context."""

    async def generate_prompt(
        self,
        video,
        feedback: str = None,
        previous_prompt: str = None,
    ) -> Tuple[str, str]:
        """
        Generate a music prompt based on video context.

        Uses GPT to analyze the scenario and create an appropriate
        music description for AI music generation.

        Args:
            video: Video model with scenario_data, project settings
            feedback: Optional user feedback for regeneration (e.g., "more upbeat")
            previous_prompt: Previous music prompt (for feedback context)

        Returns:
            Tuple of (music_prompt, tags)
        """
        # Extract context from video
        scenario = video.scenario_data or {}
        project = video.project
        duration = project.duration if project else 5

        # Build scene context from scenario data
        scene_parts = []

        if scenario.get("image_prompt"):
            scene_parts.append(f"Visual: {scenario['image_prompt']}")

        if scenario.get("motion_prompt"):
            scene_parts.append(f"Action: {scenario['motion_prompt']}")

        if scenario.get("subject_action"):
            scene_parts.append(f"Subject: {scenario['subject_action']}")

        # Fallback to description_data if no scenario
        if not scene_parts and video.description_data:
            scene_parts.append(video.description_data)

        scene_context = "\n".join(scene_parts) if scene_parts else "Short viral video"

        # Build user prompt
        user_prompt = f"""Create music for this {duration}-second video:

{scene_context}

Return JSON with music_prompt and lyrics_type."""

        # Add previous prompt and feedback context for regeneration
        if previous_prompt and feedback:
            user_prompt += f"""

REGENERATION REQUEST:
Previous music prompt: "{previous_prompt}"
User feedback: "{feedback}"

Create a NEW music prompt that addresses the feedback while keeping the video context in mind."""
        elif feedback:
            user_prompt += f"\n\nUser feedback: {feedback}"

        user_prompt += "\n\nReturn JSON with music_prompt and lyrics_type."

        logger.info(f"Generating music prompt for video {video.id}")

        # Call GPT via OpenAI with JSON output
        result = await openai_client.generate_json(
            prompt=user_prompt,
            system_prompt=_get_system_prompt(),
            temperature=0.8,
        )

        # Handle unexpected response format (list instead of dict)
        if isinstance(result, list):
            result = result[0] if result else {}
        if not isinstance(result, dict):
            logger.warning(f"Unexpected GPT response format: {type(result)}, using defaults")
            result = {}

        music_prompt = result.get("music_prompt", "Bold vocal hook with catchy melody")
        tags = result.get("tags", "pop, energetic, female vocals, catchy")

        logger.info(f"Generated music prompt: {music_prompt[:80]}... (tags={tags})")

        return music_prompt, tags

    async def generate_track(
        self,
        prompt: str,
        tags: str = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate music tracks using Lyria2 via fal.ai.

        Lyria2 generates 30-second instrumental tracks.
        Returns single track (list for compatibility).

        Args:
            prompt: Music description
            tags: Genre/style tags (included in prompt)

        Returns:
            List of track dicts with audio_url, title, duration
        """
        logger.info(f"Generating track via Lyria2 (tags={tags}): {prompt[:50]}...")

        # Combine prompt with tags for better results
        full_prompt = prompt
        if tags:
            full_prompt = f"{prompt}. Style: {tags}"

        # Sanitize before sending to fal.ai
        full_prompt = sanitize_prompt(full_prompt)

        # Lyria2 returns single audio URL
        audio_url = await media_service.generate_music(
            prompt=full_prompt,
            negative_prompt="low quality, distorted"
        )

        tracks = [{
            "audio_url": audio_url,
            "title": "Lyria2 Track",
            "duration": 30  # Lyria2 max duration
        }]

        logger.info(f"Generated {len(tracks)} track via Lyria2")
        return tracks

    async def generate_for_video(
        self,
        video,
        feedback: str = None,
        previous_prompt: str = None,
    ) -> Tuple[str, List[Dict[str, Any]], str]:
        """
        High-level method: generate music prompt and tracks for a video.

        Args:
            video: Video model
            feedback: Optional user feedback for regeneration
            previous_prompt: Previous music prompt (for feedback context)

        Returns:
            Tuple of (music_prompt, tracks_list, tags)
            tracks_list: List of dicts with audio_url, title, duration
        """
        # Generate prompt from video context
        music_prompt, tags = await self.generate_prompt(
            video,
            feedback=feedback,
            previous_prompt=previous_prompt,
        )

        # Generate tracks with vocals
        tracks = await self.generate_track(
            prompt=music_prompt,
            tags=tags,
        )

        return music_prompt, tracks, tags


# Singleton instance
music_generator = MusicGenerator()
