# Troubleshooting

## Проблема: autoenv блокирует команды

### Симптомы
```
autoenv: WARNING:
autoenv: This is the first time you are about to source /path/to/.env
autoenv: Are you sure you want to allow this? (y/N)
```

### Причина
В вашей системе установлен **autoenv** (или **direnv**), который автоматически загружает файл `.env` при входе в директорию и запрашивает подтверждение.

### ❌ НЕ ДЕЛАТЬ ТАК:
- ~~`source venv/bin/activate`~~ внутри backend/ - autoenv блокирует cd
- ~~Запускать команды через `cd backend && command`~~ - autoenv блокирует

### ✅ ПРАВИЛЬНОЕ РЕШЕНИЕ:

#### Вариант 1: Отключить autoenv навсегда (рекомендуется)

1. Откройте `~/.zshrc` (или `~/.bashrc` для bash):
```bash
nano ~/.zshrc
```

2. Найдите и закомментируйте строки:
```bash
# source ~/.autoenv/activate.sh
# source $(brew --prefix autoenv)/activate.sh
# eval "$(direnv hook zsh)"
```

3. Сохраните и перезапустите терминал:
```bash
source ~/.zshrc
```

#### Вариант 2: Временно отключить в текущей сессии

```bash
unset AUTOENV_ENABLE_PROMPT
unset AUTOENV_AUTH_FILE
unalias cd 2>/dev/null
```

#### Вариант 3: Использовать абсолютные пути (обход)

```bash
# Вместо:
# cd backend && source venv/bin/activate

# Делать:
/Users/gmartirosov/expremients/RE/generator/backend/venv/bin/pip install -r requirements.txt
/Users/gmartirosov/expremients/RE/generator/backend/venv/bin/uvicorn app.main:app
```

---

## Проблема: PostgreSQL ошибки при установке

### Симптомы
```
Error: pg_config executable not found.
psycopg2 requires PostgreSQL to build
```

### Решение
Убраны PostgreSQL зависимости из requirements.txt (проект использует SQLite).

**Если нужен PostgreSQL:**
```bash
# macOS
brew install postgresql

# Ubuntu/Debian
sudo apt-get install postgresql libpq-dev
```

---

## Проблема: Backend не запускается

### Проверка 1: Установлены ли зависимости?

```bash
cd /Users/gmartirosov/expremients/RE/generator/backend
./venv/bin/python -c "import fastapi; print('✅ FastAPI installed')"
./venv/bin/python -c "import uvicorn; print('✅ Uvicorn installed')"
```

### Проверка 2: Настроен ли .env?

```bash
cd /Users/gmartirosov/expremients/RE/generator/backend
grep AIMLAPI_KEY .env
# Должно показать: AIMLAPI_KEY=211d059252fa4fa3b2489e89f19eb6c2
```

### Проверка 3: Запуск вручную

```bash
cd /Users/gmartirosov/expremients/RE/generator/backend
./venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Проблема: Frontend не запускается

### Проверка 1: Установлены ли зависимости?

```bash
cd /Users/gmartirosov/expremients/RE/generator/frontend
ls node_modules/ | head -5
# Должны быть папки с пакетами
```

### Проверка 2: Запуск вручную

```bash
cd /Users/gmartirosov/expremients/RE/generator/frontend
npm run dev
```

---

## Правильный порядок запуска (без autoenv)

### Способ 1: Использовать start.sh после отключения autoenv

```bash
# 1. Отключите autoenv (см. выше)
# 2. Перезапустите терминал
# 3. Запустите:
cd /Users/gmartirosov/expremients/RE/generator
./start.sh
```

### Способ 2: Запуск вручную с абсолютными путями

#### Терминал 1 - Backend:
```bash
# Установка (только первый раз)
/usr/bin/python3 -m venv /Users/gmartirosov/expremients/RE/generator/backend/venv
/Users/gmartirosov/expremients/RE/generator/backend/venv/bin/pip install -r /Users/gmartirosov/expremients/RE/generator/backend/requirements.txt

# Запуск
cd /Users/gmartirosov/expremients/RE/generator/backend
./venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Терминал 2 - Frontend:
```bash
# Установка (только первый раз)
cd /Users/gmartirosov/expremients/RE/generator/frontend
npm install

# Запуск
npm run dev
```

### Способ 3: Запуск в фоне

```bash
# Backend
nohup /Users/gmartirosov/expremients/RE/generator/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &

# Frontend
cd /Users/gmartirosov/expremients/RE/generator/frontend
nohup npm run dev > frontend.log 2>&1 &

# Проверка
ps aux | grep -E "uvicorn|vite"
```

---

## Остановка сервисов

```bash
# Вариант 1: Скрипт
./stop.sh

# Вариант 2: Вручную
pkill -f uvicorn
pkill -f vite

# Вариант 3: По PID
ps aux | grep uvicorn
kill <PID>
```

---

## Логи

```bash
# Backend логи (если запущен через start.sh)
tail -f /Users/gmartirosov/expremients/RE/generator/backend/backend.log

# Frontend логи
tail -f /Users/gmartirosov/expremients/RE/generator/frontend/frontend.log

# Или если запущен вручную, смотрите вывод в терминале
```
