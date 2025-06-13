"""Metrics collection and monitoring."""

import time
import logging
import psutil
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
from dataclasses import dataclass, field
from config import get_config

logger = logging.getLogger(__name__)

@dataclass
class OperationMetrics:
    """Metrics for a specific operation."""
    count: int = 0
    total_time: float = 0.0
    errors: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    min_time: float = float('inf')
    max_time: float = 0.0
    avg_time: float = 0.0

@dataclass
class HandlerMetrics:
    """Metrics for message handlers."""
    message_count: int = 0
    callback_count: int = 0
    error_count: int = 0
    operations: Dict[str, OperationMetrics] = field(default_factory=dict)

class MetricsCollector:
    """Collects and manages application metrics."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.config = get_config()
        self._start_time = datetime.now()
        self._message_count = 0
        self._callback_count = 0
        self._error_count = 0
        self._request_times: List[float] = []
        self._handler_metrics: Dict[str, HandlerMetrics] = defaultdict(HandlerMetrics)
        self._operation_metrics: Dict[str, OperationMetrics] = defaultdict(OperationMetrics)
        self._last_cleanup = datetime.now()
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    def start(self):
        """Start metrics collection."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._collect_metrics())
            logger.info("Metrics collection started")
    
    def stop(self):
        """Stop metrics collection."""
        if self._running and self._task:
            self._running = False
            try:
                # Cancel the task and wait for it to complete
                self._task.cancel()
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._wait_for_task())
                else:
                    loop.run_until_complete(self._wait_for_task())
            except Exception as e:
                logger.error(f"Error stopping metrics collection: {e}")
            finally:
                self._task = None
                logger.info("Metrics collection stopped")
    
    def increment_message_count(self):
        """Increment message counter."""
        self._message_count += 1
    
    def increment_callback_count(self):
        """Increment callback counter."""
        self._callback_count += 1
    
    def increment_error_count(self, error_type: str = "other"):
        """Increment error counter."""
        self._error_count += 1
        self._operation_metrics[error_type].errors += 1
        self._operation_metrics[error_type].last_error_time = datetime.now()
    
    def record_operation(
        self,
        operation: str,
        duration: float,
        error: Optional[str] = None
    ):
        """Record operation metrics."""
        metrics = self._operation_metrics[operation]
        metrics.count += 1
        metrics.total_time += duration
        metrics.min_time = min(metrics.min_time, duration)
        metrics.max_time = max(metrics.max_time, duration)
        metrics.avg_time = metrics.total_time / metrics.count
        
        if error:
            metrics.errors += 1
            metrics.last_error = error
            metrics.last_error_time = datetime.now()
    
    def record_handler_operation(
        self,
        handler: str,
        operation: str,
        duration: float,
        error: Optional[str] = None
    ):
        """Record handler-specific operation metrics."""
        handler_metrics = self._handler_metrics[handler]
        if operation not in handler_metrics.operations:
            handler_metrics.operations[operation] = OperationMetrics()
        
        op_metrics = handler_metrics.operations[operation]
        op_metrics.count += 1
        op_metrics.total_time += duration
        op_metrics.min_time = min(op_metrics.min_time, duration)
        op_metrics.max_time = max(op_metrics.max_time, duration)
        op_metrics.avg_time = op_metrics.total_time / op_metrics.count
        
        if error:
            op_metrics.errors += 1
            op_metrics.last_error = error
            op_metrics.last_error_time = datetime.now()
            handler_metrics.error_count += 1
    
    def record_request_time(self, duration: float):
        """Record request processing time."""
        self._request_times.append(duration)
        if len(self._request_times) > 1000:  # Keep last 1000 requests
            self._request_times.pop(0)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            "uptime": str(datetime.now() - self._start_time),
            "message_count": self._message_count,
            "callback_count": self._callback_count,
            "error_count": self._error_count,
            "system": {
                "cpu_percent": process.cpu_percent(),
                "memory_percent": process.memory_percent(),
                "memory_usage_mb": memory_info.rss / (1024 * 1024),
                "thread_count": process.num_threads(),
                "open_files": len(process.open_files()),
                "connections": len(process.connections())
            },
            "requests": {
                "total": len(self._request_times),
                "avg_time": sum(self._request_times) / len(self._request_times) if self._request_times else 0,
                "min_time": min(self._request_times) if self._request_times else 0,
                "max_time": max(self._request_times) if self._request_times else 0
            },
            "handlers": {
                name: {
                    "message_count": metrics.message_count,
                    "callback_count": metrics.callback_count,
                    "error_count": metrics.error_count,
                    "operations": {
                        op: {
                            "count": op_metrics.count,
                            "avg_time": op_metrics.avg_time,
                            "min_time": op_metrics.min_time,
                            "max_time": op_metrics.max_time,
                            "errors": op_metrics.errors,
                            "last_error": op_metrics.last_error,
                            "last_error_time": op_metrics.last_error_time.isoformat() if op_metrics.last_error_time else None
                        }
                        for op, op_metrics in metrics.operations.items()
                    }
                }
                for name, metrics in self._handler_metrics.items()
            }
        }
    
    async def _collect_metrics(self):
        """Collect system metrics periodically."""
        while self._running:
            try:
                # Collect system metrics
                process = psutil.Process()
                memory_info = process.memory_info()
                
                metrics = {
                    "timestamp": datetime.now().isoformat(),
                    "system": {
                        "cpu_percent": process.cpu_percent(),
                        "memory_percent": process.memory_percent(),
                        "memory_usage_mb": memory_info.rss / (1024 * 1024),
                        "thread_count": process.num_threads(),
                        "open_files": len(process.open_files()),
                        "connections": len(process.connections())
                    },
                    "application": {
                        "uptime": str(datetime.now() - self._start_time),
                        "message_count": self._message_count,
                        "callback_count": self._callback_count,
                        "error_count": self._error_count
                    }
                }
                
                # Log metrics if there are issues
                if (metrics["system"]["cpu_percent"] > 80 or
                    metrics["system"]["memory_percent"] > 80):
                    logger.warning(
                        "High resource usage detected:\n"
                        f"CPU: {metrics['system']['cpu_percent']}%\n"
                        f"Memory: {metrics['system']['memory_percent']}%"
                    )
                
                # Cleanup old metrics if needed
                self._cleanup_old_metrics()
                
                await asyncio.sleep(self.config.METRICS_COLLECTION_INTERVAL)
                
            except asyncio.CancelledError:
                logger.info("Metrics collection task cancelled")
                break
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                await asyncio.sleep(self.config.METRICS_COLLECTION_INTERVAL) # Try again after interval
    
    def _cleanup_old_metrics(self):
        """Clean up metrics older than retention period."""
        # Clean up old request times
        retention_period = timedelta(days=self.config.METRICS_RETENTION_DAYS)
        cutoff_time = datetime.now() - retention_period
        self._request_times = [t for t in self._request_times if datetime.fromtimestamp(t) >= cutoff_time]
        
        # Clean up old operation metrics (example: only keep recent errors)
        for op_metrics in self._operation_metrics.values():
            if op_metrics.last_error_time and op_metrics.last_error_time < cutoff_time:
                op_metrics.last_error = None
                op_metrics.last_error_time = None
        
        # Clean up old handler operation metrics
        for handler_metrics in self._handler_metrics.values():
            for op, op_metrics in list(handler_metrics.operations.items()): # Iterate over copy to allow deletion
                if op_metrics.last_error_time and op_metrics.last_error_time < cutoff_time:
                    del handler_metrics.operations[op]
        
        # Periodically clean up old metrics if enabled
        if datetime.now() - self._last_cleanup > timedelta(seconds=self.config.METRICS_CLEANUP_INTERVAL):
            # Further cleanup for old data if needed
            logger.debug("Performing deep cleanup of old metrics")
            self._last_cleanup = datetime.now()
    
    async def _wait_for_task(self):
        """Wait for the metrics collection task to complete."""
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in metrics collection task: {e}")

    async def cleanup(self):
        """Cleanup metrics collector resources."""
        logger.info("Starting metrics collector cleanup...")
        self.stop()
        # Clear all metrics data
        self._message_count = 0
        self._callback_count = 0
        self._error_count = 0
        self._request_times.clear()
        self._handler_metrics.clear()
        self._operation_metrics.clear()
        logger.info("Metrics collector cleanup completed")

    def __del__(self):
        """Destructor to ensure cleanup on deletion."""
        if hasattr(self, '_running') and self._running:
            logger.warning("MetricsCollector was not properly stopped")
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.cleanup())
                else:
                    loop.run_until_complete(self.cleanup())
            except Exception as e:
                logger.error(f"Error in MetricsCollector cleanup: {e}")

# Create and export the metrics collector instance
metrics_collector = MetricsCollector() 