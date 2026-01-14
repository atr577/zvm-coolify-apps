"""
Music Generator - AI music generation from video context.

Generates music prompts based on video scenario and creates
full tracks using Suno or music-u (Udio) via PiAPI.

Provider controlled by settings.MUSIC_MODEL:
- "suno" (default): Suno v4
- "music-u": Udio
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.services.piapi_client import piapi_client

logger = logging.getLogger(__name__)

# System prompt for music prompt generation
MUSIC_PROMPT_SYSTEM = """ЧТО ТЫ ДЕЛАЕШЬ:
Ты получаешь описание видео-сцены.
Ты пишешь промпт для Suno AI чтобы он сгенерировал музыкальный трек с вокалом.
Музыка будет наложена на это видео.
Вокал должен петь про то, что происходит в видео.

ТВОЯ ЗАДАЧА:
1. Понять историю/настроение сцены из описания
2. Описать какой трек нужен — жанр, вокал, энергия
3. Указать контекст (о чём сцена)
4. Придумать короткую фразу-хук которая застрянет в голове

РЕЗУЛЬТАТ — JSON:
{
  "music_prompt": "описание трека для Suno (1-2 предложения)",
  "tags": "3-5 тегов через запятую"
}

ЦЕЛЬ МУЗЫКИ:
- Зацепить с первой секунды — у зрителя палец на скролле
- Earworm — фраза хука застревает в голове
- Вокал усиливает то, что происходит на видео

ФОРМУЛА ДЛЯ music_prompt:
[жанр] + [вокал] + [контекст] + [фраза хука] + [энергия]

Где:
- жанр: поджанр (synth-pop, indie pop, trap, drill, house, edm)
- вокал: характер + пол (breathy female, raspy male, powerful female, soft male)
- контекст: сеттинг из видео (about dancing at night, about running through city)
- фраза хука: короткая earworm в кавычках (hook: 'let it go', hook: 'never stop')
- энергия: темп или ощущение (high energy, pulsing, 110 BPM, atmospheric)

ПРАВИЛА ДЛЯ tags:
3-5 тегов через запятую: жанр, энергия, тип вокала, настроение

НЕ ИСПОЛЬЗОВАТЬ в tags: "viral", "tiktok", "hook" — Suno не понимает эти слова.

ПРИМЕРЫ:

Вход: woman dancing alone in neon club, slow motion, 5 sec
{
  "music_prompt": "Dark synth-pop with breathy female vocals about dancing at night. Catchy hook: 'lose yourself'. Pulsing, 100 BPM.",
  "tags": "synth-pop, dark, breathy female vocals, pulsing, emotional"
}

Вход: man running through city at sunrise, fast dynamic, 5 sec
{
  "music_prompt": "Aggressive trap with confident male vocals about chasing the moment. Hook: 'never stop'. 808s, high energy.",
  "tags": "trap, aggressive, male vocals, 808s, motivational"
}

Вход: couple watching sunset on beach, slow romantic, 10 sec
{
  "music_prompt": "Dreamy indie pop with soft male vocals about endless summer love. Hook: 'stay with me'. Atmospheric, gentle.",
  "tags": "indie pop, dreamy, soft male vocals, romantic, atmospheric"
}
"""


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

        # Call GPT via PiAPI with JSON output
        result = await piapi_client.generate_json(
            prompt=user_prompt,
            system_prompt=MUSIC_PROMPT_SYSTEM,
            temperature=0.8,
        )

        # Handle unexpected response format (list instead of dict)
        if isinstance(result, list):
            result = result[0] if result else {}
        if not isinstance(result, dict):
            logger.warning(f"Unexpected GPT response format: {type(result)}, using defaults")
            result = {}

        music_prompt = result.get("music_prompt", "Powerful vocal hook with catchy melody")
        tags = result.get("tags", "pop, energetic, female vocals, catchy")

        logger.info(f"Generated music prompt: {music_prompt[:80]}... (tags={tags})")

        return music_prompt, tags

    async def generate_track(
        self,
        prompt: str,
        tags: str = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate music tracks using configured provider.

        Provider is determined by settings.MUSIC_MODEL:
        - "suno": Suno v5 (2 track variations per request)
        - "music-u": Udio (1 track)

        Always generates with vocals (make_instrumental=False).

        Args:
            prompt: Music description
            tags: Genre/style tags (Suno only, strongly affects output)

        Returns:
            List of track dicts with audio_url, title, duration
        """
        provider = settings.MUSIC_MODEL
        logger.info(f"Generating track via {provider} (tags={tags}): {prompt[:50]}...")

        if provider == "suno":
            # Suno returns list of tracks (2 variations)
            tracks = await piapi_client.generate_music_suno(
                prompt=prompt,
                make_instrumental=False,  # Always vocals
                tags=tags,
            )
        else:
            # music-u (Udio) - returns single URL, wrap in list for consistency
            audio_url = await piapi_client.generate_music(
                prompt=prompt,
                lyrics_type="generate",  # Always vocals
            )
            tracks = [{"audio_url": audio_url, "title": "Track", "duration": 0}]

        logger.info(f"Generated {len(tracks)} tracks via {provider}")
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
