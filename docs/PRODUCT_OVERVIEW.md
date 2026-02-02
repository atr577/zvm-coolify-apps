# REGGY - AI Video Generation Platform

**Версия:** 2.0
**Дата:** 2026-01-30

---

## Концепт

REGGY — платформа для автоматизированного создания коротких вирусных видео для Instagram Reels, TikTok и YouTube Shorts с использованием AI.

**Ключевая идея:** От концепта до готового видео за минуты, с возможностью масштабирования через шаблоны.

---

## Три типа проектов

### 1. Discover (Творческий поиск)

```
Концепт → [AI генерирует сценарий] → Картинка → Видео → Музыка
```

**Когда использовать:** Поиск новых идей, эксперименты, прототипирование.

**Пример:**
- Input: "Девушка в роскошной машине, атмосферно, закат"
- AI сам придумает: позу, машину, локацию, движения камеры

### 2. Remix (Масштабирование)

```
Готовый шаблон + переменные → Картинка → Видео → Музыка
```

**Когда использовать:** Тиражирование успешного формата с вариациями.

**Пример:**
- Шаблон: "{ethnicity} woman in {car_model} at {city}..."
- Переменные: ethnicity=азиатка, car_model=Lamborghini, city=Дубай
- Результат: предсказуемый, контролируемый

### 3. Template (Batch генерация)

```
CSV с данными → Массовая генерация по шаблону
```

**Когда использовать:** Производство большого количества видео по единому шаблону.

**Пример:**
- CSV: 100 строк с комбинациями переменных
- Шаблон: image_prompt + video_prompt + настройки
- Результат: 100 видео с минимальным участием

---

## Workflow: 4 шага

```
SCENARIO → IMAGE → VIDEO → AUDIO
```

| Шаг | Discover | Remix/Template |
|-----|----------|----------------|
| SCENARIO | LLM генерирует image_prompt + motion_prompt | Шаблоны из проекта |
| IMAGE | fal.ai генерирует картинку | fal.ai генерирует картинку |
| VIDEO | fal.ai: картинка → видео с движением | fal.ai: картинка → видео |
| AUDIO | fal.ai Lyria2 генерирует музыку | fal.ai Lyria2 генерирует музыку |

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

---

## Технологический стек

### Backend
- **Framework:** FastAPI (async)
- **Database:** PostgreSQL + SQLAlchemy + Alembic
- **LLM:** OpenAI API (gpt-4o-mini, gpt-4o)
- **Image:** fal.ai (flux-pro, nano-banana-pro)
- **Video:** fal.ai (veo3.1, kling v2.1)
- **Music:** fal.ai (lyria2)
- **Auth:** JWT + OAuth (YouTube, Instagram, TikTok)

### Frontend
- **Framework:** React 18 + TypeScript
- **Build:** Vite
- **Styling:** Tailwind CSS
- **State:** Zustand + React Query

### Production
- **Deploy:** Coolify (Docker Compose + Traefik)
- **Services:** postgres, backend, frontend (nginx)

---

## Ключевые фичи

### Workspaces
- Изоляция проектов и видео по рабочим пространствам
- Invite-система для добавления участников
- Роли: owner, member

### Social Publishing
- OAuth интеграция с YouTube, Instagram, TikTok
- Привязка аккаунтов к проектам
- Автогенерация title, description, hashtags

### Lineage Tracking
При выборе варианта восстанавливается вся цепочка:
- Выбрал video вариант → автоматически восстановится image и scenario

### Feedback Loop
Regenerate с текстовым feedback:
- "Сделай более динамичным"
- LLM использует feedback для улучшения промпта

---

## API

**Swagger UI:** http://localhost:8000/docs

| Group | Path | Purpose |
|-------|------|---------|
| Auth | `/api/auth` | Login, JWT |
| Workspaces | `/api/workspaces` | Workspace CRUD + invites |
| OAuth | `/api/oauth` | Social OAuth flows |
| Projects | `/api/projects` | Project CRUD |
| Videos | `/api/videos` | Video CRUD |
| Workflow | `/api/workflow` | 4-stage generation pipeline |
| Template | `/api/template` | Template project operations |
| Publish | `/api/publish` | Social media publishing |
| Metrics | `/api/metrics` | Analytics |

---

## Запуск

```bash
# Backend
cd backend
.venv/bin/uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm run dev
```

**URLs:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
