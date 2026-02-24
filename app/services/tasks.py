from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from fastapi import HTTPException, status
from datetime import date, datetime, timezone

from app.models.tasks import Task, TaskStage, TaskTemplate, State
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate, TaskStageCreate, TaskStageUpdate
from app.services.email_worker import enqueue_email


async def get_state_by_name(db: AsyncSession, name: str) -> State:
    result = await db.execute(select(State).filter(State.state_name == name))
    state = result.scalars().first()
    if not state:
        raise HTTPException(status_code=500, detail=f"State '{name}' not found")
    return state


async def get_all_states(db: AsyncSession) -> dict[str, int]:
    result = await db.execute(select(State))
    states = result.scalars().all()
    return {s.state_name: s.state_id for s in states}


async def create_task(db: AsyncSession, task_data: TaskCreate, current_user_id: int):
    # Idempotency check
    if task_data.idempotency_key:
        result = await db.execute(
            select(Task).filter(
                Task.idempotency_key == task_data.idempotency_key,
                Task.is_deleted == False
            )
        )
        existing_task = result.scalars().first()
        if existing_task:
            return await get_task_by_id(db, existing_task.task_id)

    pending_state = await get_state_by_name(db, "pending")

    new_task = Task(
        name=task_data.name,
        description=task_data.description,
        due_date=task_data.due_date,
        priority=task_data.priority,
        assigned_user_id=task_data.assigned_user_id,
        created_by_id=current_user_id,
        idempotency_key=task_data.idempotency_key,
        status_state_id=pending_state.state_id
    )

    db.add(new_task)
    await db.flush()

    # Handle template stages
    if task_data.template_id:
        stmt = select(TaskTemplate).options(joinedload(TaskTemplate.stages)).filter(TaskTemplate.template_id == task_data.template_id)
        result = await db.execute(stmt)
        template = result.scalars().unique().first()
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        for ts in sorted(template.stages, key=lambda x: x.order_number):
            db.add(TaskStage(
                task_id=new_task.task_id,
                stage_name=ts.stage_name,
                estimated_time_hours=ts.estimated_time_hours or 0.0,
                status_state_id=pending_state.state_id,
                order_number=ts.order_number
            ))

    # Handle explicit stages
    for stage in task_data.stages:
        db.add(TaskStage(
            task_id=new_task.task_id,
            stage_name=stage.stage_name,
            estimated_time_hours=stage.estimated_time_hours,
            status_state_id=pending_state.state_id,
            order_number=stage.order_number
        ))

    return new_task


async def get_task_by_id(db: AsyncSession, task_id: int):
    result = await db.execute(
        select(Task).options(
            joinedload(Task.stages),
            joinedload(Task.assigned_user)
        ).filter(Task.task_id == task_id, Task.is_deleted == False)
    )
    task = result.scalars().unique().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


async def update_stage(db: AsyncSession, stage_id: int, update_data: TaskStageUpdate):
    result = await db.execute(select(TaskStage).filter(TaskStage.stage_id == stage_id))
    stage = result.scalars().first()
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")

    result = await db.execute(select(State).filter(State.state_id == update_data.status_state_id))
    new_status = result.scalars().first()
    if not new_status:
        raise HTTPException(status_code=404, detail="Invalid status ID")

    stage.status_state_id = update_data.status_state_id
    today = date.today()

    if new_status.state_name == "in-progress" and stage.start_date is None:
        stage.start_date = today
    if new_status.state_name == "completed":
        if update_data.actual_time_hours is None and stage.actual_time_hours is None:
            raise HTTPException(status_code=400, detail="Actual time hours required to complete stage")
        stage.completed_date = update_data.completed_date or today

    if update_data.actual_time_hours is not None:
        stage.actual_time_hours = update_data.actual_time_hours
    if update_data.start_date is not None:
        stage.start_date = update_data.start_date
    if update_data.completed_date is not None:
        stage.completed_date = update_data.completed_date

    # Update parent task status
    await update_task_status_from_stages(db, stage.task_id)

    return stage


async def update_task_status_from_stages(db: AsyncSession, task_id: int):
    result = await db.execute(
        select(Task).options(joinedload(Task.stages)).filter(Task.task_id == task_id)
    )
    task = result.scalars().unique().first()
    if not task:
        return

    states = await get_all_states(db)
    comp_id = states.get("completed")
    overdue_id = states.get("overdue")
    in_prog_id = states.get("in-progress")

    today = date.today()
    all_completed = all(s.status_state_id == comp_id for s in task.stages)

    if all_completed and task.stages:
        task.status_state_id = comp_id
        task.completed_date = max((s.completed_date for s in task.stages if s.completed_date), default=today)
    elif task.due_date < today and task.status_state_id != comp_id:
        task.status_state_id = overdue_id
    elif any(s.status_state_id == in_prog_id for s in task.stages):
        task.status_state_id = in_prog_id
