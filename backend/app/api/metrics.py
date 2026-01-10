"""
Video Metrics API - Track performance of published videos
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.video import Video, VideoMetrics, MetricsPeriod
from app.models.project import PublishResult, Project
from app.models.user import User, SocialAccount, WorkspaceMember
from app.api.workflow_helpers import verify_video_ownership, get_user_workspace_ids
from app.schemas.video import (
    VideoMetricsCreate,
    VideoMetricsUpdate,
    VideoMetricsResponse,
    VideoMetricsSummary
)
from app.services.metrics_fetcher import metrics_fetcher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["metrics"])


def calculate_engagement_rate(views: int, likes: int, comments: int, shares: int) -> Optional[int]:
    """Calculate engagement rate as percentage * 100 (e.g., 5.5% = 550)"""
    if views == 0:
        return None
    rate = ((likes + comments + shares) / views) * 100 * 100  # * 100 for percentage, * 100 for storage
    return int(rate)


@router.post("/video/{video_id}", response_model=VideoMetricsResponse)
async def create_metrics(
    video_id: int,
    metrics: VideoMetricsCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add metrics snapshot for a video at a specific time period.
    If metrics for this video/platform/period already exist, they will be updated.
    """
    # Verify video exists and user has access
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    verify_video_ownership(db, video, current_user)

    # Check if metrics already exist for this combination
    existing = db.query(VideoMetrics).filter(
        VideoMetrics.video_id == video_id,
        VideoMetrics.platform == metrics.platform,
        VideoMetrics.period == MetricsPeriod(metrics.period)
    ).first()

    engagement_rate = calculate_engagement_rate(
        metrics.views, metrics.likes, metrics.comments, metrics.shares
    )

    if existing:
        # Update existing
        existing.views = metrics.views
        existing.likes = metrics.likes
        existing.comments = metrics.comments
        existing.shares = metrics.shares
        existing.engagement_rate = engagement_rate
        existing.recorded_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Create new
        db_metrics = VideoMetrics(
            video_id=video_id,
            platform=metrics.platform,
            period=MetricsPeriod(metrics.period),
            views=metrics.views,
            likes=metrics.likes,
            comments=metrics.comments,
            shares=metrics.shares,
            engagement_rate=engagement_rate,
            is_manual=True
        )
        db.add(db_metrics)
        db.commit()
        db.refresh(db_metrics)
        return db_metrics


@router.get("/video/{video_id}", response_model=List[VideoMetricsResponse])
async def get_video_metrics(
    video_id: int,
    platform: Optional[str] = None,
    period: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all metrics for a video, optionally filtered by platform and/or period"""
    # Verify user has access to video
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    verify_video_ownership(db, video, current_user)

    query = db.query(VideoMetrics).filter(VideoMetrics.video_id == video_id)

    if platform:
        query = query.filter(VideoMetrics.platform == platform)
    if period:
        query = query.filter(VideoMetrics.period == MetricsPeriod(period))

    return query.order_by(VideoMetrics.recorded_at.desc()).all()


@router.get("/video/{video_id}/summary", response_model=VideoMetricsSummary)
async def get_video_metrics_summary(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get aggregated metrics summary for a video"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    verify_video_ownership(db, video, current_user)

    metrics = db.query(VideoMetrics).filter(VideoMetrics.video_id == video_id).all()

    # Organize by platform and period
    platforms = {}
    for m in metrics:
        if m.platform not in platforms:
            platforms[m.platform] = {}
        platforms[m.platform][m.period.value] = VideoMetricsResponse.model_validate(m)

    # Calculate totals from 7d metrics (or latest available)
    total_views = 0
    total_likes = 0
    total_comments = 0
    total_shares = 0
    engagement_rates = []

    for platform_data in platforms.values():
        # Prefer 7d, then 24h, then 6h, then 30m
        for period in ["7d", "24h", "6h", "30m"]:
            if period in platform_data:
                m = platform_data[period]
                total_views += m.views
                total_likes += m.likes
                total_comments += m.comments
                total_shares += m.shares
                if m.engagement_rate:
                    engagement_rates.append(m.engagement_rate)
                break

    avg_engagement = None
    if engagement_rates:
        avg_engagement = sum(engagement_rates) / len(engagement_rates) / 100  # Convert back to percentage

    return VideoMetricsSummary(
        video_id=video_id,
        author_rating=video.author_rating,
        platforms=platforms,
        total_views=total_views,
        total_likes=total_likes,
        total_comments=total_comments,
        total_shares=total_shares,
        avg_engagement_rate=avg_engagement
    )


@router.put("/video/{video_id}/{platform}/{period}", response_model=VideoMetricsResponse)
async def update_metrics(
    video_id: int,
    platform: str,
    period: str,
    metrics: VideoMetricsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update specific metrics entry"""
    # Verify user has access to video
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    verify_video_ownership(db, video, current_user)

    db_metrics = db.query(VideoMetrics).filter(
        VideoMetrics.video_id == video_id,
        VideoMetrics.platform == platform,
        VideoMetrics.period == MetricsPeriod(period)
    ).first()

    if not db_metrics:
        raise HTTPException(status_code=404, detail="Metrics not found")

    if metrics.views is not None:
        db_metrics.views = metrics.views
    if metrics.likes is not None:
        db_metrics.likes = metrics.likes
    if metrics.comments is not None:
        db_metrics.comments = metrics.comments
    if metrics.shares is not None:
        db_metrics.shares = metrics.shares

    # Recalculate engagement rate
    db_metrics.engagement_rate = calculate_engagement_rate(
        db_metrics.views, db_metrics.likes, db_metrics.comments, db_metrics.shares
    )
    db_metrics.recorded_at = datetime.utcnow()

    db.commit()
    db.refresh(db_metrics)
    return db_metrics


@router.delete("/video/{video_id}/{platform}/{period}")
async def delete_metrics(
    video_id: int,
    platform: str,
    period: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete specific metrics entry"""
    # Verify user has access to video
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    verify_video_ownership(db, video, current_user)

    db_metrics = db.query(VideoMetrics).filter(
        VideoMetrics.video_id == video_id,
        VideoMetrics.platform == platform,
        VideoMetrics.period == MetricsPeriod(period)
    ).first()

    if not db_metrics:
        raise HTTPException(status_code=404, detail="Metrics not found")

    db.delete(db_metrics)
    db.commit()
    return {"status": "deleted"}


@router.put("/video/{video_id}/rating")
async def set_author_rating(
    video_id: int,
    rating: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Set author's subjective rating for a video (1-5)"""
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    verify_video_ownership(db, video, current_user)

    video.author_rating = rating
    db.commit()

    return {"video_id": video_id, "author_rating": rating}


@router.get("/leaderboard", response_model=List[VideoMetricsSummary])
async def get_metrics_leaderboard(
    period: str = "7d",
    sort_by: str = "views",  # views, likes, comments, shares, engagement_rate
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get top performing videos by metrics (filtered by user's workspaces)"""
    # Get user's workspace IDs
    workspace_ids = get_user_workspace_ids(db, current_user.id)

    # Get videos with metrics for specified period, filtered by user's workspaces
    videos_with_metrics = db.query(Video).join(VideoMetrics).join(
        Project, Video.project_id == Project.id
    ).filter(
        VideoMetrics.period == MetricsPeriod(period),
        Project.workspace_id.in_(workspace_ids)
    ).distinct().all()

    summaries = []
    for video in videos_with_metrics:
        metrics = db.query(VideoMetrics).filter(
            VideoMetrics.video_id == video.id,
            VideoMetrics.period == MetricsPeriod(period)
        ).all()

        total_views = sum(m.views for m in metrics)
        total_likes = sum(m.likes for m in metrics)
        total_comments = sum(m.comments for m in metrics)
        total_shares = sum(m.shares for m in metrics)
        engagement_rates = [m.engagement_rate for m in metrics if m.engagement_rate]
        avg_engagement = sum(engagement_rates) / len(engagement_rates) / 100 if engagement_rates else None

        summaries.append(VideoMetricsSummary(
            video_id=video.id,
            author_rating=video.author_rating,
            platforms={},  # Skip detailed platforms for leaderboard
            total_views=total_views,
            total_likes=total_likes,
            total_comments=total_comments,
            total_shares=total_shares,
            avg_engagement_rate=avg_engagement
        ))

    # Sort by requested field
    sort_key = {
        "views": lambda x: x.total_views,
        "likes": lambda x: x.total_likes,
        "comments": lambda x: x.total_comments,
        "shares": lambda x: x.total_shares,
        "engagement_rate": lambda x: x.avg_engagement_rate or 0
    }.get(sort_by, lambda x: x.total_views)

    summaries.sort(key=sort_key, reverse=True)
    return summaries[:limit]


def determine_period(published_at: datetime) -> Optional[MetricsPeriod]:
    """Determine which period to use based on time since publication"""
    if not published_at:
        return None

    elapsed = datetime.utcnow() - published_at
    hours = elapsed.total_seconds() / 3600

    if hours < 0.5:
        return None  # Too early
    elif hours < 6:
        return MetricsPeriod.MINUTES_30
    elif hours < 24:
        return MetricsPeriod.HOURS_6
    elif hours < 168:  # 7 days
        return MetricsPeriod.HOURS_24
    else:
        return MetricsPeriod.DAYS_7


async def fetch_and_store_metrics(
    video_id: int,
    publish_result: PublishResult,
    social_account: SocialAccount,
    period: MetricsPeriod,
    db: Session
):
    """Background task to fetch metrics from platform and store them"""
    try:
        # Fetch metrics from platform API
        metrics_data = await metrics_fetcher.fetch(
            platform=publish_result.platform,
            post_id=publish_result.post_id,
            access_token=social_account.access_token,
            refresh_token=social_account.refresh_token
        )

        if not metrics_data:
            logger.warning(f"No metrics returned for video {video_id} on {publish_result.platform}")
            return

        views = metrics_data.get("views", 0)
        likes = metrics_data.get("likes", 0)
        comments = metrics_data.get("comments", 0)
        shares = metrics_data.get("shares", 0)

        engagement_rate = calculate_engagement_rate(views, likes, comments, shares)

        # Check if metrics for this period already exist
        existing = db.query(VideoMetrics).filter(
            VideoMetrics.video_id == video_id,
            VideoMetrics.platform == publish_result.platform,
            VideoMetrics.period == period
        ).first()

        if existing:
            existing.views = views
            existing.likes = likes
            existing.comments = comments
            existing.shares = shares
            existing.engagement_rate = engagement_rate
            existing.recorded_at = datetime.utcnow()
            existing.is_manual = False
        else:
            db_metrics = VideoMetrics(
                video_id=video_id,
                platform=publish_result.platform,
                period=period,
                views=views,
                likes=likes,
                comments=comments,
                shares=shares,
                engagement_rate=engagement_rate,
                is_manual=False
            )
            db.add(db_metrics)

        db.commit()
        logger.info(f"Fetched metrics for video {video_id} on {publish_result.platform}: {views} views, {likes} likes")

    except Exception as e:
        logger.error(f"Failed to fetch metrics for video {video_id}: {e}")


@router.post("/video/{video_id}/fetch")
async def fetch_video_metrics(
    video_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetch metrics from all platforms where video was published.
    Runs in background and stores results.
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    verify_video_ownership(db, video, current_user)

    # Get all publish results for this video
    publish_results = db.query(PublishResult).filter(
        PublishResult.video_id == video_id,
        PublishResult.status == "published",
        PublishResult.post_id.isnot(None)
    ).all()

    if not publish_results:
        raise HTTPException(status_code=400, detail="No published posts found for this video")

    tasks_scheduled = []

    for pr in publish_results:
        # Determine appropriate period based on publish time
        period = determine_period(pr.published_at)
        if not period:
            continue

        # Find social account for this platform
        social_account = db.query(SocialAccount).filter(
            SocialAccount.platform == pr.platform,
            SocialAccount.is_active == True
        ).first()

        if not social_account:
            logger.warning(f"No active social account for {pr.platform}")
            continue

        # Schedule background fetch
        background_tasks.add_task(
            fetch_and_store_metrics,
            video_id, pr, social_account, period, db
        )
        tasks_scheduled.append({
            "platform": pr.platform,
            "period": period.value,
            "post_id": pr.post_id
        })

    return {
        "status": "fetching",
        "video_id": video_id,
        "tasks": tasks_scheduled
    }


@router.post("/fetch-all")
async def fetch_all_published_metrics(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetch metrics for all published videos in user's workspaces.
    Use this for periodic batch updates.
    """
    # Get user's workspace IDs
    workspace_ids = get_user_workspace_ids(db, current_user.id)

    # Get all published videos in user's workspaces
    published_results = db.query(PublishResult).join(
        Video, PublishResult.video_id == Video.id
    ).join(
        Project, Video.project_id == Project.id
    ).filter(
        PublishResult.status == "published",
        PublishResult.post_id.isnot(None),
        Project.workspace_id.in_(workspace_ids)
    ).all()

    total_scheduled = 0

    for pr in published_results:
        period = determine_period(pr.published_at)
        if not period:
            continue

        social_account = db.query(SocialAccount).filter(
            SocialAccount.platform == pr.platform,
            SocialAccount.is_active == True
        ).first()

        if not social_account:
            continue

        background_tasks.add_task(
            fetch_and_store_metrics,
            pr.video_id, pr, social_account, period, db
        )
        total_scheduled += 1

    return {
        "status": "fetching",
        "total_tasks_scheduled": total_scheduled
    }
