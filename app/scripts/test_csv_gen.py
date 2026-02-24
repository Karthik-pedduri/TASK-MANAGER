import sys
import os

# Add parent directory to path so we can import app
sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.services.analysis import generate_csv_report
import traceback

def test():
    db = SessionLocal()
    try:
        print("Starting CSV generation...")
        csv = generate_csv_report(db)
        print("CSV Generation Successful!")
        print(f"Length: {len(csv)}")
        print("First 100 chars:")
        print(csv[:100])
    except Exception:
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test()
