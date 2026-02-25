# Backlog Audit vs Project Goals

**Дата:** 2026-02-10
**Цели:** 10M YouTube views / 3 мес, ≤$4/published unit, 60 видео/мес, ≤35% брак

---

## Критерии оценки

Каждая задача оценивается по влиянию на 4 ключевые метрики:

| Метрика | Вес | Почему |
|---------|-----|--------|
| **Volume** (60 видео/мес) | Высокий | Без объёма нет просмотров |
| **Virality** (views/видео) | Высокий | Без quality нет 10M |
| **Cost** (≤$4/unit) | Средний | Kling уже $1.02 — запас есть |
| **Ops efficiency** | Низкий | Важно, но не блокер |

Оценка: **CRITICAL** / **HIGH** / **MEDIUM** / **LOW** / **IRRELEVANT**

---

## Текущий backlog (12 задач)

### CRITICAL — делать первыми

| Task | Влияние | Обоснование |
|------|---------|-------------|
| **T23 Auto-Generation** | Volume | 60 видео/мес вручную = нереально. Auto-gen поддерживает буфер → модерация → публикация без ручного запуска батчей. **Прямой блокер цели по объёму.** |

### HIGH — делать в первом месяце

| Task | Влияние | Обоснование |
|------|---------|-------------|
| **T39 Audio Hook Picker** | Virality | Один и тот же хук на все видео = алгоритм YouTube распознаёт повтор → penalize. Возможность менять хук — базовая необходимость. |
| **T40 Multi-Hook Rotation** | Virality | Автоматическая ротация хуков в батче. Каждое видео звучит по-разному. Напрямую влияет на retention и уникальность. |

### MEDIUM — полезно, но не блокер

| Task | Влияние | Обоснование |
|------|---------|-------------|
| **T8 Credits Balance** | Cost | Нужен трекинг расходов для метрики ≤$4/unit. Но при Kling $1.02/unit — запас 4x. Можно трекать вручную первый месяц, автоматизировать позже. |
| **T35 Per-video SFX** | Virality | Звуковые эффекты добавляют уникальность. Но основной формат — музыка, не SFX. Зависит от типа контента. |
| **T37 Template UI polish** | Ops | Ускоряет ежедневную работу с Template. Не влияет на views напрямую. |

### LOW — откладываем

| Task | Влияние | Обоснование |
|------|---------|-------------|
| **T15 Video Analysis** | Indirect | Discover/Remix pipeline. Помогает найти что работает, но для 3-мес PoC шаблон уже выбран. Можно исследовать вручную. |
| **T16 Brief Generation** | Indirect | Зависит от T15. Автоматизация создания проекта из анализа — value для масштаба, не для PoC. |
| **T17 Persona & Scout** | Indirect | AI-поиск трендов. Полезно в теории, но за 3 мес — ручной ресёрч быстрее. |
| **T18 Entity Extraction** | Indirect | Качество анализа. Зависит от T15. Не влияет на Template pipeline. |
| **T34 Discover Storyline** | Indirect | Мульти-сценный таймлайн. Креативная фича для Discover. Не Template, не volume. |
| **T36 Discover UI polish** | None | UI полировка Discover. Нулевое влияние на 10M views через Template. |

---

## Чего НЕ ХВАТАЕТ в backlog

Задачи, которых нет, но которые критичны для целей:

### 1. Metrics-Driven Iteration (CRITICAL)

**Проблема:** T42/T44 собирают метрики, но нет процесса "метрики → действие". Какие видео залетают? Почему? Как адаптировать шаблоны?

**Нужно:**
- Дашборд с top/flop видео и паттернами (длительность, стиль, время публикации)
- Рекомендации: "видео с X получают в 3x больше views"
- A/B тест: один шаблон, разные параметры → сравнение

### 2. Thumbnail & Title Optimization (HIGH)

**Проблема:** CTR (click-through rate) — главный рычаг для YouTube Shorts. Сейчас метаданные генерируются GPT, но не оптимизируются под алгоритм.

**Нужно:**
- AI-генерация вариантов title/description с трендовыми ключевиками
- Анализ CTR по метаданным (какие слова/фразы работают)
- Hashtag strategy

### 3. Publishing Cadence Optimization (HIGH)

**Проблема:** 60 видео/мес = 2/день. Время публикации сильно влияет на views. Сейчас расписание фиксированное.

**Нужно:**
- Анализ лучшего времени публикации из метрик
- Адаптивное расписание на основе данных
- Burst vs steady posting — что лучше для алгоритма?

### 4. Quality Gate Automation (MEDIUM)

**Проблема:** При 60 видео/мес и 35% браке = ~92 генерации. Ручная модерация каждого — bottleneck.

**Нужно:**
- AI pre-screening: автоматический фильтр явного брака (артефакты, чёрные кадры)
- Приоритизация: сначала показать самые вероятно-хорошие
- Quick-reject patterns

### 5. Cost Tracking (MEDIUM)

**Проблема:** Цель ≤$4/unit, но нет реального трекинга cost per generation. T8 (credits) — про систему кредитов, а нужен просто учёт расходов.

**Нужно:**
- Логирование API cost per generation step (image, video, music, LLM)
- Дашборд: cost/unit за период, тренд
- Alert если cost/unit растёт

---

## Рекомендуемый порядок

### Месяц 1 (февраль): Foundation + Volume

| # | Задача | Цель |
|---|--------|------|
| 1 | **T23 Auto-Generation** | Volume: автопилот генераций |
| 2 | **T39 Audio Hook Picker** | Virality: возможность менять аудио |
| 3 | **T40 Multi-Hook Rotation** | Virality: разнообразие в батчах |
| 4 | **NEW: Cost Tracking** | Cost: учёт расходов |

### Месяц 2 (март): Optimize + Learn

| # | Задача | Цель |
|---|--------|------|
| 5 | **NEW: Metrics-Driven Iteration** | Virality: data → action loop |
| 6 | **NEW: Title/Thumbnail Optimization** | Virality: CTR improvement |
| 7 | **NEW: Publishing Cadence** | Volume+Virality: оптимальное время |
| 8 | **T35 Per-video SFX** (если нужен) | Virality: звуковое разнообразие |

### Месяц 3 (апрель): Scale + Decide

| # | Задача | Цель |
|---|--------|------|
| 9 | **NEW: Quality Gate Automation** | Ops: ускорение модерации |
| 10 | **T8 Credits Balance** (упрощённый) | Cost: автоматический контроль |
| 11 | Go/No-Go анализ | — |

### Депреоритизировать

| Задача | Причина |
|--------|---------|
| T15, T16, T17, T18 | Discover/Remix pipeline — не для 3-мес PoC |
| T34 | Discover storyline — не Template |
| T36 | Discover UI polish — нулевое влияние |
| T37 | Template UI polish — nice to have, не блокер |

---

## Резюме

**Из 12 задач в backlog:**
- 1 CRITICAL (T23)
- 2 HIGH (T39, T40)
- 3 MEDIUM (T8, T35, T37)
- 6 LOW/IRRELEVANT (T15-T18, T34, T36)

**Не хватает 4-5 задач** которые напрямую влияют на цели:
- Metrics → Action loop
- Title/Thumbnail optimization
- Publishing cadence
- Quality gate automation
- Cost tracking

**Главный risk:** backlog перегружен Discover/Remix задачами (50% задач), а PoC — на Template pipeline.
