"""Database repositories."""

from typing import List, Optional, Type, TypeVar, Generic, Dict, Any
from datetime import datetime
from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .base import BaseModel, DatabaseError
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

T = TypeVar('T', bound=BaseModel)

class BaseRepository(Generic[T]):
    """Base repository class."""
    
    def __init__(self, model: Type[T]):
        """Initialize repository.
        
        Args:
            model: SQLAlchemy model class.
        """
        self.model = model
    
    def create(self, session: Session, **kwargs) -> T:
        """Create a new record.
        
        Args:
            session: Database session.
            **kwargs: Model attributes.
            
        Returns:
            T: Created model instance.
            
        Raises:
            DatabaseError: If creation fails.
        """
        try:
            instance = self.model(**kwargs)
            session.add(instance)
            session.flush()
            return instance
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to create {self.model.__name__}: {str(e)}")
    
    def get(self, session: Session, id: int) -> Optional[T]:
        """Get record by ID.
        
        Args:
            session: Database session.
            id: Record ID.
            
        Returns:
            Optional[T]: Model instance or None if not found.
            
        Raises:
            DatabaseError: If query fails.
        """
        try:
            return session.get(self.model, id)
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get {self.model.__name__}: {str(e)}")
    
    def update(self, session: Session, id: int, **kwargs) -> Optional[T]:
        """Update record.
        
        Args:
            session: Database session.
            id: Record ID.
            **kwargs: Model attributes to update.
            
        Returns:
            Optional[T]: Updated model instance or None if not found.
            
        Raises:
            DatabaseError: If update fails.
        """
        try:
            instance = self.get(session, id)
            if instance:
                for key, value in kwargs.items():
                    setattr(instance, key, value)
                instance.updated_at = datetime.utcnow()
                session.flush()
            return instance
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to update {self.model.__name__}: {str(e)}")
    
    def delete(self, session: Session, id: int) -> bool:
        """Soft delete record.
        
        Args:
            session: Database session.
            id: Record ID.
            
        Returns:
            bool: True if deleted, False if not found.
            
        Raises:
            DatabaseError: If deletion fails.
        """
        try:
            instance = self.get(session, id)
            if instance:
                instance.is_deleted = True
                instance.updated_at = datetime.utcnow()
                session.flush()
                return True
            return False
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to delete {self.model.__name__}: {str(e)}")
    
    def list(
        self,
        session: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        **filters
    ) -> List[T]:
        """List records with filtering.
        
        Args:
            session: Database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.
            **filters: Filter conditions.
            
        Returns:
            List[T]: List of model instances.
            
        Raises:
            DatabaseError: If query fails.
        """
        try:
            query = select(self.model).where(self.model.is_deleted == False)
            
            # Apply filters
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
            
            return list(session.scalars(query.offset(skip).limit(limit)))
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to list {self.model.__name__}: {str(e)}")
    
    def count(self, session: Session, **filters) -> int:
        """Count records with filtering.
        
        Args:
            session: Database session.
            **filters: Filter conditions.
            
        Returns:
            int: Number of records.
            
        Raises:
            DatabaseError: If query fails.
        """
        try:
            query = select(self.model).where(self.model.is_deleted == False)
            
            # Apply filters
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
            
            return session.scalar(query.with_only_columns([func.count()]))
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to count {self.model.__name__}: {str(e)}")

class UserRepository(BaseRepository[User]):
    """User repository."""
    
    def __init__(self):
        super().__init__(User)
    
    def get_by_telegram_id(self, session: Session, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID.
        
        Args:
            session: Database session.
            telegram_id: Telegram user ID.
            
        Returns:
            Optional[User]: User instance or None if not found.
        """
        try:
            query = select(User).where(
                User.telegram_id == telegram_id,
                User.is_deleted == False
            )
            return session.scalar(query)
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get user by telegram_id: {str(e)}")
    
    def update_last_activity(self, session: Session, user_id: int) -> None:
        """Update user's last activity timestamp.
        
        Args:
            session: Database session.
            user_id: User ID.
        """
        try:
            stmt = update(User).where(
                User.id == user_id,
                User.is_deleted == False
            ).values(
                last_activity=datetime.utcnow()
            )
            session.execute(stmt)
            session.flush()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to update user activity: {str(e)}")

class TestRepository(BaseRepository[Test]):
    """Test repository."""
    
    def __init__(self):
        super().__init__(Test)
    
    def get_active_tests(self, session: Session, user_id: int) -> List[Test]:
        """Get active tests for user.
        
        Args:
            session: Database session.
            user_id: User ID.
            
        Returns:
            List[Test]: List of active tests.
        """
        try:
            query = select(Test).where(
                Test.user_id == user_id,
                Test.is_active == True,
                Test.is_deleted == False
            )
            return list(session.scalars(query))
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get active tests: {str(e)}")

class TestResultRepository(BaseRepository[TestResult]):
    """Test result repository."""
    
    def __init__(self):
        super().__init__(TestResult)
    
    def get_user_results(
        self,
        session: Session,
        user_id: int,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[TestResult]:
        """Get user's test results.
        
        Args:
            session: Database session.
            user_id: User ID.
            skip: Number of records to skip.
            limit: Maximum number of records to return.
            
        Returns:
            List[TestResult]: List of test results.
        """
        try:
            query = select(TestResult).where(
                TestResult.user_id == user_id,
                TestResult.is_deleted == False
            ).order_by(TestResult.created_at.desc())
            
            return list(session.scalars(query.offset(skip).limit(limit)))
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get user results: {str(e)}")

class ProductRepository(BaseRepository[Product]):
    """Product repository."""
    
    def __init__(self):
        super().__init__(Product)
    
    def get_active_products(
        self,
        session: Session,
        category_id: Optional[int] = None,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[Product]:
        """Get active products.
        
        Args:
            session: Database session.
            category_id: Optional category ID to filter by.
            skip: Number of records to skip.
            limit: Maximum number of records to return.
            
        Returns:
            List[Product]: List of active products.
        """
        try:
            query = select(Product).where(
                Product.is_active == True,
                Product.is_deleted == False
            )
            
            if category_id is not None:
                query = query.where(Product.category_id == category_id)
            
            return list(session.scalars(query.offset(skip).limit(limit)))
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get active products: {str(e)}")

class CategoryRepository(BaseRepository[Category]):
    """Category repository."""
    
    def __init__(self):
        super().__init__(Category)
    
    def get_root_categories(self, session: Session) -> List[Category]:
        """Get root categories (without parent).
        
        Args:
            session: Database session.
            
        Returns:
            List[Category]: List of root categories.
        """
        try:
            query = select(Category).where(
                Category.parent_id == None,
                Category.is_active == True,
                Category.is_deleted == False
            )
            return list(session.scalars(query))
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get root categories: {str(e)}")
    
    def get_subcategories(
        self,
        session: Session,
        parent_id: int
    ) -> List[Category]:
        """Get subcategories of a category.
        
        Args:
            session: Database session.
            parent_id: Parent category ID.
            
        Returns:
            List[Category]: List of subcategories.
        """
        try:
            query = select(Category).where(
                Category.parent_id == parent_id,
                Category.is_active == True,
                Category.is_deleted == False
            )
            return list(session.scalars(query))
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get subcategories: {str(e)}")

class UserActivityRepository(BaseRepository[UserActivity]):
    """User activity repository."""
    
    def __init__(self):
        super().__init__(UserActivity)
    
    def log_activity(
        self,
        session: Session,
        user_id: int,
        action: str,
        *,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UserActivity:
        """Log user activity.
        
        Args:
            session: Database session.
            user_id: User ID.
            action: Action name.
            details: Optional action details.
            ip_address: Optional IP address.
            user_agent: Optional User-Agent string.
            
        Returns:
            UserActivity: Created activity record.
        """
        try:
            return self.create(
                session,
                user_id=user_id,
                action=action,
                details=details,
                ip_address=ip_address,
                user_agent=user_agent
            )
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to log user activity: {str(e)}")
    
    def get_user_activities(
        self,
        session: Session,
        user_id: int,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[UserActivity]:
        """Get user's activity history.
        
        Args:
            session: Database session.
            user_id: User ID.
            skip: Number of records to skip.
            limit: Maximum number of records to return.
            
        Returns:
            List[UserActivity]: List of activity records.
        """
        try:
            query = select(UserActivity).where(
                UserActivity.user_id == user_id,
                UserActivity.is_deleted == False
            ).order_by(UserActivity.created_at.desc())
            
            return list(session.scalars(query.offset(skip).limit(limit)))
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get user activities: {str(e)}")

# Export repositories
__all__ = [
    'BaseRepository',
    'UserRepository',
    'TestRepository',
    'TestResultRepository',
    'ProductRepository',
    'CategoryRepository',
    'UserActivityRepository'
] 