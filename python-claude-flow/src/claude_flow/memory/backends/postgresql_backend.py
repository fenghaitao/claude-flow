"""
PostgreSQL backend implementation for enterprise-grade memory persistence.

This module provides a robust PostgreSQL backend for enterprise memory
storage with support for JSONB, full-text search, and advanced indexing.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import logging
from dataclasses import dataclass, field

import asyncpg
from pydantic import BaseModel, Field

from claude_flow.core.interfaces import MemoryBackend, MemoryEntry, MemoryKey, BaseComponent
from claude_flow.core.config_models import DatabaseConfig
from claude_flow.memory.schema import MemorySchemaManager


logger = logging.getLogger(__name__)


@dataclass
class PostgreSQLConnectionConfig:
    """Configuration for PostgreSQL connection parameters."""
    host: str = "localhost"
    port: int = 5432
    database: str = "claude_flow"
    username: str = "postgres"
    password: Optional[str] = None
    ssl: Union[bool, str] = "prefer"
    application_name: str = "claude-flow"
    command_timeout: float = 60.0
    min_connections: int = 10
    max_connections: int = 100
    max_inactive_connection_lifetime: float = 300.0
    
    def to_dsn(self) -> str:
        """Convert to PostgreSQL DSN format."""
        dsn_parts = [
            f"postgresql://{self.username}",
            f":{self.password}" if self.password else "",
            f"@{self.host}:{self.port}/{self.database}"
        ]
        return "".join(dsn_parts)


@dataclass
class PostgreSQLStats:
    """PostgreSQL database statistics and performance metrics."""
    total_entries: int = 0
    database_size_bytes: int = 0
    table_size_bytes: int = 0
    index_size_bytes: int = 0
    cache_hit_ratio: float = 0.0
    active_connections: int = 0
    avg_query_time_ms: float = 0.0
    slow_query_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "total_entries": self.total_entries,
            "database_size_bytes": self.database_size_bytes,
            "table_size_bytes": self.table_size_bytes,
            "index_size_bytes": self.index_size_bytes,
            "cache_hit_ratio": self.cache_hit_ratio,
            "active_connections": self.active_connections,
            "avg_query_time_ms": self.avg_query_time_ms,
            "slow_query_count": self.slow_query_count
        }


class PostgreSQLBackend(BaseComponent, MemoryBackend):
    """
    Enterprise-grade PostgreSQL backend for memory persistence.
    
    Features:
    - Async operations with connection pooling
    - JSONB for efficient JSON storage and querying
    - Full-text search with GIN indexes
    - Comprehensive indexing strategy
    - Advanced query optimization
    """
    
    def __init__(
        self,
        config: DatabaseConfig,
        schema_manager: Optional[MemorySchemaManager] = None,
        table_prefix: str = "cf_"
    ):
        super().__init__()
        self.config = config
        self.schema_manager = schema_manager or MemorySchemaManager()
        self.table_prefix = table_prefix
        
        # Connection configuration
        self.conn_config = PostgreSQLConnectionConfig(
            host=config.host,
            port=config.port,
            database=config.database_name,
            username=config.username,
            password=config.password
        )
        
        # Connection pool
        self.pool: Optional[asyncpg.Pool] = None
        
        # Statistics and monitoring
        self.stats = PostgreSQLStats()
        self._query_times: List[float] = []
        self._slow_query_threshold = 1000.0  # 1 second
        
        # Background tasks
        self._maintenance_task: Optional[asyncio.Task] = None
        self._maintenance_interval = 3600  # 1 hour
        
    async def initialize(self) -> None:
        """Initialize the PostgreSQL backend and create database schema."""
        try:
            logger.info(f"Initializing PostgreSQL backend at {self.conn_config.host}:{self.conn_config.port}")
            
            # Create connection pool
            self.pool = await asyncpg.create_pool(
                host=self.conn_config.host,
                port=self.conn_config.port,
                database=self.conn_config.database,
                user=self.conn_config.username,
                password=self.conn_config.password,
                ssl=self.conn_config.ssl,
                min_size=self.conn_config.min_connections,
                max_size=self.conn_config.max_connections,
                max_inactive_connection_lifetime=self.conn_config.max_inactive_connection_lifetime,
                command_timeout=self.conn_config.command_timeout
            )
            
            # Create database schema
            await self._create_schema()
            
            # Create indexes for performance
            await self._create_indexes()
            
            # Start background maintenance
            self._maintenance_task = asyncio.create_task(self._background_maintenance())
            
            self._initialized = True
            logger.info("PostgreSQL backend initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL backend: {e}")
            raise
    
    async def cleanup(self) -> None:
        """Clean up resources and close all connections."""
        try:
            logger.info("Cleaning up PostgreSQL backend")
            
            # Cancel background tasks
            if self._maintenance_task:
                self._maintenance_task.cancel()
                try:
                    await self._maintenance_task
                except asyncio.CancelledError:
                    pass
            
            # Close connection pool
            if self.pool:
                await self.pool.close()
            
            self._initialized = False
            logger.info("PostgreSQL backend cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during PostgreSQL backend cleanup: {e}")
    
    async def _create_schema(self) -> None:
        """Create the database schema using the schema manager."""
        async with self.pool.acquire() as conn:
            # Get PostgreSQL schema
            schema_sql = self.schema_manager.get_postgresql_schema()
            
            # Replace table prefix placeholders
            schema_sql = schema_sql.replace("memory_entries", f"{self.table_prefix}memory_entries")
            schema_sql = schema_sql.replace("memory_tags", f"{self.table_prefix}memory_tags")
            schema_sql = schema_sql.replace("memory_relations", f"{self.table_prefix}memory_relations")
            schema_sql = schema_sql.replace("memory_access_log", f"{self.table_prefix}memory_access_log")
            
            # Execute schema creation
            try:
                await conn.execute(schema_sql)
                logger.debug("Database schema created successfully")
            except asyncpg.exceptions.DuplicateTableError:
                logger.debug("Database schema already exists")
    
    async def _create_indexes(self) -> None:
        """Create performance indexes."""
        async with self.pool.acquire() as conn:
            indexes = [
                # Primary indexes
                f"CREATE INDEX IF NOT EXISTS idx_{self.table_prefix}memory_entries_namespace ON {self.table_prefix}memory_entries(namespace)",
                f"CREATE INDEX IF NOT EXISTS idx_{self.table_prefix}memory_entries_expires_at ON {self.table_prefix}memory_entries(expires_at) WHERE expires_at IS NOT NULL",
                f"CREATE INDEX IF NOT EXISTS idx_{self.table_prefix}memory_entries_created_at ON {self.table_prefix}memory_entries(created_at)",
                
                # JSONB indexes for fast JSON queries
                f"CREATE INDEX IF NOT EXISTS idx_{self.table_prefix}memory_entries_data_gin ON {self.table_prefix}memory_entries USING GIN(data)",
                f"CREATE INDEX IF NOT EXISTS idx_{self.table_prefix}memory_entries_metadata_gin ON {self.table_prefix}memory_entries USING GIN(metadata)",
                
                # Full-text search indexes
                f"CREATE INDEX IF NOT EXISTS idx_{self.table_prefix}memory_entries_fts ON {self.table_prefix}memory_entries USING GIN(to_tsvector('english', data::text))",
                
                # Tag indexes
                f"CREATE INDEX IF NOT EXISTS idx_{self.table_prefix}memory_tags_tag ON {self.table_prefix}memory_tags(tag)",
                f"CREATE INDEX IF NOT EXISTS idx_{self.table_prefix}memory_tags_entry_key ON {self.table_prefix}memory_tags(entry_key)"
            ]
            
            for index_sql in indexes:
                try:
                    await conn.execute(index_sql)
                except Exception as e:
                    logger.warning(f"Failed to create index: {e}")
            
            logger.debug("Database indexes created successfully")
    
    async def store(self, key: MemoryKey, entry: MemoryEntry) -> bool:
        """Store a memory entry in PostgreSQL."""
        try:
            start_time = time.time()
            
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    # Insert or update main entry
                    await conn.execute(f"""
                        INSERT INTO {self.table_prefix}memory_entries (
                            key, namespace, identifier, data, metadata, tags,
                            embedding, expires_at, created_at, updated_at,
                            access_count, last_accessed
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                        ON CONFLICT (key) DO UPDATE SET
                            data = EXCLUDED.data,
                            metadata = EXCLUDED.metadata,
                            tags = EXCLUDED.tags,
                            embedding = EXCLUDED.embedding,
                            expires_at = EXCLUDED.expires_at,
                            updated_at = EXCLUDED.updated_at,
                            access_count = EXCLUDED.access_count,
                            last_accessed = EXCLUDED.last_accessed
                    """, 
                        key.to_string(),
                        key.namespace,
                        key.identifier,
                        json.dumps(entry.data),
                        json.dumps(entry.metadata),
                        json.dumps(list(entry.tags)),
                        json.dumps(entry.embedding) if entry.embedding else None,
                        entry.expires_at,
                        entry.created_at,
                        entry.updated_at,
                        entry.access_count,
                        entry.last_accessed
                    )
                    
                    # Update tags table
                    await conn.execute(f"DELETE FROM {self.table_prefix}memory_tags WHERE entry_key = $1", key.to_string())
                    
                    if entry.tags:
                        tag_data = [(key.to_string(), tag, datetime.now()) for tag in entry.tags]
                        await conn.executemany(f"""
                            INSERT INTO {self.table_prefix}memory_tags (entry_key, tag, created_at)
                            VALUES ($1, $2, $3)
                        """, tag_data)
            
            # Update statistics
            query_time = (time.time() - start_time) * 1000
            self._update_query_stats(query_time)
            
            logger.debug(f"Stored memory entry in PostgreSQL: {key.to_string()}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store memory entry {key.to_string()}: {e}")
            return False
    
    async def retrieve(self, key: MemoryKey) -> Optional[MemoryEntry]:
        """Retrieve a memory entry from PostgreSQL."""
        try:
            start_time = time.time()
            
            async with self.pool.acquire() as conn:
                # Get entry data
                row = await conn.fetchrow(f"""
                    SELECT data, metadata, tags, embedding, expires_at, created_at,
                           updated_at, access_count, last_accessed
                    FROM {self.table_prefix}memory_entries
                    WHERE key = $1
                """, key.to_string())
                
                if not row:
                    return None
                
                # Check expiration
                if row['expires_at'] and datetime.now() > row['expires_at']:
                    await self._delete_entry(conn, key)
                    return None
                
                # Update access statistics
                new_access_count = (row['access_count'] or 0) + 1
                now = datetime.now()
                
                await conn.execute(f"""
                    UPDATE {self.table_prefix}memory_entries
                    SET access_count = $1, last_accessed = $2
                    WHERE key = $3
                """, new_access_count, now, key.to_string())
                
                # Construct memory entry
                entry = MemoryEntry(
                    data=json.loads(row['data']) if row['data'] else {},
                    metadata=json.loads(row['metadata']) if row['metadata'] else {},
                    tags=set(json.loads(row['tags'])) if row['tags'] else set(),
                    embedding=json.loads(row['embedding']) if row['embedding'] else None,
                    expires_at=row['expires_at'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    access_count=new_access_count,
                    last_accessed=now
                )
            
            # Update statistics
            query_time = (time.time() - start_time) * 1000
            self._update_query_stats(query_time)
            
            logger.debug(f"Retrieved memory entry from PostgreSQL: {key.to_string()}")
            return entry
            
        except Exception as e:
            logger.error(f"Failed to retrieve memory entry {key.to_string()}: {e}")
            return None
    
    async def delete(self, key: MemoryKey) -> bool:
        """Delete a memory entry from PostgreSQL."""
        try:
            start_time = time.time()
            
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    success = await self._delete_entry(conn, key)
            
            # Update statistics
            query_time = (time.time() - start_time) * 1000
            self._update_query_stats(query_time)
            
            if success:
                logger.debug(f"Deleted memory entry from PostgreSQL: {key.to_string()}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete memory entry {key.to_string()}: {e}")
            return False
    
    async def _delete_entry(self, conn: asyncpg.Connection, key: MemoryKey) -> bool:
        """Delete entry and related data within a transaction."""
        # Check if entry exists
        count = await conn.fetchval(
            f"SELECT COUNT(*) FROM {self.table_prefix}memory_entries WHERE key = $1",
            key.to_string()
        )
        
        if count == 0:
            return False
        
        # Delete related data
        await conn.execute(f"DELETE FROM {self.table_prefix}memory_tags WHERE entry_key = $1", key.to_string())
        await conn.execute(f"DELETE FROM {self.table_prefix}memory_relations WHERE source_key = $1 OR target_key = $1", key.to_string())
        
        # Delete main entry
        await conn.execute(f"DELETE FROM {self.table_prefix}memory_entries WHERE key = $1", key.to_string())
        
        return True
    
    async def search(
        self,
        query: str,
        namespace: Optional[str] = None,
        tags: Optional[Set[str]] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[Tuple[MemoryKey, MemoryEntry, float]]:
        """Search for memory entries using PostgreSQL full-text search."""
        try:
            start_time = time.time()
            results = []
            
            async with self.pool.acquire() as conn:
                # Build query conditions
                conditions = []
                params = []
                param_count = 0
                
                # Namespace filter
                if namespace:
                    param_count += 1
                    conditions.append(f"namespace = ${param_count}")
                    params.append(namespace)
                
                # Tag filters
                if tags:
                    for tag in tags:
                        param_count += 1
                        conditions.append(f"${param_count} = ANY(string_to_array(tags::text, ','))")
                        params.append(tag)
                
                # Expiration filter
                conditions.append("(expires_at IS NULL OR expires_at > NOW())")
                
                # Full-text search
                search_clause = ""
                if query.strip():
                    param_count += 1
                    search_clause = f", ts_rank(to_tsvector('english', data::text), plainto_tsquery('english', ${param_count})) as rank"
                    conditions.append(f"to_tsvector('english', data::text) @@ plainto_tsquery('english', ${param_count})")
                    params.append(query)
                else:
                    search_clause = ", 1.0 as rank"
                
                # Build final query
                where_clause = " AND ".join(conditions) if conditions else "1=1"
                param_count += 1
                params.append(limit)
                param_count += 1
                params.append(offset)
                
                sql_query = f"""
                    SELECT key, namespace, identifier, data, metadata, tags,
                           embedding, expires_at, created_at, updated_at,
                           access_count, last_accessed {search_clause}
                    FROM {self.table_prefix}memory_entries
                    WHERE {where_clause}
                    ORDER BY rank DESC, last_accessed DESC NULLS LAST, access_count DESC
                    LIMIT ${param_count-1} OFFSET ${param_count}
                """
                
                rows = await conn.fetch(sql_query, *params)
                
                for row in rows:
                    # Construct key and entry
                    key = MemoryKey(namespace=row['namespace'], identifier=row['identifier'])
                    entry = MemoryEntry(
                        data=json.loads(row['data']) if row['data'] else {},
                        metadata=json.loads(row['metadata']) if row['metadata'] else {},
                        tags=set(json.loads(row['tags'])) if row['tags'] else set(),
                        embedding=json.loads(row['embedding']) if row['embedding'] else None,
                        expires_at=row['expires_at'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],
                        access_count=row['access_count'] or 0,
                        last_accessed=row['last_accessed']
                    )
                    
                    score = float(row['rank']) if 'rank' in row else 1.0
                    results.append((key, entry, score))
            
            # Update statistics
            query_time = (time.time() - start_time) * 1000
            self._update_query_stats(query_time)
            
            logger.debug(f"Search returned {len(results)} results for query: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search memory entries: {e}")
            return []
    
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
            
            async with self.pool.acquire() as conn:
                conditions = []
                params = []
                param_count = 0
                
                if namespace:
                    param_count += 1
                    conditions.append(f"namespace = ${param_count}")
                    params.append(namespace)
                
                if prefix:
                    param_count += 1
                    conditions.append(f"key LIKE ${param_count}")
                    params.append(f"{prefix}%")
                
                # Expiration filter
                conditions.append("(expires_at IS NULL OR expires_at > NOW())")
                
                where_clause = " AND ".join(conditions) if conditions else "1=1"
                param_count += 1
                params.append(limit)
                param_count += 1
                params.append(offset)
                
                sql_query = f"""
                    SELECT namespace, identifier
                    FROM {self.table_prefix}memory_entries
                    WHERE {where_clause}
                    ORDER BY key
                    LIMIT ${param_count-1} OFFSET ${param_count}
                """
                
                rows = await conn.fetch(sql_query, *params)
                
                for row in rows:
                    keys.append(MemoryKey(namespace=row['namespace'], identifier=row['identifier']))
            
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
            async with self.pool.acquire() as conn:
                # Update current statistics
                self.stats.total_entries = await conn.fetchval(f"SELECT COUNT(*) FROM {self.table_prefix}memory_entries")
                
                # Get database size information
                size_info = await conn.fetchrow("""
                    SELECT 
                        pg_database_size(current_database()) as db_size,
                        pg_total_relation_size($1) as table_size,
                        pg_indexes_size($1) as index_size
                """, f"{self.table_prefix}memory_entries")
                
                if size_info:
                    self.stats.database_size_bytes = size_info['db_size']
                    self.stats.table_size_bytes = size_info['table_size']
                    self.stats.index_size_bytes = size_info['index_size']
                
                # Calculate query statistics
                if self._query_times:
                    self.stats.avg_query_time_ms = sum(self._query_times) / len(self._query_times)
                    self.stats.slow_query_count = sum(1 for t in self._query_times if t > self._slow_query_threshold)
            
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
                
                if not self._initialized or not self.pool:
                    continue
                
                logger.debug("Starting database maintenance")
                
                async with self.pool.acquire() as conn:
                    # Clean up expired entries
                    deleted_count = await conn.fetchval(f"""
                        DELETE FROM {self.table_prefix}memory_entries 
                        WHERE expires_at IS NOT NULL AND expires_at < NOW()
                    """)
                    
                    # Clean up orphaned tags
                    await conn.execute(f"""
                        DELETE FROM {self.table_prefix}memory_tags 
                        WHERE entry_key NOT IN (SELECT key FROM {self.table_prefix}memory_entries)
                    """)
                
                if deleted_count and deleted_count > 0:
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
            
            if not self.pool:
                return {
                    "status": "unhealthy",
                    "error": "Connection pool not initialized",
                    "dsn": self.conn_config.to_dsn()
                }
            
            async with self.pool.acquire() as conn:
                # Test basic query
                await conn.fetchval("SELECT 1")
                
                # Get basic server info
                server_version = await conn.fetchval("SELECT version()")
                
            response_time = (time.time() - start_time) * 1000
            
            return {
                "status": "healthy",
                "dsn": self.conn_config.to_dsn(),
                "response_time_ms": response_time,
                "server_version": server_version,
                "pool_size": self.pool.get_size(),
                "pool_used": self.pool.get_size() - self.pool.get_idle_size()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "dsn": self.conn_config.to_dsn()
            }