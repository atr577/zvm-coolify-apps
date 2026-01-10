"""
Migration script to create StepAttempt and Variant records
for existing workflow data.

Run: python -m scripts.migrate_to_variants
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datetime import datetime
from app.db.base import SessionLocal
from app.models import Video, WorkflowStep, StepType
from app.models.step_attempt import StepAttempt, Variant, AttemptStatus


STEP_CONTENT_FIELDS = {
    StepType.STORY: "story_data",
    StepType.DESCRIPTION: "description_data",
    StepType.PROMPT: "prompt_data",
    StepType.IMAGE: "image_url",
    StepType.SCENARIO: "scenario_data",
    StepType.VIDEO: "video_url",
    StepType.AUDIO: "audio_variants",
}


def migrate_existing_data():
    """Migrate existing workflow data to StepAttempt/Variant model."""
    db = SessionLocal()
    try:
        videos = db.query(Video).all()
        migrated = 0
        skipped = 0

        print(f"Found {len(videos)} videos to process")

        for video in videos:
            steps = db.query(WorkflowStep).filter(WorkflowStep.video_id == video.id).all()

            for step in steps:
                # Skip if already has attempts
                existing_attempts = db.query(StepAttempt).filter(
                    StepAttempt.step_id == step.id
                ).count()
                if existing_attempts > 0:
                    skipped += 1
                    continue

                # Get content from Video model
                content_field = STEP_CONTENT_FIELDS.get(step.step_type)
                if not content_field:
                    continue

                content = getattr(video, content_field, None)
                if not content:
                    continue

                # Create attempt
                attempt = StepAttempt(
                    step_id=step.id,
                    attempt_number=1,
                    status=AttemptStatus.SUCCESS,
                    started_at=step.started_at or step.created_at,
                    completed_at=step.completed_at
                )
                db.add(attempt)
                db.flush()

                # Wrap non-dict content
                if isinstance(content, str):
                    variant_content = {"url": content}
                elif isinstance(content, list):
                    variant_content = {"items": content}
                elif isinstance(content, dict):
                    variant_content = content
                else:
                    variant_content = {"value": str(content)}

                # Create variant
                variant = Variant(
                    attempt_id=attempt.id,
                    variant_number=1,
                    content=variant_content,
                    is_selected=True
                )
                db.add(variant)
                db.flush()

                # Update step's selected_variant_id
                step.selected_variant_id = variant.id
                migrated += 1

        db.commit()
        print(f"Migration complete: {migrated} steps migrated, {skipped} already had attempts")

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate_existing_data()
