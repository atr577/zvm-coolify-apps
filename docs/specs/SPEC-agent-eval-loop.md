# SPEC: Agent Producer Eval Loop

## Context

Ручной прогон paint mixing эксперимента показал полный пайплайн: concept → image → video → music → assembly → YouTube publish (~$1.80/видео). Каждый creative output требует оценки качества перед использованием. Эта спека определяет систему eval gates для Agent Producer.

## Pipeline Overview

```
Research Brief (input)
    │
    ▼
[1] Start Frame Prompt ──► EVAL GATE ──► Image Generation (fal.ai)
    │
    ▼
[2] End Frame Edit Prompt ──► EVAL GATE ──► End Frame Generation (fal.ai /edit)
    │
    ▼
[3] Video Prompt ──► EVAL GATE ──► Video Generation (fal.ai, model from KB)
    │
    ▼
[4] Music Prompt ──► EVAL GATE ──► Music Generation (Lyria2)
    │
    ▼
[5] CTA + Meta ──► EVAL GATE
    │
    ▼
[6] Forward vs Reverse ──► EVAL GATE
    │
    ▼
    Hook Extraction → Assembly → CTA Overlay → Reverse → Encode  [DETERMINISTIC]
    │
    ▼
[7] Final Assembly Eval ──► EVAL GATE ──► DONE
```

- **7 eval gates** — все LLM-based (gpt-4o-mini, temperature 0.3)
- **Media генерации** (image, video, music) — без eval (vision model потом)
- **FFmpeg шаги** — детерминированные, без eval
- **Knowledge base** решает: модель, длительность, вариации (без eval loop)

---

## 1. EvalResult

Паттерн из `backend/app/core/hook_analyzer.py` (Hook dataclass + scoring + metadata).

```python
@dataclass
class CriterionScore:
    name: str
    score: int          # 0-100
    feedback: str       # что не так / что хорошо


@dataclass
class EvalResult:
    passed: bool
    overall_score: int  # 0-100, среднее по критериям
    criteria: list[CriterionScore]
    weakest: str | None          # имя слабейшего критерия (None если passed)
    feedback: str                # actionable instruction для retry (пусто если passed)
    attempt: int                 # 1, 2 или 3
    raw_response: dict           # полный JSON от LLM для дебага
```

---

## 2. Eval Gates

**Threshold:** overall >= 80 AND каждый критерий >= 65.

### Gate 1: Start Frame Prompt

| Критерий | Вопрос |
|----------|--------|
| Visual Clarity | Сцена однозначна? Image model отрендерит без додумывания? |
| Composition | Ракурс, кадрирование, aspect ratio соответствуют брифу? |
| Hook Potential | Первый кадр остановит скролл? Контраст, чёткий subject? |
| Technical Feasibility | Совместимо с целевой image model? Нет невозможных элементов? |

### Gate 2: End Frame Edit Prompt

| Критерий | Вопрос |
|----------|--------|
| Continuity | Все элементы сцены сохранены (контейнер, инструмент, освещение, камера)? |
| End State Clarity | Целевое конечное состояние однозначно ("uniform flat color", не "mixed")? |
| Negative Constraints | Явно указано что НЕ менять и чего НЕ должно быть? |
| Edit Scope | Минимальный скоуп — только цвет/поверхность, ничего структурного? |

### Gate 3: Video Prompt

| Критерий | Вопрос |
|----------|--------|
| Motion Clarity | Движение описано как одно чёткое действие с началом и концом? |
| Pacing | Слова про тайминг соответствуют длительности? Не перегружено действиями? |
| Model Compatibility | Использует правильные паттерны для целевой модели (Subject/Motion/Camera)? |
| Narrative Arc | Есть hook → payoff → hold структура? |

### Gate 4: Music Prompt

| Критерий | Вопрос |
|----------|--------|
| Mood Match | Настроение музыки совпадает с видео (ambient для paint mixing и т.д.)? |
| Specificity | Конкретные музыкальные термины (BPM, инструменты, жанр) vs размытые описания? |
| Duration Fit | Энергетическая арка подходит под длину видео? |
| Safety | Нет unsafe/blocked слов для fal.ai? |

### Gate 5: CTA + Meta

| Критерий | Вопрос |
|----------|--------|
| Title Formula | Следует проверенному паттерну для ниши ("Color + Color = ?", "Guess the...")? |
| CTA Alignment | Текст оверлея совпадает с темой title/description? |
| Tag Relevance | Теги высокочастотные, релевантные, не спам (3-5 штук)? |
| Engagement Hook | Создаёт curiosity gap или call to action? |

### Gate 6: Forward vs Reverse

| Критерий | Вопрос |
|----------|--------|
| Content Fit | Концепт выигрывает от reverse (e.g. "unmixing")? |
| Audio Compatibility | Forward audio поверх reverse video имеет смысл? |
| CTA Adjustment | CTA адаптирован под выбранное направление? |

### Gate 7: Final Assembly

| Критерий | Вопрос |
|----------|--------|
| Coherence | Все части (image, video, music, CTA) рассказывают одну историю? |
| Timing | Music hook совпадает с video action? CTA читаем и по таймингу? |
| Quality Bar | Пройдёт на YouTube Shorts (не obviously AI, не сломано)? |
| Publishability | Нет артефактов, нет audio desync, правильный encoding? |

---

## 3. Eval Loop

Паттерн из `experiments/paint-mixing/research-algorithm.md` (5 criteria, threshold >= 85, iterate on weakest, max 3 iterations) + `backend/app/core/music_generator.py` (feedback + previous_prompt → regeneration).

```python
MAX_ATTEMPTS = 3
PASS_THRESHOLD = 80
MIN_CRITERION = 65


async def eval_loop(generate_fn, eval_fn, context: dict) -> tuple[str, EvalResult]:
    prev_feedback = None
    artifact = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        artifact = await generate_fn(
            context=context,
            attempt=attempt,
            previous_feedback=prev_feedback,
            previous_artifact=artifact,
        )
        result = await eval_fn(artifact, attempt)

        if result.passed:
            return artifact, result

        prev_feedback = result.feedback

    # 3 попытки исчерпаны — вернуть последний результат
    return artifact, result
```

### Feedback propagation

Каждый `generate_fn` при retry получает:

```
REGENERATION (attempt {N}/3):
Previous output: "{previous_artifact}"
Feedback: "{previous_feedback}"

Create NEW version addressing the feedback.
Focus on: {weakest_criterion}
```

**Temperature narrowing** (паттерн из Discover): attempt 1 → 0.8, attempt 2 → 0.6, attempt 3 → 0.5.

---

## 4. LLM Eval Call

Один reusable function для всех gates:

```python
EVAL_GATES = {
    "start_frame_prompt": {
        "criteria": [
            {"name": "visual_clarity", "question": "..."},
            {"name": "composition", "question": "..."},
            {"name": "hook_potential", "question": "..."},
            {"name": "technical_feasibility", "question": "..."},
        ],
        "context_fields": ["concept", "research_brief"],
    },
    # ... аналогично для всех 7 gates
}


async def llm_eval(gate_name: str, artifact: str, context: dict, attempt: int) -> EvalResult:
    gate = EVAL_GATES[gate_name]

    # LLM возвращает JSON с per-criterion scores
    result = await openai_client.generate_json(
        prompt=f"Evaluate this {gate_name}:\n{artifact}\n\nContext:\n{context}\n\nScore each criterion 0-100.",
        model="gpt-4o-mini",   # eval = дёшево, не креативно
        temperature=0.3,        # детерминированное scoring
    )

    criteria = [CriterionScore(**c) for c in result["criteria"]]
    overall = sum(c.score for c in criteria) // len(criteria)
    weakest = min(criteria, key=lambda c: c.score)

    passed = overall >= PASS_THRESHOLD and all(c.score >= MIN_CRITERION for c in criteria)

    return EvalResult(
        passed=passed,
        overall_score=overall,
        criteria=criteria,
        weakest=weakest.name if not passed else None,
        feedback=f"'{weakest.name}' scored {weakest.score}: {weakest.feedback}" if not passed else "",
        attempt=attempt,
        raw_response=result,
    )
```

---

## 5. Producer State

Паттерн из `backend/app/services/template_generation_service.py` (step indexing, resumability).

```python
@dataclass
class ProducerState:
    # Input
    concept: str
    research_brief: dict
    knowledge_base: dict        # model selection, duration, variations

    # Промпты (после eval gates 1-4)
    start_frame_prompt: str | None = None
    end_frame_prompt: str | None = None
    video_prompt: str | None = None
    music_prompt: str | None = None

    # Meta (после eval gates 5-6)
    cta_meta: dict | None = None       # {title, description, tags, cta_text}
    direction: str | None = None       # "forward" | "reverse"

    # Generated media (без eval)
    start_frame_url: str | None = None
    end_frame_url: str | None = None
    video_url: str | None = None
    music_url: str | None = None

    # Final
    final_video_path: str | None = None

    # Eval history
    eval_results: dict[str, EvalResult] = field(default_factory=dict)

    # Pipeline control
    current_step: str = "start_frame_prompt"
    status: str = "running"     # running | completed | failed
```

### Pipeline steps (sequential)

```
 1. start_frame_prompt      → eval_loop → state.start_frame_prompt
 2. start_frame_generation  → fal.ai    → state.start_frame_url       [NO EVAL]
 3. end_frame_prompt        → eval_loop → state.end_frame_prompt
 4. end_frame_generation    → fal.ai    → state.end_frame_url         [NO EVAL]
 5. video_prompt            → eval_loop → state.video_prompt
 6. video_generation        → fal.ai    → state.video_url             [NO EVAL]
 7. music_prompt            → eval_loop → state.music_prompt
 8. music_generation        → Lyria2    → state.music_url             [NO EVAL]
 9. cta_meta                → eval_loop → state.cta_meta
10. direction               → eval_loop → state.direction
11. hook_extraction         → FFmpeg    → trimmed audio               [DETERMINISTIC]
12. assembly                → FFmpeg    → merged video                [DETERMINISTIC]
13. cta_overlay             → FFmpeg    → video + text                [DETERMINISTIC]
14. reverse_if_needed       → FFmpeg    → final video                 [DETERMINISTIC]
15. final_eval              → eval_loop → state.eval_results["final"]
```

### Resumability

- `current_step` трекает прогресс
- State персистится после каждого шага (JSON файл)
- При падении — resume с `current_step`

---

## 6. Abort Policy

| Gate | При 3 фейлах |
|------|--------------|
| Gates 1-6 (промпты, meta) | Accept with notes, continue. Логируем warning. |
| Gate 7 (final assembly) | Reject если < 50. Accept with notes если >= 50. |

Агент не останавливает пайплайн из-за качества промптов — логирует и идёт дальше. Только финальная сборка может быть отклонена.

---

## 7. File Structure

```
backend/app/agent/
├── __init__.py
├── producer.py          # LangGraph agent, state, graph
├── eval.py              # EvalResult, CriterionScore, eval_loop(), llm_eval()
├── gates.py             # EVAL_GATES config (критерии для каждого gate)
├── tools/
│   ├── __init__.py
│   ├── prompt_tools.py  # generate_*_prompt() functions
│   ├── media_tools.py   # fal.ai wrappers (image, video, music)
│   └── ffmpeg_tools.py  # hook_extraction, assembly, overlay, reverse
└── state.py             # ProducerState dataclass
```

Переиспользует: `OpenAIClient`, `FalClient`, `media_processor`, `HookAnalyzer`.

---

## 8. Cost Estimate

При ~1.5 avg attempts per eval gate:

| Компонент | Стоимость |
|-----------|-----------|
| Image generation (start + end) | ~$0.10 |
| Video generation (Veo 3.1) | ~$1.60 |
| Music generation (Lyria2) | ~$0.10 |
| LLM generation (7 gates x 1.5 attempts) | ~$0.02 |
| LLM eval (7 gates x 1.5 attempts) | ~$0.01 |
| **Итого** | **~$1.83** |

Eval стоимость пренебрежимо мала с gpt-4o-mini.

---

## 9. Existing Patterns

| Паттерн | Файл | Что берём |
|---------|------|-----------|
| Eval loop (criteria, threshold, iterate on weakest) | `experiments/paint-mixing/research-algorithm.md` | Структура loop |
| Feedback + regeneration | `backend/app/core/music_generator.py:45-60` | `feedback` + `previous_prompt` |
| Quality gate (score >= 80) | `backend/app/services/discover_service.py:165-170` | Threshold gating |
| Resumable pipeline | `backend/app/services/template_generation_service.py:101-127` | Step indexing |
| Dataclass + scoring | `backend/app/core/hook_analyzer.py:21-34` | EvalResult |
| LLM JSON generation | `backend/app/services/openai_client.py` | `generate_json()` |

---

## Не входит в эту спеку

- Vision model eval (отдельная спека, после MVP)
- LangGraph граф (отдельная спека)
- Knowledge base формализация (отдельно)
- Trend detection, publishing, analytics (отдельные компоненты)
