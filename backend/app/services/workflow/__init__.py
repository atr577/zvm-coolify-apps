"""
Workflow service - orchestrates 4-step video generation.

SCENARIO → IMAGE → VIDEO → AUDIO

Unified for both Discover and Remix projects.
"""
from app.services.workflow.orchestrator import (
    run_auto,
    generate_step,
    select_variant,
    get_step_history,
    WORKFLOW_STEPS,
    DEFAULT_VARIANTS,
)
from app.services.workflow.strategies import get_strategy, BaseStrategy
from app.services.workflow.prompt_preview import PromptPreviewBuilder

__all__ = [
    # Orchestrator functions
    "run_auto",
    "generate_step",
    "select_variant",
    "get_step_history",
    "WORKFLOW_STEPS",
    "DEFAULT_VARIANTS",
    # Strategy
    "get_strategy",
    "BaseStrategy",
    # Preview
    "PromptPreviewBuilder",
]
