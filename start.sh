#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Запуск REGGY${NC}\n"

# Получаем директорию скрипта
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# ============ BACKEND ============
echo -e "${YELLOW}📦 Настройка Backend...${NC}"

cd "$BACKEND_DIR"

# Проверяем наличие venv
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Создание виртуального окружения...${NC}"
    python3 -m venv venv
fi

# Проверяем, установлены ли зависимости
if [ ! -f "venv/.dependencies_installed" ]; then
    echo -e "${YELLOW}Установка зависимостей Backend...${NC}"
    venv/bin/pip install -r requirements.txt
    touch venv/.dependencies_installed
else
    echo -e "${GREEN}✓ Зависимости Backend уже установлены${NC}"
fi

# Создаем директории для данных
mkdir -p data/uploads data/generated

# Запускаем Backend в фоне (используем прямой путь к uvicorn)
echo -e "${YELLOW}Запуск Backend сервера...${NC}"
venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > "$SCRIPT_DIR/.backend.pid"
echo -e "${GREEN}✓ Backend запущен (PID: $BACKEND_PID)${NC}"

# ============ FRONTEND ============
echo -e "\n${YELLOW}📦 Настройка Frontend...${NC}"

cd "$FRONTEND_DIR"

# Проверяем наличие node_modules
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Установка зависимостей Frontend...${NC}"
    npm install
else
    echo -e "${GREEN}✓ Зависимости Frontend уже установлены${NC}"
fi

# Освобождаем порт 3000 если занят
FRONTEND_PORT=3000
if lsof -i :$FRONTEND_PORT -t > /dev/null 2>&1; then
    echo -e "${YELLOW}Порт $FRONTEND_PORT занят, освобождаем...${NC}"
    lsof -i :$FRONTEND_PORT -t | xargs kill -9 2>/dev/null
    sleep 1
fi

# Запускаем Frontend в фоне
echo -e "${YELLOW}Запуск Frontend сервера...${NC}"
npm run dev > frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > "$SCRIPT_DIR/.frontend.pid"
echo -e "${GREEN}✓ Frontend запущен (PID: $FRONTEND_PID)${NC}"

# ============ ГОТОВО ============
echo -e "\n${GREEN}✅ Все сервисы запущены!${NC}\n"

# Ждём немного чтобы Vite записал порт в лог
sleep 2

# Парсим реальный порт из логов (fallback если 3000 всё ещё занят)
ACTUAL_PORT=$(grep -oE 'localhost:[0-9]+' "$FRONTEND_DIR/frontend.log" | head -1 | cut -d: -f2)
if [ -z "$ACTUAL_PORT" ]; then
    ACTUAL_PORT=$FRONTEND_PORT
fi

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}  🌐 Backend API:                      ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}     ${GREEN}http://localhost:8000${NC}              ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}     ${GREEN}http://localhost:8000/docs${NC}        ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}                                        ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}  🎨 Frontend App:                     ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}     ${GREEN}http://localhost:${ACTUAL_PORT}${NC}              ${BLUE}║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}\n"

echo -e "${YELLOW}📝 Логи:${NC}"
echo -e "   Backend:  tail -f $BACKEND_DIR/backend.log"
echo -e "   Frontend: tail -f $FRONTEND_DIR/frontend.log"
echo -e "\n${YELLOW}🛑 Остановка:${NC} ./stop.sh\n"

# Даём ещё секунду на стабилизацию
sleep 1

# Проверяем, что серверы работают
if kill -0 $BACKEND_PID 2>/dev/null && kill -0 $FRONTEND_PID 2>/dev/null; then
    echo -e "${GREEN}✓ Оба сервера успешно запущены и работают!${NC}\n"
else
    echo -e "${RED}⚠️  Проверьте логи - возможно, есть ошибки запуска${NC}\n"
fi
