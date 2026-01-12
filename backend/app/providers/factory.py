"""
Provider Factory.

Centralized factory for getting provider instances by name.
Supports runtime provider selection based on project configuration.
"""

import logging
from typing import Optional

from app.providers.protocols.audio import AudioProviderProtocol
from app.providers.protocols.video import VideoProviderProtocol

logger = logging.getLogger(__name__)


def get_audio_provider(name: Optional[str] = None) -> AudioProviderProtocol:
    """
    Get audio provider by name.

    Args:
        name: Provider name ("kling" or "ai_music"). Defaults to "kling".

    Returns:
        AudioProviderProtocol implementation

    Raises:
        ValueError: If provider name is unknown or unavailable
    """
    # Lazy imports to avoid circular dependencies
    from app.providers.audio.kling import KlingAudioProvider

    # Default to kling
    if not name:
        name = "kling"

    providers = {
        "kling": KlingAudioProvider,
    }

    # Check for ai_music provider (requires OPENAI_API_KEY)
    if name == "ai_music":
        from app.core.audio_config import is_ai_music_available

        if not is_ai_music_available():
            raise ValueError(
                "ai_music provider unavailable: OPENAI_API_KEY not configured"
            )

        from app.providers.audio.ai_music import AiMusicProvider

        providers["ai_music"] = AiMusicProvider

    if name not in providers:
        available = list(providers.keys())
        raise ValueError(f"Unknown audio provider: {name}. Available: {available}")

    logger.debug(f"Creating audio provider: {name}")
    return providers[name]()


def get_video_provider(name: Optional[str] = None) -> VideoProviderProtocol:
    """
    Get video provider by name.

    Args:
        name: Provider name. Currently only "kling" is supported.

    Returns:
        VideoProviderProtocol implementation

    Raises:
        ValueError: If provider name is unknown
    """
    # Default to kling
    if not name:
        name = "kling"

    # Currently only kling is supported for video
    # Future: add runway, pika, etc.
    if name != "kling":
        raise ValueError(f"Unknown video provider: {name}. Available: ['kling']")

    # For now, video generation still uses kling_service directly
    # This factory is prep for future providers
    logger.debug(f"Creating video provider: {name}")

    # Placeholder - will implement KlingVideoProvider when needed
    raise NotImplementedError(
        "Video provider factory not yet implemented. "
        "Use kling_service directly for now."
    )
