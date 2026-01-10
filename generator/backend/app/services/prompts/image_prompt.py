"""Image prompt generation prompts."""

from typing import Dict, Any

IMAGE_PROMPT_SYSTEM_PROMPT = "Ты эксперт по промптам для AI-генерации изображений. Создавай детальные, конкретные промпты на английском."


def build_image_prompt_prompt(description_data: Dict[str, Any]) -> str:
    """Build image prompt generation prompt from description data."""
    filled_template = description_data.get("filled_template", "") if isinstance(description_data, dict) else ""

    template_section = ""
    if filled_template:
        template_section = f"""
БАЗОВОЕ ОПИСАНИЕ (использовать как основу!):
{filled_template}

"""

    return f"""
На основе визуального описания сцены создай промпт для генерации изображения.
{template_section}
ОПИСАНИЕ СЦЕНЫ:
{description_data}

Создай промпт на АНГЛИЙСКОМ языке, который точно передаст эту сцену.
Если есть "БАЗОВОЕ ОПИСАНИЕ" - используй его как основу, это уже готовый промпт.

Верни JSON:
{{
  "main_prompt": "основной промпт 50-150 слов, детальное описание сцены",
  "style_suffix": "стилистические модификаторы: качество, стиль, освещение",
  "negative_prompt": "что НЕ должно быть в изображении",
  "recommended_aspect_ratio": "9:16" | "16:9" | "1:1"
}}

ПРАВИЛА для main_prompt:
1. Начни с главного субъекта (кто/что в центре)
2. Добавь детали внешности/вида
3. Опиши действие/позу
4. Укажи окружение и фон
5. Добавь освещение и атмосферу
6. Закончи стилистикой (cinematic, photorealistic, etc.)

Пример хорошего промпта:
"Young confident businesswoman in elegant black suit, standing by floor-to-ceiling windows, city skyline behind her, golden sunset light illuminating her face, she's looking at camera with slight smile, modern minimalist office interior, cinematic composition, professional photography, shallow depth of field"
"""
