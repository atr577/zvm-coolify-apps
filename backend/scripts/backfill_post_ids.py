"""
One-time backfill: recover YouTube post_ids for published generations,
fetch current metrics, and store them.

Run on the server inside the backend container:
    docker exec <backend-container> python scripts/backfill_post_ids.py

Or locally with SSH tunnel (ssh -L 5432:localhost:5432 root@server):
    DATABASE_URL="postgresql://reggy:pass@localhost:5432/reggy" \
    YOUTUBE_CLIENT_ID="..." YOUTUBE_CLIENT_SECRET="..." \
    .venv/bin/python scripts/backfill_post_ids.py
"""

import asyncio
import os
import sys
import logging
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DRY_RUN = "--dry-run" in sys.argv


def get_db_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        # Try to use app settings
        from app.core.config import settings
        db_url = settings.DATABASE_URL

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    return Session()


def list_youtube_uploads(access_token: str, refresh_token: str) -> list[dict]:
    """List recent YouTube uploads via Data API v3."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    client_id = os.environ.get("YOUTUBE_CLIENT_ID", "")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET", "")

    if not client_id:
        try:
            from app.core.config import settings
            client_id = settings.YOUTUBE_CLIENT_ID
            client_secret = settings.YOUTUBE_CLIENT_SECRET
        except Exception:
            pass

    credentials = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
    )

    youtube = build("youtube", "v3", credentials=credentials)

    # Get uploads playlist
    channels = youtube.channels().list(part="contentDetails", mine=True).execute()
    if not channels.get("items"):
        logger.error("No YouTube channel found")
        return []

    uploads_playlist = channels["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    # List recent uploads
    response = youtube.playlistItems().list(
        part="snippet",
        playlistId=uploads_playlist,
        maxResults=50,
    ).execute()

    items = []
    for item in response.get("items", []):
        snippet = item["snippet"]
        video_id = snippet["resourceId"]["videoId"]
        items.append({
            "video_id": video_id,
            "title": snippet["title"],
            "published_at": snippet["publishedAt"],
            "post_url": f"https://youtube.com/shorts/{video_id}",
        })

    return items


async def fetch_youtube_metrics(video_id: str, access_token: str, refresh_token: str) -> dict:
    """Fetch current metrics for a YouTube video."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    client_id = os.environ.get("YOUTUBE_CLIENT_ID", "")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET", "")

    if not client_id:
        try:
            from app.core.config import settings
            client_id = settings.YOUTUBE_CLIENT_ID
            client_secret = settings.YOUTUBE_CLIENT_SECRET
        except Exception:
            pass

    credentials = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
    )

    youtube = build("youtube", "v3", credentials=credentials)

    response = youtube.videos().list(
        part="statistics",
        id=video_id,
    ).execute()

    if not response.get("items"):
        return {}

    stats = response["items"][0]["statistics"]
    return {
        "views": int(stats.get("viewCount", 0)),
        "likes": int(stats.get("likeCount", 0)),
        "comments": int(stats.get("commentCount", 0)),
        "shares": 0,  # YouTube Data API doesn't expose shares
        "saves": 0,
        "reach": 0,
    }


def determine_period(published_at: datetime) -> str:
    """Determine the closest metrics period based on time since publish."""
    elapsed = datetime.utcnow() - published_at
    hours = elapsed.total_seconds() / 3600

    if hours < 3:
        return "30m"
    elif hours < 15:
        return "6h"
    elif hours < 72:
        return "24h"
    else:
        return "7d"


async def main():
    from app.models.approved_generation import ApprovedGeneration
    from app.models.video import VideoMetrics, MetricsPeriod
    from app.models.user import SocialAccount

    db = get_db_session()

    try:
        # 1. Find published generations without post_ids
        generations = db.query(ApprovedGeneration).filter(
            ApprovedGeneration.status.in_(["published", "partially_published"]),
            ApprovedGeneration.published_at.isnot(None),
            (ApprovedGeneration.post_ids == None),
        ).order_by(ApprovedGeneration.published_at).all()

        if not generations:
            logger.info("No generations need backfill")
            return

        logger.info(f"Found {len(generations)} generations to backfill")
        for g in generations:
            title = (g.publishing_metadata or {}).get("youtube", {}).get("title", "???")
            logger.info(f"  [{g.id}] published_at={g.published_at} title={title[:60]}")

        # 2. Get YouTube social account
        yt_account = db.query(SocialAccount).filter(
            SocialAccount.platform == "youtube",
            SocialAccount.is_active == True,
        ).first()

        if not yt_account:
            logger.error("No active YouTube social account")
            return

        logger.info(f"YouTube account: {yt_account.username}")

        # 3. List recent YouTube uploads
        logger.info("Fetching YouTube uploads...")
        uploads = list_youtube_uploads(yt_account.access_token, yt_account.refresh_token)
        logger.info(f"Found {len(uploads)} uploads")
        for u in uploads:
            logger.info(f"  [{u['video_id']}] {u['title'][:60]}")

        # 4. Match by title
        matches = []
        for gen in generations:
            yt_title = (gen.publishing_metadata or {}).get("youtube", {}).get("title", "")
            if not yt_title:
                logger.warning(f"  Gen {gen.id}: no YouTube title, skip")
                continue

            matched = None
            for upload in uploads:
                # Try exact match, then truncated (YouTube title limit = 100)
                if upload["title"].strip() == yt_title.strip() or \
                   upload["title"].strip() == yt_title[:100].strip():
                    matched = upload
                    break

            if matched:
                matches.append((gen, matched))
                logger.info(f"  MATCH: gen {gen.id} -> {matched['video_id']}")
            else:
                logger.warning(f"  NO MATCH: gen {gen.id} title='{yt_title[:50]}...'")

        if not matches:
            logger.warning("No matches found")
            return

        if DRY_RUN:
            logger.info("DRY RUN — not writing to DB")
            return

        # 5. Update post_ids
        for gen, upload in matches:
            gen.post_ids = {"youtube": upload["video_id"]}
            gen.post_urls = {"youtube": upload["post_url"]}

        db.commit()
        logger.info(f"Updated post_ids for {len(matches)} generations")

        # 6. Fetch and store current metrics
        logger.info("Fetching current metrics from YouTube...")
        for gen, upload in matches:
            metrics = await fetch_youtube_metrics(
                upload["video_id"],
                yt_account.access_token,
                yt_account.refresh_token,
            )

            if not metrics:
                logger.warning(f"  Gen {gen.id}: no metrics returned")
                continue

            period = determine_period(gen.published_at)
            period_enum = MetricsPeriod(period)

            views = metrics["views"]
            likes = metrics["likes"]
            comments = metrics["comments"]
            shares = metrics["shares"]
            saves = metrics["saves"]

            engagement_rate = None
            if views > 0:
                engagement_rate = round(((likes + comments + shares + saves) / views) * 100, 2)

            # Check if already exists
            existing = db.query(VideoMetrics).filter(
                VideoMetrics.approved_generation_id == gen.id,
                VideoMetrics.platform == "youtube",
                VideoMetrics.period == period_enum,
            ).first()

            if existing:
                existing.views = views
                existing.likes = likes
                existing.comments = comments
                existing.shares = shares
                existing.engagement_rate = engagement_rate
                existing.recorded_at = datetime.utcnow()
                logger.info(f"  Gen {gen.id}: updated {period} metrics: {views} views, {likes} likes")
            else:
                db_metrics = VideoMetrics(
                    approved_generation_id=gen.id,
                    platform="youtube",
                    period=period_enum,
                    views=views,
                    likes=likes,
                    comments=comments,
                    shares=shares,
                    saves=saves,
                    reach=0,
                    engagement_rate=engagement_rate,
                    is_manual=False,
                )
                db.add(db_metrics)
                logger.info(f"  Gen {gen.id}: stored {period} metrics: {views} views, {likes} likes")

        db.commit()
        logger.info("Done! Backfill complete.")
        logger.info("NOTE: Only current metrics snapshot stored. Future snapshots (24h, 7d)")
        logger.info("will be collected automatically by the scheduler on next publish.")

    except Exception as e:
        logger.error(f"Backfill failed: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
