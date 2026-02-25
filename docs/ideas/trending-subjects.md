# Trending Subjects в генерации видео

**Статус:** Идея, не протестирована
**Источник:** Обсуждение 2026-02-12, анализ Jack Craig tutorial
**Связь:** Гипотезы Q1 2026, пункт 4 (research pipeline)

---

## Суть

Вместо generic объектов (рыбка, ракета) использовать трендовые сущности (Super Bowl, события, символы) как переменные в existing templates.

| | Сейчас | Предлагается |
|--|--------|-------------|
| **Subject** | Generic (eagle, fish, rocket) | Trending (Super Bowl trophy, Grammy award, Olympic rings) |
| **Источник** | Вручную | Google Trends YouTube + фильтр |
| **Pipeline изменение** | — | Только subject в промпте |
| **Стоимость** | $0.66 | $0.66 (та же) |

**Data source:** https://trends.google.com/trends/explore?date=now%207-d&gprop=youtube

---

## Оценка

| Измерение | Аргумент ЗА | Контр-аргумент ПРОТИВ | Вердикт |
|-----------|------------|----------------------|---------|
| **Discovery boost** | YouTube пушит контент про трендовые темы. Тег "Super Bowl" в день Super Bowl = попадание в волну | Shorts discovery — через feed, не search. Зритель не ищет "ink transformation Super Bowl" | **Тестируемо.** Даже 20% трафика из search/suggested = значимо |
| **Скорость реакции** | Тренд живёт 3-7 дней. Наш pipeline за 2-4 часа = попадаем в окно | Тренды непредсказуемы. Батчевый подход может не успевать. Модерация задержала — тренд ушёл | **Риск.** Нужен fast-track поток отдельно от батча |
| **AI gen качество** | Абстрактные объекты (trophy, guitar) = ок для satisfying. Промпт простой | Конкретные лица (Bad Bunny) — AI не попадёт в likeness. Логотипы — copyright | **Ограничение.** Работает для событий и символов. НЕ для лиц и брендов |
| **Стоимость** | Та же $0.66. Меняется только subject в промпте. Zero incremental cost | Data pipeline: Trends → фильтрация → промпты. Разработка + поддержка | **Дёшево.** Основной cost = разработка data pipeline |
| **Title/Tags SEO** | "Ink Super Bowl Trophy" = поисковый трафик в неделю события. Titles становятся discoverable | SEO для Shorts вторичен — 90%+ трафика из feed | **За.** Бесплатный буст, пусть и маленький |
| **Операционная сложность** | pytrends: раз в день топ-20 trending → фильтр → подставить в промпты | "Trending" ≠ "можно нарисовать". Нужен фильтр визуализируемости. Ручная фильтрация убивает автоматизацию | **Полуавтомат.** Данные автоматом, фильтр "визуализируемо?" — LLM или оператор |
| **Органичность** | Trending subject + satisfying = "о, актуальная тема в крутом визуале!" | Может выглядеть forced. "Ink → Bad Bunny" — зачем? Нет связи формата с темой | **Зависит от execution.** Органично = работает, натянуто = clickbait |
| **Измеримость** | A/B: trending vs generic subject, тот же template. Чистый тест. Views at 24h | Тренды разной силы, нужна нормализация. 10+ видео на группу | **Легко.** Самая простая гипотеза для A/B из всех наших |

---

## Pipeline (концепт)

1. **Data pull** — pytrends / Google Trends API → топ trending YouTube за последние 7 дней
2. **Фильтр** — LLM оценивает: "можно ли визуализировать как объект для satisfying видео?" → да/нет + suggested visual (trophy, guitar, symbol)
3. **Промпт** — подставить trending subject в existing template prompt
4. **Fast-track** — отдельный от батча поток: генерация → экспресс-модерация → публикация за 2-4 часа
5. **Tagging** — `concept_tag: trending`, `trend_source: "super bowl"`, `trend_date: 2026-02-12`

---

## Ограничения subject'ов

| Тип | Пример | Работает? |
|-----|--------|-----------|
| Событие → символ | Super Bowl → trophy | Да |
| Музыка → инструмент/символ | Grammy → gramophone | Да |
| Природное явление | Eclipse, aurora | Да |
| Конкретный человек | Bad Bunny, Taylor Swift | Нет (likeness + copyright) |
| Бренд/логотип | Nike swoosh, Apple logo | Нет (trademark) |
| Игра/абстракция | Roblox item, game character | Возможно (если generic enough) |

---

## Open Questions

1. **pytrends reliability** — неофициальный API, может ломаться. Альтернативы?
2. **Timing workflow** — как интегрировать fast-track в текущий операционный процесс?
3. **A/B design** — сколько видео нужно для статистически значимого теста?
4. **Комбинация с H1** — trending subject + varied audio hook = двойной буст?

---

**Created:** 2026-02-12
