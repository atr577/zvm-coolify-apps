# Task 15: VPS Deployment via Coolify

## Цель
Развернуть REGGY на VPS с использованием Coolify.

## Текущее состояние
- Docker Compose есть, но для dev
- Dockerfiles есть, но frontend запускает dev server
- Coolify проект создан

## План

### Phase 1: Production Dockerfiles

#### 1.1 Frontend (multi-stage build + nginx)
```dockerfile
# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

#### 1.2 nginx.conf для SPA
```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### 1.3 Backend (production ready)
```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p data/uploads data/generated

EXPOSE 8000

# Production: без --reload, с workers
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

### Phase 2: Production docker-compose

```yaml
version: '3.8'

services:
  frontend:
    build:
      context: ./frontend
      args:
        VITE_API_URL: ${VITE_API_URL:-http://localhost:8000}
    restart: unless-stopped
    depends_on:
      - backend
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.frontend.rule=Host(`${DOMAIN}`)"
      - "traefik.http.services.frontend.loadbalancer.server.port=80"

  backend:
    build: ./backend
    restart: unless-stopped
    env_file: ./backend/.env
    environment:
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@db:5432/${DB_NAME}
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    volumes:
      - backend_data:/app/data
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.backend.rule=Host(`api.${DOMAIN}`)"
      - "traefik.http.services.backend.loadbalancer.server.port=8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/"]
      interval: 30s
      timeout: 10s
      retries: 3

  celery:
    build: ./backend
    restart: unless-stopped
    env_file: ./backend/.env
    environment:
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@db:5432/${DB_NAME}
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - backend_data:/app/data
    command: celery -A app.core.celery worker --loglevel=info

  db:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
  backend_data:
```

### Phase 3: Environment Variables

#### .env.production.example
```bash
# Domain
DOMAIN=reggy.example.com

# Database
DB_USER=reggy
DB_PASSWORD=<generate-secure-password>
DB_NAME=reggy

# Backend
SECRET_KEY=<generate-secure-key>
PIAPI_API_KEY=<your-piapi-key>
DEBUG=false
MOCK_MODE=false

# Frontend (build-time)
VITE_API_URL=https://api.reggy.example.com
```

### Phase 4: Coolify Setup

1. **Подключить Git репозиторий**
   - Source: GitHub/GitLab
   - Branch: main
   - Build Pack: Docker Compose

2. **Настроить Environment Variables**
   - Скопировать из .env.production.example
   - Сгенерировать SECRET_KEY и DB_PASSWORD

3. **Настроить домены**
   - Frontend: reggy.example.com
   - Backend: api.reggy.example.com
   - SSL: Let's Encrypt (автоматически)

4. **Deploy**
   - Coolify сам соберёт и запустит
   - Проверить логи на ошибки

### Phase 5: Post-deployment

1. **Миграции БД**
   ```bash
   docker exec reggy-backend-1 alembic upgrade head
   ```

2. **Создать admin пользователя**
   ```bash
   docker exec -it reggy-backend-1 python -c "
   from app.db.base import SessionLocal
   from app.models.user import User
   from app.core.security import hash_password

   db = SessionLocal()
   admin = User(
       email='admin@example.com',
       hashed_password=hash_password('secure-password'),
       is_active=True,
       role='admin'
   )
   db.add(admin)
   db.commit()
   print('Admin created')
   "
   ```

3. **Проверить healthchecks**
   - https://reggy.example.com → Frontend
   - https://api.reggy.example.com → Backend API
   - https://api.reggy.example.com/docs → Swagger

## Файлы для создания/изменения

- [ ] `frontend/Dockerfile` — multi-stage build
- [ ] `frontend/nginx.conf` — SPA routing + API proxy
- [ ] `backend/Dockerfile` — production CMD
- [ ] `docker-compose.prod.yml` — production compose
- [ ] `.env.production.example` — template
- [ ] `docs/DEPLOYMENT.md` — инструкция

## Оценка
- Подготовка файлов: 1-2 часа
- Настройка Coolify: 30 мин
- Тестирование: 30 мин

## Риски
- CORS между frontend и backend на разных доменах
- Миграции при первом запуске
- Secrets в environment variables
