"""System monitoring script"""

import asyncio
import logging
import os
import psutil
import time
from datetime import datetime, timedelta
from pathlib import Path
import json
from typing import Dict, List, Optional

from config import (
    METRICS_DIR, METRICS_RETENTION_DAYS,
    MAX_MEMORY_USAGE_MB, MAX_CPU_USAGE_PERCENT,
    DB_FILE, DB_BACKUP_DIR
)
from utils.db_pool import db_pool

# Configure logging
logger = logging.getLogger(__name__)

class SystemMonitor:
    """Monitors system resources and application health"""
    
    def __init__(self):
        """Initialize system monitor"""
        self._metrics_dir = Path(METRICS_DIR)
        self._metrics_dir.mkdir(exist_ok=True)
        self._process = psutil.Process()
    
    async def check_system_health(self) -> Dict:
        """Check system health status"""
        try:
            # Get system metrics
            memory_info = self._process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)  # Convert to MB
            cpu_percent = self._process.cpu_percent()
            disk_usage = psutil.disk_usage(Path.cwd())
            
            # Get database metrics
            db_size = os.path.getsize(DB_FILE) / (1024 * 1024)  # Convert to MB
            backup_size = sum(
                f.stat().st_size for f in Path(DB_BACKUP_DIR).glob("*.db*")
            ) / (1024 * 1024)  # Convert to MB
            
            # Check for issues
            issues = []
            if memory_mb > MAX_MEMORY_USAGE_MB * 0.9:  # 90% of max
                issues.append(
                    f"High memory usage: {memory_mb:.1f}MB "
                    f"({memory_mb/MAX_MEMORY_USAGE_MB*100:.1f}% of limit)"
                )
            if cpu_percent > MAX_CPU_USAGE_PERCENT:
                issues.append(
                    f"High CPU usage: {cpu_percent:.1f}% "
                    f"(limit: {MAX_CPU_USAGE_PERCENT}%)"
                )
            if disk_usage.percent > 90:
                issues.append(
                    f"Low disk space: {disk_usage.free / (1024 * 1024):.1f}MB free "
                    f"({disk_usage.percent}% used)"
                )
            
            # Get database connection info
            active_connections = len(db_pool._pool)
            total_connections = db_pool._connection_count
            
            # Compile status
            status = {
                "timestamp": datetime.now().isoformat(),
                "system": {
                    "memory_usage_mb": memory_mb,
                    "memory_limit_mb": MAX_MEMORY_USAGE_MB,
                    "cpu_usage_percent": cpu_percent,
                    "cpu_limit_percent": MAX_CPU_USAGE_PERCENT,
                    "disk_usage_percent": disk_usage.percent,
                    "disk_free_mb": disk_usage.free / (1024 * 1024)
                },
                "database": {
                    "size_mb": db_size,
                    "backup_size_mb": backup_size,
                    "active_connections": active_connections,
                    "total_connections": total_connections
                },
                "issues": issues,
                "status": "healthy" if not issues else "unhealthy"
            }
            
            # Save status
            self._save_status(status)
            
            return status
        except Exception as e:
            logger.error(f"Error checking system health: {e}")
            raise
    
    def _save_status(self, status: Dict) -> None:
        """Save system status to file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            status_file = self._metrics_dir / f"system_status_{timestamp}.json"
            
            with open(status_file, "w") as f:
                json.dump(status, f, indent=2)
            
            logger.info(f"System status saved to {status_file}")
        except Exception as e:
            logger.error(f"Error saving system status: {e}")
    
    async def cleanup_old_metrics(self) -> None:
        """Remove old metrics files"""
        try:
            cutoff_date = datetime.now() - timedelta(days=METRICS_RETENTION_DAYS)
            for metrics_file in self._metrics_dir.glob("system_status_*.json"):
                try:
                    file_date = datetime.fromtimestamp(metrics_file.stat().st_mtime)
                    if file_date < cutoff_date:
                        metrics_file.unlink()
                        logger.info(f"Deleted old metrics file: {metrics_file}")
                except Exception as e:
                    logger.error(f"Error deleting metrics file {metrics_file}: {e}")
        except Exception as e:
            logger.error(f"Error cleaning up old metrics: {e}")
    
    async def monitor_continuously(self, interval: int = 300) -> None:
        """Monitor system continuously"""
        try:
            while True:
                status = await self.check_system_health()
                
                # Log status
                if status["issues"]:
                    logger.warning(
                        f"System health issues detected:\n" +
                        "\n".join(f"- {issue}" for issue in status["issues"])
                    )
                else:
                    logger.info("System health check passed")
                
                # Cleanup old metrics periodically
                if datetime.now().hour == 0:  # At midnight
                    await self.cleanup_old_metrics()
                
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.info("System monitoring stopped")
        except Exception as e:
            logger.error(f"Error in system monitoring: {e}")
            raise

async def main() -> None:
    """Main entry point"""
    try:
        # Initialize monitor
        monitor = SystemMonitor()
        
        # Check current status
        status = await monitor.check_system_health()
        logger.info("Current system status:")
        logger.info(f"- Memory usage: {status['system']['memory_usage_mb']:.1f}MB")
        logger.info(f"- CPU usage: {status['system']['cpu_usage_percent']:.1f}%")
        logger.info(f"- Disk usage: {status['system']['disk_usage_percent']}%")
        logger.info(f"- Database size: {status['database']['size_mb']:.1f}MB")
        logger.info(f"- Active connections: {status['database']['active_connections']}")
        
        if status["issues"]:
            logger.warning("Issues detected:")
            for issue in status["issues"]:
                logger.warning(f"- {issue}")
        else:
            logger.info("No issues detected")
        
        # Start continuous monitoring
        logger.info("Starting continuous monitoring...")
        await monitor.monitor_continuously()
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
    except Exception as e:
        logger.error(f"Monitoring failed: {e}")
        raise
    finally:
        # Close database pool
        await db_pool.close_all()

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run monitoring
    asyncio.run(main()) 