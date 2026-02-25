# Multi-Scene Narrative Format

**Статус:** Идея, не протестирована
**Источник:** Анализ Jack Craig tutorial (AI Shorts viral in 7 days) + обсуждение 2026-02-12
**Связь:** Гипотезы Q1 2026, пункты 3 (micro-narrative) и 4 (research pipeline)

---

## Суть

Сдвиг единицы контента: от single-scene satisfying к multi-scene story-driven animated shorts.

| | Текущий подход | Предлагаемый |
|--|----------------|-------------|
| **Единица** | 1 сцена, 6-10 сек | 3-5 сцен, 20-45 сек |
| **Тиражируем** | Тему × вариативные объекты | Визуальный стиль × вариативные сценарии |
| **Нарратив** | Нет (чистый визуал) | S-curve с конфликтом |
| **Pipeline** | prompt → image → video → trim | сценарий → keyframes → N × (image → video) → stitch |

---

## Production Pipeline (концепт)

1. **Сценарий** — LLM генерит s-curve with conflict (hook → rise → conflict → comeback → payoff)
2. **Визуальный стиль** — few-shot референсы, фиксированы на уровне "канала/бренда"
3. **Keyframes** — LLM описывает каждую сцену: first frame + last frame
4. **Генерация** — last_frame(N) = first_frame(N+1), image gen → video gen per scene
5. **Сборка** — FFmpeg stitch + sound design + music

---

## Story Structures (из Craig tutorial)

- **Linear:** hook → action → payoff (слабая, но простая)
- **Conflict arc:** hook → rise → conflict → comeback → rise → payoff (доказано сильнее)
- **Looped arc:** два конфликта (ещё сильнее, но сложнее)

Craig доказал: conflict arc → 88% retention на 43-сек видео, 150K views за 16 дней на новом канале.

---

## Оценка

### Однозначно за
- **Engagement** — conflict arc = непредсказуемость = retention. Доказано кросс-нишево
- **Brand building** — визуальный стиль = узнаваемый бренд, сложнее скопировать чем тему
- **Content fatigue** — вариативные сценарии, 60 видео/мес без повторов
- **Нишевание** — стиль отвязан от темы, можно менять нишу сохраняя бренд

### Главные риски
- **Fail rate** — больше сцен = больше точек отказа. При 25% брака на сцену и 4 сценах → ~68% что хотя бы одна плохая
- **Стоимость** — $2-3.25 за попытку (×3-5 от текущей). Экономика сходится при fail rate ≤30%
- **Консистентность стиля** — AI drift между сценами. Few-shot помогает, но video gen добавит расхождения

### Митигация рисков
- Перегенерация отдельной сцены, не всего ролика (архитектурное решение)
- Few-shot style lock на image gen
- Жёсткая модерация (но bottleneck смещается на модерацию)

---

## Операционные инсайты из Craig

- **Upload cadence:** первые 5 видео — минимум 48ч между загрузками, ждать <100 views/час 12ч+
- **Discovery phase:** первое видео почти всегда слабое (YouTube учится). Второе — показательное
- **"Original ideas don't win. Better execution does."** — находить что работает → комбинировать по-новому
- **AI content risk:** держать темы реалистичными, избегать novelty-based content (быстро теряет appeal)
- **Research method:** разбор топ-видео по сценам, поиск engagement outliers (comments/likes), вытаскивание proven элементов

---

## Open Questions

1. **Какую нишу брать для первого Discover-теста?** — определит стиль, сценарии, аудиторию
2. **Research pipeline** — как систематизировать поиск proven элементов для комбинирования?
3. **Длина оптимальная:** 20 сек? 40 сек? Зависит от retention vs replay tradeoff
4. **Параллельно или вместо?** — multi-scene как второй формат или замена satisfying

---

**Created:** 2026-02-12
