from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
from app.utils.sanitization import sanitize_string
from app.schemas.user import UserResponse


# ── Stage schemas ───────────────────────────────────────

class TaskStageBase(BaseModel):
    stage_name: str
    estimated_time_hours: float | None = Field(None, ge=0)
    order_number: int = Field(..., ge=1)

    @field_validator("stage_name", mode="before")
    @classmethod
    def sanitize(cls, v):
        return sanitize_string(v)


class TaskStageCreate(TaskStageBase):
    estimated_time_hours: float = Field(..., gt=0, description="Must be greater than 0")


class TaskStageUpdate(BaseModel):
    status_state_id: int = Field(..., description="Required: new status (pending/in-progress/completed/overdue)")
    actual_time_hours: float | None = Field(None, gt=0)
    start_date: date | None = None
    completed_date: date | None = None


class TaskStage(TaskStageBase):
    stage_id: int
    task_id: int
    status_state_id: int
    actual_time_hours: float | None = None
    start_date: date | None = None
    completed_date: date | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


# ── Template schemas ────────────────────────────────────

class TaskTemplateStageResponse(BaseModel):
    id: int
    stage_name: str
    estimated_time_hours: float | None = None
    order_number: int

    class Config:
        from_attributes = True


class TaskTemplateResponse(BaseModel):
    template_id: int
    name: str
    description: str | None = None
    stages: list[TaskTemplateStageResponse] = []

    class Config:
        from_attributes = True


# ── Common base for readable/writeable fields ──
class TaskBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: str | None = None
    due_date: date
    priority: str | None = None
    template_id: int | None = None
    assigned_user_id: int | None = None
    idempotency_key: str | None = None

    @field_validator("name", "description", mode="before")
    @classmethod
    def sanitize(cls, v):
        return sanitize_string(v)


class TaskCreate(TaskBase):
    priority: str = Field(..., pattern=r"^(high|medium|low)$")
    stages: list[TaskStageCreate] = Field(default_factory=list)


class TaskUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    description: str | None = None
    due_date: date | None = None
    priority: str | None = Field(None, pattern=r"^(high|medium|low)$")
    assigned_user_id: int | None = None
    status_state_id: int | None = None       # admin / auto-update only in most cases


class Task(TaskBase):
    task_id: int
    status_state_id: int
    completed_date: date | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    assigned_user: UserResponse | None = None
    stages: list[TaskStage] = []

    class Config:
        from_attributes = True