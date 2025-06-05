"""Health check handler for the application."""

import logging
from typing import Callable, Awaitable
from aiohttp import web
from datetime import datetime
import json

from monitoring.metrics import MetricsCollector

logger = logging.getLogger(__name__)

def create_health_check_handler(metrics: MetricsCollector) -> Callable[[web.Request], Awaitable[web.Response]]:
    """Create a health check handler that returns application status.
    
    Args:
        metrics: MetricsCollector instance to get application metrics
        
    Returns:
        A handler function that can be used with aiohttp
    """
    async def health_check_handler(request: web.Request) -> web.Response:
        """Handle health check requests.
        
        Returns:
            JSON response with application status and metrics
        """
        try:
            # Get current metrics
            current_metrics = metrics.get_metrics()
            
            # Check if metrics indicate any issues
            system_metrics = current_metrics.get('system', {})
            cpu_percent = system_metrics.get('cpu_percent', 0)
            memory_percent = system_metrics.get('memory_percent', 0)
            
            # Determine health status
            is_healthy = True
            issues = []
            
            if cpu_percent > 80:
                is_healthy = False
                issues.append(f"High CPU usage: {cpu_percent}%")
            
            if memory_percent > 80:
                is_healthy = False
                issues.append(f"High memory usage: {memory_percent}%")
            
            # Prepare response
            response = {
                "status": "healthy" if is_healthy else "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "uptime": current_metrics.get('application', {}).get('uptime', 'unknown'),
                "metrics": current_metrics,
                "issues": issues
            }
            
            # Return response with appropriate status code
            return web.json_response(
                response,
                status=200 if is_healthy else 503
            )
            
        except Exception as e:
            logger.error(f"Error in health check handler: {e}", exc_info=True)
            return web.json_response(
                {
                    "status": "error",
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e)
                },
                status=500
            )
    
    return health_check_handler 