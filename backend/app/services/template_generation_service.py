"""
Template Generation Service - pipeline for template project video generation.

Pipeline:
1. LLM preprocessing
2. Generate image prompt
3. Generate image
4. Generate video
5. Merge audio (if hook_audio_path provided)
"""

import asyncio
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.template_settings import TemplateSettings
from app.models.video_template import VideoTemplate
from app.models.variant import Variant
from app.models.template_generation import TemplateGeneration, GenerationStatus
from app.services.openai_client import OpenAIClient
from app.services.openai_service import openai_service
from app.services.fal_client import FalClient, FalClientError
from app.services.media_downloader import download_image, download_video
from app.core.media_processor import media_processor

logger = logging.getLogger(__name__)


class GenerationError(Exception):
    """Base exception for generation errors."""
    def __init__(self, message: str, step: str):
        self.message = message
        self.step = step
        super().__init__(message)


class TemplateGenerationService:
    """Orchestrates the video generation pipeline."""

    def __init__(self):
        self.openai = OpenAIClient()
        self.fal = FalClient()

    async def run_generation(
        self,
        db: Session,
        generation_id: int,
        resume_from_step: Optional[str] = None,
        hook_audio_path: Optional[str] = None,
    ) -> TemplateGeneration:
        """
        Run the generation pipeline.

        Args:
            db: Database session
            generation_id: ID of the TemplateGeneration record
            resume_from_step: If set, resume from this step (for retries)
            hook_audio_path: Path to pre-trimmed hook audio for merging

        Returns:
            Updated TemplateGeneration record
        """
        generation = db.query(TemplateGeneration).filter(
            TemplateGeneration.id == generation_id
        ).first()

        if not generation:
            raise ValueError(f"Generation {generation_id} not found")

        # Get related objects
        settings = db.query(TemplateSettings).filter(
            TemplateSettings.project_id == generation.project_id
        ).first()

        variant = db.query(Variant).filter(
            Variant.id == generation.variant_id
        ).first() if generation.variant_id else None

        video_template = db.query(VideoTemplate).filter(
            VideoTemplate.id == generation.video_template_id
        ).first() if generation.video_template_id else None

        if not settings:
            await self._fail_generation(db, generation, "preprocessing", "Template settings not found")
            return generation

        if not variant:
            await self._fail_generation(db, generation, "preprocessing", "Variant not found")
            return generation

        if not video_template:
            await self._fail_generation(db, generation, "preprocessing", "Video template not found")
            return generation

        # Determine which steps to run
        steps = ["preprocessing", "image_prompt", "image", "video"]
        if hook_audio_path:
            steps.append("merge_audio")

        start_index = 0
        if resume_from_step and resume_from_step in steps:
            start_index = steps.index(resume_from_step)

        try:
            for step in steps[start_index:]:
                # Re-read from DB to check for cancellation
                db.refresh(generation)
                if generation.status == GenerationStatus.CANCELLED.value:
                    logger.info(f"Generation {generation.id} cancelled, stopping pipeline")
                    return generation

                if step == "preprocessing":
                    await self._step_preprocessing(db, generation, settings, variant)
                elif step == "image_prompt":
                    await self._step_image_prompt(db, generation, settings, variant)
                elif step == "image":
                    await self._step_image(db, generation, settings)
                elif step == "video":
                    await self._step_video(db, generation, settings, video_template)
                elif step == "merge_audio":
                    await self._step_merge_audio(db, generation, hook_audio_path)

            # Mark as completed
            generation.status = GenerationStatus.COMPLETED.value
            generation.completed_at = datetime.utcnow()
            db.commit()

            # Pre-generate publishing metadata (non-blocking)
            await self._generate_metadata(db, generation)

            logger.info(f"Generation {generation_id} completed successfully")

        except GenerationError as e:
            await self._fail_generation(db, generation, e.step, e.message)
            logger.error(f"Generation {generation_id} failed at {e.step}: {e.message}")

        except Exception as e:
            await self._fail_generation(db, generation, "unknown", str(e))
            logger.exception(f"Generation {generation_id} failed unexpectedly")

        return generation

    async def _step_preprocessing(
        self,
        db: Session,
        generation: TemplateGeneration,
        settings: TemplateSettings,
        variant: Variant
    ):
        """Step 1: LLM preprocessing of variant data."""
        generation.status = GenerationStatus.PREPROCESSING.value
        db.commit()

        try:
            # Build prompt: template + variant data
            variant_lines = [f"{k}: {v}" for k, v in variant.data.items()]
            variant_str = "\n".join(variant_lines)
            prompt = f"{settings.preprocessing_prompt}\n\n{variant_str}"

            # Call LLM (system prompt not needed - all instructions are in preprocessing_prompt)
            result = await self.openai.generate_json(
                prompt=prompt,
                system_prompt=None,
                model=generation.llm_model,
                temperature=0.7
            )

            generation.preprocessing_result = result
            db.commit()

            logger.info(f"Generation {generation.id}: preprocessing complete")

        except Exception as e:
            raise GenerationError(f"LLM call failed: {e}", "preprocessing")

    async def _step_image_prompt(
        self,
        db: Session,
        generation: TemplateGeneration,
        settings: TemplateSettings,
        variant: Variant
    ):
        """Step 2: Generate image prompt via LLM."""
        try:
            import json

            # Build the input for LLM: image_prompt_template + JSON from preprocessing
            preprocessing_json = json.dumps(generation.preprocessing_result, ensure_ascii=False, indent=2)

            # Combine template with JSON data
            prompt = f"{settings.image_prompt_template}\n\n{preprocessing_json}"

            # Call LLM to generate the actual image prompt
            system_prompt = "You are a prompt generator. Output ONLY the final image prompt, nothing else. No explanations, no markdown, no quotes."

            image_prompt = await self.openai.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                model=generation.llm_model,
                temperature=0.7
            )

            # Clean up the response
            image_prompt = image_prompt.strip()

            generation.image_prompt = image_prompt
            db.commit()

            logger.info(f"Generation {generation.id}: image prompt generated via LLM")

        except Exception as e:
            raise GenerationError(f"Image prompt generation failed: {e}", "image_prompt")

    async def _step_image(
        self,
        db: Session,
        generation: TemplateGeneration,
        settings: TemplateSettings
    ):
        """Step 3: Generate image using fal.ai."""
        generation.status = GenerationStatus.GENERATING_IMAGE.value
        db.commit()

        if not generation.image_prompt:
            raise GenerationError("No image prompt available", "image")

        try:
            # Check if we have a pending request from a previous attempt
            if generation.fal_image_request_id and not generation.image_url:
                logger.info(f"Generation {generation.id}: resuming image polling for {generation.fal_image_request_id}")
                request_id = generation.fal_image_request_id
            else:
                # Submit new image generation task
                request_id = await self.fal.submit_image(
                    prompt=generation.image_prompt,
                    aspect_ratio=settings.image_aspect_ratio,
                    model=generation.image_model
                )
                # Save request_id immediately
                generation.fal_image_request_id = request_id
                db.commit()
                logger.info(f"Generation {generation.id}: submitted image task {request_id}")

            # Poll for result
            image_url = await self.fal.poll_image(
                request_id=request_id,
                model=generation.image_model
            )

            generation.image_url = image_url

            # Download locally (use generation.id as video_id for filename)
            local_path = await download_image(image_url, generation.id)
            generation.image_path = local_path

            db.commit()

            logger.info(f"Generation {generation.id}: image generated")

        except FalClientError as e:
            raise GenerationError(f"Image generation failed: {e}", "image")
        except Exception as e:
            raise GenerationError(f"Image generation failed: {e}", "image")

    async def _step_video(
        self,
        db: Session,
        generation: TemplateGeneration,
        settings: TemplateSettings,
        video_template: VideoTemplate
    ):
        """Step 4: Generate video using fal.ai."""
        generation.status = GenerationStatus.GENERATING_VIDEO.value
        db.commit()

        if not generation.image_url:
            raise GenerationError("No image URL available", "video")

        try:
            # Use video template prompt directly (no placeholder replacement)
            if not generation.video_prompt:
                generation.video_prompt = video_template.prompt
                db.commit()

            # Check if we have a pending request from a previous attempt
            if generation.fal_video_request_id and not generation.video_url:
                logger.info(f"Generation {generation.id}: resuming video polling for {generation.fal_video_request_id}")
                request_id = generation.fal_video_request_id
            else:
                # Get params from settings
                is_kling = "kling" in generation.video_model.lower()
                aspect_ratio = settings.image_aspect_ratio if is_kling else "auto"

                # Submit new video generation task
                request_id = await self.fal.submit_video(
                    image_url=generation.image_url,
                    prompt=generation.video_prompt,
                    duration=settings.video_duration,
                    aspect_ratio=aspect_ratio,
                    generate_audio=False,  # Template type: no audio
                    model=generation.video_model
                )
                # Save request_id immediately
                generation.fal_video_request_id = request_id
                db.commit()
                logger.info(f"Generation {generation.id}: submitted video task {request_id}")

            # Poll for result
            video_url = await self.fal.poll_video(
                request_id=request_id,
                model=generation.video_model
            )

            generation.video_url = video_url

            # Download locally (use generation.id as video_id for filename)
            local_path = await download_video(video_url, generation.id)
            generation.video_path = local_path

            db.commit()

            logger.info(f"Generation {generation.id}: video generated")

        except FalClientError as e:
            raise GenerationError(f"Video generation failed: {e}", "video")
        except Exception as e:
            raise GenerationError(f"Video generation failed: {e}", "video")

    async def _step_merge_audio(
        self,
        db: Session,
        generation: TemplateGeneration,
        hook_audio_path: str,
    ):
        """Step 5: Merge pre-generated hook audio with video."""
        generation.status = GenerationStatus.MERGING_AUDIO.value
        db.commit()

        if not generation.video_path:
            raise GenerationError("No video path available for merge", "merge_audio")

        try:
            from app.core.config import settings as app_settings

            video_path = os.path.join(app_settings.MEDIA_DIR, generation.video_path)
            if not os.path.exists(video_path):
                raise GenerationError(f"Video file not found: {video_path}", "merge_audio")

            # Merge video + audio
            merged_path = await media_processor.merge_video_audio(
                video_path=video_path,
                audio_path=hook_audio_path,
            )

            # Move merged file to permanent location
            final_filename = f"gen_{generation.id}_with_audio.mp4"
            final_dir = os.path.join(app_settings.MEDIA_DIR, "videos")
            os.makedirs(final_dir, exist_ok=True)
            final_path = os.path.join(final_dir, final_filename)
            shutil.move(merged_path, final_path)

            # Store relative path (consistent with video_path)
            generation.audio_path = hook_audio_path
            generation.video_with_audio_path = f"videos/{final_filename}"
            db.commit()

            logger.info(f"Generation {generation.id}: audio merged successfully")

        except GenerationError:
            raise
        except Exception as e:
            raise GenerationError(f"Audio merge failed: {e}", "merge_audio")

    async def _generate_metadata(
        self,
        db: Session,
        generation: TemplateGeneration
    ):
        """Pre-generate publishing metadata after video completion."""
        try:
            project = db.query(Project).filter(
                Project.id == generation.project_id
            ).first()

            platforms = (project.platforms or ["youtube"]) if project else ["youtube"]

            scenario_data = {
                "preprocessing_result": generation.preprocessing_result,
                "image_prompt": generation.image_prompt,
                "video_prompt": generation.video_prompt,
            }

            metadata = await openai_service.generate_publishing_meta(
                platforms=platforms,
                scenario_data=scenario_data,
                fallback_text=generation.image_prompt[:500] if generation.image_prompt else None
            )

            generation.publishing_metadata = metadata
            db.commit()

            logger.info(f"Generation {generation.id}: publishing metadata pre-generated")

        except Exception as e:
            # Non-critical — don't fail the generation, just log
            logger.warning(f"Generation {generation.id}: metadata pre-generation failed: {e}")

    async def _fail_generation(
        self,
        db: Session,
        generation: TemplateGeneration,
        step: str,
        message: str
    ):
        """Mark generation as failed — but do NOT overwrite cancelled status."""
        if generation.status == GenerationStatus.CANCELLED.value:
            logger.info(f"Generation {generation.id} is cancelled, not marking as failed")
            return
        generation.status = GenerationStatus.FAILED.value
        generation.failed_at_step = step
        generation.error_message = message
        db.commit()


# Singleton instance
_service: Optional[TemplateGenerationService] = None


def get_template_generation_service() -> TemplateGenerationService:
    """Get or create the template generation service singleton."""
    global _service
    if _service is None:
        _service = TemplateGenerationService()
    return _service
