"""
Memory system for Claude-Flow

This module provides multi-tier memory management:
- Memory repositories for data access
- Backend integrations (SQLite, Redis, PostgreSQL)
- Semantic search and retrieval capabilities
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .memory_manager import MemoryManager, MemoryTier, TierAssignmentStrategy
    from .semantic_search import SemanticSearchEngine, SearchQuery, SearchResult, EmbeddingProvider
    from .schema import MemorySchemaManager, DatabaseSchema
    from .repositories.session_repository import SessionRepository
    from .repositories.agent_repository import AgentRepository
    from .backends.sqlite_backend import SQLiteBackend
    from .backends.redis_backend import RedisBackend
    from .backends.postgresql_backend import PostgreSQLBackend

__all__ = [
    "MemoryManager",
    "MemoryTier", 
    "TierAssignmentStrategy",
    "SemanticSearchEngine",
    "SearchQuery",
    "SearchResult",
    "EmbeddingProvider",
    "MemorySchemaManager",
    "DatabaseSchema",
    "SessionRepository",
    "AgentRepository", 
    "SQLiteBackend",
    "RedisBackend",
    "PostgreSQLBackend",
]

# Lazy imports to avoid circular dependencies
def __getattr__(name: str):
    if name == "MemoryManager":
        from .memory_manager import MemoryManager
        return MemoryManager
    elif name == "MemoryTier":
        from .memory_manager import MemoryTier
        return MemoryTier
    elif name == "TierAssignmentStrategy":
        from .memory_manager import TierAssignmentStrategy
        return TierAssignmentStrategy
    elif name == "SemanticSearchEngine":
        from .semantic_search import SemanticSearchEngine
        return SemanticSearchEngine
    elif name == "SearchQuery":
        from .semantic_search import SearchQuery
        return SearchQuery
    elif name == "SearchResult":
        from .semantic_search import SearchResult
        return SearchResult
    elif name == "EmbeddingProvider":
        from .semantic_search import EmbeddingProvider
        return EmbeddingProvider
    elif name == "MemorySchemaManager":
        from .schema import MemorySchemaManager
        return MemorySchemaManager
    elif name == "DatabaseSchema":
        from .schema import DatabaseSchema
        return DatabaseSchema
    elif name == "SessionRepository":
        from .repositories.session_repository import SessionRepository
        return SessionRepository
    elif name == "AgentRepository":
        from .repositories.agent_repository import AgentRepository
        return AgentRepository
    elif name == "SQLiteBackend":
        from .backends.sqlite_backend import SQLiteBackend
        return SQLiteBackend
    elif name == "RedisBackend":
        from .backends.redis_backend import RedisBackend
        return RedisBackend
    elif name == "PostgreSQLBackend":
        from .backends.postgresql_backend import PostgreSQLBackend
        return PostgreSQLBackend
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")