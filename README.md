

---

## 🛠 Tech Stack
- **Framework:** FastAPI (Asynchronous)
- **Database:** PostgreSQL with SQLAlchemy 2.0 (Async Engine)
- **Background Tasks:** APScheduler & asyncio.Queue
- **Authentication:** OAuth2 with JWT (JSON Web Tokens)
- **Validation:** Pydantic v2
- **Production Server:** Gunicorn with Uvicorn workers

---

## 🚦 Getting Started

### 1. Prerequisites
- Python 3.12+
- PostgreSQL instance

### 2. Installation
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run the Application
```bash
# Production Mode
gunicorn -c gunicorn_conf.py app.main:app

# Development Mode
uvicorn app.main:app --reload
```

---



