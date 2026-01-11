"""Publishing metadata generation prompts."""

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

Return ONLY valid JSON:
{{
  "{platforms[0]}": {{
    "title": "...",
    "description": "...",
    "hashtags": "#tag1 #tag2 ..."
  }}{', "' + '": {...}, "'.join(platforms[1:]) + '": {...}' if len(platforms) > 1 else ''}
}}
"""
