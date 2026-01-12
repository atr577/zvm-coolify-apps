"""
Audio providers package.

Providers:
- KlingAudioProvider: Sound effects via KLING API
- AiMusicProvider: AI-generated music with hook analysis
"""

from app.providers.audio.kling import KlingAudioProvider

__all__ = ["KlingAudioProvider"]

# AiMusicProvider is lazy-loaded in factory (requires OPENAI_API_KEY)
