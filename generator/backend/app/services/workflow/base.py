"""
BaseWorkflowStep - Abstract base class for all workflow steps.

Extracts common logic:
- Step creation/retrieval
- Prompt handling (project system_prompts, user custom_prompt)
- Content saving
- Validation
- Error handling
- Response building
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional, TYPE_CHECKING
from sqlalchemy.orm import Session

from app.models.video import Video, StepType, WorkflowStatus
from app.models.workflow_step import WorkflowStep
from app.models.validation_result import ValidationResult, ValidationStatus
from app.services.openai_service import openai_service
from app.services.prompt_builders import PromptData
from app.schemas.workflow import CustomPrompt

if TYPE_CHECKING:
    from app.models.project import Project


class BaseWorkflowStep(ABC):
    """
    Abstract base class for workflow steps.

    Each step must define:
    - step_type: StepType enum value
    - step_name: string name for system_prompts lookup (e.g., "story", "description")
    - content_field: field name on Video model to save content
    - requires_validation: whether AI validation is needed (default True)

    And implement:
    - build_prompt(): builds the PromptData for this step
    - generate(): performs the actual generation
    """

    step_type: StepType
    step_name: str  # For system_prompts lookup
    content_field: str
    requires_validation: bool = True

    def __init__(self, db: Session, video: Video):
        self.db = db
        self.video = video
        self.project: Optional["Project"] = video.project
        self.step: Optional[WorkflowStep] = None

        # Get project's system_prompts
        self.project_prompts: Dict[str, str] = {}
        if self.project and self.project.system_prompts:
            self.project_prompts = self.project.system_prompts

    async def execute(
        self,
        request: Any,
        custom_prompt: Optional[CustomPrompt] = None
    ) -> Dict[str, Any]:
        """
        Main execution flow for a workflow step.

        1. Get or create step
        2. Build prompt with project's system_prompt
        3. Get effective prompt (user custom > project > default)
        4. Save prompt tracking data
        5. Generate content
        6. Save content to video
        7. Validate (if required)
        8. Return response
        """
        # 1. Get or create step
        self.step = self._get_or_create_step()

        # 2. Build original prompt for tracking
        original_prompt_data = self.build_prompt(request)

        # 3. Get effective prompt
        effective_prompt = self._get_effective_prompt(original_prompt_data, custom_prompt)

        # 4. Save prompt tracking data
        self._save_prompt_tracking(original_prompt_data, custom_prompt)

        try:
            # 5. Generate content
            content = await self.generate(request, effective_prompt)

            # 6. Save content
            self._save_content(content)

            # 7. Validate if required
            validation = None
            previous_data = self._get_previous_data(request)

            if self.requires_validation:
                validation = await self._validate(content, previous_data)
            else:
                self.step.status = WorkflowStatus.AWAITING_APPROVAL
                self.step.completed_at = datetime.utcnow()
                self.db.commit()

            # 8. Build and return response
            return self._build_response(content, validation)

        except Exception as e:
            self._handle_failure(e)
            raise

    @abstractmethod
    def build_prompt(self, request: Any) -> PromptData:
        """
        Build the PromptData for this step.
        Should use self.project_prompts.get(self.step_name) for system_prompt.
        """
        pass

    @abstractmethod
    async def generate(self, request: Any, prompt: CustomPrompt) -> Dict[str, Any]:
        """
        Perform the actual content generation.
        Returns the generated content dict.
        """
        pass

    def _get_previous_data(self, request: Any) -> Optional[Dict[str, Any]]:
        """
        Get previous step data for validation context.
        Override in subclasses that need it.
        """
        return None

    def _get_or_create_step(self) -> WorkflowStep:
        """Get existing PENDING step or create a new one."""
        step = self.db.query(WorkflowStep).filter(
            WorkflowStep.video_id == self.video.id,
            WorkflowStep.step_type == self.step_type,
            WorkflowStep.status == WorkflowStatus.PENDING
        ).first()

        if step:
            step.status = WorkflowStatus.IN_PROGRESS
            step.started_at = datetime.utcnow()
        else:
            step = WorkflowStep(
                video_id=self.video.id,
                step_type=self.step_type,
                status=WorkflowStatus.IN_PROGRESS,
                started_at=datetime.utcnow()
            )
            self.db.add(step)

        self.db.commit()
        self.db.refresh(step)
        return step

    def _get_effective_prompt(
        self,
        prompt_data: PromptData,
        user_custom_prompt: Optional[CustomPrompt] = None
    ) -> CustomPrompt:
        """
        Get the effective prompt to use for generation.
        Priority: user_custom_prompt > project.system_prompts > default
        """
        if user_custom_prompt:
            return user_custom_prompt

        system_prompt = prompt_data.system_prompt

        if self.project_prompts:
            project_system_prompt = self.project_prompts.get(self.step_name)
            if project_system_prompt:
                system_prompt = project_system_prompt

        return CustomPrompt(
            system_prompt=system_prompt,
            user_prompt=prompt_data.user_prompt
        )

    def _save_prompt_tracking(
        self,
        original_prompt_data: PromptData,
        custom_prompt: Optional[CustomPrompt]
    ):
        """Save prompt tracking data to step."""
        self.step.original_prompt = original_prompt_data.to_dict()

        if custom_prompt:
            self.step.custom_prompt = {
                "system_prompt": custom_prompt.system_prompt,
                "user_prompt": custom_prompt.user_prompt
            }
            self.step.prompt_manually_edited = True
        else:
            self.step.prompt_manually_edited = False

    def _save_content(self, content: Dict[str, Any]):
        """Save generated content to step and video."""
        self.step.content = content
        setattr(self.video, self.content_field, content)
        self.video.current_step = self.step_type
        self.video.status = WorkflowStatus.IN_PROGRESS

    async def _validate(
        self,
        content: Dict[str, Any],
        previous_data: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """Validate content and save validation result."""
        validation_result_data = await openai_service.validate_content(
            content=content,
            step_type=self.step_name,
            previous_data=previous_data
        )

        validation = ValidationResult(
            step_id=self.step.id,
            status=ValidationStatus(validation_result_data["status"]),
            score=validation_result_data.get("score"),
            criteria_results=validation_result_data.get("criteria_results"),
            warnings=validation_result_data.get("warnings"),
            errors=validation_result_data.get("errors"),
            recommendations=validation_result_data.get("recommendations")
        )
        self.db.add(validation)

        # Update step status based on validation
        if validation_result_data["status"] == "fail":
            self.step.validation_attempts += 1
            if self.step.validation_attempts >= self.step.max_validation_attempts:
                self.step.status = WorkflowStatus.VALIDATION_FAILED
            else:
                self.step.status = WorkflowStatus.VALIDATING
        else:
            self.step.status = WorkflowStatus.AWAITING_APPROVAL

        self.step.completed_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(self.step)

        return validation

    def _build_response(
        self,
        content: Dict[str, Any],
        validation: Optional[ValidationResult]
    ) -> Dict[str, Any]:
        """Build the response dict."""
        response = {
            "step_id": self.step.id,
            "content": content,
            "prompt_manually_edited": self.step.prompt_manually_edited
        }

        if validation:
            response["validation"] = {
                "status": validation.status.value,
                "score": validation.score,
                "warnings": validation.warnings,
                "errors": validation.errors,
                "recommendations": validation.recommendations
            }

        return response

    def _handle_failure(self, error: Exception):
        """Handle step failure."""
        self.step.status = WorkflowStatus.FAILED
        self.step.completed_at = datetime.utcnow()
        self.db.commit()
