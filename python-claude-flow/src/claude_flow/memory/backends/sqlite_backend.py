"""
SQLite backend implementation for local memory storage.

This module provides a high-performance, async SQLite backend for local memory
operations with support for hierarchical storage, semantic search, and
automatic data lifecycle management.
"""

import asyncio
import json
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from contextlib import asynccontextmanager
import threading
import logging
from dataclasses import dataclass, field

import aiosqlite
from pydantic import BaseModel, Field, validator

from claude_flow.core.interfaces import MemoryBackend, MemoryEntry, MemoryKey, BaseComponent
from claude_flow.core.config_models import DatabaseConfig
from claude_flow.memory.schema import DatabaseSchema, MemorySchemaManager


logger = logging.getLogger(__name__)


@dataclass
class SQLiteConnectionConfig:
    """Configuration for SQLite connection parameters."""
    database_path: Path
    timeout: float = 30.0
    check_same_thread: bool = False
    journal_mode: str = "WAL"
    synchronous: str = "NORMAL"
    foreign_keys: bool = True
    cache_size: int = -64000  # 64MB cache
    temp_store: str = "MEMORY"
    mmap_size: int = 268435456  # 256MB mmap
    
    def to_uri(self) -> str:
        """Convert to SQLite URI format."""
        params = [
            f"cache=shared",
            f"mode=rwc",
            f"timeout={int(self.timeout * 1000)}"
        ]
        return f"file:{self.database_path}?{'&'.join(params)}"


@dataclass
class SQLiteStats:
    """SQLite database statistics and metrics."""
    total_entries: int = 0
    total_size_bytes: int = 0
    memory_usage_mb: float = 0.0
    cache_hit_ratio: float = 0.0
    last_vacuum: Optional[datetime] = None
    fragmentation_ratio: float = 0.0
    connection_count: int = 0
    query_count: int = 0
    avg_query_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "total_entries": self.total_entries,
            "total_size_bytes": self.total_size_bytes,
            "memory_usage_mb": self.memory_usage_mb,
            "cache_hit_ratio": self.cache_hit_ratio,
            "last_vacuum": self.last_vacuum.isoformat() if self.last_vacuum else None,
            "fragmentation_ratio": self.fragmentation_ratio,
            "connection_count": self.connection_count,
            "query_count": self.query_count,
            "avg_query_time_ms": self.avg_query_time_ms
        }


class SQLiteBackend(BaseComponent, MemoryBackend):
    """
    High-performance SQLite backend for local memory storage.
    
    Features:
    - Async operations with connection pooling
    - Automatic schema management and migrations
    - Hierarchical data organization
    - Full-text search capabilities
    - Automatic cleanup and maintenance
    - Comprehensive metrics and monitoring
    - Transaction support with rollback
    """
    
    def __init__(
        self,
        config: DatabaseConfig,
        schema_manager: Optional[MemorySchemaManager] = None,
        max_connections: int = 10,
        connection_timeout: float = 30.0
    ):
        super().__init__()
        self.config = config
        self.schema_manager = schema_manager or MemorySchemaManager()
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        
        # Database configuration
        self.db_path = Path(config.database_name)
        self.conn_config = SQLiteConnectionConfig(
            database_path=self.db_path,
            timeout=connection_timeout
        )
        
        # Connection management
        self._connection_pool: asyncio.Queue = asyncio.Queue(maxsize=max_connections)
        self._pool_initialized = False
        self._lock = asyncio.Lock()
        
        # Statistics and monitoring
        self.stats = SQLiteStats()
        self._query_times: List[float] = []
        self._last_maintenance = datetime.now()
        
        # Background tasks
        self._maintenance_task: Optional[asyncio.Task] = None
        self._maintenance_interval = 3600  # 1 hour
        
    async def initialize(self) -> None:
        """Initialize the SQLite backend and create database schema."""
        try:
            logger.info(f"Initializing SQLite backend at {self.db_path}")
            
            # Ensure directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Initialize connection pool
            await self._initialize_connection_pool()
            
            # Create database schema
            await self._create_schema()
            
            # Start background maintenance
            self._maintenance_task = asyncio.create_task(self._background_maintenance())
            
            self._initialized = True
            logger.info("SQLite backend initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize SQLite backend: {e}")
            raise
    
    async def cleanup(self) -> None:
        """Clean up resources and close all connections."""
        try:
            logger.info("Cleaning up SQLite backend")
            
            # Cancel background tasks
            if self._maintenance_task:
                self._maintenance_task.cancel()
                try:
                    await self._maintenance_task
                except asyncio.CancelledError:
                    pass
            
            # Close all connections in pool
            while not self._connection_pool.empty():
                try:
                    conn = self._connection_pool.get_nowait()
                    await conn.close()
                except asyncio.QueueEmpty:
                    break
                except Exception as e:
                    logger.warning(f"Error closing connection: {e}")
            
            self._initialized = False
            logger.info("SQLite backend cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during SQLite backend cleanup: {e}")
    
    async def _initialize_connection_pool(self) -> None:
        """Initialize the connection pool with configured connections."""
        if self._pool_initialized:
            return
            
        logger.debug(f"Initializing connection pool with {self.max_connections} connections")
        
        for _ in range(self.max_connections):
            conn = await self._create_connection()
            await self._connection_pool.put(conn)
        
        self._pool_initialized = True
        logger.debug("Connection pool initialized")
    
    async def _create_connection(self) -> aiosqlite.Connection:
        """Create a new SQLite connection with optimized settings."""
        conn = await aiosqlite.connect(
            self.conn_config.to_uri(),
            timeout=self.conn_config.timeout,
            uri=True
        )
        
        # Configure connection for performance
        await conn.execute(f"PRAGMA journal_mode = {self.conn_config.journal_mode}")
        await conn.execute(f"PRAGMA synchronous = {self.conn_config.synchronous}")
        await conn.execute(f"PRAGMA foreign_keys = {'ON' if self.conn_config.foreign_keys else 'OFF'}")
        await conn.execute(f"PRAGMA cache_size = {self.conn_config.cache_size}")
        await conn.execute(f"PRAGMA temp_store = {self.conn_config.temp_store}")
        await conn.execute(f"PRAGMA mmap_size = {self.conn_config.mmap_size}")
        
        # Enable full-text search
        await conn.execute("PRAGMA case_sensitive_like = OFF")
        
        await conn.commit()
        return conn
    
    @asynccontextmanager
    async def _get_connection(self):
        """Get a connection from the pool with automatic return."""
        if not self._pool_initialized:
            await self._initialize_connection_pool()
        
        try:
            # Get connection from pool with timeout
            conn = await asyncio.wait_for(
                self._connection_pool.get(),
                timeout=self.connection_timeout
            )
            
            try:
                yield conn
            finally:
                # Return connection to pool
                await self._connection_pool.put(conn)
                
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for database connection")
            raise
        except Exception as e:
            logger.error(f"Error with database connection: {e}")
            raise
    
    async def _create_schema(self) -> None:
        """Create the database schema using the schema manager."""
        async with self._get_connection() as conn:
            schema = self.schema_manager.get_sqlite_schema()
            
            # Execute schema creation
            for statement in schema.split(';'):
                statement = statement.strip()
                if statement:
                    await conn.execute(statement)
            
            await conn.commit()
            logger.debug("Database schema created successfully")
    
    async def store(self, key: MemoryKey, entry: MemoryEntry) -> bool:
        """Store a memory entry in the database."""
        try:
            start_time = time.time()
            
            async with self._get_connection() as conn:
                # Convert entry to storage format
                entry_data = {
                    "key": key.to_string(),
                    "namespace": key.namespace,
                    "identifier": key.identifier,
                    "data": json.dumps(entry.data),
                    "metadata": json.dumps(entry.metadata),
                    "tags": json.dumps(list(entry.tags)),
                    "embedding": json.dumps(entry.embedding) if entry.embedding else None,
                    "expires_at": entry.expires_at.isoformat() if entry.expires_at else None,
                    "created_at": entry.created_at.isoformat(),
                    "updated_at": entry.updated_at.isoformat(),
                    "access_count": entry.access_count,
                    "last_accessed": entry.last_accessed.isoformat() if entry.last_accessed else None
                }
                
                # Insert or update entry
                await conn.execute("""
                    INSERT OR REPLACE INTO memory_entries (
                        key, namespace, identifier, data, metadata, tags,
                        embedding, expires_at, created_at, updated_at,
                        access_count, last_accessed
                    ) VALUES (
                        :key, :namespace, :identifier, :data, :metadata, :tags,
                        :embedding, :expires_at, :created_at, :updated_at,
                        :access_count, :last_accessed
                    )
                """, entry_data)
                
                # Store tags separately for efficient querying
                await conn.execute("DELETE FROM memory_tags WHERE entry_key = ?", (key.to_string(),))
                for tag in entry.tags:
                    await conn.execute("""
                        INSERT INTO memory_tags (entry_key, tag, created_at)
                        VALUES (?, ?, ?)
                    """, (key.to_string(), tag, datetime.now().isoformat()))
                
                # Log access
                await conn.execute("""
                    INSERT INTO memory_access_log (entry_key, operation, timestamp, metadata)
                    VALUES (?, 'store', ?, ?)
                """, (key.to_string(), datetime.now().isoformat(), json.dumps({})))
                
                await conn.commit()
            
            # Update statistics
            query_time = (time.time() - start_time) * 1000
            self._update_query_stats(query_time)
            
            logger.debug(f"Stored memory entry: {key.to_string()}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store memory entry {key.to_string()}: {e}")
            return False
    
    async def retrieve(self, key: MemoryKey) -> Optional[MemoryEntry]:
        """Retrieve a memory entry by key."""
        try:
            start_time = time.time()
            
            async with self._get_connection() as conn:
                # Get entry data
                cursor = await conn.execute("""
                    SELECT data, metadata, tags, embedding, expires_at, created_at,
                           updated_at, access_count, last_accessed
                    FROM memory_entries
                    WHERE key = ?
                """, (key.to_string(),))
                
                row = await cursor.fetchone()
                if not row:
                    return None
                
                # Check expiration
                if row[4]:  # expires_at
                    expires_at = datetime.fromisoformat(row[4])
                    if datetime.now() > expires_at:
                        await self._delete_entry(conn, key)
                        return None
                
                # Update access statistics
                new_access_count = (row[7] or 0) + 1
                now = datetime.now().isoformat()
                
                await conn.execute("""
                    UPDATE memory_entries
                    SET access_count = ?, last_accessed = ?
                    WHERE key = ?
                """, (new_access_count, now, key.to_string()))
                
                # Log access
                await conn.execute("""
                    INSERT INTO memory_access_log (entry_key, operation, timestamp, metadata)
                    VALUES (?, 'retrieve', ?, ?)
                """, (key.to_string(), now, json.dumps({})))
                
                await conn.commit()
                
                # Construct memory entry
                entry = MemoryEntry(
                    data=json.loads(row[0]),
                    metadata=json.loads(row[1]) if row[1] else {},
                    tags=set(json.loads(row[2])) if row[2] else set(),
                    embedding=json.loads(row[3]) if row[3] else None,
                    expires_at=datetime.fromisoformat(row[4]) if row[4] else None,
                    created_at=datetime.fromisoformat(row[5]),
                    updated_at=datetime.fromisoformat(row[6]),
                    access_count=new_access_count,
                    last_accessed=datetime.fromisoformat(now)
                )
            
            # Update statistics
            query_time = (time.time() - start_time) * 1000
            self._update_query_stats(query_time)
            
            logger.debug(f"Retrieved memory entry: {key.to_string()}")
            return entry
            
        except Exception as e:
            logger.error(f"Failed to retrieve memory entry {key.to_string()}: {e}")
            return None
    
    async def delete(self, key: MemoryKey) -> bool:
        """Delete a memory entry by key."""
        try:
            start_time = time.time()
            
            async with self._get_connection() as conn:
                success = await self._delete_entry(conn, key)
                await conn.commit()
            
            # Update statistics
            query_time = (time.time() - start_time) * 1000
            self._update_query_stats(query_time)
            
            if success:
                logger.debug(f"Deleted memory entry: {key.to_string()}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete memory entry {key.to_string()}: {e}")
            return False
    
    async def _delete_entry(self, conn: aiosqlite.Connection, key: MemoryKey) -> bool:
        """Delete entry and related data within a transaction."""
        # Check if entry exists
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM memory_entries WHERE key = ?",
            (key.to_string(),)
        )
        count = await cursor.fetchone()
        
        if not count or count[0] == 0:
            return False
        
        # Delete related data
        await conn.execute("DELETE FROM memory_tags WHERE entry_key = ?", (key.to_string(),))
        await conn.execute("DELETE FROM memory_relations WHERE source_key = ? OR target_key = ?", 
                         (key.to_string(), key.to_string()))
        
        # Delete main entry
        await conn.execute("DELETE FROM memory_entries WHERE key = ?", (key.to_string(),))
        
        # Log deletion
        await conn.execute("""
            INSERT INTO memory_access_log (entry_key, operation, timestamp, metadata)
            VALUES (?, 'delete', ?, ?)
        """, (key.to_string(), datetime.now().isoformat(), json.dumps({})))
        
        return True
    
    async def search(
        self,
        query: str,
        namespace: Optional[str] = None,
        tags: Optional[Set[str]] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[Tuple[MemoryKey, MemoryEntry, float]]:
        """Search for memory entries using full-text search and filtering."""
        try:
            start_time = time.time()
            results = []
            
            async with self._get_connection() as conn:
                # Build query conditions
                conditions = []
                params = []
                
                if namespace:
                    conditions.append("namespace = ?")
                    params.append(namespace)
                
                if tags:
                    tag_conditions = []
                    for tag in tags:
                        tag_conditions.append("""
                            EXISTS (
                                SELECT 1 FROM memory_tags 
                                WHERE entry_key = memory_entries.key AND tag = ?
                            )
                        """)
                        params.append(tag)
                    if tag_conditions:
                        conditions.append("(" + " AND ".join(tag_conditions) + ")")
                
                # Add full-text search if query provided
                if query.strip():
                    conditions.append("""
                        (data LIKE ? OR metadata LIKE ? OR 
                         key LIKE ? OR identifier LIKE ?)
                    """)
                    search_term = f"%{query}%"
                    params.extend([search_term, search_term, search_term, search_term])
                
                # Build final query
                where_clause = " AND ".join(conditions) if conditions else "1=1"
                sql_query = f"""
                    SELECT key, namespace, identifier, data, metadata, tags,
                           embedding, expires_at, created_at, updated_at,
                           access_count, last_accessed
                    FROM memory_entries
                    WHERE {where_clause}
                    ORDER BY 
                        CASE WHEN last_accessed IS NOT NULL THEN last_accessed ELSE created_at END DESC,
                        access_count DESC
                    LIMIT ? OFFSET ?
                """
                params.extend([limit, offset])
                
                cursor = await conn.execute(sql_query, params)
                rows = await cursor.fetchall()
                
                for row in rows:
                    # Check expiration
                    if row[7]:  # expires_at
                        expires_at = datetime.fromisoformat(row[7])
                        if datetime.now() > expires_at:
                            continue
                    
                    # Construct key and entry
                    key = MemoryKey(namespace=row[1], identifier=row[2])
                    entry = MemoryEntry(
                        data=json.loads(row[3]),
                        metadata=json.loads(row[4]) if row[4] else {},
                        tags=set(json.loads(row[5])) if row[5] else set(),
                        embedding=json.loads(row[6]) if row[6] else None,
                        expires_at=datetime.fromisoformat(row[7]) if row[7] else None,
                        created_at=datetime.fromisoformat(row[8]),
                        updated_at=datetime.fromisoformat(row[9]),
                        access_count=row[10] or 0,
                        last_accessed=datetime.fromisoformat(row[11]) if row[11] else None
                    )
                    
                    # Calculate relevance score (simple implementation)
                    score = self._calculate_relevance_score(query, entry, key)
                    results.append((key, entry, score))
            
            # Sort by relevance score
            results.sort(key=lambda x: x[2], reverse=True)
            
            # Update statistics
            query_time = (time.time() - start_time) * 1000
            self._update_query_stats(query_time)
            
            logger.debug(f"Search returned {len(results)} results for query: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search memory entries: {e}")
            return []
    
    def _calculate_relevance_score(self, query: str, entry: MemoryEntry, key: MemoryKey) -> float:
        """Calculate relevance score for search results."""
        score = 0.0
        query_lower = query.lower()
        
        # Boost for exact matches in key
        if query_lower in key.to_string().lower():
            score += 10.0
        
        # Boost for matches in data
        data_str = json.dumps(entry.data).lower()
        if query_lower in data_str:
            score += 5.0
        
        # Boost for matches in metadata
        metadata_str = json.dumps(entry.metadata).lower()
        if query_lower in metadata_str:
            score += 3.0
        
        # Boost for recent access
        if entry.last_accessed:
            days_since_access = (datetime.now() - entry.last_accessed).days
            score += max(0, 2.0 - (days_since_access * 0.1))
        
        # Boost for frequent access
        score += min(2.0, entry.access_count * 0.1)
        
        return score
    
    async def list_keys(
        self,
        namespace: Optional[str] = None,
        prefix: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[MemoryKey]:
        """List memory keys with optional filtering."""
        try:
            start_time = time.time()
            keys = []
            
            async with self._get_connection() as conn:
                conditions = []
                params = []
                
                if namespace:
                    conditions.append("namespace = ?")
                    params.append(namespace)
                
                if prefix:
                    conditions.append("key LIKE ?")
                    params.append(f"{prefix}%")
                
                where_clause = " AND ".join(conditions) if conditions else "1=1"
                sql_query = f"""
                    SELECT namespace, identifier
                    FROM memory_entries
                    WHERE {where_clause}
                    ORDER BY key
                    LIMIT ? OFFSET ?
                """
                params.extend([limit, offset])
                
                cursor = await conn.execute(sql_query, params)
                rows = await cursor.fetchall()
                
                for row in rows:
                    keys.append(MemoryKey(namespace=row[0], identifier=row[1]))
            
            # Update statistics
            query_time = (time.time() - start_time) * 1000
            self._update_query_stats(query_time)
            
            return keys
            
        except Exception as e:
            logger.error(f"Failed to list memory keys: {e}")
            return []
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics."""
        try:
            async with self._get_connection() as conn:
                # Update current statistics
                cursor = await conn.execute("SELECT COUNT(*) FROM memory_entries")
                self.stats.total_entries = (await cursor.fetchone())[0]
                
                # Get database size
                cursor = await conn.execute("PRAGMA page_count")
                page_count = (await cursor.fetchone())[0]
                cursor = await conn.execute("PRAGMA page_size")
                page_size = (await cursor.fetchone())[0]
                self.stats.total_size_bytes = page_count * page_size
                
                # Get cache statistics
                cursor = await conn.execute("PRAGMA cache_size")
                cache_size = (await cursor.fetchone())[0]
                self.stats.memory_usage_mb = abs(cache_size) / 1024.0 if cache_size < 0 else cache_size * page_size / (1024 * 1024)
                
                # Calculate query statistics
                if self._query_times:
                    self.stats.avg_query_time_ms = sum(self._query_times) / len(self._query_times)
                
                self.stats.connection_count = self._connection_pool.qsize()
                self.stats.query_count += 1
            
            return self.stats.to_dict()
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
    
    def _update_query_stats(self, query_time_ms: float) -> None:
        """Update query performance statistics."""
        self._query_times.append(query_time_ms)
        # Keep only last 1000 query times for moving average
        if len(self._query_times) > 1000:
            self._query_times = self._query_times[-1000:]
    
    async def _background_maintenance(self) -> None:
        """Background task for database maintenance."""
        while True:
            try:
                await asyncio.sleep(self._maintenance_interval)
                
                if not self._initialized:
                    continue
                
                logger.debug("Starting database maintenance")
                
                async with self._get_connection() as conn:
                    # Clean up expired entries
                    now = datetime.now().isoformat()
                    cursor = await conn.execute("""
                        DELETE FROM memory_entries 
                        WHERE expires_at IS NOT NULL AND expires_at < ?
                    """, (now,))
                    deleted_count = cursor.rowcount
                    
                    # Clean up orphaned tags
                    await conn.execute("""
                        DELETE FROM memory_tags 
                        WHERE entry_key NOT IN (SELECT key FROM memory_entries)
                    """)
                    
                    # Clean up orphaned relations
                    await conn.execute("""
                        DELETE FROM memory_relations 
                        WHERE source_key NOT IN (SELECT key FROM memory_entries)
                           OR target_key NOT IN (SELECT key FROM memory_entries)
                    """)
                    
                    # Optimize database periodically
                    if datetime.now() - self._last_maintenance > timedelta(days=1):
                        await conn.execute("VACUUM")
                        await conn.execute("ANALYZE")
                        self.stats.last_vacuum = datetime.now()
                        self._last_maintenance = datetime.now()
                    
                    await conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"Database maintenance: cleaned up {deleted_count} expired entries")
                
            except asyncio.CancelledError:
                logger.info("Database maintenance task cancelled")
                break
            except Exception as e:
                logger.error(f"Error during database maintenance: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check and return status."""
        try:
            start_time = time.time()
            
            async with self._get_connection() as conn:
                # Test basic query
                cursor = await conn.execute("SELECT 1")
                await cursor.fetchone()
                
                # Check database integrity
                cursor = await conn.execute("PRAGMA integrity_check(1)")
                integrity = await cursor.fetchone()
                
            query_time = (time.time() - start_time) * 1000
            
            return {
                "status": "healthy",
                "database_path": str(self.db_path),
                "response_time_ms": query_time,
                "integrity_check": integrity[0] if integrity else "unknown",
                "connections_available": self._connection_pool.qsize(),
                "total_entries": self.stats.total_entries,
                "last_maintenance": self._last_maintenance.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "database_path": str(self.db_path)
            }