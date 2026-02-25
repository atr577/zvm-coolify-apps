# Гипотезы Q1 2026

**Цель:** 10M YouTube Shorts views за 3 месяца на 1 канале
**Ограничение:** max 2 видео/день = 60/мес = 180 за 3 мес
**Бюджет:** ≤ $4/published unit (Kling ~$1.02 текущая)

---

## Ключевой инсайт

Volume зафиксирован (2/день). Единственный рычаг — **quality**.

Из модели распределения:
- 30% фейлы (1K views) = 18K total — **бесполезны**
- 60% стандарт (100K) = 3.6M total — **основа**
- 10% топ (1M) = 6M total — **джекпот, но непредсказуем**

**Задача: максимизировать % видео в зоне "стандарт" (100K+), минимизировать фейлы.**

Каждое видео из "фейл" переведённое в "стандарт" = +99K views.
Снижение fail rate с 30% → 15% = +9 стандартов/мес = +900K views/мес.

---

## Гипотезы (тестируем)

### H1: Audio hook разнообразие > один хук на все видео

**Статус:** `not_started`
**Приоритет:** HIGH

**Тезис:** В Shorts видео автоплеится со звуком. Первый звук — trigger "остановиться или свайпнуть". Один хук на все 60 видео/мес = аудитория "привыкает", перестаёт цеплять.

**Текущее состояние:** Один хук на весь template. Все видео звучат одинаково.

**Тест:**
- Добавить 3 разных хука → ротация в батче
- 3 хука × 10+ видео = 30+ видео
- Сравнить avg retention (`averageViewPercentage`) по группам хуков
- Если разница >20% — хук значим

**Метрики:** `averageViewPercentage`, `views`, `engagedViews` per hook group

**Нужно от платформы:**
- [ ] Ротация хуков в батче (T39/T40)
- [ ] Сохранять какой хук на каком видео (`audio_hook_id` → generation)
- [ ] YouTube Analytics API: retention данные

**Результат:** _pending_

---

### H4: Seamless loop = множитель views

**Статус:** `not_started`
**Приоритет:** HIGH

**Тезис:** С марта 2025 YouTube считает views = starts + replays. Идеально залупленное 6-сек видео за 30 сек просмотра = 5 views. Зритель не замечает перезапуск → залипает → YouTube видит engagement → push.

**Текущее состояние:** Видео не лупятся. Конец видео ≠ начало.

**Варианты реализации:**
1. **Crossfade** — FFmpeg: последние 0.5s плавно переходят в первые 0.5s. Дёшево, надёжно.
2. **Reverse** — видео + reversed = "туда и обратно". Ink → Eagle → ink. Идеальный loop, тривиально.
3. **First=Last frame** — Veo/Kling: `last_frame = first_frame`. Loop by design.

**Тест:**
- Looped (crossfade) vs non-looped видео → сравнить views
- Reverse-loop vs crossfade → что залипательнее
- `views/engagedViews` ratio = proxy для replay count

**Метрики:** `views`, `engagedViews`, `views/engagedViews` ratio, `averageViewPercentage`

**Нужно от платформы:**
- [ ] `loop_mode` настройка на template: `none | crossfade | reverse`
- [ ] FFmpeg crossfade/reverse в media pipeline
- [ ] Вариативная длительность в рамках template

**Результат:** _pending_

---

### H5: Время публикации влияет на начальный push

**Статус:** `not_started`
**Приоритет:** LOW

**Тезис:** Начальный push YouTube (~200-500 показов) эффективнее если попадает на активную аудиторию. Время публикации может влиять на первичный retention → каскад.

**Текущее состояние:** Фиксированное расписание. `published_at` уже сохраняется.

**Тест:**
- Разные слоты публикации: утро EU, день EU, вечер US, ночь
- Сравнить views через 24h по слотам
- 10+ видео на слот

**Метрики:** `views` at 24h by time slot

**Нужно от платформы:**
- Ничего — данные уже собираются. Только анализ.

**Результат:** _pending_

---

## Стратегические решения (приняты)

### S1: "Impossible satisfying" — фильтр для новых template'ов

AI-генерация лучше всего создаёт плавные трансформации и satisfying визуалы. Совпадает с виральными жанрами Shorts. Реалистичные сцены с людьми = uncanny valley = больше фейлов.

Уточнение (из MrBeast "wow factor"): не просто satisfying, а **то что только AI может** — невозможные трансформации, нарушение физики, идеальная симметрия.

**Правило:** Новый template → "это satisfying + impossible?" → да → делаем.

### S2: Shorts-first подход

Shorts ≠ обычные видео. Title/thumbnail/description вторичны (автоплей в ленте). Главное:
- Visual hook (первый кадр)
- Audio hook (первый звук)
- Retention (досмотр)
- Replay (залипательность)

### S3: Трансформация с первого кадра, ноль setup

Из MrBeast: "первая минута — самая важная, 21M зрителей потеряно в первую минуту".
Для 6-сек Shorts: первые 0.5-1 сек = всё. Не тратить ни кадра на статичный setup. Действие/трансформация начинается с frame 1.

**Правило:** Если первый кадр статичный и "скучный" — переделать prompt.

---

## Мониторинг (отслеживаем)

### M1: Channel compound effect

Серия видео (один template = одна серия) должна растить канал со временем. Каждое новое видео стартует с большей базы.

**Метрики:** `subscribersGained` per video, тренд views по времени
**Проверка:** Views первых 10 видео vs последних 10 при прочих равных
**Нужно:** YouTube Analytics API (`subscribersGained`)

### M2: "1 out of 10" — качество канала

Из MrBeast: YouTube сравнивает каждое новое видео с предыдущими 9. Фейлы тянут вниз дистрибуцию следующих видео.

**Метрики:** % видео из последних 10 с views выше медианы канала
**Действие:** Если тренд падает — ужесточить модерацию, снизить cadence до 1/день.
**Нужно:** Данные накопятся к месяцу 2. Тогда оценим нужен ли quality gate.

---

## Сводка: что нужно от платформы

### 1. YouTube Analytics API (rich metrics)

| Метрика | Зачем | Для гипотезы |
|---------|-------|--------------|
| `averageViewPercentage` | Retention | H1, H4 |
| `engagedViews` | Quality views, replay proxy | H4 |
| `estimatedMinutesWatched` | Watch time | общее |
| `shares` | Viral signal | общее |
| `subscribersGained` | Channel growth | M1 |

Требует: scope `yt-analytics.readonly` + re-auth.

### 2. Generation Parameters (structured tags)

Auto-tagging через GPT при генерации:

| Параметр | Пример | Для чего |
|----------|--------|----------|
| `audio_hook_id` | FK → AudioLibrary | H1 |
| `duration_sec` | 6, 10, 15 | H4 |
| `loop_mode` | crossfade, reverse, none | H4 |
| `concept_tag` | "ink_transformation" | feedback loop |
| `subject` | "eagle", "lion" | feedback loop |
| `color_palette` | "cool_blue" | feedback loop |

### 3. Audio Variety (T39/T40)

Ротация хуков в батче. Для H1.

### 4. Loop Mode

Crossfade/reverse в media pipeline. Для H4.

### 5. Feedback Loop MVP

Метрики + tags → группировка → анализ → гипотезы. Месяц 2.

---

## Таймлайн

| Месяц | Платформа | Оператор |
|-------|-----------|----------|
| 1 (фев) | Analytics API, tags, audio rotation, loop mode | 2/день, разнообразие, собираем данные |
| 2 (мар) | Feedback loop MVP, дашборд top/flop | Анализ паттернов, A/B по гипотезам, оценка quality gate |
| 3 (апр) | Quality gate (если нужен), cost tracking | Best-performing комбинации, go/no-go |

---

**Источники:** [MrBeast Production Guide](docs/references/), YouTube Analytics API docs
**Created:** 2026-02-10
**Updated:** 2026-02-10
**Status:** Approved
