"""
Discover Service — orchestrates the iterative exploration workflow.

Flow: concept → image rounds → video rounds → extraction → template creation.
"""

import asyncio
from datetime import datetime
from typing import Optional
from pathlib import Path

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.models.discover import (
    DiscoverProject, DiscoverRound, DiscoverItem, DiscoverExtraction,
    DiscoverStage, DiscoverStatus, RoundType, RoundStatus, ItemStatus,
    SelectionStatus,
)
from app.services.openai_client import OpenAIClient
from app.services.fal_client import FalClient
from app.services.media_downloader import download_file, ensure_directories, MEDIA_BASE_DIR
from app.services.prompts.discover import (
    DISCOVER_IMAGE_WIDE_SYSTEM,
    DISCOVER_IMAGE_NARROW_SYSTEM,
    DISCOVER_VIDEO_SYSTEM,
    DISCOVER_EXTRACTION_SYSTEM,
    build_discover_wide_prompt,
    build_discover_narrow_prompt,
    build_discover_video_prompt,
    build_discover_extraction_prompt,
)

import logging

logger = logging.getLogger(__name__)

# Defaults (tunable)
IMAGE_ITEMS_PER_ROUND = 5
VIDEO_ITEMS_PER_ROUND = 4
MAX_REJECTED_FOR_NARROWING = 30


class DiscoverService:
    """Orchestrates the Discover workflow."""

    def __init__(self):
        self.openai = OpenAIClient()
        self.fal = FalClient()

    # ========== Project CRUD ==========

    async def create_project(
        self, db: Session, user_id: int, workspace_id: int,
        concept: str, name: str, **kwargs
    ) -> DiscoverProject:
        """Create a new Discover project."""
        project = DiscoverProject(
            workspace_id=workspace_id,
            user_id=user_id,
            concept=concept,
            name=name,
            image_model=kwargs.get("image_model", "fal-ai/flux-pro/v1.1"),
            video_model=kwargs.get("video_model", "fal-ai/veo3/fast/image-to-video"),
            image_aspect_ratio=kwargs.get("image_aspect_ratio", "9:16"),
            video_duration=kwargs.get("video_duration", "6s"),
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        logger.info(f"Created discover project {project.id}: {name}")
        return project

    async def get_project(
        self, db: Session, project_id: int, user_id: int
    ) -> DiscoverProject:
        """Get project with eager-loaded rounds, items, and extraction."""
        project = (
            db.query(DiscoverProject)
            .options(
                joinedload(DiscoverProject.rounds)
                .joinedload(DiscoverRound.items),
                joinedload(DiscoverProject.extraction),
            )
            .filter(
                DiscoverProject.id == project_id,
                DiscoverProject.user_id == user_id,
            )
            .first()
        )
        if not project:
            raise ValueError(f"Discover project {project_id} not found")
        return project

    async def list_projects(
        self, db: Session, user_id: int,
        workspace_id: int | None = None,
        status: str | None = None,
    ) -> list[DiscoverProject]:
        """List discover projects, optionally filtered by workspace."""
        query = db.query(DiscoverProject).filter(
            DiscoverProject.user_id == user_id,
        )
        if workspace_id is not None:
            query = query.filter(DiscoverProject.workspace_id == workspace_id)
        if status:
            query = query.filter(DiscoverProject.status == status)
        return query.order_by(DiscoverProject.created_at.desc()).all()

    async def archive_project(
        self, db: Session, project_id: int, user_id: int
    ) -> None:
        """Soft-archive a discover project."""
        project = await self.get_project(db, project_id, user_id)
        project.status = DiscoverStatus.ARCHIVED.value
        project.updated_at = datetime.utcnow()
        db.commit()
        logger.info(f"Archived discover project {project_id}")

    # ========== Round Generation ==========

    async def generate_round(
        self, db: Session, project_id: int, user_id: int,
        feedback: str | None = None,
        model_override: str | None = None,
        count_override: int | None = None,
    ) -> DiscoverRound:
        """
        Generate the next round of exploration.

        1. Determine round type based on current stage
        2. Check no active (generating) round exists
        3. Call LLM to generate prompts
        4. Create round + items
        5. Start background FAL generation
        """
        project = await self.get_project(db, project_id, user_id)

        # Block concurrent generation
        active_round = (
            db.query(DiscoverRound)
            .filter(
                DiscoverRound.project_id == project_id,
                DiscoverRound.status == RoundStatus.GENERATING.value,
            )
            .first()
        )
        if active_round:
            raise ValueError("A round is already generating. Wait for it to complete.")

        # Update model if overridden
        if model_override:
            if project.stage == DiscoverStage.IMAGES.value:
                project.image_model = model_override
            elif project.stage == DiscoverStage.VIDEOS.value:
                project.video_model = model_override
            db.commit()

        if project.stage == DiscoverStage.IMAGES.value:
            return await self._generate_image_round(db, project, feedback, count_override)
        elif project.stage == DiscoverStage.VIDEOS.value:
            return await self._generate_video_round(db, project, feedback, count_override)
        else:
            raise ValueError(f"Cannot generate rounds in stage: {project.stage}")

    async def _generate_image_round(
        self, db: Session, project: DiscoverProject,
        feedback: str | None = None,
        count_override: int | None = None,
    ) -> DiscoverRound:
        """Generate an image exploration round."""
        round_number = project.current_image_round + 1
        count = count_override or IMAGE_ITEMS_PER_ROUND

        ar = project.image_aspect_ratio

        if round_number == 1:
            # Wide: use concept only
            system_prompt = DISCOVER_IMAGE_WIDE_SYSTEM.format(count=count, aspect_ratio=ar)
            user_prompt = build_discover_wide_prompt(project.concept, count)
        else:
            # Narrowing: gather selections from previous rounds
            selected, rejected = self._gather_selections(db, project, RoundType.IMAGE.value)
            system_prompt = DISCOVER_IMAGE_NARROW_SYSTEM.format(count=count, aspect_ratio=ar)
            user_prompt = build_discover_narrow_prompt(
                project.concept, selected, rejected, feedback, count
            )

        # Call LLM for prompts
        result = await self.openai.generate_json(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model="gpt-4o",
            temperature=0.9 if round_number == 1 else 0.7,
        )
        prompts = result.get("prompts", [])
        if not prompts:
            raise ValueError("LLM returned no prompts")

        # Create round + items
        round_obj = DiscoverRound(
            project_id=project.id,
            round_number=round_number,
            round_type=RoundType.IMAGE.value,
            status=RoundStatus.GENERATING.value,
            system_prompt_used=system_prompt,
            user_prompt_used=user_prompt,
            generated_prompts=prompts,
            feedback_text=feedback,
            total_items=len(prompts),
        )
        db.add(round_obj)
        db.flush()

        for i, prompt in enumerate(prompts):
            item = DiscoverItem(
                round_id=round_obj.id,
                position=i + 1,
                prompt=prompt,
                status=ItemStatus.PENDING.value,
            )
            db.add(item)

        project.current_image_round = round_number
        project.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(round_obj)

        logger.info(
            f"Discover {project.id}: image round {round_number} created "
            f"with {len(prompts)} prompts"
        )

        # Start background generation
        asyncio.create_task(
            self._generate_items_background(project.id, round_obj.id, RoundType.IMAGE.value)
        )

        return round_obj

    async def _generate_video_round(
        self, db: Session, project: DiscoverProject,
        feedback: str | None = None,
        count_override: int | None = None,
    ) -> DiscoverRound:
        """Generate a video exploration round."""
        round_number = project.current_video_round + 1
        count = count_override or VIDEO_ITEMS_PER_ROUND

        # Get finalist image prompt
        finalist_image = (
            db.query(DiscoverItem)
            .filter(DiscoverItem.id == project.finalist_image_item_id)
            .first()
        )
        if not finalist_image:
            raise ValueError("No finalist image selected")

        ar = project.image_aspect_ratio

        system_prompt = DISCOVER_VIDEO_SYSTEM.format(count=count, aspect_ratio=ar)

        if round_number == 1:
            user_prompt = build_discover_video_prompt(
                finalist_image.prompt, count, direction=feedback,
            )
        else:
            selected, rejected = self._gather_selections(db, project, RoundType.VIDEO.value)
            user_prompt = build_discover_video_prompt(
                finalist_image.prompt, count, selected, rejected, feedback,
            )

        result = await self.openai.generate_json(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model="gpt-4o",
            temperature=0.8,
        )
        prompts = result.get("prompts", [])
        if not prompts:
            raise ValueError("LLM returned no video prompts")

        round_obj = DiscoverRound(
            project_id=project.id,
            round_number=round_number,
            round_type=RoundType.VIDEO.value,
            status=RoundStatus.GENERATING.value,
            system_prompt_used=system_prompt,
            user_prompt_used=user_prompt,
            generated_prompts=prompts,
            feedback_text=feedback,
            total_items=len(prompts),
        )
        db.add(round_obj)
        db.flush()

        for i, prompt in enumerate(prompts):
            item = DiscoverItem(
                round_id=round_obj.id,
                position=i + 1,
                prompt=prompt,
                status=ItemStatus.PENDING.value,
                source_image_item_id=finalist_image.id,
            )
            db.add(item)

        project.current_video_round = round_number
        project.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(round_obj)

        logger.info(
            f"Discover {project.id}: video round {round_number} created "
            f"with {len(prompts)} prompts"
        )

        asyncio.create_task(
            self._generate_items_background(project.id, round_obj.id, RoundType.VIDEO.value)
        )

        return round_obj

    async def _generate_items_background(
        self, project_id: int, round_id: int, item_type: str
    ):
        """Background task: generate all items in a round via FAL (parallel)."""
        from app.db.base import SessionLocal

        db = SessionLocal()
        try:
            round_obj = db.query(DiscoverRound).filter(
                DiscoverRound.id == round_id
            ).first()
            items = db.query(DiscoverItem).filter(
                DiscoverItem.round_id == round_id
            ).order_by(DiscoverItem.position).all()
            project = db.query(DiscoverProject).filter(
                DiscoverProject.id == project_id
            ).first()

            # For video generation, get source image URL once
            source_image_url = None
            if item_type == RoundType.VIDEO.value and items:
                source_item = db.query(DiscoverItem).filter(
                    DiscoverItem.id == items[0].source_image_item_id
                ).first()
                source_image_url = source_item.result_url if source_item else None

            # Mark all as generating
            for item in items:
                item.status = ItemStatus.GENERATING.value
            db.commit()

            # Prepare generation parameters (snapshot before parallel execution)
            gen_params = []
            for item in items:
                gen_params.append({
                    "item_id": item.id,
                    "prompt": item.prompt,
                    "position": item.position,
                })

            # Run all generations in parallel
            async def generate_one(params: dict) -> dict:
                """Generate a single item. Returns result dict."""
                try:
                    if item_type == RoundType.IMAGE.value:
                        url = await self.fal.generate_image(
                            prompt=params["prompt"],
                            aspect_ratio=project.image_aspect_ratio,
                            model=project.image_model,
                        )
                        local_path = await self._download_discover_media(
                            url, project_id, round_id, params["position"], "image"
                        )
                    else:
                        url = await self.fal.generate_video(
                            image_url=source_image_url,
                            prompt=params["prompt"],
                            duration=project.video_duration,
                            aspect_ratio=project.image_aspect_ratio,
                            generate_audio=False,
                            model=project.video_model,
                        )
                        local_path = await self._download_discover_media(
                            url, project_id, round_id, params["position"], "video"
                        )
                    return {
                        "item_id": params["item_id"],
                        "success": True,
                        "url": url,
                        "local_path": local_path,
                    }
                except Exception as e:
                    logger.error(f"Discover item {params['item_id']} failed: {e}")
                    return {
                        "item_id": params["item_id"],
                        "success": False,
                        "error": str(e)[:500],
                    }

            # Execute all in parallel
            results = await asyncio.gather(*[generate_one(p) for p in gen_params])

            # Update items with results (new db session for thread safety)
            db2 = SessionLocal()
            try:
                completed = 0
                failed = 0

                for result in results:
                    item = db2.query(DiscoverItem).filter(
                        DiscoverItem.id == result["item_id"]
                    ).first()
                    if not item:
                        continue

                    if result["success"]:
                        item.result_url = result["url"]
                        item.local_path = result["local_path"]
                        item.status = ItemStatus.COMPLETED.value
                        item.completed_at = datetime.utcnow()
                        completed += 1
                    else:
                        item.status = ItemStatus.FAILED.value
                        item.error_message = result.get("error", "Unknown error")
                        failed += 1

                # Update round status
                round_obj2 = db2.query(DiscoverRound).filter(
                    DiscoverRound.id == round_id
                ).first()
                if round_obj2:
                    if failed == len(items):
                        round_obj2.status = RoundStatus.FAILED.value
                    else:
                        round_obj2.status = RoundStatus.COMPLETED.value
                    round_obj2.completed_at = datetime.utcnow()

                db2.commit()

                logger.info(
                    f"Discover round {round_id}: {completed} completed, {failed} failed (parallel)"
                )
            finally:
                db2.close()

        except Exception as e:
            logger.error(f"Background generation failed for round {round_id}: {e}")
            try:
                round_obj = db.query(DiscoverRound).filter(
                    DiscoverRound.id == round_id
                ).first()
                if round_obj:
                    round_obj.status = RoundStatus.FAILED.value
                    round_obj.error_message = str(e)[:500]
                    db.commit()
            except Exception:
                pass
        finally:
            db.close()

    # ========== Selection ==========

    async def submit_selection(
        self, db: Session, project_id: int, round_id: int,
        selections: dict[str, str], feedback: str | None = None,
    ) -> dict:
        """Submit user selections for a round."""
        round_obj = db.query(DiscoverRound).filter(
            DiscoverRound.id == round_id,
            DiscoverRound.project_id == project_id,
            DiscoverRound.status == RoundStatus.COMPLETED.value,
        ).first()
        if not round_obj:
            raise ValueError("Round not found or not completed")

        items = db.query(DiscoverItem).filter(
            DiscoverItem.round_id == round_id
        ).all()

        selected_count = 0
        rejected_count = 0

        for item in items:
            sel = selections.get(str(item.id), SelectionStatus.UNREVIEWED.value)
            item.selection = sel
            if sel == SelectionStatus.SELECTED.value:
                selected_count += 1
            elif sel == SelectionStatus.REJECTED.value:
                rejected_count += 1

        round_obj.selected_count = selected_count
        round_obj.rejected_count = rejected_count
        if feedback:
            round_obj.feedback_text = feedback
        db.commit()

        return {
            "round_id": round_id,
            "selected_count": selected_count,
            "rejected_count": rejected_count,
            "can_advance_to_video": (
                selected_count == 1
                and round_obj.round_type == RoundType.IMAGE.value
            ),
            "can_generate_next_round": selected_count >= 1,
        }

    # ========== Stage Advancement ==========

    async def advance_to_video(
        self, db: Session, project_id: int, user_id: int,
        finalist_item_id: int,
    ) -> DiscoverProject:
        """Advance from images to videos stage."""
        project = await self.get_project(db, project_id, user_id)

        if project.stage != DiscoverStage.IMAGES.value:
            raise ValueError(f"Cannot advance: stage is {project.stage}, expected images")

        finalist_item = db.query(DiscoverItem).filter(
            DiscoverItem.id == finalist_item_id,
            DiscoverItem.status == ItemStatus.COMPLETED.value,
            DiscoverItem.selection == SelectionStatus.SELECTED.value,
        ).first()
        if not finalist_item:
            raise ValueError("Finalist item not found or not completed/selected")

        # Ensure finalist image is downloaded locally (FAL URLs expire)
        if finalist_item.result_url and not finalist_item.local_path:
            finalist_item.local_path = await self._download_discover_media(
                finalist_item.result_url, project_id, 0, 0, "image"
            )

        project.stage = DiscoverStage.VIDEOS.value
        project.finalist_image_item_id = finalist_item_id
        project.updated_at = datetime.utcnow()
        db.commit()

        logger.info(f"Discover {project_id}: advanced to videos, finalist image={finalist_item_id}")
        return project

    async def advance_to_extraction(
        self, db: Session, project_id: int, user_id: int,
        finalist_video_item_id: int,
    ) -> DiscoverProject:
        """Advance from videos to extraction stage."""
        project = await self.get_project(db, project_id, user_id)

        if project.stage != DiscoverStage.VIDEOS.value:
            raise ValueError(f"Cannot advance: stage is {project.stage}, expected videos")

        finalist_item = db.query(DiscoverItem).filter(
            DiscoverItem.id == finalist_video_item_id,
            DiscoverItem.status == ItemStatus.COMPLETED.value,
            DiscoverItem.selection == SelectionStatus.SELECTED.value,
        ).first()
        if not finalist_item:
            raise ValueError("Video finalist item not found or not completed/selected")

        project.stage = DiscoverStage.EXTRACTION.value
        project.finalist_video_item_id = finalist_video_item_id
        project.updated_at = datetime.utcnow()
        db.commit()

        logger.info(f"Discover {project_id}: advanced to extraction, finalist video={finalist_video_item_id}")
        return project

    # ========== Rollback ==========

    async def rollback(
        self, db: Session, project_id: int, user_id: int,
    ) -> dict:
        """Roll back the last round. Delete items + media."""
        project = await self.get_project(db, project_id, user_id)

        if project.stage == DiscoverStage.VIDEOS.value:
            # Rolling back from video stage → go back to images
            if project.current_video_round > 0:
                return await self._rollback_round(db, project, RoundType.VIDEO.value)
            else:
                # No video rounds yet, go back to images
                project.stage = DiscoverStage.IMAGES.value
                project.finalist_image_item_id = None
                project.updated_at = datetime.utcnow()
                db.commit()
                return {
                    "rolled_back_round_id": None,
                    "current_image_round": project.current_image_round,
                    "current_video_round": 0,
                    "stage": project.stage,
                }

        elif project.stage == DiscoverStage.IMAGES.value:
            if project.current_image_round < 1:
                raise ValueError("No rounds to rollback")
            return await self._rollback_round(db, project, RoundType.IMAGE.value)

        else:
            raise ValueError(f"Cannot rollback in stage: {project.stage}")

    async def _rollback_round(
        self, db: Session, project: DiscoverProject, round_type: str,
    ) -> dict:
        """Delete the last round of given type."""
        if round_type == RoundType.IMAGE.value:
            current_round_num = project.current_image_round
        else:
            current_round_num = project.current_video_round

        last_round = db.query(DiscoverRound).filter(
            DiscoverRound.project_id == project.id,
            DiscoverRound.round_type == round_type,
            DiscoverRound.round_number == current_round_num,
        ).first()

        rolled_back_id = last_round.id if last_round else None

        if last_round:
            # Delete items (cascade should handle, but be explicit)
            db.query(DiscoverItem).filter(
                DiscoverItem.round_id == last_round.id
            ).delete()
            db.delete(last_round)

        if round_type == RoundType.IMAGE.value:
            project.current_image_round = current_round_num - 1
        else:
            project.current_video_round = current_round_num - 1

        project.updated_at = datetime.utcnow()
        db.commit()

        logger.info(f"Discover {project.id}: rolled back {round_type} round {current_round_num}")

        return {
            "rolled_back_round_id": rolled_back_id,
            "current_image_round": project.current_image_round,
            "current_video_round": project.current_video_round,
            "stage": project.stage,
        }

    # ========== Extraction ==========

    async def extract_template(
        self, db: Session, project_id: int, user_id: int,
    ) -> DiscoverExtraction:
        """Extract base_prompt + variation_prompt from winning combo."""
        project = await self.get_project(db, project_id, user_id)

        if project.stage not in (
            DiscoverStage.EXTRACTION.value,
            DiscoverStage.VIDEOS.value,
        ):
            raise ValueError(f"Cannot extract in stage: {project.stage}")

        finalist_image = db.query(DiscoverItem).filter(
            DiscoverItem.id == project.finalist_image_item_id
        ).first()
        if not finalist_image:
            raise ValueError("No finalist image")

        finalist_video = None
        if project.finalist_video_item_id:
            finalist_video = db.query(DiscoverItem).filter(
                DiscoverItem.id == project.finalist_video_item_id
            ).first()

        # Call LLM
        result = await self.openai.generate_json(
            prompt=build_discover_extraction_prompt(
                finalist_image.prompt,
                finalist_video.prompt if finalist_video else None,
                video_duration=project.video_duration or "5s",
                aspect_ratio=project.image_aspect_ratio or "9:16",
            ),
            system_prompt=DISCOVER_EXTRACTION_SYSTEM,
            model="gpt-4o",
            temperature=0.5,
        )

        # Delete old extraction if re-extracting
        old = db.query(DiscoverExtraction).filter(
            DiscoverExtraction.project_id == project.id
        ).first()
        if old:
            db.delete(old)
            db.flush()

        extraction = DiscoverExtraction(
            project_id=project.id,
            winning_image_prompt=finalist_image.prompt,
            winning_video_prompt=finalist_video.prompt if finalist_video else None,
            base_prompt=result["base_prompt"],
            variation_prompt=result["variation_prompt"],
            video_template_prompt=result.get("video_template_prompt"),
            slot_names=result.get("slot_names"),
            slot_examples=result.get("slot_examples"),
        )
        db.add(extraction)

        project.stage = DiscoverStage.EXTRACTION.value
        project.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(extraction)

        logger.info(f"Discover {project_id}: extraction complete")
        return extraction

    async def update_extraction(
        self, db: Session, project_id: int, user_id: int,
        edited_base_prompt: str | None = None,
        edited_variation_prompt: str | None = None,
    ) -> DiscoverExtraction:
        """Update user-edited extraction prompts."""
        project = await self.get_project(db, project_id, user_id)
        extraction = project.extraction
        if not extraction:
            raise ValueError("No extraction found")

        if edited_base_prompt is not None:
            extraction.edited_base_prompt = edited_base_prompt
        if edited_variation_prompt is not None:
            extraction.edited_variation_prompt = edited_variation_prompt
        extraction.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(extraction)
        return extraction

    # ========== Template Creation ==========

    async def _generate_preprocessing_prompt(
        self,
        winning_image_prompt: str,
        winning_video_prompt: str | None,
        base_prompt: str,
        slot_names: list[str],
        slot_examples: dict | None,
    ) -> str:
        """Generate a rich preprocessing megaprompt via LLM.

        The preprocessing prompt takes variant data (slot values) and produces
        a detailed JSON scene description that the image_prompt_template
        can then convert into a final image generation prompt.
        """
        import json as _json

        examples_str = ""
        if slot_examples:
            examples_str = f"\nSlot examples: {_json.dumps(slot_examples, ensure_ascii=False)}"

        prompt = f"""You are a prompt-engineering expert. Your task is to create a PREPROCESSING MEGAPROMPT for an AI image/video generation pipeline.

CONTEXT — This is how the pipeline works:
1. Variant generation: LLM generates rows of data with columns: {', '.join(slot_names)}
2. PREPROCESSING (what you're writing): Takes ONE variant row → produces a DETAILED JSON scene description
3. Image prompt generation: Another LLM takes that JSON + a template → writes the final image prompt

YOUR OUTPUT must be a complete, self-contained preprocessing prompt that:
- Accepts input: one row of variant data with fields: {', '.join(slot_names)}{examples_str}
- Produces output: a SINGLE JSON object with a rich, structured scene description
- Captures the EXACT visual style, mood, composition from the reference prompts below
- Defines a clear JSON schema with nested sections (subject, composition, lighting, camera, constraints, etc.)
- Includes strict rules: JSON only, no explanations, no markdown

REFERENCE — The winning image prompt that defines the visual style:
{winning_image_prompt}

REFERENCE — The base prompt template (shows what varies):
{base_prompt}

{f"REFERENCE — The winning video prompt (for motion/mood context):" + chr(10) + winning_video_prompt if winning_video_prompt else ""}

REQUIREMENTS for your preprocessing prompt:
1. Define the JSON schema explicitly with all keys
2. Hardcode the visual style elements (lighting, camera angle, composition, mood) from the reference
3. Only the slot values ({', '.join(slot_names)}) should vary — everything else stays consistent
4. Include constraints section (no text, no watermark, etc.)
5. Be detailed enough that ANY variant produces a high-quality, on-brand result
6. Write it as a direct instruction to an LLM (imperative tone)

Output ONLY the preprocessing prompt text. No explanations before or after."""

        result = await self.openai.generate_text(
            prompt=prompt,
            system_prompt="You are a world-class prompt engineer. Output only the requested prompt, nothing else.",
            model="gpt-4o",
            temperature=0.5,
        )

        logger.info(f"Generated preprocessing prompt ({len(result)} chars)")
        return result.strip()

    async def create_template_project(
        self, db: Session, project_id: int, user_id: int,
        name: str, platforms: list[str],
        video_template_prompt: str | None = None,
    ) -> int:
        """Create Template project from extraction."""
        from app.models.project import Project
        from app.models.template_settings import TemplateSettings
        from app.models.video_template import VideoTemplate

        project = await self.get_project(db, project_id, user_id)
        extraction = project.extraction
        if not extraction:
            raise ValueError("No extraction — run extract first")

        # Use edited versions if available
        base_prompt = extraction.edited_base_prompt or extraction.base_prompt
        variation_prompt = extraction.edited_variation_prompt or extraction.variation_prompt
        slot_names = extraction.slot_names or ["object"]

        # Use templated video prompt from extraction (with slots), fallback to winning
        video_prompt = (
            extraction.edited_video_template_prompt
            or extraction.video_template_prompt
            or video_template_prompt
            or extraction.winning_video_prompt
            or ""
        )

        # Generate preprocessing megaprompt via LLM
        preprocessing = await self._generate_preprocessing_prompt(
            winning_image_prompt=extraction.winning_image_prompt,
            winning_video_prompt=extraction.winning_video_prompt,
            base_prompt=base_prompt,
            slot_names=slot_names,
            slot_examples=extraction.slot_examples,
        )

        # Create Project
        template_project = Project(
            user_id=user_id,
            workspace_id=project.workspace_id,
            name=name,
            project_type="template",
            story_template="",
            platforms=platforms,
            duration=10,
            aspect_ratio=project.image_aspect_ratio,
        )
        db.add(template_project)
        db.flush()

        # Create TemplateSettings
        settings = TemplateSettings(
            project_id=template_project.id,
            preprocessing_prompt=preprocessing,
            image_prompt_template=base_prompt,
            variant_generation_prompt=variation_prompt,
            csv_columns=slot_names,
            llm_model="gpt-4o-mini",
            image_model=project.image_model,
            video_model=project.video_model,
            image_aspect_ratio=project.image_aspect_ratio,
            video_duration=project.video_duration,
            source_discover_id=project.id,
        )
        db.add(settings)

        # Create VideoTemplate
        vt = VideoTemplate(
            project_id=template_project.id,
            name="Default",
            prompt=video_prompt,
            is_default=True,
        )
        db.add(vt)

        # Update discover project
        project.created_project_id = template_project.id
        project.stage = DiscoverStage.COMPLETED.value
        project.status = DiscoverStatus.COMPLETED.value
        project.updated_at = datetime.utcnow()
        db.commit()

        logger.info(
            f"Discover {project_id}: created template project {template_project.id}"
        )
        return template_project.id

    # ========== Retry ==========

    async def retry_failed_items(
        self, db: Session, project_id: int, round_id: int, user_id: int,
    ) -> int:
        """Retry all failed items in a round. Returns count of retried items."""
        project = await self.get_project(db, project_id, user_id)

        round_obj = db.query(DiscoverRound).filter(
            DiscoverRound.id == round_id,
            DiscoverRound.project_id == project_id,
        ).first()
        if not round_obj:
            raise ValueError("Round not found")

        failed_items = db.query(DiscoverItem).filter(
            DiscoverItem.round_id == round_id,
            DiscoverItem.status == ItemStatus.FAILED.value,
        ).all()

        if not failed_items:
            return 0

        # Reset failed items to pending
        for item in failed_items:
            item.status = ItemStatus.PENDING.value
            item.error_message = None

        round_obj.status = RoundStatus.GENERATING.value
        db.commit()

        # Start background retry
        asyncio.create_task(
            self._generate_items_background(project_id, round_id, round_obj.round_type)
        )

        return len(failed_items)

    # ========== Helpers ==========

    def _gather_selections(
        self, db: Session, project: DiscoverProject, round_type: str,
    ) -> tuple[list[str], list[str]]:
        """Gather all selected/rejected prompts across rounds for narrowing."""
        rounds = db.query(DiscoverRound).filter(
            DiscoverRound.project_id == project.id,
            DiscoverRound.round_type == round_type,
        ).order_by(DiscoverRound.round_number).all()

        selected = []
        rejected = []
        for r in rounds:
            items = db.query(DiscoverItem).filter(
                DiscoverItem.round_id == r.id
            ).all()
            for item in items:
                if item.selection == SelectionStatus.SELECTED.value:
                    selected.append(item.prompt)
                else:
                    rejected.append(item.prompt)

        # Context window management: cap rejected prompts
        if len(rejected) > MAX_REJECTED_FOR_NARROWING:
            rejected = rejected[-MAX_REJECTED_FOR_NARROWING:]

        return selected, rejected

    async def _download_discover_media(
        self, url: str, project_id: int, round_id: int,
        position: int, media_type: str,
    ) -> Optional[str]:
        """Download FAL result to local storage with discover-specific naming."""
        if not url:
            return None

        ensure_directories()

        ext = "jpg" if media_type == "image" else "mp4"
        filename = f"discover_{project_id}_r{round_id}_{position}.{ext}"
        folder = "images" if media_type == "image" else "videos"
        dest_path = MEDIA_BASE_DIR / folder / filename

        success = await download_file(url, dest_path)
        if success:
            return f"{folder}/{filename}"
        return None


# ========== Singleton ==========

_service: Optional[DiscoverService] = None


def get_discover_service() -> DiscoverService:
    global _service
    if _service is None:
        _service = DiscoverService()
    return _service
