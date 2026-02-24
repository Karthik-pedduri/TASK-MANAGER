
import sys
# flushing stdout to ensure we see output
def p(msg):
    print(msg)
    sys.stdout.flush()

p("Starting debug...")
try:
    p("Importing app.database...")
    import app.database
    p("Success.")
    
    p("Importing app.routers.users...")
    import app.routers.users
    p("Success.")
    
    p("Importing app.routers.tasks...")
    import app.routers.tasks
    p("Success.")
    
    p("Importing app.routers.analysis...")
    import app.routers.analysis
    p("Success.")
    
    p("Importing app.services.scheduler...")
    import app.services.scheduler
    p("Success.")
    
    p("Importing app.main...")
    import app.main
    p("Success.")
except Exception:
    import traceback
    traceback.print_exc()
