import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app.models.tasks import State

# Use an in-memory SQLite database for testing, or a test file
# Note: SQLite async requires aiosqlite driver
# But the app uses postgresql+asyncpg. 
# Better to use a separate test database on the same postgres instance if possible,
# or drag in aiosqlite. 
# Given environment constraints, let's try to mock or use the existing dev DB but be careful.
# Actually, since I can't easily install new packages (aiosqlite), I should use the existing PG DB 
# but maybe a different table prefix or just use it as is if it's a dev environment.
# The user's prompt implies "refactoring environment", so dev DB usage is acceptable if careful.
# However, `comprehensive_api_tests.py` runs against localhost:8000 which uses the dev DB.

# Let's try to use the dev DB but ensuring we don't break things.
# Actually, let's just run a sanity check on the existing DB.

# Override dependency
async def override_get_db():
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        yield db

app.dependency_overrides[get_db] = override_get_db


async def test_create_and_fetch_task():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Create Task
        response = await ac.post("/tasks/", json={
            "name": "Integration Test Task",
            "description": "Testing async refactor",
            "priority": "high",
            "due_date": "2024-12-31" 
        })
        assert response.status_code == 201, f"Create failed: {response.text}"
        data = response.json()
        task_id = data["task_id"]
        assert data["name"] == "Integration Test Task"
        
        # Get Task
        response = await ac.get(f"/tasks/{task_id}")
        assert response.status_code == 200
        assert response.json()["task_id"] == task_id
        
        print(f"Verified Async Task Creation & Fetch: Task ID {task_id}")


async def test_analysis_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Completion Stats
        response = await ac.get("/analysis/completion")
        assert response.status_code == 200
        print("Verified Async Analysis Service (Stats):", response.json())

        # Visualization (Priority Pie)
        response = await ac.get("/analysis/visualizations/priority")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert len(response.content) > 0
        print("Verified Sync/Threadpool Visualization Generation")

if __name__ == "__main__":
    # If run directly, executes the async tests manually without pytest
    async def run_checks():
        print("Starting Verification...")
        try:
            from app.database import engine, Base
            # Ensure tables exist (optional, usually they do)
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            # Replaced override with actual function to ensure correct scope if needed
            # but app.dependency_overrides is already set.
            
            async with AsyncClient(app=app, base_url="http://test") as ac:
                 # 1. Create Task
                print("1. Testing Task Creation...")
                response = await ac.post("/tasks/", json={
                    "name": "Refactor Verification Task",
                    "description": "Verifying async refactor",
                    "priority": "high",
                    "due_date": "2024-12-31"
                })
                if response.status_code != 201:
                    print(f"FAILED: {response.status_code} - {response.text}")
                    return
                task_id = response.json()["task_id"]
                print(f"   SUCCESS: Created Task {task_id}")

                # 2. Get Task
                print("2. Testing Task Retrieval...")
                response = await ac.get(f"/tasks/{task_id}")
                if response.status_code != 200:
                    print(f"FAILED: {response.status_code} - {response.text}")
                    return
                print("   SUCCESS: Retrieved Task")

                # 3. Analysis Stats
                print("3. Testing Analysis Stats (Hybrid Async/Sync)...")
                response = await ac.get("/analysis/completion")
                if response.status_code != 200:
                    print(f"FAILED: {response.status_code} - {response.text}")
                    return
                print(f"   SUCCESS: Stats Retrieved: {response.json()}")

                # 4. Visualization
                print("4. Testing Visualization (Sync in Threadpool)...")
                response = await ac.get("/analysis/visualizations/priority")
                if response.status_code != 200:
                    print(f"FAILED: {response.status_code} - {response.text}")
                    return
                if response.headers["content-type"] != "image/png":
                     print(f"FAILED: Wrong content type {response.headers['content-type']}")
                     return
                print("   SUCCESS: Image generated")
                
            print("\nALL CHECKS PASSED. Refactoring Verified.")
            
        except Exception as e:
            print(f"CRITICAL FAILURE: {e}")
            import traceback
            traceback.print_exc()

    asyncio.run(run_checks())
