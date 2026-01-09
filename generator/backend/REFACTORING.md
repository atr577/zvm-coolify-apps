# Workflow Refactoring Plan

## Overview

Рефакторинг workflow системы для улучшения maintainability, testability и extensibility.

---

## Roadmap с приоритетами

| # | Задача | Усилия | Риск без неё | ROI | Статус |
|---|--------|--------|--------------|-----|--------|
| 1 | Security: bcrypt | 2-3 часа | Критический | Высокий | [x] |
| 2 | Phase 2: Media Services | 3-5 дней | Vendor lock-in | Высокий | [x] |
| 3 | Тесты workflow | 2-3 дня | Регрессии | Высокий | [x] |
| 4 | N+1 + Пагинация | 3-4 часа | Медленный UI | Средний | [x] |
| 5 | Split VideoDetail.tsx | 1 день | Tech debt | Средний | [x] |
| 6 | Типизация frontend | 1 день | Runtime errors | Средний | [x] |
| 7 | Phase 3: Workflow Orchestration | 0.5 дня | Code complexity | Высокий | [x] |

---

## 1. Security: SHA256 → bcrypt

### Проблема
SHA256 без salt легко брутфорсится. При утечке базы все пароли будут скомпрометированы за часы.

### Выгода
bcrypt с cost factor 12 делает брутфорс нерентабельным — взлом одного пароля займёт годы вместо секунд.

### Риск бездействия
Утечка базы = компрометация всех аккаунтов.

### Задачи
- [ ] Добавить `passlib[bcrypt]` в requirements.txt
- [ ] Создать `app/core/security.py` с `hash_password()` и `verify_password()`
- [ ] Миграция: добавить поле `password_hash_v2`
- [ ] Обновить регистрацию и логин
- [ ] Миграция существующих паролей при следующем логине

---

## 2. N+1 Queries + Пагинация

### Проблема
- N+1: 100 видео = 101 запрос к базе (1 на список + 100 на projects)
- Без пагинации: загружаем ВСЕ записи в память

При 1000 видео: 1001 запрос + 1000 объектов в памяти + медленный рендер.

### Решение

| Было | Стало |
|------|-------|
| `SELECT * FROM videos` | `SELECT * FROM videos LIMIT 20 OFFSET 0` |
| + 100 запросов на projects | + `JOIN projects` (1 запрос) |
| Всё в память | Только текущая страница |

### Выгода
- **Скорость**: 1001 запрос → 1 запрос
- **Память**: 1000 объектов → 20 объектов
- **Масштабируемость**: 10 видео или 100,000 — одинаковая скорость
- **UX**: Страница грузится мгновенно

### Пример
```
До:  GET /videos → 2.3 сек (1000 видео)
После: GET /videos?page=1&limit=20 → 50 мс
```

### Задачи
- [ ] Добавить `joinedload()` в запросы Videos с Project
- [ ] Создать `PaginatedResponse` schema
- [ ] Обновить endpoints: `GET /videos`, `GET /projects/{id}/videos`
- [ ] Frontend: добавить infinite scroll или pagination
- [ ] Опционально: cursor-based pagination для real-time

---

## 3. Тесты для Workflow Endpoints

### Проблема
50% coverage. Workflow endpoints (generate-image, generate-video) не покрыты. Рефакторинг может сломать production незаметно.

### Выгода
- **Уверенность при деплое** — CI ловит регрессии до продакшена
- **Смелый рефакторинг** — меняешь код, тесты подтверждают что ничего не сломалось
- **Документация поведения** — тесты показывают как API должен работать

### Риск бездействия
Каждый деплой = рулетка. Баг в Remix mode который поймали вручную — мог бы поймать тест.

### Задачи
- [ ] Тесты для `generate-image` endpoint (mock KLING)
- [ ] Тесты для `generate-video` endpoint
- [ ] Тесты для `generate-audio` endpoint
- [ ] Тесты для `auto_generate_to_video` (Discover + Remix)
- [ ] Тесты для `require_image_approval` flow
- [ ] CI: запуск тестов на каждый PR

---

## 4. Frontend: Split VideoDetail.tsx

### Проблема
1,301 строка в одном файле. Изменение одной фичи требует понимания всего файла. Merge conflicts при параллельной работе.

### Выгода
- **Изолированные изменения** — правишь StepProgress не трогая MediaPlayer
- **Быстрее онбординг** — новый разработчик читает один компонент
- **Переиспользование** — StepIndicator можно использовать в других местах
- **Тестируемость** — маленькие компоненты проще тестировать

### Задачи
- [ ] Выделить `StepProgressBar.tsx`
- [ ] Выделить `MediaPreview.tsx` (image/video player)
- [ ] Выделить `StepContent.tsx` (story, description, prompt display)
- [ ] Выделить `ApprovalControls.tsx`
- [ ] Выделить `VariantSelector.tsx` (audio variants)

---

## 5. Frontend: Типизация (убрать `any`)

### Проблема
51 место с `any` = 51 место где TypeScript не ловит ошибки. Опечатка в поле объекта → runtime error в проде.

### Выгода
- IDE подсказывает поля и методы
- Ошибки ловятся при компиляции, не в runtime
- Рефакторинг API → TypeScript показывает все места которые нужно обновить

### Задачи
- [ ] Типизировать API responses в `services/api.ts`
- [ ] Типизировать workflow state в VideoDetail
- [ ] Типизировать props компонентов
- [ ] Включить `strict: true` в tsconfig (постепенно)

---

## Архитектура Step-классов

```
app/services/workflow/
├── base.py                    # BaseWorkflowStep - абстрактный базовый класс
└── steps/
    ├── __init__.py
    │
    │   # Text Generation Steps (LLM)
    ├── story.py               # [x] StoryStep
    ├── description.py         # [x] DescriptionStep
    ├── prompt.py              # [x] PromptStep
    ├── scenario.py            # [x] ScenarioStep
    ├── adaptation.py          # [x] AdaptationStep
    │
    │   # Media Generation Steps (External Services)
    ├── image.py               # [ ] ImageStep
    ├── video.py               # [ ] VideoStep
    └── audio.py               # [ ] AudioStep
```

---

## Выполнено: Phase 1 - Text Generation Steps

### Что сделано

- [x] `BaseWorkflowStep` - базовый класс с общей логикой:
  - Создание/получение WorkflowStep
  - Project system_prompts lookup
  - Prompt tracking (original, custom, edited)
  - Content saving to video & step
  - AI validation
  - Error handling
  - Response building

- [x] `StoryStep` - генерация концепции видео
- [x] `DescriptionStep` - генерация описания сцены
- [x] `PromptStep` - генерация промпта для изображения
- [x] `ScenarioStep` - генерация сценария движения
- [x] `AdaptationStep` - адаптация для платформ

- [x] Рефакторинг endpoints:
  - `generate-description` - использует DescriptionStep
  - `generate-prompt` - использует PromptStep
  - `generate-scenario` - использует ScenarioStep
  - `adapt-for-platforms` - использует AdaptationStep

### Результаты Phase 1

| Метрика | До | После |
|---------|-----|-------|
| Строк кода на endpoint | ~70 | ~20 |
| Дублирование логики | Много | Минимум |
| Тесты | 67 pass | 67 pass |

---

## План: Phase 2 - Media Generation Steps

### Зачем это нужно

**Проблема**: KLING API жёстко вшит в workflow.py. Чтобы попробовать Runway или Pika — нужно переписывать workflow код.

**Выгода**:
- Смена провайдера = замена одной строки в конфиге
- A/B тестирование провайдеров без изменения кода
- Fallback на другой провайдер при даунтайме KLING
- Юнит-тесты с mock-сервисами вместо реальных API calls

**Пример**: KLING упал на 2 часа → переключил на Runway в конфиге → продолжаешь работать.

### Архитектура

```
app/services/
├── media/
│   ├── __init__.py
│   ├── base.py                    # BaseMediaService - абстрактный интерфейс
│   ├── image_service.py           # ImageServiceProtocol
│   ├── video_service.py           # VideoServiceProtocol
│   └── audio_service.py           # AudioServiceProtocol
│
├── providers/
│   ├── __init__.py
│   ├── kling/                     # KLING implementation
│   │   ├── __init__.py
│   │   ├── image.py               # KlingImageService
│   │   ├── video.py               # KlingVideoService
│   │   └── audio.py               # KlingAudioService
│   │
│   ├── runway/                    # Future: Runway implementation
│   │   └── ...
│   │
│   └── replicate/                 # Future: Replicate implementation
│       └── ...
│
└── workflow/
    └── steps/
        ├── image.py               # ImageStep (uses ImageServiceProtocol)
        ├── video.py               # VideoStep (uses VideoServiceProtocol)
        └── audio.py               # AudioStep (uses AudioServiceProtocol)
```

### Интерфейсы

```python
# app/services/media/base.py

from abc import ABC, abstractmethod
from typing import Optional, Tuple

class ImageServiceProtocol(ABC):
    """Protocol for image generation services."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        aspect_ratio: str = "9:16",
        negative_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate image, return URL."""
        pass


class VideoServiceProtocol(ABC):
    """Protocol for video generation services."""

    @abstractmethod
    async def generate(
        self,
        image_url: str,
        prompt: str,
        duration: int = 5,
        **kwargs
    ) -> Tuple[str, str]:
        """Generate video from image, return (video_url, task_id)."""
        pass


class AudioServiceProtocol(ABC):
    """Protocol for audio generation services."""

    @abstractmethod
    async def add_to_video(
        self,
        video_task_id: str,
        **kwargs
    ) -> list[str]:
        """Add audio to video, return list of variant URLs."""
        pass
```

### Пример ImageStep

```python
# app/services/workflow/steps/image.py

class ImageStep(BaseWorkflowStep):
    """Image generation step - provider agnostic."""

    step_type = StepType.IMAGE
    step_name = "image"
    content_field = "image_url"
    requires_validation = False  # No AI validation for images

    def __init__(
        self,
        db: Session,
        video: Video,
        image_service: ImageServiceProtocol  # Injected dependency
    ):
        super().__init__(db, video)
        self.image_service = image_service

    async def generate(self, request: Any, prompt: CustomPrompt) -> Dict[str, Any]:
        """Generate image using injected service."""
        image_url = await self.image_service.generate(
            prompt=self.video.image_prompt,
            aspect_ratio=self.project.aspect_ratio,
            negative_prompt=self.video.prompt_data.get("negative_prompt")
        )
        return {"image_url": image_url}
```

### Dependency Injection

```python
# app/core/deps.py

from app.services.providers.kling import KlingImageService, KlingVideoService

def get_image_service() -> ImageServiceProtocol:
    """Get current image generation service."""
    # Could be configured via settings
    return KlingImageService()

def get_video_service() -> VideoServiceProtocol:
    """Get current video generation service."""
    return KlingVideoService()
```

### Задачи Phase 2

- [ ] Создать `app/services/media/base.py` с протоколами
- [ ] Переместить KLING логику в `app/services/providers/kling/`
- [ ] Создать `ImageStep` с DI
- [ ] Создать `VideoStep` с DI
- [ ] Создать `AudioStep` с DI
- [ ] Рефакторить endpoints `generate-image`, `generate-video`, `generate-audio`
- [ ] Рефакторить `auto_generate_to_video` на использование step-классов
- [ ] Обновить тесты

---

## Выполнено: Phase 3 - Workflow Orchestration

### Что сделано

- [x] Создан `WorkflowOrchestrator` класс (`app/services/workflow/orchestrator.py`):
  - `run()` - точка входа, определяет режим (Discover/Remix/Resume)
  - `run_discover_workflow()` - полный 7-шаговый пайплайн
  - `run_remix_workflow()` - упрощённый 4-шаговый пайплайн
  - `resume_after_image_approval()` - продолжение после одобрения
  - `_complete_video_generation()` - общая логика завершения

- [x] Создан `ServiceContainer` - DI контейнер для media-сервисов:
  - Lazy initialization сервисов
  - Позволяет подменять сервисы для тестов

- [x] Создан `WorkflowResult` dataclass для структурированного результата

- [x] Рефакторинг `auto_generate_to_video` endpoint:
  - Было: ~620 строк inline-логики
  - Стало: ~55 строк - создание orchestrator и вызов run()

- [x] Обновлены тесты с новыми mock-путями для KLING-провайдеров

### Результаты Phase 3

| Метрика | До | После |
|---------|-----|-------|
| Строк кода в endpoint | ~620 | ~55 |
| Тесты | 73 pass | 73 pass |
| Циклом. сложность | Высокая | Низкая |

### Архитектура

```
app/services/workflow/
├── orchestrator.py      # WorkflowOrchestrator + ServiceContainer + WorkflowResult
├── base.py              # BaseWorkflowStep
└── steps/
    ├── story.py         # Text generation steps
    ├── description.py
    ├── prompt.py
    ├── scenario.py
    ├── adaptation.py
    ├── image.py         # Media generation steps (with DI)
    ├── video.py
    └── audio.py
```

---

## Notes

- Все 73 теста проходят после каждой фазы
- Backward compatibility - старые endpoints продолжают работать
- Постепенный rollout - можно мигрировать по одному endpoint'у
