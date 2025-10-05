"""
Database configuration and session management.
"""
import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    database_url: str = "sqlite:///./data/birds.db"
    echo: bool = False
    
    model_config = ConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"  # Ignore extra environment variables
    )


# Global settings
db_settings = DatabaseSettings()

# Create engine
if db_settings.database_url.startswith("sqlite"):
    # SQLite configuration with thread safety
    engine = create_engine(
        db_settings.database_url,
        echo=db_settings.echo,
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
        },
    )
else:
    # PostgreSQL configuration
    engine = create_engine(
        db_settings.database_url,
        echo=db_settings.echo,
    )

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine
)

# Create declarative base
Base = declarative_base()

# Metadata for Alembic migrations
metadata = MetaData()


def get_db():
    """Get database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)