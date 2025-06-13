"""Base service class."""

from typing import TypeVar, Generic, Type, Optional, List, Dict, Any
from datetime import datetime
from contextlib import contextmanager

from database import get_session, DatabaseError
from database.repositories import BaseRepository

T = TypeVar('T')

class BaseService(Generic[T]):
    """Base service class."""
    
    def __init__(self, repository: BaseRepository[T]):
        """Initialize service.
        
        Args:
            repository: Repository instance.
        """
        self.repository = repository
    
    @contextmanager
    def _get_session(self):
        """Get database session.
        
        Yields:
            Session: Database session.
        """
        with get_session() as session:
            yield session
    
    def create(self, **kwargs) -> T:
        """Create a new record.
        
        Args:
            **kwargs: Model attributes.
            
        Returns:
            T: Created model instance.
            
        Raises:
            DatabaseError: If creation fails.
        """
        with self._get_session() as session:
            return self.repository.create(session, **kwargs)
    
    def get(self, id: int) -> Optional[T]:
        """Get record by ID.
        
        Args:
            id: Record ID.
            
        Returns:
            Optional[T]: Model instance or None if not found.
            
        Raises:
            DatabaseError: If query fails.
        """
        with self._get_session() as session:
            return self.repository.get(session, id)
    
    def update(self, id: int, **kwargs) -> Optional[T]:
        """Update record.
        
        Args:
            id: Record ID.
            **kwargs: Model attributes to update.
            
        Returns:
            Optional[T]: Updated model instance or None if not found.
            
        Raises:
            DatabaseError: If update fails.
        """
        with self._get_session() as session:
            return self.repository.update(session, id, **kwargs)
    
    def delete(self, id: int) -> bool:
        """Soft delete record.
        
        Args:
            id: Record ID.
            
        Returns:
            bool: True if deleted, False if not found.
            
        Raises:
            DatabaseError: If deletion fails.
        """
        with self._get_session() as session:
            return self.repository.delete(session, id)
    
    def list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        **filters
    ) -> List[T]:
        """List records with filtering.
        
        Args:
            skip: Number of records to skip.
            limit: Maximum number of records to return.
            **filters: Filter conditions.
            
        Returns:
            List[T]: List of model instances.
            
        Raises:
            DatabaseError: If query fails.
        """
        with self._get_session() as session:
            return self.repository.list(
                session,
                skip=skip,
                limit=limit,
                **filters
            )
    
    def count(self, **filters) -> int:
        """Count records with filtering.
        
        Args:
            **filters: Filter conditions.
            
        Returns:
            int: Number of records.
            
        Raises:
            DatabaseError: If query fails.
        """
        with self._get_session() as session:
            return self.repository.count(session, **filters)
    
    def exists(self, **filters) -> bool:
        """Check if record exists.
        
        Args:
            **filters: Filter conditions.
            
        Returns:
            bool: True if record exists, False otherwise.
            
        Raises:
            DatabaseError: If query fails.
        """
        return self.count(**filters) > 0
    
    def get_or_create(
        self,
        *,
        defaults: Optional[Dict[str, Any]] = None,
        **filters
    ) -> tuple[T, bool]:
        """Get existing record or create new one.
        
        Args:
            defaults: Default values for new record.
            **filters: Filter conditions.
            
        Returns:
            tuple[T, bool]: (Model instance, created flag)
            
        Raises:
            DatabaseError: If operation fails.
        """
        with self._get_session() as session:
            instance = self.repository.list(
                session,
                limit=1,
                **filters
            )
            
            if instance:
                return instance[0], False
            
            if defaults is None:
                defaults = {}
            
            instance = self.repository.create(
                session,
                **{**filters, **defaults}
            )
            
            return instance, True
    
    def update_or_create(
        self,
        *,
        defaults: Optional[Dict[str, Any]] = None,
        **filters
    ) -> tuple[T, bool]:
        """Update existing record or create new one.
        
        Args:
            defaults: Default values for new record.
            **filters: Filter conditions.
            
        Returns:
            tuple[T, bool]: (Model instance, created flag)
            
        Raises:
            DatabaseError: If operation fails.
        """
        with self._get_session() as session:
            instance = self.repository.list(
                session,
                limit=1,
                **filters
            )
            
            if instance:
                if defaults:
                    instance = self.repository.update(
                        session,
                        instance[0].id,
                        **defaults
                    )
                return instance, False
            
            if defaults is None:
                defaults = {}
            
            instance = self.repository.create(
                session,
                **{**filters, **defaults}
            )
            
            return instance, True 