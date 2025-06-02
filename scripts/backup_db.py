"""Database backup script"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
import aiosqlite
import shutil
import json

from config import (
    DB_FILE, DB_BACKUP_DIR, DB_BACKUP_KEEP_DAYS,
    DB_BACKUP_COMPRESS
)
from utils.db_pool import db_pool

# Configure logging
logger = logging.getLogger(__name__)

class DatabaseBackup:
    """Handles database backups"""
    
    def __init__(self):
        """Initialize backup handler"""
        self._backup_dir = Path(DB_BACKUP_DIR)
        self._backup_dir.mkdir(exist_ok=True)
    
    async def create_backup(self) -> str:
        """Create a backup of the database"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self._backup_dir / f"backup_{timestamp}.db"
        
        try:
            # Ensure all connections are closed
            await db_pool.close_all()
            
            # Copy database file
            shutil.copy2(DB_FILE, backup_file)
            
            # Compress backup if enabled
            if DB_BACKUP_COMPRESS:
                compressed_file = backup_file.with_suffix(".db.gz")
                with open(backup_file, "rb") as f_in:
                    with open(compressed_file, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                backup_file.unlink()  # Remove uncompressed file
                backup_file = compressed_file
            
            # Create backup metadata
            metadata = {
                "timestamp": timestamp,
                "original_size": os.path.getsize(DB_FILE),
                "backup_size": os.path.getsize(backup_file),
                "compressed": DB_BACKUP_COMPRESS
            }
            
            metadata_file = backup_file.with_suffix(".json")
            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Database backup created: {backup_file}")
            return str(backup_file)
        except Exception as e:
            logger.error(f"Error creating database backup: {e}")
            raise
    
    async def cleanup_old_backups(self) -> None:
        """Remove old database backups"""
        try:
            cutoff_date = datetime.now() - timedelta(days=DB_BACKUP_KEEP_DAYS)
            for backup_file in self._backup_dir.glob("backup_*.*"):
                try:
                    file_date = datetime.fromtimestamp(backup_file.stat().st_mtime)
                    if file_date < cutoff_date:
                        # Remove backup file and its metadata
                        backup_file.unlink()
                        metadata_file = backup_file.with_suffix(".json")
                        if metadata_file.exists():
                            metadata_file.unlink()
                        logger.info(f"Deleted old backup: {backup_file}")
                except Exception as e:
                    logger.error(f"Error deleting backup {backup_file}: {e}")
        except Exception as e:
            logger.error(f"Error cleaning up old backups: {e}")
    
    async def list_backups(self) -> List[Dict]:
        """List all available backups"""
        try:
            backups = []
            for backup_file in self._backup_dir.glob("backup_*.db*"):
                try:
                    metadata_file = backup_file.with_suffix(".json")
                    if metadata_file.exists():
                        with open(metadata_file) as f:
                            metadata = json.load(f)
                    else:
                        metadata = {
                            "timestamp": backup_file.stem.split("_")[1],
                            "original_size": None,
                            "backup_size": os.path.getsize(backup_file),
                            "compressed": backup_file.suffix == ".gz"
                        }
                    
                    backups.append({
                        "file": str(backup_file),
                        "size": os.path.getsize(backup_file),
                        "created_at": datetime.fromtimestamp(backup_file.stat().st_mtime),
                        **metadata
                    })
                except Exception as e:
                    logger.error(f"Error reading backup {backup_file}: {e}")
            
            return sorted(backups, key=lambda x: x["created_at"], reverse=True)
        except Exception as e:
            logger.error(f"Error listing backups: {e}")
            raise

async def main() -> None:
    """Main entry point"""
    try:
        # Initialize backup handler
        backup = DatabaseBackup()
        
        # Create backup
        backup_file = await backup.create_backup()
        logger.info(f"Created backup: {backup_file}")
        
        # List backups
        backups = await backup.list_backups()
        logger.info("Available backups:")
        for b in backups:
            logger.info(
                f"- {b['file']} "
                f"({b['backup_size'] / 1024 / 1024:.1f}MB, "
                f"created at {b['created_at']})"
            )
        
        # Cleanup old backups
        await backup.cleanup_old_backups()
        
        logger.info("Backup process completed successfully")
    except Exception as e:
        logger.error(f"Backup process failed: {e}")
        raise

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run backup
    asyncio.run(main()) 