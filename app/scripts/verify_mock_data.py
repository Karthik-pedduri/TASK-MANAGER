"""
Quick verification script to check the realistic mock data
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.tasks import Task, TaskStage, State
from app.models.user import User
from sqlalchemy.orm import joinedload

def verify_data():
    db = SessionLocal()
    try:
        print("\n" + "="*60)
        print("📊 MOCK DATA VERIFICATION REPORT")
        print("="*60 + "\n")
        
        # Count records
        user_count = db.query(User).count()
        task_count = db.query(Task).count()
        stage_count = db.query(TaskStage).count()
        
        print(f"✅ Database Record Counts:")
        print(f"   - Users: {user_count}")
        print(f"   - Tasks: {task_count}")
        print(f"   - Task Stages: {stage_count}")
        
        # Sample users
        print(f"\n✅ Sample Users (showing 5):")
        users = db.query(User).limit(5).all()
        for u in users:
            print(f"   - {u.full_name} (@{u.username}) - {u.email}")
        
        # Sample tasks
        print(f"\n✅ Sample Tasks (showing 8):")
        tasks = db.query(Task).options(joinedload(Task.assigned_user)).limit(8).all()
        states_map = {1: "pending", 2: "in-progress", 3: "completed", 4: "overdue"}
        
        for t in tasks:
            status_name = states_map.get(t.status_state_id, "unknown")
            assigned_to = t.assigned_user.full_name if t.assigned_user else "Unassigned"
            print(f"   - {t.name}")
            print(f"     Priority: {t.priority} | Status: {status_name} | Assigned: {assigned_to}")
        
        # Check for template names (should be NONE)
        print(f"\n🔍 Checking for template/generic names...")
        template_tasks = db.query(Task).filter(
            (Task.name.like('%Task #%')) | 
            (Task.name.like('%Historical%')) |
            (Task.name.like('%Active%'))
        ).all()
        
        if template_tasks:
            print(f"   ❌ WARNING: Found {len(template_tasks)} template-style task names!")
            for t in template_tasks[:3]:
                print(f"      - {t.name}")
        else:
            print(f"   ✅ No template/generic names found - all tasks have realistic names!")
        
        # Status distribution
        print(f"\n📈 Task Status Distribution:")
        for state_id, state_name in states_map.items():
            count = db.query(Task).filter(Task.status_state_id == state_id).count()
            print(f"   - {state_name.capitalize()}: {count} tasks")
        
        # Priority distribution
        print(f"\n🎯 Task Priority Distribution:")
        for priority in ["high", "medium", "low"]:
            count = db.query(Task).filter(Task.priority == priority).count()
            print(f"   - {priority.capitalize()}: {count} tasks")
        
        print("\n" + "="*60)
        print("✨ Verification Complete!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error during verification: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_data()
