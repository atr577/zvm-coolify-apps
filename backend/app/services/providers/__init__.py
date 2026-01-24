"""
Media service providers.

Each provider implements the protocols from app.services.media.base
"""
from app.services.providers.falai import (
    FalImageService,
    FalVideoService,
    FalAudioService,
)

__all__ = [
    "FalImageService",
    "FalVideoService",
    "FalAudioService",
]
