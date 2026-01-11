# REGGY - AI Video Generation Platform

**Версия:** 1.0 (as built)
**Дата:** 2026-01-12

---

## Концепт

REGGY — платформа для автоматизированного создания коротких вирусных видео для Instagram Reels, TikTok и YouTube Shorts с использованием AI (GPT + KLING через PiAPI).

**Ключевая идея:** От концепта до готового видео за минуты, с возможностью масштабирования через шаблоны.

---

## Два режима работы

### 1. Discover (Творческий поиск)

```
Концепт → [AI генерирует сценарий] → Картинка → Видео → Аудио
```

**Когда использовать:** Поиск новых идей, эксперименты, прототипирование.

**Пример:**
- Input: "Девушка в роскошной машине, атмосферно, закат"
- AI сам придумает: позу, машину, локацию, движения камеры

### 2. Remix (Масштабирование)

```
Готовый шаблон + переменные → Картинка → Видео → Аудио
```

**Когда использовать:** Тиражирование успешного формата с вариациями.

**Пример:**
- Шаблон: "{ethnicity} woman in {car_model} at {city}..."
- Переменные: ethnicity=азиатка, car_model=Lamborghini, city=Дубай
- Результат: предсказуемый, контролируемый

---

## Workflow: 4 шага

```
SCENARIO → IMAGE → VIDEO → AUDIO
```

| Шаг | Discover | Remix |
|-----|----------|-------|
| SCENARIO | LLM генерирует image_prompt + motion_prompt | Пропускается (шаблоны в проекте) |
| IMAGE | KLING генерирует картинку | KLING генерирует картинку |
| VIDEO | KLING: картинка → видео с движением | KLING: картинка → видео с движением |
| AUDIO | KLING добавляет звук | KLING добавляет звук |

---

## Режимы выполнения

| Режим | Поведение | Use Case |
|-------|-----------|----------|
| **AUTO** | Все шаги без пауз | Batch generation, быстрый прототип |
| **MANUAL** | Пауза после каждого шага для approve/regenerate | Контроль качества, творческий поиск |

### MANUAL режим возможности:
- Просмотр результата каждого шага
- Regenerate с текстовым feedback
- История вариантов (можно вернуться к предыдущему)
- Навигация назад по шагам
- Edit содержимого (для scenario)

---

## Архитектура

### Backend (FastAPI + SQLite)

```
app/
├── api/
│   └── workflow.py          # Единый API для всех операций
├── models/
│   ├── project.py           # Проект = шаблон для видео
│   ├── video.py             # Видео = экземпляр генерации
│   └── step_history.py      # История вариантов каждого шага
├── services/
│   ├── openai_service.py    # LLM для текстовой генерации
│   ├── kling_service.py     # KLING для image/video/audio
│   └── workflow/
│       ├── orchestrator.py  # Оркестратор workflow
│       └── strategies/      # Strategy pattern для Discover/Remix
```

### Frontend (React + TypeScript)

```
src/
├── components/
│   └── workflow/
│       ├── WorkflowRunner.tsx  # Основной компонент workflow
│       └── StepReview.tsx      # UI для approve/regenerate
├── hooks/
│   └── useWorkflowV3.ts        # React Query mutations
└── pages/
    └── VideoDetail.tsx         # Страница видео
```

---

## Модели данных

### Project (шаблон)

```typescript
{
  id: number
  name: string
  project_type: "discover" | "remix"

  // Шаблоны
  story_template: string      // Discover: концепт, Remix: image prompt
  motion_template: string     // Только Remix: motion prompt

  // Remix-specific
  placeholders: string[]                    // ["hair_color", "car_model"]
  placeholder_suggestions: Record<string, string[]>  // {hair_color: ["blonde", "brunette"]}

  // Настройки
  platforms: string[]         // ["instagram", "tiktok", "youtube"]
  duration: number            // 5, 10, 15 секунд
  audio_mode: string          // "none" | "scene" | "music" | "auto"
  workflow_mode: string       // default mode для новых видео
}
```

### Video (экземпляр)

```typescript
{
  id: number
  project_id: number
  workflow_mode: "AUTO" | "MANUAL"
  status: "pending" | "in_progress" | "completed" | "failed"
  current_step: "scenario" | "image" | "video" | "audio" | null

  // Remix: значения переменных
  content_variables: Record<string, string>

  // Результаты шагов
  scenario_data: {
    image_prompt: string
    motion_prompt: string
    camera_movement: object
  }
  image_url: string
  video_url: string
  video_with_audio_url: string

  // Publishing
  publishing_meta: {
    instagram: { title, description, hashtags }
    tiktok: { title, description, hashtags }
    youtube: { title, description, hashtags }
  }
}
```

### StepHistory (варианты)

```typescript
{
  id: number
  video_id: number
  step_type: "scenario" | "image" | "video" | "audio"
  content: object             // Результат генерации
  is_selected: boolean        // Выбранный вариант
  feedback: string            // Feedback при regenerate

  // Lineage tracking
  parent_id: number           // Родительский вариант
  source_scenario: object     // Snapshot scenario при генерации
  source_image_url: string    // Snapshot image при генерации video
}
```

---

## API Endpoints

### Workflow API

| Method | Endpoint | Описание |
|--------|----------|----------|
| POST | `/api/workflow/{video_id}/run-auto` | Запустить AUTO режим |
| POST | `/api/workflow/{video_id}/generate/{step}` | Сгенерировать шаг (MANUAL) |
| GET | `/api/workflow/{video_id}/variants/{step}` | Получить варианты шага |
| POST | `/api/workflow/{video_id}/switch/{variant_id}` | Переключить вариант (preview) |
| POST | `/api/workflow/{video_id}/approve/{variant_id}` | Approve и перейти к следующему |
| POST | `/api/workflow/{video_id}/goto/{step}` | Навигация назад |
| PATCH | `/api/workflow/{video_id}/update/{step}` | Редактировать содержимое |

### CRUD API

| Resource | Endpoints |
|----------|-----------|
| Projects | GET/POST/PATCH/DELETE `/api/projects` |
| Videos | GET/POST/PATCH/DELETE `/api/videos` |
| Publishing | POST `/api/publish/{platform}` |

---

## Внешние сервисы

| Сервис | Провайдер | Использование |
|--------|-----------|---------------|
| LLM | PiAPI (OpenAI-compatible) | Генерация сценариев, publishing meta |
| Image | KLING via PiAPI | Text-to-image |
| Video | KLING via PiAPI | Image-to-video |
| Audio | KLING via PiAPI | Video + audio |

---

## Ключевые фичи

### Lineage Tracking
При выборе варианта восстанавливается вся цепочка:
- Выбрал video вариант 1 → автоматически восстановится image и scenario из которых он был создан

### Feedback Loop
Regenerate с текстовым feedback:
- "Сделай более динамичным"
- LLM использует feedback для улучшения промпта

### Auto Publishing Meta
При завершении workflow автоматически генерируется:
- Title, description, hashtags для каждой платформы
- Учитываются лимиты платформ (Instagram 30 хэштегов, TikTok 7)

---

## Статус реализации

| Компонент | Статус |
|-----------|--------|
| Discover AUTO | ✅ Работает |
| Discover MANUAL | ✅ Работает |
| Remix AUTO | ✅ Работает |
| Remix MANUAL | ✅ Работает |
| Lineage tracking | ✅ Работает |
| Publishing meta | ✅ Работает |
| Social publishing | ⚠️ Требует OAuth настройки |
| Metrics | ✅ UI готов, ручной ввод |

---

## Запуск

```bash
# Backend
cd backend
venv/bin/uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm run dev
```

**URLs:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
