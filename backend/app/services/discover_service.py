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

from app.models.user import WorkspaceMember

from app.models.discover import (
    DiscoverProject, DiscoverRound, DiscoverItem, DiscoverExtraction,
    DiscoverRefinement, DiscoverAudioVariant,
    DiscoverStage, DiscoverStatus, RoundType, RoundStatus, ItemStatus,
    SelectionStatus,
)
from app.models.audio_library import AudioLibrary
from app.services.openai_client import OpenAIClient
from app.services.fal_client import FalClient
from app.services.media_downloader import download_file, ensure_directories, MEDIA_BASE_DIR
from app.services.prompts.discover import (
    DISCOVER_IMAGE_WIDE_SYSTEM,
    DISCOVER_IMAGE_NARROW_SYSTEM,
    DISCOVER_IMAGE_REFINED_SYSTEM,
    DISCOVER_VIDEO_SYSTEM,
    DISCOVER_EXTRACTION_SYSTEM,
    DISCOVER_REFINEMENT_SYSTEM,
    DISCOVER_COMPILE_SYSTEM,
    CREATIVE_BLOCKS, TECHNICAL_BLOCKS, ALL_BLOCKS, ALWAYS_RELEVANT, NEGATIVE_SUFFIX,
    build_discover_wide_prompt,
    build_discover_refined_prompt,
    build_discover_narrow_prompt,
    build_discover_video_prompt,
    build_discover_extraction_prompt,
)

import logging

logger = logging.getLogger(__name__)

# Defaults (tunable)
IMAGE_ITEMS_PER_ROUND = 3
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
            image_model=kwargs.get("image_model", "fal-ai/nano-banana-pro"),
            video_model=kwargs.get("video_model", "fal-ai/veo3/fast/image-to-video"),
            image_aspect_ratio=kwargs.get("image_aspect_ratio", "9:16"),
            video_duration=kwargs.get("video_duration", "6s"),
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        logger.info(f"Created discover project {project.id}: {name}")
        return project

    def _get_user_workspace_ids(self, db: Session, user_id: int) -> list[int]:
        """Get all workspace IDs the user is a member of."""
        memberships = db.query(WorkspaceMember).filter(
            WorkspaceMember.user_id == user_id
        ).all()
        return [m.workspace_id for m in memberships]

    async def get_project(
        self, db: Session, project_id: int, user_id: int
    ) -> DiscoverProject:
        """Get project with eager-loaded rounds, items, and extraction."""
        workspace_ids = self._get_user_workspace_ids(db, user_id)
        project = (
            db.query(DiscoverProject)
            .options(
                joinedload(DiscoverProject.rounds)
                .joinedload(DiscoverRound.items),
                joinedload(DiscoverProject.extraction),
                joinedload(DiscoverProject.audio_variants),
            )
            .filter(
                DiscoverProject.id == project_id,
                DiscoverProject.workspace_id.in_(workspace_ids),
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
        """List discover projects visible to user via workspace membership."""
        workspace_ids = self._get_user_workspace_ids(db, user_id)
        query = db.query(DiscoverProject).filter(
            DiscoverProject.workspace_id.in_(workspace_ids),
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

        # Check refinement for image rounds
        if project.stage == DiscoverStage.IMAGES.value:
            refinement = db.query(DiscoverRefinement).filter(
                DiscoverRefinement.project_id == project_id
            ).first()
            if project.current_image_round == 0:
                if not refinement or refinement.score < 80:
                    raise ValueError(
                        "Complete prompt refinement first (score must be 80+)"
                    )
                if not refinement.refined_prompt:
                    raise ValueError("Compile the refined prompt first")

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

        # Use refined_prompt if available, otherwise raw concept
        refinement = db.query(DiscoverRefinement).filter(
            DiscoverRefinement.project_id == project.id
        ).first()
        concept = (
            refinement.refined_prompt
            if refinement and refinement.refined_prompt
            else project.concept
        )

        if round_number == 1 and refinement and refinement.refined_prompt:
            # Refined: variations of the pre-refined prompt
            system_prompt = DISCOVER_IMAGE_REFINED_SYSTEM.format(count=count, aspect_ratio=ar)
            user_prompt = build_discover_refined_prompt(refinement.refined_prompt, count)
        elif round_number == 1:
            # Wide: no refinement, explore broadly
            system_prompt = DISCOVER_IMAGE_WIDE_SYSTEM.format(count=count, aspect_ratio=ar)
            user_prompt = build_discover_wide_prompt(concept, count)
        else:
            # Narrowing: gather selections from previous rounds
            selected, rejected = self._gather_selections(db, project, RoundType.IMAGE.value)
            system_prompt = DISCOVER_IMAGE_NARROW_SYSTEM.format(count=count, aspect_ratio=ar)
            user_prompt = build_discover_narrow_prompt(
                concept, selected, rejected, feedback, count
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
            model_used=project.image_model,
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

        # Get refinement blocks for motion context
        refinement = db.query(DiscoverRefinement).filter(
            DiscoverRefinement.project_id == project.id
        ).first()
        blocks = None
        if refinement and refinement.blocks:
            import json
            blocks = json.loads(refinement.blocks) if isinstance(refinement.blocks, str) else refinement.blocks

        ar = project.image_aspect_ratio

        system_prompt = DISCOVER_VIDEO_SYSTEM.format(count=count, aspect_ratio=ar)

        if round_number == 1:
            user_prompt = build_discover_video_prompt(
                finalist_image.prompt, count,
                direction=feedback,
                blocks=blocks,
            )
        else:
            selected, rejected = self._gather_selections(db, project, RoundType.VIDEO.value)
            user_prompt = build_discover_video_prompt(
                finalist_image.prompt, count, selected, rejected, feedback,
                blocks=blocks,
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

        # Validate labeled format — all required fields present
        REQUIRED_LABELS = ["Subject:", "Motion:", "Camera:", "Continuity:"]
        for i, prompt in enumerate(prompts):
            missing = [lbl for lbl in REQUIRED_LABELS if lbl not in prompt]
            if missing:
                logger.warning(
                    f"Discover {project.id}: video prompt {i+1} missing labels: {missing}. "
                    f"Prompt: {prompt[:100]}..."
                )

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
            model_used=project.video_model,
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
        ).first()
        if not finalist_item:
            raise ValueError("Finalist item not found or not completed")
        # Mark as selected if not already
        if finalist_item.selection != SelectionStatus.SELECTED.value:
            finalist_item.selection = SelectionStatus.SELECTED.value

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
        """Advance from videos (or audio) to extraction stage."""
        project = await self.get_project(db, project_id, user_id)

        if project.stage not in (DiscoverStage.VIDEOS.value, DiscoverStage.AUDIO.value):
            raise ValueError(f"Cannot advance: stage is {project.stage}, expected videos or audio")

        finalist_item = db.query(DiscoverItem).filter(
            DiscoverItem.id == finalist_video_item_id,
            DiscoverItem.status == ItemStatus.COMPLETED.value,
        ).first()
        if not finalist_item:
            raise ValueError("Video finalist item not found or not completed")
        # Mark as selected if not already
        if finalist_item.selection != SelectionStatus.SELECTED.value:
            finalist_item.selection = SelectionStatus.SELECTED.value

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

        # Resolve audio inheritance from Discover → Template
        audio_mode = project.audio_mode or "none"
        audio_source_id = None
        audio_prompt = None
        selected_variant = None

        if audio_mode != "none" and project.selected_audio_variant_id:
            selected_variant = db.query(DiscoverAudioVariant).filter(
                DiscoverAudioVariant.id == project.selected_audio_variant_id,
            ).first()

            if selected_variant:
                audio_prompt = selected_variant.prompt

                if selected_variant.library_item_id:
                    # Music/library — already in library
                    audio_source_id = selected_variant.library_item_id
                elif selected_variant.audio_type == "sound_fx" and selected_variant.file_path:
                    # SFX — store as library item for Template reuse
                    from app.services.audio_library_service import get_audio_library_service
                    lib_service = get_audio_library_service()
                    audio_file = selected_variant.trimmed_file_path or selected_variant.file_path
                    lib_item = await lib_service.add_from_variant(
                        db,
                        workspace_id=project.workspace_id,
                        source_type="sound_fx",
                        file_path=audio_file,
                        file_url=selected_variant.file_url,
                        duration_ms=selected_variant.duration_ms or selected_variant.full_duration_ms or 0,
                        prompt=selected_variant.prompt,
                        source_discover_project_id=project.id,
                        track_path=selected_variant.file_path,
                    )
                    audio_source_id = lib_item.id

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
            audio_mode=audio_mode,
            audio_source_id=audio_source_id,
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
            reference_video_path=project.merged_video_path,
            music_mode="library" if audio_source_id else ("generate" if audio_prompt else "none"),
            music_prompt=audio_prompt,
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
        db.flush()

        # Seed generation from Discover results (goes into moderation queue)
        from app.models.template_generation import TemplateGeneration
        finalist_image = None
        finalist_video = None
        if project.finalist_image_item_id:
            finalist_image = db.query(DiscoverItem).filter(
                DiscoverItem.id == project.finalist_image_item_id,
            ).first()
        if project.finalist_video_item_id:
            finalist_video = db.query(DiscoverItem).filter(
                DiscoverItem.id == project.finalist_video_item_id,
            ).first()

        # Convert absolute merged_video_path to relative for /api/files/ serving
        merged_relative = None
        if project.merged_video_path:
            mp = Path(project.merged_video_path)
            merged_relative = f"{mp.parent.name}/{mp.name}"

        seed_gen = TemplateGeneration(
            project_id=template_project.id,
            video_template_id=vt.id,
            llm_model="gpt-4o-mini",
            image_model=project.image_model,
            video_model=project.video_model,
            image_prompt=finalist_image.prompt if finalist_image else None,
            video_prompt=finalist_video.prompt if finalist_video else None,
            image_url=finalist_image.result_url if finalist_image else None,
            image_path=finalist_image.local_path if finalist_image else None,
            video_url=finalist_video.result_url if finalist_video else None,
            video_path=finalist_video.local_path if finalist_video else None,
            video_with_audio_path=merged_relative,
            status="completed",
            completed_at=datetime.utcnow(),
        )
        db.add(seed_gen)

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

    # ========== Audio Selection ==========

    MAX_AUDIO_VARIANTS = 3

    async def advance_to_audio(
        self, db: Session, project_id: int, user_id: int,
        finalist_video_item_id: int,
    ) -> DiscoverProject:
        """Advance from videos → audio stage. Sets video finalist."""
        project = await self.get_project(db, project_id, user_id)

        if project.stage != DiscoverStage.VIDEOS.value:
            raise ValueError(f"Cannot advance to audio: stage is {project.stage}, expected videos")

        finalist_item = db.query(DiscoverItem).filter(
            DiscoverItem.id == finalist_video_item_id,
            DiscoverItem.status == ItemStatus.COMPLETED.value,
        ).first()
        if not finalist_item:
            raise ValueError("Video finalist item not found or not completed")

        if finalist_item.selection != SelectionStatus.SELECTED.value:
            finalist_item.selection = SelectionStatus.SELECTED.value

        project.stage = DiscoverStage.AUDIO.value
        project.finalist_video_item_id = finalist_video_item_id
        project.updated_at = datetime.utcnow()
        db.commit()

        logger.info(f"Discover {project_id}: advanced to audio, finalist video={finalist_video_item_id}")
        return project

    async def generate_sfx(
        self, db: Session, project_id: int, user_id: int,
        mode: str, prompt: str | None = None,
    ) -> DiscoverAudioVariant:
        """Generate Sound FX via MMAudio V2."""
        project = await self.get_project(db, project_id, user_id)
        if project.stage != DiscoverStage.AUDIO.value:
            raise ValueError(f"Cannot generate SFX: stage is {project.stage}")

        # Check variant limit (completed only)
        completed_count = db.query(DiscoverAudioVariant).filter(
            DiscoverAudioVariant.project_id == project_id,
            DiscoverAudioVariant.audio_type == "sfx",
            DiscoverAudioVariant.status == "completed",
        ).count()
        if completed_count >= self.MAX_AUDIO_VARIANTS:
            raise ValueError(f"Max {self.MAX_AUDIO_VARIANTS} completed SFX variants reached")

        if mode == "manual" and not prompt:
            raise ValueError("Prompt required for manual mode")

        # Get finalist video URL
        finalist_video = db.query(DiscoverItem).filter(
            DiscoverItem.id == project.finalist_video_item_id
        ).first()
        if not finalist_video or not finalist_video.result_url:
            raise ValueError("No finalist video URL available")

        # Create variant
        variant = DiscoverAudioVariant(
            project_id=project_id,
            audio_type="sfx",
            prompt=prompt if mode == "manual" else None,
            prompt_mode=mode,
            status="generating",
        )
        db.add(variant)
        project.audio_mode = "sound_fx"
        db.commit()
        db.refresh(variant)

        # Start background generation
        asyncio.create_task(
            self._generate_sfx_background(project_id, variant.id, finalist_video.result_url, prompt)
        )

        return variant

    async def _generate_sfx_background(
        self, project_id: int, variant_id: int,
        video_url: str, prompt: str | None,
    ):
        """Background: generate SFX via MMAudio V2."""
        from app.db.base import SessionLocal

        db = SessionLocal()
        try:
            audio_url = await self.fal.generate_mmaudio(video_url=video_url, prompt=prompt)

            variant = db.query(DiscoverAudioVariant).filter(
                DiscoverAudioVariant.id == variant_id
            ).first()
            if not variant:
                return

            # Download audio
            local_path = await self._download_discover_audio(audio_url, project_id, variant_id)

            # Get duration
            from app.core.media_processor import media_processor
            duration_s = await media_processor.get_audio_duration(local_path)
            duration_ms = int(duration_s * 1000)

            variant.file_url = audio_url
            variant.file_path = local_path
            variant.full_duration_ms = duration_ms
            variant.duration_ms = duration_ms  # SFX: no hook trim
            variant.status = "completed"
            variant.completed_at = datetime.utcnow()

            db.commit()
            logger.info(f"SFX variant {variant_id} completed: {audio_url}")

        except Exception as e:
            logger.error(f"SFX generation failed for variant {variant_id}: {e}")
            try:
                variant = db.query(DiscoverAudioVariant).filter(
                    DiscoverAudioVariant.id == variant_id
                ).first()
                if variant:
                    variant.status = "failed"
                    variant.error_message = str(e)[:500]
                    db.commit()
            except Exception:
                pass
        finally:
            db.close()

    async def generate_music(
        self, db: Session, project_id: int, user_id: int,
        mode: str, prompt: str | None = None,
    ) -> DiscoverAudioVariant:
        """Generate music via Lyria2."""
        project = await self.get_project(db, project_id, user_id)
        if project.stage != DiscoverStage.AUDIO.value:
            raise ValueError(f"Cannot generate music: stage is {project.stage}")

        completed_count = db.query(DiscoverAudioVariant).filter(
            DiscoverAudioVariant.project_id == project_id,
            DiscoverAudioVariant.audio_type == "music",
            DiscoverAudioVariant.status == "completed",
        ).count()
        if completed_count >= self.MAX_AUDIO_VARIANTS:
            raise ValueError(f"Max {self.MAX_AUDIO_VARIANTS} completed music variants reached")

        if mode == "manual" and not prompt:
            raise ValueError("Prompt required for manual mode")

        # For auto mode, build prompt from context
        auto_prompt = None
        if mode == "auto":
            auto_prompt = await self._build_auto_music_prompt(project)

        variant = DiscoverAudioVariant(
            project_id=project_id,
            audio_type="music",
            prompt=auto_prompt if mode == "auto" else prompt,
            prompt_mode=mode,
            status="generating",
        )
        db.add(variant)
        project.audio_mode = "music"
        db.commit()
        db.refresh(variant)

        final_prompt = auto_prompt if mode == "auto" else prompt
        asyncio.create_task(
            self._generate_music_background(project_id, variant.id, final_prompt)
        )

        return variant

    async def _build_auto_music_prompt(self, project: DiscoverProject) -> str:
        """Build music prompt from project context via GPT."""
        # Get video finalist prompt for context
        video_prompt = ""
        if project.finalist_video_item_id:
            from app.db.base import SessionLocal
            db = SessionLocal()
            try:
                item = db.query(DiscoverItem).filter(
                    DiscoverItem.id == project.finalist_video_item_id
                ).first()
                if item:
                    video_prompt = item.prompt
            finally:
                db.close()

        scene_context = f"Concept: {project.concept}"
        if video_prompt:
            scene_context += f"\nVideo motion: {video_prompt}"

        user_prompt = f"""Create background music for this short viral video:

{scene_context}

Return a single concise music prompt (1-2 sentences) describing the mood, genre, tempo and instruments.
No JSON, just the prompt text."""

        openai = OpenAIClient()
        result = await openai.generate_text(
            prompt=user_prompt,
            system_prompt="You are a music director for short-form viral videos. Write concise music descriptions for AI music generation.",
            temperature=0.8,
        )
        return result.strip() or "Energetic instrumental with driving beat"

    async def _generate_music_background(
        self, project_id: int, variant_id: int, prompt: str,
    ):
        """Background: generate music via Lyria2 + hook detection."""
        from app.db.base import SessionLocal

        db = SessionLocal()
        try:
            audio_url = await self.fal.generate_music(prompt=prompt)

            variant = db.query(DiscoverAudioVariant).filter(
                DiscoverAudioVariant.id == variant_id
            ).first()
            if not variant:
                return

            local_path = await self._download_discover_audio(audio_url, project_id, variant_id)

            from app.core.media_processor import media_processor
            duration_s = await media_processor.get_audio_duration(local_path)
            duration_ms = int(duration_s * 1000)

            variant.file_url = audio_url
            variant.file_path = local_path
            variant.full_duration_ms = duration_ms
            variant.status = "completed"
            variant.completed_at = datetime.utcnow()

            # Run hook detection inline with timeout
            project = db.query(DiscoverProject).filter(
                DiscoverProject.id == project_id
            ).first()
            if project:
                video_duration_s = self._parse_video_duration(project.video_duration)
                await self._detect_hooks(variant, local_path, video_duration_s)

            db.commit()
            logger.info(f"Music variant {variant_id} completed with hooks: {audio_url}")

        except Exception as e:
            logger.error(f"Music generation failed for variant {variant_id}: {e}")
            try:
                variant = db.query(DiscoverAudioVariant).filter(
                    DiscoverAudioVariant.id == variant_id
                ).first()
                if variant:
                    variant.status = "failed"
                    variant.error_message = str(e)[:500]
                    db.commit()
            except Exception:
                pass
        finally:
            db.close()

    async def _detect_hooks(
        self, variant: DiscoverAudioVariant, audio_path: str, video_duration_s: float,
    ):
        """Run HookAnalyzer on audio. 5s timeout, fallback to full track."""
        try:
            from app.core.hook_analyzer import HookAnalyzer

            analyzer = HookAnalyzer()
            hooks = await asyncio.wait_for(
                analyzer.find_hooks(
                    audio_path=audio_path,
                    video=None,
                    num_hooks=4,
                    hook_duration=video_duration_s,
                ),
                timeout=5.0,
            )

            variant.detected_hooks = [
                {
                    "start_ms": int(h.start * 1000),
                    "end_ms": int(h.end * 1000),
                    "energy": h.energy,
                    "type": h.type,
                }
                for h in hooks
            ]
        except (asyncio.TimeoutError, Exception) as e:
            logger.warning(f"Hook detection failed/timed out for variant {variant.id}: {e}")
            variant.detected_hooks = [
                {
                    "start_ms": 0,
                    "end_ms": variant.full_duration_ms or 30000,
                    "energy": "medium",
                    "type": "full",
                }
            ]

    async def select_hook(
        self, db: Session, project_id: int, user_id: int,
        variant_id: int, hook_start_ms: int, hook_end_ms: int,
    ) -> DiscoverAudioVariant:
        """Record hook selection. Audio is trimmed only at confirm time."""
        project = await self.get_project(db, project_id, user_id)
        if project.stage != DiscoverStage.AUDIO.value:
            raise ValueError(f"Cannot select hook: stage is {project.stage}")

        variant = db.query(DiscoverAudioVariant).filter(
            DiscoverAudioVariant.id == variant_id,
            DiscoverAudioVariant.project_id == project_id,
            DiscoverAudioVariant.status == "completed",
        ).first()
        if not variant:
            raise ValueError("Audio variant not found or not completed")

        if hook_end_ms <= hook_start_ms:
            raise ValueError("hook_end_ms must be greater than hook_start_ms")

        variant.hook_start_ms = hook_start_ms
        variant.hook_end_ms = hook_end_ms
        variant.duration_ms = hook_end_ms - hook_start_ms
        db.commit()
        db.refresh(variant)

        logger.info(f"Hook selected for variant {variant_id}: {hook_start_ms}-{hook_end_ms}ms")
        return variant

    async def select_from_library(
        self, db: Session, project_id: int, user_id: int,
        library_item_id: int,
    ) -> DiscoverAudioVariant:
        """Select track from audio library."""
        project = await self.get_project(db, project_id, user_id)
        if project.stage != DiscoverStage.AUDIO.value:
            raise ValueError(f"Cannot select from library: stage is {project.stage}")

        lib_item = db.query(AudioLibrary).filter(
            AudioLibrary.id == library_item_id,
        ).first()
        if not lib_item:
            raise ValueError("Library item not found")

        variant = DiscoverAudioVariant(
            project_id=project_id,
            audio_type="library",
            prompt=lib_item.prompt,
            prompt_mode="manual",
            status="completed",
            file_path=lib_item.file_path,
            file_url=lib_item.file_url,
            full_duration_ms=lib_item.duration_ms,
            library_item_id=library_item_id,
            completed_at=datetime.utcnow(),
        )
        db.add(variant)
        project.audio_mode = "library"

        # Run hook detection if track is longer than video
        video_duration_s = self._parse_video_duration(project.video_duration)
        video_duration_ms = int(video_duration_s * 1000)
        if lib_item.duration_ms > video_duration_ms and lib_item.file_path:
            await self._detect_hooks(variant, lib_item.file_path, video_duration_s)

        db.commit()
        db.refresh(variant)

        logger.info(f"Library item {library_item_id} selected for project {project_id}")
        return variant

    async def confirm_audio(
        self, db: Session, project_id: int, user_id: int,
        variant_id: int,
    ) -> DiscoverProject:
        """Confirm audio selection. Merges video+audio. Advances to extraction."""
        project = await self.get_project(db, project_id, user_id)
        if project.stage != DiscoverStage.AUDIO.value:
            raise ValueError(f"Cannot confirm audio: stage is {project.stage}")

        variant = db.query(DiscoverAudioVariant).filter(
            DiscoverAudioVariant.id == variant_id,
            DiscoverAudioVariant.project_id == project_id,
            DiscoverAudioVariant.status == "completed",
        ).first()
        if not variant:
            raise ValueError("Audio variant not found or not completed")

        # For music/library, require hook selection (unless single full-track)
        if variant.audio_type in ("music", "library") and not variant.hook_start_ms:
            if not variant.detected_hooks or (
                len(variant.detected_hooks) == 1
                and variant.detected_hooks[0].get("type") == "full"
            ):
                variant.duration_ms = variant.full_duration_ms
            else:
                raise ValueError("Select a hook segment before confirming")

        if not variant.file_path:
            raise ValueError("No audio file available for merge")

        # Trim audio if a hook was selected
        from app.core.media_processor import media_processor
        ensure_directories()

        if variant.hook_start_ms is not None and variant.hook_end_ms is not None:
            trimmed_path = str(
                MEDIA_BASE_DIR / "audio" / f"discover_{project_id}_confirmed_{variant_id}.mp3"
            )
            await media_processor.trim_audio(
                audio_path=variant.file_path,
                start=variant.hook_start_ms / 1000.0,
                end=variant.hook_end_ms / 1000.0,
                output_path=trimmed_path,
            )
            variant.trimmed_file_path = trimmed_path
            audio_path = trimmed_path
        else:
            audio_path = variant.file_path

        # Get video file path
        finalist_video = db.query(DiscoverItem).filter(
            DiscoverItem.id == project.finalist_video_item_id,
        ).first()
        if not finalist_video:
            raise ValueError("No finalist video found")

        video_path = finalist_video.local_path
        if not video_path:
            # Download video if not local
            if finalist_video.result_url:
                video_path = await self._download_discover_media(
                    finalist_video.result_url, project_id, 0, 0, "video"
                )
                finalist_video.local_path = video_path
            else:
                raise ValueError("No video file available for merge")

        # Merge video + audio via FFmpeg
        merged_path = str(
            MEDIA_BASE_DIR / "videos" / f"discover_{project_id}_merged.mp4"
        )
        await media_processor.merge_video_audio(
            video_path=str(MEDIA_BASE_DIR / video_path) if not video_path.startswith("/") else video_path,
            audio_path=audio_path if audio_path.startswith("/") else str(MEDIA_BASE_DIR / audio_path),
            output_path=merged_path,
        )

        # Update project
        project.selected_audio_variant_id = variant_id
        project.audio_mode = variant.audio_type
        project.merged_video_path = merged_path
        project.stage = DiscoverStage.EXTRACTION.value
        project.updated_at = datetime.utcnow()

        # Save confirmed audio to library (trimmed version if hook selected)
        if variant.audio_type != "library":
            lib_item = AudioLibrary(
                workspace_id=project.workspace_id,
                source_type=variant.audio_type,
                source_discover_project_id=project_id,
                file_path=audio_path,
                track_path=variant.file_path,  # full original track for re-trimming
                file_url=variant.file_url,
                duration_ms=variant.duration_ms or variant.full_duration_ms or 0,
                prompt=variant.prompt,
            )
            db.add(lib_item)
            db.flush()
            variant.library_item_id = lib_item.id

        # Increment library use count (for library-sourced variants)
        if variant.audio_type == "library" and variant.library_item_id:
            from app.services.audio_library_service import get_audio_library_service
            lib_service = get_audio_library_service()
            await lib_service.increment_use_count(db, variant.library_item_id)

        db.commit()
        logger.info(f"Discover {project_id}: audio confirmed, merged video at {merged_path}")
        return project

    async def skip_audio(
        self, db: Session, project_id: int, user_id: int,
    ) -> DiscoverProject:
        """Skip audio. Advance to extraction with audio_mode='none'."""
        project = await self.get_project(db, project_id, user_id)
        if project.stage != DiscoverStage.AUDIO.value:
            raise ValueError(f"Cannot skip audio: stage is {project.stage}")

        project.audio_mode = "none"
        project.stage = DiscoverStage.EXTRACTION.value
        project.updated_at = datetime.utcnow()
        db.commit()

        logger.info(f"Discover {project_id}: audio skipped, advanced to extraction")
        return project

    async def rollback_from_extraction(
        self, db: Session, project_id: int, user_id: int,
    ) -> DiscoverProject:
        """Rollback from extraction → audio stage. Clears merged video and selection."""
        project = await self.get_project(db, project_id, user_id)
        if project.stage not in (DiscoverStage.EXTRACTION.value, DiscoverStage.COMPLETED.value):
            raise ValueError(f"Cannot rollback to audio: stage is {project.stage}")

        project.stage = DiscoverStage.AUDIO.value
        project.selected_audio_variant_id = None
        project.merged_video_path = None
        project.audio_mode = None
        project.created_project_id = None
        project.status = DiscoverStatus.ACTIVE.value
        project.updated_at = datetime.utcnow()

        # Delete extraction if exists
        if project.extraction:
            db.delete(project.extraction)

        db.commit()
        logger.info(f"Discover {project_id}: rolled back from extraction to audio")
        return project

    async def rollback_from_audio(
        self, db: Session, project_id: int, user_id: int,
    ) -> DiscoverProject:
        """Rollback from audio → videos stage. Deletes all audio variants."""
        project = await self.get_project(db, project_id, user_id)
        if project.stage != DiscoverStage.AUDIO.value:
            raise ValueError(f"Cannot rollback from audio: stage is {project.stage}")

        # Delete all audio variants
        db.query(DiscoverAudioVariant).filter(
            DiscoverAudioVariant.project_id == project_id,
        ).delete()

        project.stage = DiscoverStage.VIDEOS.value
        project.audio_mode = None
        project.selected_audio_variant_id = None
        project.updated_at = datetime.utcnow()
        db.commit()

        logger.info(f"Discover {project_id}: rolled back from audio to videos")
        return project

    async def _download_discover_audio(
        self, url: str, project_id: int, variant_id: int,
    ) -> str:
        """Download audio file to local storage."""
        ensure_directories()
        filename = f"discover_{project_id}_audio_{variant_id}.mp3"
        dest_path = MEDIA_BASE_DIR / "audio" / filename
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        success = await download_file(url, dest_path)
        if not success:
            raise RuntimeError(f"Failed to download audio: {url}")
        return str(dest_path)

    def _parse_video_duration(self, duration_str: str) -> float:
        """Parse video duration string (e.g. '6s') to seconds."""
        try:
            return float(duration_str.rstrip("s"))
        except (ValueError, AttributeError):
            return 6.0

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


    # ========== Prompt Refinement ==========

    async def get_refinement(
        self, db: Session, project_id: int, user_id: int
    ) -> dict | None:
        """Get existing refinement or None."""
        await self.get_project(db, project_id, user_id)
        refinement = db.query(DiscoverRefinement).filter(
            DiscoverRefinement.project_id == project_id
        ).first()
        if not refinement:
            return None
        return self._format_refinement(refinement)

    async def analyze_concept(
        self, db: Session, project_id: int, user_id: int
    ) -> dict:
        """Create refinement: LLM analyzes concept, returns blocks."""
        project = await self.get_project(db, project_id, user_id)

        existing = db.query(DiscoverRefinement).filter(
            DiscoverRefinement.project_id == project_id
        ).first()
        if existing:
            raise ValueError("Refinement already exists. Use GET to fetch it.")

        try:
            result = await self.openai.generate_json(
                prompt=f"USER CONCEPT:\n{project.concept}",
                system_prompt=DISCOVER_REFINEMENT_SYSTEM,
                model="gpt-4o",
                temperature=0.3,
            )
        except Exception as e:
            logger.error(f"LLM analysis failed for project {project_id}: {e}")
            raise RuntimeError("AI service temporarily unavailable. Please try again.")

        blocks = result.get("blocks", {})

        # Validate: relevant_blocks must include ALWAYS_RELEVANT
        relevant = result.get("relevant_blocks", [])
        for block in ALWAYS_RELEVANT:
            if block not in relevant:
                relevant.append(block)

        # Validate: block names must be in ALL_BLOCKS (minus format)
        valid_block_names = [b for b in ALL_BLOCKS if b != "format"]
        blocks = {k: v for k, v in blocks.items() if k in valid_block_names}

        # Format block — auto-confirmed from project settings
        blocks["format"] = {
            "value": f"{project.image_aspect_ratio} vertical"
                     if project.image_aspect_ratio == "9:16"
                     else project.image_aspect_ratio,
            "status": "confirmed",
            "source": "settings",
            "question": None,
            "options": None,
        }
        if "format" not in relevant:
            relevant.append("format")

        refinement = DiscoverRefinement(
            project_id=project_id,
            original_concept=project.concept,
            relevant_blocks=relevant,
            blocks=blocks,
            score=_calculate_score(relevant, blocks),
            analysis_prompt_used=project.concept,
            analysis_response=result,
        )
        db.add(refinement)
        db.commit()
        db.refresh(refinement)

        return self._format_refinement(refinement)

    async def update_block(
        self, db: Session, project_id: int, user_id: int,
        block_name: str, value: str,
    ) -> dict:
        """Update a single block value. Auto-save + recalculate score."""
        await self.get_project(db, project_id, user_id)

        refinement = db.query(DiscoverRefinement).filter(
            DiscoverRefinement.project_id == project_id
        ).first()
        if not refinement:
            raise ValueError("No refinement found. Run analyze first.")

        if block_name not in [b for b in ALL_BLOCKS if b != "format"]:
            raise ValueError(f"Invalid block_name: {block_name}")

        blocks = dict(refinement.blocks)
        blocks[block_name] = {
            "value": value,
            "status": "confirmed",
            "source": "user",
            "question": blocks.get(block_name, {}).get("question"),
            "options": blocks.get(block_name, {}).get("options"),
        }
        refinement.blocks = blocks
        refinement.score = _calculate_score(refinement.relevant_blocks, blocks)
        refinement.refined_prompt = None  # Invalidate compiled prompt
        refinement.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(refinement)

        return self._format_refinement(refinement)

    async def compile_prompt(
        self, db: Session, project_id: int, user_id: int
    ) -> dict:
        """Compile final prompt from blocks. Score >= 80 required."""
        project = await self.get_project(db, project_id, user_id)

        refinement = db.query(DiscoverRefinement).filter(
            DiscoverRefinement.project_id == project_id
        ).first()
        if not refinement:
            raise ValueError("No refinement found. Run analyze first.")
        if refinement.score < 80:
            raise ValueError(f"Score {refinement.score}% too low. Need 80+.")

        blocks_text = "\n".join(
            f"{name}: {block.get('value', '')}"
            for name, block in refinement.blocks.items()
            if block.get("value") and block.get("status") == "confirmed"
        )

        try:
            result = await self.openai.generate_json(
                prompt=f"BLOCKS:\n{blocks_text}\n\nASPECT RATIO: {project.image_aspect_ratio}",
                system_prompt=DISCOVER_COMPILE_SYSTEM,
                model="gpt-4o",
                temperature=0.5,
            )
        except Exception as e:
            logger.error(f"LLM compile failed for project {project_id}: {e}")
            raise RuntimeError("AI service temporarily unavailable. Please try again.")

        compiled = result.get("refined_prompt", "")
        refinement.refined_prompt = f"{compiled} {NEGATIVE_SUFFIX}"
        refinement.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(refinement)

        return self._format_refinement(refinement)

    async def update_refined_prompt(
        self, db: Session, project_id: int, user_id: int,
        refined_prompt: str,
    ) -> dict:
        """User edits the compiled prompt before generation."""
        await self.get_project(db, project_id, user_id)

        refinement = db.query(DiscoverRefinement).filter(
            DiscoverRefinement.project_id == project_id
        ).first()
        if not refinement:
            raise ValueError("No refinement found.")

        refinement.refined_prompt = refined_prompt
        refinement.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(refinement)

        return self._format_refinement(refinement)

    async def delete_refinement(
        self, db: Session, project_id: int, user_id: int
    ) -> None:
        """Delete refinement for re-analysis."""
        await self.get_project(db, project_id, user_id)

        refinement = db.query(DiscoverRefinement).filter(
            DiscoverRefinement.project_id == project_id
        ).first()
        if not refinement:
            raise ValueError("No refinement found.")

        db.delete(refinement)
        db.commit()

    def _format_refinement(self, refinement: DiscoverRefinement) -> dict:
        """Format refinement for API response."""
        return {
            "refinement_id": refinement.id,
            "original_concept": refinement.original_concept,
            "score": refinement.score,
            "relevant_blocks": refinement.relevant_blocks,
            "blocks": refinement.blocks,
            "refined_prompt": refinement.refined_prompt,
            "ready_to_generate": (
                refinement.score >= 80
                and refinement.refined_prompt is not None
            ),
        }


def _calculate_score(relevant_blocks: list[str], blocks: dict) -> int:
    """Score = confirmed blocks / relevant blocks * 100.
    Only 'confirmed' status counts."""
    if not relevant_blocks:
        return 0
    confirmed = sum(
        1 for name in relevant_blocks
        if blocks.get(name, {}).get("status") == "confirmed"
    )
    return int(confirmed / len(relevant_blocks) * 100)


# ========== Singleton ==========

_service: Optional[DiscoverService] = None


def get_discover_service() -> DiscoverService:
    global _service
    if _service is None:
        _service = DiscoverService()
    return _service
