"""
Video Metrics API - Track performance of published videos
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.db.base import get_db
from app.models.video import Video, VideoMetrics, MetricsPeriod
from app.schemas.video import (
    VideoMetricsCreate,
    VideoMetricsUpdate,
    VideoMetricsResponse,
    VideoMetricsSummary
)

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
    db: Session = Depends(get_db)
):
    """
    Add metrics snapshot for a video at a specific time period.
    If metrics for this video/platform/period already exist, they will be updated.
    """
    # Verify video exists
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

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
    db: Session = Depends(get_db)
):
    """Get all metrics for a video, optionally filtered by platform and/or period"""
    query = db.query(VideoMetrics).filter(VideoMetrics.video_id == video_id)

    if platform:
        query = query.filter(VideoMetrics.platform == platform)
    if period:
        query = query.filter(VideoMetrics.period == MetricsPeriod(period))

    return query.order_by(VideoMetrics.recorded_at.desc()).all()


@router.get("/video/{video_id}/summary", response_model=VideoMetricsSummary)
async def get_video_metrics_summary(
    video_id: int,
    db: Session = Depends(get_db)
):
    """Get aggregated metrics summary for a video"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

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
    db: Session = Depends(get_db)
):
    """Update specific metrics entry"""
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
    db: Session = Depends(get_db)
):
    """Delete specific metrics entry"""
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
    db: Session = Depends(get_db)
):
    """Set author's subjective rating for a video (1-5)"""
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    video.author_rating = rating
    db.commit()

    return {"video_id": video_id, "author_rating": rating}


@router.get("/leaderboard", response_model=List[VideoMetricsSummary])
async def get_metrics_leaderboard(
    period: str = "7d",
    sort_by: str = "views",  # views, likes, comments, shares, engagement_rate
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get top performing videos by metrics"""
    # Get all videos with metrics for specified period
    videos_with_metrics = db.query(Video).join(VideoMetrics).filter(
        VideoMetrics.period == MetricsPeriod(period)
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
