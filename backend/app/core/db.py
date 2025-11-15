"""
Database configuration and session management.

Uses synchronous SQLAlchemy with session_scope pattern for transaction management.
"""

from collections.abc import Generator
from contextlib import contextmanager

import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Database Engine Configuration
# =============================================================================


def get_engine_args() -> dict:
    """
    Get database engine arguments based on configuration.

    Returns:
        dict: Engine configuration arguments
    """
    args = {
        "pool_pre_ping": settings.db_pool_pre_ping,
        "future": True,  # SQLAlchemy 2.0 style
        "echo": settings.debug,
    }

    # SQLite doesn't support connection pools in the same way
    if settings.db_vendor == "sqlite":
        args["connect_args"] = {"check_same_thread": False}
        args["poolclass"] = NullPool
    else:
        args["pool_size"] = settings.db_pool_size
        args["max_overflow"] = settings.db_max_overflow
        args["pool_recycle"] = 3600  # Recycle connections after 1 hour

    return args


# Create the synchronous engine
engine = sa.create_engine(settings.database_url, **get_engine_args())

# Create session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True,  # SQLAlchemy 2.0 style
)


# =============================================================================
# Session Management
# =============================================================================


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """
    Provide a transactional scope for database operations.

    This context manager handles session lifecycle:
    - Creates a new session
    - Commits on successful completion
    - Rolls back on exception
    - Closes the session in all cases

    Yields:
        Session: SQLAlchemy database session

    Example:
        with session_scope() as session:
            user = session.query(User).filter_by(id=1).first()
            user.name = "New Name"
            # Commit happens automatically on successful exit
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
        logger.debug("Database transaction committed successfully")
    except Exception as e:
        session.rollback()
        logger.error(f"Database transaction failed, rolling back: {e}", exc_info=True)
        raise
    finally:
        session.close()
        logger.debug("Database session closed")


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database session injection.

    This function is used as a FastAPI dependency to provide
    database sessions to route handlers.

    Yields:
        Session: SQLAlchemy database session

    Example:
        @app.get("/users/{user_id}")
        def get_user(user_id: int, db: Session = Depends(get_db)):
            return db.query(User).filter_by(id=user_id).first()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# =============================================================================
# Database Initialization and Health Check
# =============================================================================


def init_db() -> None:
    """
    Initialize the database.

    This function can be called at application startup to ensure
    database connectivity and run any necessary initialization.
    """
    try:
        # Test database connection
        with engine.connect() as conn:
            conn.execute(sa.text("SELECT 1"))
        logger.info(f"Database connection established: {settings.db_vendor}")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}", exc_info=True)
        raise


def check_db_health() -> bool:
    """
    Check if the database is accessible and healthy.

    Returns:
        bool: True if database is healthy, False otherwise
    """
    try:
        with engine.connect() as conn:
            conn.execute(sa.text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


def close_db() -> None:
    """
    Close all database connections.

    This function should be called at application shutdown.
    """
    try:
        engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}", exc_info=True)


# =============================================================================
# Database Utilities
# =============================================================================


def get_db_info() -> dict:
    """
    Get information about the current database configuration.

    Returns:
        dict: Database configuration information
    """
    return {
        "vendor": settings.db_vendor,
        "url": settings.database_url.split("@")[-1] if "@" in settings.database_url else "sqlite",
        "pool_size": settings.db_pool_size,
        "max_overflow": settings.db_max_overflow,
    }


def execute_raw_sql(sql: str, params: dict | None = None) -> list:
    """
    Execute raw SQL query (use with caution).

    Args:
        sql: SQL query string
        params: Optional parameters for the query

    Returns:
        list: Query results

    Note:
        This should only be used for maintenance tasks or when ORM
        is not suitable. Always prefer using the ORM for regular operations.
    """
    with session_scope() as session:
        result = session.execute(sa.text(sql), params or {})
        return result.fetchall()
