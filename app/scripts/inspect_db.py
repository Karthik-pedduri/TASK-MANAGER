from app.database import SessionLocal
from app.models.tasks import State
from sqlalchemy import text

def inspect_states():
    db = SessionLocal()
    try:
        states = db.query(State).all()
        print(f"Found {len(states)} states:")
        for s in states:
            print(f"ID: {s.state_id}, Name: '{s.state_name}'")
            
        if not states:
            print("No states found! This is why creation fails.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    inspect_states()
