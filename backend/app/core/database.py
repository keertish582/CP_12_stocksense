import os
import logging
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

logger = logging.getLogger("stocksense.db")

DATABASE_URL = os.getenv("DATABASE_URL", settings.DATABASE_URL)

def get_engine(url: str):
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        engine = create_engine(url, connect_args=connect_args)
        
        # Enable SQLite foreign key constraints and WAL mode
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()
        return engine
    else:
        return create_engine(url, pool_pre_ping=True, pool_size=10, max_overflow=20)

# Attempt to connect to configured DB, or fallback to SQLite if PostgreSQL is unreachable in local dev
try:
    engine = get_engine(DATABASE_URL)
    # Quick connectivity test
    with engine.connect() as conn:
        pass
except Exception as e:
    if settings.USE_SQLITE_FALLBACK:
        logger.warning(
            f"Could not connect to {DATABASE_URL}: {e}. Falling back to SQLite {settings.FALLBACK_SQLITE_URL} for local development."
        )
        DATABASE_URL = settings.FALLBACK_SQLITE_URL
        engine = get_engine(DATABASE_URL)
    else:
        raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
