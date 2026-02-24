from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import date, timedelta
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from app.database import AsyncSessionLocal
from app.models.tasks import (
    Task as TaskModel, 
    TaskStage as TaskStageModel, 
    State, 
    ArchivedTask, 
    ArchivedTaskStage
)
from app.services.email_worker import enqueue_email
import asyncio

async def check_overdue_and_notify():

    print("[SCHEDULER] Starting overdue check and notification job...")
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(State))
            all_states = result.scalars().all()
            states = {s.state_name: s.state_id for s in all_states}
            
            comp_id = states.get("completed")
            overdue_id = states.get("overdue")
            
            if comp_id is None or overdue_id is None:
                print("Required states missing - skipping job")
                return

            today = date.today()
            tomorrow = today + timedelta(days=1)
            reminder_threshold = today + timedelta(days=2)

            # Eager load assigned_user to prevent lazy load errors in async
            result = await db.execute(
                select(TaskModel)
                .options(joinedload(TaskModel.assigned_user))
                .filter(
                    TaskModel.status_state_id != comp_id,
                    TaskModel.due_date < today
                )
            )
            tasks = result.scalars().all()

            # Collect all email tasks to send concurrently
            email_tasks = []
            
            for task in tasks:
                if task.status_state_id != overdue_id:
                    task.status_state_id = overdue_id
                
                recipient = task.assigned_user.email if task.assigned_user else None
                recipient_name = task.assigned_user.full_name if task.assigned_user else "User"
                
                if recipient:
                    subject = f"Task Overdue: {task.name}"
                    body = (
                        f"Hello {recipient_name},\n\n"
                        f"The following task is now OVERDUE:\n"
                        f"Task ID: {task.task_id}\n"
                        f"Name: {task.name}\n"
                        f"Due Date: {task.due_date}\n"
                        f"Priority: {task.priority}\n\n"
                        f"Please update the status or contact your manager."
                    )
                    email_tasks.append(enqueue_email(subject, body, to_email=recipient))

            # Update overdue stages (granular)
            # Join TaskModel to check due_date, load task and user for email
            result = await db.execute(
                select(TaskStageModel)
                .join(TaskModel)
                .options(
                    joinedload(TaskStageModel.task).joinedload(TaskModel.assigned_user)
                )
                .filter(
                    TaskStageModel.status_state_id != comp_id,
                    TaskStageModel.completed_date.is_(None),
                    TaskStageModel.start_date.isnot(None),
                    TaskModel.due_date < today
                )
            )
            stages = result.scalars().all()

            for stage in stages:
                stage.status_state_id = overdue_id
                
                task = stage.task
                recipient = task.assigned_user.email if task.assigned_user else None
                recipient_name = task.assigned_user.full_name if task.assigned_user else "User"

                if recipient:
                    subject = f"Stage Overdue in Task {stage.task_id}"
                    body = (
                         f"Hello {recipient_name},\n\n"
                         f"A stage in your task is overdue:\n"
                         f"Stage: {stage.stage_name}\n"
                         f"Task: {task.name} (ID: {task.task_id})\n\n"
                         f"Please attend to this immediately."
                    )
                    email_tasks.append(enqueue_email(subject, body, to_email=recipient))

            await db.commit()
            
            # Send all emails concurrently (non-blocking, fails gracefully)
            if email_tasks:
                await asyncio.gather(*email_tasks, return_exceptions=True)
                print(f"[SCHEDULER] Sent {len(email_tasks)} overdue notifications")

            # Reminders for near-due tasks
            reminder_tasks = []
            
            result = await db.execute(
                select(TaskModel)
                .options(joinedload(TaskModel.assigned_user))
                .filter(
                    TaskModel.status_state_id != comp_id,
                    TaskModel.due_date.between(tomorrow, reminder_threshold)
                )
            )
            near_due_tasks = result.scalars().all()

            for task in near_due_tasks:
                recipient = task.assigned_user.email if task.assigned_user else None
                recipient_name = task.assigned_user.full_name if task.assigned_user else "User"

                if recipient:
                    subject = f"Reminder: Task Due Soon - {task.name}"
                    body = (
                        f"Hello {recipient_name},\n\n"
                        f"This is a reminder that your task is due soon:\n"
                        f"Task ID: {task.task_id}\n"
                        f"Name: {task.name}\n"
                        f"Due Date: {task.due_date}\n\n"
                        f"Please ensure it is completed on time."
                    )
                    reminder_tasks.append(enqueue_email(subject, body, to_email=recipient))
            
            # Send all reminder emails concurrently
            if reminder_tasks:
                await asyncio.gather(*reminder_tasks, return_exceptions=True)
                print(f"[SCHEDULER] Sent {len(reminder_tasks)} reminder notifications")
            
            print("[SCHEDULER] Overdue check completed successfully")

        except Exception as e:
            await db.rollback()
            print(f"[SCHEDULER] Error during overdue job: {e}")

async def archive_old_tasks():
    print("[SCHEDULER] Starting archiving job for completed tasks...")
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(State).filter(State.state_name == "completed"))
            completed_state = result.scalars().first()
            if not completed_state:
                print("[SCHEDULER] Completed state not found - skipping archiving")
                return

            # Keep tasks for 30 days after completion
            archive_threshold = date.today() - timedelta(days=30)
            
            # Find tasks to archive
            result = await db.execute(
                select(TaskModel)
                .options(joinedload(TaskModel.stages))
                .filter(
                    TaskModel.status_state_id == completed_state.state_id,
                    TaskModel.completed_date <= archive_threshold
                )
            )
            tasks_to_archive = result.scalars().unique().all()
            
            if not tasks_to_archive:
                print("[SCHEDULER] No tasks found to archive")
                return

            for task in tasks_to_archive:
                # 1. Archive Task
                archived_task = ArchivedTask(
                    task_id=task.task_id,
                    name=task.name,
                    description=task.description,
                    status_state_id=task.status_state_id,
                    due_date=task.due_date,
                    completed_date=task.completed_date,
                    priority=task.priority,
                    assigned_user_id=task.assigned_user_id,
                    created_by_id=task.created_by_id,
                    idempotency_key=task.idempotency_key,
                    created_at=task.created_at,
                    updated_at=task.updated_at
                )
                db.add(archived_task)
                
                # 2. Archive Stages
                for stage in task.stages:
                    archived_stage = ArchivedTaskStage(
                        stage_id=stage.stage_id,
                        task_id=stage.task_id,
                        stage_name=stage.stage_name,
                        estimated_time_hours=stage.estimated_time_hours,
                        actual_time_hours=stage.actual_time_hours,
                        status_state_id=stage.status_state_id,
                        order_number=stage.order_number,
                        start_date=stage.start_date,
                        completed_date=stage.completed_date,
                        created_at=stage.created_at,
                        updated_at=stage.updated_at
                    )
                    db.add(archived_stage)
                
                # 3. Remove Original Task (Stages will be removed by CASCADE if configured, 
                # but we explicitly archived them so deleting the task is enough)
                await db.delete(task)
            
            await db.commit()
            print(f"[SCHEDULER] Successfully archived {len(tasks_to_archive)} tasks.")

        except Exception as e:
            await db.rollback()
            print(f"[SCHEDULER] Error during archiving job: {e}")

def setup_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_overdue_and_notify,
        trigger=CronTrigger(hour=9, minute=0) 
    )
    scheduler.add_job(
        archive_old_tasks,
        trigger=CronTrigger(hour=2, minute=0) # Run at 2 AM
    )
    scheduler.start()
    return scheduler