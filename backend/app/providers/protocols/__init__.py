"""Protocol definitions for providers."""

from app.providers.protocols.audio import AudioProviderProtocol
from app.providers.protocols.video import VideoProviderProtocol

__all__ = ["AudioProviderProtocol", "VideoProviderProtocol"]
