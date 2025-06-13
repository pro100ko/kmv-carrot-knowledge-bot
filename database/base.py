"""Base database module."""

from typing import Any, Dict, List, Optional, TypeVar, Generic, Type
from abc import ABC, abstractmethod
import asyncio
from datetime import datetime
import logging
from pathlib import Path
import aiosqlite
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import MetaData, Table, Column, Integer, String, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.sql import select, update, delete
from sqlalchemy.exc import SQLAlchemyError

from config import get_config

# Type variables
T = TypeVar('T', bound='BaseModel')

class BaseModel(DeclarativeBase):
    """Base model class."""
    
    metadata = MetaData()
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

class DatabaseError(Exception):
    """Base database error."""
    pass

class DatabaseConnectionError(DatabaseError):
    """Database connection error."""
    pass

class DatabaseQueryError(DatabaseError):
    """Database query error."""
    pass

class BaseDatabase(ABC, Generic[T]):
    """Base database class with common functionality."""
    
    def __init__(self, model_class: Type[T]):
        """Initialize database with model class."""
        self.model_class = model_class
        self.config = get_config()
        self.logger = logging.getLogger(f"database.{model_class.__name__}")
        self._engine = None
        self._session_factory = None
    
    async def initialize(self) -> None:
        """Initialize database connection."""
        try:
            # Create async engine
            self._engine = create_async_engine(
                f"sqlite+aiosqlite:///{self.config.DB_FILE}",
                pool_size=self.config.DB_POOL_SIZE,
                pool_timeout=self.config.DB_POOL_TIMEOUT,
                pool_recycle=self.config.DB_POOL_RECYCLE,
                echo=self.config.is_development()
            )
            
            # Create session factory
            self._session_factory = async_sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Create tables
            async with self._engine.begin() as conn:
                await conn.run_sync(self.model_class.metadata.create_all)
            
            self.logger.info("Database initialized successfully")
        
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise DatabaseConnectionError(f"Failed to initialize database: {e}")
    
    async def close(self) -> None:
        """Close database connection."""
        if self._engine:
            await self._engine.dispose()
            self.logger.info("Database connection closed")
    
    async def get_session(self) -> AsyncSession:
        """Get database session."""
        if not self._session_factory:
            raise DatabaseConnectionError("Database not initialized")
        return self._session_factory()
    
    async def create(self, **kwargs: Any) -> T:
        """Create new record."""
        try:
            async with await self.get_session() as session:
                instance = self.model_class(**kwargs)
                session.add(instance)
                await session.commit()
                await session.refresh(instance)
                return instance
        
        except SQLAlchemyError as e:
            self.logger.error(f"Create operation failed: {e}")
            raise DatabaseQueryError(f"Failed to create record: {e}")
    
    async def get(self, id: int) -> Optional[T]:
        """Get record by ID."""
        try:
            async with await self.get_session() as session:
                stmt = select(self.model_class).where(
                    self.model_class.id == id,
                    self.model_class.is_deleted == False
                )
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
        
        except SQLAlchemyError as e:
            self.logger.error(f"Get operation failed: {e}")
            raise DatabaseQueryError(f"Failed to get record: {e}")
    
    async def update(self, id: int, **kwargs: Any) -> Optional[T]:
        """Update record."""
        try:
            async with await self.get_session() as session:
                stmt = update(self.model_class).where(
                    self.model_class.id == id,
                    self.model_class.is_deleted == False
                ).values(**kwargs).execution_options(synchronize_session="fetch")
                
                result = await session.execute(stmt)
                await session.commit()
                
                if result.rowcount > 0:
                    return await self.get(id)
                return None
        
        except SQLAlchemyError as e:
            self.logger.error(f"Update operation failed: {e}")
            raise DatabaseQueryError(f"Failed to update record: {e}")
    
    async def delete(self, id: int, hard: bool = False) -> bool:
        """Delete record (soft or hard delete)."""
        try:
            async with await self.get_session() as session:
                if hard:
                    stmt = delete(self.model_class).where(self.model_class.id == id)
                else:
                    stmt = update(self.model_class).where(
                        self.model_class.id == id,
                        self.model_class.is_deleted == False
                    ).values(is_deleted=True)
                
                result = await session.execute(stmt)
                await session.commit()
                return result.rowcount > 0
        
        except SQLAlchemyError as e:
            self.logger.error(f"Delete operation failed: {e}")
            raise DatabaseQueryError(f"Failed to delete record: {e}")
    
    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        **filters: Any
    ) -> List[T]:
        """List records with optional filtering."""
        try:
            async with await self.get_session() as session:
                stmt = select(self.model_class).where(
                    self.model_class.is_deleted == False
                )
                
                # Apply filters
                for key, value in filters.items():
                    if hasattr(self.model_class, key):
                        stmt = stmt.where(getattr(self.model_class, key) == value)
                
                # Apply pagination
                stmt = stmt.offset(skip).limit(limit)
                
                result = await session.execute(stmt)
                return list(result.scalars().all())
        
        except SQLAlchemyError as e:
            self.logger.error(f"List operation failed: {e}")
            raise DatabaseQueryError(f"Failed to list records: {e}")
    
    async def count(self, **filters: Any) -> int:
        """Count records with optional filtering."""
        try:
            async with await self.get_session() as session:
                stmt = select(self.model_class).where(
                    self.model_class.is_deleted == False
                )
                
                # Apply filters
                for key, value in filters.items():
                    if hasattr(self.model_class, key):
                        stmt = stmt.where(getattr(self.model_class, key) == value)
                
                result = await session.execute(stmt)
                return len(list(result.scalars().all()))
        
        except SQLAlchemyError as e:
            self.logger.error(f"Count operation failed: {e}")
            raise DatabaseQueryError(f"Failed to count records: {e}")
    
    @abstractmethod
    async def create_indexes(self) -> None:
        """Create database indexes."""
        pass 