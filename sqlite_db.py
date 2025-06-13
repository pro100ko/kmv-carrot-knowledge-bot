import aiosqlite
import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple, AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum
import json
import bcrypt
from pathlib import Path
import shutil

from config import get_config
from utils.db_pool import with_connection
from utils.resource_manager import log_execution_time

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    """Base exception for database errors"""
    pass

class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails"""
    pass

class DatabaseQueryError(DatabaseError):
    """Raised when a database query fails"""
    pass

class DatabaseMigrationError(DatabaseError):
    """Raised when database migration fails"""
    pass

class UserRole(str, Enum):
    """User roles in the system"""
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"

@dataclass
class DatabaseStats:
    """Database statistics"""
    size_bytes: int
    last_backup: Optional[datetime]
    backup_count: int
    table_count: int
    total_records: int
    last_vacuum: Optional[datetime]

class DatabasePool:
    """Connection pool for database connections"""
    def __init__(self):
        self.config = get_config()
        self.pool_size = self.config.DB_POOL_SIZE
        self.pool: List[aiosqlite.Connection] = []
        self._lock = asyncio.Lock()
        self._available = asyncio.Queue()
        self._initialized = False

    async def initialize(self):
        """Initialize the connection pool"""
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:  # Double-check pattern
                return

            try:
                # Create initial connections
                for _ in range(self.pool_size):
                    conn = await aiosqlite.connect(
                        self.config.DB_FILE,
                        timeout=self.config.DB_POOL_TIMEOUT,
                        isolation_level=None  # Enable autocommit mode
                    )
                    conn.row_factory = aiosqlite.Row
                    await conn.execute("PRAGMA foreign_keys = ON")
                    await conn.execute("PRAGMA journal_mode = WAL")
                    await conn.execute("PRAGMA synchronous = NORMAL")
                    self.pool.append(conn)
                    await self._available.put(conn)

                self._initialized = True
                logger.info(f"Database pool initialized with {self.pool_size} connections")
            except Exception as e:
                logger.error(f"Failed to initialize database pool: {e}")
                await self.close()
                raise DatabaseConnectionError(f"Failed to initialize database pool: {e}")

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Acquire a connection from the pool"""
        if not self._initialized:
            await self.initialize()

        conn = await self._available.get()
        try:
            yield conn
        finally:
            await self._available.put(conn)

    async def close(self):
        """Close all connections in the pool"""
        async with self._lock:
            for conn in self.pool:
                try:
                    await conn.close()
                except Exception as e:
                    logger.error(f"Error closing database connection: {e}")
            self.pool.clear()
            self._initialized = False

class Database:
    """Base database class with connection pool support"""
    
    _instance = None
    _pool: Optional[DatabasePool] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize database connection"""
        self._pool = None # Will be set later
        self._initialized = False
        self.config = get_config() # Получаем объект конфигурации
        
    def set_pool(self, pool):
        """Set the database pool instance."""
        self._pool = pool

    @with_connection
    async def execute(self, conn: aiosqlite.Connection, query: str, params: tuple = ()) -> None:
        """Execute a query without returning results"""
        try:
            await conn.execute(query, params)
            await conn.commit()
        except Exception as e:
            await conn.rollback()
            logger.error(f"Database error executing query: {e}")
            raise
    
    @with_connection
    async def execute_many(self, conn: aiosqlite.Connection, query: str, params_list: List[tuple]) -> None:
        """Execute multiple queries"""
        try:
            await conn.executemany(query, params_list)
            await conn.commit()
        except Exception as e:
            await conn.rollback()
            logger.error(f"Database error executing many queries: {e}")
            raise
    
    @with_connection
    async def fetch_one(self, conn: aiosqlite.Connection, query: str, params: tuple = ()) -> Optional[tuple]:
        """Fetch a single row from the database"""
        try:
            async with conn.execute(query, params) as cursor:
                return await cursor.fetchone()
        except Exception as e:
            logger.error(f"Database error fetching one row: {e}")
            raise
    
    @with_connection
    async def fetch_all(self, conn: aiosqlite.Connection, query: str, params: tuple = ()) -> List[tuple]:
        """Fetch all rows from the database"""
        try:
            async with conn.execute(query, params) as cursor:
                return await cursor.fetchall()
        except Exception as e:
            logger.error(f"Database error fetching all rows: {e}")
            raise
    
    @with_connection
    async def fetch_value(self, conn: aiosqlite.Connection, query: str, params: tuple = ()) -> Any:
        """Fetch a single value from the database"""
        try:
            async with conn.execute(query, params) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Database error fetching value: {e}")
            raise
    
    @with_connection
    async def table_exists(self, conn: aiosqlite.Connection, table_name: str) -> bool:
        """Check if a table exists"""
        query = """
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
        """
        result = await self.fetch_one(conn, query, (table_name,))
        return result is not None
    
    @with_connection
    async def get_table_columns(self, conn: aiosqlite.Connection, table_name: str) -> List[str]:
        """Get column names for a table"""
        query = f"PRAGMA table_info({table_name})"
        columns = await self.fetch_all(conn, query)
        return [col[1] for col in columns]
    
    @with_connection
    async def begin_transaction(self, conn: aiosqlite.Connection) -> None:
        """Begin a transaction"""
        await conn.execute("BEGIN TRANSACTION")
    
    @with_connection
    async def commit_transaction(self, conn: aiosqlite.Connection) -> None:
        """Commit a transaction"""
        await conn.commit()
    
    @with_connection
    async def rollback_transaction(self, conn: aiosqlite.Connection) -> None:
        """Rollback a transaction"""
        await conn.rollback()
    
    @with_connection
    async def vacuum(self, conn: aiosqlite.Connection) -> None:
        """Vacuum the database to optimize storage"""
        try:
            await conn.execute("VACUUM")
            logger.info("Database vacuum completed successfully")
        except Exception as e:
            logger.error(f"Error during database vacuum: {e}")
            raise

    async def initialize(self):
        """Initialize database and run migrations"""
        try:
            # Ensure directories exist
            os.makedirs(self.config.DB_BACKUP_DIR, exist_ok=True)
            os.makedirs(self.config.DB_MIGRATIONS_DIR, exist_ok=True)
            
            # Create backup before any schema changes
            await self._backup_database()
            
            # Run migrations
            await self._run_migrations()
            
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise DatabaseConnectionError(f"Database initialization failed: {e}")

    async def _backup_database(self):
        """Create a backup of the database"""
        if not self.config.DB_BACKUP_DIR:
            logger.info("DB_BACKUP_DIR is not set. Skipping database backup.")
            return
        
        backup_dir = Path(self.config.DB_BACKUP_DIR)
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"backup_{timestamp}.db"
        source_db_file = Path(self.config.DB_FILE)

        try:
            # Copy the database file to the backup location
            shutil.copy2(source_db_file, backup_file)
            logger.info(f"Database backup created: {backup_file}")
        except Exception as e:
            logger.error(f"Failed to create database backup: {e}", exc_info=True)
            raise DatabaseError(f"Failed to create database backup: {e}")

        # Clean up old backups
        await self.cleanup_old_backups()

    async def _run_migrations(self):
        """Run database migrations from files."""
        migrations_dir = Path(self.config.DB_MIGRATIONS_DIR)
        if not migrations_dir.exists():
            logger.info(f"Migrations directory does not exist: {migrations_dir}. Skipping migrations.")
            return

        logger.info(f"Running database migrations from {migrations_dir}")
        migration_files = sorted(migrations_dir.glob("*.sql"))

        if not migration_files:
            logger.info("No migration files found. Skipping migrations.")
            return

        for migration_file in migration_files:
            try:
                logger.info(f"Applying migration: {migration_file.name}")
                with open(migration_file, 'r') as f:
                    script = f.read()
                await self.execute(script)
                logger.info(f"Migration {migration_file.name} applied successfully.")
            except Exception as e:
                logger.error(f"Failed to apply migration {migration_file.name}: {e}", exc_info=True)
                raise DatabaseMigrationError(f"Failed to apply migration {migration_file.name}: {e}")
        logger.info("All migrations applied successfully.")

    @asynccontextmanager
    async def transaction(self):
        """Context manager for database transactions"""
        async with self._pool.acquire() as conn:
            try:
                await conn.execute("BEGIN")
                yield conn
                await conn.commit()
            except Exception as e:
                await conn.rollback()
                raise DatabaseQueryError(f"Transaction failed: {e}")

    async def execute(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute a query and return results"""
        async with self._pool.acquire() as conn:
            try:
                async with conn.cursor() as cursor:
                    if params:
                        await cursor.execute(query, params)
                    else:
                        await cursor.execute(query)
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
            except Exception as e:
                raise DatabaseQueryError(f"Query failed: {e}")

    async def execute_one(self, query: str, params: tuple = None) -> Optional[Dict]:
        """Execute a query and return one result"""
        async with self._pool.acquire() as conn:
            try:
                async with conn.cursor() as cursor:
                    if params:
                        await cursor.execute(query, params)
                    else:
                        await cursor.execute(query)
                    row = await cursor.fetchone()
                    return dict(row) if row else None
            except Exception as e:
                raise DatabaseQueryError(f"Query failed: {e}")

    async def execute_many(self, query: str, params_list: List[tuple]) -> None:
        """Execute multiple queries"""
        async with self._pool.acquire() as conn:
            try:
                async with conn.cursor() as cursor:
                    await cursor.executemany(query, params_list)
            except Exception as e:
                raise DatabaseQueryError(f"Batch query failed: {e}")

    # User management methods
    async def register_user(self, user_data: Dict) -> bool:
        """Register a new user"""
        try:
            # Hash password if provided
            if "password" in user_data:
                user_data["password"] = bcrypt.hashpw(
                    user_data["password"].encode(),
                    bcrypt.gensalt()
                ).decode()

            async with self.transaction() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("""
                        INSERT INTO users (
                            telegram_id, username, first_name, last_name,
                            role, password, created_at, is_active
                        ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 1)
                    """, (
                        user_data["telegram_id"],
                        user_data.get("username"),
                        user_data.get("first_name"),
                        user_data.get("last_name"),
                        user_data.get("role", UserRole.USER.value),
                        user_data.get("password")
                    ))
            return True
        except Exception as e:
            logger.error(f"Failed to register user: {e}")
            return False

    async def get_user(self, telegram_id: int) -> Optional[Dict]:
        """Get user by telegram ID"""
        try:
            return await self.execute_one(
                "SELECT * FROM users WHERE telegram_id = ?",
                (telegram_id,)
            )
        except Exception as e:
            logger.error(f"Failed to get user: {e}")
            return None

    async def verify_password(self, telegram_id: int, password: str) -> bool:
        """Verify user password"""
        try:
            user = await self.get_user(telegram_id)
            if not user or not user.get("password"):
                return False
            return bcrypt.checkpw(
                password.encode(),
                user["password"].encode()
            )
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False

    # Product management methods
    async def add_product(self, product_data: Dict) -> Optional[int]:
        """Add a new product"""
        try:
            async with self.transaction() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("""
                        INSERT INTO products (
                            category_id, name, description, image_path,
                            created_at, updated_at, is_active
                        ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1)
                    """, (
                        product_data["category_id"],
                        product_data["name"],
                        product_data.get("description"),
                        product_data.get("image_path")
                    ))
                    return cursor.lastrowid
        except Exception as e:
            logger.error(f"Failed to add product: {e}")
            return None

    async def get_products_by_category(
        self,
        category_id: int,
        include_inactive: bool = False
    ) -> List[Dict]:
        """Get products by category"""
        try:
            query = """
                SELECT p.*, c.name as category_name
                FROM products p
                JOIN categories c ON p.category_id = c.id
                WHERE p.category_id = ?
            """
            params = [category_id]
            
            if not include_inactive:
                query += " AND p.is_active = 1"
                
            return await self.execute(query, tuple(params))
        except Exception as e:
            logger.error(f"Failed to get products: {e}")
            return []

    # Test management methods
    async def add_test(self, test_data: Dict) -> Optional[int]:
        """Add a new test"""
        try:
            async with self.transaction() as conn:
                async with conn.cursor() as cursor:
                    # Insert test
                    await cursor.execute("""
                        INSERT INTO tests (
                            title, description, category_id,
                            time_limit, passing_score, is_active,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (
                        test_data["title"],
                        test_data.get("description"),
                        test_data.get("category_id"),
                        test_data.get("time_limit"),
                        test_data.get("passing_score")
                    ))
                    test_id = cursor.lastrowid

                    # Insert questions
                    if "questions" in test_data:
                        for question in test_data["questions"]:
                            await cursor.execute("""
                                INSERT INTO test_questions (
                                    test_id, question_text, question_type,
                                    correct_answer, points
                                ) VALUES (?, ?, ?, ?, ?)
                            """, (
                                test_id,
                                question["text"],
                                question.get("type", "single"),
                                json.dumps(question["correct_answer"]),
                                question.get("points", 1)
                            ))

                    return test_id
        except Exception as e:
            logger.error(f"Failed to add test: {e}")
            return None

    async def get_test(self, test_id: int) -> Optional[Dict]:
        """Get test with questions"""
        try:
            # Get test details
            test = await self.execute_one(
                "SELECT * FROM tests WHERE id = ?",
                (test_id,)
            )
            if not test:
                return None

            # Get questions
            questions = await self.execute(
                "SELECT * FROM test_questions WHERE test_id = ? ORDER BY id",
                (test_id,)
            )

            # Parse correct answers
            for question in questions:
                question["correct_answer"] = json.loads(question["correct_answer"])

            test["questions"] = questions
            return test
        except Exception as e:
            logger.error(f"Failed to get test: {e}")
            return None

    # Statistics methods
    async def get_database_stats(self) -> DatabaseStats:
        """Get database statistics"""
        try:
            async with self._pool.acquire() as conn:
                # Get database size
                size = os.path.getsize(self.config.DB_FILE)

                # Get last backup
                backup_files = await self.get_backup_files()
                last_backup = (
                    datetime.strptime(backup_files[0]["timestamp"], "%Y%m%d_%H%M%S")
                    if backup_files
                    else None
                )

                # Get table count and total records
                async with conn.cursor() as cursor:
                    await cursor.execute("""
                        SELECT COUNT(*) as table_count,
                               SUM((SELECT COUNT(*) FROM sqlite_master WHERE type='table')) as total_records
                        FROM sqlite_master
                        WHERE type='table'
                    """)
                    stats = await cursor.fetchone()

                # Get last vacuum time
                vacuum_time = await self.execute_one(
                    "SELECT last_vacuum FROM database_stats ORDER BY last_vacuum DESC LIMIT 1"
                )

                return DatabaseStats(
                    size_bytes=size,
                    last_backup=last_backup,
                    backup_count=len(backup_files),
                    table_count=stats["table_count"],
                    total_records=stats["total_records"],
                    last_vacuum=datetime.fromisoformat(vacuum_time["last_vacuum"])
                    if vacuum_time
                    else None
                )
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            raise DatabaseError(f"Failed to get database stats: {e}")

    async def close(self):
        """Close database connections"""
        if self._pool:
            await self._pool.close()

    async def vacuum(self):
        """Vacuum database to optimize space"""
        try:
            async with self._pool.acquire() as conn:
                await conn.execute("VACUUM")
                await conn.execute(
                    "INSERT INTO database_stats (last_vacuum) VALUES (CURRENT_TIMESTAMP)"
                )
            logger.info("Database vacuum completed")
        except Exception as e:
            logger.error(f"Database vacuum failed: {e}")
            raise DatabaseError(f"Vacuum failed: {e}")

    async def cleanup_old_backups(self, keep_last_n: int = 5) -> bool:
        """Clean up old database backups"""
        try:
            backup_files = await self.get_backup_files()
            if len(backup_files) <= keep_last_n:
                return True

            for backup in backup_files[keep_last_n:]:
                try:
                    os.remove(backup["path"])
                    logger.info(f"Removed old backup: {backup['path']}")
                except Exception as e:
                    logger.error(f"Failed to remove backup {backup['path']}: {e}")

            return True
        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")
            return False

    async def get_backup_files(self) -> List[Dict]:
        """Get list of backup files"""
        try:
            backup_files = []
            for file in os.listdir(self.config.DB_BACKUP_DIR):
                if file.startswith("backup_") and file.endswith(".db"):
                    path = os.path.join(self.config.DB_BACKUP_DIR, file)
                    timestamp = file[7:-3]  # Remove 'backup_' prefix and '.db' suffix
                    backup_files.append({
                        "path": path,
                        "timestamp": timestamp,
                        "size": os.path.getsize(path)
                    })
            return sorted(backup_files, key=lambda x: x["timestamp"], reverse=True)
        except Exception as e:
            logger.error(f"Failed to get backup files: {e}")
            return []

    async def check_database_integrity(self) -> bool:
        """Check database integrity"""
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("PRAGMA integrity_check")
                    result = await cursor.fetchone()
                    return result[0] == "ok"
        except Exception as e:
            logger.error(f"Database integrity check failed: {e}")
            return False

def build_schemas():
    """Build database schemas (for initial setup)."""
    # This function is typically for initial schema creation, not migrations.
    # In a production environment, migrations handle schema updates.
    # For SQLite, if the database file doesn't exist, it will be created by aiosqlite.connect().
    # No explicit schema building needed here beyond what migrations handle.
    pass

# Global database instance
db = Database()

def initialize(pool: DatabasePool):
    """Initialize the global database instance with a given connection pool."""
    db.set_pool(pool)
    db.config = get_config() # Убедитесь, что config установлен для глобального экземпляра db
    # Остальные настройки уже будут получены из self.config в DatabasePool и Database

# Инициализация при импорте
if __name__ == '__main__':
    # Тестовая проверка соединения и целостности
    try:
        if db.check_database_integrity():
            logger.info("Database connection and integrity test successful")
            
            # Print database stats
            stats = db.get_database_stats()
            logger.info("Database statistics:")
            logger.info(f"Size: {stats['size_bytes'] / 1024:.2f} KB")
            logger.info(f"Backup files: {stats['backup_count']}")
            logger.info("Table record counts:")
            logger.info(f"  Total records: {stats['total_records']}")
            logger.info(f"  Table count: {stats['table_count']}")
        else:
            logger.error("Database integrity check failed")
    except Exception as e:
        logger.error(f"Database test failed: {e}")
