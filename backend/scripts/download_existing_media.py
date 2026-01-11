#!/usr/bin/env python3
"""
One-time script to download existing media from CDN to local storage.

Usage:
    cd backend
    venv/bin/python scripts/download_existing_media.py
"""
import asyncio
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db.base import SessionLocal
from app.models.video import Video
from app.services import media_downloader


async def download_media_for_video(video: Video, db: Session) -> dict:
    """Download all media for a single video."""
    results = {"id": video.id, "title": video.title, "downloaded": [], "failed": [], "skipped": []}

    # Image
    if video.image_url and not video.local_image_path:
        try:
            local_path = await media_downloader.download_image(video.image_url, video.id)
            if local_path:
                video.local_image_path = local_path
                results["downloaded"].append(f"image: {local_path}")
            else:
                results["failed"].append("image")
        except Exception as e:
            results["failed"].append(f"image: {e}")
    elif video.local_image_path:
        results["skipped"].append("image (already local)")

    # Video
    if video.video_url and not video.local_video_path:
        try:
            local_path = await media_downloader.download_video(video.video_url, video.id, "video")
            if local_path:
                video.local_video_path = local_path
                results["downloaded"].append(f"video: {local_path}")
            else:
                results["failed"].append("video")
        except Exception as e:
            results["failed"].append(f"video: {e}")
    elif video.local_video_path:
        results["skipped"].append("video (already local)")

    # Audio (video with audio)
    if video.video_with_audio_url and not video.local_audio_path:
        try:
            local_path = await media_downloader.download_video(video.video_with_audio_url, video.id, "audio")
            if local_path:
                video.local_audio_path = local_path
                results["downloaded"].append(f"audio: {local_path}")
            else:
                results["failed"].append("audio")
        except Exception as e:
            results["failed"].append(f"audio: {e}")
    elif video.local_audio_path:
        results["skipped"].append("audio (already local)")

    return results


async def main():
    print("=" * 60)
    print("Downloading existing media to local storage")
    print("=" * 60)

    db = SessionLocal()
    try:
        # Get all videos that have CDN URLs but missing local paths
        videos = db.query(Video).filter(
            # Has at least one CDN URL
            (Video.image_url.isnot(None)) |
            (Video.video_url.isnot(None)) |
            (Video.video_with_audio_url.isnot(None))
        ).all()

        print(f"\nFound {len(videos)} videos to process\n")

        total_downloaded = 0
        total_failed = 0
        total_skipped = 0

        for i, video in enumerate(videos, 1):
            print(f"[{i}/{len(videos)}] Video #{video.id}: {video.title[:40]}...")

            results = await download_media_for_video(video, db)

            if results["downloaded"]:
                for item in results["downloaded"]:
                    print(f"  ✓ Downloaded {item}")
                total_downloaded += len(results["downloaded"])

            if results["skipped"]:
                for item in results["skipped"]:
                    print(f"  - Skipped {item}")
                total_skipped += len(results["skipped"])

            if results["failed"]:
                for item in results["failed"]:
                    print(f"  ✗ Failed {item}")
                total_failed += len(results["failed"])

            # Commit after each video
            db.commit()

        print("\n" + "=" * 60)
        print(f"DONE!")
        print(f"  Downloaded: {total_downloaded}")
        print(f"  Skipped:    {total_skipped}")
        print(f"  Failed:     {total_failed}")
        print("=" * 60)

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
