"""Metrics collection and monitoring."""

import time
import logging
import psutil
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
from dataclasses import dataclass, field
from config import (
    METRICS_RETENTION_DAYS,
    METRICS_COLLECTION_INTERVAL,
    METRICS_CLEANUP_INTERVAL
)

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
            self._task.cancel()
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
                if datetime.now() - self._last_cleanup > timedelta(seconds=METRICS_CLEANUP_INTERVAL):
                    self._cleanup_old_metrics()
                    self._last_cleanup = datetime.now()
                
                await asyncio.sleep(METRICS_COLLECTION_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                await asyncio.sleep(METRICS_COLLECTION_INTERVAL)
    
    def _cleanup_old_metrics(self):
        """Clean up old metrics data."""
        cutoff_time = datetime.now() - timedelta(days=METRICS_RETENTION_DAYS)
        
        # Clean up handler metrics
        for handler_metrics in self._handler_metrics.values():
            for op_metrics in handler_metrics.operations.values():
                if (op_metrics.last_error_time and
                    op_metrics.last_error_time < cutoff_time):
                    op_metrics.last_error = None
                    op_metrics.last_error_time = None
        
        # Clean up operation metrics
        for op_metrics in self._operation_metrics.values():
            if (op_metrics.last_error_time and
                op_metrics.last_error_time < cutoff_time):
                op_metrics.last_error = None
                op_metrics.last_error_time = None

# Create and export the metrics collector instance
metrics_collector = MetricsCollector() 