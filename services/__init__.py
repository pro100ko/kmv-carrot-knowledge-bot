"""Services package initialization."""

from .base import BaseService
from .user import UserService
from .test import TestService

# Export services
__all__ = [
    'BaseService',
    'UserService',
    'TestService'
]

# Global service instances
_user_service: UserService = None
_test_service: TestService = None

def get_user_service() -> UserService:
    """Get global user service instance.
    
    Returns:
        UserService: User service instance.
    """
    global _user_service
    if _user_service is None:
        _user_service = UserService()
    return _user_service

def get_test_service() -> TestService:
    """Get global test service instance.
    
    Returns:
        TestService: Test service instance.
    """
    global _test_service
    if _test_service is None:
        _test_service = TestService()
    return _test_service

def init_services() -> None:
    """Initialize global service instances."""
    global _user_service, _test_service
    _user_service = UserService()
    _test_service = TestService() 