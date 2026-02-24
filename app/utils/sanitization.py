import re

def sanitize_string(v: str) -> str:
    if not isinstance(v, str):
        return v
    # 1. Strip HTML tags
    v = re.sub(r'<[^>]*>', '', v)
    # 2. Trim whitespace
    return v.strip()
