# Quick Start Guide

## Быстрый старт

### 1. Подготовка

Клонируйте репозиторий и перейдите в папку проекта:

```bash
cd generator
```

### 2. Настройка Backend

```bash
# Перейдите в папку backend
cd backend

# Создайте виртуальное окружение
python -m venv venv

# Активируйте виртуальное окружение
# MacOS/Linux:
source venv/bin/activate
# Windows:
# venv\Scripts\activate

# Установите зависимости
pip install -r requirements.txt

# Скопируйте файл с примером переменных окружения
cp .env.example .env

# Откройте .env и заполните необходимые API ключи:
# - OPENAI_API_KEY (обязательно)
# - PIAPI_KEY (обязательно для KLING)
# - SECRET_KEY (сгенерируйте случайную строку)
```

Минимальная конфигурация `.env`:

```env
SECRET_KEY=your-secret-key-here
OPENAI_API_KEY=sk-your-openai-key
PIAPI_KEY=your-piapi-key
DATABASE_URL=sqlite:///./generator.db
REDIS_URL=redis://localhost:6379/0
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

### 3. Настройка Frontend

```bash
# Откройте новый терминал и перейдите в папку frontend
cd generator/frontend

# Установите зависимости
npm install

# Скопируйте файл с примером переменных окружения
cp .env.example .env
```

Содержимое `frontend/.env`:

```env
VITE_API_URL=http://localhost:8000
```

### 4. Запуск Redis (для background tasks)

#### MacOS (с Homebrew):
```bash
brew install redis
brew services start redis
```

#### Linux:
```bash
sudo apt-get install redis-server
sudo systemctl start redis
```

#### Windows:
Скачайте Redis для Windows или используйте Docker:
```bash
docker run -d -p 6379:6379 redis:7-alpine
```

### 5. Запуск приложения

Откройте **3 терминала**:

#### Терминал 1 - Backend API:
```bash
cd generator/backend
source venv/bin/activate  # или venv\Scripts\activate для Windows
uvicorn app.main:app --reload
```

Backend будет доступен на http://localhost:8000

#### Терминал 2 - Celery Worker (для фоновых задач):
```bash
cd generator/backend
source venv/bin/activate
celery -A app.core.celery_app worker --loglevel=info
```

#### Терминал 3 - Frontend:
```bash
cd generator/frontend
npm run dev
```

Frontend будет доступен на http://localhost:3000

### 6. Первое использование

1. Откройте браузер: http://localhost:3000
2. Нажмите "New Project"
3. Введите название проекта
4. Следуйте workflow шагам:
   - Генерация сюжета
   - Детальное описание
   - Промпт для KLING
   - Генерация изображения
   - Сценарий видео
   - Генерация видео
   - Адаптация для платформ
   - Публикация

### 7. Использование Docker (альтернатива)

Если у вас установлен Docker:

```bash
cd generator
docker-compose up -d
```

Это запустит все сервисы автоматически:
- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### 8. API Документация

После запуска backend откройте:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Получение API ключей

### OpenAI API
1. Зайдите на https://platform.openai.com
2. Создайте аккаунт или войдите
3. Перейдите в API Keys
4. Создайте новый ключ

### KLING (через PiAPI)
1. Зайдите на https://piapi.ai
2. Зарегистрируйтесь
3. Пополните баланс
4. Скопируйте API ключ из dashboard

### Instagram API (опционально)
1. Создайте Facebook App: https://developers.facebook.com
2. Добавьте Instagram Graph API
3. Получите Access Token для Business аккаунта

### TikTok API (опционально)
1. Зайдите на https://developers.tiktok.com
2. Создайте приложение
3. Запросите доступ к Content Posting API

### YouTube API (опционально)
1. Зайдите в Google Cloud Console
2. Создайте проект
3. Включите YouTube Data API v3
4. Создайте OAuth 2.0 credentials

## Troubleshooting

### Backend не запускается:
- Проверьте, что виртуальное окружение активировано
- Убедитесь, что все зависимости установлены: `pip install -r requirements.txt`
- Проверьте `.env` файл

### Frontend не запускается:
- Убедитесь, что Node.js установлен (версия 18+)
- Удалите `node_modules` и `package-lock.json`, затем `npm install`

### Redis ошибки:
- Убедитесь, что Redis запущен: `redis-cli ping` (должен вернуть PONG)
- Проверьте `REDIS_URL` в `.env`

### CORS ошибки:
- Проверьте `CORS_ORIGINS` в backend `.env`
- Убедитесь, что frontend и backend URL совпадают

## Дополнительная информация

Полная документация в [README.md](./README.md)
