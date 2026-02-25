# Paint Mixing v4 — Olympic Medals → Deep Teal Shimmer

Concept: Three Olympic medals (gold, silver, bronze) melt and mix like paint. Unexpected result: deep teal metallic with gold shimmer.

## Hook Analysis

- **Концепт:** Olympic medals (узнаваемые объекты) + "impossible satisfying" (медали плавятся как краска)
- **Pattern interrupt:** мозг видит медали (знакомое) + они жидкие (неожиданное)
- **Text overlay:** "What color do Olympic medals make?"
- **Timing:** Winter Olympics Milan Cortina 2026 (6-22 feb) — пик интереса
- **Surprise:** ожидают тёплый bronze/copper → получают cold teal с gold shimmer

## Structure (8s)

```
[0s]     3 медали на тёмной поверхности, вид сверху
[1-3s]   Медали начинают плавиться в металлические лужицы
[3-6s]   Палетт-найф смешивает три жидких металлика
[6-8s]   Uniform deep teal metallic с gold shimmer
→ loop
```

## Pipeline

| Step | Model | Prompt | Result |
|------|-------|--------|--------|
| Start frame | Nano Banana Pro | `prompts/start-frame.md` | `results/frames/` |
| End frame | Nano Banana Pro /edit | `prompts/end-frame.md` | `results/frames/` |
| Video | Veo 3.1 8s | `prompts/video.md` | `results/video/` |
| Music | Lyria2 + hook 8s | `prompts/music.md` | `results/music/` |
| Assembly | FFmpeg | `scripts/assemble.py` | `results/final/` |

## Eval Gates (из SPEC-agent-eval-loop)

Threshold: overall >= 80 AND каждый критерий >= 65. Max 3 attempts на gate.

**Принцип из спеки:** Gates 1-6 оценивают ПРОМПТЫ (текст). Media генерации (image, video, music) — БЕЗ eval. Только Gate 7 оценивает финальную сборку.

### Gate 1: Start Frame Prompt

Оценивается ПРОМПТ перед отправкой в Nano Banana Pro.

| Критерий | Вопрос | Pass |
|----------|--------|------|
| Visual Clarity | Сцена однозначна? Image model отрендерит медали без додумывания? | |
| Composition | Ракурс (top-down flat lay), кадрирование, 9:16 указаны? | |
| Hook Potential | Описанный первый кадр остановит скролл? Контраст, чёткий subject? | |
| Technical Feasibility | Совместимо с Nano Banana Pro? Нет невозможных элементов? | |

### Gate 2: End Frame Edit Prompt

Оценивается ПРОМПТ для /edit перед отправкой.

| Критерий | Вопрос | Pass |
|----------|--------|------|
| Continuity | Явно указано сохранить поверхность, руку, освещение, камеру? | |
| End State Clarity | Целевое состояние однозначно ("deep teal metallic", не "mixed")? | |
| Negative Constraints | Явно указано что НЕ менять и чего НЕ должно быть (no medals, no ribbons)? | |
| Edit Scope | Минимальный скоуп — только медали → краска, ничего структурного? | |

### Gate 3: Video Prompt

Оценивается ПРОМПТ перед отправкой в Veo 3.1.

| Критерий | Вопрос | Pass |
|----------|--------|------|
| Motion Clarity | Движение (melting + mixing) описано как чёткое действие с началом и концом? | |
| Pacing | Описание не перегружено для 8s? Одно основное действие? | |
| Model Compatibility | Использует правильные паттерны для Veo 3.1 (Subject/Motion/Camera)? | |
| Narrative Arc | Есть hook (medals) → process (melting) → payoff (teal shimmer)? | |

### Gate 4: Music Prompt

Оценивается ПРОМПТ перед отправкой в Lyria2.

| Критерий | Вопрос | Pass |
|----------|--------|------|
| Mood Match | Настроение (ambient metallic) совпадает с видео? | |
| Specificity | Конкретные термины (BPM, инструменты) vs размытые описания? | |
| Duration Fit | Энергетическая арка подходит под 8s? | |
| Safety | Нет unsafe/blocked слов для fal.ai? | |

### Gate 5: CTA + Meta

| Критерий | Вопрос | Pass |
|----------|--------|------|
| Title Formula | Следует паттерну ("What color do X make?")? Вызывает curiosity? | |
| CTA Alignment | Text overlay совпадает с темой title/description? | |
| Tag Relevance | Теги высокочастотные + Olympic timing теги для discovery? | |
| Engagement Hook | Создаёт curiosity gap или call to action? | |

### Gate 6: Forward vs Reverse

| Критерий | Вопрос | Pass |
|----------|--------|------|
| Content Fit | Концепт выигрывает от reverse ("unmixing" medals)? | |
| Audio Compatibility | Forward audio поверх reverse video имеет смысл? | |
| CTA Adjustment | CTA адаптирован под выбранное направление? | |
| **Decision** | **Forward** — melting medals = "impossible" hook, reverse потеряет этот момент | |

---

**Media генерации (image, video, music) — БЕЗ eval gate.** Качество визуала оценивается человеком. Vision model eval — отдельная спека, после MVP.

---

### Gate 7: Final Assembly

Единственный gate который оценивает РЕЗУЛЬТАТ (собранное видео).

| Критерий | Вопрос | Pass |
|----------|--------|------|
| Coherence | Все части (video, music, CTA) рассказывают одну историю? | |
| Timing | Music hook совпадает с video action? CTA читаем и по таймингу? | |
| Quality Bar | Пройдёт на YouTube Shorts? Не obviously broken? | |
| Publishability | Нет артефактов, нет audio desync, правильный encoding? | |

**Abort policy:** Gates 1-6 при 3 фейлах — accept with notes, continue. Gate 7 при score < 50 — reject.

## Meta

See `meta.md` for YouTube title, description, tags.

## Target Metrics

Based on v3b (best performer: 58.7% Viewed, 83% APV):
- **Viewed%:** >60% (stronger hook concept + Olympic timing)
- **APV:** >100% (short 8s format + loop)
- **Views 24h:** >1K (improvement over v3b trajectory)
