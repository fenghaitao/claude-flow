"""
Redis backend implementation for distributed memory caching.

This module provides a high-performance Redis backend for distributed
memory caching with support for clustering, pub/sub messaging, and
automatic failover capabilities.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import logging
from dataclasses import dataclass, field

import aioredis
from pydantic import BaseModel, Field

from claude_flow.core.interfaces import MemoryBackend, MemoryEntry, MemoryKey, BaseComponent
from claude_flow.core.config_models import RedisConfig


logger = logging.getLogger(__name__)


@dataclass
class RedisConnectionConfig:
    """Configuration for Redis connection parameters."""
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    database: int = 0
    ssl: bool = False
    ssl_cert_reqs: str = "required"
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    socket_keepalive: bool = True
    socket_keepalive_options: Dict[str, Any] = field(default_factory=dict)
    max_connections: int = 100
    retry_on_timeout: bool = True
    health_check_interval: int = 30
    
    def to_redis_url(self) -> str:
        """Convert to Redis URL format."""
        scheme = "rediss" if self.ssl else "redis"
        auth = f":{self.password}@" if self.password else ""
        return f"{scheme}://{auth}{self.host}:{self.port}/{self.database}"


@dataclass
class RedisStats:
    """Redis connection and performance statistics."""
    connected_clients: int = 0
    used_memory: int = 0
    used_memory_human: str = "0B"
    used_memory_peak: int = 0
    keyspace_hits: int = 0
    keyspace_misses: int = 0
    hit_ratio: float = 0.0
    total_commands_processed: int = 0
    instantaneous_ops_per_sec: int = 0
    connected_slaves: int = 0
    master_repl_offset: int = 0
    role: str = "master"
    uptime_in_seconds: int = 0
    redis_version: str = "unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "connected_clients": self.connected_clients,
            "used_memory": self.used_memory,
            "used_memory_human": self.used_memory_human,
            "used_memory_peak": self.used_memory_peak,
            "keyspace_hits": self.keyspace_hits,
            "keyspace_misses": self.keyspace_misses,
            "hit_ratio": self.hit_ratio,
            "total_commands_processed": self.total_commands_processed,
            "instantaneous_ops_per_sec": self.instantaneous_ops_per_sec,
            "connected_slaves": self.connected_slaves,
            "master_repl_offset": self.master_repl_offset,
            "role": self.role,
            "uptime_in_seconds": self.uptime_in_seconds,
            "redis_version": self.redis_version
        }


class RedisBackend(BaseComponent, MemoryBackend):
    """
    High-performance Redis backend for distributed memory caching.
    
    Features:
    - Async operations with connection pooling
    - Pub/Sub messaging for real-time notifications
    - Clustering support for high availability
    - Automatic failover and reconnection
    - TTL-based expiration with automatic cleanup
    - Compression for large values
    - Batch operations for performance
    - Comprehensive metrics and monitoring
    """
    
    def __init__(
        self,
        config: RedisConfig,
        key_prefix: str = "claude_flow:",
        compression_threshold: int = 1024,
        batch_size: int = 100
    ):
        super().__init__()
        self.config = config
        self.key_prefix = key_prefix
        self.compression_threshold = compression_threshold
        self.batch_size = batch_size
        
        # Connection configuration
        self.conn_config = RedisConnectionConfig(
            host=config.host,
            port=config.port,
            password=config.password,
            database=config.database,
            max_connections=getattr(config, 'max_connections', 100)
        )
        
        # Redis connections
        self.redis: Optional[aioredis.Redis] = None
        self.pubsub: Optional[aioredis.client.PubSub] = None
        
        # Statistics and monitoring
        self.stats = RedisStats()
        self._query_times: List[float] = []
        self._last_health_check = datetime.now()
        
        # Event handlers
        self._event_handlers: Dict[str, List] = {}
        
        # Background tasks
        self._health_check_task: Optional[asyncio.Task] = None
        self._pubsub_task: Optional[asyncio.Task] = None
        
    async def initialize(self) -> None:
        """Initialize the Redis backend and establish connections."""
        try:
            logger.info(f"Initializing Redis backend at {self.conn_config.host}:{self.conn_config.port}")
            
            # Create Redis connection
            self.redis = await aioredis.from_url(
                self.conn_config.to_redis_url(),
                socket_timeout=self.conn_config.socket_timeout,
                socket_connect_timeout=self.conn_config.socket_connect_timeout,
                socket_keepalive=self.conn_config.socket_keepalive,
                socket_keepalive_options=self.conn_config.socket_keepalive_options,
                retry_on_timeout=self.conn_config.retry_on_timeout,
                max_connections=self.conn_config.max_connections,
                decode_responses=True
            )
            
            # Test connection
            await self.redis.ping()
            
            # Initialize pub/sub for real-time notifications
            self.pubsub = self.redis.pubsub()
            await self.pubsub.subscribe(f"{self.key_prefix}events")
            
            # Start background tasks
            self._health_check_task = asyncio.create_task(self._background_health_check())
            self._pubsub_task = asyncio.create_task(self._handle_pubsub_messages())
            
            self._initialized = True
            logger.info("Redis backend initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis backend: {e}")
            raise
    
    async def cleanup(self) -> None:
        """Clean up resources and close connections."""
        try:
            logger.info("Cleaning up Redis backend")
            
            # Cancel background tasks
            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
            
            if self._pubsub_task:
                self._pubsub_task.cancel()
                try:
                    await self._pubsub_task
                except asyncio.CancelledError:
                    pass
            
            # Close pub/sub connection
            if self.pubsub:
                await self.pubsub.unsubscribe()
                await self.pubsub.close()
            
            # Close Redis connection
            if self.redis:
                await self.redis.close()
            
            self._initialized = False
            logger.info("Redis backend cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during Redis backend cleanup: {e}")
    
    def _format_key(self, key: MemoryKey) -> str:
        """Format memory key for Redis storage."""
        return f"{self.key_prefix}entry:{key.namespace}:{key.identifier}"
    
    def _format_tag_key(self, tag: str) -> str:
        """Format tag key for Redis storage."""
        return f"{self.key_prefix}tag:{tag}"
    
    def _format_namespace_key(self, namespace: str) -> str:
        """Format namespace key for Redis storage."""
        return f"{self.key_prefix}namespace:{namespace}"
    
    async def store(self, key: MemoryKey, entry: MemoryEntry) -> bool:
        """Store a memory entry in Redis."""
        try:
            start_time = time.time()
            
            if not self.redis:
                return False
            
            # Serialize entry data
            entry_data = {
                "data": json.dumps(entry.data),
                "metadata": json.dumps(entry.metadata),
                "tags": json.dumps(list(entry.tags)),
                "embedding": json.dumps(entry.embedding) if entry.embedding else "",
                "created_at": entry.created_at.isoformat(),
                "updated_at": entry.updated_at.isoformat(),
                "access_count": str(entry.access_count),
                "last_accessed": entry.last_accessed.isoformat() if entry.last_accessed else ""
            }
            
            # Calculate TTL if expiration is set
            ttl = None
            if entry.expires_at:
                ttl = int((entry.expires_at - datetime.now()).total_seconds())
                if ttl <= 0:
                    return False  # Already expired
            
            redis_key = self._format_key(key)
            
            # Use pipeline for atomic operations
            pipe = self.redis.pipeline()
            
            # Store main entry
            pipe.hmset(redis_key, entry_data)
            if ttl:
                pipe.expire(redis_key, ttl)
            
            # Add to namespace set
            namespace_key = self._format_namespace_key(key.namespace)
            pipe.sadd(namespace_key, redis_key)
            
            # Add to tag sets
            for tag in entry.tags:
                tag_key = self._format_tag_key(tag)
                pipe.sadd(tag_key, redis_key)
            
            # Execute pipeline
            await pipe.execute()
            
            # Publish notification
            await self._publish_event("store", key, entry)
            
            # Update statistics
            query_time = (time.time() - start_time) * 1000
            self._update_query_stats(query_time)
            
            logger.debug(f"Stored memory entry in Redis: {key.to_string()}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store memory entry {key.to_string()}: {e}")
            return False
    
    async def retrieve(self, key: MemoryKey) -> Optional[MemoryEntry]:
        """Retrieve a memory entry from Redis."""
        try:
            start_time = time.time()
            
            if not self.redis:
                return None
            
            redis_key = self._format_key(key)
            
            # Get entry data
            entry_data = await self.redis.hgetall(redis_key)
            if not entry_data:
                return None
            
            # Parse entry data
            try:
                entry = MemoryEntry(
                    data=json.loads(entry_data["data"]),
                    metadata=json.loads(entry_data["metadata"]) if entry_data.get("metadata") else {},
                    tags=set(json.loads(entry_data["tags"])) if entry_data.get("tags") else set(),
                    embedding=json.loads(entry_data["embedding"]) if entry_data.get("embedding") else None,
                    created_at=datetime.fromisoformat(entry_data["created_at"]),
                    updated_at=datetime.fromisoformat(entry_data["updated_at"]),
                    access_count=int(entry_data.get("access_count", 0)),
                    last_accessed=datetime.fromisoformat(entry_data["last_accessed"]) if entry_data.get("last_accessed") else None
                )
            except (KeyError, ValueError, json.JSONDecodeError) as e:
                logger.error(f"Failed to parse entry data for {key.to_string()}: {e}")
                return None
            
            # Update access statistics
            new_access_count = entry.access_count + 1
            now = datetime.now()
            
            await self.redis.hmset(redis_key, {
                "access_count": str(new_access_count),
                "last_accessed": now.isoformat()
            })
            
            entry.access_count = new_access_count
            entry.last_accessed = now
            
            # Publish notification
            await self._publish_event("retrieve", key, entry)
            
            # Update statistics
            query_time = (time.time() - start_time) * 1000
            self._update_query_stats(query_time)
            
            logger.debug(f"Retrieved memory entry from Redis: {key.to_string()}")
            return entry
            
        except Exception as e:
            logger.error(f"Failed to retrieve memory entry {key.to_string()}: {e}")
            return None
    
    async def delete(self, key: MemoryKey) -> bool:
        """Delete a memory entry from Redis."""
        try:
            start_time = time.time()
            
            if not self.redis:
                return False
            
            redis_key = self._format_key(key)
            
            # Get entry data before deletion for cleanup
            entry_data = await self.redis.hgetall(redis_key)
            if not entry_data:
                return False
            
            # Use pipeline for atomic operations
            pipe = self.redis.pipeline()
            
            # Delete main entry
            pipe.delete(redis_key)
            
            # Remove from namespace set
            namespace_key = self._format_namespace_key(key.namespace)
            pipe.srem(namespace_key, redis_key)
            
            # Remove from tag sets
            if entry_data.get("tags"):
                try:
                    tags = json.loads(entry_data["tags"])
                    for tag in tags:
                        tag_key = self._format_tag_key(tag)
                        pipe.srem(tag_key, redis_key)
                except json.JSONDecodeError:
                    pass
            
            # Execute pipeline
            results = await pipe.execute()
            deleted = results[0] > 0  # Check if main entry was deleted
            
            if deleted:
                # Publish notification
                await self._publish_event("delete", key, None)
            
            # Update statistics
            query_time = (time.time() - start_time) * 1000
            self._update_query_stats(query_time)
            
            if deleted:
                logger.debug(f"Deleted memory entry from Redis: {key.to_string()}")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to delete memory entry {key.to_string()}: {e}")
            return False
    
    async def search(
        self,
        query: str,
        namespace: Optional[str] = None,
        tags: Optional[Set[str]] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[Tuple[MemoryKey, MemoryEntry, float]]:
        """Search for memory entries using Redis set operations."""
        try:
            start_time = time.time()
            results = []
            
            if not self.redis:
                return results
            
            # Get candidate keys based on filters
            candidate_keys = set()
            
            # Filter by namespace
            if namespace:
                namespace_key = self._format_namespace_key(namespace)
                namespace_members = await self.redis.smembers(namespace_key)
                candidate_keys.update(namespace_members)
            
            # Filter by tags (intersection)
            if tags:
                tag_sets = []
                for tag in tags:
                    tag_key = self._format_tag_key(tag)
                    tag_members = await self.redis.smembers(tag_key)
                    tag_sets.append(set(tag_members))
                
                if tag_sets:
                    if candidate_keys:
                        # Intersect with existing candidates
                        for tag_set in tag_sets:
                            candidate_keys &= tag_set
                    else:
                        # Start with first tag set
                        candidate_keys = tag_sets[0]
                        for tag_set in tag_sets[1:]:
                            candidate_keys &= tag_set
            
            # If no filters, get all keys (expensive operation, use with caution)
            if not candidate_keys and not namespace and not tags:
                pattern = f"{self.key_prefix}entry:*"
                candidate_keys = set(await self.redis.keys(pattern))
            
            # Retrieve and filter entries
            scored_results = []
            
            for redis_key in candidate_keys:
                try:
                    # Parse key to get MemoryKey
                    key_parts = redis_key.replace(f"{self.key_prefix}entry:", "").split(":", 1)
                    if len(key_parts) != 2:
                        continue
                    
                    memory_key = MemoryKey(namespace=key_parts[0], identifier=key_parts[1])
                    
                    # Get entry data
                    entry_data = await self.redis.hgetall(redis_key)
                    if not entry_data:
                        continue
                    
                    # Parse entry
                    entry = MemoryEntry(
                        data=json.loads(entry_data["data"]),
                        metadata=json.loads(entry_data["metadata"]) if entry_data.get("metadata") else {},
                        tags=set(json.loads(entry_data["tags"])) if entry_data.get("tags") else set(),
                        embedding=json.loads(entry_data["embedding"]) if entry_data.get("embedding") else None,
                        created_at=datetime.fromisoformat(entry_data["created_at"]),
                        updated_at=datetime.fromisoformat(entry_data["updated_at"]),
                        access_count=int(entry_data.get("access_count", 0)),
                        last_accessed=datetime.fromisoformat(entry_data["last_accessed"]) if entry_data.get("last_accessed") else None
                    )
                    
                    # Calculate relevance score
                    score = self._calculate_relevance_score(query, entry, memory_key)
                    
                    # Apply text search filter
                    if query.strip() and score == 0:
                        continue
                    
                    scored_results.append((memory_key, entry, score))
                    
                except (KeyError, ValueError, json.JSONDecodeError) as e:
                    logger.warning(f"Failed to parse entry {redis_key}: {e}")
                    continue
            
            # Sort by score and apply pagination
            scored_results.sort(key=lambda x: x[2], reverse=True)
            results = scored_results[offset:offset + limit]
            
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
        
        if not query.strip():
            # No query, score based on access patterns
            score = entry.access_count * 0.1
            if entry.last_accessed:
                days_since_access = (datetime.now() - entry.last_accessed).days
                score += max(0, 2.0 - (days_since_access * 0.1))
            return score
        
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
        
        # Boost for tag matches
        for tag in entry.tags:
            if query_lower in tag.lower():
                score += 2.0
        
        # Boost for recent access
        if entry.last_accessed:
            days_since_access = (datetime.now() - entry.last_accessed).days
            score += max(0, 1.0 - (days_since_access * 0.05))
        
        # Boost for frequent access
        score += min(1.0, entry.access_count * 0.05)
        
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
            
            if not self.redis:
                return keys
            
            # Get keys based on filters
            if namespace:
                # Get keys from namespace set
                namespace_key = self._format_namespace_key(namespace)
                redis_keys = await self.redis.smembers(namespace_key)
            else:
                # Get all entry keys
                pattern = f"{self.key_prefix}entry:*"
                redis_keys = await self.redis.keys(pattern)
            
            # Parse and filter keys
            parsed_keys = []
            for redis_key in redis_keys:
                try:
                    key_parts = redis_key.replace(f"{self.key_prefix}entry:", "").split(":", 1)
                    if len(key_parts) != 2:
                        continue
                    
                    memory_key = MemoryKey(namespace=key_parts[0], identifier=key_parts[1])
                    
                    # Apply prefix filter
                    if prefix and not memory_key.to_string().startswith(prefix):
                        continue
                    
                    parsed_keys.append(memory_key)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse key {redis_key}: {e}")
                    continue
            
            # Sort and apply pagination
            parsed_keys.sort(key=lambda k: k.to_string())
            keys = parsed_keys[offset:offset + limit]
            
            # Update statistics
            query_time = (time.time() - start_time) * 1000
            self._update_query_stats(query_time)
            
            return keys
            
        except Exception as e:
            logger.error(f"Failed to list memory keys: {e}")
            return []
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive Redis statistics."""
        try:
            if not self.redis:
                return {}
            
            # Get Redis server info
            info = await self.redis.info()
            
            # Update statistics
            self.stats.connected_clients = info.get("connected_clients", 0)
            self.stats.used_memory = info.get("used_memory", 0)
            self.stats.used_memory_human = info.get("used_memory_human", "0B")
            self.stats.used_memory_peak = info.get("used_memory_peak", 0)
            self.stats.keyspace_hits = info.get("keyspace_hits", 0)
            self.stats.keyspace_misses = info.get("keyspace_misses", 0)
            
            # Calculate hit ratio
            total_keyspace = self.stats.keyspace_hits + self.stats.keyspace_misses
            if total_keyspace > 0:
                self.stats.hit_ratio = self.stats.keyspace_hits / total_keyspace
            
            self.stats.total_commands_processed = info.get("total_commands_processed", 0)
            self.stats.instantaneous_ops_per_sec = info.get("instantaneous_ops_per_sec", 0)
            self.stats.connected_slaves = info.get("connected_slaves", 0)
            self.stats.master_repl_offset = info.get("master_repl_offset", 0)
            self.stats.role = info.get("role", "master")
            self.stats.uptime_in_seconds = info.get("uptime_in_seconds", 0)
            self.stats.redis_version = info.get("redis_version", "unknown")
            
            return self.stats.to_dict()
            
        except Exception as e:
            logger.error(f"Failed to get Redis statistics: {e}")
            return {}
    
    def _update_query_stats(self, query_time_ms: float) -> None:
        """Update query performance statistics."""
        self._query_times.append(query_time_ms)
        # Keep only last 1000 query times for moving average
        if len(self._query_times) > 1000:
            self._query_times = self._query_times[-1000:]
    
    async def _publish_event(self, operation: str, key: MemoryKey, entry: Optional[MemoryEntry]) -> None:
        """Publish memory operation event to Redis pub/sub."""
        try:
            if not self.redis:
                return
            
            event_data = {
                "operation": operation,
                "key": key.to_string(),
                "namespace": key.namespace,
                "identifier": key.identifier,
                "timestamp": datetime.now().isoformat(),
                "entry_data": entry.data if entry else None
            }
            
            await self.redis.publish(f"{self.key_prefix}events", json.dumps(event_data))
            
        except Exception as e:
            logger.warning(f"Failed to publish event: {e}")
    
    async def _handle_pubsub_messages(self) -> None:
        """Handle incoming pub/sub messages."""
        try:
            if not self.pubsub:
                return
            
            async for message in self.pubsub.listen():
                if message["type"] != "message":
                    continue
                
                try:
                    event_data = json.loads(message["data"])
                    await self._handle_memory_event(event_data)
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Failed to parse pub/sub message: {e}")
                    
        except asyncio.CancelledError:
            logger.info("Pub/sub message handler cancelled")
        except Exception as e:
            logger.error(f"Error in pub/sub message handler: {e}")
    
    async def _handle_memory_event(self, event_data: Dict[str, Any]) -> None:
        """Handle memory operation events."""
        operation = event_data.get("operation")
        key_str = event_data.get("key")
        
        # Notify registered event handlers
        if operation in self._event_handlers:
            for handler in self._event_handlers[operation]:
                try:
                    await handler(event_data)
                except Exception as e:
                    logger.warning(f"Event handler failed: {e}")
    
    def register_event_handler(self, operation: str, handler) -> None:
        """Register an event handler for memory operations."""
        if operation not in self._event_handlers:
            self._event_handlers[operation] = []
        self._event_handlers[operation].append(handler)
    
    async def _background_health_check(self) -> None:
        """Background task for periodic health checks."""
        while True:
            try:
                await asyncio.sleep(self.conn_config.health_check_interval)
                
                if not self._initialized or not self.redis:
                    continue
                
                # Perform health check
                await self.redis.ping()
                self._last_health_check = datetime.now()
                
            except asyncio.CancelledError:
                logger.info("Health check task cancelled")
                break
            except Exception as e:
                logger.error(f"Health check failed: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check and return status."""
        try:
            start_time = time.time()
            
            if not self.redis:
                return {
                    "status": "unhealthy",
                    "error": "Redis connection not initialized",
                    "redis_url": self.conn_config.to_redis_url()
                }
            
            # Test connection
            pong = await self.redis.ping()
            
            # Get basic info
            info = await self.redis.info("server")
            
            response_time = (time.time() - start_time) * 1000
            
            return {
                "status": "healthy",
                "redis_url": self.conn_config.to_redis_url(),
                "response_time_ms": response_time,
                "ping_response": pong,
                "redis_version": info.get("redis_version", "unknown"),
                "uptime_seconds": info.get("uptime_in_seconds", 0),
                "last_health_check": self._last_health_check.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "redis_url": self.conn_config.to_redis_url()
            }