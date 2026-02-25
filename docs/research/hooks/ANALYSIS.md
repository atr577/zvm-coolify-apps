# Хуки для YouTube Shorts — аналитический документ

**Дата:** 2026-02-18 (v2 — после кроссчеков)
**Контекст:** REGGY — AI-генерация коротких видео (satisfying/process формат). Цель: 10M views за 3 месяца.

---

## Executive Summary

Хук — первые 1-3 секунды видео — определяет 80%+ судьбы Short. Наши собственные данные это подтверждают: retention >100% (контент залипательный), но swipe-away >80% (хук провальный). Фикс хука = потенциально 4x рост views при тех же расходах.

Этот документ прошёл два раунда кроссчека: против внешних источников (слабые данные отсеяны) и против наших собственных экспериментов/гипотез (конфликты выявлены и разрешены).

**Что надёжно:** visual hook > audio hook, loop работает, вариативность обязательна.
**Что не доказано:** оптимальная длительность (три конкурирующих теории), точные % от техник.
**Что пересмотрено:** приоритет audio hooks снижен, длительность 6-11 сек под вопросом, revenue model скорректирована.

---

## 1. Как работает воронка YouTube Shorts

```
Показ в ленте (impression)
    ↓ [1-2 сек: Viewed vs Swiped Away]
Seed audience test (1K-10K views)
    ↓ [цель: >75% viewed — НАДЁЖНЫЙ benchmark]
Расширение охвата (exploit)
    ↓ [3 сек: intro retention — сравнивать с собой, не абсолют]
Середина видео
    ↓ [visual cuts каждые 2-4 сек]
Завершение
    ↓ [completion rate >60%]
Loop/replay
    ↓ [AVD >100% = надёжно подтверждённый сигнал]
Расширение на новые аудитории
```

**Наша узкая точка:** этап 1. >80% свайпают — видео не проходит seed тест, не получает шанса показать залипательный контент.

### Что подтверждено, что нет

| Утверждение | Статус | Примечание |
|-------------|--------|-----------|
| >75% viewed = target | **Надёжно** | Несколько независимых источников сходятся |
| 50-60% drop-off в первые 3 сек | **Слабый источник** | Цитируется повсеместно, оригинал не найден |
| Loop/AVD >100% помогает | **Надёжно** | Включая официальные YouTube данные |
| Первые 24 часа решают всё | **МИФ** | Видео может "проснуться" через месяцы |
| CTR irrelevant для Shorts | **Надёжно** | Autoplay в feed, нет клика |
| Tags влияют на discovery | **Почти нет** | 1-2% случаев по данным YouTube |

---

## 2. Какие хуки работают для нашего формата

### Наш формат: satisfying/process, faceless, без голоса

80% зрителей на mute → **visual + text = единственный хук**. Audio попадёт в 20% аудитории.

Это ключевой пересмотр после кроссчека: audio hook (HK2 из motion-hooks.md) был P0, стал P1.

### Ранжирование хуков (обновлённое)

| Ранг | Тип хука | Реализация | Надёжность данных |
|------|----------|-----------|-------------------|
| 1 | **Visual Pattern Interrupt** | Яркий контраст + движение с frame 1 | Высокая (множество источников + наши данные) |
| 2 | **Reverse Reveal** | Результат первым → process назад | Высокая (HK1 из motion-hooks.md + research) |
| 3 | **Text Hook Overlay** | 3-6 слов, вопрос/вызов, первые 2 сек | Высокая (80% mute = text обязателен) |
| 4 | **Before/After** | Split или sequential: хаос → порядок | Средняя (proven format, нет наших данных) |
| 5 | **Impossible Scenario** | AI-only визуал (нереальные материалы) | Средняя (тренд 2025-2026, не тестировали) |
| 6 | **Audio Drop** | Резкий звук 0-0.3 сек | Средняя (только 20% аудитории, но сильный сигнал) |

### Что изменилось vs v1

| Было | Стало | Почему |
|------|-------|--------|
| Audio drop не в ранжировании | Rank 6 (был бы P0) | 80% mute → только 20% услышат |
| Text overlay = rank 4 | Rank 3 | 80% mute = text единственный способ донести message |
| Impossible scenario = rank 7 | Rank 5 | Подтверждён как тренд + наша стратегия S1 |
| "Question + Visual" отдельно | Объединён с Text Hook | Это одно и то же для нашего формата |

### Антипаттерны (подтверждены)
- Статичный первый кадр (наш текущий грех — swipe >80%)
- Одинаковый hook в серии (Sand Tagious decline)
- Текст >6 слов, мелкий шрифт
- Slow fade-in, чёрный фон

---

## 3. Длительность — ОТКРЫТЫЙ ВОПРОС

**Это главный конфликт в данных.** Три конкурирующих теории, ни одна не доказана для нашего формата.

| Теория | Длительность | Аргумент ЗА | Аргумент ПРОТИВ |
|--------|-------------|-------------|-----------------|
| **Короткое + loop** | 6-15 сек | Max replay, AVD >100%. Наши данные: 6-11 сек, retention >100% | Наши views = 50-88 avg. Не доказано что работает для discovery |
| **Среднее + hook** | 15-30 сек | Баланс retention и watch time. 80%+ retention по research | Нет наших данных. Generic benchmark, не satisfying-specific |
| **Длинное + narrative** | 40-60 сек | +85% absolute views (5,400 Shorts study). Craig: 88% retention на 43 сек | Completion падает. Другой формат (narrative vs pure satisfying) |

### Наши данные vs benchmarks

| Метрика | Наш канал (7 видео, 6-11 сек) | Benchmark |
|---------|-------------------------------|-----------|
| Avg views | 50-88 | 19K (Kapwing, faceless), 106K (Sand Tagious) |
| Retention | 113-1866% | 80-90% (satisfying avg) |
| Swipe-away | >80% | Target: <25% |

**Интерпретация:** наш контент удерживает (retention отличный), но не получает шанс (swipe убивает). Длительность может быть не виновата — виноват хук. Но и 6 сек слишком мало для watch time accumulation.

**Решение:** A/B тест (новая гипотеза H6). Три группы: 8-10 / 15-20 / 40-55 сек. По 10+ видео на группу. Метрика: views × completion rate.

---

## 4. Метрики и targets (скорректированные)

### Основные KPI

| Метрика | Target | Красная зона | Надёжность benchmark |
|---------|--------|-------------|---------------------|
| Viewed vs Swiped Away | >75% | <50% | **Высокая** |
| Completion rate | >60% | <40% | **Средняя** (зависит от длины) |
| AVD >100% (loop rate) | >20% видео | <5% | **Высокая** |

### Метрики с оговорками

| Метрика | Target из research | Оговорка |
|---------|-------------------|----------|
| Intro retention (3 сек) | >70% | Сравнивать с собой, не абсолют. Shortimize прямо отказывается давать single-number benchmark |
| Pattern interrupt +23% | — | **Одна статья OpusClip, не верифицировано.** Направление верное, % фейковый |
| Open loops +32% | — | **Одна статья, не верифицировано.** То же самое |
| Captions +15-25% | +10-15% (реалистичнее) | Маркетинговые блоги, нет первоисточника. Помогают — да, но точный % unknown |

### Вторичные метрики

| Метрика | Значимость для satisfying | Примечание |
|---------|--------------------------|-----------|
| Shares | Средняя | Satisfying шарят меньше чем funny/educational |
| Saves | **Высокая** | "Посмотреть ещё раз" — наша ниша |
| Comments | Низкая | Sand Tagious: 0.03% comment rate — нормально для ниши |
| Like rate | Низкая | Sand Tagious: 0.34% — нормально |

**Вывод для нашей ниши:** retention и replay >>> engagement. Не пытаться оптимизировать comments/shares.

---

## 5. Наши данные vs реальные каналы

### Кейсы (из channel-cases.md)

| Канал | Формат | Subs | Avg views | Ключевой инсайт |
|-------|--------|------|-----------|-----------------|
| Sand Tagious | Kinetic sand, faceless | 7.5M | 106K (declining) | Один формат = degradation. Engagement minimal, views через discovery |
| Bella's ASMR | AI ASMR, long-form | 150K (3 мес) | 70-100K | AI контент работает. Но long-form (RPM $10-11 vs Shorts $0.03-0.20) |
| Kapwing case | Faceless Shorts | 1.2K (5 мес) | 19K | Не прошёл монетизацию. AI content flag. Честный baseline |
| tonesterpaints | Real paint mixing, TikTok | 1.4M TikTok | — | Paint mixing = proven format. Уволен за это. AI = advantage |

### Наш канал vs кейсы

| | Наш (7 видео) | Sand Tagious (882) | Kapwing (60) |
|--|---------------|-------------------|--------------|
| Avg views | 50-88 | 106K | 19K |
| Retention | >100% | ~80% (est) | Unknown |
| Swipe-away | >80% | Low (mature) | Unknown |
| Формат | Pure visual, 6-11 сек | Pure visual + audio | Faceless + AI voice |

**Мы в pre-traction фазе.** 30-40 видео = минимум для алгоритма. До этого — инвестиционная фаза.

---

## 6. Пересмотр стратегии (после кроссчеков)

### Что остаётся в силе

1. **Visual hook = #1 приоритет.** Наши данные подтверждают: контент ок, хук убивает
2. **Loop design** — надёжно подтверждён как рычаг (H4 валидна)
3. **"Impossible satisfying"** — правильная стратегия (S1 валидна), тренд 2025-2026
4. **Вариативность** — Sand Tagious decline + YouTube repetitive policy = обязательно
5. **Batch production** — наше конкурентное преимущество ($1.80/видео)

### Что пересмотрено

| Было (v1 / гипотезы) | Стало (v2) | Причина |
|----------------------|------------|---------|
| Audio hook = P0 (HK2) | **P1** | 80% на mute. Visual+text важнее |
| Duration = 15-20 сек default | **Открытый вопрос. A/B обязателен** | Данные противоречивы: 6-11 (наш), 15-30 (research), 50-60 (+85% views) |
| 100K avg views (GOALS.md) | **30-50K реалистичнее** для нового канала | Kapwing = 19K, Sand Tagious = 106K но mature & declining |
| Revenue $500/мес при 10M | **$300-500**, Shorts RPM $0.03-0.20 | Внешние данные по RPM жёсткие |
| Trending subjects = тестируемо | **Приоритет снижен** | SEO/tags irrelevant для Shorts, 90%+ из feed |
| НИКОГДА больше 30 сек | **Тестировать 40-55 сек** | Данные по 50-60 сек (+85% views) нельзя игнорировать |

### Новые гипотезы (добавить к H1-H5)

| ID | Гипотеза | Обоснование | Приоритет |
|----|----------|-------------|-----------|
| H1b | **Visual hook rotation** — 3 разных первых кадра для одного концепта | 80% mute → visual > audio. Дополняет H1 (audio rotation) | HIGH |
| H6 | **Duration A/B:** 8-10 vs 15-20 vs 40-55 сек | Три конкурирующих теории, ни одна не доказана | HIGH |
| H7 | **Text overlay в первые 2 сек** — вопрос/обещание на первом кадре | 80% mute, captions +10-15% retention | HIGH |
| H8 | **Multi-scene (10-20% батча)** — conflict arc для вариативности | Sand Tagious decline. Craig 88% retention, 150K views | MEDIUM |

### Пересмотр приоритетов motion hooks (из motion-hooks.md)

| ID | Было | Стало |
|----|------|-------|
| HK1 (Reverse Reveal) | P0 | **P0** — подтверждён |
| HK2 (Audio Drop) | P0 | **P1** — только 20% аудитории |
| HK3 (Контрастный кадр) | P1 | **P0** — visual pattern interrupt = #1 |
| HK4 (Text Hook) | P1 | **P0** — 80% mute, text обязателен |
| HK5 (Speed Ramp) | P1 | **P2** — не подтверждён ни одним источником |
| HK6 (Zoom-in) | P2 | **P2** — косвенные данные, не доказан |

**Итого P0: HK1 + HK3 + HK4.** Reverse reveal + яркий контраст + text overlay. Комбинировать и тестировать первыми.

---

## 7. Конкретные рекомендации по производству

### Первый кадр (frame 1)
- **ВСЕГДА яркий цвет** на контрастном фоне
- **ВСЕГДА движение** — не статика (наш текущий грех)
- **Результат или пик процесса** — не начало (reverse reveal)
- **Text overlay** 3-6 слов, крупный шрифт, контрастный, в safe zone

### Структуры видео (тестировать все три)

**A. Короткое loop (8-15 сек)**
```
[0-2 сек]  HOOK: reverse reveal (результат) + text
[2-8 сек]  PROCESS: трансформация
[8-10 сек] PAYOFF: результат hold
[→ LOOP]   Seamless → начало
```

**B. Среднее с hook (15-25 сек)**
```
[0-2 сек]  HOOK: яркий кадр + text overlay + movement
[2-5 сек]  SETUP: начало процесса
[5-18 сек] PROCESS: основной визуал, cut каждые 2-3 сек
[18-22 сек] PAYOFF: финальный результат (hold 2-3 сек)
[→ LOOP]   Seamless → начало
```

**C. Длинное с narrative (40-55 сек)**
```
[0-2 сек]  HOOK: impossible/wow кадр + text
[2-10 сек] SETUP: исходное состояние, что будет происходить
[10-35 сек] PROCESS: трансформация в 3-4 этапа, cuts, нарастание
[35-45 сек] CONFLICT: что-то идёт не так / неожиданный поворот
[45-50 сек] RESOLUTION: финальный wow-результат
[50-55 сек] HOLD + LOOP
```

### Text overlays (расширенный список)

| Формулировка | Когда | Тип хука |
|-------------|-------|----------|
| "Wait for it..." | Процесс с payoff | Curiosity |
| "Watch what happens" | Неожиданный результат | Curiosity |
| "Which color wins?" | Смешивание цветов | Question |
| "Can you guess?" | Непредсказуемый исход | Question |
| "You've never seen this" | AI impossible | Challenge |
| "This shouldn't be possible" | AI impossible | Pattern interrupt |
| "3 colors → 1 result" | Countdown | Structure |
| "The most satisfying thing today" | Прямое обещание | Direct promise |

---

## 8. Unit Economics (скорректированные)

### Стоимость производства

| Сценарий | Videos/мес | Published | Cost/published |
|----------|-----------|-----------|---------------|
| Без A/B | 90 | 60 | $2.70 |
| С visual A/B (×2 хука) | 120 | 60 | $3.60 |
| С visual A/B (×3 хука) | 180 | 60 | $5.40 (выходит за $4 ceiling) |

**×2 visual хука** — оптимальный баланс. $3.60/published, в рамках $4 target.

### Revenue (скорректированная)

| Views/мес | Revenue/мес (RPM $0.05) | Revenue/мес (RPM $0.20) |
|-----------|------------------------|------------------------|
| 1.8M (30K avg × 60) | $90 | $360 |
| 3.3M (55K avg × 60) | $165 | $660 |
| 6M (100K avg × 60) | $300 | $1,200 |

**Реалистичный сценарий:** 30-50K avg × 60 = 1.8-3M views/мес. Revenue: $90-660/мес.

**Честный вывод:** Shorts revenue при текущем RPM не покрывает даже production costs ($162-216/мес). Монетизация Shorts-only — не viable бизнес-модель. Value = **audience building + channel growth** для последующей long-form монетизации или brand deals.

### Path to monetization

| Порог | Требование | При 60 видео/мес, 30-50K avg |
|-------|-----------|-------------------------------|
| Shorts monetization | 10M views / 90 дней | 3.3M/мес = 10M/90 дней — **на грани** при 55K avg |
| YPP (alt) | 1K subs + 4K watch hours / 12 мес | Watch hours проблема при 15-сек Shorts |

---

## 9. Фазированный план

### Phase 1: Fix the hook (сейчас → +30 видео)

**Цель:** снизить swipe-away с >80% до <30%.

Действия:
- Внедрить P0 хуки: reverse reveal (HK1) + яркий контраст (HK3) + text overlay (HK4)
- Visual hook rotation: 2-3 варианта первого кадра на концепт
- Нарастить до 30-40 видео (traction point для алгоритма)

**Метрика успеха:** Viewed vs Swiped Away >60% (улучшение с текущих 20%)

### Phase 2: Duration A/B (+30 видео)

**Цель:** определить оптимальную длительность для нашего формата.

Действия:
- Три группы: 8-15 / 15-25 / 40-55 сек
- 10+ видео на группу
- Loop design для всех трёх
- Измерить: views, completion, AVD, viewed%

**Метрика успеха:** определена winning длительность (>2x views vs другие)

### Phase 3: Scale & diversify (+60 видео)

**Цель:** выйти на 3.3M views/мес (10M/90 дней для монетизации).

Действия:
- Winning hook + winning duration → основной формат
- 10-20% батча = multi-scene / impossible scenarios (вариативность)
- Cross-platform: YouTube + TikTok + Reels
- YouTube Analytics API → feedback loop

---

## 10. Открытые вопросы

| Вопрос | Как ответить |
|--------|-------------|
| Оптимальная длительность | H6 A/B тест |
| Reverse reveal "убивает удивление" или "создаёт curiosity"? | A/B reverse vs forward |
| AI content flag risk | Мониторить, вариативность, не mass-produce один шаблон |
| Когда добавлять long-form compilations? | После 100+ Shorts, если watch hours отстают |
| Trending subjects дают ли реальный boost? | Low-cost тест, но low priority |

---

## Заключение

**Три факта, подтверждённых и данными и кроссчеком:**

1. **Хук решает 80% успеха.** Наш контент работает (retention >100%), наш хук нет (swipe >80%). Visual + text > audio.

2. **Loop — самый надёжный рычаг.** Подтверждён множеством источников + логикой платформы (replay = views с марта 2025).

3. **Вариативность обязательна.** YouTube пенализирует repetitive, Sand Tagious declining, один формат = diminishing returns.

**Главная неопределённость:** длительность. 6-11 сек (наш текущий), 15-30 (generic advice), 40-60 (data says more views) — решается только A/B тестом.

**Честная оценка revenue:** Shorts-only = audience building, не revenue stream. RPM $0.03-0.20 не покрывает costs. Value = channel growth → long-form / brand deals / audience monetization.

---

*Полные данные: `hook-types.md`, `algorithm-metrics.md`, `ai-video-specifics.md`, `satisfying-niche.md`*
*Кроссчеки: `crosscheck.md` (внешний), `crosscheck-internal.md` (внутренний)*
*Кейсы: `channel-cases.md`*
