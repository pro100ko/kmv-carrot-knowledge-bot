"""User service."""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from database import DatabaseError
from database.models import User
from database.repositories import UserRepository, UserActivityRepository
from .base import BaseService

class UserService(BaseService[User]):
    """User service."""
    
    def __init__(self):
        """Initialize service."""
        super().__init__(UserRepository())
        self.activity_repo = UserActivityRepository()
    
    def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID.
        
        Args:
            telegram_id: Telegram user ID.
            
        Returns:
            Optional[User]: User instance or None if not found.
            
        Raises:
            DatabaseError: If query fails.
        """
        with self._get_session() as session:
            return self.repository.get_by_telegram_id(session, telegram_id)
    
    def register_user(
        self,
        telegram_id: int,
        *,
        username: Optional[str] = None,
        first_name: str,
        last_name: Optional[str] = None,
        is_admin: bool = False
    ) -> User:
        """Register new user.
        
        Args:
            telegram_id: Telegram user ID.
            username: Optional username.
            first_name: First name.
            last_name: Optional last name.
            is_admin: Whether user is admin.
            
        Returns:
            User: Created user instance.
            
        Raises:
            DatabaseError: If registration fails.
        """
        with self._get_session() as session:
            # Check if user exists
            user = self.repository.get_by_telegram_id(session, telegram_id)
            if user:
                # Update user info
                user = self.repository.update(
                    session,
                    user.id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    is_admin=is_admin,
                    is_blocked=False
                )
            else:
                # Create new user
                user = self.repository.create(
                    session,
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    is_admin=is_admin,
                    is_blocked=False
                )
            
            # Log activity
            self.activity_repo.log_activity(
                session,
                user.id,
                "register",
                details=f"User registered: {username or telegram_id}"
            )
            
            return user
    
    def update_user_info(
        self,
        user_id: int,
        *,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> Optional[User]:
        """Update user information.
        
        Args:
            user_id: User ID.
            username: Optional username.
            first_name: Optional first name.
            last_name: Optional last name.
            
        Returns:
            Optional[User]: Updated user instance or None if not found.
            
        Raises:
            DatabaseError: If update fails.
        """
        with self._get_session() as session:
            # Get user
            user = self.repository.get(session, user_id)
            if not user:
                return None
            
            # Update user info
            updates = {}
            if username is not None:
                updates["username"] = username
            if first_name is not None:
                updates["first_name"] = first_name
            if last_name is not None:
                updates["last_name"] = last_name
            
            if updates:
                user = self.repository.update(session, user_id, **updates)
                
                # Log activity
                self.activity_repo.log_activity(
                    session,
                    user_id,
                    "update_info",
                    details=f"User info updated: {updates}"
                )
            
            return user
    
    def block_user(
        self,
        user_id: int,
        *,
        reason: Optional[str] = None
    ) -> Optional[User]:
        """Block user.
        
        Args:
            user_id: User ID.
            reason: Optional block reason.
            
        Returns:
            Optional[User]: Updated user instance or None if not found.
            
        Raises:
            DatabaseError: If update fails.
        """
        with self._get_session() as session:
            # Get user
            user = self.repository.get(session, user_id)
            if not user:
                return None
            
            # Block user
            user = self.repository.update(
                session,
                user_id,
                is_blocked=True
            )
            
            # Log activity
            self.activity_repo.log_activity(
                session,
                user_id,
                "block",
                details=f"User blocked: {reason or 'No reason provided'}"
            )
            
            return user
    
    def unblock_user(
        self,
        user_id: int,
        *,
        reason: Optional[str] = None
    ) -> Optional[User]:
        """Unblock user.
        
        Args:
            user_id: User ID.
            reason: Optional unblock reason.
            
        Returns:
            Optional[User]: Updated user instance or None if not found.
            
        Raises:
            DatabaseError: If update fails.
        """
        with self._get_session() as session:
            # Get user
            user = self.repository.get(session, user_id)
            if not user:
                return None
            
            # Unblock user
            user = self.repository.update(
                session,
                user_id,
                is_blocked=False
            )
            
            # Log activity
            self.activity_repo.log_activity(
                session,
                user_id,
                "unblock",
                details=f"User unblocked: {reason or 'No reason provided'}"
            )
            
            return user
    
    def get_active_users(
        self,
        *,
        days: int = 30,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """Get active users.
        
        Args:
            days: Number of days to look back.
            skip: Number of records to skip.
            limit: Maximum number of records to return.
            
        Returns:
            List[User]: List of active users.
            
        Raises:
            DatabaseError: If query fails.
        """
        with self._get_session() as session:
            # Calculate cutoff date
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            # Get active users
            query = select(User).where(
                User.last_activity >= cutoff,
                User.is_blocked == False,
                User.is_deleted == False
            ).order_by(User.last_activity.desc())
            
            return list(session.scalars(query.offset(skip).limit(limit)))
    
    def get_inactive_users(
        self,
        *,
        days: int = 30,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """Get inactive users.
        
        Args:
            days: Number of days to look back.
            skip: Number of records to skip.
            limit: Maximum number of records to return.
            
        Returns:
            List[User]: List of inactive users.
            
        Raises:
            DatabaseError: If query fails.
        """
        with self._get_session() as session:
            # Calculate cutoff date
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            # Get inactive users
            query = select(User).where(
                User.last_activity < cutoff,
                User.is_blocked == False,
                User.is_deleted == False
            ).order_by(User.last_activity.asc())
            
            return list(session.scalars(query.offset(skip).limit(limit)))
    
    def get_user_activity(
        self,
        user_id: int,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get user activity history.
        
        Args:
            user_id: User ID.
            skip: Number of records to skip.
            limit: Maximum number of records to return.
            
        Returns:
            List[Dict[str, Any]]: List of activity records.
            
        Raises:
            DatabaseError: If query fails.
        """
        with self._get_session() as session:
            # Get activity records
            activities = self.activity_repo.get_user_activities(
                session,
                user_id,
                skip=skip,
                limit=limit
            )
            
            # Convert to dict
            return [
                {
                    "id": activity.id,
                    "action": activity.action,
                    "details": activity.details,
                    "created_at": activity.created_at.isoformat(),
                    "ip_address": activity.ip_address,
                    "user_agent": activity.user_agent
                }
                for activity in activities
            ]
    
    def update_last_activity(self, user_id: int) -> None:
        """Update user's last activity timestamp.
        
        Args:
            user_id: User ID.
            
        Raises:
            DatabaseError: If update fails.
        """
        with self._get_session() as session:
            self.repository.update_last_activity(session, user_id)
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user statistics.
        
        Args:
            user_id: User ID.
            
        Returns:
            Dict[str, Any]: User statistics.
            
        Raises:
            DatabaseError: If query fails.
        """
        with self._get_session() as session:
            # Get user
            user = self.repository.get(session, user_id)
            if not user:
                return {}
            
            # Get activity count
            activity_count = self.activity_repo.count(
                session,
                user_id=user_id
            )
            
            # Get last activity
            last_activity = self.activity_repo.get_user_activities(
                session,
                user_id,
                limit=1
            )
            
            return {
                "id": user.id,
                "telegram_id": user.telegram_id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_admin": user.is_admin,
                "is_blocked": user.is_blocked,
                "created_at": user.created_at.isoformat(),
                "last_activity": user.last_activity.isoformat(),
                "activity_count": activity_count,
                "last_action": last_activity[0].action if last_activity else None,
                "last_action_time": last_activity[0].created_at.isoformat() if last_activity else None
            } 