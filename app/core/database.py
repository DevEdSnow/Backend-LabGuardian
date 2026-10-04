
"""
Database configuration for LabGuardian AI.

This module configures the SQLAlchemy engine,
session factory and declarative base used by
the application models.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


# ─────────────────────────────────────────────
# Database Engine
# ─────────────────────────────────────────────

engine = create_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_pre_ping=True,
)


# ─────────────────────────────────────────────
# Session Factory
# ─────────────────────────────────────────────

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autocommit=False,
    autoflush=False,
)


# ─────────────────────────────────────────────
# Declarative Base
# ─────────────────────────────────────────────

class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.
    """

    pass


# ─────────────────────────────────────────────
# Database Dependency
# ─────────────────────────────────────────────

def get_db() -> Generator[Session, None, None]:
    """
    Provides a database session for FastAPI endpoints.

    The session is automatically closed after
    the request finishes.

    Example:

        @router.get("/")
        def get_samples(
            db: Session = Depends(get_db),
        ):
            ...
    """

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# ─────────────────────────────────────────────
# Database Initialization
# ─────────────────────────────────────────────

def init_db() -> None:
    """
    Creates all registered database tables.

    This function should be called after importing
    the application models so SQLAlchemy knows
    which tables need to be created.

    For production environments, Alembic migrations
    should be used instead.
    """

    Base.metadata.create_all(
        bind=engine,
    )

