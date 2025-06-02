"""Database migration script"""

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
import aiosqlite
import json

from config import (
    DB_FILE, DB_MIGRATIONS_DIR, DB_BACKUP_DIR,
    DB_BACKUP_KEEP_DAYS
)
from utils.db_pool import db_pool

# Configure logging
logger = logging.getLogger(__name__)

class DatabaseMigrator:
    """Handles database migrations"""
    
    def __init__(self):
        """Initialize migrator"""
        self._migrations_dir = Path(DB_MIGRATIONS_DIR)
        self._migrations_dir.mkdir(exist_ok=True)
        self._backup_dir = Path(DB_BACKUP_DIR)
        self._backup_dir.mkdir(exist_ok=True)
    
    async def backup_database(self) -> str:
        """Create a backup of the database"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self._backup_dir / f"backup_{timestamp}.db"
        
        try:
            # Copy database file
            async with aiosqlite.connect(DB_FILE) as src_db:
                await src_db.backup(backup_file)
            
            logger.info(f"Database backup created: {backup_file}")
            return str(backup_file)
        except Exception as e:
            logger.error(f"Error creating database backup: {e}")
            raise
    
    async def cleanup_old_backups(self) -> None:
        """Remove old database backups"""
        try:
            cutoff_date = datetime.now() - timedelta(days=DB_BACKUP_KEEP_DAYS)
            for backup_file in self._backup_dir.glob("backup_*.db"):
                try:
                    file_date = datetime.fromtimestamp(backup_file.stat().st_mtime)
                    if file_date < cutoff_date:
                        backup_file.unlink()
                        logger.info(f"Deleted old backup: {backup_file}")
                except Exception as e:
                    logger.error(f"Error deleting backup {backup_file}: {e}")
        except Exception as e:
            logger.error(f"Error cleaning up old backups: {e}")
    
    async def get_applied_migrations(self) -> List[str]:
        """Get list of applied migrations"""
        try:
            async with aiosqlite.connect(DB_FILE) as db:
                # Create migrations table if it doesn't exist
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS migrations (
                        id TEXT PRIMARY KEY,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                await db.commit()
                
                # Get applied migrations
                async with db.execute("SELECT id FROM migrations ORDER BY applied_at") as cursor:
                    return [row[0] for row in await cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting applied migrations: {e}")
            raise
    
    async def apply_migration(self, migration_file: Path) -> None:
        """Apply a single migration"""
        try:
            # Read migration file
            with open(migration_file) as f:
                migration = json.load(f)
            
            migration_id = migration_file.stem
            async with aiosqlite.connect(DB_FILE) as db:
                # Begin transaction
                await db.execute("BEGIN TRANSACTION")
                try:
                    # Apply migration
                    for query in migration["queries"]:
                        await db.execute(query)
                    
                    # Record migration
                    await db.execute(
                        "INSERT INTO migrations (id) VALUES (?)",
                        (migration_id,)
                    )
                    
                    # Commit transaction
                    await db.commit()
                    logger.info(f"Applied migration: {migration_id}")
                except Exception as e:
                    # Rollback on error
                    await db.rollback()
                    logger.error(f"Error applying migration {migration_id}: {e}")
                    raise
        except Exception as e:
            logger.error(f"Error processing migration {migration_file}: {e}")
            raise
    
    async def run_migrations(self) -> None:
        """Run all pending migrations"""
        try:
            # Get applied migrations
            applied_migrations = await self.get_applied_migrations()
            
            # Get all migration files
            migration_files = sorted(
                self._migrations_dir.glob("*.json"),
                key=lambda f: f.stem
            )
            
            # Find pending migrations
            pending_migrations = [
                f for f in migration_files
                if f.stem not in applied_migrations
            ]
            
            if not pending_migrations:
                logger.info("No pending migrations found")
                return
            
            # Create backup before migrations
            backup_file = await self.backup_database()
            logger.info(f"Created backup before migrations: {backup_file}")
            
            try:
                # Apply pending migrations
                for migration_file in pending_migrations:
                    await self.apply_migration(migration_file)
                
                logger.info("All migrations applied successfully")
            except Exception as e:
                logger.error(f"Error during migrations: {e}")
                logger.info(f"Restoring from backup: {backup_file}")
                
                # Restore from backup
                async with aiosqlite.connect(backup_file) as src_db:
                    async with aiosqlite.connect(DB_FILE) as dst_db:
                        await src_db.backup(dst_db)
                
                logger.info("Database restored from backup")
                raise
            
            # Cleanup old backups
            await self.cleanup_old_backups()
        except Exception as e:
            logger.error(f"Error running migrations: {e}")
            raise

async def main() -> None:
    """Main entry point"""
    try:
        # Initialize migrator
        migrator = DatabaseMigrator()
        
        # Run migrations
        await migrator.run_migrations()
        
        logger.info("Migration process completed successfully")
    except Exception as e:
        logger.error(f"Migration process failed: {e}")
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
    
    # Run migrations
    asyncio.run(main()) 