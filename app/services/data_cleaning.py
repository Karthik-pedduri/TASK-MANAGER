from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timezone
from app.models.tasks import Task as TaskModel

async def run_data_cleaning(db: AsyncSession):
    """
    Loops through all active tasks and removes duplicates with the same name and creation date.
    Performs a soft-delete rather than a hard delete to match the application's architecture.
    """
    result = await db.execute(select(TaskModel).filter(TaskModel.is_deleted == False).order_by(TaskModel.created_at.desc()))
    tasks = result.scalars().all()
    seen = {}
    log = []

    for t in tasks:
        day = t.created_at.date()
        key = (t.name, day)

        if key in seen:
            t.is_deleted = True
            t.deleted_at = datetime.now(timezone.utc)
            log.append(f"Deleted Dupe: {t.name} (ID: {t.task_id})")
        else:
            seen[key] = t.task_id

    if log:
        await db.commit()
        return {"status": "success", "cleaned": len(log), "items": log}
    
    return {"status": "success", "message": "No duplicates found"}
