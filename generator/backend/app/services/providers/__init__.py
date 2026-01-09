"""
Media service providers.

Each provider implements the protocols from app.services.media.base
"""
from app.services.providers.kling import (
    KlingImageService,
    KlingVideoService,
    KlingAudioService,
)

__all__ = [
    "KlingImageService",
    "KlingVideoService",
    "KlingAudioService",
]
