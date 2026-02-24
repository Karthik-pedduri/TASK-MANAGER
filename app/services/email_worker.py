import asyncio
from sqlalchemy.future import select
from app.utils.email import send_email_async
from typing import TypedDict

from app.database import AsyncSessionLocal
from app.models.email import EmailLog
from datetime import datetime, timezone

class EmailJob(TypedDict):
    log_id: int
    subject: str
    body: str
    to_email: str | None

# Global queue for email jobs
email_queue: asyncio.Queue[EmailJob] = asyncio.Queue()

async def email_worker():
    """
    Background worker that pulls jobs from the email_queue and sends them.
    This runs indefinitely until the application shuts down.
    Now uses pure async await for sending.
    """
    print("[WORKER] Background email worker (Pure Async) started.")
    while True:
        # Get an email job from the queue (blocks if empty)
        job = await email_queue.get()
        log_id = job.get("log_id")
        subject = job.get("subject")
        body = job.get("body")
        to_email = job.get("to_email")
        
        try:
            # Direct await - no thread executor needed anymore!
            await send_email_async(subject, body, to_email)
            
            # Update DB status to 'sent'
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(EmailLog).filter(EmailLog.id == log_id))
                log_entry = result.scalars().first()
                if log_entry:
                    log_entry.status = "sent"
                    log_entry.sent_at = datetime.now(timezone.utc)
                    await db.commit()
            
        except Exception as e:
            print(f"[WORKER ERROR] Failed to process email job: {e}")
            # Update DB status to 'failed'
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(EmailLog).filter(EmailLog.id == log_id))
                log_entry = result.scalars().first()
                if log_entry:
                    log_entry.status = "failed"
                    log_entry.error_message = str(e)
                    await db.commit()
        finally:
            # Notify the queue that the job has been processed
            email_queue.task_done()

async def enqueue_email(subject: str, body: str, to_email: str | None = None):
    """
    Public API to add an email job to the database and background queue.
    """
    # 1. Save to DB
    async with AsyncSessionLocal() as db:
        new_log = EmailLog(subject=subject, body=body, to_email=to_email, status="pending")
        db.add(new_log)
        await db.commit()
        await db.refresh(new_log)
        log_id = new_log.id

    # 2. Add to queue for immediate processing
    await email_queue.put({
        "log_id": log_id,
        "subject": subject,
        "body": body,
        "to_email": to_email
    })
    print(f"[QUEUE] Enqueued email (DB ID: {log_id}): {subject[:30]}...")
