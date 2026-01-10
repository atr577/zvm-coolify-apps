"""Platform adaptation prompts."""

from typing import Dict, Any, List

ADAPTATION_SYSTEM_PROMPT = "Ты SMM-эксперт по всем социальным платформам."

TONE_STYLES = {
    "comedic": "весёлый, с юмором, эмодзи",
    "dramatic": "серьёзный, эмоциональный",
    "wholesome": "тёплый, душевный, милый",
    "absurd": "странный, мемный, ироничный",
    "suspenseful": "интригующий, загадочный",
    "inspiring": "мотивирующий, вдохновляющий"
}


def build_adaptation_prompt(
    content_data: Dict[str, Any],
    platforms: List[str]
) -> str:
    """Build platform adaptation prompt."""
    story = content_data.get("story", {})
    scenario = content_data.get("scenario", {})

    tone = story.get('tone', 'comedic')
    tone_style = TONE_STYLES.get(tone, "нейтральный")

    return f"""
Адаптируй контент для платформ: {', '.join(platforms)}

СЮЖЕТ ВИДЕО:
- Концепция: {story.get('concept', 'N/A')}
- Hook (зацепка): {story.get('hook', 'N/A')}
- Кульминация: {story.get('climax', 'N/A')}
- Тон: {tone} ({tone_style})
- Эмоция: {story.get('emotional_trigger', 'N/A')}

СЦЕНАРИЙ:
- Действие: {scenario.get('subject_action', 'N/A')}

Создай оптимизированные версии для каждой платформы.

ПРАВИЛА:
1. Title должен использовать hook — это первое что видит зритель
2. Description раскрывает climax (но не спойлерит!)
3. Стиль текста соответствует tone: {tone_style}
4. Хештеги релевантные эмоции ({story.get('emotional_trigger', 'N/A')})

ВАЖНО: Верни ТОЛЬКО JSON объект с платформами напрямую, БЕЗ обёртки.

Пример (если запрошены instagram и youtube):
{{
  "instagram": {{
    "title": "Когда твоя собака умнее тебя 🐕",
    "description": "Этот пёс точно знает что делает...",
    "hashtags": "#собака #пёс #смешныеживотные #reels"
  }},
  "youtube": {{
    "title": "Собака устроила хаос на кухне",
    "description": "Посмотрите что натворил этот милый пёс! #Shorts",
    "tags": "собака, смешные животные, shorts"
  }}
}}

Включай ТОЛЬКО: {', '.join(platforms)}
"""
