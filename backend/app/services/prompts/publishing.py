"""Publishing metadata generation prompts."""

from typing import List


def build_publishing_meta_prompt(
    prompt_or_template: str,
    platforms: List[str]
) -> str:
    """Build publishing metadata generation prompt."""
    return f"""
Create publishing metadata for video on platforms: {', '.join(platforms)}

VIDEO CONTEXT (generation prompt):
{prompt_or_template[:1000]}

For each platform create:
- title: short catchy title (up to 100 chars)
- description: description with CTA (up to 500 chars). DO NOT include hashtags here!
- hashtags: relevant hashtags separated by space (ONLY here, not in description)

Return ONLY JSON:
{{
  "{platforms[0]}": {{
    "title": "...",
    "description": "...",
    "hashtags": "#tag1 #tag2 #tag3"
  }}
}}

Platforms: {', '.join(platforms)}
"""
