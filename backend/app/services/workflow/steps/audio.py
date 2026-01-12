"""
Audio step - adds AI-generated audio to video.

Uses provider factory to select appropriate audio provider:
- kling: KLING Sound API (scene audio)
- ai_music: AI music generation + hook analysis

The provider is determined by video.project.audio_provider.
"""
from typing import Dict, Any
import logging

from app.providers.factory import get_audio_provider

logger = logging.getLogger(__name__)


async def generate(video) -> Dict[str, Any]:
    """
    Generate audio for video using configured provider.

    Args:
        video: Video model with:
            - video.project.audio_mode: "none" | "scene" | "music" | "voiceover" | "auto"
            - video.project.audio_provider: "kling" | "ai_music"
            - video.video_task_id: required for kling provider
            - video.scenario_data: used by ai_music for context

    Returns:
        Dict from provider. Format depends on provider:

        For kling provider:
            - audio_variants: list of video URLs with audio
            - video_with_audio_url: first variant URL
            - provider: "kling"

        For ai_music provider:
            - variants: list of hook dicts with preview URLs
            - full_track_url: URL of full generated track
            - music_prompt: the prompt used for generation
            - provider: "ai_music"

    Raises:
        ValueError: If provider unavailable or required data missing
    """
    logger.info(f"Audio step: generating for video {video.id}")

    # Check if audio should be skipped
    if video.project and video.project.audio_mode == "none":
        logger.info("Audio step: skipped (audio_mode=none)")
        return {
            "audio_variants": [],
            "video_with_audio_url": video.video_url,
            "skipped": True,
        }

    # Get provider name from project settings
    provider_name = None
    if video.project and video.project.audio_provider:
        provider_name = video.project.audio_provider

    # Get provider instance via factory
    try:
        provider = get_audio_provider(provider_name)
    except ValueError as e:
        logger.error(f"Audio step: failed to get provider: {e}")
        raise

    logger.info(f"Audio step: using provider '{provider_name or 'kling'}'")

    # Generate audio via provider
    result = await provider.generate(video)

    logger.info(f"Audio step: completed with provider '{result.get('provider')}'")

    return result
