from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from pydantic import BaseModel, Field
from app.dependencies import get_db
from app.models.tasks import TaskTemplate, TaskTemplateStage, State, TaskStage
from app.schemas.task import TaskTemplateResponse


router = APIRouter(prefix="/templates", tags=["templates"])

# ── Schemas ─────────────────────────────────────────────
class TemplateStageCreate(BaseModel):
    stage_name: str = Field(..., min_length=1, max_length=100)
    estimated_time_hours: float | None = Field(None, ge=0)
    order_number: int = Field(..., ge=1)

class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    stages: list[TemplateStageCreate] = Field(default_factory=list)


# ── Routes ─────────────────────────────────────────────
@router.get("/", response_model=list[TaskTemplateResponse])
async def list_templates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TaskTemplate).options(joinedload(TaskTemplate.stages))
    )
    return result.scalars().unique().all()


@router.post("/", response_model=TaskTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(data: TemplateCreate, db: AsyncSession = Depends(get_db)):
    template = TaskTemplate(name=data.name, description=data.description)
    db.add(template)
    await db.flush()

    for s in data.stages:
        db.add(TaskTemplateStage(
            template_id=template.template_id,
            stage_name=s.stage_name,
            estimated_time_hours=s.estimated_time_hours,
            order_number=s.order_number,
        ))

    await db.commit()

    # Reload with stages
    result = await db.execute(
        select(TaskTemplate).options(joinedload(TaskTemplate.stages))
        .filter(TaskTemplate.template_id == template.template_id)
    )
    return result.scalars().unique().first()


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(template_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TaskTemplate).filter(TaskTemplate.template_id == template_id)
    )
    template = result.scalars().first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    await db.delete(template)
    await db.commit()
    return None
