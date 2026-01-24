"""
DEPRECATED: KLING Audio Provider

Kling Sound API is not available with Veo 3.1.
Use AIMusicProvider (Lyria2) instead.
"""

import logging
from typing import Any, Dict

from app.services.media_service import media_service

logger = logging.getLogger(__name__)


class KlingAudioProvider:
    """
    DEPRECATED: KLING audio provider.

    Kling Sound API is not available with Veo 3.1.
    This provider now returns empty variants.
    Use AIMusicProvider with Lyria2 instead.
    """

    async def generate(self, video, feedback: str = None) -> Dict[str, Any]:
        """
        DEPRECATED: Generate audio for video.

        This method is deprecated. Use AIMusicProvider instead.
        Returns empty variants to avoid breaking existing code.
        """
        logger.warning(
            "KlingAudioProvider is DEPRECATED. "
            "Kling Sound API not available with Veo 3.1. "
            "Use ai_music provider (Lyria2) instead."
        )

        # Check if audio should be skipped
        if video.project and video.project.audio_mode == "none":
            logger.info("KlingAudioProvider: skipped (audio_mode=none)")
            return {
                "audio_variants": [],
                "video_with_audio_url": video.video_url,
                "provider": "kling",
                "skipped": True,
            }

        # Return video without audio since Kling Sound is not available
        return {
            "audio_variants": [],
            "video_with_audio_url": video.video_url,
            "provider": "kling",
            "deprecated": True,
            "message": "Kling Sound API not available with Veo 3.1. Use ai_music provider.",
        }
