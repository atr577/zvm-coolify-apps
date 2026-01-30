# SPEC-T19: Template Project Type

## Summary

**Для пользователя:** Новый тип проекта "Template" — загружаешь CSV с вариантами, настраиваешь промпты и модели, генерируешь видео одной кнопкой.

**Техническое:** Расширение Project (type=template), 4 новые модели, 7-step pipeline, 12 API endpoints.

---

## 1. Integration with Existing Project

### 1.1 Project Type Extension

```python
# backend/app/models/project.py

# Existing enum (add "template")
ProjectType = Literal["discover", "remix", "template"]

# Project.project_type already exists as String(20)
# No model changes needed — just accept "template" as valid value
```

### 1.2 Schema Validation

```python
# backend/app/schemas/project.py

class TemplateProjectCreate(ProjectBase):
    """Extended schema for template project creation."""
    project_type: Literal["template"] = "template"

    # TemplateSettings fields (required)
    preprocessing_prompt: str
    image_prompt_template: str
    llm_model: LLMModelEnum = LLMModelEnum.GPT4O_MINI
    image_model: ImageModelEnum = ImageModelEnum.NANO_BANANA
    video_model: VideoModelEnum = VideoModelEnum.VEO3_FAST
    image_aspect_ratio: AspectRatioEnum = AspectRatioEnum.PORTRAIT

    # First VideoTemplate (required)
    video_template_name: str
    video_template_prompt: str

    @model_validator(mode="after")
    def validate_required_fields(self):
        if not self.preprocessing_prompt:
            raise ValueError("preprocessing_prompt is required")
        if not self.image_prompt_template:
            raise ValueError("image_prompt_template is required")
        if not self.video_template_name or not self.video_template_prompt:
            raise ValueError("video_template is required")
        return self
```

**При создании проекта type=template:**
1. Создаётся Project
2. Создаётся TemplateSettings (с промптами и моделями)
3. Создаётся первый VideoTemplate (is_default=true)

### 1.3 Relationship Pattern

```
Project (type=template)
    │
    ├── TemplateSettings (1:1, unique FK)
    │       └── csv_columns, prompts, models
    │
    ├── VideoTemplate (1:N)
    │       └── name, prompt, is_default, is_deleted
    │
    ├── Variant (1:N)
    │       └── row_number, data, usage_count
    │
    └── TemplateGeneration (1:N)
            └── variant_id, video_template_id, results, status
```

---

## 2. Database Models

### 2.1 TemplateSettings

```python
# backend/app/models/template_settings.py

from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, DateTime, Enum
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime
import enum

class AspectRatio(str, enum.Enum):
    PORTRAIT = "9:16"
    LANDSCAPE = "16:9"
    SQUARE = "1:1"

class TemplateSettings(Base):
    __tablename__ = "template_settings"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), unique=True, nullable=False)

    # LLM Prompts
    preprocessing_prompt = Column(Text, nullable=False)
    image_prompt_template = Column(Text, nullable=False)

    # LLM Model
    llm_model = Column(String(50), nullable=False, default="gpt-4o-mini")

    # Generation Models
    image_model = Column(String(100), nullable=False, default="fal-ai/nano-banana-pro")
    video_model = Column(String(100), nullable=False, default="fal-ai/veo3/fast/image-to-video")

    # Image Settings
    image_aspect_ratio = Column(Enum(AspectRatio), nullable=False, default=AspectRatio.PORTRAIT)

    # CSV Metadata
    csv_columns = Column(JSON, nullable=True)  # ["№", "Место", "Авто", ...]

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="template_settings")
```

### 2.2 VideoTemplate

```python
# backend/app/models/video_template.py

class VideoTemplate(Base):
    __tablename__ = "video_templates"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(100), nullable=False)
    prompt = Column(Text, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)  # Soft delete

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="video_templates")
    generations = relationship("TemplateGeneration", back_populates="video_template")
```

### 2.3 Variant

```python
# backend/app/models/variant.py

class Variant(Base):
    __tablename__ = "variants"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    row_number = Column(Integer, nullable=False)
    data = Column(JSON, nullable=False)  # {"№": "43", "Место": "...", ...}

    # Usage tracking
    usage_count = Column(Integer, default=0, nullable=False)
    last_used_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="variants")
    generations = relationship("TemplateGeneration", back_populates="variant")

    # Index for "pick least used"
    __table_args__ = (
        Index("ix_variants_project_usage", "project_id", "usage_count"),
    )
```

### 2.4 TemplateGeneration

```python
# backend/app/models/template_generation.py

class GenerationStatus(str, enum.Enum):
    PENDING = "pending"
    PREPROCESSING = "preprocessing"
    GENERATING_IMAGE = "generating_image"
    GENERATING_VIDEO = "generating_video"
    COMPLETED = "completed"
    FAILED = "failed"

class TemplateGeneration(Base):
    __tablename__ = "template_generations"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    variant_id = Column(Integer, ForeignKey("variants.id", ondelete="SET NULL"), nullable=True)
    video_template_id = Column(Integer, ForeignKey("video_templates.id", ondelete="SET NULL"), nullable=True)

    # Models used (snapshot for display)
    llm_model = Column(String(50), nullable=False)
    image_model = Column(String(100), nullable=False)
    video_model = Column(String(100), nullable=False)

    # Pipeline results
    preprocessing_result = Column(JSON, nullable=True)
    image_prompt = Column(Text, nullable=True)
    video_prompt = Column(Text, nullable=True)  # Copy from VideoTemplate at generation time
    image_url = Column(String(500), nullable=True)
    video_url = Column(String(500), nullable=True)

    # Local paths (after download)
    image_path = Column(String(255), nullable=True)
    video_path = Column(String(255), nullable=True)

    # Status
    status = Column(Enum(GenerationStatus), default=GenerationStatus.PENDING, nullable=False)
    failed_at_step = Column(String(20), nullable=True)  # "preprocessing", "image_prompt", "image", "video"
    error_message = Column(Text, nullable=True)

    # Cost tracking
    llm_tokens_used = Column(Integer, nullable=True)
    image_cost = Column(Float, nullable=True)
    video_cost = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    project = relationship("Project", back_populates="template_generations")
    variant = relationship("Variant", back_populates="generations")
    video_template = relationship("VideoTemplate", back_populates="generations")
```

### 2.5 Project Model Extension

```python
# backend/app/models/project.py (add relationships)

class Project(Base):
    # ... existing fields ...

    # Add relationships for template type
    template_settings = relationship("TemplateSettings", back_populates="project", uselist=False, cascade="all, delete-orphan")
    video_templates = relationship("VideoTemplate", back_populates="project", cascade="all, delete-orphan")
    variants = relationship("Variant", back_populates="project", cascade="all, delete-orphan")
    template_generations = relationship("TemplateGeneration", back_populates="project", cascade="all, delete-orphan")
```

---

## 3. Pydantic Schemas

### 3.1 TemplateSettings Schemas

```python
# backend/app/schemas/template.py

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class AspectRatioEnum(str, Enum):
    PORTRAIT = "9:16"
    LANDSCAPE = "16:9"
    SQUARE = "1:1"

class LLMModelEnum(str, Enum):
    GPT4O_MINI = "gpt-4o-mini"
    GPT4O = "gpt-4o"

class ImageModelEnum(str, Enum):
    NANO_BANANA = "fal-ai/nano-banana-pro"
    FLUX_PRO_ULTRA = "fal-ai/flux-pro/v1.1-ultra"
    FLUX_PRO = "fal-ai/flux-pro/v1.1"
    IDEOGRAM_V3 = "fal-ai/ideogram/v3"
    IMAGEN3 = "fal-ai/imagen3"

class VideoModelEnum(str, Enum):
    VEO3_FAST = "fal-ai/veo3/fast/image-to-video"
    VEO3 = "fal-ai/veo3/image-to-video"
    VEO31 = "fal-ai/veo3.1/reference-to-video"
    KLING_V21 = "fal-ai/kling-video/v2.1/pro"
    MINIMAX = "fal-ai/minimax/video-01"

# --- TemplateSettings ---

class TemplateSettingsBase(BaseModel):
    preprocessing_prompt: str
    image_prompt_template: str
    llm_model: str = "gpt-4o-mini"
    image_model: str = "fal-ai/nano-banana-pro"
    video_model: str = "fal-ai/veo3/fast/image-to-video"
    image_aspect_ratio: AspectRatioEnum = AspectRatioEnum.PORTRAIT

class TemplateSettingsCreate(TemplateSettingsBase):
    pass

class TemplateSettingsUpdate(BaseModel):
    preprocessing_prompt: Optional[str] = None
    image_prompt_template: Optional[str] = None
    llm_model: Optional[str] = None
    image_model: Optional[str] = None
    video_model: Optional[str] = None
    image_aspect_ratio: Optional[AspectRatioEnum] = None

class TemplateSettingsResponse(TemplateSettingsBase):
    id: int
    project_id: int
    csv_columns: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### 3.2 VideoTemplate Schemas

```python
class VideoTemplateBase(BaseModel):
    name: str = Field(..., max_length=100)
    prompt: str
    is_default: bool = False

class VideoTemplateCreate(VideoTemplateBase):
    pass

class VideoTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    prompt: Optional[str] = None
    is_default: Optional[bool] = None

class VideoTemplateResponse(VideoTemplateBase):
    id: int
    project_id: int
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### 3.3 Variant Schemas

```python
class VariantBase(BaseModel):
    row_number: int
    data: dict  # Arbitrary JSON

class VariantCreate(VariantBase):
    pass

class VariantUpdate(BaseModel):
    data: Optional[dict] = None

class VariantResponse(VariantBase):
    id: int
    project_id: int
    usage_count: int
    last_used_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class VariantListResponse(BaseModel):
    variants: List[VariantResponse]
    total: int
    csv_columns: Optional[List[str]] = None
```

### 3.4 Generation Schemas

```python
class GenerationStatusEnum(str, Enum):
    PENDING = "pending"
    PREPROCESSING = "preprocessing"
    GENERATING_IMAGE = "generating_image"
    GENERATING_VIDEO = "generating_video"
    COMPLETED = "completed"
    FAILED = "failed"

class GenerateRequest(BaseModel):
    variant_id: Optional[int] = None  # null = auto-select
    video_template_id: Optional[int] = None  # null = use default

class GenerationResponse(BaseModel):
    id: int
    project_id: int
    variant_id: Optional[int]
    video_template_id: Optional[int]

    # Models used (snapshot from generation time)
    llm_model: str
    image_model: str
    video_model: str

    # Results
    preprocessing_result: Optional[dict] = None
    image_prompt: Optional[str] = None
    video_prompt: Optional[str] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    image_path: Optional[str] = None
    video_path: Optional[str] = None

    # Status
    status: GenerationStatusEnum
    failed_at_step: Optional[str] = None
    error_message: Optional[str] = None

    # Variant data (for display) — enriched from variant relationship in endpoint
    variant_data: Optional[dict] = None  # Not in DB, populated from gen.variant.data

    # Timestamps
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class GenerationListResponse(BaseModel):
    generations: List[GenerationResponse]
    total: int
```

### 3.5 CSV Upload Schema

```python
class CSVUploadResponse(BaseModel):
    variants_created: int
    csv_columns: List[str]
    preview: List[dict]  # First 5 rows
```

---

## 4. Services

### 4.1 CSV Parser Service

```python
# backend/app/services/csv_parser.py

import csv
import io
from typing import List, Dict, Tuple

class CSVParserError(Exception):
    pass

class CSVParser:
    """Parse CSV with arbitrary columns, handle edge cases."""

    @staticmethod
    def parse(content: bytes, encoding: str = "utf-8") -> Tuple[List[str], List[Dict[str, str]]]:
        """
        Parse CSV content.

        Returns:
            (columns, rows) where rows are list of dicts

        Edge cases handled:
            - Empty cells → ""
            - Cyrillic column names → OK
            - Duplicate rows → OK
        """
        try:
            text = content.decode(encoding)
        except UnicodeDecodeError:
            # Try cp1251 for Russian Windows files
            text = content.decode("cp1251")

        reader = csv.DictReader(io.StringIO(text))
        columns = reader.fieldnames

        if not columns:
            raise CSVParserError("CSV has no header row")

        rows = []
        for i, row in enumerate(reader, start=1):
            # Replace None with "" for empty cells
            clean_row = {k: (v or "") for k, v in row.items()}
            rows.append(clean_row)

        if not rows:
            raise CSVParserError("CSV has no data rows")

        return columns, rows
```

### 4.2 Placeholder Replacement Service

```python
# backend/app/services/placeholder_service.py

import re
from typing import Dict

class PlaceholderService:
    """Replace {column_name} placeholders with variant data."""

    PATTERN = re.compile(r"\{([^}]+)\}")

    @classmethod
    def replace(cls, template: str, data: Dict[str, str]) -> str:
        """
        Replace placeholders in template with values from data.

        Example:
            template = "На вход: {№} | {Место}"
            data = {"№": "43", "Место": "Макао"}
            result = "На вход: 43 | Макао"
        """
        def replacer(match):
            key = match.group(1)
            return data.get(key, match.group(0))  # Keep original if key not found

        return cls.PATTERN.sub(replacer, template)

    @classmethod
    def get_placeholders(cls, template: str) -> List[str]:
        """Extract all placeholder names from template."""
        return cls.PATTERN.findall(template)
```

### 4.3 Template Generation Service

```python
# backend/app/services/template_generation_service.py

from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import logging

from app.models.template_generation import TemplateGeneration, GenerationStatus
from app.models.variant import Variant
from app.models.video_template import VideoTemplate
from app.models.template_settings import TemplateSettings
from app.services.openai_service import OpenAIService
from app.services.fal_client import FalClient
from app.services.media_downloader import MediaDownloader
from app.services.placeholder_service import PlaceholderService

logger = logging.getLogger(__name__)

class TemplateGenerationError(Exception):
    def __init__(self, step: str, message: str):
        self.step = step
        self.message = message
        super().__init__(f"[{step}] {message}")

class TemplateGenerationService:
    def __init__(self, db: Session):
        self.db = db
        self.openai = OpenAIService()
        self.fal = FalClient()
        self.downloader = MediaDownloader()

    async def generate(
        self,
        project_id: int,
        variant_id: Optional[int] = None,
        video_template_id: Optional[int] = None
    ) -> TemplateGeneration:
        """
        Run the 7-step generation pipeline.

        Steps:
            1. Pick Variant + VideoTemplate
            2. Prepare Input (placeholder replacement)
            3. LLM #1: Preprocessing
            4. LLM #2: Image Prompt
            5. Image Generation
            6. Video Generation
            7. Save & Update
        """
        # Get settings
        settings = self.db.query(TemplateSettings).filter(
            TemplateSettings.project_id == project_id
        ).first()

        if not settings:
            raise TemplateGenerationError("init", "Template settings not found")

        # Step 1: Pick Variant
        variant = self._pick_variant(project_id, variant_id)

        # Step 1b: Pick VideoTemplate
        video_template = self._pick_video_template(project_id, video_template_id)

        # Create generation record
        generation = TemplateGeneration(
            project_id=project_id,
            variant_id=variant.id,
            video_template_id=video_template.id if video_template else None,
            image_model=settings.image_model,
            video_model=settings.video_model,
            video_prompt=video_template.prompt if video_template else None,
            status=GenerationStatus.PENDING
        )
        self.db.add(generation)
        self.db.commit()
        self.db.refresh(generation)

        try:
            # Step 2: Prepare Input
            prepared_prompt = PlaceholderService.replace(
                settings.preprocessing_prompt,
                variant.data
            )

            # Step 3: LLM #1 Preprocessing
            generation.status = GenerationStatus.PREPROCESSING
            self.db.commit()

            preprocessing_result = await self._run_preprocessing(
                prepared_prompt, settings.llm_model
            )
            generation.preprocessing_result = preprocessing_result
            self.db.commit()

            # Step 4: LLM #2 Image Prompt
            image_prompt = await self._run_image_prompt(
                preprocessing_result,
                settings.image_prompt_template,
                settings.llm_model
            )
            generation.image_prompt = image_prompt
            self.db.commit()

            # Step 5: Image Generation
            generation.status = GenerationStatus.GENERATING_IMAGE
            self.db.commit()

            image_url = await self._generate_image(
                image_prompt,
                settings.image_model,
                settings.image_aspect_ratio.value
            )
            generation.image_url = image_url

            # Download image
            image_path = await self.downloader.download_image(image_url, generation.id)
            generation.image_path = image_path
            self.db.commit()

            # Step 6: Video Generation
            generation.status = GenerationStatus.GENERATING_VIDEO
            self.db.commit()

            video_url = await self._generate_video(
                image_url,
                generation.video_prompt,
                settings.video_model,
                project_duration=self._get_project_duration(project_id)
            )
            generation.video_url = video_url

            # Download video
            video_path = await self.downloader.download_video(video_url, generation.id)
            generation.video_path = video_path

            # Step 7: Complete
            generation.status = GenerationStatus.COMPLETED
            generation.completed_at = datetime.utcnow()

            # Update variant usage
            variant.usage_count += 1
            variant.last_used_at = datetime.utcnow()

            self.db.commit()
            logger.info(f"Generation {generation.id} completed successfully")

            return generation

        except TemplateGenerationError as e:
            generation.status = GenerationStatus.FAILED
            generation.failed_at_step = e.step
            generation.error_message = e.message
            self.db.commit()
            logger.error(f"Generation {generation.id} failed at {e.step}: {e.message}")
            raise
        except Exception as e:
            generation.status = GenerationStatus.FAILED
            generation.error_message = str(e)
            self.db.commit()
            logger.error(f"Generation {generation.id} failed: {e}")
            raise

    def _pick_variant(self, project_id: int, variant_id: Optional[int]) -> Variant:
        """Pick variant by ID or auto-select least used."""
        if variant_id:
            variant = self.db.query(Variant).filter(
                Variant.id == variant_id,
                Variant.project_id == project_id
            ).first()
            if not variant:
                raise TemplateGenerationError("init", f"Variant {variant_id} not found")
            return variant

        # Auto-select: least used first
        variant = self.db.query(Variant).filter(
            Variant.project_id == project_id
        ).order_by(Variant.usage_count.asc()).first()

        if not variant:
            raise TemplateGenerationError("init", "No variants available")

        return variant

    def _pick_video_template(self, project_id: int, template_id: Optional[int]) -> Optional[VideoTemplate]:
        """Pick video template by ID or get default."""
        if template_id:
            template = self.db.query(VideoTemplate).filter(
                VideoTemplate.id == template_id,
                VideoTemplate.project_id == project_id,
                VideoTemplate.is_deleted == False
            ).first()
            if not template:
                raise TemplateGenerationError("init", f"Video template {template_id} not found")
            return template

        # Get default
        return self.db.query(VideoTemplate).filter(
            VideoTemplate.project_id == project_id,
            VideoTemplate.is_default == True,
            VideoTemplate.is_deleted == False
        ).first()

    async def _run_preprocessing(self, prompt: str, model: str) -> dict:
        """LLM #1: Run preprocessing megaprompt."""
        try:
            result = await self.openai.generate_json(
                prompt=prompt,
                model=model,
                response_format="json"
            )
            return result
        except Exception as e:
            raise TemplateGenerationError("preprocessing", str(e))

    async def _run_image_prompt(self, json_data: dict, template: str, model: str) -> str:
        """LLM #2: Generate image prompt from JSON."""
        try:
            # Prepare prompt with JSON
            full_prompt = template.replace("<<<PASTE JSON HERE>>>", json.dumps(json_data, ensure_ascii=False))

            result = await self.openai.generate_text(
                prompt=full_prompt,
                model=model
            )

            # Validate length
            if len(result) > 1800:
                result = result[:1800]

            return result
        except Exception as e:
            raise TemplateGenerationError("image_prompt", str(e))

    async def _generate_image(self, prompt: str, model: str, aspect_ratio: str) -> str:
        """Generate image using fal.ai."""
        try:
            result = await self.fal.generate_image(
                prompt=prompt,
                model=model,
                aspect_ratio=aspect_ratio
            )
            return result["url"]
        except Exception as e:
            raise TemplateGenerationError("image", str(e))

    async def _generate_video(self, image_url: str, prompt: str, model: str, project_duration: int) -> str:
        """Generate video using fal.ai image-to-video."""
        try:
            result = await self.fal.generate_video_from_image(
                image_url=image_url,
                prompt=prompt,
                model=model,
                duration=project_duration
            )
            return result["url"]
        except Exception as e:
            raise TemplateGenerationError("video", str(e))

    def _get_project_duration(self, project_id: int) -> int:
        """Get video duration from project settings."""
        from app.models.project import Project
        project = self.db.query(Project).filter(Project.id == project_id).first()
        return project.duration if project else 10

    async def retry(self, generation_id: int) -> TemplateGeneration:
        """Retry generation from failed step."""
        generation = self.db.query(TemplateGeneration).filter(
            TemplateGeneration.id == generation_id
        ).first()

        if not generation:
            raise TemplateGenerationError("retry", "Generation not found")

        if generation.status != GenerationStatus.FAILED:
            raise TemplateGenerationError("retry", "Generation is not in failed state")

        failed_step = generation.failed_at_step

        # Get settings
        settings = self.db.query(TemplateSettings).filter(
            TemplateSettings.project_id == generation.project_id
        ).first()

        try:
            if failed_step == "preprocessing":
                # Restart from preprocessing
                variant = self.db.query(Variant).filter(
                    Variant.id == generation.variant_id
                ).first()

                prepared_prompt = PlaceholderService.replace(
                    settings.preprocessing_prompt,
                    variant.data
                )

                generation.status = GenerationStatus.PREPROCESSING
                self.db.commit()

                preprocessing_result = await self._run_preprocessing(
                    prepared_prompt, settings.llm_model
                )
                generation.preprocessing_result = preprocessing_result

                # Continue to image prompt
                failed_step = "image_prompt"

            if failed_step == "image_prompt":
                image_prompt = await self._run_image_prompt(
                    generation.preprocessing_result,
                    settings.image_prompt_template,
                    settings.llm_model
                )
                generation.image_prompt = image_prompt
                failed_step = "image"

            if failed_step == "image":
                generation.status = GenerationStatus.GENERATING_IMAGE
                self.db.commit()

                image_url = await self._generate_image(
                    generation.image_prompt,
                    settings.image_model,
                    settings.image_aspect_ratio.value
                )
                generation.image_url = image_url

                image_path = await self.downloader.download_image(image_url, generation.id)
                generation.image_path = image_path
                failed_step = "video"

            if failed_step == "video":
                generation.status = GenerationStatus.GENERATING_VIDEO
                self.db.commit()

                video_url = await self._generate_video(
                    generation.image_url,
                    generation.video_prompt,
                    settings.video_model,
                    project_duration=self._get_project_duration(generation.project_id)
                )
                generation.video_url = video_url

                video_path = await self.downloader.download_video(video_url, generation.id)
                generation.video_path = video_path

            # Complete
            generation.status = GenerationStatus.COMPLETED
            generation.completed_at = datetime.utcnow()
            generation.failed_at_step = None
            generation.error_message = None

            # Update variant usage
            variant = self.db.query(Variant).filter(
                Variant.id == generation.variant_id
            ).first()
            variant.usage_count += 1
            variant.last_used_at = datetime.utcnow()

            self.db.commit()
            return generation

        except TemplateGenerationError as e:
            generation.status = GenerationStatus.FAILED
            generation.failed_at_step = e.step
            generation.error_message = e.message
            self.db.commit()
            raise
```

---

## 5. API Endpoints

### 5.1 Router Setup

```python
# backend/app/api/template.py

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.template_settings import TemplateSettings
from app.models.video_template import VideoTemplate
from app.models.variant import Variant
from app.models.template_generation import TemplateGeneration
from app.schemas.template import *
from app.services.csv_parser import CSVParser, CSVParserError
from app.services.template_generation_service import TemplateGenerationService

router = APIRouter(prefix="/api/projects/{project_id}", tags=["template"])

# Helper
def get_template_project(db: Session, project_id: int, user: User) -> Project:
    """Get project and verify it's template type with user access."""
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.project_type != "template":
        raise HTTPException(status_code=400, detail="Project is not template type")

    # Verify workspace access (use existing pattern)
    from app.api.projects import user_has_workspace_access
    if project.workspace_id and not user_has_workspace_access(db, user.id, project.workspace_id):
        raise HTTPException(status_code=403, detail="No access to workspace")

    return project
```

### 5.2 Template Settings Endpoints

```python
@router.get("/template-settings", response_model=TemplateSettingsResponse)
async def get_template_settings(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = get_template_project(db, project_id, current_user)

    settings = db.query(TemplateSettings).filter(
        TemplateSettings.project_id == project_id
    ).first()

    if not settings:
        raise HTTPException(status_code=404, detail="Template settings not found")

    return settings

@router.put("/template-settings", response_model=TemplateSettingsResponse)
async def update_template_settings(
    project_id: int,
    data: TemplateSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = get_template_project(db, project_id, current_user)

    settings = db.query(TemplateSettings).filter(
        TemplateSettings.project_id == project_id
    ).first()

    if not settings:
        # Create if not exists
        settings = TemplateSettings(
            project_id=project_id,
            preprocessing_prompt=data.preprocessing_prompt or "",
            image_prompt_template=data.image_prompt_template or ""
        )
        db.add(settings)
    else:
        # Update existing
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(settings, field, value)

    db.commit()
    db.refresh(settings)
    return settings
```

### 5.3 Variants Endpoints

```python
@router.post("/variants/upload", response_model=CSVUploadResponse)
async def upload_variants(
    project_id: int,
    file: UploadFile = File(...),
    confirm_replace: bool = False,  # Frontend must confirm if has generations
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload CSV to replace all variants.
    If project has generations, frontend should show confirmation dialog
    and pass confirm_replace=true.
    """
    project = get_template_project(db, project_id, current_user)

    # Check if has generations - warn user
    has_generations = db.query(TemplateGeneration).filter(
        TemplateGeneration.project_id == project_id
    ).count() > 0

    if has_generations and not confirm_replace:
        raise HTTPException(
            status_code=409,
            detail="Project has generations. Existing variant links will be lost. Pass confirm_replace=true to proceed."
        )

    # Parse CSV
    content = await file.read()
    try:
        columns, rows = CSVParser.parse(content)
    except CSVParserError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Delete existing variants (re-import)
    db.query(Variant).filter(Variant.project_id == project_id).delete()

    # Create variants
    for i, row_data in enumerate(rows, start=1):
        variant = Variant(
            project_id=project_id,
            row_number=i,
            data=row_data
        )
        db.add(variant)

    # Update settings with columns
    settings = db.query(TemplateSettings).filter(
        TemplateSettings.project_id == project_id
    ).first()

    if settings:
        settings.csv_columns = columns

    db.commit()

    return CSVUploadResponse(
        variants_created=len(rows),
        csv_columns=columns,
        preview=rows[:5]
    )

@router.get("/variants", response_model=VariantListResponse)
async def list_variants(
    project_id: int,
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    sort_by: str = "row_number",  # row_number, usage_count
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = get_template_project(db, project_id, current_user)

    query = db.query(Variant).filter(Variant.project_id == project_id)

    # Search in JSON data
    if search:
        # PostgreSQL JSON search
        query = query.filter(
            Variant.data.cast(String).ilike(f"%{search}%")
        )

    # Sort
    if sort_by == "usage_count":
        query = query.order_by(Variant.usage_count.desc())
    else:
        query = query.order_by(Variant.row_number.asc())

    total = query.count()
    variants = query.offset(skip).limit(limit).all()

    # Get columns
    settings = db.query(TemplateSettings).filter(
        TemplateSettings.project_id == project_id
    ).first()

    return VariantListResponse(
        variants=variants,
        total=total,
        csv_columns=settings.csv_columns if settings else None
    )

@router.put("/variants/{variant_id}", response_model=VariantResponse)
async def update_variant(
    project_id: int,
    variant_id: int,
    data: VariantUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = get_template_project(db, project_id, current_user)

    variant = db.query(Variant).filter(
        Variant.id == variant_id,
        Variant.project_id == project_id
    ).first()

    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    if data.data is not None:
        variant.data = data.data

    db.commit()
    db.refresh(variant)
    return variant

@router.delete("/variants/{variant_id}")
async def delete_variant(
    project_id: int,
    variant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = get_template_project(db, project_id, current_user)

    variant = db.query(Variant).filter(
        Variant.id == variant_id,
        Variant.project_id == project_id
    ).first()

    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    db.delete(variant)
    db.commit()
    return {"status": "deleted"}

@router.delete("/variants")
async def delete_all_variants(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = get_template_project(db, project_id, current_user)

    count = db.query(Variant).filter(Variant.project_id == project_id).delete()
    db.commit()

    return {"deleted": count}
```

### 5.4 Video Templates Endpoints

```python
@router.get("/video-templates", response_model=List[VideoTemplateResponse])
async def list_video_templates(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = get_template_project(db, project_id, current_user)

    templates = db.query(VideoTemplate).filter(
        VideoTemplate.project_id == project_id,
        VideoTemplate.is_deleted == False
    ).all()

    return templates

@router.post("/video-templates", response_model=VideoTemplateResponse)
async def create_video_template(
    project_id: int,
    data: VideoTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = get_template_project(db, project_id, current_user)

    # If setting as default, unset others
    if data.is_default:
        db.query(VideoTemplate).filter(
            VideoTemplate.project_id == project_id,
            VideoTemplate.is_deleted == False
        ).update({"is_default": False})

    template = VideoTemplate(
        project_id=project_id,
        **data.model_dump()
    )
    db.add(template)
    db.commit()
    db.refresh(template)

    return template

@router.put("/video-templates/{template_id}", response_model=VideoTemplateResponse)
async def update_video_template(
    project_id: int,
    template_id: int,
    data: VideoTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = get_template_project(db, project_id, current_user)

    template = db.query(VideoTemplate).filter(
        VideoTemplate.id == template_id,
        VideoTemplate.project_id == project_id,
        VideoTemplate.is_deleted == False
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Video template not found")

    # If setting as default, unset others
    if data.is_default:
        db.query(VideoTemplate).filter(
            VideoTemplate.project_id == project_id,
            VideoTemplate.is_deleted == False,
            VideoTemplate.id != template_id
        ).update({"is_default": False})

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(template, field, value)

    db.commit()
    db.refresh(template)
    return template

@router.delete("/video-templates/{template_id}")
async def delete_video_template(
    project_id: int,
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = get_template_project(db, project_id, current_user)

    template = db.query(VideoTemplate).filter(
        VideoTemplate.id == template_id,
        VideoTemplate.project_id == project_id,
        VideoTemplate.is_deleted == False
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Video template not found")

    # Soft delete
    template.is_deleted = True
    db.commit()

    return {"status": "deleted"}
```

### 5.5 Generation Endpoints

```python
@router.post("/generate", response_model=GenerationResponse)
async def start_generation(
    project_id: int,
    data: GenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start generation as background task. Poll GET /generations/{id} for progress."""
    project = get_template_project(db, project_id, current_user)

    service = TemplateGenerationService(db)

    # Validate and create generation record
    try:
        generation = service.create_generation_record(
            project_id=project_id,
            variant_id=data.variant_id,
            video_template_id=data.video_template_id
        )
    except TemplateGenerationError as e:
        raise HTTPException(status_code=400, detail=f"{e.step}: {e.message}")

    # Start background task
    background_tasks.add_task(service.run_pipeline, generation.id)

    return generation  # Returns immediately with status=pending

@router.get("/generations", response_model=GenerationListResponse)
async def list_generations(
    project_id: int,
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = get_template_project(db, project_id, current_user)

    query = db.query(TemplateGeneration).filter(
        TemplateGeneration.project_id == project_id
    )

    if status:
        query = query.filter(TemplateGeneration.status == status)

    total = query.count()
    generations = query.order_by(
        TemplateGeneration.created_at.desc()
    ).offset(skip).limit(limit).all()

    # Enrich with variant data
    for gen in generations:
        if gen.variant:
            gen.variant_data = gen.variant.data

    return GenerationListResponse(
        generations=generations,
        total=total
    )

@router.get("/generations/{generation_id}", response_model=GenerationResponse)
async def get_generation(
    project_id: int,
    generation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = get_template_project(db, project_id, current_user)

    generation = db.query(TemplateGeneration).filter(
        TemplateGeneration.id == generation_id,
        TemplateGeneration.project_id == project_id
    ).first()

    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    if generation.variant:
        generation.variant_data = generation.variant.data

    return generation

@router.post("/generations/{generation_id}/retry", response_model=GenerationResponse)
async def retry_generation(
    project_id: int,
    generation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = get_template_project(db, project_id, current_user)

    service = TemplateGenerationService(db)

    try:
        generation = await service.retry(generation_id)
        return generation
    except TemplateGenerationError as e:
        raise HTTPException(status_code=500, detail=f"{e.step}: {e.message}")

@router.delete("/generations/{generation_id}")
async def delete_generation(
    project_id: int,
    generation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = get_template_project(db, project_id, current_user)

    generation = db.query(TemplateGeneration).filter(
        TemplateGeneration.id == generation_id,
        TemplateGeneration.project_id == project_id
    ).first()

    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    # Note: usage_count is NOT decremented
    db.delete(generation)
    db.commit()

    return {"status": "deleted"}
```

---

## 6. Migrations

### 6.1 Migration Script

```python
# backend/alembic/versions/xxx_add_template_project_type.py

"""add template project type models

Revision ID: xxx
Revises: <previous>
Create Date: 2026-01-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'xxx'
down_revision = '<previous>'

def upgrade() -> None:
    # 1. Create aspect_ratio enum
    aspect_ratio_enum = postgresql.ENUM('9:16', '16:9', '1:1', name='aspectratio')
    aspect_ratio_enum.create(op.get_bind())

    # 2. Create generation_status enum
    status_enum = postgresql.ENUM(
        'pending', 'preprocessing', 'generating_image',
        'generating_video', 'completed', 'failed',
        name='generationstatus'
    )
    status_enum.create(op.get_bind())

    # 3. Create template_settings table
    op.create_table(
        'template_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('preprocessing_prompt', sa.Text(), nullable=False),
        sa.Column('image_prompt_template', sa.Text(), nullable=False),
        sa.Column('llm_model', sa.String(50), nullable=False, server_default='gpt-4o-mini'),
        sa.Column('image_model', sa.String(100), nullable=False, server_default='fal-ai/nano-banana-pro'),
        sa.Column('video_model', sa.String(100), nullable=False, server_default='fal-ai/veo3/fast/image-to-video'),
        sa.Column('image_aspect_ratio', aspect_ratio_enum, nullable=False, server_default='9:16'),
        sa.Column('csv_columns', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id')
    )
    op.create_index('ix_template_settings_id', 'template_settings', ['id'])

    # 4. Create video_templates table
    op.create_table(
        'video_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_video_templates_id', 'video_templates', ['id'])

    # 5. Create variants table
    op.create_table(
        'variants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('row_number', sa.Integer(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_variants_id', 'variants', ['id'])
    op.create_index('ix_variants_project_usage', 'variants', ['project_id', 'usage_count'])

    # 6. Create template_generations table
    op.create_table(
        'template_generations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('variant_id', sa.Integer(), nullable=True),
        sa.Column('video_template_id', sa.Integer(), nullable=True),
        sa.Column('llm_model', sa.String(50), nullable=False),
        sa.Column('image_model', sa.String(100), nullable=False),
        sa.Column('video_model', sa.String(100), nullable=False),
        sa.Column('preprocessing_result', sa.JSON(), nullable=True),
        sa.Column('image_prompt', sa.Text(), nullable=True),
        sa.Column('video_prompt', sa.Text(), nullable=True),
        sa.Column('image_url', sa.String(500), nullable=True),
        sa.Column('video_url', sa.String(500), nullable=True),
        sa.Column('image_path', sa.String(255), nullable=True),
        sa.Column('video_path', sa.String(255), nullable=True),
        sa.Column('status', status_enum, nullable=False, server_default='pending'),
        sa.Column('failed_at_step', sa.String(20), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('llm_tokens_used', sa.Integer(), nullable=True),
        sa.Column('image_cost', sa.Float(), nullable=True),
        sa.Column('video_cost', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['variant_id'], ['variants.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['video_template_id'], ['video_templates.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_template_generations_id', 'template_generations', ['id'])

def downgrade() -> None:
    op.drop_table('template_generations')
    op.drop_table('variants')
    op.drop_table('video_templates')
    op.drop_table('template_settings')

    op.execute('DROP TYPE generationstatus')
    op.execute('DROP TYPE aspectratio')
```

---

## 7. Error Handling

### 7.1 Error Codes

| Status | Condition | Message |
|--------|-----------|---------|
| 400 | Invalid CSV | "CSV has no header row" / "CSV has no data rows" |
| 400 | Not template project | "Project is not template type" |
| 400 | Generation not failed | "Generation is not in failed state" |
| 403 | No workspace access | "No access to workspace" |
| 404 | Project not found | "Project not found" |
| 404 | Settings not found | "Template settings not found" |
| 404 | Variant not found | "Variant not found" |
| 404 | Template not found | "Video template not found" |
| 404 | Generation not found | "Generation not found" |
| 500 | Pipeline error | "{step}: {error_message}" |

### 7.2 Pipeline Error Recovery

```
failed_at_step = "preprocessing" → Retry from LLM #1 (variant data available)
failed_at_step = "image_prompt"  → Retry from LLM #2 (preprocessing_result preserved)
failed_at_step = "image"         → Retry from image gen (image_prompt preserved)
failed_at_step = "video"         → Retry from video gen (image_url preserved)
```

### 7.3 Background Task Pattern

```python
from fastapi import BackgroundTasks

# In endpoint: create record, start background task, return immediately
generation = service.create_generation_record(...)
background_tasks.add_task(service.run_pipeline, generation.id)
return generation  # status=pending

# Frontend polls GET /generations/{id} every 2-3 seconds
# until status in (completed, failed)
```

---

## 8. Existing Services Integration

### 8.1 Services to Reuse

| Service | Usage |
|---------|-------|
| `openai_service.py` | LLM calls (preprocessing, image prompt) |
| `fal_client.py` | Image/video generation |
| `media_downloader.py` | Download to data/media/ |

### 8.2 New Methods Needed

```python
# fal_client.py — add if not exists
async def generate_video_from_image(
    self,
    image_url: str,
    prompt: str,
    model: str,
    duration: int = 10
) -> dict:
    """Image-to-video generation."""
    pass
```

---

## 9. Implementation Order

| # | Component | Est. Lines | Dependencies |
|---|-----------|------------|--------------|
| 1 | Models (4 files) | ~200 | — |
| 2 | Migration | ~100 | Models |
| 3 | Schemas | ~150 | Models |
| 4 | CSV Parser | ~50 | — |
| 5 | Placeholder Service | ~30 | — |
| 6 | Generation Service | ~300 | Models, Services |
| 7 | API Router | ~350 | All above |
| 8 | Router Registration | ~10 | API |
| **Total** | | **~1200** | |

---

## 10. Testing Plan

### 10.1 Unit Tests

- CSV parser: encoding, empty cells, cyrillic
- Placeholder service: replacement, missing keys
- Variant selection: least used logic

### 10.2 Integration Tests

- Full pipeline: CSV → Generate → Video
- Retry from each failed step
- Soft delete behavior

### 10.3 Manual Testing

- [ ] Create template project
- [ ] Upload CSV with cyrillic
- [ ] Edit variant inline
- [ ] Create video template
- [ ] Generate with auto-select
- [ ] Generate with manual select
- [ ] Retry failed generation
- [ ] Delete generation
- [ ] Verify models shown on cards

---

Created: 2026-01-29
