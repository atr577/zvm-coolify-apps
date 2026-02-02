"""URL utilities for media files."""


def get_local_url(local_path: str | None, remote_url: str | None) -> str | None:
    """Return local file URL if available, otherwise fall back to remote URL.

    Args:
        local_path: Local file path relative to MEDIA_DIR (e.g., "images/123.png")
        remote_url: Remote CDN URL as fallback

    Returns:
        Local URL (/api/files/...) if local_path exists, otherwise remote_url
    """
    if local_path:
        return f"/api/files/{local_path}"
    return remote_url
