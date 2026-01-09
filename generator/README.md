# Viral Video Generator

Автоматизированная система для создания вирусных коротких видео с публикацией в Instagram, TikTok и YouTube Shorts.

## Возможности

- Генерация сюжетов через ChatGPT
- Создание детальных описаний (модель, авто, композиция)
- Генерация промптов для KLING AI
- Создание изображений и видео через KLING
- Самопроверка на каждом этапе
- Checkpoints для ручного контроля
- Публикация на платформах: Instagram Reels, TikTok, YouTube Shorts

## Workflow

```
Сюжет → Самопроверка → Checkpoint
  ↓
Детальное описание → Самопроверка → Checkpoint
  ↓
Промпт для фото → Самопроверка → Checkpoint
  ↓
Генерация фото → Самопроверка → Checkpoint
  ↓
Сценарий видео → Самопроверка → Checkpoint
  ↓
Генерация видео → Самопроверка → Checkpoint
  ↓
Адаптация для платформ → Самопроверка → Checkpoint
  ↓
Публикация → Готово
```

## Структура проекта

```
generator/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/         # API endpoints
│   │   ├── core/        # Configuration, security
│   │   ├── db/          # Database setup
│   │   ├── models/      # SQLAlchemy models
│   │   ├── schemas/     # Pydantic schemas
│   │   └── services/    # Business logic
│   └── tests/
├── frontend/            # React frontend
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── pages/       # Pages
│   │   ├── services/    # API clients
│   │   ├── hooks/       # Custom hooks
│   │   ├── store/       # State management
│   │   └── types/       # TypeScript types
│   └── public/
├── scripts/             # Utility scripts
└── data/               # Generated content
```

## Технологии

### Backend
- FastAPI
- SQLAlchemy
- Celery (background tasks)
- Redis (task queue)
- PostgreSQL/SQLite

### Frontend
- React
- TypeScript
- Tailwind CSS
- React Query
- Zustand (state management)

### Интеграции
- OpenAI API (ChatGPT o1)
- KLING AI API (PiAPI)
- Instagram Graph API
- TikTok Content Posting API
- YouTube Data API v3

## Установка

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # или venv\Scripts\activate на Windows
pip install -r requirements.txt
cp .env.example .env
# Настройте .env с вашими API ключами
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
# Настройте .env
```

## Настройка API ключей

Создайте `.env` файл в `backend/`:

```
# OpenAI
OPENAI_API_KEY=your_openai_key

# KLING (PiAPI)
PIAPI_KEY=your_piapi_key

# Instagram
INSTAGRAM_ACCESS_TOKEN=your_token
INSTAGRAM_BUSINESS_ACCOUNT_ID=your_account_id

# TikTok
TIKTOK_CLIENT_KEY=your_client_key
TIKTOK_CLIENT_SECRET=your_client_secret

# YouTube
YOUTUBE_CLIENT_ID=your_client_id
YOUTUBE_CLIENT_SECRET=your_client_secret

# Database
DATABASE_URL=sqlite:///./generator.db
# DATABASE_URL=postgresql://user:password@localhost/generator

# Redis
REDIS_URL=redis://localhost:6379/0
```

## Запуск

### Development

Backend:
```bash
cd backend
uvicorn app.main:app --reload
```

Frontend:
```bash
cd frontend
npm run dev
```

Celery Worker:
```bash
cd backend
celery -A app.core.celery worker --loglevel=info
```

### Production

```bash
docker-compose up -d
```

## API Endpoints

### Projects
- `POST /api/projects` - Создать новый проект
- `GET /api/projects` - Список проектов
- `GET /api/projects/{id}` - Детали проекта
- `DELETE /api/projects/{id}` - Удалить проект

### Workflow
- `POST /api/workflow/generate-story` - Генерация сюжета
- `POST /api/workflow/generate-description` - Генерация описания
- `POST /api/workflow/generate-prompt` - Генерация промпта
- `POST /api/workflow/generate-image` - Генерация изображения
- `POST /api/workflow/generate-video` - Генерация видео
- `POST /api/workflow/validate-step` - Самопроверка этапа
- `POST /api/workflow/approve-step` - Одобрить checkpoint

### Publishing
- `POST /api/publish/instagram` - Публикация в Instagram
- `POST /api/publish/tiktok` - Публикация в TikTok
- `POST /api/publish/youtube` - Публикация в YouTube

## Лицензия

MIT
