"""
Workflow steps - media generation functions.

Each step is a simple async function: generate(video) -> Dict[str, Any]
Orchestrator saves results to StepHistory.
"""
from app.services.workflow.steps import image
from app.services.workflow.steps import video
from app.services.workflow.steps import audio

__all__ = [
    "image",
    "video",
    "audio",
]
