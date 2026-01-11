"""
Files API - Serve local media files

Provides endpoints to serve locally stored images and videos.
"""
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.services.media_downloader import MEDIA_BASE_DIR

logger = logging.getLogger(__name__)

router = APIRouter()

# Allowed media types and their MIME types
MIME_TYPES = {
    # Images
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
    # Videos
    "mp4": "video/mp4",
    "mov": "video/quicktime",
    "webm": "video/webm",
}

# Allowed directories
ALLOWED_TYPES = {"images", "videos"}


@router.get("/{file_type}/{filename}")
async def serve_file(file_type: str, filename: str):
    """
    Serve a local media file.

    Args:
        file_type: Type of file (images or videos)
        filename: Name of the file to serve

    Returns:
        FileResponse with appropriate Content-Type
    """
    # Validate file type
    if file_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid file type: {file_type}")

    # Security: prevent path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Build file path
    file_path = MEDIA_BASE_DIR / file_type / filename

    # Check if file exists
    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        raise HTTPException(status_code=404, detail="File not found")

    # Determine MIME type from extension
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    media_type = MIME_TYPES.get(extension, "application/octet-stream")

    logger.debug(f"Serving file: {file_path} as {media_type}")

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename,
        # Cache for 1 year (immutable content)
        headers={"Cache-Control": "public, max-age=31536000, immutable"}
    )
