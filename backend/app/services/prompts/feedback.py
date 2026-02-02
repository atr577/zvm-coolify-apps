"""Feedback-based prompt modification prompts."""

from typing import Optional


FEEDBACK_SYSTEM_PROMPT = "Ты эксперт по AI-генерации изображений и видео. Модифицируй промпты на основе фидбэка пользователя."


def build_feedback_modification_prompt(
    original_image_prompt: str,
    original_video_prompt: Optional[str],
    feedback: str
) -> str:
    """Build prompt for modifying generation prompts based on user feedback."""

    video_section = ""
    if original_video_prompt:
        video_section = f"""
ИСХОДНЫЙ VIDEO PROMPT:
{original_video_prompt}
"""

    return f"""
Пользователь хочет перегенерировать контент с изменениями.

ИСХОДНЫЙ IMAGE PROMPT:
{original_image_prompt}
{video_section}
ФИДБЭК ПОЛЬЗОВАТЕЛЯ (что изменить):
{feedback}

Твоя задача: модифицировать промпты с учётом фидбэка, сохраняя основную концепцию.

ПРАВИЛА:
1. Сохрани структуру и стиль исходного промпта
2. Внеси изменения согласно фидбэку
3. Если фидбэк противоречит исходному промпту — приоритет у фидбэка
4. Промпты должны быть на АНГЛИЙСКОМ языке
5. Если video_prompt не был указан — создай его на основе image_prompt

Верни JSON:
{{
  "image_prompt": "модифицированный промпт для изображения (50-150 слов)",
  "video_prompt": "модифицированный промпт для видео (краткое описание движения, 20-50 слов)",
  "changes_summary": "краткое описание внесённых изменений на русском"
}}
"""
