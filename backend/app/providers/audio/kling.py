"""
KLING Audio Provider - Sound effects via KLING API.

Uses video task_id to add scene-appropriate audio via KLING Sound.
Returns 4 audio variants.
"""

import logging
from typing import Any, Dict

from app.services.kling_service import kling_service

logger = logging.getLogger(__name__)


class KlingAudioProvider:
    """
    KLING audio provider.

    Uses KLING Sound API to add scene-appropriate audio to videos.
    Requires video_task_id from video generation step.
    Returns 4 variants with different audio tracks.
    """

    async def generate(self, video, feedback: str = None) -> Dict[str, Any]:
        """
        Generate audio for video using KLING Sound.

        Args:
            video: Video model with video_task_id
            feedback: Optional user feedback (not used by KLING)

        Returns:
            Dict with:
                - audio_variants: list of video URLs with audio
                - video_with_audio_url: first variant URL
                - provider: "kling"

        Raises:
            ValueError: If video_task_id not found
        """
        # Note: feedback not used by KLING Sound API
        logger.info(f"KlingAudioProvider: generating for video {video.id}")

        # Check if audio should be skipped
        if video.project and video.project.audio_mode == "none":
            logger.info("KlingAudioProvider: skipped (audio_mode=none)")
            return {
                "audio_variants": [],
                "video_with_audio_url": video.video_url,
                "provider": "kling",
                "skipped": True,
            }

        # Get task_id from video generation
        task_id = video.video_task_id
        if not task_id:
            raise ValueError("video_task_id not found. Run video step first.")

        # Generate audio variants via KLING Sound
        audio_variants = await kling_service.add_audio_to_video(task_id)

        logger.info(f"KlingAudioProvider: generated {len(audio_variants)} variants")

        # First variant is the default
        video_with_audio_url = audio_variants[0] if audio_variants else video.video_url

        return {
            "audio_variants": audio_variants,
            "video_with_audio_url": video_with_audio_url,
            "provider": "kling",
        }
