# GAP Analysis: MVP Концепт vs Template Pipeline

**Дата:** 2026-01-30
**Источник:** MVP Концепт.md
**Scope:** Template project type (Single State → Video pipeline)

---

## Executive Summary

MVP концепт описывает 9 типов пайплайнов генерации видео. Текущая реализация Template проекта покрывает **базовый pipeline генерации** (CSV → LLM → Image → Video), но не включает:
- Генерацию метаданных (название, описание)
- Публикацию
- Расписание
- Модерацию

---

## Pipeline Types Overview

| # | MVP Pipeline | Наш тип | Статус |
|---|--------------|---------|--------|
| 1 | Single state → Video | **Template** | Частично |
| 2 | Dual state → Video | — | Не реализован |
| 3 | Multi state → Video | — | Не реализован |
| 4 | Timed Assembly → Video | — | Не реализован |
| 5 | Template-Based → Video | **Template** | Частично |
| 6 | Script → Scene → Video | **Discover** | Реализован |
| 7 | Data-Driven → Video | — | Не реализован |
| 8 | Audio-First → Video | — | Не реализован |
| 9 | Multi-Modal Narrative | — | Не реализован |

**Фокус MVP:** Single state → Video (человек + объект + среда)

---

## Single State Pipeline: Детальное сравнение

### MVP Flow

```
START_SPEC → FULL_SPEC_PROMPT → IMAGE_SPEC_PROMPT → IMAGE → VIDEO_PROMPT → VIDEO
                                                                    ↓
                                              NAME_PROMPT → DESCR_PROMPT → PUBLISH
```

### Наш Flow (Template)

```
CSV/Variant → preprocessing_prompt → image_prompt_template → IMAGE → VideoTemplate → VIDEO
     ✅              ✅                      ✅                ✅          ✅           ✅
```

### Mapping

| MVP Термин | Наша реализация | Файл/Модель | Статус |
|------------|-----------------|-------------|--------|
| START_SPEC | `Variant.data` | `models/variant.py` | ✅ |
| FULL_SPEC_PROMPT | `preprocessing_prompt` | `TemplateSettings` | ✅ |
| FULL_SPEC | `preprocessing_result` | `TemplateGeneration` | ✅ |
| IMAGE_SPEC_PROMPT | `image_prompt_template` | `TemplateSettings` | ✅ |
| IMAGE_PROMPT | `image_prompt` | `TemplateGeneration` | ✅ |
| IMAGE | `image_url` / `image_path` | `TemplateGeneration` | ✅ |
| VIDEO_PROMPT | `VideoTemplate.prompt` | `models/video_template.py` | ✅ |
| VIDEO | `video_url` / `video_path` | `TemplateGeneration` | ✅ |
| NAME_PROMPT | — | — | ❌ |
| NAME | — | — | ❌ |
| DESCR_PROMPT | — | — | ❌ |
| DESCRIPTION | — | — | ❌ |
| MUSIC | — | — | ❌ |
| SCHEDULING | — | — | ❌ |
| MODERATION | — | — | ❌ |
| PUBLISH | — | — | ❌ |

---

## GAP List

### HIGH Priority

| # | Feature | Описание | Сложность | Зависимости |
|---|---------|----------|-----------|-------------|
| G1 | **Name Generation** | Промпт + поле для генерации названия ролика | Low | — |
| G2 | **Description Generation** | Промпт + поле для генерации описания | Low | — |
| G3 | **Template Publishing** | Публикация TemplateGeneration в соцсети | Medium | Social accounts binding (✅ done) |
| G4 | **Publishing Schedule** | Слоты публикации (день/время) | High | G3 |

### MEDIUM Priority

| # | Feature | Описание | Сложность | Зависимости |
|---|---------|----------|-----------|-------------|
| G5 | **Moderation Workflow** | Статусы: draft → pending → approved → scheduled → published | Medium | G3, G4 |
| G6 | **Structured FULL_SPEC** | JSON-структура вместо free-form text | Medium | — |

### LOW Priority

| # | Feature | Описание | Сложность | Зависимости |
|---|---------|----------|-----------|-------------|
| G7 | **Music Generation** | Lyria2 для Template (как в Discover) | Low | — |
| G8 | **Auto-generate START_SPEC** | LLM-генерация вариантов без CSV | Medium | — |
| G9 | **Dynamic VIDEO_PROMPT** | Генерация video prompt вместо выбора из списка | Low | — |

---

## Архитектурные заметки

### 1. FULL_SPEC: JSON vs Free-form

**MVP ожидает:** Строгая JSON-структура с полями (header, model, car, location, etc.)

**У нас:** `preprocessing_result` — свободный текст или произвольный JSON

**Рекомендация:** Оставить гибкость (free-form), но добавить опцию JSON-схемы в настройках проекта.

### 2. VIDEO_PROMPT: Список vs Генерация

**MVP:** Два режима — выбор из списка ИЛИ динамическая генерация

**У нас:** Только выбор из VideoTemplate

**Рекомендация:** Добавить `video_prompt_template` в TemplateSettings для динамической генерации (optional).

### 3. Модерация

**MVP Flow:**
```
Генерация → Показать превью → [Подтвердить | Перегенерировать | Отклонить] → Слот публикации
```

**Рекомендация:** Добавить статусы в TemplateGeneration:
- `draft` — только что создано
- `pending_review` — ожидает модерации
- `approved` — одобрено, ждёт слота
- `rejected` — отклонено
- `scheduled` — назначено на публикацию
- `published` — опубликовано

---

## Примеры промптов из MVP

### NAME_PROMPT (генерация названия)

```
Формат: 🌍 {SCENE TITLE ≤35 chars} 👠 {CAR TITLE ≤35 chars} 🚗 #luxury #car #model #travel #shorts

Пример: "🌍 Helsinki Cathedral Dusk 👠 Deep Emerald Bentayga 🚗 #luxury #car #model #travel #shorts"
```

### DESCR_PROMPT (генерация описания)

```
Структура:
1) 2-3 коротких абзаца (editorial voice-over)
2) Пустая строка
3) Хэштеги в одну строку

Стиль: luxury editorial, не реклама
Эмодзи: 1-3 на весь текст
```

### VIDEO_PROMPT (примеры из MVP)

5 вариантов готовых промптов для 10-секундного видео:
1. Выход из машины → закрыть дверь → идти к капоту → опереться → взгляд вверх
2. Выход → закрыть → идти к багажнику → полуоборот → уходить спиной
3. Выход → закрыть → идти к капоту → поворот к камере → поза с поднятой ногой
4. Выход → идти к камере → 3 позы → финальная поза (застыть)
5. Выход (с намёком) → позы → разворот 180° → уход → взгляд через плечо

---

## Рекомендуемый план доработок

### Phase 1: Metadata Generation (G1, G2)

**Scope:** Добавить генерацию названия и описания

**Изменения:**
- `TemplateSettings`: добавить `name_prompt`, `description_prompt`
- `TemplateGeneration`: добавить `generated_name`, `generated_description`
- `template_generation_service.py`: добавить шаги генерации

**Effort:** 1-2 дня

### Phase 2: Publishing (G3)

**Scope:** Публикация TemplateGeneration в соцсети

**Изменения:**
- Новые endpoints в `api/template.py` или отдельный `api/template_publishing.py`
- Связь с существующим `social_service.py`

**Effort:** 2-3 дня

### Phase 3: Moderation & Scheduling (G4, G5)

**Scope:** Workflow модерации и расписание публикаций

**Изменения:**
- `TemplateGeneration`: добавить статусы модерации
- Новая модель `PublishingSlot` или расширение существующей
- APScheduler jobs для публикации по расписанию

**Effort:** 3-5 дней

---

## Приложение: Текущая структура Template

### Models

```
Project (type=template)
    ├── TemplateSettings (prompts, models, aspect_ratio)
    ├── VideoTemplate[] (video prompt templates)
    ├── Variant[] (CSV rows)
    └── TemplateGeneration[] (generation results)
```

### Generation Pipeline

```python
# template_generation_service.py
async def run_generation(generation_id):
    1. Load variant data
    2. Run preprocessing (LLM) → preprocessing_result
    3. Build image_prompt from template + preprocessing_result
    4. Generate image (fal.ai) → image_url
    5. Get video_prompt from VideoTemplate
    6. Generate video (fal.ai) → video_url
    # TODO: 7. Generate name
    # TODO: 8. Generate description
```

### API Endpoints

```
POST   /api/projects/template              # Create project
GET    /api/projects/{id}/template-settings
PUT    /api/projects/{id}/template-settings
POST   /api/projects/{id}/variants/upload  # CSV upload
GET    /api/projects/{id}/variants
GET    /api/projects/{id}/video-templates
POST   /api/projects/{id}/video-templates
POST   /api/projects/{id}/generate         # Start generation
GET    /api/projects/{id}/generations
# TODO: POST /api/projects/{id}/generations/{id}/publish
# TODO: POST /api/projects/{id}/generations/{id}/schedule
```

---

## References

- MVP Концепт.md (source document)
- SPEC-T19-template-project-type.md (original spec)
- backend/app/services/template_generation_service.py
- backend/app/api/template.py
