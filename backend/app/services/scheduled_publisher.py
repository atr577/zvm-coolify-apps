"""
Scheduled Publisher Service for Template projects.

Runs periodically to check for videos that should be published
based on project publishing config (days, time, timezone).
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import pytz

from sqlalchemy.orm import Session, joinedload

from app.db.base import SessionLocal
from app.models.project import Project
from app.models.publishing_config import PublishingConfig
from app.models.approved_generation import ApprovedGeneration
from app.models.template_generation import TemplateGeneration
from app.models.user import SocialAccount
from app.models.youtube_account import YouTubeAccount, YouTubeAccountStatus
from app.core.config import settings
from app.services.social_service import social_publisher

logger = logging.getLogger(__name__)

# Error classification
RETRIABLE_ERRORS = [
    "timeout",
    "connection",
    "rate limit",
    "429",
    "500",
    "502",
    "503",
    "504",
]

NON_RETRIABLE_ERRORS = [
    "token expired",
    "token revoked",
    "unauthorized",
    "forbidden",
    "invalid",
    "suspended",
    "content rejected",
]

MAX_RETRY_COUNT = 3


def is_retriable_error(error_message: str) -> bool:
    """Check if error is retriable based on message."""
    error_lower = error_message.lower()
    return any(err in error_lower for err in RETRIABLE_ERRORS)


def get_user_friendly_error(error_message: str) -> str:
    """Convert technical error to user-friendly message."""
    error_lower = error_message.lower()

    if "token expired" in error_lower:
        return "Token expired. Please reconnect your account."
    if "token revoked" in error_lower or "unauthorized" in error_lower:
        return "Account disconnected. Please reconnect."
    if "suspended" in error_lower:
        return "Account suspended by platform."
    if "content rejected" in error_lower:
        return "Content rejected by platform moderation."
    if "rate limit" in error_lower or "429" in error_lower:
        return "Platform rate limit reached. Will retry later."

    return error_message


async def publish_to_platform(
    platform: str,
    video_url: str,
    metadata: Dict[str, str],
    social_account: SocialAccount
) -> Dict[str, Any]:
    """Publish video to a single platform."""
    title = metadata.get("title", "")
    description = metadata.get("description", "")
    hashtags = metadata.get("hashtags", "")

    # Combine description with hashtags
    if hashtags:
        full_description = f"{description}\n\n{hashtags}"
    else:
        full_description = description

    kwargs = {
        "platform": platform,
        "video_url": video_url,
        "title": title,
        "description": full_description,
        "access_token": social_account.access_token,
    }

    # Platform-specific params
    if platform == "instagram":
        kwargs["business_account_id"] = (
            social_account.platform_data.get("business_account_id")
            if social_account.platform_data else None
        )
    elif platform == "youtube":
        kwargs["refresh_token"] = social_account.refresh_token
        kwargs["tags"] = []
        kwargs["privacy_status"] = "public"

    result = await social_publisher.publish(**kwargs)
    return result


async def scheduled_publish_job():
    """
    Main job function for scheduled publishing.

    Runs every 5 minutes, checks all projects with enabled publishing config,
    and publishes videos when the current time matches a schedule slot.
    """
    logger.info("Running scheduled publish job")

    db = SessionLocal()
    try:
        # Get all projects with enabled publishing config
        configs = db.query(PublishingConfig).filter(
            PublishingConfig.enabled == True
        ).options(
            joinedload(PublishingConfig.project)
        ).all()

        logger.info(f"Found {len(configs)} projects with enabled publishing")

        for config in configs:
            project = config.project
            if not project or project.project_type != "template":
                continue

            # Check if we should publish now (returns slot UTC datetime or None)
            slot_utc = check_should_publish_now(config, project.timezone)
            if not slot_utc:
                continue

            # Guard: skip if this slot already handled
            already_handled = db.query(ApprovedGeneration).filter(
                ApprovedGeneration.project_id == project.id,
                ApprovedGeneration.scheduled_for == slot_utc,
            ).first()

            if already_handled:
                logger.info(f"Project {project.id}: Slot {slot_utc} already handled, skipping")
                continue

            # Get next item to publish
            item = db.query(ApprovedGeneration).options(
                joinedload(ApprovedGeneration.template_generation)
            ).filter(
                ApprovedGeneration.project_id == project.id,
                ApprovedGeneration.status == "approved"
            ).order_by(ApprovedGeneration.position.asc()).first()

            if not item:
                logger.info(f"Project {project.id}: No approved items to publish")
                continue

            # Stamp slot before publishing (prevents duplicates across job runs)
            item.scheduled_for = slot_utc
            db.commit()

            # Publish
            await publish_approved_generation(db, project, item)

    except Exception as e:
        logger.error(f"Scheduled publish job failed: {e}")
        db.rollback()
    finally:
        db.close()


def check_should_publish_now(config: PublishingConfig, timezone: str) -> Optional[datetime]:
    """
    Check if current time matches a publishing slot.

    Returns the matched slot as UTC datetime if:
    - Current day is in config.days
    - Current time is within 5 minutes of any preferred_time

    Returns None if no slot matches.
    """
    if not config.days:
        return None

    DAY_MAP = {
        0: 'mon', 1: 'tue', 2: 'wed', 3: 'thu', 4: 'fri', 5: 'sat', 6: 'sun'
    }

    try:
        tz = pytz.timezone(timezone)
    except pytz.UnknownTimeZoneError:
        tz = pytz.UTC

    now = datetime.now(tz)
    current_day = DAY_MAP.get(now.weekday())

    # Check if today is a publishing day
    if current_day not in [d.lower() for d in config.days]:
        return None

    # Check each preferred time
    preferred_times = config.preferred_times or ["18:00"]
    for time_str in preferred_times:
        try:
            hour, minute = map(int, time_str.split(':'))
        except (ValueError, AttributeError):
            continue

        # Check if within 5 minutes of this preferred time
        preferred_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        time_diff = abs((now - preferred_time).total_seconds())

        # Within 5 minute window (job runs every 5 mins, so we catch it once)
        if time_diff < 300:  # 5 minutes
            # Return slot as UTC datetime for storage
            slot_utc = preferred_time.astimezone(pytz.UTC).replace(tzinfo=None)
            return slot_utc

    return None


async def publish_approved_generation(
    db: Session,
    project: Project,
    item: ApprovedGeneration
):
    """Publish a single approved generation to all configured platforms."""
    logger.info(f"Publishing item {item.id} for project {project.id}")

    generation = item.template_generation
    if not generation or not generation.video_url:
        logger.error(f"Item {item.id}: No video URL available")
        item.status = "failed"
        item.last_error = "No video URL available"
        db.commit()
        return

    # Video must have merged audio
    if not generation.video_with_audio_path:
        logger.error(f"Item {item.id}: Video has no merged audio")
        item.status = "failed"
        item.last_error = "Video has no merged audio. Re-generate with audio enabled."
        db.commit()
        return

    if not settings.APP_BASE_URL:
        logger.error(f"Item {item.id}: APP_BASE_URL not configured")
        item.status = "failed"
        item.last_error = "APP_BASE_URL not configured. Set it in environment variables."
        db.commit()
        return

    video_url = f"{settings.APP_BASE_URL}/api/files/{generation.video_with_audio_path}"
    logger.info(f"Item {item.id}: Publishing video with audio: {video_url}")

    # Mark as publishing (prevents duplicate processing)
    item.status = "publishing"
    db.commit()

    # Get platforms to publish to
    platforms = project.platforms or []
    metadata = item.publishing_metadata or {}

    if not platforms:
        logger.warning(f"Project {project.id}: No platforms configured")
        item.status = "failed"
        item.last_error = "No platforms configured"
        db.commit()
        return

    # Track per-platform results
    platform_statuses: Dict[str, str] = {}
    errors: List[str] = []
    any_success = False

    for platform in platforms:
        platform_metadata = metadata.get(platform, {})
        if not platform_metadata:
            logger.warning(f"No metadata for platform {platform}, skipping")
            platform_statuses[platform] = "skipped"
            continue

        # Get social account for this platform
        social_account = get_project_social_account(db, project, platform)
        if not social_account:
            logger.warning(f"No social account for {platform}")
            platform_statuses[platform] = "no_account"
            errors.append(f"{platform}: No connected account")
            continue

        try:
            result = await publish_to_platform(
                platform=platform,
                video_url=video_url,
                metadata=platform_metadata,
                social_account=social_account
            )

            platform_statuses[platform] = "published"
            any_success = True
            logger.info(f"Published to {platform}: {result}")

            # Save post_id and post_url
            post_id = result.get("post_id")
            post_url = result.get("post_url")
            if not item.post_ids:
                item.post_ids = {}
            if not item.post_urls:
                item.post_urls = {}
            if post_id:
                item.post_ids = {**item.post_ids, platform: post_id}
            if post_url:
                item.post_urls = {**item.post_urls, platform: post_url}

            # Schedule metrics collection (isolated — must not affect publish status)
            if post_id:
                try:
                    from app.core.scheduler import schedule_metrics_for_generation
                    schedule_metrics_for_generation(
                        approved_generation_id=item.id,
                        platform=platform,
                        post_id=post_id,
                        published_at=datetime.utcnow()
                    )
                except Exception as sched_err:
                    logger.error(f"Failed to schedule metrics for {platform}: {sched_err}")

        except Exception as e:
            error_msg = str(e)
            friendly_error = get_user_friendly_error(error_msg)
            platform_statuses[platform] = "failed"
            errors.append(f"{platform}: {friendly_error}")
            logger.error(f"Failed to publish to {platform}: {error_msg}")

            # Check if retriable
            if is_retriable_error(error_msg):
                platform_statuses[platform] = "failed_retriable"

    # Update item status
    item.platform_statuses = platform_statuses

    if all(s == "published" for s in platform_statuses.values()):
        item.status = "published"
        item.published_at = datetime.utcnow()
    elif any_success:
        item.status = "partially_published"
        item.published_at = datetime.utcnow()
    else:
        # All failed
        item.retry_count += 1
        if item.retry_count >= MAX_RETRY_COUNT:
            item.status = "failed"
        else:
            # Keep as "approved" for retry
            item.status = "approved"
        item.last_error = "; ".join(errors)

    db.commit()
    logger.info(f"Item {item.id} final status: {item.status}")


class _YouTubeAccountAdapter:
    """Adapter to make YouTubeAccount quack like SocialAccount for publish_to_platform."""
    def __init__(self, yt: YouTubeAccount):
        self.id = yt.id
        self.access_token = yt.access_token
        self.refresh_token = yt.refresh_token
        self.platform = "youtube"
        self.is_active = True
        self.is_token_expired = False
        self.platform_data = None
        self._source = "workspace"
        self._channel_title = yt.channel_title

    def __repr__(self):
        return f"<_YouTubeAccountAdapter(yt_id={self.id}, channel='{self._channel_title}')>"


def get_project_social_account(
    db: Session,
    project: Project,
    platform: str
) -> Optional[SocialAccount]:
    """Get active social account for platform from project's linked accounts.

    For YouTube: if no personal SocialAccount bound, check project.youtube_account_id
    and return a SocialAccount-compatible adapter.
    """
    for account in project.social_accounts:
        if account.platform == platform and account.is_active and not account.is_token_expired:
            return account

    # Fallback: workspace YouTubeAccount for YouTube platform
    if platform == "youtube" and project.youtube_account_id:
        yt_account = db.query(YouTubeAccount).filter(
            YouTubeAccount.id == project.youtube_account_id,
            YouTubeAccount.token_status == YouTubeAccountStatus.ACTIVE.value,
        ).first()
        if yt_account:
            return _YouTubeAccountAdapter(yt_account)

    return None
