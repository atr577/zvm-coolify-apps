# SPEC: Research Agent

## Context

Ручной прогон paint mixing эксперимента показал: прежде чем production agent может генерить контент, нужен research phase — изучить нишу, конкурентов, визуальный стиль, engagement механики, подобрать модели. Для paint mixing это заняло ~15 web-поисков, 3 итерации eval loop, и дало research brief со score 85.

Research Agent автоматизирует этот процесс. На входе — строка из Google Sheets таблицы идей. На выходе — Production Config, по которому Production Agent генерит контент.

---

## Pipeline

```
Строка из таблицы идей (Google Sheets)
    │
    ▼
[1] Parse Input ──► структурированный concept brief
    │
    ▼
[2] Knowledge Base Lookup ──► что уже знаем (модели, паттерны, механики)
    │
    ▼
[3] Web Research (широкий) ──► сырые данные по 6 направлениям
    │
    ▼
[4] Research Brief (draft) ──► EVAL GATE ──► iterate on weakest (max 3)
    │
    ▼
[5] Model Matching ──► выбор моделей из KB по типу контента
    │
    ▼
[6] Production Config (draft) ──► EVAL GATE ──► iterate (max 3)
    │
    ▼
[7] Human Review ──► approved Production Config
    │
    ▼
    Production Agent (SPEC-agent-eval-loop.md)
```

Ноль API-генераций. Только LLM calls + web search. Стоимость: ~$0.05-0.15 на концепт.

---

## 1. Input: Строка из таблицы

Google Sheets ID: `1PuluIu5bsG_-XnrXp_kaEGWdbecHkiNdnjkXYcMSinE`

| Поле таблицы | Mapping | Обязательное |
|---|---|---|
| Название | `concept_name` | да |
| Суть идеи | `concept_description` | да |
| Платформа/тип | `platform` | да |
| ДЛ | `target_duration` | нет (research определит) |
| Хук ЦПК | `hook_hypothesis` | нет |
| Хук ПВС | `rewatch_hypothesis` | нет |
| Вовлечение | `engagement_hypothesis` | нет |
| Пример | `reference_url` | нет |

Поля "Хук ЦПК", "Хук ПВС", "Вовлечение" — это **гипотезы** авторов идеи. Research agent должен их валидировать, расширить или опровергнуть, а не слепо копировать.

### Parse Input

```python
@dataclass
class ConceptBrief:
    concept_name: str
    concept_description: str
    platform: str
    target_duration: str | None
    hook_hypothesis: str | None
    rewatch_hypothesis: str | None
    engagement_hypothesis: str | None
    reference_url: str | None
```

---

## 2. Knowledge Base Lookup

Перед web search — проверить что уже знаем. Не искать то что есть в KB.

| KB файл | Что берём |
|---------|-----------|
| `docs/knowledge/viral-shorts-mechanics.md` | Hook паттерны, retention benchmarks, algorithm mechanics, engagement CTAs, technical parameters (safe zones, duration, audio levels) |
| `docs/knowledge/prompting-video.md` | Правила промптинга для video моделей |
| `docs/knowledge/prompting-image.md` | Правила промптинга для image моделей |
| `memory/fal-video-models.md` | Модели, цены, capabilities, gotchas |

**Результат:** список того что УЖЕ покрыто KB (не нужно ресерчить) + список пробелов (нужен web search).

---

## 3. Web Research

### 6 направлений исследования

| # | Направление | Что искать | Метод |
|---|-------------|-----------|-------|
| 1 | **Нишевый ресерч** | Топовые каналы/авторы в нише, что набирает views, какие форматы работают | Web search: "{concept} viral {platform}", "{concept} top channels" |
| 2 | **Визуальный стиль** | Как выглядят успешные видео — камера, освещение, композиция, цвета | Анализ reference_url (если есть) + поиск конкурентов |
| 3 | **Структура и тайминг** | Фазы видео, длительность каждой, hook timing | Анализ конкурентов + KB (viral-shorts-mechanics.md) |
| 4 | **Engagement паттерн** | Какие CTA работают в этой нише, что вызывает комменты/шеры | Web search + валидация hook_hypothesis и engagement_hypothesis |
| 5 | **Feasibility** | Можно ли это сгенерить нашими инструментами (fal.ai модели) | KB (fal-video-models.md) + промпт-гайды моделей |
| 6 | **Risks** | Что может не работать, где AI артефакты, policy risks | KB (AI content policy) + web search |

### Reference URL Analysis

Если `reference_url` есть — это главный источник:
1. Открыть видео
2. Описать: visual style, structure, timing, engagement mechanics
3. Использовать как baseline для research brief

Если нет — research agent ищет 3-5 примеров сам и выбирает лучший как референс.

### Метод поиска

- 5-10 web searches параллельно (по направлениям)
- 2-3 глубоких чтения страниц на каждый результат
- Перекрёстная проверка фактов: если факт из одного источника — пометить `[unverified]`
- KB lookup первичен — не искать то что уже знаем

---

## 4. Research Brief

### Структура (фиксированная)

```markdown
# Research Brief: {concept_name}

## 1. Визуальный стиль
- Формат, камера, освещение, цвета
- Референсные каналы (имя, подписчики, что делают)
- Подформаты (вариации внутри концепта)

## 2. Структура и тайминг
- Длительность (обоснованная данными)
- Фазы с секундами (hook → build → payoff → hold)
- Одно действие на фазу

## 3. Dos / Don'ts
- DO: конкретные приёмы
- DON'T: конкретные ошибки

## 4. Инструменты
- Image model + обоснование
- Video model + обоснование
- Audio strategy
- Post-processing

## 5. Engagement паттерн
- Hook strategy (валидация/расширение гипотезы автора)
- Rewatch trigger
- CTA pattern
- Масштабирование (как делать 60+ уникальных видео)

## 6. Риски и ограничения
- Таблица: риск | вероятность | митигация
```

### Eval Gate: Research Brief

Паттерн из `experiments/paint-mixing/research-algorithm.md`.

| Критерий | Вопрос | Порог |
|----------|--------|-------|
| Quality | Достаточно глубоко для создания видео? Конкретика vs общие слова? | >= 80 |
| Completeness | Все 6 направлений покрыты? Нет дыр? | >= 80 |
| Unambiguity | Production agent сможет работать без уточнений? | >= 80 |
| Feasibility | Реализуемо нашими инструментами? Модели подтверждены? | >= 80 |
| Accuracy | Факты проверены? Непроверенное помечено? | >= 80 |

**Threshold:** overall >= 80 AND каждый критерий >= 70.

**Eval loop:** max 3 итерации. На каждой — найти слабейший критерий, целевой ресерч (2-4 поиска ТОЛЬКО по слабому месту), обновить brief, пересчитать оценки.

**Паттерн paint mixing:** v1 (score 59) → v2 (score 83, +24 от целевого ресерча) → v3 (score 85, подтверждение feasibility).

---

## 5. Model Matching

На основе research brief + KB — выбрать конкретные модели и параметры.

### Решения

| Решение | На основе чего | Пример |
|---------|---------------|--------|
| Video model | Тип motion + бюджет | Жидкости → Veo 3.1; физика → Kling v3; бюджет → Minimax |
| Image model | Стиль + нужен ли edit | Реализм → Nano Banana Pro; edit → Flux Kontext |
| Audio strategy | Engagement pattern | Satisfying → ambient music (Lyria2); puzzle → timer SFX |
| Duration | KB benchmarks + ниша | Satisfying → 15-30s; puzzle → 10-15s |
| Needs end frame? | Тип контента | Process video → да; static → нет |
| Needs video gen? | Тип контента | Motion → да; spot the difference → нет (compose_static) |

### Источник решений: Knowledge Base

```
memory/fal-video-models.md:
  - Модели с start+end frame support
  - Цены, длительности, gotchas
  - Quality notes по типу контента

docs/knowledge/viral-shorts-mechanics.md:
  - Duration sweet spots по типу контента
  - Engagement patterns по нише
  - Technical parameters (safe zones, audio levels)
```

Если KB не покрывает тип контента (новая ниша, новый формат) — agent отмечает `model_confidence: low` и рекомендует тестовый прогон перед массовой генерацией.

---

## 6. Production Config

### Schema

```python
@dataclass
class ProductionConfig:
    # Metadata
    concept_name: str
    concept_description: str
    created_at: str
    research_brief_score: int

    # Visual
    visual_style: str              # "overhead close-up, studio lighting, no face"
    camera: str                    # "top-down flat lay, static, 90 degrees"
    color_palette: str             # "high contrast, saturated on neutral background"

    # Structure
    target_duration: int           # seconds
    phases: list[dict]             # [{name: "hook", start: 0, end: 2, description: "..."}, ...]
    needs_end_frame: bool
    needs_video_gen: bool
    direction: str                 # "forward" | "reverse" | "agent_decides"

    # Models
    image_model: str               # fal.ai model path
    image_model_reason: str        # why this model
    video_model: str | None        # fal.ai model path (None if no video gen)
    video_model_reason: str | None
    audio_strategy: str            # "lyria2_ambient" | "sfx_timer" | "no_audio"
    music_prompt_template: str | None

    # Prompts
    image_prompt_template: str     # with {variables}
    end_frame_prompt_template: str | None
    video_prompt_template: str | None

    # Engagement
    hook_strategy: str             # validated/expanded from hypothesis
    rewatch_trigger: str
    cta_pattern: str               # "guess the {X}" | "spot the difference" | ...
    cta_position: str              # "center_above_middle" | "top_safe" | ...

    # Meta
    title_template: str            # "Color + Color = ? {emoji}" with {variables}
    description_template: str
    tags: list[str]

    # Scaling
    variation_axis: str            # what changes per video: "color pair" | "object" | "scenario"
    variation_examples: list[str]  # 5-10 примеров вариаций
    estimated_unique_videos: int   # сколько уникальных видео можно сделать

    # Cost
    estimated_cost_per_video: float  # $ estimate
    model_confidence: str          # "high" (tested) | "medium" (KB match) | "low" (new niche)

    # Risks
    risks: list[dict]             # [{risk, probability, mitigation}, ...]
```

### Eval Gate: Production Config

| Критерий | Вопрос | Порог |
|----------|--------|-------|
| Completeness | Все поля заполнены? Нет None где не должно быть? | >= 80 |
| Consistency | Модели совместимы с visual style? Duration совпадает с phases? | >= 80 |
| Actionability | Production agent может сразу начать без вопросов? | >= 80 |
| Scalability | variation_axis + examples дают >= 30 уникальных видео? | >= 70 |

**Threshold:** overall >= 80 AND каждый критерий >= 70.

---

## 7. Human Review

Production Config показывается человеку. Человек может:

1. **Approve** — config идёт в Production Agent as-is
2. **Adjust** — поправить конкретные поля (model, duration, CTA) и approve
3. **Reject** — отправить обратно с комментарием (research agent делает дополнительный ресерч)

### Что показывать человеку (summary)

```
Концепт: Смешивание красок
Visual: overhead close-up, studio lighting
Duration: 15-20s
Video model: Veo 3.1 ($1.60/gen) — confidence: high (tested)
Image model: Nano Banana Pro
Audio: Lyria2 ambient
Hook: 3 ярких блоба краски → "guess the color"
CTA: "What color will it make?" center above middle
Variations: color pairs (60+ combinations)
Cost: ~$1.83/video
Risks: AI content policy (mitigate: vary visual style per video)
```

---

## 8. Research Agent State

```python
@dataclass
class ResearchState:
    # Input
    concept_brief: ConceptBrief

    # KB context
    kb_findings: dict              # what KB already knows
    kb_gaps: list[str]             # what needs web research

    # Research
    web_search_results: list[dict] # raw search results
    reference_analysis: dict | None # analysis of reference_url

    # Outputs
    research_brief: str | None
    research_brief_score: int | None
    production_config: dict | None
    production_config_score: int | None

    # Eval history
    eval_results: dict[str, list]  # gate_name → list of EvalResults

    # Pipeline control
    current_step: str              # "kb_lookup" | "web_research" | "research_brief" | "model_matching" | "production_config"
    status: str                    # "running" | "awaiting_review" | "approved" | "rejected"
```

---

## 9. Примеры: как Research Agent обработает разные концепты

### Пример 1: "Смешивание красок" (строка 10 таблицы)

```
Input: {name: "Смешивание красок", description: "загадка какой цвет получится",
        hook: "стартовая заставка", engagement: "Угадал цвет?",
        reference: "youtube.com/shorts/213pgzkTljg"}

KB lookup → viral-shorts-mechanics.md (duration: 15-30s для satisfying),
            fal-video-models.md (Veo 3.1 для жидкостей, start+end frame)

Web research → tonesterpaints (1.4M), paintturner (4M), overhead camera,
               minimal style, no commentary, color reveal = payoff

Research brief eval → v1: 72 (feasibility weak) → v2: 83 (confirmed Veo) → v3: 86 ✓

Model matching → Veo 3.1, Nano Banana Pro, Lyria2 ambient

Production Config → 15-20s, overhead, forward, "guess the color" CTA,
                    variation_axis: color pair (60+ combinations)
```

### Пример 2: "Найди отличия" (строка 15 таблицы)

```
Input: {name: "Найти Х отличий", description: "2 картинки и Х отличий",
        hook: "Яркая картинка и первые явные отличия",
        engagement: "Реальное количество отличий Х-1",
        duration: "15"}

KB lookup → viral-shorts-mechanics.md (puzzle format: competition + curiosity),
            no video model needed (static)

Web research → spot the difference channels, engagement mechanics,
               "impossible last difference" trick

Research brief eval → v1: 78 → v2: 85 ✓

Model matching → Nano Banana Pro (base image), Flux Kontext (edit для отличий),
                 NO video generation, compose_static (FFmpeg),
                 timer SFX audio

Production Config → 15s, two images side by side,
                    needs_video_gen: false, needs_end_frame: false,
                    variation_axis: scene theme (kitchen, park, office...),
                    CTA: "How many did you find?"
```

### Пример 3: "Космические катастрофы" (строка 11 таблицы)

```
Input: {name: "Космические катастрофы", description: "Если вместо Солнца...",
        hook: "стартовая заставка", engagement: "Какую катастрофу представляешь?"}

KB lookup → no direct match for space content in KB,
            fal-video-models.md (Kling v3 для физика?)

Web research → "what if" space channels, Universe Sandbox,
               epic scale comparisons, Kurzgesagt style

Research brief eval → v1: 65 (feasibility low — space visuals hard for AI)
                    → v2: 75 (found Kling O3 for multi-shot, epic scale)
                    → v3: 82 ✓

Model matching → Kling O3 (multi-shot transitions), Flux Kontext (planet composites),
                 epic orchestral music (Lyria2)
                 model_confidence: "low" — space visuals not tested

Production Config → 10-15s, wide shot → zoom → impact,
                    needs_video_gen: true, needs_end_frame: false,
                    variation_axis: scenario ("if Moon hit Earth", "if Sun disappeared"),
                    risk: AI space visuals may look cheap → recommend test run
```

---

## 10. Cost Estimate

| Компонент | Стоимость |
|-----------|-----------|
| LLM: KB lookup + parsing | ~$0.005 |
| LLM: Web research analysis (5-10 searches) | ~$0.02 |
| LLM: Research brief generation (3 attempts) | ~$0.02 |
| LLM: Research brief eval (3 attempts) | ~$0.01 |
| LLM: Production config generation (3 attempts) | ~$0.02 |
| LLM: Production config eval (3 attempts) | ~$0.01 |
| Web search API calls | ~$0.00 (Tavily free tier / web search tool) |
| **Total per concept** | **~$0.05-0.10** |

Пренебрежимо мало. Research для 30 концептов = ~$1.50-3.00.

---

## 11. File Structure

```
backend/app/agent/
├── research/
│   ├── __init__.py
│   ├── agent.py              # Research agent (LangGraph)
│   ├── state.py              # ResearchState, ConceptBrief, ProductionConfig
│   ├── kb_lookup.py          # Knowledge base search
│   ├── web_research.py       # Web search + analysis
│   ├── brief_generator.py    # Research brief generation
│   ├── model_matcher.py      # Model selection from KB
│   ├── config_generator.py   # Production Config generation
│   └── eval.py               # Eval gates for brief + config (reuses agent/eval.py)
```

Переиспользует: `agent/eval.py` (EvalResult, eval_loop), `OpenAIClient`.

---

## 12. Existing Patterns

| Паттерн | Файл | Что берём |
|---------|------|-----------|
| Research algorithm (6 направлений, eval loop, iterate on weakest) | `experiments/paint-mixing/research-algorithm.md` | Весь research flow |
| Research brief structure (6 секций) | `experiments/paint-mixing/research-brief.md` | Формат выходного документа |
| Eval loop (criteria, threshold, max attempts) | `docs/specs/SPEC-agent-eval-loop.md` | EvalResult, eval_loop() |
| Input from Google Sheets | Таблица идей (spreadsheet ID в спеке) | Структура входных данных |
| KB lookup pattern | `docs/knowledge/*.md` | Файлы для поиска |
| Model selection by content type | `docs/ideas/agent-producer.md` | Таблица моделей |

---

## Не входит в эту спеку

- Production Agent (отдельная спека: SPEC-agent-eval-loop.md)
- Reference video analysis через vision model (потом)
- Автоматическая публикация (потом)
- A/B testing разных configs (потом)
- Feedback loop от метрик YouTube (потом)

---

Created: 2026-02-17
