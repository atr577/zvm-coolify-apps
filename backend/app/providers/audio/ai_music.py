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
from pathlib import Path
from typing import Any, Dict, List

from app.core.config import settings

# Directories
TEMP_DIR = Path(settings.TEMP_DIR)
AUDIO_DIR = Path(settings.MEDIA_AUDIO_DIR)
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

    async def generate(self, video, feedback: str = None) -> Dict[str, Any]:
        """
        Generate AI music with hooks for video.

        Args:
            video: Video model with scenario_data, project settings
            feedback: Optional user feedback for regeneration (e.g., "more upbeat")

        Returns:
            Dict with:
                - variants: list of hook dicts with preview URLs
                - tracks: list of generated tracks (Suno returns 2)
                - music_prompt: the prompt used for generation
                - provider: "ai_music"

            Each variant contains:
                - hook: Hook data (start, end, duration, reason, energy, type)
                - preview_url: URL to pre-trimmed audio file
                - video_id: for reference
                - track_index: which track this hook is from (0 or 1)
                - index: hook index within track (0-3)

        Raises:
            RuntimeError: If OPENAI_API_KEY not configured
            ValueError: On generation or analysis failures
        """
        logger.info(f"AiMusicProvider: generating for video {video.id}, feedback={feedback}")

        # Check if audio should be skipped
        if video.project and video.project.audio_mode == "none":
            logger.info("AiMusicProvider: skipped (audio_mode=none)")
            return {
                "variants": [],
                "tracks": [],
                "music_prompt": None,
                "provider": "ai_music",
                "skipped": True,
            }

        # Get hook duration from project (default 5 seconds)
        hook_duration = video.project.duration if video.project else 5.0

        # Get previous music_prompt for feedback context
        previous_prompt = None
        if feedback and video.audio_data:
            previous_prompt = video.audio_data.get("music_prompt")

        # Step 1 & 2: Generate music prompt and tracks (Suno returns 2 variations)
        logger.info("AiMusicProvider: generating music prompt and tracks...")
        music_prompt, tracks, tags = await self.music_generator.generate_for_video(
            video=video,
            feedback=feedback,
            previous_prompt=previous_prompt,
        )
        logger.info(f"AiMusicProvider: got {len(tracks)} tracks, tags={tags}")

        # Process each track: download, find hooks, trim
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        all_variants = []
        global_index = 0

        for track_index, track in enumerate(tracks):
            track_url = track.get("audio_url")
            track_title = track.get("title", f"Track {track_index + 1}")

            if not track_url:
                logger.warning(f"Track {track_index} has no audio_url, skipping")
                continue

            logger.info(f"AiMusicProvider: processing track {track_index + 1}/{len(tracks)}: {track_title}")

            # Step 3: Download track to temp storage
            local_track_path = await self.media_processor.download_file(
                url=track_url,
                dest_path=str(TEMP_DIR / f"track_{video.id}_{track_index}_{os.urandom(4).hex()}.mp3"),
            )

            # Step 4: Find best hooks using GPT-4o-audio-preview
            logger.info(f"AiMusicProvider: analyzing track {track_index + 1} for hooks...")
            hooks = await self.hook_analyzer.find_hooks(
                audio_path=local_track_path,
                video=video,
                num_hooks=4,
                hook_duration=float(hook_duration),
            )

            # Step 5: Pre-trim all hooks with fade in/out
            logger.info(f"AiMusicProvider: trimming {len(hooks)} hooks from track {track_index + 1}...")
            variants = await self._trim_hooks(
                video_id=video.id,
                local_track_path=local_track_path,
                hooks=hooks,
                track_index=track_index,
                track_title=track_title,
                global_index_start=global_index,
            )

            all_variants.extend(variants)
            global_index += len(variants)

            # Cleanup: remove downloaded track (variants have their own files)
            try:
                os.remove(local_track_path)
            except OSError:
                pass

        logger.info(
            f"AiMusicProvider: generated {len(all_variants)} variants from {len(tracks)} tracks for video {video.id}"
        )

        return {
            "variants": all_variants,
            "tracks": tracks,
            "music_prompt": music_prompt,
            "tags": tags,
            "provider": "ai_music",
        }

    async def _trim_hooks(
        self,
        video_id: int,
        local_track_path: str,
        hooks: List[Hook],
        track_index: int = 0,
        track_title: str = "Track",
        global_index_start: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Trim all hooks and create variant records.

        Args:
            video_id: Video ID for naming
            local_track_path: Path to downloaded full track
            hooks: List of Hook objects to trim
            track_index: Index of the track (0 or 1 for Suno)
            track_title: Title of the track from Suno
            global_index_start: Starting index for global variant numbering

        Returns:
            List of variant dicts with preview URLs
        """
        variants = []
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)

        for i, hook in enumerate(hooks):
            global_idx = global_index_start + i
            # Generate unique filename: {video_id}_t{track}_hook_{index}_{start}_{end}.mp3
            output_filename = (
                f"{video_id}_t{track_index}_hook_{i}_{int(hook.start)}_{int(hook.end)}.mp3"
            )
            output_path = str(AUDIO_DIR / output_filename)

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
                        "index": global_idx,  # Global index across all tracks
                        "track_index": track_index,  # Which track (0 or 1)
                        "track_title": track_title,  # Track title from Suno
                        "hook_index": i,  # Hook index within this track (0-3)
                    }
                )

                logger.debug(
                    f"Trimmed track {track_index} hook {i}: {hook.start:.1f}-{hook.end:.1f}s -> {output_filename}"
                )

            except Exception as e:
                logger.error(f"Failed to trim track {track_index} hook {i}: {e}")
                # Continue with other hooks

        return variants
