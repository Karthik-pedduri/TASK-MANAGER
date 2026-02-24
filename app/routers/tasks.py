from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from datetime import datetime, timezone

from app.dependencies import get_db, get_current_user
from app.models.user import User as UserModel
from app.models.tasks import Task as TaskModel, TaskStage as TaskStageModel, TaskTemplate, State
from app.schemas.task import (TaskCreate, Task as TaskSchema, TaskStageUpdate, TaskStage, TaskUpdate, TaskTemplateResponse, TaskStageCreate)
from app.services import tasks as task_service
from app.services.email_worker import enqueue_email

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("/", response_model=TaskSchema, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    task = await task_service.create_task(db, task_data, current_user.user_id)
    await db.commit()
    return await task_service.get_task_by_id(db, task.task_id)

@router.post("/{task_id}/stages", response_model=TaskStage, status_code=status.HTTP_201_CREATED)
async def add_stage_to_task(
    task_id: int,
    stage_data: TaskStageCreate,
    db: AsyncSession = Depends(get_db),
):
    # Ensure task exists
    task = await task_service.get_task_by_id(db, task_id)

    # Figure out the max order number
    result = await db.execute(
        select(TaskStageModel.order_number)
        .filter(TaskStageModel.task_id == task_id)
        .order_by(TaskStageModel.order_number.desc())
    )
    max_order = result.scalars().first() or 0

    pending_state = await task_service.get_state_by_name(db, "pending")

    new_stage = TaskStageModel(
        task_id=task_id,
        stage_name=stage_data.stage_name,
        estimated_time_hours=stage_data.estimated_time_hours,
        status_state_id=pending_state.state_id,
        order_number=max_order + 1,
    )
    db.add(new_stage)
    await db.commit()
    await db.refresh(new_stage)
    return new_stage

@router.put("/stages/{stage_id}", response_model=TaskStage)
async def update_stage(stage_id: int, update_data: TaskStageUpdate, db: AsyncSession = Depends(get_db)):
    stage = await task_service.update_stage(db, stage_id, update_data)
    await db.commit()
    await db.refresh(stage)
    return stage

@router.patch("/{task_id}", response_model=TaskSchema)
async def update_task(task_id: int, update_data: TaskUpdate, db: AsyncSession = Depends(get_db)):
    task = await task_service.get_task_by_id(db, task_id)

    if update_data.name is not None:
        task.name = update_data.name
    if update_data.description is not None:
        task.description = update_data.description
    if update_data.due_date is not None:
        task.due_date = update_data.due_date
    if update_data.priority is not None:
        task.priority = update_data.priority
    if update_data.assigned_user_id is not None:
        task.assigned_user_id = update_data.assigned_user_id

    if update_data.status_state_id is not None:
        states = await task_service.get_all_states(db)
        completed_id = states.get("completed")
        if update_data.status_state_id == completed_id:
            if any(s.status_state_id != completed_id for s in task.stages):
                raise HTTPException(
                    status_code=400, 
                    detail="Cannot mark task as completed while stages are still open"
                )
        task.status_state_id = update_data.status_state_id

    await db.commit()
    return await task_service.get_task_by_id(db, task_id)

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await task_service.get_task_by_id(db, task_id)
    task.is_deleted = True
    task.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return None

@router.delete("/stages/{stage_id}", response_model=TaskSchema)
async def delete_stage(stage_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TaskStageModel).filter(TaskStageModel.stage_id == stage_id))
    stage = result.scalars().first()
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")

    task_id = stage.task_id
    await db.delete(stage)
    await db.commit()

    # Reorder remaining stages
    result = await db.execute(
        select(TaskStageModel)
        .filter_by(task_id=task_id)
        .order_by(TaskStageModel.order_number)
    )
    remaining_stages = result.scalars().all()
    for i, s in enumerate(remaining_stages, start=1):
        s.order_number = i
    await db.commit()
    
    return await task_service.get_task_by_id(db, task_id)

@router.get("/", response_model=list[TaskSchema])
async def list_tasks(
    last_id: int | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    query = select(TaskModel).options(
        joinedload(TaskModel.stages),
        joinedload(TaskModel.assigned_user)
    ).filter(TaskModel.is_deleted == False)

    if last_id:
        query = query.filter(TaskModel.task_id > last_id)

    query = query.order_by(TaskModel.task_id).limit(limit)
    result = await db.execute(query)
    return result.scalars().unique().all()

@router.get("/templates", response_model=list[TaskTemplateResponse])
async def list_templates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TaskTemplate).options(joinedload(TaskTemplate.stages)))
    return result.scalars().unique().all()

@router.get("/{task_id}", response_model=TaskSchema)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    return await task_service.get_task_by_id(db, task_id)

@router.post("/{task_id}/notify")
async def notify_user_manually(task_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TaskModel)
        .options(joinedload(TaskModel.assigned_user), joinedload(TaskModel.status))
        .filter(TaskModel.task_id == task_id)
    )
    task = result.scalars().first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not task.assigned_user:
        raise HTTPException(status_code=400, detail="Task has no assigned user")
    
    recipient = task.assigned_user.email
    subject = f"Notification: Task {task.name}"
    body = (
        f"This is a manual notification for your task:\n"
        f"Task: {task.name} (ID: {task.task_id})\n"
        f"Status: {task.status.state_name if task.status else 'Unknown'}\n"
        f"Priority: {task.priority}\n"
    )
    await enqueue_email(subject, body, to_email=recipient)
    return {"message": f"Notification sent to {recipient}"}
