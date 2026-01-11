"""
PREPARE phase for Remix workflow.
Fills templates with content variables before generation steps.
"""
from typing import Dict, Any, Optional, Union
from app.models.project import Project
from app.models.video import Video


def prepare_remix(
    project: Project,
    video: Video,
    batch_index: Optional[int] = None
) -> None:
    """
    Fill templates for Remix steps (IMAGE, VIDEO).
    Modifies video in-place.

    Args:
        project: Remix project with templates and placeholders
        video: Video to prepare
        batch_index: Optional index for batch generation (round-robin variable selection)
    """
    variables = dict(video.content_variables or {})

    # Get placeholders from project (default to empty list)
    placeholders = project.placeholders or []
    suggestions = project.placeholder_suggestions or {}

    # Auto-fill missing variables from suggestions
    missing = set(placeholders) - set(variables.keys())
    for placeholder in missing:
        placeholder_suggestions = suggestions.get(placeholder, [])

        if batch_index is not None and placeholder_suggestions:
            # Batch mode: round-robin for even coverage
            variables[placeholder] = placeholder_suggestions[batch_index % len(placeholder_suggestions)]
        elif placeholder_suggestions:
            # Single mode: use first suggestion
            variables[placeholder] = placeholder_suggestions[0]
        else:
            raise ValueError(f"No suggestion for placeholder: {placeholder}")

    # Save auto-filled variables
    video.content_variables = variables

    # Fill prompt template (story_template is used as image prompt template for remix)
    if project.story_template:
        video.image_prompt = fill_template(project.story_template, variables)
        video.prompt_data = {"main_prompt": video.image_prompt}

    # Fill scenario template or use default
    if project.scenario_template:
        video.scenario_data = fill_template(project.scenario_template, variables)
    else:
        # Default motion for remix without explicit scenario
        video.scenario_data = {"motion_prompt": "Subtle natural movement, cinematic atmosphere"}

    # Store filled template in story_data for reference
    video.story_data = {"filled_template": video.image_prompt}


def fill_template(template: Union[str, dict, list], variables: Dict[str, Any]) -> Union[str, dict, list]:
    """
    Replace {placeholders} with values recursively.

    Args:
        template: String, dict, or list with {placeholder} markers
        variables: Dict of placeholder -> value mappings

    Returns:
        Template with placeholders replaced
    """
    if isinstance(template, str):
        result = template
        for key, value in variables.items():
            # Handle dict values by converting to string representation
            if isinstance(value, dict):
                value_str = ", ".join(f"{k}: {v}" for k, v in value.items())
            else:
                value_str = str(value)
            result = result.replace(f"{{{key}}}", value_str)
        return result
    elif isinstance(template, dict):
        return {k: fill_template(v, variables) for k, v in template.items()}
    elif isinstance(template, list):
        return [fill_template(item, variables) for item in template]
    return template


def validate_remix_project(project: Project) -> None:
    """
    Validate that a remix project has all required fields.

    Raises:
        ValueError: If validation fails
    """
    if project.project_type != "remix":
        raise ValueError("Project is not a remix project")

    if not project.story_template:
        raise ValueError("Remix project must have a story_template (prompt template)")

    placeholders = project.placeholders or []
    suggestions = project.placeholder_suggestions or {}

    # Check all placeholders have suggestions
    missing_suggestions = set(placeholders) - set(suggestions.keys())
    if missing_suggestions:
        raise ValueError(f"Missing suggestions for placeholders: {missing_suggestions}")

    # Check no empty suggestions
    empty_suggestions = [p for p in placeholders if not suggestions.get(p)]
    if empty_suggestions:
        raise ValueError(f"Empty suggestions for placeholders: {empty_suggestions}")
