from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel
from app.db.base import get_db
from app.models import Project
from app.services.openai_service import openai_service

router = APIRouter()


class GenerateVariantsRequest(BaseModel):
    project_id: int


class RegenerateVariantsRequest(BaseModel):
    project_id: int
    exclude_variants: List[Dict[str, Any]] = []


class ContentVariant(BaseModel):
    id: int
    description: str
    content_variables: Dict[str, Any]


class VariantsResponse(BaseModel):
    variants: List[ContentVariant]


@router.post("/generate-variants", response_model=VariantsResponse)
async def generate_content_variants(
    request: GenerateVariantsRequest,
    db: Session = Depends(get_db)
):
    """
    Генерирует 10 вариантов контента на основе Story Template проекта

    Возвращает:
    {
        "variants": [
            {
                "id": 1,
                "description": "Блондинка в красном платье, Ferrari красная, Париж, закат",
                "content_variables": {
                    "character": {
                        "appearance": "blonde",
                        "outfit": "red evening dress",
                        "age": "25"
                    },
                    "vehicle": {
                        "brand": "Ferrari SF90",
                        "color": "red"
                    },
                    "location": {
                        "city": "Paris",
                        "landmark": "Eiffel Tower",
                        "time": "sunset"
                    }
                }
            },
            ... (еще 9 вариантов)
        ]
    }
    """
    project = db.query(Project).filter(Project.id == request.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Вызываем AI для генерации вариантов
    variants = await openai_service.generate_content_variants(
        story_template=project.story_template,
        count=10
    )

    return {"variants": variants}


@router.post("/regenerate-variants", response_model=VariantsResponse)
async def regenerate_content_variants(
    request: RegenerateVariantsRequest,
    db: Session = Depends(get_db)
):
    """
    Регенерирует 10 новых вариантов, исключая уже показанные
    """
    project = db.query(Project).filter(Project.id == request.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    variants = await openai_service.generate_content_variants(
        story_template=project.story_template,
        count=10,
        exclude=request.exclude_variants
    )

    return {"variants": variants}
