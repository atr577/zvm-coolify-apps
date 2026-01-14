"""
Audio Provider Protocol.

All audio providers must implement this protocol.
Signature matches existing image.py and video.py pattern.
"""

from typing import Any, Dict, Protocol, runtime_checkable


@runtime_checkable
class AudioProviderProtocol(Protocol):
    """
    Protocol for audio generation providers.

    Implementations:
    - KlingAudioProvider: Sound effects via KLING API
    - AiMusicProvider: AI-generated music via music-u + hook analysis

    Future:
    - SunoProvider: AI music via Suno API
    - EpidemicSoundProvider: Licensed music catalog
    """

    async def generate(self, video, feedback: str = None) -> Dict[str, Any]:
        """
        Generate audio for a video.

        Args:
            video: Video model instance with:
                - video.scenario_data: Dict with scene description, mood
                - video.project.audio_mode: "none" | "scene" | "music" | "voiceover" | "auto"
                - video.project.audio_provider: "kling" | "ai_music"
                - video.project.duration: int (5 or 10 seconds)
                - video.project.platforms: list[str]
                - video.video_url: str (for merge)
            feedback: Optional user feedback for regeneration (e.g., "more upbeat")

        Returns:
            Dict with provider-specific content:
            - For kling: {"audio_url": str, "video_with_audio_url": str}
            - For ai_music: {"variants": list[dict], "full_track_url": str}
              where each variant has: hook, preview_url, full_track_url, music_prompt

        Raises:
            ValueError: If required data is missing
            Exception: On API or processing errors (will fail the step)
        """
        ...
