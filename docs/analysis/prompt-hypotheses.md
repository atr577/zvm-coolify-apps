# Prompt Hypotheses & Experiments

Документ для тестирования гипотез по улучшению промтов.
Создан: 2026-01-09

---

## Текущие оценки

| Промпт | Текущий балл | Потенциал | Главная проблема |
|--------|--------------|-----------|------------------|
| STORY | 6/10 | 9/10 | Нет формулы hook'ов |
| DESCRIPTION | 5/10 | 8/10 | Слишком абстрактный, лишний шаг |
| PROMPT | 4/10 | 9/10 | Не учитывает специфику KLING |
| SCENARIO | 5/10 | 8/10 | motion_prompt не оптимизирован |
| ADAPTATION | 6/10 | 8/10 | Нет platform-specific формул |
| VALIDATION | 3/10 | 7/10 | Не может валидировать визуал |

---

## Hypothesis 1: Конкретные типы хуков в STORY

### Проблема
Текущий промпт просит "захватывающий hook" — слишком абстрактно.

### Гипотеза
Если дать GPT конкретные типы хуков с примерами, качество hook'ов вырастет.

### Типы хуков (доказанная эффективность):

```
QUESTION — вопрос, на который хочется узнать ответ
  "Почему эта собака умнее большинства людей?"
  "Что будет если смешать кока-колу и ментос?"

PATTERN_INTERRUPT — неожиданный визуал в первом кадре
  "Кот в костюме акулы на роботе-пылесосе"
  "Бабушка делает backflip"

OPEN_LOOP — незавершённость, требующая досмотра
  "Подождите до конца — то что он сделал..."
  "Никто не ожидал что произойдёт на 0:47"

CONTROVERSY — спорное утверждение
  "Собаки умнее кошек и вот почему"
  "Этот лайфхак опасен и вот почему все его используют"

TRANSFORMATION — до/после
  "Из бомжа в миллионера за 30 дней"
  "Эта собака была на улице, а теперь..."

SOCIAL_PROOF — цифры и авторитет
  "10 миллионов людей делают это неправильно"
  "Врачи скрывают этот простой способ"
```

### Изменение в промпте

**Было:**
```
- hook: захватывающий hook для первых 3 секунд - что зацепит зрителя
- hook_type: тип хука - "visual" | "text" | "audio"
```

**Стало:**
```
- hook_strategy: выбери ОДНУ стратегию хука:
  - "question": вопрос → "Почему X делает Y?"
  - "pattern_interrupt": шок-визуал → необычная ситуация в первом кадре
  - "open_loop": интрига → "Досмотри до конца чтобы узнать..."
  - "controversy": спорное → "Все делают X неправильно"
  - "transformation": до/после → драматичное изменение
  - "social_proof": цифры → "N людей не знают что..."

- hook_text: конкретный текст/визуал хука (под выбранную стратегию)

- hook_delivery: как доставить хук зрителю:
  - "visual_only": сама картинка цепляет (драма, красота, шок)
  - "text_overlay": текст на экране в первые 0.5s
  - "voiceover": голос за кадром
  - "text_and_visual": комбинация текста и визуала
```

### Метрики успеха
- [ ] Hook более конкретный и actionable
- [ ] Hook соответствует выбранной стратегии
- [ ] Легче оценить качество (есть критерий)

### Статус: TODO

---

## Hypothesis 2: Убрать DESCRIPTION, сразу генерить IMAGE PROMPT

### Проблема
Текущий flow: Story → Description → Prompt → KLING
Три уровня абстракции = потеря информации на каждом шаге.

### Гипотеза
Объединить Description + Prompt в один шаг, который сразу генерит camera-direction style промпт для KLING.

### Camera Direction Style (best practice):

```
"Close-up shot, golden retriever puppy, soft natural window light,
shallow depth of field, puppy tilts head 15 degrees left,
ears perked up, curious expression, warm wooden floor background,
shot on 85mm lens, cinematic color grading"
```

**Ключевые элементы:**
1. Shot type — close-up, medium, wide, extreme close-up
2. Subject — конкретное описание (не "собака", а "golden retriever puppy")
3. Lighting — natural, studio, neon, golden hour, overcast
4. Lens — 24mm wide, 50mm natural, 85mm portrait, 200mm compressed
5. Environment — background, setting, atmosphere
6. Mood keywords — cinematic, documentary, dreamy, gritty
7. Technical — depth of field, color grading, film stock

### Новый промпт (вместо Description + Prompt):

```
На основе Story создай промпт для генерации первого кадра видео.

STORY:
- Concept: {concept}
- Hook: {hook_text}
- Hook Strategy: {hook_strategy}
- Tone: {tone}

Напиши промпт в стиле CAMERA DIRECTION на английском.

СТРУКТУРА ПРОМПТА:
1. Shot type (close-up / medium / wide / POV)
2. Main subject с деталями (порода, одежда, выражение лица)
3. Action/Pose (одно конкретное положение)
4. Lighting (тип света, направление, время суток)
5. Environment (локация, фон, атмосфера)
6. Camera/Lens (focal length, depth of field)
7. Style keywords (cinematic, documentary, vibrant, moody)

ПРИМЕР:
"Medium shot, orange tabby cat wearing tiny shark costume,
riding Roomba vacuum cleaner through modern living room,
cat looks directly at camera with annoyed expression,
soft afternoon window light from left, shallow depth of field,
minimalist Scandinavian interior background,
shot on 50mm lens, comedy film style, slight motion blur on Roomba"

ПРАВИЛА:
- Один абзац, 50-80 слов
- Только английский
- Конкретные детали, не абстракции
- Промпт должен визуализировать HOOK

Верни JSON:
{
  "image_prompt": "...",
  "negative_prompt": "blurry, low quality, watermark, text, deformed",
  "aspect_ratio": "9:16"
}
```

### Метрики успеха
- [ ] Промпт более конкретный и визуальный
- [ ] Меньше "потерянной информации" между шагами
- [ ] KLING генерит более точные изображения
- [ ] Сокращение времени генерации (один шаг вместо двух)

### Статус: TODO

---

## Hypothesis 3: Physics-based MOTION PROMPT

### Проблема
Текущий motion_prompt: "краткий промпт движения" — KLING нужен детальный промпт с физикой.

### Гипотеза
Промпт с описанием физики движения даст более реалистичную анимацию.

### Physics-based подход (Runway best practice):

> "Stop describing what things look like. Start describing the forces acting on them."
> "Add weight descriptors: 'person trudges forward, each step pressing deep into snow'"

### Новый промпт для SCENARIO:

```
Создай motion prompt для KLING video generation.

ПЕРВЫЙ КАДР: {image_prompt}
STORY: {concept}
DURATION: {duration}s

Опиши ФИЗИКУ движения, не внешний вид.

СТРУКТУРА MOTION PROMPT:

1. SUBJECT PHYSICS (как двигается субъект):
   - Вес и инерция: "heavy paws pressing into cushion"
   - Ускорение: "movement builds gradually, then snaps into action"
   - Микро-движения: "fur ripples with each breath, whiskers twitch"

2. CAMERA PHYSICS (как двигается камера):
   - Тип: dolly in/out, pan, tilt, orbit, handheld
   - Скорость: "smooth 2-second dolly in" или "quick snap pan"
   - Стабилизация: "steady gimbal" или "organic handheld micro-shake"

3. ENVIRONMENTAL PHYSICS (как реагирует окружение):
   - Свет: "sunbeam shifts across floor"
   - Частицы: "dust motes float through light beam"
   - Реакция: "cushion compresses under weight"

4. TIMING:
   - Build-up: первые 30% — подготовка
   - Peak: 50-70% — главное действие
   - Settle: последние 20% — завершение

ПРИМЕР для кота на пылесосе:
"Cat maintains rigid posture as Roomba accelerates beneath it,
ears flatten back from air resistance, tail extends for balance,
slight body sway as Roomba turns corner,
smooth tracking shot follows movement left to right,
cat's eyes lock onto camera with growing irritation,
movement builds over 2 seconds then holds steady"

Верни JSON:
{
  "motion_prompt": "... (40-60 words, English)",
  "camera_movement": {
    "type": "tracking",
    "speed": "medium",
    "description": "follows subject left to right"
  },
  "physics_notes": ["weight on Roomba", "air resistance on fur", "balance adjustments"]
}
```

### Метрики успеха
- [ ] Движение более реалистичное
- [ ] Меньше "плавающих" артефактов
- [ ] Физика объектов соответствует ожиданиям
- [ ] Camera movement более плавный

### Статус: TODO

---

## Hypothesis 4: Platform-Specific ADAPTATION формулы

### Проблема
Текущий промпт не учитывает специфику каждой платформы.

### Гипотеза
Детальные формулы для каждой платформы улучшат engagement.

### Platform Formulas 2025:

```
INSTAGRAM REELS:
- Title: 40-60 символов
- Emoji: 1-2 в начале title
- Hashtags: 5-8 нишевых + 2-3 широких (#reels #viral)
- CTA: вопрос в description для комментов
- Optimal length: 15-30s для reach, 60-90s для engagement

TIKTOK:
- Title: до 150 символов, разговорный стиль
- Emoji: минимум или ноль
- Hashtags: 3-5 максимум (НЕ #fyp spam)
- Sound: предложить trending sound или original
- CTA: "Duet this" или "Stitch with your reaction"
- Optimal length: 60-90s

YOUTUBE SHORTS:
- Title: clickbait-style, 50-70 символов, БЕЗ hashtags
- Description: hashtags здесь + развёрнутое описание
- Tags: 8-12 релевантных keywords
- CTA: "Subscribe for more [niche]"
- End screen: prompt для subscription
- Optimal length: 30-60s
```

### Новый промпт для ADAPTATION:

```
Адаптируй видео для платформ: {platforms}

ВИДЕО:
- Hook: {hook_text} ({hook_strategy})
- Concept: {concept}
- Tone: {tone}
- Emotional trigger: {emotional_trigger}

ДЛЯ КАЖДОЙ ПЛАТФОРМЫ создай оптимизированную версию:

INSTAGRAM REELS:
{
  "title": "emoji + hook в 40-60 символов",
  "description": "развёрнутый текст + CTA вопрос",
  "hashtags": ["5-8 нишевых", "2-3 широких"],
  "cta_type": "question" | "challenge" | "save"
}

TIKTOK:
{
  "title": "разговорный hook до 150 символов",
  "hashtags": ["3-5 релевантных"],
  "sound_suggestion": "trending sound или 'original'",
  "cta_type": "duet" | "stitch" | "comment"
}

YOUTUBE SHORTS:
{
  "title": "clickbait 50-70 символов БЕЗ hashtags",
  "description": "SEO описание 100-200 слов",
  "tags": ["8-12 keywords"],
  "end_cta": "Subscribe for more [niche]"
}

ПРАВИЛА:
- Title должен содержать HOOK
- Стиль текста = tone видео ({tone})
- Hashtags релевантны emotional_trigger ({emotional_trigger})
- Каждая платформа = уникальная адаптация, не копия
```

### Метрики успеха
- [ ] Title содержит hook
- [ ] Hashtags релевантны контенту
- [ ] Character limits соблюдены
- [ ] CTA соответствует платформе

### Статус: TODO

---

## Hypothesis 5: Убрать VALIDATION для image/video

### Проблема
GPT не может "увидеть" изображение по URL. Валидация image/video бессмысленна.

### Гипотеза
Заменить AI-валидацию на rule-based проверки + human review.

### Новый подход:

```
STORY/DESCRIPTION/PROMPT — AI validation (GPT может оценить текст)

IMAGE — Rule-based:
- URL доступен и возвращает 200
- Файл > 10KB (не placeholder)
- Aspect ratio соответствует запросу
- Human review: показать пользователю для approval

VIDEO — Rule-based:
- URL доступен
- Duration соответствует запросу
- Файл > 100KB
- Human review: показать пользователю

ADAPTATION — AI validation (GPT может оценить текст)
```

### Метрики успеха
- [ ] Нет ложных "pass" для плохих изображений
- [ ] Быстрее (нет лишних API calls)
- [ ] Честная оценка через human review

### Статус: TODO

---

## Experiment Log

### Experiment 1: [DATE] — [HYPOTHESIS]
- **Изменение:** ...
- **Результат:** ...
- **Метрики:** ...
- **Вывод:** PASS / FAIL / INCONCLUSIVE

---

## Sources

- [AI Video Prompting Strategies - Runway, Kling, Veo](https://medium.com/@creativeaininja/how-to-actually-control-next-gen-video-ai-runway-kling-veo-and-sora-prompting-strategies-92ef0055658b)
- [Viral Video Hooks Strategies](https://www.aikenhouse.com/post/viral-video-hooks-strategies-for-short-form-success)
- [Best TikTok Hooks 2025](https://www.submagic.co/blog/best-hooks-for-tiktok-and-instagram)
- [Video Content Optimization 2025](https://stackinfluence.com/video-content-optimization-in-2025/)
- [AI Video Models Guide 2025](https://ulazai.com/ai-video-models-guide-2025/)
