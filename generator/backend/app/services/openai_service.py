"""
OpenAI Service - now powered by AIMLAPI
Handles all text generation and content validation
"""

from app.services.piapi_client import piapi_client, PiAPIError
from app.core.config import settings
from app.schemas.workflow import CustomPrompt
from typing import Dict, Any, List, Optional
import logging
import asyncio
import json

logger = logging.getLogger(__name__)


class OpenAIService:
    def __init__(self):
        self.client = piapi_client
        self.model = settings.GPT_MODEL
        self.mock_mode = settings.MOCK_MODE

    async def generate_story(
        self,
        theme: str = None,
        target_audience: str = None,
        mood: str = None,
        key_elements: str = None,
        duration: int = 5,
        platforms: List[str] = None,
        additional_notes: str = None,
        content_variables: Dict[str, Any] = None,
        custom_prompt: Optional[CustomPrompt] = None
    ) -> Dict[str, Any]:
        """
        Генерация сюжета на основе вводных от пользователя и content_variables
        """
        if self.mock_mode:
            logger.info("MOCK MODE: Returning mock story data")
            from app.services.mock_data import MOCK_STORY
            await asyncio.sleep(1)  # Simulate API delay
            return MOCK_STORY

        # Формируем контекст из параметров
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

        # Формируем описание content_variables если есть
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

        prompt = f"""
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

        try:
            # Use custom prompt if provided
            if custom_prompt:
                result = await self.client.generate_json(
                    prompt=custom_prompt.user_prompt,
                    system_prompt=custom_prompt.system_prompt,
                    temperature=0.8
                )
            else:
                result = await self.client.generate_json(
                    prompt=prompt,
                    system_prompt="Ты эксперт по созданию вирального видео-контента.",
                    temperature=0.8
                )
            logger.info(f"Story generated successfully")
            return result
        except PiAPIError as e:
            logger.error(f"Failed to generate story: {e}")
            raise

    async def generate_description(
        self,
        story_data: Dict[str, Any],
        custom_prompt: Optional[CustomPrompt] = None
    ) -> Dict[str, Any]:
        """
        Генерация детального визуального описания сцены
        Адаптируется под любой тип контента
        Учитывает hook_type, tone, pacing для правильного построения сцены

        Ожидает единый формат story_data:
        concept, hook, hook_type, climax, tone, pacing, emotional_trigger
        """
        if self.mock_mode:
            logger.info("MOCK MODE: Returning mock description data")
            from app.services.mock_data import MOCK_DESCRIPTION
            await asyncio.sleep(1)
            return MOCK_DESCRIPTION

        # Единый формат story_data
        concept = story_data.get('concept', 'N/A')
        hook = story_data.get("hook", "")
        hook_type = story_data.get("hook_type", "visual")
        climax = story_data.get('climax', 'N/A')
        tone = story_data.get('tone', 'comedic')
        pacing = story_data.get('pacing', 'medium')
        emotional_trigger = story_data.get('emotional_trigger', 'N/A')
        filled_template = story_data.get('filled_template', '')

        # Инструкции по тону
        tone_instructions = {
            "comedic": "Стиль: комедийный, лёгкий, забавный. Яркие цвета, весёлое настроение.",
            "dramatic": "Стиль: драматичный, напряжённый. Контрастное освещение, глубокие тени.",
            "wholesome": "Стиль: тёплый, уютный, душевный. Мягкий свет, тёплые тона.",
            "absurd": "Стиль: абсурдный, сюрреалистичный. Неожиданные элементы, странные ракурсы.",
            "suspenseful": "Стиль: напряжённый, интригующий. Тени, недосказанность, тревожная атмосфера.",
            "inspiring": "Стиль: вдохновляющий, эпичный. Широкие планы, красивый свет."
        }.get(tone, "")

        # Инструкции по темпу (для первого кадра влияет на композицию)
        pacing_instructions = {
            "fast": "Композиция: динамичная, энергичная. Субъект в движении или готов к действию.",
            "medium": "Композиция: сбалансированная. Есть пространство для развития.",
            "slow": "Композиция: созерцательная, cinematic. Больше атмосферы, меньше суеты."
        }.get(pacing, "")

        # Формируем инструкции в зависимости от типа хука
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

        # Добавляем filled_template как референс если есть
        template_context = ""
        if filled_template:
            template_context = f"""
РЕФЕРЕНСНОЕ ОПИСАНИЕ СЦЕНЫ (обязательно учитывай!):
{filled_template}

"""

        prompt = f"""
Проанализируй сюжет и создай детальное ВИЗУАЛЬНОЕ описание для первого кадра видео.
{template_context}
СЮЖЕТ:
- Концепция: {concept}
- Hook: {hook}
- Кульминация: {climax}
- Эмоция: {emotional_trigger}

{tone_instructions}
{pacing_instructions}
{hook_instructions}

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

        try:
            # Use custom prompt if provided
            if custom_prompt:
                result = await self.client.generate_json(
                    prompt=custom_prompt.user_prompt,
                    system_prompt=custom_prompt.system_prompt,
                    temperature=0.7
                )
            else:
                result = await self.client.generate_json(
                    prompt=prompt,
                    system_prompt="Ты визуальный режиссёр. Твоя задача — превратить абстрактную идею в конкретное визуальное описание сцены для генерации изображения.",
                    temperature=0.7
                )
            # Прокидываем filled_template для использования в Prompt step
            if filled_template:
                result["filled_template"] = filled_template
            logger.info(f"Description generated successfully")
            return result
        except PiAPIError as e:
            logger.error(f"Failed to generate description: {e}")
            raise

    async def generate_image_prompt(
        self,
        description_data: Dict[str, Any],
        custom_prompt: Optional[CustomPrompt] = None
    ) -> Dict[str, Any]:
        """
        Создание структурированного промпта для генерации изображения
        """
        if self.mock_mode:
            logger.info("MOCK MODE: Returning mock prompt data")
            from app.services.mock_data import MOCK_PROMPT
            await asyncio.sleep(1)
            return MOCK_PROMPT

        # Если есть filled_template - это уже готовое описание для image gen
        filled_template = description_data.get("filled_template", "") if isinstance(description_data, dict) else ""

        template_section = ""
        if filled_template:
            template_section = f"""
БАЗОВОЕ ОПИСАНИЕ (использовать как основу!):
{filled_template}

"""

        prompt = f"""
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

        try:
            # Use custom prompt if provided
            if custom_prompt:
                result = await self.client.generate_json(
                    prompt=custom_prompt.user_prompt,
                    system_prompt=custom_prompt.system_prompt,
                    temperature=0.6
                )
            else:
                result = await self.client.generate_json(
                    prompt=prompt,
                    system_prompt="Ты эксперт по промптам для AI-генерации изображений. Создавай детальные, конкретные промпты на английском.",
                    temperature=0.6
                )
            logger.info(f"Image prompt generated successfully")
            return result
        except PiAPIError as e:
            logger.error(f"Failed to generate image prompt: {e}")
            raise

    async def generate_scenario(
        self,
        image_url: str,
        description_data: Dict[str, Any],
        story_data: Dict[str, Any] = None,
        duration: int = 5,
        custom_prompt: Optional[CustomPrompt] = None
    ) -> Dict[str, Any]:
        """
        Создание сценария движения для видео на основе описания сцены.
        Учитывает tone и pacing из story для правильного ритма.
        """
        if self.mock_mode:
            logger.info("MOCK MODE: Returning mock scenario data")
            from app.services.mock_data import MOCK_SCENARIO
            await asyncio.sleep(1)
            return MOCK_SCENARIO

        # Контекст из story
        story_context = ""
        pacing_instructions = ""
        tone_instructions = ""

        if story_data:
            # Базовый контекст
            story_context = f"""
СЮЖЕТ:
- Концепция: {story_data.get('concept', 'N/A')}
- Hook: {story_data.get('hook', 'N/A')}
- Кульминация: {story_data.get('climax', 'N/A')}
- Эмоция: {story_data.get('emotional_trigger', 'N/A')}
"""
            # Инструкции по темпу
            pacing = story_data.get('pacing', 'medium')
            pacing_instructions = {
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
            }.get(pacing, "")

            # Инструкции по тону
            tone = story_data.get('tone', 'comedic')
            tone_instructions = {
                "comedic": "ТОН: Комедийный — движения могут быть забавными, неожиданными",
                "dramatic": "ТОН: Драматичный — напряжённые, выразительные движения",
                "wholesome": "ТОН: Душевный — мягкие, тёплые движения",
                "absurd": "ТОН: Абсурдный — странные, сюрреалистичные движения",
                "suspenseful": "ТОН: Интрига — медленные, напряжённые движения с недосказанностью",
                "inspiring": "ТОН: Вдохновляющий — эпичные, размашистые движения"
            }.get(tone, "")

        # Извлекаем ключевые элементы из description_data
        scene_summary = description_data.get('scene_summary', '')
        main_subject = description_data.get('main_subject', {})
        environment = description_data.get('environment', {})

        prompt = f"""
Создай ДЕТАЛЬНЫЙ сценарий ДВИЖЕНИЯ для {duration}-секундного видео.

{story_context}
{tone_instructions}
{pacing_instructions}

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

        try:
            # Use custom prompt if provided
            if custom_prompt:
                result = await self.client.generate_json(
                    prompt=custom_prompt.user_prompt,
                    system_prompt=custom_prompt.system_prompt,
                    temperature=0.7
                )
            else:
                result = await self.client.generate_json(
                    prompt=prompt,
                    system_prompt="Ты режиссёр коротких видео. Создавай плавные, кинематографичные сценарии движения.",
                    temperature=0.7
                )
            logger.info("Scenario generated successfully")
            return result
        except PiAPIError as e:
            logger.error(f"Failed to generate scenario: {e}")
            raise

    async def validate_content(
        self,
        content: Dict[str, Any],
        step_type: str,
        previous_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Самопроверка/валидация контента
        """
        if self.mock_mode:
            logger.info("MOCK MODE: Returning mock validation result")
            from app.services.mock_data import MOCK_VALIDATION_RESULT
            await asyncio.sleep(0.5)
            return MOCK_VALIDATION_RESULT

        validation_prompts = {
            "story": """
Проверь сюжет на:
1. Виральный потенциал (0-100)
2. Ясность концепции
3. Привлекательность для целевой аудитории
4. Наличие сильного hook
            """,
            "description": """
Проверь описание на:
1. Соответствие сюжету
2. Достаточность деталей для визуализации
3. Отсутствие противоречий
4. Техническую реализуемость
            """,
            "prompt": """
Проверь промпт на:
1. Соответствие описанию
2. Техническую корректность для AI-генерации изображений
3. Детальность и конкретность
4. Отсутствие конфликтующих элементов
            """,
            "image": """
Проверь изображение на:
1. Соответствие промпту
2. Качество и композицию
3. Пригодность как первый кадр видео
4. Визуальную привлекательность
            """,
            "scenario": """
Проверь сценарий на:
1. Соответствие общей концепции
2. Динамику и хронометраж
3. Техническую реализуемость для image-to-video
4. Виральный потенциал
            """,
            "video": """
Проверь видео на:
1. Соответствие сценарию
2. Качество и плавность
3. Отсутствие артефактов
4. Готовность к публикации
            """,
            "adaptation": """
Проверь адаптацию на:
1. Соответствие специфике каждой платформы
2. Оптимизацию хештегов
3. Корректность технических параметров
4. Привлекательность для аудитории платформы
            """
        }

        validation_criteria = validation_prompts.get(
            step_type,
            "Проверь контент на качество и соответствие требованиям."
        )

        prompt = f"""
{validation_criteria}

Контент для проверки:
{content}

{f"Предыдущие данные для сравнения: {previous_data}" if previous_data else ""}

Верни JSON:
- status: "pass" | "pass_with_warnings" | "fail"
- score: общая оценка 0-100
- criteria_results: {{критерий: {{score: 0-100, comment: "комментарий"}}}}
- warnings: массив предупреждений (если есть)
- errors: массив критических ошибок (если есть)
- recommendations: массив рекомендаций по улучшению
"""

        try:
            result = await self.client.generate_json(
                prompt=prompt,
                system_prompt="Ты строгий QA-специалист по видео-контенту.",
                temperature=0.3
            )
            logger.info(f"Validation completed for {step_type}: {result.get('status')}")
            return result
        except PiAPIError as e:
            logger.error(f"Failed to validate content: {e}")
            raise

    async def adapt_for_platforms(
        self,
        content_data: Dict[str, Any],
        platforms: List[str],
        custom_prompt: Optional[CustomPrompt] = None
    ) -> Dict[str, Dict[str, str]]:
        """
        Адаптация контента для разных платформ

        Args:
            content_data: Полный контекст с полями:
                - story: данные сюжета (concept, hook, climax, tone, pacing, emotional_trigger)
                - scenario: данные сценария (motion_prompt, etc.)
                - image_url: URL сгенерированного изображения
                - video_url: URL сгенерированного видео
            platforms: Список целевых платформ
        """
        if self.mock_mode:
            logger.info("MOCK MODE: Returning mock adaptations")
            from app.services.mock_data import MOCK_ADAPTATIONS
            await asyncio.sleep(1)
            # Фильтруем только запрошенные платформы
            filtered_result = {
                platform: MOCK_ADAPTATIONS[platform]
                for platform in platforms
                if platform in MOCK_ADAPTATIONS
            }
            return filtered_result

        # Извлекаем данные из контекста
        story = content_data.get("story", {})
        scenario = content_data.get("scenario", {})

        # Определяем стиль контента по tone
        tone = story.get('tone', 'comedic')
        tone_style = {
            "comedic": "весёлый, с юмором, эмодзи",
            "dramatic": "серьёзный, эмоциональный",
            "wholesome": "тёплый, душевный, милый",
            "absurd": "странный, мемный, ироничный",
            "suspenseful": "интригующий, загадочный",
            "inspiring": "мотивирующий, вдохновляющий"
        }.get(tone, "нейтральный")

        prompt = f"""
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

        try:
            # Use custom prompt if provided
            if custom_prompt:
                result = await self.client.generate_json(
                    prompt=custom_prompt.user_prompt,
                    system_prompt=custom_prompt.system_prompt,
                    temperature=0.6
                )
            else:
                result = await self.client.generate_json(
                    prompt=prompt,
                    system_prompt="Ты SMM-эксперт по всем социальным платформам.",
                    temperature=0.6
                )

            # GPT может обернуть ответ в объект типа {"platforms": {...}, "adaptations": {...}}
            # Извлекаем данные платформ
            platform_data = result
            if isinstance(result, dict):
                # Проверяем, есть ли платформы напрямую в result
                has_platform_keys = any(p in result for p in platforms)
                if not has_platform_keys:
                    # Ищем вложенный объект с платформами
                    for key in ["platforms", "adaptations", "data", "result"]:
                        if key in result and isinstance(result[key], dict):
                            platform_data = result[key]
                            break

            # Фильтруем только запрошенные платформы
            filtered_result = {
                platform: platform_data[platform]
                for platform in platforms
                if platform in platform_data
            }

            logger.info(f"Platform adaptation completed for: {', '.join(filtered_result.keys())}")
            return filtered_result

        except PiAPIError as e:
            logger.error(f"Failed to adapt for platforms: {e}")
            raise

    async def generate_publishing_meta(
        self,
        prompt_or_template: str,
        platforms: List[str],
        image_url: Optional[str] = None
    ) -> Dict[str, Dict[str, str]]:
        """
        Generate simple publishing metadata (title, description, hashtags) for platforms.
        Works with minimal context - just the prompt/template used for generation.
        """
        if self.mock_mode:
            logger.info("MOCK MODE: Returning mock publishing meta")
            await asyncio.sleep(0.5)
            return {
                platform: {
                    "title": f"Mock title for {platform}",
                    "description": f"Mock description for {platform}",
                    "hashtags": f"#mock #{platform} #shorts"
                }
                for platform in platforms
            }

        prompt = f"""
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

        try:
            result = await self.client.generate_json(
                prompt=prompt,
                system_prompt="You are an SMM expert. Create viral titles and descriptions in English.",
                temperature=0.7
            )

            # Extract platform data from response
            platform_data = result
            if isinstance(result, dict):
                has_platform_keys = any(p in result for p in platforms)
                if not has_platform_keys:
                    for key in ["platforms", "data", "result"]:
                        if key in result and isinstance(result[key], dict):
                            platform_data = result[key]
                            break

            filtered_result = {
                platform: platform_data.get(platform, {
                    "title": "Untitled",
                    "description": "",
                    "hashtags": ""
                })
                for platform in platforms
            }

            logger.info(f"Publishing meta generated for: {', '.join(filtered_result.keys())}")
            return filtered_result

        except PiAPIError as e:
            logger.error(f"Failed to generate publishing meta: {e}")
            raise

    async def generate_content_variants(
        self,
        story_template: str,
        count: int = 4,
        exclude: List[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Генерирует N вариантов контента на основе Story Template

        Args:
            story_template: Шаблон концепции ролика
            count: Количество вариантов (по умолчанию 10)
            exclude: Список уже показанных вариантов для исключения

        Returns:
            List[Dict]: Список вариантов с id, description, content_variables
        """
        if self.mock_mode:
            logger.info(f"MOCK MODE: Returning {count} mock content variants")
            await asyncio.sleep(1)

            # Генерируем generic mock variants
            # Структура адаптируется под любой тип контента
            mock_variants = []
            for i in range(1, count + 1):
                mock_variants.append({
                    "id": i,
                    "description": f"Mock вариант #{i} для шаблона",
                    "content_variables": {
                        "mock_entity": {
                            "type": f"entity_{i}",
                            "style": "default",
                            "note": "This is mock data - real API will generate proper structure"
                        }
                    }
                })
            return mock_variants

        # Реальная генерация через AI
        exclude_descriptions = [v.get("description", "") for v in (exclude or [])]
        exclude_text = f"\n\nИСКЛЮЧИ эти уже показанные варианты:\n" + "\n".join(f"- {d}" for d in exclude_descriptions) if exclude_descriptions else ""

        prompt = f"""
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

ВАЖНО: Верни ТОЛЬКО JSON массив, без обёртки. Ключи content_variables должны соответствовать ТВОЕМУ шаблону.

Верни ровно {count} вариантов.
"""

        try:
            result = await self.client.generate_json(
                prompt=prompt,
                model=self.model
            )

            # GPT может вернуть массив напрямую или обернуть в объект
            if isinstance(result, list):
                variants = result
            elif isinstance(result, dict):
                # Ищем массив в любом ключе объекта
                variants = (
                    result.get("variants") or
                    result.get("concepts") or
                    result.get("items") or
                    result.get("data") or
                    list(result.values())[0] if result else []
                )
            else:
                variants = []

            logger.info(f"Generated {len(variants)} content variants")
            return variants

        except PiAPIError as e:
            logger.error(f"Failed to generate content variants: {e}")
            raise

    async def generate_story_from_template(
        self,
        story_template: str,
        content_variables: dict,
        duration: int,
        platforms: list,
        system_prompt: str = None
    ) -> dict:
        """
        Генерирует Story, комбинируя шаблон и конкретные переменные контента
        Используется для автогенерации обычных роликов
        Возвращает ЕДИНЫЙ формат: concept, hook, hook_type, climax, tone, pacing, emotional_trigger
        """
        if self.mock_mode:
            return {
                "concept": "Story based on template with specific content variables",
                "hook": "Captivating opening moment",
                "hook_type": "visual",
                "climax": "Satisfying payoff moment",
                "tone": "comedic",
                "pacing": "medium",
                "emotional_trigger": "curiosity",
                "duration": duration
            }

        # Подставляем content_variables в шаблон
        filled_template = story_template
        if content_variables:
            for key, value in content_variables.items():
                if isinstance(value, dict):
                    # Для вложенных объектов - форматируем как строку
                    value_str = ", ".join(f"{k}: {v}" for k, v in value.items())
                else:
                    value_str = str(value)
                filled_template = filled_template.replace(f"{{{key}}}", value_str)

        prompt = f"""
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

        try:
            result = await self.client.generate_json(
                prompt=prompt,
                model=self.model,
                system_prompt=system_prompt
            )
            # Сохраняем заполненный шаблон для использования на следующих шагах
            result["filled_template"] = filled_template
            logger.info(f"Generated story from template")
            return result

        except PiAPIError as e:
            logger.error(f"Failed to generate story from template: {e}")
            raise


# Singleton instance
openai_service = OpenAIService()
