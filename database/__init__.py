"""Database package initialization."""

from typing import Type
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from contextlib import contextmanager

from .base import BaseDatabase, BaseModel, DatabaseError
from .models import (
    User,
    Test,
    Question,
    Option,
    Product,
    Category,
    TestResult,
    UserActivity
)

# Create declarative base
Base = declarative_base()

# Export commonly used types and classes
__all__ = [
    'Base',
    'BaseDatabase',
    'BaseModel',
    'DatabaseError',
    'User',
    'Test',
    'Question',
    'Option',
    'Product',
    'Category',
    'TestResult',
    'UserActivity',
    'get_database',
    'init_database'
]

# Global database instance
_db: BaseDatabase = None

def get_database() -> BaseDatabase:
    """Get the global database instance.
    
    Returns:
        BaseDatabase: The database instance.
        
    Raises:
        DatabaseError: If database is not initialized.
    """
    if _db is None:
        raise DatabaseError("Database not initialized")
    return _db

def init_database(
    db_url: str,
    pool_size: int = 5,
    max_overflow: int = 10,
    pool_timeout: int = 30,
    pool_recycle: int = 3600
) -> BaseDatabase:
    """Initialize the database connection.
    
    Args:
        db_url: Database URL.
        pool_size: Size of the connection pool.
        max_overflow: Maximum number of connections that can be created beyond pool_size.
        pool_timeout: Timeout for getting a connection from the pool.
        pool_recycle: Number of seconds after which a connection is automatically recycled.
        
    Returns:
        BaseDatabase: The initialized database instance.
        
    Raises:
        DatabaseError: If database initialization fails.
    """
    global _db
    
    try:
        # Create engine
        engine = create_engine(
            db_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            echo=False
        )
        
        # Create session factory
        session_factory = sessionmaker(
            bind=engine,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )
        
        # Create database instance
        _db = BaseDatabase(engine, session_factory)
        
        # Create tables
        Base.metadata.create_all(engine)
        
        return _db
        
    except Exception as e:
        raise DatabaseError(f"Failed to initialize database: {str(e)}")

@contextmanager
def get_session() -> Session:
    """Get a database session.
    
    Yields:
        Session: Database session.
        
    Raises:
        DatabaseError: If database is not initialized.
    """
    db = get_database()
    session = db.get_session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise DatabaseError(f"Database session error: {str(e)}")
    finally:
        session.close() 