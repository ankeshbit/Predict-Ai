"""
Database connection and session factory for Neon PostgreSQL
"""

import logging
import time
from typing import Generator

from app.core.config import settings
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


# Connect arguments for Neon PgBouncer transaction pooling mode:
# - prepare_threshold=None: disables psycopg prepared statements
connect_args = {
    "prepare_threshold": None,
    "connect_timeout": settings.DB_CONNECT_TIMEOUT,
}

# Add sslmode if not local test DB
local_hosts = ("localhost", "127.0.0.1", "test-postgres", "postgres", "predict_ai_test_postgres")
if not any(h in settings.DATABASE_URL for h in local_hosts):
    connect_args["sslmode"] = "require"

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,      # handles Neon scale-to-zero wakeups
    pool_size=5,             # modest pool size for serverless
    max_overflow=10,
    pool_recycle=300,        # recycle connections every 5 minutes
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding a database session with retry-with-backoff for cold starts.
    """
    max_retries = 3
    retry_delay = 0.5
    session: Session = None

    for attempt in range(max_retries):
        try:
            session = SessionLocal()
            # Perform a lightweight ping to verify connection
            session.execute(text("SELECT 1"))
            break
        except OperationalError as e:
            if session:
                session.close()
            if attempt == max_retries - 1:
                logger.error(f"Database connection failed after {max_retries} attempts: {e}")
                raise
            logger.warning(f"Database cold start retry {attempt + 1}/{max_retries} in {retry_delay}s...")
            time.sleep(retry_delay)
            retry_delay *= 2

    try:
        yield session
    finally:
        if session:
            session.close()
