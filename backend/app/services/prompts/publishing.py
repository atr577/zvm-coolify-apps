"""Publishing metadata generation prompts.

Two modes:
1. Default (no custom prompts): build_publishing_meta_prompt() — single call, all metadata at once
2. Custom (user prompts set): build_custom_*_prompt() — per-type calls with envelope
"""

from typing import List, Dict, Any, Optional
import json


# Platform-specific limits and styles
PLATFORM_SPECS = {
    "instagram": {
        "max_hashtags": 30,
        "title_max": 100,
        "description_max": 2200,
        "style": "engaging, emoji-friendly, trendy"
    },
    "tiktok": {
        "max_hashtags": 7,
        "title_max": 100,
        "description_max": 300,
        "style": "short, punchy, Gen-Z friendly, use trending phrases"
    },
    "youtube": {
        "max_hashtags": 15,
        "title_max": 100,
        "description_max": 500,
        "style": "SEO-friendly, clear, professional"
    }
}


def build_publishing_meta_prompt(
    prompt_or_template: str,
    platforms: List[str],
    scenario_data: Optional[Dict[str, Any]] = None
) -> str:
    """Build publishing metadata generation prompt.

    Args:
        prompt_or_template: Fallback text (story_template or image_prompt)
        platforms: List of platforms to generate for
        scenario_data: Full scenario data with story_template and content_variables
    """
    # Build context from scenario_data if available
    if scenario_data:
        context_parts = []
        if scenario_data.get("story_template"):
            context_parts.append(f"Story concept: {scenario_data['story_template']}")
        if scenario_data.get("content_variables"):
            vars_str = json.dumps(scenario_data["content_variables"], ensure_ascii=False)
            context_parts.append(f"Content details: {vars_str}")
        if scenario_data.get("image_prompt"):
            context_parts.append(f"Visual: {scenario_data['image_prompt'][:300]}")
        context = "\n".join(context_parts)
    else:
        context = prompt_or_template[:1000]

    # Build platform requirements
    platform_reqs = []
    for p in platforms:
        spec = PLATFORM_SPECS.get(p, PLATFORM_SPECS["instagram"])
        platform_reqs.append(f"""
"{p}":
  - title: {spec['title_max']} chars max, style: {spec['style']}
  - description: {spec['description_max']} chars max, include CTA, NO hashtags here
  - hashtags: up to {spec['max_hashtags']} hashtags, space-separated""")

    return f"""Create viral publishing metadata for a short video.

VIDEO CONTEXT:
{context}

REQUIREMENTS PER PLATFORM:
{''.join(platform_reqs)}

RULES:
- Write in the language appropriate for viral content (usually English)
- Titles should hook attention immediately
- Descriptions should have a call-to-action (follow, like, comment)
- Hashtags should mix popular and niche tags

Return ONLY a FLAT JSON object with platform names as top-level keys.
Do NOT wrap in any parent key like "platforms", "data", or "result".

EXACT FORMAT:
{{
  "{platforms[0]}": {{
    "title": "...",
    "description": "...",
    "hashtags": "#tag1 #tag2 ..."
  }}{', "' + '": {...}, "'.join(platforms[1:]) + '": {...}' if len(platforms) > 1 else ''}
}}
"""


# --- Custom envelope builders (per-type calls) ---

def _build_video_context(scenario_data: Optional[Dict[str, Any]]) -> str:
    """Extract video context from scenario_data for envelope."""
    if not scenario_data:
        return "No context available"
    parts = []
    if scenario_data.get("preprocessing_result"):
        pr = scenario_data["preprocessing_result"]
        if isinstance(pr, dict):
            pr = json.dumps(pr, ensure_ascii=False)
        parts.append(f"Content: {str(pr)[:500]}")
    if scenario_data.get("image_prompt"):
        parts.append(f"Visual: {scenario_data['image_prompt'][:300]}")
    if scenario_data.get("video_prompt"):
        parts.append(f"Motion: {scenario_data['video_prompt'][:200]}")
    return "\n".join(parts) or "No context available"


_SPEC_FIELD_MAP = {
    "title": lambda spec: f"max {spec['title_max']} chars, style: {spec['style']}",
    "description": lambda spec: f"max {spec['description_max']} chars, include CTA",
    "hashtags": lambda spec: f"up to {spec['max_hashtags']} hashtags, space-separated",
}


def _build_platform_reqs(platforms: List[str], meta_type: str) -> str:
    """Build platform requirements for a specific metadata type."""
    fmt = _SPEC_FIELD_MAP.get(meta_type)
    if not fmt:
        return ""
    lines = []
    for p in platforms:
        spec = PLATFORM_SPECS.get(p, PLATFORM_SPECS["instagram"])
        lines.append(f'  "{p}": {fmt(spec)}')
    return "\n".join(lines)


def _build_custom_envelope(
    user_prompt: str,
    platforms: List[str],
    scenario_data: Optional[Dict[str, Any]],
    meta_type: str,
    response_format_example: str,
) -> str:
    """Build envelope prompt for a specific metadata type."""
    return f"""USER INSTRUCTIONS:
{user_prompt}

VIDEO CONTEXT:
{_build_video_context(scenario_data)}

PLATFORM REQUIREMENTS:
{_build_platform_reqs(platforms, meta_type)}

RESPONSE FORMAT (return ONLY this JSON, nothing else):
{response_format_example}"""


def build_custom_title_prompt(
    user_prompt: str, platforms: List[str], scenario_data: Optional[Dict[str, Any]]
) -> str:
    example = json.dumps({p: "title text here" for p in platforms})
    return _build_custom_envelope(user_prompt, platforms, scenario_data, "title", example)


def build_custom_description_prompt(
    user_prompt: str, platforms: List[str], scenario_data: Optional[Dict[str, Any]]
) -> str:
    example = json.dumps({p: "description text here" for p in platforms})
    return _build_custom_envelope(user_prompt, platforms, scenario_data, "description", example)


def build_custom_hashtags_prompt(
    user_prompt: str, platforms: List[str], scenario_data: Optional[Dict[str, Any]]
) -> str:
    example = json.dumps({p: "#tag1 #tag2 #tag3" for p in platforms})
    return _build_custom_envelope(user_prompt, platforms, scenario_data, "hashtags", example)
