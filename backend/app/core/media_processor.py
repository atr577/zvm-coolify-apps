"""
Media Processor - FFmpeg operations for audio/video processing.

Shared utility for all audio providers. Handles:
- Downloading remote files
- Getting audio duration (FFprobe)
- Trimming audio with fade in/out
- Merging video + audio
- Temp file cleanup
"""

import asyncio
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Directories from settings
TEMP_DIR = Path(settings.TEMP_DIR)
MEDIA_DIR = Path(settings.MEDIA_DIR)
AUDIO_DIR = Path(settings.MEDIA_AUDIO_DIR)
VIDEOS_DIR = Path(settings.MEDIA_VIDEOS_DIR)


class MediaProcessor:
    """FFmpeg-based media processor for audio operations."""

    def __init__(self):
        """Initialize media processor and ensure directories exist."""
        self._ensure_directories()

    def _ensure_directories(self):
        """Create required directories if they don't exist."""
        for dir_path in [TEMP_DIR, AUDIO_DIR, VIDEOS_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)

    async def check_ffmpeg_available(self) -> bool:
        """
        Check if FFmpeg is available on the system.

        Returns:
            True if FFmpeg is available, False otherwise
        """
        try:
            process = await asyncio.create_subprocess_exec(
                "ffmpeg", "-version",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await process.wait()
            return process.returncode == 0
        except FileNotFoundError:
            return False

    async def download_file(self, url: str, dest_path: Optional[str] = None) -> str:
        """
        Download a file from URL to local path.

        Args:
            url: Remote URL to download
            dest_path: Local path to save file. If None, generates temp path.

        Returns:
            Local file path

        Raises:
            httpx.HTTPError: On download failure
        """
        if dest_path is None:
            # Generate temp filename from URL
            ext = url.split(".")[-1].split("?")[0][:4] or "bin"
            dest_path = str(TEMP_DIR / f"download_{int(time.time())}_{os.urandom(4).hex()}.{ext}")

        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Downloading {url[:80]}... to {dest_path}")

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()

            with open(dest, "wb") as f:
                f.write(response.content)

        logger.info(f"Downloaded {len(response.content)} bytes to {dest_path}")
        return str(dest)

    async def get_audio_duration(self, audio_path: str) -> float:
        """
        Get duration of an audio file using FFprobe.

        Args:
            audio_path: Path to audio file

        Returns:
            Duration in seconds

        Raises:
            RuntimeError: If FFprobe fails
        """
        process = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"FFprobe failed: {stderr.decode()}")

        duration = float(stdout.decode().strip())
        logger.debug(f"Audio duration: {duration}s for {audio_path}")
        return duration

    async def trim_audio(
        self,
        audio_path: str,
        start: float,
        end: float,
        fade_in: float = 0.5,
        fade_out: float = 0.5,
        output_path: Optional[str] = None,
    ) -> str:
        """
        Trim audio segment with fade in/out.

        Uses two-step process for quality:
        1. Trim to exact segment
        2. Apply fade effects

        Args:
            audio_path: Source audio file path
            start: Start time in seconds
            end: End time in seconds
            fade_in: Fade in duration (default 0.5s)
            fade_out: Fade out duration (default 0.5s)
            output_path: Output file path. If None, generates temp path.

        Returns:
            Path to trimmed audio file

        Raises:
            RuntimeError: If FFmpeg fails
        """
        duration = end - start

        if output_path is None:
            output_path = str(TEMP_DIR / f"trim_{int(start)}_{int(end)}_{os.urandom(4).hex()}.mp3")

        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Step 1: Trim to exact segment
        temp_trimmed = str(TEMP_DIR / f"temp_trim_{os.urandom(4).hex()}.mp3")

        logger.debug(f"Trimming {audio_path} from {start}s to {end}s")

        process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y",
            "-i", audio_path,
            "-ss", str(start),
            "-t", str(duration),
            "-vn",  # No video
            "-b:a", "192k",  # Audio bitrate
            temp_trimmed,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"FFmpeg trim failed: {stderr.decode()}")

        # Step 2: Apply fade in/out
        fade_out_start = duration - fade_out

        logger.debug(f"Applying fade: in={fade_in}s, out={fade_out}s at {fade_out_start}s")

        process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y",
            "-i", temp_trimmed,
            "-af", f"afade=t=in:d={fade_in},afade=t=out:st={fade_out_start}:d={fade_out}",
            "-b:a", "192k",
            output_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()

        # Cleanup temp file
        try:
            os.remove(temp_trimmed)
        except OSError:
            pass

        if process.returncode != 0:
            raise RuntimeError(f"FFmpeg fade failed: {stderr.decode()}")

        logger.info(f"Trimmed audio: {output_path} ({duration}s with fade)")
        return output_path

    async def merge_video_audio(
        self,
        video_path: str,
        audio_path: str,
        output_path: Optional[str] = None,
    ) -> str:
        """
        Merge video and audio into single file.

        Uses -shortest to handle duration mismatch.

        Args:
            video_path: Source video file path
            audio_path: Source audio file path
            output_path: Output file path. If None, generates temp path.

        Returns:
            Path to merged video file

        Raises:
            RuntimeError: If FFmpeg fails
        """
        if output_path is None:
            output_path = str(TEMP_DIR / f"merged_{os.urandom(4).hex()}.mp4")

        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Merging video {video_path} with audio {audio_path}")

        process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",  # Copy video stream (no re-encoding)
            "-c:a", "aac",   # Encode audio to AAC
            "-shortest",     # Use shortest stream duration
            output_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"FFmpeg merge failed: {stderr.decode()}")

        logger.info(f"Merged video: {output_path}")
        return output_path

    async def cleanup_temp_files(self, max_age_hours: int = 24) -> int:
        """
        Clean up old temporary files.

        Args:
            max_age_hours: Delete files older than this (default 24h)

        Returns:
            Number of files deleted
        """
        if not TEMP_DIR.exists():
            return 0

        max_age_seconds = max_age_hours * 3600
        current_time = time.time()
        deleted = 0

        for file_path in TEMP_DIR.iterdir():
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    try:
                        file_path.unlink()
                        deleted += 1
                        logger.debug(f"Deleted old temp file: {file_path}")
                    except OSError as e:
                        logger.warning(f"Failed to delete {file_path}: {e}")

        if deleted > 0:
            logger.info(f"Cleaned up {deleted} temp files older than {max_age_hours}h")

        return deleted


# Singleton instance for convenience
media_processor = MediaProcessor()
