"""
AI Music Provider - AI-generated music with hook analysis.

Composes:
- MusicGenerator: Generate music prompt (GPT) + full track (music-u)
- HookAnalyzer: Find best hooks using GPT-4o-audio-preview
- MediaProcessor: Download + trim hooks with fade in/out

Returns multiple hook variants for user selection.
Final merge happens after user approval.
"""

import logging
import os
from typing import Any, Dict, List

from app.core.config import settings
from app.core.hook_analyzer import Hook, hook_analyzer
from app.core.media_processor import media_processor
from app.core.music_generator import music_generator

logger = logging.getLogger(__name__)


class AiMusicProvider:
    """
    AI Music provider with hook analysis.

    Flow:
    1. Generate music prompt from video context (GPT)
    2. Generate full track from prompt (music-u via PiAPI)
    3. Download track to temp storage
    4. Find best hooks using GPT-4o-audio-preview
    5. Pre-trim all hooks with fade in/out
    6. Return variants for user selection

    Note: Requires OPENAI_API_KEY for hook analysis.
    """

    def __init__(self):
        """Initialize provider with required services."""
        self.music_generator = music_generator
        self.hook_analyzer = hook_analyzer
        self.media_processor = media_processor

    async def generate(self, video) -> Dict[str, Any]:
        """
        Generate AI music with hooks for video.

        Args:
            video: Video model with scenario_data, project settings

        Returns:
            Dict with:
                - variants: list of hook dicts with preview URLs
                - full_track_url: URL of the full generated track
                - music_prompt: the prompt used for generation
                - provider: "ai_music"

            Each variant contains:
                - hook: Hook data (start, end, duration, reason, energy, type)
                - preview_url: URL to pre-trimmed audio file
                - video_id: for reference

        Raises:
            RuntimeError: If OPENAI_API_KEY not configured
            ValueError: On generation or analysis failures
        """
        logger.info(f"AiMusicProvider: generating for video {video.id}")

        # Check if audio should be skipped
        if video.project and video.project.audio_mode == "none":
            logger.info("AiMusicProvider: skipped (audio_mode=none)")
            return {
                "variants": [],
                "full_track_url": None,
                "music_prompt": None,
                "provider": "ai_music",
                "skipped": True,
            }

        # Get hook duration from project (default 5 seconds)
        hook_duration = video.project.duration if video.project else 5.0

        # Step 1 & 2: Generate music prompt and full track
        logger.info("AiMusicProvider: generating music prompt and track...")
        music_prompt, full_track_url = await self.music_generator.generate_for_video(
            video=video,
            lyrics_type="instrumental",
        )

        # Step 3: Download track to temp storage
        logger.info("AiMusicProvider: downloading full track...")
        local_track_path = await self.media_processor.download_file(
            url=full_track_url,
            dest_path=str(
                settings.TEMP_DIR
                + f"/track_{video.id}_{os.urandom(4).hex()}.mp3"
            ),
        )

        # Step 4: Find best hooks using GPT-4o-audio-preview
        logger.info("AiMusicProvider: analyzing for hooks...")
        hooks = await self.hook_analyzer.find_hooks(
            audio_path=local_track_path,
            video=video,
            num_hooks=4,
            hook_duration=float(hook_duration),
        )

        # Step 5: Pre-trim all hooks with fade in/out
        logger.info(f"AiMusicProvider: trimming {len(hooks)} hooks...")
        variants = await self._trim_hooks(
            video_id=video.id,
            local_track_path=local_track_path,
            hooks=hooks,
        )

        # Cleanup: remove downloaded track (variants have their own files)
        try:
            os.remove(local_track_path)
        except OSError:
            pass

        logger.info(
            f"AiMusicProvider: generated {len(variants)} variants for video {video.id}"
        )

        return {
            "variants": variants,
            "full_track_url": full_track_url,
            "music_prompt": music_prompt,
            "provider": "ai_music",
        }

    async def _trim_hooks(
        self,
        video_id: int,
        local_track_path: str,
        hooks: List[Hook],
    ) -> List[Dict[str, Any]]:
        """
        Trim all hooks and create variant records.

        Args:
            video_id: Video ID for naming
            local_track_path: Path to downloaded full track
            hooks: List of Hook objects to trim

        Returns:
            List of variant dicts with preview URLs
        """
        variants = []

        for i, hook in enumerate(hooks):
            # Generate unique filename: {video_id}_hook_{index}_{start}_{end}.mp3
            output_filename = (
                f"{video_id}_hook_{i}_{int(hook.start)}_{int(hook.end)}.mp3"
            )
            output_path = str(settings.TEMP_DIR + f"/{output_filename}")

            try:
                # Trim with fade in/out
                trimmed_path = await self.media_processor.trim_audio(
                    audio_path=local_track_path,
                    start=hook.start,
                    end=hook.end,
                    fade_in=0.5,
                    fade_out=0.5,
                    output_path=output_path,
                )

                # Build preview URL (served via /api/files/audio/{filename})
                preview_url = f"/api/files/audio/{output_filename}"

                variants.append(
                    {
                        "hook": hook.to_dict(),
                        "preview_url": preview_url,
                        "local_path": trimmed_path,
                        "video_id": video_id,
                        "index": i,
                    }
                )

                logger.debug(
                    f"Trimmed hook {i}: {hook.start:.1f}-{hook.end:.1f}s -> {output_filename}"
                )

            except Exception as e:
                logger.error(f"Failed to trim hook {i}: {e}")
                # Continue with other hooks

        return variants
