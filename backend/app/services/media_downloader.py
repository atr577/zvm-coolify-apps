"""
Media Downloader Service

Downloads media files from CDN URLs and saves them locally.
Provides retry logic with exponential backoff.
"""
import os
import time
import httpx
import logging
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Base directory for media storage
MEDIA_BASE_DIR = Path(__file__).parent.parent.parent.parent / "data" / "media"

# Subdirectories for different media types
IMAGES_DIR = MEDIA_BASE_DIR / "images"
VIDEOS_DIR = MEDIA_BASE_DIR / "videos"

# Retry settings
MAX_RETRIES = 3
RETRY_DELAYS = [1, 3, 5]  # seconds between retries (exponential backoff)
DOWNLOAD_TIMEOUT = 120  # seconds


def ensure_directories():
    """Create media directories if they don't exist."""
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)


def get_extension_from_url(url: str) -> str:
    """Extract file extension from URL."""
    parsed = urlparse(url)
    path = parsed.path

    # Try to get extension from path
    if "." in path:
        ext = path.rsplit(".", 1)[-1].lower()
        # Clean up query params if any
        if "?" in ext:
            ext = ext.split("?")[0]
        if ext in ["jpg", "jpeg", "png", "gif", "webp", "mp4", "mov", "webm"]:
            return ext

    # Default extensions
    return "png"  # Will be overridden based on content-type


def get_extension_from_content_type(content_type: str) -> str:
    """Get file extension from Content-Type header."""
    mapping = {
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/png": "png",
        "image/gif": "gif",
        "image/webp": "webp",
        "video/mp4": "mp4",
        "video/quicktime": "mov",
        "video/webm": "webm",
    }
    return mapping.get(content_type.split(";")[0].strip(), "bin")


async def download_file(url: str, dest_path: Path) -> bool:
    """
    Download a file from URL to destination path with retry logic.

    Returns True on success, False on failure.
    """
    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=DOWNLOAD_TIMEOUT) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()

                # Write to file
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                dest_path.write_bytes(response.content)

                logger.info(f"Downloaded {url} to {dest_path} ({len(response.content)} bytes)")
                return True

        except httpx.TimeoutException as e:
            logger.warning(f"Timeout downloading {url} (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error downloading {url} (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
        except Exception as e:
            logger.warning(f"Error downloading {url} (attempt {attempt + 1}/{MAX_RETRIES}): {e}")

        # Wait before retry (except on last attempt)
        if attempt < MAX_RETRIES - 1:
            delay = RETRY_DELAYS[attempt]
            logger.info(f"Retrying in {delay}s...")
            time.sleep(delay)

    logger.error(f"Failed to download {url} after {MAX_RETRIES} attempts")
    return False


def generate_filename(video_id: int, step: str, extension: str) -> str:
    """Generate a unique filename for the media file."""
    timestamp = int(time.time())
    return f"{video_id}_{step}_{timestamp}.{extension}"


async def download_image(url: str, video_id: int) -> Optional[str]:
    """
    Download image from URL and save locally.

    Returns relative path (e.g., "images/123_image_1736600000.png") or None on failure.
    """
    if not url:
        return None

    ensure_directories()

    # Determine extension
    ext = get_extension_from_url(url)
    if ext == "png":  # Default, try to get from content-type
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                head_response = await client.head(url, follow_redirects=True)
                content_type = head_response.headers.get("content-type", "")
                ext = get_extension_from_content_type(content_type)
        except Exception:
            pass  # Keep default extension

    filename = generate_filename(video_id, "image", ext)
    dest_path = IMAGES_DIR / filename

    success = await download_file(url, dest_path)
    if success:
        return f"images/{filename}"
    return None


async def download_video(url: str, video_id: int, step: str = "video") -> Optional[str]:
    """
    Download video from URL and save locally.

    Args:
        url: Video URL to download
        video_id: Video ID for filename
        step: Step name (video or audio) for filename

    Returns relative path (e.g., "videos/123_video_1736600000.mp4") or None on failure.
    """
    if not url:
        return None

    ensure_directories()

    # Determine extension
    ext = get_extension_from_url(url)
    if ext == "png":  # Wrong default for video
        ext = "mp4"

    filename = generate_filename(video_id, step, ext)
    dest_path = VIDEOS_DIR / filename

    success = await download_file(url, dest_path)
    if success:
        return f"videos/{filename}"
    return None


def get_local_file_path(relative_path: str) -> Optional[Path]:
    """
    Get the full filesystem path for a relative media path.

    Returns None if file doesn't exist.
    """
    if not relative_path:
        return None

    full_path = MEDIA_BASE_DIR / relative_path
    if full_path.exists():
        return full_path
    return None


def delete_local_file(relative_path: str) -> bool:
    """
    Delete a local media file.

    Returns True if deleted, False otherwise.
    """
    if not relative_path:
        return False

    full_path = MEDIA_BASE_DIR / relative_path
    try:
        if full_path.exists():
            full_path.unlink()
            logger.info(f"Deleted local file: {relative_path}")
            return True
    except Exception as e:
        logger.error(f"Failed to delete {relative_path}: {e}")
    return False


# Initialize directories on module load
ensure_directories()
