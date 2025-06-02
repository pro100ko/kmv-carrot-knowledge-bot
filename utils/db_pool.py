"""Database connection pool management."""

import asyncio
import logging
from typing import Optional, AsyncGenerator
import aiosqlite
from contextlib import asynccontextmanager

from config import (
    DB_FILE,
    DB_POOL_SIZE,
    MAX_MEMORY_USAGE_MB,
)

logger = logging.getLogger(__name__)

class DatabasePool:
    """Manages a pool of database connections."""
    
    def __init__(self, db_file: str, pool_size: int = DB_POOL_SIZE):
        """Initialize database pool.
        
        Args:
            db_file: Path to the SQLite database file
            pool_size: Maximum number of connections in the pool
        """
        self.db_file = db_file
        self.pool_size = pool_size
        self.pool: asyncio.Queue[aiosqlite.Connection] = asyncio.Queue(maxsize=pool_size)
        self.active_connections = 0
        self._lock = asyncio.Lock()
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the connection pool."""
        if self._initialized:
            return
        
        async with self._lock:
            if self._initialized:  # Double-check pattern
                return
            
            try:
                # Create initial connections
                for _ in range(self.pool_size):
                    conn = await aiosqlite.connect(self.db_file)
                    await conn.execute("PRAGMA journal_mode=WAL")  # Enable WAL mode
                    await conn.execute("PRAGMA synchronous=NORMAL")  # Faster writes
                    await conn.execute("PRAGMA cache_size=-2000")  # Use 2MB of cache
                    await conn.execute("PRAGMA temp_store=MEMORY")  # Store temp tables in memory
                    await conn.execute("PRAGMA mmap_size=30000000000")  # Use memory mapping
                    await self.pool.put(conn)
                    self.active_connections += 1
                
                self._initialized = True
                logger.info(f"Database pool initialized with {self.pool_size} connections")
            
            except Exception as e:
                logger.error(f"Failed to initialize database pool: {e}")
                await self.close()  # Clean up any created connections
                raise
    
    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Acquire a database connection from the pool.
        
        Yields:
            A database connection
            
        Raises:
            RuntimeError: If the pool is not initialized
            Exception: If no connection is available
        """
        if not self._initialized:
            raise RuntimeError("Database pool not initialized")
        
        conn = None
        try:
            # Try to get a connection from the pool
            try:
                conn = await asyncio.wait_for(self.pool.get(), timeout=5.0)
            except asyncio.TimeoutError:
                # If no connection is available, create a new one if possible
                async with self._lock:
                    if self.active_connections < self.pool_size:
                        conn = await aiosqlite.connect(self.db_file)
                        await conn.execute("PRAGMA journal_mode=WAL")
                        await conn.execute("PRAGMA synchronous=NORMAL")
                        await conn.execute("PRAGMA cache_size=-2000")
                        await conn.execute("PRAGMA temp_store=MEMORY")
                        await conn.execute("PRAGMA mmap_size=30000000000")
                        self.active_connections += 1
                        logger.debug("Created new database connection")
                    else:
                        raise Exception("No database connections available")
            
            yield conn
        
        finally:
            if conn:
                try:
                    # Return the connection to the pool
                    await self.pool.put(conn)
                except Exception as e:
                    logger.error(f"Error returning connection to pool: {e}")
                    await self._close_connection(conn)
    
    async def _close_connection(self, conn: aiosqlite.Connection) -> None:
        """Close a database connection."""
        try:
            await conn.close()
            async with self._lock:
                self.active_connections -= 1
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")
    
    async def close(self) -> None:
        """Close all connections in the pool."""
        if not self._initialized:
            return
        
        async with self._lock:
            while not self.pool.empty():
                try:
                    conn = await self.pool.get_nowait()
                    await self._close_connection(conn)
                except asyncio.QueueEmpty:
                    break
                except Exception as e:
                    logger.error(f"Error closing connection: {e}")
            
            self._initialized = False
            self.active_connections = 0
            logger.info("Database pool closed")
    
    async def execute(self, query: str, *args, **kwargs) -> None:
        """Execute a query using a connection from the pool.
        
        Args:
            query: SQL query to execute
            *args: Query parameters
            **kwargs: Additional query parameters
        """
        async with self.acquire() as conn:
            try:
                await conn.execute(query, *args, **kwargs)
                await conn.commit()
            except Exception as e:
                await conn.rollback()
                logger.error(f"Database error executing query: {e}")
                raise
    
    async def fetchone(self, query: str, *args, **kwargs) -> Optional[tuple]:
        """Execute a query and fetch one row.
        
        Args:
            query: SQL query to execute
            *args: Query parameters
            **kwargs: Additional query parameters
            
        Returns:
            A single row as a tuple, or None if no rows found
        """
        async with self.acquire() as conn:
            try:
                async with conn.execute(query, *args, **kwargs) as cursor:
                    return await cursor.fetchone()
            except Exception as e:
                logger.error(f"Database error fetching one row: {e}")
                raise
    
    async def fetchall(self, query: str, *args, **kwargs) -> list[tuple]:
        """Execute a query and fetch all rows.
        
        Args:
            query: SQL query to execute
            *args: Query parameters
            **kwargs: Additional query parameters
            
        Returns:
            A list of rows, each as a tuple
        """
        async with self.acquire() as conn:
            try:
                async with conn.execute(query, *args, **kwargs) as cursor:
                    return await cursor.fetchall()
            except Exception as e:
                logger.error(f"Database error fetching all rows: {e}")
                raise
    
    async def execute_many(self, query: str, params: list[tuple]) -> None:
        """Execute a query multiple times with different parameters.
        
        Args:
            query: SQL query to execute
            params: List of parameter tuples
        """
        async with self.acquire() as conn:
            try:
                await conn.executemany(query, params)
                await conn.commit()
            except Exception as e:
                await conn.rollback()
                logger.error(f"Database error executing many: {e}")
                raise

# Create a singleton instance
db_pool = DatabasePool(DB_FILE) 