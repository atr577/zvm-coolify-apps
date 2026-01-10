"""Story generation prompts."""

from typing import Dict, Any, List, Optional

STORY_SYSTEM_PROMPT = "Ты эксперт по созданию вирального видео-контента."


def build_story_prompt(
    theme: str = None,
    target_audience: str = None,
    mood: str = None,
    key_elements: str = None,
    duration: int = 5,
    platforms: List[str] = None,
    additional_notes: str = None,
    content_variables: Dict[str, Any] = None
) -> str:
    """Build story generation prompt from parameters."""
    # Build context from parameters
    context_parts = []
    if theme:
        context_parts.append(f"Тема/ниша: {theme}")
    if target_audience:
        context_parts.append(f"Целевая аудитория: {target_audience}")
    if mood:
        context_parts.append(f"Настроение/стиль: {mood}")
    if key_elements:
        context_parts.append(f"Обязательные элементы: {key_elements}")
    if platforms:
        context_parts.append(f"Целевые платформы: {', '.join(platforms)}")
    context_parts.append(f"Длительность видео: {duration} секунд")

    context = "\n".join(context_parts) if context_parts else "Без специфических требований"

    # Build content_variables section
    content_context = ""
    if content_variables:
        content_context = "\n\nКОНТЕНТ ВИДЕО (ОБЯЗАТЕЛЬНО использовать):\n"
        for key, value in content_variables.items():
            if isinstance(value, dict):
                content_context += f"\n{key.upper()}:\n"
                for k, v in value.items():
                    content_context += f"  - {k}: {v}\n"
            else:
                content_context += f"- {key}: {value}\n"

    return f"""
Сгенерируй идею для вирального короткого видео (Instagram Reels/TikTok/YouTube Shorts).

ВВОДНЫЕ ПАРАМЕТРЫ:
{context}
{content_context}
{f"Дополнительные указания: {additional_notes}" if additional_notes else ""}

Верни результат в формате JSON с такими полями:

- concept: концепция видео (2-3 предложения) - что происходит в кадре
- hook: захватывающий hook для первых 3 секунд - что зацепит зрителя
- hook_type: тип хука - "visual" | "text" | "audio"
  - visual: сама картинка цепляет (драма, красота, шок)
  - text: текст на экране цепляет (вопрос, список, интрига)
  - audio: звук/голос цепляет (voiceover, мем-саунд, музыка)
- climax: кульминация/развязка - чем заканчивается видео, какой payoff
- tone: тон видео - "comedic" | "dramatic" | "wholesome" | "absurd" | "suspenseful" | "inspiring"
- pacing: темп видео - "fast" | "medium" | "slow"
  - fast: быстрые переходы, энергичный монтаж
  - medium: сбалансированный темп
  - slow: медленный, cinematic, созерцательный
- emotional_trigger: эмоциональный триггер (смех, удивление, умиление, страх, любопытство)
- duration: {duration}

ВАЖНО:
- ОБЯЗАТЕЛЬНО используй данные из "КОНТЕНТ ВИДЕО" если они указаны
- Концепция должна быть ИМЕННО про указанный контент (животное, локацию и т.д.)
- Hook должен работать в первые 3 секунды
- Climax - это payoff, ради которого смотрят до конца
- Концепция должна быть реализуема за {duration} секунд
- Tone и pacing должны соответствовать друг другу
"""


def build_story_from_template_prompt(
    filled_template: str,
    duration: int
) -> str:
    """Build story prompt for template-based generation."""
    return f"""
Создай идею для вирального короткого видео на основе этого описания:

ОПИСАНИЕ СЦЕНЫ:
{filled_template}

Длительность: {duration} секунд

ВАЖНО: Это описание определяет что именно должно быть в видео - персонаж, локация, стиль, атмосфера.

Верни результат в формате JSON с такими полями:

- concept: концепция видео (2-3 предложения) - что происходит в кадре
- hook: захватывающий hook для первых 3 секунд - что зацепит зрителя
- hook_type: тип хука - "visual" | "text" | "audio"
  - visual: сама картинка цепляет (драма, красота, шок)
  - text: текст на экране цепляет (вопрос, список, интрига)
  - audio: звук/голос цепляет (voiceover, мем-саунд, музыка)
- climax: кульминация/развязка - чем заканчивается видео, какой payoff
- tone: тон видео - "comedic" | "dramatic" | "wholesome" | "absurd" | "suspenseful" | "inspiring"
- pacing: темп видео - "fast" | "medium" | "slow"
- emotional_trigger: эмоциональный триггер (смех, удивление, умиление, страх, любопытство)
- duration: {duration}
"""
