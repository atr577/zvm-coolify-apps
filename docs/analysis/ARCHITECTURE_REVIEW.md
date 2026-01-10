# Критический анализ архитектуры

## Резюме

Проект представляет собой MVP-стадию с рабочим функционалом, но содержит значительный технический долг, который затруднит масштабирование и поддержку.

**Общая оценка: 5/10**

| Категория | Оценка | Комментарий |
|-----------|--------|-------------|
| Структура кода | 4/10 | Монолитные файлы, дублирование |
| Безопасность | 5/10 | Базовая auth, но есть уязвимости |
| Тестирование | 1/10 | Полное отсутствие тестов |
| Масштабируемость | 4/10 | Синхронные операции, нет очередей |
| Поддерживаемость | 5/10 | Много deprecated кода, нет документации API |
| Frontend | 6/10 | Хорошая структура, но слабая типизация |

---

## Критические проблемы (P0)

### 1. Монолитный workflow.py — 1145 строк

**Файл:** `backend/app/api/workflow.py`

**Проблема:** Весь workflow сосредоточен в одном файле с массивным дублированием.

```python
# Этот паттерн повторяется 8+ раз:
step = get_or_create_step(db, video.id, StepType.XXX)
try:
    xxx_data = await openai_service.generate_xxx(...)
    step.content = xxx_data
    video.xxx_data = xxx_data
    video.current_step = StepType.XXX
    validation = await validate_and_save(db, step, xxx_data, "xxx")
    return {...}
except Exception as e:
    step.status = WorkflowStatus.FAILED
    db.commit()
    raise HTTPException(status_code=500, detail=str(e))
```

**Последствия:**
- Изменение логики требует правок в 8+ местах
- Высокий риск багов при рефакторинге
- Невозможно тестировать изолированно

**Рекомендация:**
```
backend/app/
├── services/
│   └── workflow/
│       ├── __init__.py
│       ├── base.py          # BaseWorkflowStep
│       ├── story.py         # StoryStep(BaseWorkflowStep)
│       ├── description.py   # DescriptionStep
│       ├── orchestrator.py  # WorkflowOrchestrator
│       └── state_machine.py # FSM для переходов
```

---

### 2. Отсутствие тестов

**Факт:** `generator/backend/tests/` — пустая директория.

**Последствия:**
- Невозможно безопасно рефакторить
- Регрессии не ловятся
- Нет уверенности в работоспособности

**Минимально необходимо:**
- Unit тесты для сервисов (openai_service, kling_service)
- Integration тесты для workflow endpoints
- E2E тесты для критического пути

---

### 3. Синхронные long-polling операции

**Файл:** `backend/app/services/piapi_client.py:337-383`

```python
async def wait_for_video(self, task_id: str, max_wait_time: int = 900, ...):
    while elapsed < max_wait_time:  # До 15 минут!
        result = await self.get_task_status(task_id)
        await asyncio.sleep(poll_interval)
```

**Проблема:** HTTP request висит до 15 минут, блокируя worker.

**Последствия:**
- При 10 concurrent генерациях — 10 зависших workers
- Timeout на reverse proxy (nginx default: 60s)
- Плохой UX — нет прогресса

**Рекомендация:**
1. Создавать task через Celery
2. Возвращать task_id сразу
3. Polling на фронтенде через `/api/workflow/status/{task_id}`
4. WebSocket для real-time обновлений

---

### 4. Утечка данных при ошибках

**Файл:** `backend/app/api/workflow.py` (многократно)

```python
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```

**Проблема:** Внутренние ошибки (stack traces, пути файлов, API ключи в сообщениях) уходят клиенту.

**Рекомендация:**
```python
except PiAPIError as e:
    logger.error(f"AI generation failed: {e}")
    raise HTTPException(status_code=502, detail="AI service temporarily unavailable")
except Exception as e:
    logger.exception("Unexpected error in workflow")
    raise HTTPException(status_code=500, detail="Internal server error")
```

---

### 5. Дублирование данных Video ↔ WorkflowStep

**Модели:**
- `Video.story_data`, `Video.description_data`, etc.
- `WorkflowStep.content` — те же данные

**Проблема:** Два источника истины, могут рассинхронизироваться.

**Рекомендация:** Оставить данные только в `WorkflowStep`, добавить методы в Video:
```python
@property
def story_data(self):
    step = next((s for s in self.workflow_steps if s.step_type == StepType.STORY), None)
    return step.content if step else None
```

---

## Серьёзные проблемы (P1)

### 6. State Machine без валидации переходов

**Проблема:** `WorkflowStatus` — просто enum. Нет защиты от невалидных переходов.

```python
# Текущий код позволяет:
step.status = WorkflowStatus.COMPLETED  # Из любого состояния!
```

**Рекомендация:** Использовать `transitions` или `python-statemachine`:
```python
VALID_TRANSITIONS = {
    WorkflowStatus.PENDING: [WorkflowStatus.IN_PROGRESS],
    WorkflowStatus.IN_PROGRESS: [WorkflowStatus.VALIDATING, WorkflowStatus.FAILED],
    WorkflowStatus.VALIDATING: [WorkflowStatus.AWAITING_APPROVAL, WorkflowStatus.VALIDATION_FAILED],
    # ...
}

def transition_to(self, new_status: WorkflowStatus):
    if new_status not in VALID_TRANSITIONS.get(self.status, []):
        raise InvalidTransitionError(f"Cannot transition from {self.status} to {new_status}")
    self.status = new_status
```

---

### 7. Множественные db.commit() без транзакций

**Файл:** `backend/app/api/workflow.py:634-923` (approve_step)

```python
db.commit()  # 1
db.refresh(audio_step)
# ... логика ...
db.commit()  # 2
# ... ещё логика ...
db.commit()  # 3
```

**Проблема:** Если ошибка между commit'ами — данные в inconsistent state.

**Рекомендация:**
```python
from contextlib import contextmanager

@contextmanager
def transaction(db: Session):
    try:
        yield
        db.commit()
    except:
        db.rollback()
        raise
```

---

### 8. Frontend: слабая типизация API

**Файл:** `frontend/src/services/api.ts`

```typescript
generateDescription: (videoId: number, storyData: any) =>  // any!
    api.post('/api/workflow/generate-description', {...}),
```

**Проблема:** `any` типы убивают type safety.

**Рекомендация:** Создать типы для всех request/response:
```typescript
interface GenerateDescriptionRequest {
    video_id: number;
    story_data: StoryData;
}
interface GenerateDescriptionResponse {
    step_id: number;
    content: DescriptionData;
    validation: ValidationResult;
}
```

---

### 9. Нет interceptor для token refresh

**Файл:** `frontend/src/services/api.ts`

```typescript
const api = axios.create({...})
// Нет interceptor'ов!
```

**Проблема:** При 401 пользователь просто выбрасывается, без попытки refresh.

**Рекомендация:**
```typescript
api.interceptors.response.use(
    response => response,
    async error => {
        if (error.response?.status === 401) {
            const newToken = await refreshToken();
            error.config.headers.Authorization = `Bearer ${newToken}`;
            return api.request(error.config);
        }
        return Promise.reject(error);
    }
);
```

---

### 10. Deprecated код не удалён

**Файл:** `backend/app/core/config.py`
```python
AIMLAPI_KEY: str = ""  # Legacy AIMLAPI support (deprecated)
INSTAGRAM_ACCESS_TOKEN: str = ""  # Deprecated: use OAuth flow instead
TIKTOK_CLIENT_KEY: str = ""  # Deprecated: use TIKTOK_CLIENT_ID
```

**Файл:** `backend/app/models/video.py`
```python
image_prompt = Column(Text, nullable=True)  # Deprecated: use prompt_data instead
```

**Проблема:** Увеличивает cognitive load, запутывает новых разработчиков.

**Рекомендация:** Удалить deprecated поля или создать миграцию.

---

## Умеренные проблемы (P2)

### 11. Нет rate limiting

**Проблема:** Любой authenticated пользователь может спамить AI endpoints.

**Последствия:**
- Исчерпание API лимитов
- DoS на сервис
- Непредсказуемые счета

**Рекомендация:** `slowapi` или Redis-based rate limiter:
```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@router.post("/generate-story")
@limiter.limit("10/minute")
async def generate_story(...):
```

---

### 12. JSON поля без валидации схемы

**Проблема:** `story_data`, `description_data` — просто `Column(JSON)`.

```python
video.story_data = {"random": "garbage"}  # Валидно!
```

**Рекомендация:** Pydantic модели для JSON контента:
```python
class StoryContent(BaseModel):
    concept: str
    hook: str
    hook_type: Literal["visual", "text", "audio"]
    climax: str
    tone: str
    pacing: str
    emotional_trigger: str
    duration: int
```

---

### 13. Hardcoded промпты в коде

**Файл:** `backend/app/services/openai_service.py`

```python
prompt = f"""
Сгенерируй идею для вирального короткого видео...
"""
```

**Проблема:**
- Изменение промптов требует деплоя
- Нельзя A/B тестировать
- Нет версионирования

**Рекомендация:** Вынести в БД или файлы конфигурации:
```
prompts/
├── story_v1.txt
├── story_v2.txt
└── description_v1.txt
```

---

### 14. Нет health checks для зависимостей

**Файл:** `backend/app/main.py`
```python
@app.get("/health")
async def health():
    return {"status": "healthy"}  # Всегда healthy!
```

**Проблема:** Health check не проверяет:
- Подключение к БД
- Доступность Redis
- Валидность API ключей

**Рекомендация:**
```python
@app.get("/health")
async def health():
    checks = {}
    try:
        db.execute("SELECT 1")
        checks["database"] = "ok"
    except:
        checks["database"] = "fail"
    # ...
    return {"status": "healthy" if all(v == "ok" for v in checks.values()) else "unhealthy", "checks": checks}
```

---

### 15. Celery настроен, но не используется

**Файлы:**
- `backend/app/core/celery_app.py` — существует
- `docker-compose.yml` — celery worker запущен
- `workflow.py` — всё синхронно/async в request

**Рекомендация:** Перевести генерацию на Celery tasks:
```python
@celery.task
def generate_video_task(video_id: int):
    # Long-running generation
    pass

@router.post("/generate-video")
async def generate_video(...):
    task = generate_video_task.delay(video_id)
    return {"task_id": task.id, "status": "queued"}
```

---

## Архитектурные рекомендации

### Краткосрочные (1-2 недели)

1. **Добавить базовые тесты** — хотя бы для workflow endpoints
2. **Исправить error handling** — не утекать внутренние ошибки
3. **Добавить транзакции** — один commit на операцию
4. **Rate limiting** — защита от злоупотреблений

### Среднесрочные (1-2 месяца)

1. **Рефакторинг workflow.py** — разбить на классы
2. **Перевести на Celery** — async генерация
3. **WebSocket** — real-time обновления статуса
4. **Типизация frontend** — убрать все `any`
5. **State machine** — валидация переходов

### Долгосрочные

1. **Микросервисы** — выделить AI generation в отдельный сервис
2. **Event sourcing** — для аудита workflow
3. **S3 integration** — для production файлов
4. **Monitoring** — Prometheus + Grafana

---

## Что сделано хорошо

1. **Структура проекта** — логичное разделение на api/models/schemas/services
2. **PiAPI client** — хороший retry logic, кэширование
3. **Workspace model** — правильная multi-tenancy архитектура
4. **Frontend structure** — хорошее разделение pages/components
5. **Docker setup** — готов к production deployment
6. **Validation system** — AI-валидация на каждом шаге — инновационно

---

## Приоритетный план действий

| Приоритет | Задача | Effort | Impact |
|-----------|--------|--------|--------|
| P0 | Добавить тесты для критического пути | 3d | Высокий |
| P0 | Исправить error handling | 1d | Высокий |
| P0 | Обернуть workflow в транзакции | 1d | Высокий |
| P1 | Rate limiting | 1d | Средний |
| P1 | Перевести на Celery | 1w | Высокий |
| P1 | Рефакторинг workflow.py | 1w | Высокий |
| P2 | Типизация frontend | 3d | Средний |
| P2 | WebSocket для статусов | 3d | Средний |
| P2 | Удалить deprecated код | 1d | Низкий |
