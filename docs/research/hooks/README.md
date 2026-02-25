# Hooks Research — YouTube Shorts

Глубокий ресерч по хукам для YouTube Shorts: типы, метрики, специфика AI-видео, применение к REGGY. Два раунда кроссчека (внешний + внутренний), реальные кейсы каналов, timeline-модель.

**Дата:** 2026-02-18

---

## Структура (8 документов)

| Файл | Содержимое |
|------|------------|
| `README.md` | Этот файл — навигация + финальное summary |
| `hook-types.md` | 18 шаблонов хуков, 3 базовые формулы, антипаттерны |
| `algorithm-metrics.md` | Explore/Exploit модель, Viewed vs Swiped, retention benchmarks |
| `ai-video-specifics.md` | YouTube vs AI-контент, 10 форматов, AI ASMR тренд |
| `satisfying-niche.md` | Психология (дофамин, Zeigarnik, зеркальные нейроны), формула satisfying |
| `crosscheck.md` | Кроссчек внешний: что подтвердилось, слабые источники, противоречия |
| `channel-cases.md` | Кейсы: Sand Tagious (7.5M subs), Bella's ASMR, Kapwing, tonesterpaints |
| `crosscheck-internal.md` | Кроссчек vs наши гипотезы H1-H5, motion-hooks.md, GOALS.md |
| `timeline-benchmarks.md` | Динамика метрик: 30мин → 3ч → 6ч → 12ч → 24ч, 5 сценариев |
| `ANALYSIS.md` | Аналитический документ v2 (после всех кроссчеков) |

---

## Финальное Summary

### Что мы точно знаем (подтверждено данными + кроссчеком)

**1. Хук решает 80% успеха. Наши данные это доказывают.**

Наш канал: retention >100% (люди пересматривают), но swipe-away >80% (8 из 10 уходят в первую секунду). Контент залипательный — хук мёртвый. Снижение swipe с 80% до 25% = **потенциально 4x рост views** при нулевых доп. расходах.

**2. Visual + Text > Audio. 80% зрителей на mute.**

Пересмотр после кроссчека: audio hook (HK2) был P0, стал P1. Для нашего faceless-формата хук = яркий первый кадр + текст-вопрос. Не звук.

**3. Loop — самый надёжный рычаг.**

Подтверждён множеством источников. С марта 2025 каждый replay = view. Seamless loop поднимает AVD >100% — сильнейший алгоритмический сигнал. Для satisfying-контента loop органичен.

**4. Вариативность обязательна.**

Sand Tagious (7.5M subs) на спаде после 882 видео одного формата. YouTube с июля 2025 пенализирует "mass-produced repetitive content". Один шаблон = diminishing returns + risk бана.

**5. "Impossible satisfying" — наше конкурентное преимущество.**

AI может создать то что камера не снимет: стеклянные фрукты, самоцветный джем, нереальные текстуры. Тренд 2025-2026. Совпадает с нашей стратегией S1.

**6. 30-40 видео = минимум до оценки.**

Faceless каналы набирают traction после 30-40 видео. Мы на 7. Рано делать выводы о формате — но хук надо фиксить уже сейчас.

### Что мы НЕ знаем (противоречивые данные)

**7. Оптимальная длительность — открытый вопрос.**

| Теория | Длительность | Данные ЗА |
|--------|-------------|-----------|
| Короткое + loop | 6-15 сек | Наш retention >100%, max replay |
| Среднее + hook | 15-30 сек | Generic research: 80%+ retention |
| Длинное + narrative | 40-60 сек | +85% абсолютных views (5,400 Shorts study) |

Ни одна не доказана для нашего формата. Решается только A/B тестом.

**8. Точные % от техник — не верифицированы.**

"+23% от pattern interrupt", "+32% от open loops", "+15-25% от captions" — цитируются повсюду, но первоисточники не найдены. Направления верные, конкретные числа — маркетинговый фольклор.

### Что пересмотрено (vs наши прежние гипотезы)

| Было | Стало | Почему |
|------|-------|--------|
| Audio hook = P0 | **P1** | 80% на mute |
| Duration = 6-11 сек | **A/B: 8-15 vs 15-25 vs 40-55** | Противоречивые данные |
| 100K avg views target | **30-50K** реалистичнее | Kapwing = 19K, Sand Tagious declining |
| Revenue $500/мес при 10M | **$90-660**, RPM $0.03-0.20 | Shorts RPM жёсткий |
| Trending subjects = тестируемо | **Приоритет снижен** | SEO/tags irrelevant для Shorts feed |
| "Никогда >30 сек" | **Тестировать 40-55** | Данные нельзя игнорировать |

### Новые гипотезы (добавить к H1-H5)

| ID | Что | Приоритет |
|----|-----|-----------|
| H1b | Visual hook rotation (3 разных первых кадра на концепт) | HIGH |
| H6 | Duration A/B: 8-15 vs 15-25 vs 40-55 сек | HIGH |
| H7 | Text overlay в первые 2 сек (вопрос/обещание) | HIGH |
| H8 | Multi-scene 10-20% батча (вариативность) | MEDIUM |

### Обновлённые приоритеты хуков

**P0 (делать первыми):**
- HK1: Reverse Reveal — результат в первом кадре
- HK3: Контрастный яркий первый кадр с движением
- HK4: Text overlay 3-6 слов ("Wait for it...", "Can you guess?")

**P1 (следующие):**
- HK2: Audio drop (для 20% не на mute)
- H1b: Visual hook rotation

**P2 (тестировать позже):**
- HK5: Speed ramp (не подтверждён)
- HK6: Zoom-in от макро (косвенные данные)

### Timeline-модель (чекпоинты)

| Чекпоинт | Ключевая метрика | Жив | Мёртв |
|-----------|-----------------|-----|-------|
| 30 мин | Viewed% | >60% | <30% |
| 3 ч | Trend views | Ускоряется, >500 | Flat, <200 |
| 6 ч | Абсолют views | >5K | <1K |
| 12 ч | Views/час | Растёт | Падает |
| 24 ч | Total | >50K → viral | <500 → dead (может проснуться) |

**Наши 7 видео = все Scenario A (dead on arrival).** Viewed% ~20%. Но retention >100% = контент ок.

### Unit economics (честная картина)

| Метрика | Значение |
|---------|----------|
| Cost per video | $1.80 (paint mixing, Veo) |
| Cost per published (35% reject + ×2 A/B) | $3.60 |
| Target: 60 published/мес | $216/мес production |
| Revenue при 3.3M views/мес (RPM $0.05) | $165/мес |
| Revenue при 3.3M views/мес (RPM $0.20) | $660/мес |

**Shorts-only = audience building, не revenue stream.** Revenue не покрывает costs при RPM $0.05. Value = channel growth → long-form / brand deals.

### Фазированный план

| Фаза | Что | Цель | Сколько видео |
|------|-----|------|--------------|
| 1 | Fix hook (P0: HK1+HK3+HK4) | Swipe-away <30% (с текущих >80%) | +30 |
| 2 | Duration A/B (H6) | Определить winning длительность | +30 |
| 3 | Scale + diversify | 3.3M views/мес, монетизация | +60 |

---

## Источники

### Первичный ресерч
- [vidIQ: 18 Viral Hook Ideas](https://vidiq.com/blog/post/viral-video-hooks-youtube-shorts/)
- [OpusClip: Hook Formulas](https://www.opus.pro/blog/youtube-shorts-hook-formulas)
- [OpusClip: Ideal Length & Retention](https://www.opus.pro/blog/ideal-youtube-shorts-length-format-retention)
- [Miraflow: 10 AI Formats](https://miraflow.ai/blog/ai-shorts-formats-that-go-viral-2026)
- [virvid.ai: 10 Hook Templates](https://virvid.ai/blog/ai-shorts-script-hook-ultimate-guide-2026)

### Алгоритм и метрики
- [vidIQ: Shorts Algorithm 2026](https://vidiq.com/blog/post/youtube-shorts-algorithm/)
- [Shortimize: Retention Rate](https://www.shortimize.com/blog/youtube-shorts-retention-rate)
- [Shortimize: Algorithm 2025](https://www.shortimize.com/blog/how-does-youtube-shorts-algorithm-work)
- [SocialRails: Audience Retention Benchmarks](https://socialrails.com/blog/youtube-audience-retention-complete-guide)

### Кейсы и данные каналов
- [Playboard: Sand Tagious](https://playboard.co/en/channel/UCMlSf7BCzfdRsIGAIpCnrXA)
- [CloneViral: AI ASMR Growth](https://www.cloneviral.ai/blog/ai-asmr-video-generator-youtube-growth-strategy)
- [Kapwing: Faceless Channel Case Study](https://www.kapwing.com/resources/we-grew-a-faceless-youtube-channel-to-1000-subscribers/)
- [YouTube Blog: Oddly Satisfying Videos](https://blog.youtube/culture-and-trends/youtube-oddly-satisfying-asmr-videos/)

### Психология и ниша
- [Paul Pope: Psychology of Satisfying Videos](https://paulpope.co.uk/why-oddly-satisfying-videos-captivate-us-a-psychological-view/)
- [Gyre: Algorithm Myths Debunked](https://gyre.pro/blog/youtube-algorithm-myths-in-what-actually-matters-for-growth)

### Внутренние документы
- `docs/knowledge/viral-shorts-mechanics.md`
- `docs/hypotheses-q1-2026.md`
- `docs/ideas/motion-hooks.md`
- `experiments/paint-mixing/README.md`
- `docs/GOALS.md`
