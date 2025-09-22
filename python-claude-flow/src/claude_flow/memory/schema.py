"""
Multi-Tier Memory System Schema Design for Claude-Flow

This module defines the database schemas and data models for the multi-tier
memory system supporting SQLite, Redis, and PostgreSQL backends.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Tuple
from enum import Enum
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import json
import uuid
import hashlib

from ..core.interfaces import BaseComponent
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MemoryTier(Enum):
    """Memory tier types"""
    LOCAL = "local"          # SQLite - fast local access
    DISTRIBUTED = "distributed"  # Redis - shared cache
    PERSISTENT = "persistent"    # PostgreSQL - long-term storage


class MemoryType(Enum):
    """Memory content types"""
    TASK_CONTEXT = "task_context"
    AGENT_STATE = "agent_state"
    SESSION_DATA = "session_data"
    LEARNING_DATA = "learning_data"
    PATTERN_DATA = "pattern_data"
    CONVERSATION = "conversation"
    KNOWLEDGE_BASE = "knowledge_base"
    METRICS = "metrics"
    CACHE = "cache"


class AccessPattern(Enum):
    """Memory access patterns"""
    READ_HEAVY = "read_heavy"
    WRITE_HEAVY = "write_heavy"
    BALANCED = "balanced"
    SEQUENTIAL = "sequential"
    RANDOM = "random"
    TEMPORAL = "temporal"


@dataclass
class MemoryKey:
    """Memory key structure"""
    namespace: str
    entity_type: str
    entity_id: str
    version: Optional[int] = None
    
    def to_string(self) -> str:
        """Convert to string representation"""
        parts = [self.namespace, self.entity_type, self.entity_id]
        if self.version is not None:
            parts.append(str(self.version))
        return ":".join(parts)
    
    @classmethod
    def from_string(cls, key_str: str) -> 'MemoryKey':
        """Create from string representation"""
        parts = key_str.split(":")
        if len(parts) < 3:
            raise ValueError(f"Invalid memory key format: {key_str}")
        
        namespace, entity_type, entity_id = parts[:3]
        version = int(parts[3]) if len(parts) > 3 else None
        
        return cls(namespace, entity_type, entity_id, version)


@dataclass
class MemoryMetadata:
    """Memory metadata"""
    created_at: datetime
    updated_at: datetime
    accessed_at: datetime
    access_count: int
    size_bytes: int
    ttl: Optional[timedelta]
    tags: List[str] = field(default_factory=list)
    priority: int = 1  # 1-10 scale
    compression: Optional[str] = None
    encryption: bool = False


class MemoryEntry(BaseModel):
    """Memory entry data model"""
    key: str
    content: Dict[str, Any]
    memory_type: MemoryType
    tier: MemoryTier
    metadata: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    class Config:
        arbitrary_types_allowed = True


class DatabaseSchema:
    """
    Database schema definitions for multi-tier memory system
    
    Provides schema definitions for SQLite, Redis, and PostgreSQL
    with optimizations for different access patterns and data types.
    """
    
    # SQLite schema for local memory
    SQLITE_SCHEMAS = {
        "memory_entries": """
            CREATE TABLE IF NOT EXISTS memory_entries (
                key TEXT PRIMARY KEY,
                namespace TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                version INTEGER,
                content TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                tier TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                accessed_at TEXT,
                access_count INTEGER DEFAULT 0,
                expires_at TEXT,
                size_bytes INTEGER,
                checksum TEXT
            )
        """,
        
        "memory_indexes": """
            CREATE INDEX IF NOT EXISTS idx_memory_namespace ON memory_entries(namespace);
            CREATE INDEX IF NOT EXISTS idx_memory_entity_type ON memory_entries(entity_type);
            CREATE INDEX IF NOT EXISTS idx_memory_entity_id ON memory_entries(entity_id);
            CREATE INDEX IF NOT EXISTS idx_memory_type ON memory_entries(memory_type);
            CREATE INDEX IF NOT EXISTS idx_memory_created_at ON memory_entries(created_at);
            CREATE INDEX IF NOT EXISTS idx_memory_updated_at ON memory_entries(updated_at);
            CREATE INDEX IF NOT EXISTS idx_memory_expires_at ON memory_entries(expires_at);
        """,
        
        "memory_relations": """
            CREATE TABLE IF NOT EXISTS memory_relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_key TEXT NOT NULL,
                target_key TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                strength REAL DEFAULT 1.0,
                created_at TEXT NOT NULL,
                metadata TEXT,
                FOREIGN KEY (source_key) REFERENCES memory_entries (key),
                FOREIGN KEY (target_key) REFERENCES memory_entries (key)
            )
        """,
        
        "memory_relations_indexes": """
            CREATE INDEX IF NOT EXISTS idx_relations_source ON memory_relations(source_key);
            CREATE INDEX IF NOT EXISTS idx_relations_target ON memory_relations(target_key);
            CREATE INDEX IF NOT EXISTS idx_relations_type ON memory_relations(relation_type);
        """,
        
        "memory_tags": """
            CREATE TABLE IF NOT EXISTS memory_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_key TEXT NOT NULL,
                tag TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (memory_key) REFERENCES memory_entries (key),
                UNIQUE(memory_key, tag)
            )
        """,
        
        "memory_tags_indexes": """
            CREATE INDEX IF NOT EXISTS idx_tags_memory_key ON memory_tags(memory_key);
            CREATE INDEX IF NOT EXISTS idx_tags_tag ON memory_tags(tag);
        """,
        
        "memory_access_log": """
            CREATE TABLE IF NOT EXISTS memory_access_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_key TEXT NOT NULL,
                operation TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                source TEXT,
                duration_ms INTEGER,
                success BOOLEAN DEFAULT TRUE,
                error_message TEXT,
                FOREIGN KEY (memory_key) REFERENCES memory_entries (key)
            )
        """,
        
        "memory_access_log_indexes": """
            CREATE INDEX IF NOT EXISTS idx_access_log_key ON memory_access_log(memory_key);
            CREATE INDEX IF NOT EXISTS idx_access_log_timestamp ON memory_access_log(timestamp);
            CREATE INDEX IF NOT EXISTS idx_access_log_operation ON memory_access_log(operation);
        """
    }
    
    # PostgreSQL schema for persistent memory
    POSTGRESQL_SCHEMAS = {
        "memory_entries": """
            CREATE TABLE IF NOT EXISTS memory_entries (
                key VARCHAR(255) PRIMARY KEY,
                namespace VARCHAR(100) NOT NULL,
                entity_type VARCHAR(100) NOT NULL,
                entity_id VARCHAR(255) NOT NULL,
                version INTEGER,
                content JSONB NOT NULL,
                memory_type VARCHAR(50) NOT NULL,
                tier VARCHAR(20) NOT NULL,
                metadata JSONB,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                accessed_at TIMESTAMPTZ,
                access_count INTEGER DEFAULT 0,
                expires_at TIMESTAMPTZ,
                size_bytes INTEGER,
                checksum VARCHAR(64),
                search_vector TSVECTOR
            )
        """,
        
        "memory_indexes": """
            CREATE INDEX IF NOT EXISTS idx_memory_namespace ON memory_entries(namespace);
            CREATE INDEX IF NOT EXISTS idx_memory_entity_type ON memory_entries(entity_type);
            CREATE INDEX IF NOT EXISTS idx_memory_entity_id ON memory_entries(entity_id);
            CREATE INDEX IF NOT EXISTS idx_memory_type ON memory_entries(memory_type);
            CREATE INDEX IF NOT EXISTS idx_memory_created_at ON memory_entries(created_at);
            CREATE INDEX IF NOT EXISTS idx_memory_updated_at ON memory_entries(updated_at);
            CREATE INDEX IF NOT EXISTS idx_memory_expires_at ON memory_entries(expires_at);
            CREATE INDEX IF NOT EXISTS idx_memory_content_gin ON memory_entries USING GIN(content);
            CREATE INDEX IF NOT EXISTS idx_memory_metadata_gin ON memory_entries USING GIN(metadata);
            CREATE INDEX IF NOT EXISTS idx_memory_search_gin ON memory_entries USING GIN(search_vector);
        """,
        
        "memory_partitions": """
            -- Partition by memory type for better performance
            CREATE TABLE IF NOT EXISTS memory_entries_task_context 
            PARTITION OF memory_entries FOR VALUES IN ('task_context');
            
            CREATE TABLE IF NOT EXISTS memory_entries_agent_state 
            PARTITION OF memory_entries FOR VALUES IN ('agent_state');
            
            CREATE TABLE IF NOT EXISTS memory_entries_session_data 
            PARTITION OF memory_entries FOR VALUES IN ('session_data');
            
            CREATE TABLE IF NOT EXISTS memory_entries_learning_data 
            PARTITION OF memory_entries FOR VALUES IN ('learning_data');
        """,
        
        "memory_relations": """
            CREATE TABLE IF NOT EXISTS memory_relations (
                id SERIAL PRIMARY KEY,
                source_key VARCHAR(255) NOT NULL,
                target_key VARCHAR(255) NOT NULL,
                relation_type VARCHAR(50) NOT NULL,
                strength REAL DEFAULT 1.0,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                metadata JSONB,
                FOREIGN KEY (source_key) REFERENCES memory_entries (key) ON DELETE CASCADE,
                FOREIGN KEY (target_key) REFERENCES memory_entries (key) ON DELETE CASCADE
            )
        """,
        
        "memory_relations_indexes": """
            CREATE INDEX IF NOT EXISTS idx_relations_source ON memory_relations(source_key);
            CREATE INDEX IF NOT EXISTS idx_relations_target ON memory_relations(target_key);
            CREATE INDEX IF NOT EXISTS idx_relations_type ON memory_relations(relation_type);
            CREATE INDEX IF NOT EXISTS idx_relations_strength ON memory_relations(strength);
        """,
        
        "memory_embeddings": """
            CREATE TABLE IF NOT EXISTS memory_embeddings (
                memory_key VARCHAR(255) PRIMARY KEY,
                embedding_model VARCHAR(100) NOT NULL,
                embedding_vector VECTOR(1536), -- OpenAI embedding dimension
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                FOREIGN KEY (memory_key) REFERENCES memory_entries (key) ON DELETE CASCADE
            )
        """,
        
        "memory_embeddings_indexes": """
            CREATE INDEX IF NOT EXISTS idx_embeddings_model ON memory_embeddings(embedding_model);
            CREATE INDEX IF NOT EXISTS idx_embeddings_vector_cosine ON memory_embeddings 
            USING ivfflat (embedding_vector vector_cosine_ops);
        """,
        
        "memory_statistics": """
            CREATE TABLE IF NOT EXISTS memory_statistics (
                id SERIAL PRIMARY KEY,
                namespace VARCHAR(100),
                memory_type VARCHAR(50),
                tier VARCHAR(20),
                total_entries INTEGER,
                total_size_bytes BIGINT,
                avg_access_frequency REAL,
                cache_hit_rate REAL,
                last_calculated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(namespace, memory_type, tier)
            )
        """,
        
        "memory_triggers": """
            -- Trigger to update search vector when content changes
            CREATE OR REPLACE FUNCTION update_memory_search_vector()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.search_vector := to_tsvector('english', 
                    COALESCE(NEW.content->>'title', '') || ' ' ||
                    COALESCE(NEW.content->>'description', '') || ' ' ||
                    COALESCE(NEW.content->>'content', '')
                );
                NEW.updated_at := NOW();
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            
            DROP TRIGGER IF EXISTS memory_search_vector_update ON memory_entries;
            CREATE TRIGGER memory_search_vector_update
                BEFORE INSERT OR UPDATE ON memory_entries
                FOR EACH ROW EXECUTE FUNCTION update_memory_search_vector();
        """
    }
    
    # Redis data structures
    REDIS_STRUCTURES = {
        "memory_entry": {
            "description": "Hash structure for memory entries",
            "fields": [
                "content",          # JSON serialized content
                "memory_type",      # Memory type
                "created_at",       # Creation timestamp
                "updated_at",       # Update timestamp
                "expires_at",       # Expiration timestamp
                "access_count",     # Access counter
                "size_bytes",       # Content size
                "checksum"          # Content checksum
            ]
        },
        
        "memory_namespace": {
            "description": "Set of memory keys per namespace",
            "pattern": "namespace:{namespace}"
        },
        
        "memory_type_index": {
            "description": "Set of memory keys per type",
            "pattern": "type:{memory_type}"
        },
        
        "memory_expiry": {
            "description": "Sorted set for expiry tracking",
            "pattern": "expiry:*",
            "score": "expires_at timestamp"
        },
        
        "memory_access_frequency": {
            "description": "Sorted set for LRU/LFU tracking",
            "pattern": "frequency:*",
            "score": "access_count or last_accessed"
        },
        
        "memory_relations": {
            "description": "Hash for memory relations",
            "pattern": "relations:{source_key}",
            "fields": ["target_key", "relation_type", "strength"]
        }
    }


class MemorySchemaManager(BaseComponent):
    """
    Memory Schema Manager
    
    Manages database schemas across different tiers of the memory system.
    Handles schema creation, migration, and optimization for each backend.
    """
    
    def __init__(self):
        super().__init__()
        self.schema_versions = {
            "sqlite": "1.0.0",
            "postgresql": "1.0.0", 
            "redis": "1.0.0"
        }
        
        # Schema migration tracking
        self.migrations_applied = {}
        
    async def _start_implementation(self) -> None:
        """Start the schema manager"""
        logger.info("Memory Schema Manager started")
    
    async def _stop_implementation(self) -> None:
        """Stop the schema manager"""
        logger.info("Memory Schema Manager stopped")
    
    async def _health_check_implementation(self) -> Dict[str, Any]:
        """Health check for schema manager"""
        return {
            "schema_versions": self.schema_versions,
            "migrations_applied": len(self.migrations_applied)
        }
    
    async def initialize_sqlite_schema(self, db_path: str) -> bool:
        """Initialize SQLite schema"""
        try:
            import aiosqlite
            
            async with aiosqlite.connect(db_path) as db:
                # Create tables and indexes
                for name, schema in DatabaseSchema.SQLITE_SCHEMAS.items():
                    try:
                        await db.executescript(schema)
                        logger.debug(f"Created SQLite schema component: {name}")
                    except Exception as e:
                        logger.error(f"Failed to create SQLite schema {name}: {e}")
                        return False
                
                await db.commit()
                
                # Create schema version tracking
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS schema_version (
                        component TEXT PRIMARY KEY,
                        version TEXT NOT NULL,
                        applied_at TEXT NOT NULL
                    )
                """)
                
                await db.execute("""
                    INSERT OR REPLACE INTO schema_version (component, version, applied_at)
                    VALUES ('memory_system', ?, ?)
                """, (self.schema_versions["sqlite"], datetime.now().isoformat()))
                
                await db.commit()
            
            logger.info(f"SQLite memory schema initialized: {db_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize SQLite schema: {e}")
            return False
    
    async def initialize_postgresql_schema(self, connection_config: Dict[str, Any]) -> bool:
        """Initialize PostgreSQL schema"""
        try:
            import asyncpg
            
            # Create connection
            conn = await asyncpg.connect(**connection_config)
            
            try:
                # Enable required extensions
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
                await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
                
                # Create schemas and indexes
                for name, schema in DatabaseSchema.POSTGRESQL_SCHEMAS.items():
                    try:
                        await conn.execute(schema)
                        logger.debug(f"Created PostgreSQL schema component: {name}")
                    except Exception as e:
                        logger.error(f"Failed to create PostgreSQL schema {name}: {e}")
                        return False
                
                # Create schema version tracking
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS schema_version (
                        component VARCHAR(100) PRIMARY KEY,
                        version VARCHAR(20) NOT NULL,
                        applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """)
                
                await conn.execute("""
                    INSERT INTO schema_version (component, version) 
                    VALUES ('memory_system', $1)
                    ON CONFLICT (component) DO UPDATE SET 
                        version = EXCLUDED.version,
                        applied_at = NOW()
                """, self.schema_versions["postgresql"])
                
            finally:
                await conn.close()
            
            logger.info("PostgreSQL memory schema initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL schema: {e}")
            return False
    
    async def initialize_redis_structures(self, redis_config: Dict[str, Any]) -> bool:
        """Initialize Redis data structures"""
        try:
            import redis.asyncio as redis
            
            # Create Redis connection
            redis_client = redis.Redis(**redis_config)
            
            try:
                # Test connection
                await redis_client.ping()
                
                # Initialize structure documentation (as metadata)
                structures_doc = json.dumps(DatabaseSchema.REDIS_STRUCTURES, indent=2)
                await redis_client.set("memory:schema:structures", structures_doc)
                
                # Set schema version
                await redis_client.set("memory:schema:version", self.schema_versions["redis"])
                
            finally:
                await redis_client.aclose()
            
            logger.info("Redis memory structures initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis structures: {e}")
            return False
    
    def get_memory_key_structure(self, namespace: str, entity_type: str, entity_id: str) -> MemoryKey:
        """Generate standardized memory key"""
        return MemoryKey(
            namespace=namespace,
            entity_type=entity_type,
            entity_id=entity_id
        )
    
    def calculate_tier_assignment(self, memory_type: MemoryType, 
                                access_pattern: AccessPattern,
                                data_size: int,
                                retention_days: Optional[int] = None) -> MemoryTier:
        """Calculate optimal memory tier assignment"""
        
        # Tier assignment heuristics
        if memory_type in [MemoryType.CACHE, MemoryType.METRICS]:
            return MemoryTier.DISTRIBUTED  # Redis for cache and metrics
        
        if access_pattern == AccessPattern.READ_HEAVY and data_size < 1024 * 1024:  # < 1MB
            return MemoryTier.LOCAL  # SQLite for small, frequently read data
        
        if access_pattern == AccessPattern.WRITE_HEAVY:
            return MemoryTier.DISTRIBUTED  # Redis for high-write scenarios
        
        if retention_days and retention_days > 30:
            return MemoryTier.PERSISTENT  # PostgreSQL for long-term storage
        
        if data_size > 10 * 1024 * 1024:  # > 10MB
            return MemoryTier.PERSISTENT  # PostgreSQL for large data
        
        # Default to local tier
        return MemoryTier.LOCAL
    
    def optimize_schema_for_workload(self, workload_pattern: Dict[str, Any]) -> Dict[str, Any]:
        """Generate schema optimization recommendations"""
        recommendations = {
            "sqlite": [],
            "postgresql": [],
            "redis": []
        }
        
        # Analyze workload patterns
        read_ratio = workload_pattern.get("read_ratio", 0.7)
        write_ratio = workload_pattern.get("write_ratio", 0.3)
        data_size_avg = workload_pattern.get("avg_data_size", 1024)
        access_frequency = workload_pattern.get("access_frequency", "medium")
        
        # SQLite optimizations
        if read_ratio > 0.8:
            recommendations["sqlite"].append("Enable WAL mode for better read concurrency")
            recommendations["sqlite"].append("Increase cache_size pragma")
        
        if data_size_avg > 1024 * 1024:  # > 1MB
            recommendations["sqlite"].append("Consider page_size optimization")
        
        # PostgreSQL optimizations
        if write_ratio > 0.5:
            recommendations["postgresql"].append("Tune checkpoint settings for write-heavy workloads")
            recommendations["postgresql"].append("Consider increasing shared_buffers")
        
        if access_frequency == "high":
            recommendations["postgresql"].append("Enable connection pooling")
            recommendations["postgresql"].append("Optimize vacuum settings")
        
        # Redis optimizations
        recommendations["redis"].append("Configure appropriate eviction policy")
        recommendations["redis"].append("Set optimal maxmemory based on workload")
        
        return recommendations
    
    def generate_migration_script(self, from_version: str, to_version: str, 
                                backend: str) -> List[str]:
        """Generate database migration scripts"""
        migrations = []
        
        # This would contain actual migration logic
        # For now, return placeholder migrations
        if backend == "sqlite":
            migrations.append("-- SQLite migration placeholder")
        elif backend == "postgresql":
            migrations.append("-- PostgreSQL migration placeholder")
        elif backend == "redis":
            migrations.append("-- Redis migration placeholder")
        
        return migrations
    
    def validate_schema_compatibility(self, backend: str, version: str) -> bool:
        """Validate schema compatibility"""
        current_version = self.schema_versions.get(backend)
        if not current_version:
            return False
        
        # Simple version comparison (in practice, use semantic versioning)
        return version == current_version
    
    def get_schema_statistics(self) -> Dict[str, Any]:
        """Get schema statistics"""
        return {
            "schema_versions": self.schema_versions,
            "supported_backends": ["sqlite", "postgresql", "redis"],
            "total_tables": {
                "sqlite": len([k for k in DatabaseSchema.SQLITE_SCHEMAS.keys() if not k.endswith("_indexes")]),
                "postgresql": len([k for k in DatabaseSchema.POSTGRESQL_SCHEMAS.keys() if not k.endswith("_indexes")])
            },
            "redis_structures": len(DatabaseSchema.REDIS_STRUCTURES)
        }