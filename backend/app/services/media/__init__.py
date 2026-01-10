"""
Media service protocols - provider-agnostic interfaces.
"""
from app.services.media.base import (
    ImageServiceProtocol,
    VideoServiceProtocol,
    AudioServiceProtocol,
)

__all__ = [
    "ImageServiceProtocol",
    "VideoServiceProtocol",
    "AudioServiceProtocol",
]
