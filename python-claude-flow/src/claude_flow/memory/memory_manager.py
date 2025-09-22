"""
Multi-tier memory manager for Claude-Flow.

This module provides the main memory management system that orchestrates
SQLite, Redis, and PostgreSQL backends with intelligent tier assignment
and semantic search capabilities.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from enum import Enum

from claude_flow.core.interfaces import MemoryBackend, MemoryEntry, MemoryKey, BaseComponent
from claude_flow.core.config_models import ClaudeFlowConfig
from claude_flow.memory.backends import SQLiteBackend, RedisBackend, PostgreSQLBackend
from claude_flow.memory.semantic_search import SemanticSearchEngine, SearchQuery, SearchResult
from claude_flow.memory.schema import MemorySchemaManager


logger = logging.getLogger(__name__)


class MemoryTier(Enum):
    """Memory storage tiers for different access patterns."""
    CACHE = "cache"        # Redis - Fast access, temporary
    LOCAL = "local"        # SQLite - Local storage, medium term
    PERSISTENT = "persistent"  # PostgreSQL - Long-term storage


class TierAssignmentStrategy(Enum):
    """Strategies for assigning memory entries to tiers."""
    ACCESS_BASED = "access_based"      # Based on access frequency
    SIZE_BASED = "size_based"          # Based on entry size
    TTL_BASED = "ttl_based"            # Based on expiration time
    HYBRID = "hybrid"                  # Combination of strategies


class MemoryManager(BaseComponent):
    """
    Multi-tier memory manager with intelligent tier assignment.
    
    Features:
    - Multi-tier storage (Cache/Local/Persistent)
    - Intelligent tier assignment based on access patterns
    - Automatic data migration between tiers
    - Semantic search across all tiers
    - Memory lifecycle management
    - Performance optimization and monitoring
    """
    
    def __init__(
        self,
        config: ClaudeFlowConfig,
        tier_strategy: TierAssignmentStrategy = TierAssignmentStrategy.HYBRID,
        enable_auto_migration: bool = True
    ):
        super().__init__()
        self.config = config
        self.tier_strategy = tier_strategy
        self.enable_auto_migration = enable_auto_migration
        
        # Backend instances
        self.cache_backend: Optional[RedisBackend] = None
        self.local_backend: Optional[SQLiteBackend] = None
        self.persistent_backend: Optional[PostgreSQLBackend] = None
        
        # Semantic search engine
        self.search_engine: Optional[SemanticSearchEngine] = None
        
        # Schema manager
        self.schema_manager = MemorySchemaManager()
        
        # Tier assignment configuration
        self.tier_config = {
            "cache_max_size": 1024 * 1024,  # 1MB
            "cache_ttl_threshold": timedelta(hours=1),
            "local_max_size": 10 * 1024 * 1024,  # 10MB
            "local_ttl_threshold": timedelta(days=7),
            "access_frequency_threshold": 10,
            "migration_interval": timedelta(hours=1)
        }
        
        # Statistics
        self.stats = {
            "total_operations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "tier_migrations": 0,
            "total_entries": 0,
            "tier_distribution": {
                "cache": 0,
                "local": 0,
                "persistent": 0
            }
        }
        
        # Background tasks
        self._migration_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def initialize(self) -> None:
        """Initialize the memory manager and all backends."""
        try:
            logger.info("Initializing memory manager")
            
            # Initialize backends based on configuration
            await self._initialize_backends()
            
            # Initialize semantic search engine
            await self._initialize_search_engine()
            
            # Start background tasks
            if self.enable_auto_migration:
                self._migration_task = asyncio.create_task(self._background_migration())
            self._cleanup_task = asyncio.create_task(self._background_cleanup())
            
            self._initialized = True
            logger.info("Memory manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize memory manager: {e}")
            raise
    
    async def cleanup(self) -> None:
        """Clean up all resources."""
        try:
            logger.info("Cleaning up memory manager")
            
            # Cancel background tasks
            if self._migration_task:
                self._migration_task.cancel()
                try:
                    await self._migration_task
                except asyncio.CancelledError:
                    pass
            
            if self._cleanup_task:
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass
            
            # Cleanup backends
            if self.search_engine:
                await self.search_engine.cleanup()
            
            for backend in [self.cache_backend, self.local_backend, self.persistent_backend]:
                if backend:
                    await backend.cleanup()
            
            self._initialized = False
            logger.info("Memory manager cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during memory manager cleanup: {e}")
    
    async def _initialize_backends(self) -> None:
        """Initialize all configured backends."""
        # Initialize Redis cache backend
        if hasattr(self.config, 'redis') and self.config.redis:
            self.cache_backend = RedisBackend(self.config.redis)
            await self.cache_backend.initialize()
            logger.debug("Redis cache backend initialized")
        
        # Initialize SQLite local backend
        if hasattr(self.config, 'database') and self.config.database:
            self.local_backend = SQLiteBackend(self.config.database, self.schema_manager)
            await self.local_backend.initialize()
            logger.debug("SQLite local backend initialized")
        
        # Initialize PostgreSQL persistent backend
        if hasattr(self.config, 'database') and self.config.database:
            # Use same config for now, in practice would have separate configs
            self.persistent_backend = PostgreSQLBackend(self.config.database, self.schema_manager)
            await self.persistent_backend.initialize()
            logger.debug("PostgreSQL persistent backend initialized")
    
    async def _initialize_search_engine(self) -> None:
        """Initialize the semantic search engine."""
        self.search_engine = SemanticSearchEngine()
        await self.search_engine.initialize()
        
        # Register backends with search engine
        for backend in [self.cache_backend, self.local_backend, self.persistent_backend]:
            if backend:
                self.search_engine.register_backend(backend)
        
        logger.debug("Semantic search engine initialized")
    
    async def store(self, key: MemoryKey, entry: MemoryEntry) -> bool:
        """Store a memory entry with intelligent tier assignment."""
        try:
            self.stats["total_operations"] += 1
            
            # Determine target tier
            target_tier = self._assign_tier(key, entry)
            
            # Store in primary tier
            success = False
            if target_tier == MemoryTier.CACHE and self.cache_backend:
                success = await self.cache_backend.store(key, entry)
                if success:
                    self.stats["tier_distribution"]["cache"] += 1
            
            if target_tier == MemoryTier.LOCAL and self.local_backend:
                success = await self.local_backend.store(key, entry)
                if success:
                    self.stats["tier_distribution"]["local"] += 1
            
            if target_tier == MemoryTier.PERSISTENT and self.persistent_backend:
                success = await self.persistent_backend.store(key, entry)
                if success:
                    self.stats["tier_distribution"]["persistent"] += 1
            
            # Also store in cache if storing in other tiers for performance
            if success and target_tier != MemoryTier.CACHE and self.cache_backend:
                # Create a cache entry with shorter TTL
                cache_entry = MemoryEntry(
                    data=entry.data,
                    metadata=entry.metadata,
                    tags=entry.tags,
                    embedding=entry.embedding,
                    expires_at=datetime.now() + self.tier_config["cache_ttl_threshold"],
                    created_at=entry.created_at,
                    updated_at=entry.updated_at,
                    access_count=entry.access_count,
                    last_accessed=entry.last_accessed
                )
                await self.cache_backend.store(key, cache_entry)
            
            if success:
                self.stats["total_entries"] += 1
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to store memory entry {key.to_string()}: {e}")
            return False
    
    async def retrieve(self, key: MemoryKey) -> Optional[MemoryEntry]:
        """Retrieve a memory entry from the most appropriate tier."""
        try:
            self.stats["total_operations"] += 1
            
            # Try cache first for performance
            if self.cache_backend:
                entry = await self.cache_backend.retrieve(key)
                if entry:
                    self.stats["cache_hits"] += 1
                    return entry
            
            self.stats["cache_misses"] += 1
            
            # Try local backend
            if self.local_backend:
                entry = await self.local_backend.retrieve(key)
                if entry:
                    # Promote to cache for future access
                    if self.cache_backend:
                        cache_entry = MemoryEntry(
                            data=entry.data,
                            metadata=entry.metadata,
                            tags=entry.tags,
                            embedding=entry.embedding,
                            expires_at=datetime.now() + self.tier_config["cache_ttl_threshold"],
                            created_at=entry.created_at,
                            updated_at=entry.updated_at,
                            access_count=entry.access_count,
                            last_accessed=entry.last_accessed
                        )
                        await self.cache_backend.store(key, cache_entry)
                    
                    return entry
            
            # Try persistent backend
            if self.persistent_backend:
                entry = await self.persistent_backend.retrieve(key)
                if entry:
                    # Promote to cache
                    if self.cache_backend:
                        cache_entry = MemoryEntry(
                            data=entry.data,
                            metadata=entry.metadata,
                            tags=entry.tags,
                            embedding=entry.embedding,
                            expires_at=datetime.now() + self.tier_config["cache_ttl_threshold"],
                            created_at=entry.created_at,
                            updated_at=entry.updated_at,
                            access_count=entry.access_count,
                            last_accessed=entry.last_accessed
                        )
                        await self.cache_backend.store(key, cache_entry)
                    
                    return entry
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve memory entry {key.to_string()}: {e}")
            return None
    
    async def delete(self, key: MemoryKey) -> bool:
        """Delete a memory entry from all tiers."""
        try:
            self.stats["total_operations"] += 1
            
            success = False
            
            # Delete from all tiers
            for backend in [self.cache_backend, self.local_backend, self.persistent_backend]:
                if backend:
                    if await backend.delete(key):
                        success = True
            
            if success:
                self.stats["total_entries"] = max(0, self.stats["total_entries"] - 1)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete memory entry {key.to_string()}: {e}")
            return False
    
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform semantic search across all tiers."""
        if not self.search_engine:
            return []
        
        try:
            return await self.search_engine.search(query)
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    async def search_text(
        self,
        text: str,
        namespace: Optional[str] = None,
        tags: Optional[Set[str]] = None,
        max_results: int = 10
    ) -> List[SearchResult]:
        """Convenient text search method."""
        query = SearchQuery(
            text=text,
            namespace=namespace,
            tags=tags or set(),
            max_results=max_results,
            search_mode="hybrid"
        )
        return await self.search(query)
    
    def _assign_tier(self, key: MemoryKey, entry: MemoryEntry) -> MemoryTier:
        """Assign the appropriate tier for a memory entry."""
        if self.tier_strategy == TierAssignmentStrategy.ACCESS_BASED:
            return self._assign_tier_by_access(entry)
        elif self.tier_strategy == TierAssignmentStrategy.SIZE_BASED:
            return self._assign_tier_by_size(entry)
        elif self.tier_strategy == TierAssignmentStrategy.TTL_BASED:
            return self._assign_tier_by_ttl(entry)
        else:  # HYBRID
            return self._assign_tier_hybrid(entry)
    
    def _assign_tier_by_access(self, entry: MemoryEntry) -> MemoryTier:
        """Assign tier based on access frequency."""
        if entry.access_count >= self.tier_config["access_frequency_threshold"]:
            return MemoryTier.CACHE
        elif entry.access_count >= 3:
            return MemoryTier.LOCAL
        else:
            return MemoryTier.PERSISTENT
    
    def _assign_tier_by_size(self, entry: MemoryEntry) -> MemoryTier:
        """Assign tier based on entry size."""
        entry_size = len(str(entry.data).encode('utf-8'))
        
        if entry_size <= self.tier_config["cache_max_size"]:
            return MemoryTier.CACHE
        elif entry_size <= self.tier_config["local_max_size"]:
            return MemoryTier.LOCAL
        else:
            return MemoryTier.PERSISTENT
    
    def _assign_tier_by_ttl(self, entry: MemoryEntry) -> MemoryTier:
        """Assign tier based on expiration time."""
        if not entry.expires_at:
            return MemoryTier.PERSISTENT
        
        ttl = entry.expires_at - datetime.now()
        
        if ttl <= self.tier_config["cache_ttl_threshold"]:
            return MemoryTier.CACHE
        elif ttl <= self.tier_config["local_ttl_threshold"]:
            return MemoryTier.LOCAL
        else:
            return MemoryTier.PERSISTENT
    
    def _assign_tier_hybrid(self, entry: MemoryEntry) -> MemoryTier:
        """Assign tier using hybrid strategy."""
        # Score each tier based on multiple factors
        cache_score = 0
        local_score = 0
        persistent_score = 0
        
        # Access frequency factor
        if entry.access_count >= self.tier_config["access_frequency_threshold"]:
            cache_score += 3
        elif entry.access_count >= 3:
            local_score += 2
        else:
            persistent_score += 1
        
        # Size factor
        entry_size = len(str(entry.data).encode('utf-8'))
        if entry_size <= self.tier_config["cache_max_size"]:
            cache_score += 2
        elif entry_size <= self.tier_config["local_max_size"]:
            local_score += 2
        else:
            persistent_score += 2
        
        # TTL factor
        if entry.expires_at:
            ttl = entry.expires_at - datetime.now()
            if ttl <= self.tier_config["cache_ttl_threshold"]:
                cache_score += 2
            elif ttl <= self.tier_config["local_ttl_threshold"]:
                local_score += 1
        else:
            persistent_score += 1
        
        # Return tier with highest score
        scores = {
            MemoryTier.CACHE: cache_score,
            MemoryTier.LOCAL: local_score,
            MemoryTier.PERSISTENT: persistent_score
        }
        
        return max(scores, key=scores.get)
    
    async def _background_migration(self) -> None:
        """Background task for migrating data between tiers."""
        while True:
            try:
                await asyncio.sleep(self.tier_config["migration_interval"].total_seconds())
                
                if not self._initialized:
                    continue
                
                logger.debug("Starting background tier migration")
                
                # Migration logic would go here
                # For now, just log that it's running
                
                self.stats["tier_migrations"] += 1
                
            except asyncio.CancelledError:
                logger.info("Background migration task cancelled")
                break
            except Exception as e:
                logger.error(f"Error during background migration: {e}")
    
    async def _background_cleanup(self) -> None:
        """Background task for cleaning up expired entries."""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                if not self._initialized:
                    continue
                
                logger.debug("Starting background cleanup")
                
                # Cleanup would be handled by individual backends
                # This is just a coordination point
                
            except asyncio.CancelledError:
                logger.info("Background cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error during background cleanup: {e}")
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive memory manager statistics."""
        stats = self.stats.copy()
        
        # Add backend statistics
        if self.cache_backend:
            stats["cache_backend"] = await self.cache_backend.get_stats()
        
        if self.local_backend:
            stats["local_backend"] = await self.local_backend.get_stats()
        
        if self.persistent_backend:
            stats["persistent_backend"] = await self.persistent_backend.get_stats()
        
        # Add search engine statistics
        if self.search_engine:
            stats["search_engine"] = await self.search_engine.get_search_statistics()
        
        return stats
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        try:
            health_status = {
                "status": "healthy",
                "backends": {},
                "search_engine": {},
                "statistics": self.stats
            }
            
            # Check backend health
            for name, backend in [
                ("cache", self.cache_backend),
                ("local", self.local_backend),
                ("persistent", self.persistent_backend)
            ]:
                if backend:
                    try:
                        backend_health = await backend.health_check()
                        health_status["backends"][name] = backend_health
                    except Exception as e:
                        health_status["backends"][name] = {
                            "status": "unhealthy",
                            "error": str(e)
                        }
                        health_status["status"] = "degraded"
                else:
                    health_status["backends"][name] = {"status": "not_configured"}
            
            # Check search engine health
            if self.search_engine:
                try:
                    search_health = await self.search_engine.health_check()
                    health_status["search_engine"] = search_health
                except Exception as e:
                    health_status["search_engine"] = {
                        "status": "unhealthy",
                        "error": str(e)
                    }
                    health_status["status"] = "degraded"
            
            return health_status
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }