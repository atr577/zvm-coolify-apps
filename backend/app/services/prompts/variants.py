"""Content variants generation prompts."""

from typing import List, Dict, Any


def build_variants_prompt(
    story_template: str,
    count: int,
    exclude: List[Dict[str, Any]] = None
) -> str:
    """Build content variants generation prompt."""
    exclude_descriptions = [v.get("description", "") for v in (exclude or [])]
    exclude_text = (
        f"\n\nИСКЛЮЧИ эти уже показанные варианты:\n" +
        "\n".join(f"- {d}" for d in exclude_descriptions)
    ) if exclude_descriptions else ""

    return f"""
На основе этого шаблона концепции, сгенерируй {count} уникальных вариантов контента.

ШАБЛОН КОНЦЕПЦИИ:
{story_template}

Сделай варианты разнообразными и интересными.
{exclude_text}

ИНСТРУКЦИИ:
1. Проанализируй шаблон и определи КЛЮЧЕВЫЕ СУЩНОСТИ (животное, человек, место, предмет и т.д.)
2. Создай content_variables с РЕЛЕВАНТНЫМИ ключами для этих сущностей
3. НЕ используй фиксированную структуру - адаптируй под контент

ПРИМЕРЫ для разных типов контента:

Если шаблон про СОБАКУ:
{{
  "id": 1,
  "description": "Бостон терьер на диване, разбросанные игрушки, довольный вид",
  "content_variables": {{
    "animal": {{"breed": "бостон терьер", "action": "лежит на диване", "expression": "довольный"}},
    "environment": {{"location": "гостиная", "items": "разбросанные игрушки", "mood": "уютный"}}
  }}
}}

Если шаблон про ЧЕЛОВЕКА И МАШИНУ:
{{
  "id": 1,
  "description": "Блондинка в красном платье, Ferrari, Париж",
  "content_variables": {{
    "person": {{"appearance": "блондинка", "outfit": "красное платье", "pose": "стоит у машины"}},
    "vehicle": {{"brand": "Ferrari", "model": "SF90", "color": "красный"}},
    "location": {{"city": "Париж", "landmark": "Эйфелева башня", "time": "закат"}}
  }}
}}

Если шаблон про ЕДУ:
{{
  "id": 1,
  "description": "Сочный бургер с сыром, крупный план, пар поднимается",
  "content_variables": {{
    "food": {{"dish": "бургер", "ingredients": "говядина, сыр, салат", "style": "сочный"}},
    "presentation": {{"angle": "крупный план", "effects": "пар", "lighting": "тёплый"}}
  }}
}}

ВАЖНО: Верни JSON объект с ключом "variants", содержащим массив из {count} вариантов.
Ключи content_variables должны соответствовать ТВОЕМУ шаблону.

Формат ответа:
{{"variants": [ ... {count} вариантов ... ]}}
"""
