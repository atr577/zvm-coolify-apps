"""
Hook Analyzer - Find best audio hooks using GPT-4o-audio-preview.

Analyzes music tracks to find the most impactful segments
for short-form video content.
"""

import base64
import json
import logging
from dataclasses import dataclass, asdict
from typing import List, Optional

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.media_processor import media_processor

logger = logging.getLogger(__name__)


@dataclass
class Hook:
    """Represents a hook segment in an audio track."""

    start: float  # Start time in seconds
    end: float  # End time in seconds
    duration: float  # Duration (end - start)
    reason: str  # Why this is a good hook
    energy: str  # Energy level: low, medium, high
    type: str  # Hook type: chorus, drop, bridge, intro, etc.

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


# System prompt for hook analysis
HOOK_ANALYSIS_PROMPT = """You are an expert music editor for viral short-form videos.
Analyze this audio track and find the BEST hooks for a {duration}-second video.

A good hook should:
1. Have instant impact (grab attention in first 0.5 seconds)
2. Be energetic and memorable
3. Work well when trimmed to exactly {duration} seconds
4. Match the video mood: {mood}

Video context:
{context}

Find {num_hooks} different hooks at different parts of the track.
For each hook, provide:
- start: exact start time in seconds (e.g., 73.5)
- end: exact end time in seconds (start + {duration})
- reason: why this segment works as a hook (1 sentence)
- energy: "low", "medium", or "high"
- type: "chorus", "drop", "bridge", "intro", "verse", or "outro"

IMPORTANT:
- Timestamps must be precise (to 0.1 second)
- Each hook must be exactly {duration} seconds
- Hooks should be from different parts of the track
- Prefer high-energy sections with clear beats

Respond in JSON format:
{{
    "hooks": [
        {{"start": 73.0, "end": 78.0, "reason": "...", "energy": "high", "type": "chorus"}},
        ...
    ]
}}
"""


class HookAnalyzer:
    """Analyzes audio to find best hooks using GPT-4o-audio-preview."""

    def __init__(self):
        """Initialize with OpenAI client."""
        self.client: Optional[AsyncOpenAI] = None
        self._init_client()

    def _init_client(self):
        """Initialize OpenAI client if API key is available."""
        if settings.OPENAI_API_KEY:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("HookAnalyzer: OpenAI client initialized")
        else:
            logger.warning("HookAnalyzer: OPENAI_API_KEY not set, hook analysis unavailable")

    async def find_hooks(
        self,
        audio_path: str,
        video,
        num_hooks: int = 4,
        hook_duration: float = 5.0,
    ) -> List[Hook]:
        """
        Find best hooks in an audio track.

        Args:
            audio_path: Path to audio file (mp3)
            video: Video model for context
            num_hooks: Number of hooks to find (default 4)
            hook_duration: Duration of each hook in seconds (default 5)

        Returns:
            List of Hook objects sorted by energy (highest first)

        Raises:
            RuntimeError: If OpenAI client not initialized
            ValueError: If audio analysis fails
        """
        if not self.client:
            raise RuntimeError(
                "HookAnalyzer not available: OPENAI_API_KEY not configured"
            )

        # Get audio duration for context
        total_duration = await media_processor.get_audio_duration(audio_path)
        logger.info(f"Analyzing audio: {audio_path} ({total_duration:.1f}s)")

        # Read and encode audio
        with open(audio_path, "rb") as f:
            audio_data = f.read()
        audio_b64 = base64.b64encode(audio_data).decode()

        # Build context from video
        scenario = video.scenario_data or {}
        context = self._build_context(video, scenario)
        mood = scenario.get("mood", "energetic")

        # Build prompt
        prompt = HOOK_ANALYSIS_PROMPT.format(
            duration=hook_duration,
            mood=mood,
            context=context,
            num_hooks=num_hooks,
        )

        logger.info(f"Sending audio to GPT-4o-audio-preview ({len(audio_data)} bytes)")

        try:
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_AUDIO_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_audio",
                                "input_audio": {
                                    "data": audio_b64,
                                    "format": "mp3",
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt,
                            },
                        ],
                    }
                ],
                response_format={"type": "json_object"},
            )

            # Parse response
            content = response.choices[0].message.content
            result = json.loads(content)
            hooks_data = result.get("hooks", [])

            if not hooks_data:
                logger.warning("No hooks found in response, using fallback")
                return self._create_fallback_hook(total_duration, hook_duration)

            # Convert to Hook objects
            hooks = []
            for h in hooks_data:
                hook = Hook(
                    start=float(h["start"]),
                    end=float(h["end"]),
                    duration=float(h["end"]) - float(h["start"]),
                    reason=h.get("reason", "Good hook segment"),
                    energy=h.get("energy", "medium"),
                    type=h.get("type", "unknown"),
                )
                # Validate hook is within track bounds
                if hook.start >= 0 and hook.end <= total_duration:
                    hooks.append(hook)

            if not hooks:
                logger.warning("All hooks out of bounds, using fallback")
                return self._create_fallback_hook(total_duration, hook_duration)

            # Sort by energy (high first)
            energy_order = {"high": 0, "medium": 1, "low": 2}
            hooks.sort(key=lambda h: energy_order.get(h.energy, 1))

            logger.info(f"Found {len(hooks)} hooks")
            for i, h in enumerate(hooks):
                logger.debug(f"  Hook {i+1}: {h.start:.1f}-{h.end:.1f}s ({h.type}, {h.energy})")

            return hooks

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse hook response: {e}")
            return self._create_fallback_hook(total_duration, hook_duration)
        except Exception as e:
            logger.error(f"Hook analysis failed: {e}")
            raise ValueError(f"Audio analysis failed: {e}")

    def _build_context(self, video, scenario: dict) -> str:
        """Build context string from video data."""
        parts = []

        if scenario.get("scene_description"):
            parts.append(f"Scene: {scenario['scene_description']}")
        elif video.description_data:
            desc = video.description_data
            if isinstance(desc, dict):
                parts.append(f"Scene: {desc.get('description', '')}")
            else:
                parts.append(f"Scene: {desc}")

        if scenario.get("visual_style"):
            parts.append(f"Style: {scenario['visual_style']}")

        if video.project:
            parts.append(f"Platforms: {', '.join(video.project.platforms or [])}")
            parts.append(f"Video duration: {video.project.duration}s")

        return "\n".join(parts) if parts else "Short viral video"

    def _create_fallback_hook(
        self,
        total_duration: float,
        hook_duration: float,
    ) -> List[Hook]:
        """
        Create fallback hook using full track if analysis fails.

        Returns single hook from beginning of track.
        """
        logger.info("Creating fallback hook (full track start)")

        # Use beginning of track
        start = 0.0
        end = min(hook_duration, total_duration)

        return [
            Hook(
                start=start,
                end=end,
                duration=end - start,
                reason="Fallback: start of track",
                energy="medium",
                type="intro",
            )
        ]


# Singleton instance
hook_analyzer = HookAnalyzer()
