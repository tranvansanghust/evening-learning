"""
Database configuration and session management.

Provides SQLAlchemy engine, session factory, and base model for ORM models.
Uses configuration from app.config to establish database connections.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
from typing import Generator

from app.config import settings


# Create SQLAlchemy engine with connection pooling
engine = create_engine(
    settings.get_database_url(),
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before using
    echo=settings.debug,  # Log SQL queries in debug mode
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Base class for all ORM models
Base = declarative_base()


def get_db() -> Generator:
    """
    Dependency for FastAPI to inject database sessions.

    Yields:
        Session: SQLAlchemy database session

    Ensures proper session cleanup after request completion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
