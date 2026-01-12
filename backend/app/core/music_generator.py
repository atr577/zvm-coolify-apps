"""
Music Generator - AI music generation from video context.

Generates music prompts based on video scenario and creates
full tracks using music-u (Udio) via PiAPI.
"""

import logging
from typing import Optional

from app.services.piapi_client import piapi_client

logger = logging.getLogger(__name__)

# System prompt for music prompt generation
MUSIC_PROMPT_SYSTEM = """You are an expert music director for short-form viral videos.
Your task is to create a music prompt for AI music generation.

The music must:
1. Match the mood and energy of the video scene
2. Be catchy and memorable (hook-worthy)
3. Work well for short clips (5-15 seconds)
4. Be suitable for the target platforms

Output a concise music description (2-3 sentences max) that includes:
- Genre/style (e.g., "80s synthpop", "lo-fi hip hop", "epic orchestral")
- Mood/energy (e.g., "energetic", "chill", "dramatic")
- Key characteristics (e.g., "catchy melody", "strong beat", "atmospheric")

Do NOT include:
- Lyrics or vocal descriptions (we want instrumental)
- Specific artist names
- Technical music terms (BPM, key signatures)

Example outputs:
- "Upbeat 80s synthpop with energetic drums and catchy synth melody. Nostalgic summer vibes."
- "Dark cinematic trap with heavy 808s and atmospheric pads. Mysterious and powerful."
- "Bright indie pop with acoustic guitar and uplifting energy. Feel-good summer anthem."
"""


class MusicGenerator:
    """Generates AI music from video context."""

    async def generate_prompt(self, video) -> str:
        """
        Generate a music prompt based on video context.

        Uses GPT to analyze the scenario and create an appropriate
        music description for AI music generation.

        Args:
            video: Video model with scenario_data, project settings

        Returns:
            Music prompt string for music-u API
        """
        # Extract context from video
        scenario = video.scenario_data or {}
        project = video.project

        # Build context for GPT
        scene_description = scenario.get("scene_description", "")
        mood = scenario.get("mood", "")
        visual_style = scenario.get("visual_style", "")

        # Project settings
        platforms = project.platforms if project else ["instagram"]
        duration = project.duration if project else 5

        # Build user prompt
        user_prompt = f"""Create a music prompt for this video:

Scene: {scene_description or video.description_data or "Short viral video"}
Mood: {mood or "energetic"}
Visual style: {visual_style or "modern, vibrant"}
Platforms: {', '.join(platforms)}
Duration: {duration} seconds

Generate a concise music description (instrumental only)."""

        logger.info(f"Generating music prompt for video {video.id}")

        # Call GPT via PiAPI
        response = await piapi_client.generate_text(
            prompt=user_prompt,
            system_prompt=MUSIC_PROMPT_SYSTEM,
            temperature=0.8,  # Some creativity for variety
        )

        music_prompt = response.strip()
        logger.info(f"Generated music prompt: {music_prompt[:100]}...")

        return music_prompt

    async def generate_track(
        self,
        prompt: str,
        lyrics_type: str = "instrumental",
        seed: int = -1,
    ) -> str:
        """
        Generate a full music track using music-u API.

        Args:
            prompt: Music description
            lyrics_type: "instrumental" or "generate"
            seed: Random seed (-1 for random)

        Returns:
            Audio URL (mp3)
        """
        logger.info(f"Generating track: {prompt[:50]}...")

        audio_url = await piapi_client.generate_music(
            prompt=prompt,
            lyrics_type=lyrics_type,
            seed=seed,
        )

        logger.info(f"Track generated: {audio_url}")
        return audio_url

    async def generate_for_video(
        self,
        video,
        lyrics_type: str = "instrumental",
    ) -> tuple[str, str]:
        """
        High-level method: generate music prompt and track for a video.

        Args:
            video: Video model
            lyrics_type: "instrumental" or "generate"

        Returns:
            Tuple of (music_prompt, audio_url)
        """
        # Generate prompt from video context
        music_prompt = await self.generate_prompt(video)

        # Generate track
        audio_url = await self.generate_track(
            prompt=music_prompt,
            lyrics_type=lyrics_type,
        )

        return music_prompt, audio_url


# Singleton instance
music_generator = MusicGenerator()
