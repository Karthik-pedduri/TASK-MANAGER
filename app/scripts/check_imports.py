
import sys
with open("imports.log", "w") as f:
    try:
        import fastapi
        f.write("fastapi: OK\n")
    except ImportError:
        f.write("fastapi: MISSING\n")

    try:
        import sqlalchemy
        f.write("sqlalchemy: OK\n")
    except ImportError:
        f.write("sqlalchemy: MISSING\n")
        
    try:
        import pandas
        f.write("pandas: OK\n")
    except ImportError:
        f.write("pandas: MISSING\n")

    try:
        import httpx
        f.write("httpx: OK\n")
    except ImportError:
        f.write("httpx: MISSING\n")
        
    try:
        import requests
        f.write("requests: OK\n")
    except ImportError:
        f.write("requests: MISSING\n")
