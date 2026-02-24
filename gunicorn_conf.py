import multiprocessing

# Gunicorn configuration file
# For FastAPI/Uvicorn, we use the UvicornWorker

# Bind to all interfaces on port 8000
bind = "0.0.0.0:8000"

# Worker configuration
# Standard formula: (2 x num_cores) + 1
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"

# Timeout and Keepalive
timeout = 120
keepalive = 5

# Logging
accesslog = "-" # Log to stdout
errorlog = "-"  # Log to stderr
loglevel = "info"

# Process management
name = "task_manager_api"
reload = False  # Set to True for development only
