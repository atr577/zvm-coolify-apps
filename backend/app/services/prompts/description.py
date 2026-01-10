"""Description generation prompts."""

from typing import Dict, Any

DESCRIPTION_SYSTEM_PROMPT = "Ты визуальный режиссёр. Твоя задача — превратить абстрактную идею в конкретное визуальное описание сцены для генерации изображения."

TONE_INSTRUCTIONS = {
    "comedic": "Стиль: комедийный, лёгкий, забавный. Яркие цвета, весёлое настроение.",
    "dramatic": "Стиль: драматичный, напряжённый. Контрастное освещение, глубокие тени.",
    "wholesome": "Стиль: тёплый, уютный, душевный. Мягкий свет, тёплые тона.",
    "absurd": "Стиль: абсурдный, сюрреалистичный. Неожиданные элементы, странные ракурсы.",
    "suspenseful": "Стиль: напряжённый, интригующий. Тени, недосказанность, тревожная атмосфера.",
    "inspiring": "Стиль: вдохновляющий, эпичный. Широкие планы, красивый свет."
}

PACING_INSTRUCTIONS = {
    "fast": "Композиция: динамичная, энергичная. Субъект в движении или готов к действию.",
    "medium": "Композиция: сбалансированная. Есть пространство для развития.",
    "slow": "Композиция: созерцательная, cinematic. Больше атмосферы, меньше суеты."
}


def _build_hook_instructions(hook_type: str, hook: str) -> str:
    """Build hook-specific instructions."""
    if hook_type == "text":
        return f"""
ТИП ХУКА: TEXT
Первые 3 секунды зацепят ТЕКСТОМ на экране.
- Предусмотри место для текстового оверлея: "{hook}"
- Текст должен быть читаемым — контрастный фон, свободное пространство
- Основной субъект не должен перекрываться текстом
"""
    elif hook_type == "audio":
        return f"""
ТИП ХУКА: AUDIO
Первые 3 секунды зацепят ЗВУКОМ/ГОЛОСОМ.
- Визуал должен дополнять аудио-хук: "{hook}"
- Сцена должна быть интригующей, но не отвлекать от аудио
- Можно использовать более спокойную композицию
"""
    else:  # visual
        return f"""
ТИП ХУКА: VISUAL
Первые 3 секунды зацепят ВИЗУАЛЬНО.
- Изображение должно СРАЗУ привлекать внимание
- Hook: "{hook}" — это должно быть видно в первом кадре
- Максимальный визуальный импакт с первой секунды
"""


def build_description_prompt(story_data: Dict[str, Any]) -> str:
    """Build description generation prompt from story data."""
    concept = story_data.get('concept', 'N/A')
    hook = story_data.get("hook", "")
    hook_type = story_data.get("hook_type", "visual")
    climax = story_data.get('climax', 'N/A')
    tone = story_data.get('tone', 'comedic')
    pacing = story_data.get('pacing', 'medium')
    emotional_trigger = story_data.get('emotional_trigger', 'N/A')
    filled_template = story_data.get('filled_template', '')

    tone_instr = TONE_INSTRUCTIONS.get(tone, "")
    pacing_instr = PACING_INSTRUCTIONS.get(pacing, "")
    hook_instr = _build_hook_instructions(hook_type, hook)

    template_context = ""
    if filled_template:
        template_context = f"""
РЕФЕРЕНСНОЕ ОПИСАНИЕ СЦЕНЫ (обязательно учитывай!):
{filled_template}

"""

    return f"""
Проанализируй сюжет и создай детальное ВИЗУАЛЬНОЕ описание для первого кадра видео.
{template_context}
СЮЖЕТ:
- Концепция: {concept}
- Hook: {hook}
- Кульминация: {climax}
- Эмоция: {emotional_trigger}

{tone_instr}
{pacing_instr}
{hook_instr}

Твоя задача — описать КОНКРЕТНУЮ СЦЕНУ на основе референса и сюжета.

Верни JSON с полями:

1. "scene_summary": краткое описание сцены в 1-2 предложения

2. "main_subject": главный объект/персонаж в кадре
   - type: "person" | "object" | "animal" | "text" | "abstract"
   - description: детальное описание (внешность, одежда, поза, эмоции)
   - position: где в кадре находится

3. "secondary_elements": массив второстепенных элементов (если есть)
   - каждый элемент: {{type, description, position}}

4. "environment": окружение
   - location: где происходит (интерьер/экстерьер, конкретное место)
   - time_of_day: время суток
   - weather: погода/атмосфера (если применимо)
   - background: что на заднем плане

5. "visual_style": визуальный стиль
   - lighting: тип освещения (естественное, студийное, неон, и т.д.)
   - color_palette: основные цвета
   - mood: настроение кадра
   - camera_angle: ракурс (крупный план, средний, общий, сверху, снизу)
   - aesthetic: стилистика (cinematic, minimalist, vibrant, dark, и т.д.)

6. "key_details": массив важных деталей, которые должны быть в кадре

7. "text_overlay": (ТОЛЬКО если hook_type = "text") информация о тексте на экране
   - text: какой текст показать
   - position: где разместить (top, center, bottom)
   - style: стиль текста (bold, minimal, dramatic)
   - background_contrast: нужен ли контрастный фон для читаемости

ВАЖНО:
- Описывай КОНКРЕТНО и ВИЗУАЛЬНО — что именно видит зритель
- Не пиши абстракции типа "успех" — пиши что ПОКАЗАТЬ чтобы передать успех
- Адаптируйся под тип контента из сюжета
- Если hook_type = "text", ОБЯЗАТЕЛЬНО включи поле text_overlay
"""
