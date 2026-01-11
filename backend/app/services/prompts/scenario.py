"""Scenario generation prompts."""

import json
from typing import Dict, Any, Optional

SCENARIO_SYSTEM_PROMPT = "Ты режиссёр коротких видео. Создавай плавные, кинематографичные сценарии движения."

PACING_INSTRUCTIONS = {
    "fast": """
ТЕМП: FAST
- Быстрое начало движения с первого кадра
- Динамичные действия субъекта
- camera_movement.speed = "fast" или "medium"
- Много изменений за {duration} секунд
""",
    "medium": """
ТЕМП: MEDIUM
- Плавное начало, нарастание к кульминации
- Сбалансированные движения
- camera_movement.speed = "medium"
""",
    "slow": """
ТЕМП: SLOW
- Очень плавные, cinematic движения
- Минимум резких изменений
- camera_movement.speed = "slow"
- Созерцательная атмосфера
"""
}

TONE_INSTRUCTIONS = {
    "comedic": "ТОН: Комедийный — движения могут быть забавными, неожиданными",
    "dramatic": "ТОН: Драматичный — напряжённые, выразительные движения",
    "wholesome": "ТОН: Душевный — мягкие, тёплые движения",
    "absurd": "ТОН: Абсурдный — странные, сюрреалистичные движения",
    "suspenseful": "ТОН: Интрига — медленные, напряжённые движения с недосказанностью",
    "inspiring": "ТОН: Вдохновляющий — эпичные, размашистые движения"
}


def build_scenario_prompt(
    description_data: Dict[str, Any],
    story_data: Optional[Dict[str, Any]] = None,
    duration: int = 5
) -> str:
    """Build scenario generation prompt."""
    # Story context
    story_context = ""
    pacing_instr = ""
    tone_instr = ""

    if story_data:
        story_context = f"""
СЮЖЕТ:
- Концепция: {story_data.get('concept', 'N/A')}
- Hook: {story_data.get('hook', 'N/A')}
- Кульминация: {story_data.get('climax', 'N/A')}
- Эмоция: {story_data.get('emotional_trigger', 'N/A')}
"""
        pacing = story_data.get('pacing', 'medium')
        pacing_instr = PACING_INSTRUCTIONS.get(pacing, "").format(duration=duration)

        tone = story_data.get('tone', 'comedic')
        tone_instr = TONE_INSTRUCTIONS.get(tone, "")

    # Extract from description_data
    scene_summary = description_data.get('scene_summary', '')
    main_subject = description_data.get('main_subject', {})
    environment = description_data.get('environment', {})

    return f"""
Создай ДЕТАЛЬНЫЙ сценарий ДВИЖЕНИЯ для {duration}-секундного видео.

{story_context}
{tone_instr}
{pacing_instr}

ОПИСАНИЕ СЦЕНЫ:
{scene_summary}

ГЛАВНЫЙ ОБЪЕКТ:
{json.dumps(main_subject, ensure_ascii=False, indent=2) if main_subject else 'Не указан'}

ОКРУЖЕНИЕ:
{json.dumps(environment, ensure_ascii=False, indent=2) if environment else 'Не указано'}

ЗАДАЧА: Создай покадровый сценарий движения от hook к climax.

КРИТИЧНО для key_moments:
- Каждое ОТДЕЛЬНОЕ действие = отдельный момент с точным таймингом
- Минимум 4-6 моментов для {duration}s видео
- Тайминг с точностью до 0.5s (например: "0.0-0.8s", "0.8-1.5s")
- НЕ объединяй несколько действий в один момент
- Каждый action описывает ОДНО конкретное движение/изменение

Пример хорошей разбивки для 5s:
- "0.0-0.5s": "собака поворачивает голову влево"
- "0.5-1.2s": "замечает свой хвост, уши поднимаются"
- "1.2-2.0s": "начинает кружиться, пытаясь поймать"
- "2.0-3.0s": "ускоряется, хвост мелькает"
- "3.0-4.0s": "теряет равновесие"
- "4.0-5.0s": "падает на спину, лапы в воздухе"

Верни JSON:
{{
  "motion_prompt": "краткий промпт движения на английском для KLING (общее описание что происходит)",
  "camera_movement": {{
    "type": "static" | "pan_left" | "pan_right" | "zoom_in" | "zoom_out" | "tilt_up" | "tilt_down",
    "speed": "slow" | "medium" | "fast",
    "description": "описание движения камеры"
  }},
  "subject_action": "общее описание что делает субъект",
  "atmosphere_change": "как меняется атмосфера — или null",
  "key_moments": [
    {{"timestamp": "0.0-0.5s", "action": "первое микро-действие"}},
    {{"timestamp": "0.5-1.2s", "action": "второе микро-действие"}},
    ... // минимум 4-6 моментов
  ]
}}

ВАЖНО:
- motion_prompt на английском, краткий
- key_moments — ДЕТАЛЬНАЯ покадровая раскадровка
- Каждый момент = одно атомарное действие
- Движения плавные и реалистичные для image-to-video
"""


def format_content_variables(content_variables: Dict[str, Any]) -> str:
    """Format content variables into readable text."""
    if not content_variables:
        return "Не указаны"

    lines = []
    for key, value in content_variables.items():
        if isinstance(value, dict):
            details = ", ".join(f"{k}: {v}" for k, v in value.items() if v)
            lines.append(f"- {key}: {details}")
        else:
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def build_scenario_from_template_prompt(
    story_template: str,
    content_variables: Dict[str, Any],
    duration: int = 5,
    aspect_ratio: str = "9:16",
    feedback: Optional[str] = None,
    previous_scenario: Optional[Dict[str, Any]] = None
) -> str:
    """
    Build scenario prompt from story_template + content_variables.

    This is the NEW Discover workflow - generates scenario with image_prompt directly.

    Args:
        story_template: The concept/idea for the video
        content_variables: Hard constraints (actor, vehicle, location, etc.)
        duration: Video duration in seconds
        aspect_ratio: Video aspect ratio
        feedback: Optional user feedback for regeneration
        previous_scenario: Previous scenario to improve upon
    """
    variables_text = format_content_variables(content_variables)

    # Map aspect ratio to orientation description
    orientation_map = {
        "9:16": "vertical 9:16 (portrait, mobile-first)",
        "16:9": "horizontal 16:9 (landscape, widescreen)",
        "1:1": "square 1:1",
    }
    orientation = orientation_map.get(aspect_ratio, f"{aspect_ratio}")

    prompt = f"""
Ты режиссёр коротких вирусных видео. Создай ПОЛНЫЙ сценарий для {duration}-секундного видео.

КОНЦЕПЦИЯ ВИДЕО:
{story_template}

ВЫБРАННЫЙ ВАРИАНТ (ОБЯЗАТЕЛЬНО использовать эти детали БЕЗ ИЗМЕНЕНИЙ):
{variables_text}

КРИТИЧЕСКИ ВАЖНО:
- Используй ТОЛЬКО детали из выбранного варианта
- НЕ ЗАМЕНЯЙ персонажа, объекты, локацию на другие
- Если указан "Ford Mustang" - это Ford Mustang, НЕ Ferrari
- Если указаны "горы" - это горы, НЕ Париж
- Все элементы из content_variables должны быть в image_prompt

Задача: Создай сценарий включающий:
1. image_prompt - детальное описание ПЕРВОГО КАДРА для генерации изображения
2. motion_prompt - как будет двигаться субъект
3. camera_movement - как будет двигаться камера

Верни JSON:
{{
  "image_prompt": "Детальный промпт на АНГЛИЙСКОМ для генерации изображения первого кадра.
                  Включает: субъект (внешность, поза, одежда), объекты, локацию, освещение, стиль.
                  ОБЯЗАТЕЛЬНО включи все детали из выбранного варианта!
                  Формат: cinematic, {orientation}, high quality",

  "negative_prompt": "что НЕ должно быть на изображении (на английском)",

  "motion_prompt": "краткое описание движения на АНГЛИЙСКОМ для KLING (1-2 предложения)",

  "camera_movement": {{
    "type": "static" | "pan_left" | "pan_right" | "zoom_in" | "zoom_out" | "dolly_in" | "dolly_out",
    "speed": "slow" | "medium" | "fast",
    "description": "описание движения камеры на русском"
  }},

  "subject_action": "что делает субъект (на русском)",

  "key_moments": [
    {{"timestamp": "0.0-1.0s", "action": "описание действия"}},
    {{"timestamp": "1.0-2.5s", "action": "описание действия"}},
    {{"timestamp": "2.5-{duration}s", "action": "описание действия"}}
  ]
}}

ВАЖНО для image_prompt:
- На АНГЛИЙСКОМ языке
- Детальное описание: кто, что, где, как освещено, какой стиль
- Включи ВСЕ детали из выбранного варианта
- Формат: {orientation}
- Кинематографичное качество
"""

    # Add feedback section if regenerating with feedback
    if feedback and previous_scenario:
        import json
        feedback_section = f"""

ДОРАБОТКА:
Предыдущий сценарий:
{json.dumps(previous_scenario, ensure_ascii=False, indent=2)}

ФИДБЕК ПОЛЬЗОВАТЕЛЯ (обязательно учесть):
{feedback}

Создай УЛУЧШЕННЫЙ сценарий с учётом фидбека. Сохрани структуру JSON.
"""
        return prompt + feedback_section

    return prompt
