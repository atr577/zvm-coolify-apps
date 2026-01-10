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
