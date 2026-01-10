---
id: T16
title: "Prompt Preview & Edit в Manual Mode"
status: todo
priority: medium
created: 2026-01-10
updated: 2026-01-10
tags: []
depends_on: []
estimate: ""
branch: ""
---

# Task 16: Prompt Preview & Edit в Manual Mode

## Цель
Дать возможность просматривать и редактировать промты на каждом шаге генерации перед отправкой в AI. При ручном редактировании — сохранять с пометкой.

## User Story
```
Как создатель контента в Manual Mode,
я хочу видеть и редактировать промт перед каждым шагом,
чтобы контролировать что именно отправляется в AI.
```

## Новый Flow

### Было (текущий Manual Mode):
```
┌─────────┐     ┌──────────┐     ┌────────┐     ┌─────────┐
│ Кнопка  │ ──► │ AI генер.│ ──► │Результат│ ──► │ Approve │
│ Generate│     │ (скрыто) │     │         │     │ /Reject │
└─────────┘     └──────────┘     └────────┘     └─────────┘
```

### Станет:
```
┌─────────┐     ┌──────────┐     ┌─────────┐     ┌──────────┐     ┌────────┐     ┌─────────┐
│ Prepare │ ──► │ Preview  │ ──► │  Edit   │ ──► │ AI генер.│ ──► │Результат│ ──► │ Approve │
│  Step   │     │  Prompt  │     │(optional)│     │          │     │         │     │ /Reject │
└─────────┘     └──────────┘     └─────────┘     └──────────┘     └────────┘     └─────────┘
```

## Требования

### Функциональные

1. **Preview Prompt**
   - На каждом шаге показываем промт ДО отправки в AI
   - Промт форматирован и читаем (не JSON blob)
   - Показываем system prompt + user prompt отдельно

2. **Edit Prompt**
   - Textarea с возможностью редактирования
   - Подсветка синтаксиса (опционально)
   - Кнопка "Reset to default" — вернуть оригинальный

3. **Save Edited Prompt**
   - Если промт изменён — сохранять в `WorkflowStep.custom_prompt`
   - Флаг `WorkflowStep.prompt_manually_edited = True`
   - Сохранять оригинальный промт в `WorkflowStep.original_prompt`

4. **Audit Trail**
   - В истории шага видно: был ли промт изменён
   - Можно сравнить original vs custom

## Технический дизайн

### Backend

#### Новые поля в WorkflowStep
```python
# app/models/workflow_step.py

class WorkflowStep(Base):
    # ... existing fields ...

    # Prompt tracking
    original_prompt = Column(JSON, nullable=True)      # Промт сгенерированный системой
    custom_prompt = Column(JSON, nullable=True)        # Промт после ручного редактирования
    prompt_manually_edited = Column(Boolean, default=False)
```

#### Новый endpoint: Preview Prompt
```python
# POST /api/workflow/preview-prompt
# Возвращает промт который будет отправлен, без выполнения

class PreviewPromptRequest(BaseModel):
    video_id: int
    step_type: StepType
    # Контекст для генерации промта
    context: Optional[dict] = None  # story_data, description_data, etc.

class PreviewPromptResponse(BaseModel):
    system_prompt: str
    user_prompt: str
    full_context: dict  # Для дебага
```

#### Модификация generate endpoints
```python
# Все generate endpoints принимают optional custom_prompt

class GenerateStoryRequest(BaseModel):
    video_id: int
    # ... existing fields ...
    custom_prompt: Optional[dict] = None  # {"system": "...", "user": "..."}
```

#### Логика сохранения
```python
async def generate_story(request: GenerateStoryRequest, ...):
    # 1. Генерируем оригинальный промт
    original = build_story_prompt(request)

    # 2. Используем custom если передан
    prompt_to_use = request.custom_prompt or original

    # 3. Сохраняем в step
    step.original_prompt = original
    if request.custom_prompt:
        step.custom_prompt = request.custom_prompt
        step.prompt_manually_edited = True

    # 4. Отправляем в AI
    result = await openai_service.generate(prompt_to_use)
```

### Frontend

#### Новый компонент: PromptEditor
```tsx
// src/components/PromptEditor.tsx

interface PromptEditorProps {
  systemPrompt: string;
  userPrompt: string;
  onSystemChange: (value: string) => void;
  onUserChange: (value: string) => void;
  onReset: () => void;
  isModified: boolean;
}

const PromptEditor: React.FC<PromptEditorProps> = ({...}) => {
  return (
    <div className="prompt-editor">
      <div className="prompt-section">
        <label>System Prompt</label>
        <textarea value={systemPrompt} onChange={...} />
      </div>
      <div className="prompt-section">
        <label>User Prompt</label>
        <textarea value={userPrompt} onChange={...} />
      </div>
      {isModified && (
        <div className="modified-badge">
          ✏️ Manually edited
          <button onClick={onReset}>Reset to default</button>
        </div>
      )}
    </div>
  );
};
```

#### Модификация WorkflowStep компонента
```tsx
// src/components/WorkflowStep.tsx

const [showPromptEditor, setShowPromptEditor] = useState(false);
const [prompt, setPrompt] = useState({ system: '', user: '' });
const [originalPrompt, setOriginalPrompt] = useState({ system: '', user: '' });

// 1. При входе на шаг — загружаем preview
useEffect(() => {
  if (step.status === 'pending') {
    fetchPromptPreview();
  }
}, [step]);

// 2. UI flow
return (
  <div>
    {step.status === 'pending' && (
      <>
        <PromptEditor
          {...prompt}
          isModified={prompt !== originalPrompt}
          onReset={() => setPrompt(originalPrompt)}
        />
        <button onClick={runWithPrompt}>
          Run Generation
        </button>
      </>
    )}

    {step.status === 'completed' && (
      <StepResult ... />
    )}
  </div>
);
```

## UI Mockup

```
┌─────────────────────────────────────────────────────────────┐
│  Step 1: Story Generation                      [In Progress]│
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  System Prompt:                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ You are a viral video content creator...               ││
│  │ Generate a story concept for a short video.            ││
│  │ ...                                                    ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  User Prompt:                                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Theme: cats on the beach                               ││
│  │ Target audience: pet lovers                            ││
│  │ Mood: funny                                            ││
│  │ Duration: 5 seconds                                    ││
│  │ Platforms: instagram, tiktok                           ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌──────────────────┐                                       │
│  │ ✏️ Modified      │  [Reset to default]                   │
│  └──────────────────┘                                       │
│                                                             │
│  [Run Generation]                              [Skip Step]  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Шаги для каждого Step Type

| Step | System Prompt Source | User Prompt Contains |
|------|---------------------|---------------------|
| Story | `STORY_SYSTEM_PROMPT` | theme, audience, mood, duration, platforms |
| Description | `DESCRIPTION_SYSTEM_PROMPT` | story_data |
| Prompt | `IMAGE_PROMPT_SYSTEM_PROMPT` | description_data |
| Scenario | `SCENARIO_SYSTEM_PROMPT` | image_url, description_data |
| Adaptation | `ADAPTATION_SYSTEM_PROMPT` | story, scenario, platforms |

## Миграция БД

```python
# alembic/versions/xxx_add_prompt_tracking.py

def upgrade():
    op.add_column('workflow_steps',
        sa.Column('original_prompt', sa.JSON(), nullable=True))
    op.add_column('workflow_steps',
        sa.Column('custom_prompt', sa.JSON(), nullable=True))
    op.add_column('workflow_steps',
        sa.Column('prompt_manually_edited', sa.Boolean(), default=False))

def downgrade():
    op.drop_column('workflow_steps', 'original_prompt')
    op.drop_column('workflow_steps', 'custom_prompt')
    op.drop_column('workflow_steps', 'prompt_manually_edited')
```

## Файлы для изменения

### Backend
- [ ] `app/models/workflow_step.py` — новые поля
- [ ] `app/schemas/workflow.py` — PreviewPromptRequest/Response
- [ ] `app/api/workflow.py` — endpoint preview-prompt, модификация generate endpoints
- [ ] `app/services/openai_service.py` — extract prompt building в отдельные методы
- [ ] `alembic/versions/xxx_add_prompt_tracking.py` — миграция

### Frontend
- [ ] `src/components/PromptEditor.tsx` — новый компонент
- [ ] `src/components/WorkflowStep.tsx` — интеграция editor
- [ ] `src/services/api.ts` — previewPrompt API call
- [ ] `src/types/index.ts` — типы для промтов

## Acceptance Criteria

1. [ ] На каждом шаге вижу промт ДО генерации
2. [ ] Могу редактировать system и user prompt
3. [ ] При редактировании — показывается badge "Modified"
4. [ ] Кнопка Reset возвращает оригинальный промт
5. [ ] После генерации в БД сохранены original_prompt и custom_prompt (если был изменён)
6. [ ] В UI результата шага видно был ли промт изменён
7. [ ] Работает для всех AI-шагов: Story, Description, Prompt, Scenario, Adaptation

## Оценка

- Backend (модели, endpoints): 2 часа
- Frontend (PromptEditor, интеграция): 2-3 часа
- Миграция + тесты: 1 час
- **Итого: 5-6 часов**

## Риски

1. **Большие промты** — нужен scroll в textarea
2. **JSON в промтах** — нужна валидация что не сломали структуру
3. **Контекст между шагами** — user prompt зависит от предыдущих шагов
