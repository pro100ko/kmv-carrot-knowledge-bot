"""Resource management utilities for the bot"""

import atexit
import signal
import sys
import logging
import asyncio
from typing import List, Callable, Any, Dict, Optional
from functools import wraps
import time
import psutil
import os

# Configure logging
logger = logging.getLogger(__name__)

class ResourceManager:
    """Manages application resources and cleanup"""
    
    def __init__(self):
        """Initialize resource manager"""
        self._cleanup_handlers: List[Callable[[], None]] = []
        self._start_time = time.time()
        self._memory_limit = int(os.getenv("MAX_MEMORY_USAGE", "512")) * 1024 * 1024  # Convert MB to bytes
        self._memory_warning_threshold = 0.8  # 80% of limit
        self._monitoring_task: Optional[asyncio.Task] = None
        
        # Register cleanup handlers
        # atexit.register(self.cleanup) # Removed due to incompatibility with async cleanup
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
    
    async def initialize(self) -> None:
        """Initialize resource manager asynchronously.
        
        This method should be called after the event loop is running.
        """
        if self._monitoring_task is None:
            self._start_memory_monitoring()
            logger.info("Resource manager initialized")
    
    def register_cleanup(self, handler: Callable[[], None]) -> None:
        """Register a cleanup handler"""
        self._cleanup_handlers.append(handler)
    
    async def cleanup(self) -> None:
        """Execute all cleanup handlers in reverse order"""
        logger.info("Starting cleanup...")
        
        # Cancel monitoring task if running
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
        
        # Execute cleanup handlers
        for handler in reversed(self._cleanup_handlers):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler()
                else:
                    handler()
            except Exception as e:
                logger.error(f"Cleanup error in {handler.__name__}: {e}")
        
        logger.info("Cleanup completed")
    
    def _handle_signal(self, signum: int, frame: Any) -> None:
        """Handle termination signals"""
        logger.info(f"Received signal {signum}, starting cleanup...")
        # Create event loop if needed and run cleanup
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        try:
            # Run cleanup in the event loop
            if loop.is_running():
                # If loop is running, create a task
                loop.create_task(self.cleanup())
            else:
                # If loop is not running, run until complete
                loop.run_until_complete(self.cleanup())
        finally:
            if not loop.is_running():
                loop.close()
        sys.exit(0)
    
    def _start_memory_monitoring(self) -> None:
        """Start periodic memory monitoring"""
        async def monitor_memory():
            while True:
                try:
                    process = psutil.Process()
                    memory_info = process.memory_info()
                    memory_usage = memory_info.rss  # Resident Set Size
                    
                    if memory_usage > self._memory_limit:
                        logger.error(
                            f"Memory limit exceeded: {memory_usage / 1024 / 1024:.1f}MB "
                            f"(limit: {self._memory_limit / 1024 / 1024:.1f}MB)"
                        )
                        # Trigger cleanup
                        self.cleanup()
                    elif memory_usage > self._memory_limit * self._memory_warning_threshold:
                        logger.warning(
                            f"Memory usage high: {memory_usage / 1024 / 1024:.1f}MB "
                            f"(limit: {self._memory_limit / 1024 / 1024:.1f}MB)"
                        )
                    
                    # Log uptime
                    uptime = time.time() - self._start_time
                    if uptime % 3600 < 60:  # Log every hour
                        logger.info(
                            f"Bot uptime: {uptime / 3600:.1f}h, "
                            f"Memory usage: {memory_usage / 1024 / 1024:.1f}MB"
                        )
                    
                except Exception as e:
                    logger.error(f"Error in memory monitoring: {e}")
                
                await asyncio.sleep(60)  # Check every minute
        
        # Start monitoring in background
        self._monitoring_task = asyncio.create_task(monitor_memory())
        logger.info("Memory monitoring started")

def log_execution_time(logger: logging.Logger) -> Callable:
    """Decorator to log function execution time"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Log slow operations
                if execution_time > 1.0:
                    logger.warning(
                        f"Slow operation: {func.__name__} took {execution_time:.2f}s",
                        extra={
                            "function": func.__name__,
                            "execution_time": execution_time,
                            "args": str(args),
                            "kwargs": str(kwargs)
                        }
                    )
                return result
            except Exception as e:
                logger.error(
                    f"Error in {func.__name__}: {str(e)}",
                    exc_info=True,
                    extra={
                        "function": func.__name__,
                        "args": str(args),
                        "kwargs": str(kwargs)
                    }
                )
                raise
        return wrapper
    return decorator

# Create singleton instance
resource_manager = ResourceManager() 