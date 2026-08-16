import uuid
from datetime import datetime

def generate_id():
    return str(uuid.uuid4())

def current_timestamp():
    return datetime.utcnow().isoformat()
