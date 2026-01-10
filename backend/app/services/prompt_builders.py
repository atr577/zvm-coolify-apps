"""
Prompt Builders - builds prompts for each workflow step.
Used by both preview-prompt endpoint and generate endpoints.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


# Default system prompts for each step - stored in project, editable by user
DEFAULT_SYSTEM_PROMPTS = {
    "story": "Ты эксперт по созданию вирального видео-контента для социальных сетей. Создавай концепции, которые цепляют с первых секунд и удерживают внимание до конца.",
    "description": "Ты визуальный режиссёр. Твоя задача — превратить абстрактную идею в конкретное визуальное описание сцены для генерации изображения. Описывай детально и конкретно.",
    "prompt": "Ты эксперт по промптам для AI-генерации изображений. Создавай детальные, конкретные промпты на английском языке, которые точно передают задуманную сцену.",
    "scenario": "Ты режиссёр короткометражных видео. Создавай динамичные, но реалистичные сценарии движения для AI-генерации видео. Учитывай ограничения по длительности.",
    "adaptation": "Ты SMM-эксперт. Адаптируй контент под специфику каждой платформы для максимального охвата. Знаешь тренды Instagram, TikTok и YouTube Shorts."
}


@dataclass
class PromptData:
    """Structure for prompt data."""
    system_prompt: str
    user_prompt: str
    temperature: float = 0.7

    def to_dict(self) -> Dict[str, Any]:
        return {
            "system_prompt": self.system_prompt,
            "user_prompt": self.user_prompt,
            "temperature": self.temperature
        }


def build_story_prompt(
    theme: str = None,
    target_audience: str = None,
    mood: str = None,
    key_elements: str = None,
    duration: int = 5,
    platforms: List[str] = None,
    additional_notes: str = None,
    content_variables: Dict[str, Any] = None,
    system_prompt: str = None
) -> PromptData:
    """Build prompt for story generation."""

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

    # Format content_variables if present
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

    user_prompt = f"""
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

    return PromptData(
        system_prompt=system_prompt or DEFAULT_SYSTEM_PROMPTS["story"],
        user_prompt=user_prompt.strip(),
        temperature=0.8
    )


def build_description_prompt(story_data: Dict[str, Any], system_prompt: str = None) -> PromptData:
    """Build prompt for description generation."""

    concept = story_data.get('concept', 'N/A')
    hook = story_data.get("hook", "")
    hook_type = story_data.get("hook_type", "visual")
    climax = story_data.get('climax', 'N/A')
    tone = story_data.get('tone', 'comedic')
    pacing = story_data.get('pacing', 'medium')
    emotional_trigger = story_data.get('emotional_trigger', 'N/A')

    # Tone instructions
    tone_instructions = {
        "comedic": "Стиль: комедийный, лёгкий, забавный. Яркие цвета, весёлое настроение.",
        "dramatic": "Стиль: драматичный, напряжённый. Контрастное освещение, глубокие тени.",
        "wholesome": "Стиль: тёплый, уютный, душевный. Мягкий свет, тёплые тона.",
        "absurd": "Стиль: абсурдный, сюрреалистичный. Неожиданные элементы, странные ракурсы.",
        "suspenseful": "Стиль: напряжённый, интригующий. Тени, недосказанность, тревожная атмосфера.",
        "inspiring": "Стиль: вдохновляющий, эпичный. Широкие планы, красивый свет."
    }.get(tone, "")

    # Pacing instructions
    pacing_instructions = {
        "fast": "Композиция: динамичная, энергичная. Субъект в движении или готов к действию.",
        "medium": "Композиция: сбалансированная. Есть пространство для развития.",
        "slow": "Композиция: созерцательная, cinematic. Больше атмосферы, меньше суеты."
    }.get(pacing, "")

    # Hook type instructions
    hook_instructions = ""
    if hook_type == "text":
        hook_instructions = f"""
ТИП ХУКА: TEXT
Первые 3 секунды зацепят ТЕКСТОМ на экране.
- Предусмотри место для текстового оверлея: "{hook}"
- Текст должен быть читаемым — контрастный фон, свободное пространство
- Основной субъект не должен перекрываться текстом
"""
    elif hook_type == "audio":
        hook_instructions = f"""
ТИП ХУКА: AUDIO
Первые 3 секунды зацепят ЗВУКОМ/ГОЛОСОМ.
- Визуал должен дополнять аудио-хук: "{hook}"
- Сцена должна быть интригующей, но не отвлекать от аудио
- Можно использовать более спокойную композицию
"""
    else:  # visual
        hook_instructions = f"""
ТИП ХУКА: VISUAL
Первые 3 секунды зацепят ВИЗУАЛЬНО.
- Изображение должно СРАЗУ привлекать внимание
- Hook: "{hook}" — это должно быть видно в первом кадре
- Максимальный визуальный импакт с первой секунды
"""

    user_prompt = f"""
Проанализируй сюжет и создай детальное ВИЗУАЛЬНОЕ описание для первого кадра видео.

СЮЖЕТ:
- Концепция: {concept}
- Hook: {hook}
- Кульминация: {climax}
- Эмоция: {emotional_trigger}

{tone_instructions}
{pacing_instructions}
{hook_instructions}

Твоя задача — описать КОНКРЕТНУЮ СЦЕНУ, которую нужно сгенерировать.

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

    return PromptData(
        system_prompt=system_prompt or DEFAULT_SYSTEM_PROMPTS["description"],
        user_prompt=user_prompt.strip(),
        temperature=0.7
    )


def build_image_prompt_prompt(description_data: Dict[str, Any], system_prompt: str = None) -> PromptData:
    """Build prompt for image prompt generation."""

    user_prompt = f"""
На основе визуального описания сцены создай промпт для генерации изображения.

ОПИСАНИЕ СЦЕНЫ:
{description_data}

Создай промпт на АНГЛИЙСКОМ языке, который точно передаст эту сцену.

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

    return PromptData(
        system_prompt=system_prompt or DEFAULT_SYSTEM_PROMPTS["prompt"],
        user_prompt=user_prompt.strip(),
        temperature=0.6
    )


def build_scenario_prompt(
    image_url: str,
    description_data: Dict[str, Any],
    story_data: Dict[str, Any] = None,
    duration: int = 5,
    system_prompt: str = None
) -> PromptData:
    """Build prompt for scenario generation."""

    story_context = ""
    if story_data:
        story_context = f"""
КОНТЕКСТ ИЗ СЮЖЕТА:
- Концепция: {story_data.get('concept', 'N/A')}
- Hook: {story_data.get('hook', 'N/A')}
- Кульминация: {story_data.get('climax', 'N/A')}
- Тон: {story_data.get('tone', 'N/A')}
- Темп: {story_data.get('pacing', 'N/A')}
"""

    user_prompt = f"""
На основе изображения и описания создай детальный сценарий движения для видео.

ИЗОБРАЖЕНИЕ: {image_url}

ОПИСАНИЕ СЦЕНЫ:
{description_data}
{story_context}

ДЛИТЕЛЬНОСТЬ: {duration} секунд

Создай сценарий движения, который оживит это изображение.

Верни JSON:
{{
  "scene_direction": "общее описание того, что происходит в видео",
  "motion_prompt": "промпт для генерации видео (на английском, 20-50 слов)",
  "camera_movement": {{
    "type": "static" | "pan_left" | "pan_right" | "tilt_up" | "tilt_down" | "zoom_in" | "zoom_out" | "dolly_in" | "dolly_out",
    "speed": "slow" | "medium" | "fast",
    "description": "описание движения камеры"
  }},
  "subject_motion": {{
    "primary": "основное движение главного субъекта",
    "secondary": "движения второстепенных элементов"
  }},
  "atmosphere": {{
    "particles": "частицы в воздухе (пыль, снег, листья, искры)",
    "lighting_changes": "изменения освещения за время видео",
    "background_motion": "движение на фоне"
  }},
  "key_moments": [
    {{"time": 0, "action": "что происходит в начале"}},
    {{"time": {duration//2}, "action": "что происходит в середине"}},
    {{"time": {duration}, "action": "чем заканчивается"}}
  ],
  "audio_suggestion": "рекомендация по звуку/музыке"
}}

ВАЖНО:
- motion_prompt должен быть на АНГЛИЙСКОМ
- Движения должны быть плавными и реалистичными для {duration}-секундного видео
- Камера и субъект должны двигаться гармонично
- Учитывай темп (pacing) из сюжета
"""

    return PromptData(
        system_prompt=system_prompt or DEFAULT_SYSTEM_PROMPTS["scenario"],
        user_prompt=user_prompt.strip(),
        temperature=0.7
    )


def build_adaptation_prompt(
    full_context: Dict[str, Any],
    platforms: List[str],
    system_prompt: str = None
) -> PromptData:
    """Build prompt for platform adaptation."""

    user_prompt = f"""
Адаптируй контент для публикации на платформах: {', '.join(platforms)}

КОНТЕКСТ:
- Сюжет: {full_context.get('story', {})}
- Сценарий: {full_context.get('scenario', {})}

Для КАЖДОЙ платформы создай адаптированный контент.

Верни JSON:
{{
  "instagram": {{
    "caption": "текст поста (до 2200 символов, но оптимально 150-200)",
    "hashtags": ["список", "хештегов", "15-30 штук"],
    "first_comment": "первый комментарий с дополнительными хештегами",
    "best_posting_time": "рекомендуемое время публикации",
    "cta": "призыв к действию"
  }},
  "tiktok": {{
    "caption": "короткое описание (до 150 символов)",
    "hashtags": ["трендовые", "хештеги", "5-10 штук"],
    "sounds_suggestion": "рекомендация по звуку/тренду",
    "duet_stitch_potential": "идеи для duet/stitch"
  }},
  "youtube": {{
    "title": "заголовок (до 100 символов, кликбейтный но честный)",
    "description": "описание для Shorts",
    "tags": ["теги", "для", "поиска"],
    "thumbnail_text": "текст для превью если нужен"
  }}
}}

ВАЖНО:
- Каждая платформа имеет свой tone of voice
- Instagram: более "lifestyle", эстетика
- TikTok: тренды, юмор, вовлечение
- YouTube: информативность, кликабельность
- Хештеги должны быть релевантными и актуальными
"""

    return PromptData(
        system_prompt=system_prompt or DEFAULT_SYSTEM_PROMPTS["adaptation"],
        user_prompt=user_prompt.strip(),
        temperature=0.7
    )


# Mapping step types to builders
STEP_PROMPT_BUILDERS = {
    "story": build_story_prompt,
    "description": build_description_prompt,
    "prompt": build_image_prompt_prompt,
    "scenario": build_scenario_prompt,
    "adaptation": build_adaptation_prompt,
}
