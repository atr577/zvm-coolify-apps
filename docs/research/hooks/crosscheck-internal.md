# Кроссчек: hooks research vs наши внутренние данные

**Дата:** 2026-02-18

Сверка выводов hooks-ресерча с тем что мы уже знаем из собственных экспериментов, гипотез, и ресерчей.

---

## Источники для кроссчека

| Документ | Что внутри |
|----------|-----------|
| `docs/knowledge/viral-shorts-mechanics.md` | Предыдущий ресерч по Shorts механикам (17+ поисков, февраль 2026) |
| `docs/hypotheses-q1-2026.md` | Гипотезы: audio hooks, loops, timing |
| `docs/ideas/motion-hooks.md` | Концепция motion hooks (из реальных данных канала) |
| `experiments/paint-mixing/README.md` | Результаты paint mixing эксперимента |
| `docs/ideas/vision-content-machine.md` | Vision: 35 каналов, unit economics |
| `docs/ideas/multi-scene-narrative.md` | Идея перехода к multi-scene формату |
| `docs/ideas/trending-subjects.md` | Идея trending subjects |
| `docs/GOALS.md` | Target: 10M views, 60 видео/мес, ≤$4/unit |
| `memory/paint-mixing-insights.md` | Инсайты из эксперимента |

---

## 1. Длительность — КОНФЛИКТ трёх источников

| Источник | Рекомендация |
|----------|-------------|
| **Hooks research** | 15-20 сек (satisfying), НО 50-60 сек даёт +85% views |
| **viral-shorts-mechanics.md** | 15-30 сек, max virality 11-18 сек |
| **paint-mixing-insights.md** | 8-10 сек sweet spot (из опыта генерации) |
| **Реальные данные канала** | 6-11 сек ролики, retention >100% |
| **multi-scene-narrative.md** | 20-45 сек с conflict arc, 88% retention у Craig |

**Анализ:**
- Наши реальные данные (6-11 сек) и insights (8-10 сек) — самые короткие из всех рекомендаций
- НО: при 6-11 сек max views = 1.9K. Канал НЕ прошёл seed тест (views <100 на нескольких)
- Проблема может быть **не в длительности, а в хуке** (swipe-away >80% — из motion-hooks.md)
- Craig data: 43 сек + conflict arc = 150K views. Другой формат, но сильный контрпример к "короче = лучше"

**Вывод:**
Три конкурирующих теории:
1. **Короткое + loop** (6-15 сек) — max replay, высокий AVD%. Наш текущий подход
2. **Среднее + hook** (15-30 сек) — баланс retention и watch time
3. **Длинное + narrative** (40-60 сек) — max absolute views, max watch time

**Ни одна не доказана для нашего формата.** Нужен A/B. Гипотеза H4 (loop) тестирует вариант 1. Нет гипотезы для вариантов 2 и 3.

**Рекомендация:** добавить гипотезу H6: длительность 40-55 сек vs 15-20 сек vs текущие 8-10 сек.

---

## 2. Swipe-away — подтверждение главной проблемы

| Источник | Данные |
|----------|--------|
| **Hooks research** | Target: >75% viewed, <25% swipe |
| **motion-hooks.md** | Реальные данные канала: **>80% swipe-away** |
| **motion-hooks.md** | Retention у оставшихся: 113-1866% (!) |

**Анализ:**
Это **идеальная валидация** выводов hooks-ресерча:
- Контент залипательный (retention >100% — люди пересматривают)
- Хук провальный (>80% свайпают в первые секунды)
- Диагноз из motion-hooks.md совпадает с ресерчем: **первые 1-2 сек решают всё**

**Конкретные цифры:** при 80% swipe-away → видео получает 20% потенциальных views. Снижение до 25% swipe = **4x рост views** при тех же расходах.

**Это наш #1 рычаг.** Все остальные оптимизации вторичны.

---

## 3. Motion hooks гипотезы vs hooks research

| Гипотеза (motion-hooks.md) | Поддержка из hooks research |
|-----------------------------|----------------------------|
| HK1: Reverse Reveal — результат первым | **Сильная.** "Result-first hook" в топ-3 для satisfying. Rank #2 в нашем ранжировании |
| HK2: Audio Drop — резкий звук 0.3 сек | **Косвенная.** 80% смотрят на mute → audio hook попадёт только в 20% аудитории. НО: те 20% — сильный сигнал |
| HK3: Контрастный первый кадр | **Сильная.** Visual pattern interrupt = rank #1 для satisfying |
| HK4: Text Hook | **Сильная.** Text overlay 3-6 слов = обязательный элемент для 80% mute viewers |
| HK5: Speed Ramp | **Не найдено.** Ни один источник не упоминает speed ramp как хук |
| HK6: Zoom-in от макро | **Косвенная.** "Extreme close-ups work well (hides AI imperfections)" — но как opening, не как zoom |

**Пересмотр приоритетов:**

| Было | Стало (после кроссчека) |
|------|------------------------|
| HK1 + HK2 = P0 | HK1 (reverse) + HK3 (контраст) + HK4 (text) = **P0** |
| HK3, HK4, HK5 = P1 | HK2 (audio) = P1 (только 20% аудитории) |
| HK6 = P2 | HK5 (speed ramp), HK6 (zoom) = P2 (не подтверждены) |

**Ключевое:** Audio hook (HK2) переоценён. 80% mute → visual+text важнее.

---

## 4. Audio hooks гипотеза H1 vs hooks research

| H1 (hypotheses-q1) | Hooks research |
|---------------------|---------------|
| Audio hook разнообразие > один хук | Подтверждено: monotonous формат деградирует (Sand Tagious кейс) |
| Один хук на все 60 видео = "привыкает" | Подтверждено: YouTube пенализирует repetitive content |
| 3 разных хука × ротация | Research: A/B testing × 3 варианта — рекомендуется |

**НО:** hooks research показал что 80% на mute → audio hook попадёт только в 20%. Это значит:
- Audio rotation всё ещё важна (для тех 20%)
- НО: visual hook rotation **критичнее** и не заложена в гипотезы

**Рекомендация:** H1 остаётся, но добавить **H1b: visual hook rotation** — 3 разных первых кадра для одного концепта.

---

## 5. Loop гипотеза H4 vs hooks research

| H4 (hypotheses-q1) | Hooks research |
|---------------------|---------------|
| Seamless loop = множитель views | **Надёжно подтверждено** (crosscheck.md) |
| С марта 2025: replay = view | Подтверждено, multiple sources |
| Crossfade vs Reverse vs First=Last | Research: все три варианта рабочие |
| "views/engagedViews ratio" как proxy | Подтверждено: YouTube разделил views и engaged views |

**Валидация полная.** H4 — одна из самых надёжных гипотез. Приоритет HIGH обоснован.

**Дополнение из кейсов:** Sand Tagious (3.36B views) = loop-first контент. Zach King = loop master.

---

## 6. Unit economics — столкновение с реальностью

| Метрика | GOALS.md | Hooks research (channel-cases.md) |
|---------|----------|----------------------------------|
| Target views | 10M / 3 мес | Faceless Shorts: 1.1M за 157 дней (Kapwing case) |
| Avg views/video | 100K (стандарт) | 19K (Kapwing), 106K (Sand Tagious avg, но declining) |
| Cost per published | ≤ $4 | $1.80 (paint mixing), $0.66 (Kling) |
| Revenue per 1M views | — | **$30-200** (Shorts RPM) |
| Монетизация порог | — | 10M views / 90 дней ИЛИ 1K subs + 4K watch hours |

**Критический конфликт:**

1. **Revenue при 10M views = $300-2,000.** Это при RPM $0.03-0.20. Vision document предполагает $500/мес/канал при 10M/мес. Реалистично: **$300-500**.

2. **100K avg views/video — амбициозно.** Kapwing (не satisfying) = 19K avg. Sand Tagious (7.5M subs, mature) = 106K avg, declining. Для нового канала **30-50K avg — более реалистичный target**.

3. **При 30K avg × 60 videos = 1.8M/мес = 5.4M за 3 мес.** Попадает в Go зону (≥5M), но не в 10M. Нужны viral outliers.

4. **Модель распределения из GOALS.md:**
   - 30% фейлы (1K) + 60% стандарт (100K) + 10% топ (1M)
   - Это предполагает 36 видео по 100K — оптимистично для нового канала
   - Более реалистично: 40% фейлы + 50% стандарт (30-50K) + 10% outliers

**Вывод:** GOALS.md модель оптимистична. Но Go/No-Go на 5M (не 10M) — достижимо.

---

## 7. "Impossible satisfying" стратегия S1 vs research

| S1 (hypotheses-q1) | Hooks research |
|---------------------|---------------|
| AI создаёт невозможные трансформации | **Подтверждённый тренд 2025-2026** (AI impossible scenarios) |
| Лучше satisfying + impossible | Research: "AI может создать то, что камера не снимет" = конкурентное преимущество |
| Реалистичные люди = uncanny valley | Подтверждено: satisfying/ASMR ниша = faceless, без людей |

**Полная валидация.** S1 — правильная стратегия. Research добавляет конкретные примеры: стеклянные фрукты, самоцветный джем, молоко-мороженое.

---

## 8. Multi-scene narrative vs satisfying-only

| multi-scene-narrative.md | Hooks research |
|--------------------------|---------------|
| 20-45 сек, conflict arc | Research: 50-60 сек = +85% views (channel-cases.md) |
| 88% retention у Craig | Research: satisfying без narrative = 80-90% retention |
| Fail rate: ~68% при 4 сценах | Не адресовано в research |
| Стоимость: $2-3.25/попытка | В рамках $4 target |

**Анализ:**
- Multi-scene даёт narrative arc → длиннее → потенциально больше absolute views
- НО: satisfying без narrative уже имеет 80-90% retention → narrative не обязателен для retention
- Multi-scene решает проблему **content fatigue** (Sand Tagious decline) — вариативность
- Цена × fail rate = рискованнее, но в рамках бюджета

**Вывод:** Multi-scene — не замена satisfying, а **дополнительный формат для вариативности.** Не либо/либо.

---

## 9. Trending subjects vs research findings

| trending-subjects.md | Hooks research |
|----------------------|---------------|
| Trending subject в title/tags = boost | Research: **"CTR irrelevant for Shorts"** (autoplay). Tags = irrelevant (1-2% cases) |
| SEO трафик | Research: 74% views от non-subscribers через feed, не search |
| Discovery через тренды | Research: discovery = algorithmic, не search-based |

**Конфликт:** Trending subjects были оценены как "тестируемо" в ideas doc. Но hooks research показывает что для Shorts SEO/search/tags практически не работают — 90%+ трафика из feed.

**Пересмотр:** Trending subjects могут работать не через SEO, а через **algorithmic categorization** — YouTube может пушить trending-тему шире. Но доказательств этому нет.

**Вердикт:** Приоритет trending subjects СНИЖЕН. Тестировать можно (zero cost), но не ожидать значимого impact.

---

## 10. Текущие данные канала (7 видео) vs benchmarks

| Метрика | Наш канал | Benchmark (research) |
|---------|-----------|---------------------|
| Views best | 1,518 (лев) | 216K (Kapwing best) |
| Views avg | 50-88 | 19K (Kapwing avg) |
| Swipe-away | >80% | Target: <25% |
| Retention (у оставшихся) | 113-1866% | 80-90% (satisfying avg) |
| Videos published | 7 | 30-40 до traction (research) |
| Duration | 6-11 сек | 15-30 сек (research), 50-60 (views max) |

**Диагноз:** Канал в **pre-traction фазе** (7 видео, нужно 30-40 для алгоритма). Главная проблема = хук (>80% swipe). Контент quality подтверждён retention >100%.

**30-40 видео — критическая масса.** До этого рано делать выводы о формате/нише.

---

## Сводная таблица: что подтвердилось, что пересмотреть

### Подтверждено

| Что | Где подтверждено |
|-----|-----------------|
| Хук = #1 проблема, контент ок | motion-hooks.md (>80% swipe, >100% retention) |
| Loop = сильный рычаг | H4 + множество внешних источников |
| Impossible satisfying = правильная стратегия | S1 + AI ASMR тренд |
| Вариативность обязательна | Sand Tagious decline + YouTube repetitive policy |
| 30-40 видео = минимум для оценки | Faceless growth data |
| Reverse reveal = top hook для нас | HK1 + hooks research rank #2 |

### Пересмотреть

| Что | Было | Стало |
|-----|------|-------|
| **Audio hook приоритет** | P0 (HK2) | P1 — 80% на mute, visual важнее |
| **Длительность 6-11 сек** | Текущий default | Тестировать 15-20 и 40-55 сек тоже |
| **Trending subjects** | "Тестируемо" | Приоритет снижен — SEO/tags ~irrelevant для Shorts |
| **100K avg views target** | GOALS.md модель | 30-50K реалистичнее для нового канала |
| **Revenue model** | $500/мес при 10M views | $300-500, RPM $0.03-0.20 |

### Новые гипотезы (добавить)

| ID | Гипотеза | Обоснование |
|----|----------|-------------|
| H1b | Visual hook rotation (3 разных первых кадра) | 80% mute → visual > audio |
| H6 | Duration A/B: 8-10 vs 15-20 vs 40-55 сек | Противоречивые данные, нет ответа без теста |
| H7 | Text overlay в первые 2 сек | 80% mute, captions +10-15% retention |
| H8 | Multi-scene как % от batch | Вариативность vs fail rate tradeoff |

---

## Главные выводы

1. **Хук — это 80% успеха.** Наши данные подтверждают: контент залипательный, хук убивает. Все усилия на первые 1.5 сек.

2. **Visual > Audio.** 80% на mute = audio хук попадёт в 20%. Пересмотреть приоритет HK2 и H1.

3. **Длительность — открытый вопрос.** Три конкурирующих теории, ни одна не доказана для нашего формата. Нужен A/B.

4. **30-40 видео до оценки.** Мы на 7. Рано делать выводы. Но хук надо фиксить уже сейчас.

5. **Unit economics реалистичнее чем казалось** ($1.80/видео, $4 ceiling), но **revenue оптимистичнее чем есть** (Shorts RPM = $0.03-0.20, не $0.50).

---

## Источники

Внутренние:
- `docs/knowledge/viral-shorts-mechanics.md`
- `docs/hypotheses-q1-2026.md`
- `docs/ideas/motion-hooks.md`
- `experiments/paint-mixing/README.md`
- `docs/ideas/vision-content-machine.md`
- `docs/ideas/multi-scene-narrative.md`
- `docs/ideas/trending-subjects.md`
- `docs/GOALS.md`

Внешние:
- `docs/research/hooks/crosscheck.md`
- `docs/research/hooks/channel-cases.md`
