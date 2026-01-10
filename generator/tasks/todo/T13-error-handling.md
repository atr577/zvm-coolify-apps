---
id: T13
title: "Исправление Error Handling"
status: todo
priority: critical
created: 2026-01-10
updated: 2026-01-10
tags: []
depends_on: []
estimate: "1 день"
branch: ""
---

# Task 13: Исправление Error Handling

## Проблема

Утечка внутренних ошибок клиенту.

**Текущий код:**

```python
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```

**Что утекает:**
- Пути к файлам: `FileNotFoundError: /Users/gmartirosov/...`
- SQL ошибки: `UNIQUE constraint failed: users.email`
- API ключи в сообщениях ошибок
- Stack trace детали

## Цель

Безопасное логирование ошибок без утечки данных.

## Детальный план

### Phase 1: Централизованный Exception Handler (1-2 часа)

**Файл:** `backend/app/core/exceptions.py`

```python
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import traceback
from typing import Union

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base application exception"""
    def __init__(self, message: str, status_code: int = 500, internal_message: str = None):
        self.message = message
        self.status_code = status_code
        self.internal_message = internal_message or message
        super().__init__(self.message)


class ValidationError(AppException):
    """Validation failed"""
    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class NotFoundError(AppException):
    """Resource not found"""
    def __init__(self, resource: str = "Resource"):
        super().__init__(f"{resource} not found", status_code=404)


class ForbiddenError(AppException):
    """Access denied"""
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, status_code=403)


class AIServiceError(AppException):
    """AI service failed"""
    def __init__(self, internal_message: str):
        super().__init__(
            message="AI service temporarily unavailable. Please try again.",
            status_code=502,
            internal_message=internal_message
        )


class RateLimitError(AppException):
    """Rate limit exceeded"""
    def __init__(self):
        super().__init__(
            message="Too many requests. Please wait and try again.",
            status_code=429
        )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handler for AppException"""
    logger.error(
        f"AppException: {exc.internal_message}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code
        }
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handler for FastAPI HTTPException"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler for unhandled exceptions"""
    # Log full traceback
    logger.exception(
        f"Unhandled exception: {type(exc).__name__}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "traceback": traceback.format_exc()
        }
    )

    # Return generic message
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please contact support if the issue persists."}
    )


def setup_exception_handlers(app):
    """Register exception handlers"""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
```

### Phase 2: Обновление main.py (30 мин)

**Файл:** `backend/app/main.py`

```python
from app.core.exceptions import setup_exception_handlers

# После создания app
app = FastAPI(...)

# Регистрируем handlers
setup_exception_handlers(app)
```

### Phase 3: Обновление workflow.py (2-3 часа)

**До:**

```python
@router.post("/generate-story")
async def generate_story(...):
    video = db.query(Video).filter(Video.id == request.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    try:
        story_data = await openai_service.generate_story(...)
        # ...
    except Exception as e:
        step.status = WorkflowStatus.FAILED
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))  # ПЛОХО!
```

**После:**

```python
from app.core.exceptions import NotFoundError, ForbiddenError, AIServiceError
from app.services.piapi_client import PiAPIError

@router.post("/generate-story")
async def generate_story(...):
    video = db.query(Video).filter(Video.id == request.video_id).first()
    if not video:
        raise NotFoundError("Video")

    if not has_access(db, video, current_user):
        raise ForbiddenError("You don't have access to this video")

    try:
        story_data = await openai_service.generate_story(...)
        # ...
    except PiAPIError as e:
        step.status = WorkflowStatus.FAILED
        db.commit()
        raise AIServiceError(str(e))
    except ValueError as e:
        # Known validation error - safe to show
        raise ValidationError(str(e))
    # Unhandled exceptions будут пойманы global handler
```

### Phase 4: Обновление PiAPI client (1 час)

**Файл:** `backend/app/services/piapi_client.py`

```python
class PiAPIError(Exception):
    """Base exception for PiAPI - НЕ включает sensitive данные"""
    def __init__(self, message: str, original_error: str = None):
        # Очищаем сообщение от потенциально sensitive данных
        clean_message = self._sanitize(message)
        super().__init__(clean_message)
        self._original = original_error  # Только для логирования

    @staticmethod
    def _sanitize(message: str) -> str:
        """Remove potentially sensitive data from error message"""
        import re
        # Remove API keys
        message = re.sub(r'(api[_-]?key|token|secret)[=:]\s*["\']?[\w-]+["\']?', '[REDACTED]', message, flags=re.I)
        # Remove file paths
        message = re.sub(r'/[\w/.-]+', '[PATH]', message)
        return message


async def _make_request(self, ...):
    try:
        # ...
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text if e.response else str(e)
        logger.error(f"HTTP error: {error_detail}")  # Логируем полностью
        raise PiAPIError(
            "Request to AI service failed",
            original_error=error_detail  # Сохраняем для отладки
        )
```

### Phase 5: Настройка логирования (1 час)

**Файл:** `backend/app/core/logging_config.py`

```python
import logging
import sys
from logging.handlers import RotatingFileHandler
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """Format logs as JSON for production"""

    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # Add extra fields
        if hasattr(record, "path"):
            log_record["path"] = record.path
        if hasattr(record, "method"):
            log_record["method"] = record.method
        if hasattr(record, "status_code"):
            log_record["status_code"] = record.status_code
        if hasattr(record, "traceback"):
            log_record["traceback"] = record.traceback

        # Exception info
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record)


def setup_logging(debug: bool = False):
    """Configure application logging"""

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)

    if debug:
        # Human-readable for development
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
    else:
        # JSON for production
        console_handler.setFormatter(JSONFormatter())

    root_logger.addHandler(console_handler)

    # File handler for errors
    error_handler = RotatingFileHandler(
        'logs/error.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(error_handler)

    # Silence noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
```

**Обновить `main.py`:**

```python
from app.core.logging_config import setup_logging
from app.core.config import settings

# В начале файла
setup_logging(debug=settings.DEBUG)
```

## Чеклист

- [ ] Создать `app/core/exceptions.py`
- [ ] Добавить custom exceptions (AppException, AIServiceError, etc.)
- [ ] Создать exception handlers
- [ ] Зарегистрировать handlers в main.py
- [ ] Обновить workflow.py (заменить все `raise HTTPException(500, str(e))`)
- [ ] Обновить PiAPIError для sanitization
- [ ] Настроить JSON logging
- [ ] Добавить файл для error logs
- [ ] Протестировать с разными типами ошибок

## Файлы для обновления

| Файл | Изменения |
|------|-----------|
| `app/core/exceptions.py` | Новый файл |
| `app/core/logging_config.py` | Новый файл |
| `app/main.py` | Регистрация handlers |
| `app/api/workflow.py` | Заменить HTTPException(500) |
| `app/api/projects.py` | Заменить HTTPException |
| `app/api/videos.py` | Заменить HTTPException |
| `app/services/piapi_client.py` | Sanitize errors |

## Примеры ответов

**До (плохо):**
```json
{
  "detail": "FileNotFoundError: /Users/gmartirosov/expremients/RE/generator/data/uploads/file.mp4"
}
```

**После (хорошо):**
```json
{
  "detail": "AI service temporarily unavailable. Please try again."
}
```

**Лог (для отладки):**
```json
{
  "timestamp": "2026-01-09T12:00:00Z",
  "level": "ERROR",
  "message": "AI service error",
  "path": "/api/workflow/generate-video",
  "method": "POST",
  "traceback": "..."
}
```

## Метрики успеха

| Метрика | До | После |
|---------|-----|-------|
| Утечка путей | Да | Нет |
| Утечка SQL | Да | Нет |
| Утечка API ключей | Возможно | Нет |
| Логирование ошибок | Частичное | Полное |

---

**Статус:** Готова к выполнению (независима от других задач)
**Ответственный:** TBD
