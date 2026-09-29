import time
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


def create_db_engine(retries: int = 10, delay: int = 3):
    """Create engine with retry logic for container startup timing."""
    for attempt in range(1, retries + 1):
        try:
            engine = create_engine(
                settings.database_url,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
            )
            # Test the connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection established.")
            return engine
        except Exception as e:
            logger.warning(f"DB not ready (attempt {attempt}/{retries}): {e}")
            if attempt == retries:
                raise RuntimeError("Could not connect to the database after multiple retries.") from e
            time.sleep(delay)


engine = create_db_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency that provides a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
