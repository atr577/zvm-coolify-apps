# SPEC-T32: Prompt Refinement for Discover

## Overview

Между созданием Discover-проекта и первым раундом генерации добавляется шаг Prompt Refinement — умная доработка пользовательского концепта через 9 блоков (4 творческих + 5 технических).

**Текущий flow:**
```
concept → create project → generate round 1
```

**Новый flow:**
```
concept → create project → REFINE CONCEPT → review prompt → generate round 1
```

## Data Model

### Новая модель: `DiscoverRefinement`

Хранится отдельно от проекта — один refinement на проект. Авто-сохранение при каждом изменении.

```python
# backend/app/models/discover.py

class DiscoverRefinement(Base):
    __tablename__ = "discover_refinements"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("discover_projects.id", ondelete="CASCADE"),
        unique=True, nullable=False, index=True
    )

    # Исходный концепт (копия из project.concept)
    original_concept = Column(Text, nullable=False)

    # Анализ от LLM
    relevant_blocks = Column(JSON, nullable=False)    # ["subject", "action", ...]

    # Заполненные блоки (JSON dict: block_name → BlockData)
    blocks = Column(JSON, nullable=False, default={})

    # Финальный промпт (English, собранный из блоков)
    refined_prompt = Column(Text, nullable=True)

    # Текущий score (0-100)
    score = Column(Integer, nullable=False, default=0)

    # LLM audit
    analysis_prompt_used = Column(Text, nullable=True)
    analysis_response = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("DiscoverProject", back_populates="refinement")
```

### Изменения в `DiscoverProject`

```python
# Добавить relationship
refinement = relationship(
    "DiscoverRefinement",
    back_populates="project",
    uselist=False,
    cascade="all, delete-orphan",
)
```

### Блоки — константы

```python
CREATIVE_BLOCKS = ["subject", "action", "moment", "environment"]
TECHNICAL_BLOCKS = ["camera", "lighting", "style", "format", "details"]
ALL_BLOCKS = CREATIVE_BLOCKS + TECHNICAL_BLOCKS
ALWAYS_RELEVANT = ["subject", "camera", "lighting", "style"]  # Минимум 4
```

## Pydantic Schemas

```python
# backend/app/schemas/discover.py (добавить к существующим)

from pydantic import BaseModel, Field
from typing import Optional

class RefinementBlockSchema(BaseModel):
    value: Optional[str] = None
    status: str  # auto_filled | needs_input | auto_generated | confirmed
    source: Optional[str] = None  # parsed | llm | user | settings
    question: Optional[str] = None
    options: Optional[list[str]] = None

class RefinementResponse(BaseModel):
    refinement_id: int
    original_concept: str
    score: int
    relevant_blocks: list[str]
    blocks: dict[str, RefinementBlockSchema]
    refined_prompt: Optional[str] = None
    ready_to_generate: bool

class BlockUpdateRequest(BaseModel):
    block_name: str = Field(..., pattern=r'^(subject|action|moment|environment|camera|lighting|style|details)$')
    value: str = Field(..., min_length=1)

class PromptUpdateRequest(BaseModel):
    refined_prompt: str = Field(..., min_length=10)

class CompileResponse(BaseModel):
    refined_prompt: str
    score: int
    ready_to_generate: bool
```

## API

### 1. `GET /api/discover/{project_id}/refine` — Получить refinement

Возвращает существующий refinement или 404.

**Response:** `RefinementResponse` или `404: No refinement found`

### 2. `POST /api/discover/{project_id}/refine` — Анализ концепта

Создаёт refinement. Если уже существует — возвращает 409.

**Request:** `{}` (концепт берётся из проекта)

**Response:** `RefinementResponse`

**Errors:**
- `409: Refinement already exists` — используйте GET
- `503: AI service temporarily unavailable` — LLM failure

### 2a. `DELETE /api/discover/{project_id}/refine` — Re-analyze (перезапуск)

Удаляет текущий refinement. Фронтенд после этого вызывает POST /refine заново.

**Response:** `204 No Content`

**Errors:**
- `404: No refinement found`

**Пример response:**
```json
{
  "refinement_id": 1,
  "original_concept": "собака ныряет за рыбой",
  "score": 12,
  "relevant_blocks": ["subject", "action", "moment", "environment", "camera", "lighting", "style", "format", "details"],
  "blocks": {
    "subject": {
      "value": "A dog diving underwater",
      "status": "auto_filled",
      "source": "parsed",
      "question": null,
      "options": null
    },
    "action": {
      "value": "Diving and chasing a fish",
      "status": "auto_filled",
      "source": "parsed",
      "question": null,
      "options": null
    },
    "moment": {
      "value": null,
      "status": "needs_input",
      "source": null,
      "question": "Какой именно момент запечатлеть?",
      "options": [
        "The initial leap into water — splash and anticipation",
        "Underwater pursuit — dog swimming toward fish",
        "The catch — dog grabs fish in mouth",
        "Surfacing triumphantly with fish"
      ]
    },
    "environment": {
      "value": null,
      "status": "needs_input",
      "source": null,
      "question": "Где это происходит?",
      "options": [
        "Clear mountain lake with rocky bottom",
        "Tropical ocean with coral reef",
        "Forest river with sunlight filtering through trees",
        "Backyard pool, suburban setting"
      ]
    },
    "camera": {
      "value": "Wide underwater POV from 3 meters depth, looking up toward surface with light rays",
      "status": "auto_generated",
      "source": "llm",
      "question": null,
      "options": null
    },
    "lighting": {
      "value": "Natural sunlight filtering through water, dappled caustic patterns on the bottom",
      "status": "auto_generated",
      "source": "llm",
      "question": null,
      "options": null
    },
    "style": {
      "value": "Photorealistic, hyper-detailed, National Geographic quality",
      "status": "auto_generated",
      "source": "llm",
      "question": null,
      "options": null
    },
    "format": {
      "value": "9:16 vertical",
      "status": "confirmed",
      "source": "settings",
      "question": null,
      "options": null
    },
    "details": {
      "value": "Water bubbles streaming from dog's nose, fish scales glinting, suspended sediment particles",
      "status": "auto_generated",
      "source": "llm",
      "question": null,
      "options": null
    }
  },
  "refined_prompt": null,
  "ready_to_generate": false
}
```

**Score = 12%:** только Format confirmed (1 из 9 relevant). `auto_filled` (Subject, Action) не считаются пока пользователь не нажмёт Accept.

### 3. `PUT /api/discover/{project_id}/refine` — Обновление блока

Пользователь выбирает вариант, вводит текст, или нажимает Accept. Авто-сохранение, score пересчитывается.

**Request:** `BlockUpdateRequest`
```json
{
  "block_name": "moment",
  "value": "The initial leap into water — splash and anticipation"
}
```

**Response:** `RefinementResponse` с обновлённым score.

**Errors:**
- `404: No refinement found` — сначала POST /refine
- `400: Invalid block_name` — не в списке допустимых

**Accept flow:** Для Accept auto_filled/auto_generated блока фронтенд отправляет PUT с текущим value блока → статус становится `confirmed`.

### 4. `POST /api/discover/{project_id}/refine/compile` — Собрать финальный промпт

Когда score >= 80. LLM собирает из блоков финальный English-промпт.

**Request:** `{}`

**Response:** `CompileResponse`
```json
{
  "refined_prompt": "A golden retriever mid-leap, diving into a crystal-clear mountain lake...",
  "score": 100,
  "ready_to_generate": true
}
```

**Errors:**
- `400: Score 62% too low. Need 80+`
- `503: AI service temporarily unavailable`

### 5. `PUT /api/discover/{project_id}/refine/prompt` — Редактировать финальный промпт

Пользователь правит скомпилированный промпт перед генерацией.

**Request:** `PromptUpdateRequest`
```json
{
  "refined_prompt": "A golden retriever mid-leap, diving into a crystal-clear mountain lake with sunlight..."
}
```

**Response:** `RefinementResponse`

### Изменения в существующем API

`POST /api/discover/{project_id}/rounds` — добавить проверку для первого раунда:

```python
refinement = db.query(DiscoverRefinement).filter(
    DiscoverRefinement.project_id == project_id
).first()

if project.current_image_round == 0:
    if not refinement or refinement.score < 80:
        raise HTTPException(400, "Complete prompt refinement first (score must be 80+)")
    if not refinement.refined_prompt:
        raise HTTPException(400, "Compile the refined prompt first")

# Использовать refined_prompt для ВСЕХ раундов (качественнее чем raw concept)
concept_for_generation = refinement.refined_prompt if refinement and refinement.refined_prompt else project.concept
```

## Scoring

```python
def calculate_score(relevant_blocks: list[str], blocks: dict) -> int:
    """Score = confirmed blocks / relevant blocks * 100.
    Only 'confirmed' status counts. Format is always confirmed."""
    if not relevant_blocks:
        return 0
    confirmed = sum(
        1 for name in relevant_blocks
        if blocks.get(name, {}).get("status") == "confirmed"
    )
    return int(confirmed / len(relevant_blocks) * 100)
```

**Правила:**
- Только `confirmed` считается в score
- `auto_filled` НЕ считается — нужен Accept от пользователя
- `auto_generated` НЕ считается — нужен Accept от пользователя
- `needs_input` НЕ считается — нужен ответ от пользователя
- Format = `confirmed` сразу (авто из настроек проекта, Accept не нужен)
- При любом изменении блока → статус `confirmed`, source `user`
- `ready_to_generate = score >= 80 and refined_prompt is not None`

## LLM Prompts

### Файл: `backend/app/services/prompts/discover.py`

```python
DISCOVER_REFINEMENT_SYSTEM = """You are a creative prompt analyst for AI image generation.

Your job: analyze a user's concept and break it down into structured blocks for a high-quality image prompt.

BLOCKS TO ANALYZE:
1. Subject — main subject/object (WHO/WHAT is in frame)
2. Action — what's happening (dynamic aspect, movement)
3. Moment — which exact moment to capture (timing)
4. Environment — where it's happening (location, surroundings)
5. Camera — angle, distance, composition
6. Lighting — light source, character, mood
7. Style — visual style (photorealistic, cinematic, anime, etc.)
8. Format — aspect ratio, frame (DO NOT include, handled by system)
9. Details — textures, materials, particles, fine elements

TASK:
1. Parse the concept — extract what's already specified
   - If concept clearly states the subject → auto_filled
   - If concept implies action → auto_filled
   - Values must be in ENGLISH even if concept is in another language
2. Determine which blocks are RELEVANT:
   - Subject, Camera, Lighting, Style are ALWAYS relevant
   - Action: skip if concept is static (portrait, still life)
   - Moment: skip if only one possible moment (static scene, no timeline)
   - Environment: skip if abstract/studio/no location implied
   - Details: skip for simple concepts with no specific textures
3. For CREATIVE blocks that need user input (no clear answer from concept):
   - Write a clear question in the user's detected language
   - Provide exactly 4 diverse options (in ENGLISH, concise, 5-15 words each)
4. For TECHNICAL blocks:
   - Generate appropriate values automatically based on concept (in ENGLISH)
   - Status: auto_generated
5. Do NOT include Format block — it is handled by the system

INPUT LANGUAGE: User may write in any language. Detect it. Ask questions in that language.
OUTPUT VALUES: All block values and options must be in ENGLISH.

Return JSON:
{{
  "detected_language": "ru",
  "relevant_blocks": ["subject", "action", ...],
  "blocks": {{
    "subject": {{
      "value": "extracted value or null",
      "status": "auto_filled | needs_input | auto_generated",
      "question": "question text in user language, or null",
      "options": ["opt1", "opt2", "opt3", "opt4"] or null
    }}
  }}
}}

IMPORTANT:
- Do NOT include "format" in blocks or relevant_blocks
- relevant_blocks must include at least: subject, camera, lighting, style
- Each block must have exactly the fields shown above
- Options must be exactly 4 items when provided"""


DISCOVER_COMPILE_SYSTEM = """You are a prompt engineer for AI image generation.

Given a set of completed blocks describing a visual concept, compile them into a single, cohesive,
detailed image prompt in ENGLISH.

RULES:
1. The prompt should be 80-150 words
2. Write as a flowing, cinematic description (not a list of blocks)
3. Incorporate ALL provided blocks naturally into one coherent paragraph
4. Compose for the specified aspect ratio (mention framing)
5. End with style/quality keywords
6. Do NOT include text overlays, watermarks, logos
7. The prompt should be suitable as a first frame for a short viral video
8. Do NOT mention block names — just weave the content together

Return JSON:
{{
  "refined_prompt": "the compiled prompt text"
}}"""
```

## Backend Service

### Файл: `backend/app/services/discover_service.py`

Добавить методы в `DiscoverService`:

```python
async def get_refinement(self, db: Session, project_id: int, user_id: int) -> dict | None:
    """Получить существующий refinement. Возвращает None если нет."""
    await self.get_project(db, project_id, user_id)  # Auth check
    refinement = db.query(DiscoverRefinement).filter(
        DiscoverRefinement.project_id == project_id
    ).first()
    if not refinement:
        return None
    return self._format_refinement(refinement)


async def analyze_concept(self, db: Session, project_id: int, user_id: int) -> dict:
    """Создать refinement: LLM анализирует концепт, возвращает блоки."""
    project = await self.get_project(db, project_id, user_id)

    # Проверить что refinement ещё нет
    existing = db.query(DiscoverRefinement).filter(
        DiscoverRefinement.project_id == project_id
    ).first()
    if existing:
        raise ValueError("Refinement already exists. Use GET to fetch it.")

    # Вызвать LLM
    try:
        result = await self.openai.generate_validated_json(
            prompt=f"USER CONCEPT:\n{project.concept}",
            response_schema=RefinementLLMResponse,  # Pydantic schema for validation
            system_prompt=DISCOVER_REFINEMENT_SYSTEM,
            model="gpt-4o",
            temperature=0.3,  # Детерминизм для анализа
        )
    except Exception as e:
        logger.error(f"LLM analysis failed for project {project_id}: {e}")
        raise RuntimeError("AI service temporarily unavailable. Please try again.")

    blocks = result.get("blocks", {})

    # Validate: relevant_blocks must include ALWAYS_RELEVANT
    relevant = result.get("relevant_blocks", [])
    for block in ALWAYS_RELEVANT:
        if block not in relevant:
            relevant.append(block)

    # Validate: block names must be in ALL_BLOCKS (minus format)
    valid_block_names = [b for b in ALL_BLOCKS if b != "format"]
    blocks = {k: v for k, v in blocks.items() if k in valid_block_names}

    # Format блок — auto-confirmed из настроек проекта
    blocks["format"] = {
        "value": f"{project.image_aspect_ratio} vertical"
                 if project.image_aspect_ratio == "9:16"
                 else project.image_aspect_ratio,
        "status": "confirmed",
        "source": "settings",
        "question": None,
        "options": None,
    }
    if "format" not in relevant:
        relevant.append("format")

    refinement = DiscoverRefinement(
        project_id=project_id,
        original_concept=project.concept,
        relevant_blocks=relevant,
        blocks=blocks,
        score=calculate_score(relevant, blocks),
        analysis_prompt_used=project.concept,
        analysis_response=result,
    )
    db.add(refinement)
    db.commit()
    db.refresh(refinement)

    return self._format_refinement(refinement)


async def update_block(
    self, db: Session, project_id: int, user_id: int,
    block_name: str, value: str
) -> dict:
    """Обновить значение блока. Авто-сохранение + пересчёт score."""
    await self.get_project(db, project_id, user_id)  # Auth check

    refinement = db.query(DiscoverRefinement).filter(
        DiscoverRefinement.project_id == project_id
    ).first()
    if not refinement:
        raise ValueError("No refinement found. Run analyze first.")

    if block_name not in [b for b in ALL_BLOCKS if b != "format"]:
        raise ValueError(f"Invalid block_name: {block_name}")

    blocks = dict(refinement.blocks)
    blocks[block_name] = {
        "value": value,
        "status": "confirmed",
        "source": "user",
        "question": blocks.get(block_name, {}).get("question"),
        "options": blocks.get(block_name, {}).get("options"),
    }
    refinement.blocks = blocks
    refinement.score = calculate_score(refinement.relevant_blocks, blocks)
    refinement.refined_prompt = None  # Invalidate compiled prompt
    refinement.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(refinement)

    return self._format_refinement(refinement)


async def compile_prompt(self, db: Session, project_id: int, user_id: int) -> dict:
    """Собрать финальный промпт из блоков. Score >= 80 required."""
    project = await self.get_project(db, project_id, user_id)

    refinement = db.query(DiscoverRefinement).filter(
        DiscoverRefinement.project_id == project_id
    ).first()
    if not refinement:
        raise ValueError("No refinement found. Run analyze first.")
    if refinement.score < 80:
        raise ValueError(f"Score {refinement.score}% too low. Need 80+.")

    # Собрать блоки в текст для LLM
    blocks_text = "\n".join(
        f"{name}: {block.get('value', '')}"
        for name, block in refinement.blocks.items()
        if block.get("value") and block.get("status") == "confirmed"
    )

    try:
        result = await self.openai.generate_json(
            prompt=f"BLOCKS:\n{blocks_text}\n\nASPECT RATIO: {project.image_aspect_ratio}",
            system_prompt=DISCOVER_COMPILE_SYSTEM,
            model="gpt-4o",
            temperature=0.5,
        )
    except Exception as e:
        logger.error(f"LLM compile failed for project {project_id}: {e}")
        raise RuntimeError("AI service temporarily unavailable. Please try again.")

    refinement.refined_prompt = result.get("refined_prompt", "")
    refinement.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(refinement)

    return self._format_refinement(refinement)


async def delete_refinement(self, db: Session, project_id: int, user_id: int) -> None:
    """Удалить refinement для перезапуска анализа."""
    await self.get_project(db, project_id, user_id)
    refinement = db.query(DiscoverRefinement).filter(
        DiscoverRefinement.project_id == project_id
    ).first()
    if not refinement:
        raise ValueError("No refinement found.")
    db.delete(refinement)
    db.commit()


async def update_refined_prompt(
    self, db: Session, project_id: int, user_id: int, refined_prompt: str
) -> dict:
    """Пользователь редактирует скомпилированный промпт."""
    await self.get_project(db, project_id, user_id)

    refinement = db.query(DiscoverRefinement).filter(
        DiscoverRefinement.project_id == project_id
    ).first()
    if not refinement:
        raise ValueError("No refinement found.")

    refinement.refined_prompt = refined_prompt
    refinement.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(refinement)

    return self._format_refinement(refinement)


def _format_refinement(self, refinement: DiscoverRefinement) -> dict:
    """Format refinement for API response."""
    return {
        "refinement_id": refinement.id,
        "original_concept": refinement.original_concept,
        "score": refinement.score,
        "relevant_blocks": refinement.relevant_blocks,
        "blocks": refinement.blocks,
        "refined_prompt": refinement.refined_prompt,
        "ready_to_generate": refinement.score >= 80 and refinement.refined_prompt is not None,
    }
```

## Frontend

### Компонент: `frontend/src/components/discover/PromptRefinement.tsx`

Встраивается в `DiscoverPage.tsx` — показывается когда `project.stage === 'images'` и `current_image_round === 0`.

**UI структура:**

```
┌─────────────────────────────────────────────┐
│ Prompt Refinement                    12/100  │
│ ██░░░░░░░░░░░░░░░░░░                        │
│                                             │
│ ┌─ Subject ──────────────────────── ✏️ ──┐  │
│ │ A golden retriever, wet fur             │  │
│ │                           [Accept] Edit │  │
│ └─────────────────────────────────────────┘  │
│                                             │
│ ┌─ Moment ───────────────────────── ❓ ──┐  │
│ │ Какой именно момент запечатлеть?        │  │
│ │                                         │  │
│ │ ○ The initial leap — splash             │  │
│ │ ○ Underwater pursuit — swimming         │  │
│ │ ○ The catch — grabs fish                │  │
│ │ ○ Surfacing triumphantly                │  │
│ │ ○ Other: [____________]                 │  │
│ └─────────────────────────────────────────┘  │
│                                             │
│ ┌─ Camera ───────────────────────── 🤖 ──┐  │
│ │ Wide underwater POV from 3m depth       │  │
│ │                           [Accept] Edit │  │
│ └─────────────────────────────────────────┘  │
│                                             │
│ ┌─ Format ───────────────────────── ✅ ──┐  │
│ │ 9:16 vertical                           │  │
│ └─────────────────────────────────────────┘  │
│                                             │
│  [Re-analyze]  [Compile Prompt] (disabled < 80) │
└─────────────────────────────────────────────┘

  ↓ after Compile ↓

┌─────────────────────────────────────────────┐
│ Final Prompt                         100%   │
│ ┌─────────────────────────────────────────┐  │
│ │ A golden retriever mid-leap, diving     │  │
│ │ into a crystal-clear mountain lake...   │  │
│ │                                         │  │
│ │ [editable textarea]                     │  │
│ └─────────────────────────────────────────┘  │
│                                             │
│  [Generate Images]                           │
└─────────────────────────────────────────────┘
```

**Логика:**
1. На загрузке → `GET /refine`
2. Если 404 → автоматически `POST /refine` для анализа
3. Блоки отображаются все сразу (свободная навигация)
4. `auto_filled` блоки показывают значение + Accept / Edit (✏️ иконка)
5. `needs_input` блоки показывают вопрос + 4 radio + "Other" text field (❓ иконка)
6. `auto_generated` блоки показывают значение + Accept / Edit (🤖 иконка)
7. `confirmed` блоки показывают значение + Edit (✅ иконка)
8. Format блок — readonly, всегда ✅
9. Accept = PUT /refine с текущим value блока
10. Select option / type Other = PUT /refine с выбранным value
11. Edit = textarea открывается, сохранение по blur/enter = PUT /refine
12. Score обновляется в реальном времени из response
13. Кнопка "Compile Prompt" активна при score >= 80
14. После Compile → показать textarea с промптом + "Generate Images"
15. Если пользователь правит промпт → `PUT /refine/prompt` по blur
16. Re-analyze → confirm dialog → `DELETE /refine` → `POST /refine` → обновить UI

**Состояния блока (иконки):**
- ✅ `confirmed` — зелёная галка (подтверждён)
- ❓ `needs_input` — жёлтый вопрос (ждёт ответа)
- 🤖 `auto_generated` — серый робот (ждёт Accept)
- ✏️ `auto_filled` — синий карандаш (распарсено, ждёт Accept)

### Типы: `frontend/src/types/index.ts`

```typescript
export type BlockStatus = 'auto_filled' | 'needs_input' | 'auto_generated' | 'confirmed'

export interface DiscoverRefinementBlock {
  value: string | null
  status: BlockStatus
  source: 'parsed' | 'llm' | 'user' | 'settings' | null
  question?: string | null
  options?: string[] | null
}

export interface DiscoverRefinement {
  refinement_id: number
  original_concept: string
  score: number
  relevant_blocks: string[]
  blocks: Record<string, DiscoverRefinementBlock>
  refined_prompt: string | null
  ready_to_generate: boolean
}
```

### API client: `frontend/src/services/api.ts`

```typescript
// В discoverApi добавить:
getRefinement: (projectId: number) =>
  api.get<DiscoverRefinement>(`/api/discover/${projectId}/refine`),

analyzePrompt: (projectId: number) =>
  api.post<DiscoverRefinement>(`/api/discover/${projectId}/refine`),

updateBlock: (projectId: number, blockName: string, value: string) =>
  api.put<DiscoverRefinement>(`/api/discover/${projectId}/refine`, {
    block_name: blockName, value
  }),

compilePrompt: (projectId: number) =>
  api.post<DiscoverRefinement>(`/api/discover/${projectId}/refine/compile`),

updatePrompt: (projectId: number, refinedPrompt: string) =>
  api.put<DiscoverRefinement>(`/api/discover/${projectId}/refine/prompt`, {
    refined_prompt: refinedPrompt
  }),

deleteRefinement: (projectId: number) =>
  api.delete(`/api/discover/${projectId}/refine`),
```

## Миграция

```python
# Alembic: add discover_refinements table

def upgrade():
    op.create_table(
        'discover_refinements',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('project_id', sa.Integer(),
                  sa.ForeignKey('discover_projects.id', ondelete='CASCADE'),
                  unique=True, nullable=False, index=True),
        sa.Column('original_concept', sa.Text(), nullable=False),
        sa.Column('relevant_blocks', sa.JSON(), nullable=False),
        sa.Column('blocks', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('refined_prompt', sa.Text(), nullable=True),
        sa.Column('score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('analysis_prompt_used', sa.Text(), nullable=True),
        sa.Column('analysis_response', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )

def downgrade():
    op.drop_table('discover_refinements')
```

## Error Handling

```python
# В API endpoints:

@router.post("/{project_id}/refine")
async def analyze_concept(project_id: int, ...):
    try:
        result = await discover_service.analyze_concept(db, project_id, current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(409, str(e))  # Already exists
    except RuntimeError as e:
        raise HTTPException(503, str(e))  # LLM failure

@router.put("/{project_id}/refine")
async def update_block(project_id: int, data: BlockUpdateRequest, ...):
    try:
        result = await discover_service.update_block(
            db, project_id, current_user.id, data.block_name, data.value
        )
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.post("/{project_id}/refine/compile")
async def compile_prompt(project_id: int, ...):
    try:
        result = await discover_service.compile_prompt(db, project_id, current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(503, str(e))  # LLM failure
```

## Затрагиваемые файлы

| Файл | Изменение |
|------|-----------|
| `backend/app/models/discover.py` | + DiscoverRefinement модель, + relationship в DiscoverProject |
| `backend/app/schemas/discover.py` | + RefinementResponse, BlockUpdateRequest, CompileResponse, PromptUpdateRequest |
| `backend/app/services/discover_service.py` | + get_refinement, analyze_concept, update_block, compile_prompt, update_refined_prompt, delete_refinement, _format_refinement, calculate_score |
| `backend/app/services/prompts/discover.py` | + DISCOVER_REFINEMENT_SYSTEM, DISCOVER_COMPILE_SYSTEM |
| `backend/app/api/discover.py` | + 6 endpoints (GET/POST/DELETE/PUT refine, POST compile, PUT prompt), update POST /rounds |
| `frontend/src/components/discover/PromptRefinement.tsx` | НОВЫЙ компонент |
| `frontend/src/pages/DiscoverPage.tsx` | + интеграция PromptRefinement |
| `frontend/src/types/index.ts` | + BlockStatus, DiscoverRefinement, DiscoverRefinementBlock |
| `frontend/src/services/api.ts` | + getRefinement, analyzePrompt, updateBlock, compilePrompt, updatePrompt, deleteRefinement |
| `alembic/versions/xxx_add_discover_refinements.py` | Миграция + downgrade |

## Testing

### Unit Tests
- `calculate_score()` — все комбинации: 0 confirmed, partial, full, format-only
- `_format_refinement()` — correct output shape
- Block validation — invalid block names rejected

### API Tests
- `GET /refine` — 404 if none, 200 with data
- `POST /refine` — creates refinement, 409 on duplicate
- `PUT /refine` — updates block, score recalculates, 400 on invalid block
- `POST /refine/compile` — 400 if score < 80, 200 with prompt
- `PUT /refine/prompt` — updates refined_prompt
- `POST /rounds` — 400 if no refinement on first round, 200 if score >= 80

### E2E
- Full flow: create project → POST /refine → accept all blocks → compile → edit prompt → generate round 1
- Minimal concept: all blocks needs_input
- Complete concept: most blocks auto_filled, quick accept flow
- Multilingual: Russian concept → Russian questions → English values

## Edge Cases

1. **Полный концепт** — LLM заполнит большинство блоков как `auto_filled`. Score всё равно 12% (только Format), пользователь должен Accept каждый блок
2. **Минимальный концепт** ("красиво") — большинство блоков `needs_input`, score низкий
3. **Повторный POST /refine** — 409, используйте GET
4. **Язык** — вопросы на языке пользователя, значения блоков на English
5. **Пользователь уходит** — авто-сохранение, при возвращении GET /refine загружает из БД
6. **Блок принят, затем отредактирован** — статус остаётся `confirmed`, value обновляется
7. **Блок после compile** — PUT /refine после compile → refined_prompt обнуляется (нужен re-compile)

## НЕ входит в scope

- Skip refinement для power users (V2)
- Кеширование по хешу концепта (V2)
- Refinement для video stage (отдельная задача)
- Batch update нескольких блоков одним запросом (V2)
