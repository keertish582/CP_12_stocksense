from datetime import datetime, timezone
from sqlalchemy import DateTime
from sqlalchemy.orm import declarative_base

def utc_now():
    return datetime.now(timezone.utc)
