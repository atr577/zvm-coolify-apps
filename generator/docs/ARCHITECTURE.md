# Архитектура и инфраструктура REGGY

## Обзор проекта

**REGGY** — платформа для автоматического создания коротких вирусных видео для Instagram Reels, TikTok и YouTube Shorts с использованием AI.

**Основной пайплайн:** Story → Description → Prompt → Image → Scenario → Video → Audio → Adaptation → Publishing

---

## 1. Общая структура проекта

```
RE/
├── generator.db                 # SQLite база данных
└── generator/
    ├── backend/                 # FastAPI бэкенд (Python 3.11)
    │   ├── app/
    │   │   ├── api/            # API эндпоинты (9 групп маршрутов)
    │   │   ├── core/           # Конфигурация, безопасность, планировщик
    │   │   ├── db/             # Настройка базы данных
    │   │   ├── models/         # SQLAlchemy ORM модели (12 таблиц)
    │   │   ├── schemas/        # Pydantic схемы валидации
    │   │   ├── services/       # Бизнес-логика и AI клиенты
    │   │   └── main.py         # Точка входа FastAPI приложения
    │   ├── alembic/            # Миграции базы данных
    │   ├── tests/              # Тесты
    │   ├── Dockerfile          # Docker образ бэкенда
    │   └── requirements.txt    # Python зависимости
    ├── frontend/                # React + TypeScript фронтенд
    │   ├── src/
    │   │   ├── components/     # Переиспользуемые React компоненты (~13)
    │   │   ├── pages/          # Страницы приложения (~12)
    │   │   ├── services/       # API клиент (api.ts)
    │   │   ├── contexts/       # React Context (AuthContext)
    │   │   ├── hooks/          # Кастомные хуки
    │   │   ├── store/          # Zustand хранилище
    │   │   ├── types/          # TypeScript типы
    │   │   ├── App.tsx         # Корневой компонент с роутингом
    │   │   └── main.tsx        # Точка входа React
    │   ├── Dockerfile          # Docker образ фронтенда
    │   ├── package.json        # Node.js зависимости
    │   └── vite.config.ts      # Конфигурация Vite
    ├── data/                    # Хранилище контента
    │   ├── generated/          # Сгенерированные видео и изображения
    │   ├── uploads/            # Загруженные пользователем файлы
    │   └── api_cache/          # Кэш API ответов
    ├── scripts/                 # Утилиты
    ├── docs/                    # Документация
    └── docker-compose.yml       # Оркестрация контейнеров
```

---

## 2. Технологический стек

### Backend

| Категория | Технологии |
|-----------|------------|
| Web Framework | FastAPI 0.109.0, Uvicorn 0.27.0 |
| ORM | SQLAlchemy 2.0.25, Alembic 1.13.1 |
| Async HTTP | HTTPX 0.26.0 |
| Task Queue | Celery 5.3.6, Redis 5.0.1 |
| Scheduler | APScheduler 3.10.4 |
| Auth | python-jose (JWT), passlib (bcrypt) |
| Media | Pillow 10.2.0, OpenCV 4.9.0 |
| Validation | Pydantic 2.5.3 |

### Frontend

| Категория | Технологии |
|-----------|------------|
| Framework | React 18.2.0, TypeScript 5.3.3 |
| Build Tool | Vite 5.0.11 |
| Styling | Tailwind CSS 3.4.1 |
| State (Server) | React Query 3.39.3 |
| State (Client) | Zustand 4.4.7 |
| HTTP Client | Axios 1.6.5 |
| Routing | React Router DOM 6.21.0 |
| Icons | Lucide React 0.309.0 |

### Инфраструктура

| Категория | Технологии |
|-----------|------------|
| Database | SQLite (dev) / PostgreSQL 15 (prod) |
| Cache/Queue | Redis 7 |
| Containers | Docker, Docker Compose |
| AI Services | PiAPI (GPT + KLING) |

---

## 3. Backend архитектура

### 3.1 Точка входа (main.py)

Файл: `generator/backend/app/main.py`

- Инициализация FastAPI приложения
- Создание таблиц БД при старте
- Настройка CORS middleware (localhost:3000)
- Lifespan management для планировщика
- Подключение 9 групп API маршрутов

### 3.2 API маршруты

Расположение: `generator/backend/app/api/`

| Маршрут | Файл | Назначение |
|---------|------|------------|
| `/api/auth` | auth.py | Аутентификация, регистрация, JWT токены |
| `/api/workspaces` | auth.py | Создание и управление рабочими пространствами |
| `/api/oauth` | oauth.py | OAuth потоки для соцсетей |
| `/api/social-accounts` | social_accounts.py | Подключенные аккаунты соцсетей |
| `/api/projects` | projects.py | CRUD для проектов-шаблонов |
| `/api/videos` | videos.py | CRUD для видео |
| `/api/ai` | ai_generation.py | Генерация вариантов контента с AI |
| `/api/workflow` | workflow.py | 8-этапный генерационный пайплайн |
| `/api/publish` | publishing.py | Публикация в соцсети |
| `/api/metrics` | metrics.py | Метрики и аналитика видео |

### 3.3 Модели данных

Расположение: `generator/backend/app/models/`

#### Управление пользователями (user.py)

- **User** — email/password аутентификация, роли (admin/user)
- **Workspace** — рабочее пространство для совместной работы
- **WorkspaceMember** — связь пользователей с workspace (роли: owner/member)
- **Invite** — токены приглашений для регистрации
- **SocialAccount** — OAuth credentials для Instagram/TikTok/YouTube

#### Контент (project.py, video.py)

- **Project** — шаблон видео:
  - `story_template` — базовый нарратив
  - `platforms` — целевые платформы
  - `duration` — длительность (5/10/15 секунд)
  - `aspect_ratio` — соотношение сторон (9:16, 16:9, 1:1)

- **Video** — отдельное видео:
  - `workflow_mode` — MANUAL или AUTO
  - `content_variables` — выбранный контент из вариантов
  - Данные каждого этапа: story_data, description_data, prompt_data, image_url, scenario_data, video_url, audio_variants, video_with_audio_url, adaptation_data
  - `current_step` — текущий этап workflow
  - `status` — статус генерации
  - `author_rating` — оценка автора (1-5)

#### Workflow (workflow_step.py, validation_result.py)

- **WorkflowStep** — отслеживание этапа:
  - `step_type` — STORY/DESCRIPTION/PROMPT/IMAGE/SCENARIO/VIDEO/AUDIO/ADAPTATION
  - `status` — статус этапа
  - `content` — сгенерированный контент (JSON)
  - `validation_attempts` — количество попыток валидации

- **ValidationResult** — результат AI-валидации:
  - `status` — pass/pass_with_warnings/fail
  - `score` — оценка 0-100
  - `criteria_results` — результаты по критериям
  - `warnings`, `errors`, `recommendations`

- **PublishResult** — результат публикации на платформе

- **VideoMetrics** — метрики видео (views, likes, comments, shares)

### 3.4 Сервисы

Расположение: `generator/backend/app/services/`

| Сервис | Назначение |
|--------|------------|
| piapi_client.py | Унифицированный AI клиент для GPT и KLING через PiAPI |
| openai_service.py | Генерация текста и логика валидации |
| kling_service.py | Генерация видео/изображений с polling |
| metrics_fetcher.py | Получение метрик с платформ |
| social_service.py | Интеграция с соцсетями |
| mock_data.py | Mock ответы для тестирования |

### 3.5 Конфигурация

Расположение: `generator/backend/app/core/`

- **config.py** — Pydantic settings:
  - API ключи (PIAPI_KEY, AIMLAPI_KEY)
  - Модели (GPT_MODEL, KLING_MODEL)
  - OAuth credentials
  - DATABASE_URL, REDIS_URL
  - CORS origins

- **security.py** — генерация/валидация JWT токенов
- **deps.py** — FastAPI dependencies (get_current_user, get_db)
- **scheduler.py** — APScheduler для фоновых задач метрик
- **celery_app.py** — конфигурация Celery

---

## 4. Frontend архитектура

### 4.1 Структура

```
frontend/src/
├── main.tsx              # Точка входа React
├── App.tsx               # Корневой компонент с роутингом
├── pages/                # Страницы (route-level компоненты)
│   ├── Dashboard.tsx     # Список проектов и видео
│   ├── CreateVideo.tsx   # Создание видео
│   ├── VideoDetail.tsx   # Детали видео и workflow
│   ├── ProjectEdit.tsx   # Редактирование проекта
│   ├── Login.tsx         # Авторизация
│   ├── Register.tsx      # Регистрация
│   ├── Analytics.tsx     # Метрики видео
│   ├── Settings.tsx      # Настройки пользователя
│   ├── SocialAccounts.tsx # Подключенные соцсети
│   └── Workspaces.tsx    # Управление workspace
├── components/           # Переиспользуемые компоненты
│   ├── Layout.tsx        # Основной layout с навигацией
│   ├── ProtectedRoute.tsx # Защита маршрутов
│   ├── ProjectCard.tsx   # Карточка проекта
│   ├── VideoCard.tsx     # Карточка видео
│   ├── VideoWorkflowView.tsx # Визуализация workflow
│   ├── StepCard.tsx      # Карточка этапа
│   └── ...
├── services/api.ts       # Axios API клиент
├── contexts/AuthContext.tsx # Контекст аутентификации
├── types/index.ts        # TypeScript типы
├── hooks/                # Кастомные хуки
└── store/                # Zustand хранилища
```

### 4.2 API клиент

Файл: `generator/frontend/src/services/api.ts`

Группы API:
- `projectsApi` — CRUD проектов
- `videosApi` — CRUD видео
- `aiApi` — генерация вариантов AI
- `workflowApi` — 8-этапный workflow
- `publishingApi` — публикация в соцсети
- `metricsApi` — метрики и аналитика
- `authApi` — аутентификация
- `workspaceApi` — управление workspace

### 4.3 Типы

Файл: `generator/frontend/src/types/index.ts`

Ключевые типы:
- `WorkflowStatus` — pending, in_progress, validating, awaiting_approval, approved, rejected, completed, failed
- `StepType` — story, description, prompt, image, scenario, video, audio, adaptation, publishing
- `WorkflowStep` — данные этапа с массивом валидаций
- `Video` — полная запись видео со всеми данными workflow
- `Project` — конфигурация шаблона
- `VideoMetrics` — метрики платформ

---

## 5. База данных

### 5.1 Настройка

- **Development:** SQLite (`generator.db` в корне проекта)
- **Production:** PostgreSQL

Таблицы создаются автоматически при старте через `Base.metadata.create_all()`

### 5.2 Миграции

Инструмент: Alembic

```bash
# Создать миграцию
alembic revision --autogenerate -m "description"

# Применить миграции
alembic upgrade head
```

### 5.3 Схема таблиц

1. users
2. workspaces
3. workspace_members
4. invites
5. social_accounts
6. projects
7. project_social_accounts (связующая)
8. videos
9. workflow_steps
10. validation_results
11. publish_results
12. video_metrics

---

## 6. Инфраструктура

### 6.1 Docker Compose

Файл: `generator/docker-compose.yml`

```yaml
services:
  backend:
    ports: ["8000:8000"]
    volumes: ["./backend:/app", "./data:/app/data"]
    depends_on: [db, redis]
    command: uvicorn app.main:app --reload

  celery:
    # Фоновый воркер для задач
    # Та же конфигурация что и backend

  frontend:
    ports: ["3000:3000"]
    volumes: ["./frontend:/app"]
    command: npm start

  db:
    image: postgres:15
    ports: ["5432:5432"]
    volumes: [postgres_data]
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: generator

  redis:
    image: redis:7
    ports: ["6379:6379"]
    volumes: [redis_data]
```

### 6.2 Переменные окружения

**Backend (.env):**
```env
APP_NAME=REGGY
DEBUG=True
SECRET_KEY=your-secret-key

# AI
PIAPI_KEY=your-piapi-key
GPT_MODEL=gpt-4o-mini
KLING_MODEL=2.1

# Database
DATABASE_URL=sqlite:///./generator.db

# Redis
REDIS_URL=redis://localhost:6379/0

# OAuth (опционально)
INSTAGRAM_CLIENT_ID=...
TIKTOK_CLIENT_ID=...
YOUTUBE_CLIENT_ID=...
```

**Frontend (.env):**
```env
VITE_API_URL=http://localhost:8000
```

---

## 7. Workflow архитектура

### 7.1 8-этапный генерационный пайплайн

Каждый этап проходит через состояния:
1. **IN_PROGRESS** — вызов AI сервиса
2. **VALIDATING** — AI самовалидация
3. **AWAITING_APPROVAL** — чекпоинт для пользователя
4. **APPROVED** — пользователь принял контент
5. **COMPLETED** — этап завершен

| Этап | Вход | Выход | Сервис |
|------|------|-------|--------|
| Story | Тема, аудитория, настроение | Нарратив (JSON) | OpenAI |
| Description | Story | Детали сцены (модель, локация) | OpenAI |
| Prompt | Description | Промпт для генерации | OpenAI |
| Image | Prompt | URL изображения/видео | KLING |
| Scenario | Image, Description | Движения камеры, действия | OpenAI |
| Video | Image, Scenario | URL беззвучного видео | KLING |
| Audio | Video URL | 4 варианта аудио | KLING |
| Adaptation | Video + Audio | Данные для платформ | OpenAI |
| Publishing | Adapted data | URL постов | Social Service |

### 7.2 Режимы workflow

**MANUAL** — останавливается на каждом чекпоинте, пользователь одобряет/отклоняет

**AUTO** — выполняет все этапы последовательно, останавливается только при ошибках

---

## 8. Запуск для разработки

### Backend

```bash
cd generator/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd generator/frontend
npm install
npm run dev
```

### API документация

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 9. Ключевые файлы для разработки

| Задача | Файл |
|--------|------|
| Добавить API эндпоинт | `backend/app/api/*.py` |
| Добавить модель БД | `backend/app/models/*.py` |
| Добавить схему валидации | `backend/app/schemas/*.py` |
| Добавить страницу | `frontend/src/pages/*.tsx` |
| Добавить компонент | `frontend/src/components/*.tsx` |
| Добавить типы | `frontend/src/types/index.ts` |
| Изменить конфигурацию | `backend/app/core/config.py` |

---

## 10. Известные ограничения

- OAuth потоки реализованы частично
- S3 интеграция не реализована (локальное хранение файлов)
- Нет WebSocket поддержки для real-time обновлений
- KLING image generation возвращает видео (ограничение API)
