"""
Providers package - pluggable service providers for media generation.

Architecture:
- protocols/ - Protocol definitions for type safety
- audio/ - Audio providers (kling, ai_music, future: suno, epidemic, etc.)
- video/ - Video providers (kling, future: runway, etc.)
- image/ - Image providers (kling)

Usage:
    from app.providers.factory import get_audio_provider, get_video_provider

    provider = get_audio_provider("ai_music")
    result = await provider.generate(video)
"""

from app.providers.factory import get_audio_provider, get_video_provider

__all__ = ["get_audio_provider", "get_video_provider"]
