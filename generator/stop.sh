#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛑 Остановка REGGY${NC}\n"

# Получаем директорию скрипта
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Останавливаем Backend
if [ -f "$SCRIPT_DIR/.backend.pid" ]; then
    BACKEND_PID=$(cat "$SCRIPT_DIR/.backend.pid")
    if kill -0 $BACKEND_PID 2>/dev/null; then
        echo -e "${YELLOW}Остановка Backend (PID: $BACKEND_PID)...${NC}"
        kill $BACKEND_PID
        echo -e "${GREEN}✓ Backend остановлен${NC}"
    else
        echo -e "${YELLOW}Backend уже не работает${NC}"
    fi
    rm "$SCRIPT_DIR/.backend.pid"
else
    echo -e "${YELLOW}PID файл Backend не найден${NC}"
fi

# Останавливаем Frontend
if [ -f "$SCRIPT_DIR/.frontend.pid" ]; then
    FRONTEND_PID=$(cat "$SCRIPT_DIR/.frontend.pid")
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        echo -e "${YELLOW}Остановка Frontend (PID: $FRONTEND_PID)...${NC}"
        kill $FRONTEND_PID
        echo -e "${GREEN}✓ Frontend остановлен${NC}"
    else
        echo -e "${YELLOW}Frontend уже не работает${NC}"
    fi
    rm "$SCRIPT_DIR/.frontend.pid"
else
    echo -e "${YELLOW}PID файл Frontend не найден${NC}"
fi

# Убиваем возможные оставшиеся процессы uvicorn и vite
echo -e "\n${YELLOW}Проверка оставшихся процессов...${NC}"
pkill -f "uvicorn app.main:app" 2>/dev/null && echo -e "${GREEN}✓ Убиты процессы uvicorn${NC}"
pkill -f "vite" 2>/dev/null && echo -e "${GREEN}✓ Убиты процессы vite${NC}"

echo -e "\n${GREEN}✅ Все сервисы остановлены!${NC}\n"
