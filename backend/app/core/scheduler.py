"""
APScheduler configuration for periodic metrics fetching.

Jobs are scheduled per-video at exact intervals after publication:
- 30 minutes
- 6 hours
- 24 hours
- 7 days

Uses SQLite job store for persistence across restarts.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

from app.core.config import settings

logger = logging.getLogger(__name__)

# Metrics fetch intervals after publication
METRICS_INTERVALS = {
    "30m": timedelta(minutes=30),
    "6h": timedelta(hours=6),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
}

# Scheduler instance (singleton)
scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> AsyncIOScheduler:
    """Get or create the scheduler instance"""
    global scheduler

    if scheduler is None:
        # Use SQLite for job persistence
        jobstores = {
            "default": SQLAlchemyJobStore(url=settings.DATABASE_URL)
        }

        executors = {
            "default": AsyncIOExecutor()
        }

        job_defaults = {
            "coalesce": True,  # Combine missed runs into one
            "max_instances": 3,  # Max concurrent instances of same job
            "misfire_grace_time": 3600,  # 1 hour grace for missed jobs
        }

        scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone="UTC"
        )

    return scheduler


def start_scheduler():
    """Start the scheduler"""
    sched = get_scheduler()
    if not sched.running:
        sched.start()
        logger.info("Scheduler started")

        # Add scheduled publisher job (runs every 5 minutes)
        _add_scheduled_publisher_job(sched)


def _add_scheduled_publisher_job(sched: AsyncIOScheduler):
    """Add the scheduled publisher job if not already present."""
    from app.services.scheduled_publisher import scheduled_publish_job

    job_id = "scheduled_publisher"

    # Check if job already exists (from persistent store)
    existing = sched.get_job(job_id)
    if existing:
        logger.info(f"Scheduled publisher job already exists, next run: {existing.next_run_time}")
        return

    # Add new job - runs every 5 minutes
    sched.add_job(
        scheduled_publish_job,
        trigger="interval",
        minutes=5,
        id=job_id,
        replace_existing=True,
        misfire_grace_time=300,  # 5 minutes grace
    )
    logger.info("Added scheduled publisher job (every 5 minutes)")


def shutdown_scheduler():
    """Gracefully shutdown the scheduler"""
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("Scheduler shutdown")


async def fetch_video_metrics_job(
    video_id: int,
    platform: str,
    post_id: str,
    period: str
):
    """
    Job function to fetch metrics for a specific video.
    Called by scheduler at scheduled times.
    """
    from app.db.base import SessionLocal
    from app.models.video import Video, VideoMetrics, MetricsPeriod
    from app.models.user import SocialAccount
    from app.services.metrics_fetcher import metrics_fetcher
    from app.api.metrics import calculate_engagement_rate

    logger.info(f"Fetching {period} metrics for video {video_id} on {platform}")

    db = SessionLocal()
    try:
        # Get social account with valid token
        social_account = db.query(SocialAccount).filter(
            SocialAccount.platform == platform,
            SocialAccount.is_active == True
        ).first()

        if not social_account:
            logger.warning(f"No active social account for {platform}")
            return

        # Fetch metrics from platform
        metrics_data = await metrics_fetcher.fetch(
            platform=platform,
            post_id=post_id,
            access_token=social_account.access_token,
            refresh_token=social_account.refresh_token
        )

        if not metrics_data:
            logger.warning(f"No metrics returned for video {video_id}")
            return

        views = metrics_data.get("views", 0)
        likes = metrics_data.get("likes", 0)
        comments = metrics_data.get("comments", 0)
        shares = metrics_data.get("shares", 0)
        saves = metrics_data.get("saves", 0)
        reach = metrics_data.get("reach", 0)

        engagement_rate = calculate_engagement_rate(views, likes, comments, shares, saves)

        # Store metrics
        period_enum = MetricsPeriod(period)

        existing = db.query(VideoMetrics).filter(
            VideoMetrics.video_id == video_id,
            VideoMetrics.platform == platform,
            VideoMetrics.period == period_enum
        ).first()

        if existing:
            existing.views = views
            existing.likes = likes
            existing.comments = comments
            existing.shares = shares
            existing.saves = saves
            existing.reach = reach
            existing.engagement_rate = engagement_rate
            existing.recorded_at = datetime.utcnow()
            existing.is_manual = False
        else:
            db_metrics = VideoMetrics(
                video_id=video_id,
                platform=platform,
                period=period_enum,
                views=views,
                likes=likes,
                comments=comments,
                shares=shares,
                saves=saves,
                reach=reach,
                engagement_rate=engagement_rate,
                is_manual=False
            )
            db.add(db_metrics)

        db.commit()
        logger.info(f"Stored {period} metrics for video {video_id}: {views} views, {likes} likes")

    except Exception as e:
        logger.error(f"Failed to fetch metrics for video {video_id}: {e}")
        db.rollback()
    finally:
        db.close()


def schedule_metrics_for_video(
    video_id: int,
    platform: str,
    post_id: str,
    published_at: datetime
):
    """
    Schedule all 4 metrics fetch jobs for a newly published video.
    Called from publishing API after successful publication.
    """
    sched = get_scheduler()

    for period, delta in METRICS_INTERVALS.items():
        run_time = published_at + delta
        job_id = f"metrics_{video_id}_{platform}_{period}"

        # Remove existing job if any (in case of re-publish)
        try:
            sched.remove_job(job_id)
        except:
            pass

        # Schedule new job
        sched.add_job(
            fetch_video_metrics_job,
            trigger="date",
            run_date=run_time,
            id=job_id,
            args=[video_id, platform, post_id, period],
            replace_existing=True
        )

        logger.info(f"Scheduled {period} metrics fetch for video {video_id} at {run_time}")


def get_scheduled_jobs_for_video(video_id: int) -> list:
    """Get all scheduled jobs for a specific video"""
    sched = get_scheduler()
    jobs = []

    for job in sched.get_jobs():
        if job.id.startswith(f"metrics_{video_id}_"):
            jobs.append({
                "id": job.id,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "args": job.args
            })

    return jobs


async def fetch_generation_metrics_job(
    approved_generation_id: int,
    platform: str,
    post_id: str,
    period: str
):
    """
    Job function to fetch metrics for a published template generation.
    Called by scheduler at scheduled times (30m, 6h, 24h, 7d after publish).
    """
    from app.db.base import SessionLocal
    from app.models.video import VideoMetrics, MetricsPeriod
    from app.models.user import SocialAccount
    from app.services.metrics_fetcher import metrics_fetcher
    from app.api.metrics import calculate_engagement_rate

    logger.info(f"Fetching {period} metrics for generation {approved_generation_id} on {platform}")

    db = SessionLocal()
    try:
        social_account = db.query(SocialAccount).filter(
            SocialAccount.platform == platform,
            SocialAccount.is_active == True
        ).first()

        if not social_account:
            logger.warning(f"No active social account for {platform}")
            return

        metrics_data = await metrics_fetcher.fetch(
            platform=platform,
            post_id=post_id,
            access_token=social_account.access_token,
            refresh_token=social_account.refresh_token
        )

        if not metrics_data:
            logger.warning(f"No metrics returned for generation {approved_generation_id}")
            return

        views = metrics_data.get("views", 0)
        likes = metrics_data.get("likes", 0)
        comments = metrics_data.get("comments", 0)
        shares = metrics_data.get("shares", 0)
        saves = metrics_data.get("saves", 0)
        reach = metrics_data.get("reach", 0)

        engagement_rate = calculate_engagement_rate(views, likes, comments, shares, saves)

        period_enum = MetricsPeriod(period)

        existing = db.query(VideoMetrics).filter(
            VideoMetrics.approved_generation_id == approved_generation_id,
            VideoMetrics.platform == platform,
            VideoMetrics.period == period_enum
        ).first()

        if existing:
            existing.views = views
            existing.likes = likes
            existing.comments = comments
            existing.shares = shares
            existing.saves = saves
            existing.reach = reach
            existing.engagement_rate = engagement_rate
            existing.recorded_at = datetime.utcnow()
            existing.is_manual = False
        else:
            db_metrics = VideoMetrics(
                approved_generation_id=approved_generation_id,
                platform=platform,
                period=period_enum,
                views=views,
                likes=likes,
                comments=comments,
                shares=shares,
                saves=saves,
                reach=reach,
                engagement_rate=engagement_rate,
                is_manual=False
            )
            db.add(db_metrics)

        db.commit()
        logger.info(f"Stored {period} metrics for generation {approved_generation_id}: {views} views, {likes} likes")

    except Exception as e:
        logger.error(f"Failed to fetch metrics for generation {approved_generation_id}: {e}")
        db.rollback()
    finally:
        db.close()


def schedule_metrics_for_generation(
    approved_generation_id: int,
    platform: str,
    post_id: str,
    published_at: datetime
):
    """
    Schedule all 4 metrics fetch jobs for a published template generation.
    Called from scheduled_publisher after successful publication.
    """
    sched = get_scheduler()

    for period, delta in METRICS_INTERVALS.items():
        run_time = published_at + delta
        job_id = f"metrics_gen_{approved_generation_id}_{platform}_{period}"

        try:
            sched.remove_job(job_id)
        except:
            pass

        sched.add_job(
            fetch_generation_metrics_job,
            trigger="date",
            run_date=run_time,
            id=job_id,
            args=[approved_generation_id, platform, post_id, period],
            replace_existing=True
        )

        logger.info(f"Scheduled {period} metrics fetch for generation {approved_generation_id} at {run_time}")


def cancel_metrics_jobs_for_video(video_id: int):
    """Cancel all scheduled metrics jobs for a video"""
    sched = get_scheduler()

    for job in sched.get_jobs():
        if job.id.startswith(f"metrics_{video_id}_"):
            sched.remove_job(job.id)
            logger.info(f"Cancelled job {job.id}")
