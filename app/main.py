import asyncio
import fcntl
import os
import traceback
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base
from app.routers.tasks import router as tasks_router
from app.routers.analysis import router as analysis_router      
from app.routers.users import router as users_router
from app.routers.auth import router as auth_router
from app.routers.templates import router as templates_router

from app.services.scheduler import setup_scheduler
from app.services.email_worker import email_worker

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Determine if this process should run the scheduler
    # We use a file lock. Only the first worker to grab the lock will start the scheduler.
    lock_file = "/tmp/fastapi_scheduler.lock"
    lock_fd = None
    scheduler = None
    
    try:
        lock_fd = open(lock_file, "w")
        # Try to acquire an exclusive, non-blocking lock
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        print(f"[PROCESS {os.getpid()}] Acquired scheduler lock. Starting APScheduler...")
        scheduler = setup_scheduler()
    except (BlockingIOError, IOError):
        # Lock is held by another worker
        print(f"[PROCESS {os.getpid()}] Another worker is running the scheduler. Skipping.")
        if lock_fd:
            lock_fd.close()
            lock_fd = None

    # Start Email Worker - we still want one worker pulling from the queue per process,
    # or ideally only one process, but `asyncio.Queue` is per-process so the DB ensures 
    # we don't process emails multiple times if we've handled the queue correctly.
    # Actually, if the queue is per-process, we'd need Redis for distributed queuing.
    # For now, this worker just checks its local queue, which is fine as `enqueue_email` pushes locally.
    worker_task = asyncio.create_task(email_worker())
    
    yield
    
    # Clean up
    if scheduler:
        scheduler.shutdown(wait=True)
        if lock_fd:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()
            
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        print("[WORKER] Email worker shut down.")


app = FastAPI(
    lifespan=lifespan,
    title="Task Manager API",
    description="Task Management System with Stages, Analysis & Notifications",
    version="1.0.0",
)

# Enable CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex="https?://.*",  # Flexibly allow all origins during development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#Global exception handler to ensure CORS headers on failure
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_msg = traceback.format_exc()
    print(f"CRITICAL ERROR: {error_msg}")
    
    # Write to log
    with open("error.log", "a") as f:
        f.write(f"\n[{datetime.now()}] 500 Error:\n{error_msg}\n")
        
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "error": str(exc)},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true"
        }
    )

app.include_router(tasks_router)
app.include_router(analysis_router)
app.include_router(users_router)
app.include_router(auth_router)
app.include_router(templates_router)

@app.get("/")
def root():
    return {"message": "Task Manager API running "}
