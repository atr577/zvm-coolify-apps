"""
DEPRECATED: KLING Service - now redirects to media_service

This module is kept for backward compatibility.
Use media_service directly instead.
"""

import warnings
from app.services.media_service import media_service, MediaService

# Show deprecation warning
warnings.warn(
    "kling_service is deprecated. Use media_service instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export for backward compatibility
kling_service = media_service
KlingService = MediaService
