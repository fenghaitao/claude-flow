"""
Memory system interfaces for Claude-Flow

This module defines interfaces for the multi-tier memory system including
repositories, backends, and memory management.
"""

from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from ..core.interfaces import Backend, Repository, BaseComponent


class MemoryTier(Enum):
    """Memory storage tiers"""
    L1_CACHE = "l1_cache"          # In-process cache
    L2_SESSION = "l2_session"      # SQLite session storage
    L3_PERSISTENT = "l3_persistent" # PostgreSQL persistent storage
    L4_DISTRIBUTED = "l4_distributed" # Redis distributed cache


class MemoryType(Enum):
    """Types of memory stored"""
    TASK_MEMORY = "task_memory"
    AGENT_MEMORY = "agent_memory"
    PROJECT_MEMORY = "project_memory"
    NEURAL_MEMORY = "neural_memory"
    PATTERN_MEMORY = "pattern_memory"


@dataclass
class MemoryEntry:
    """Represents a memory entry"""
    id: str
    namespace: str
    memory_type: MemoryType
    content: Any
    embeddings: Optional[List[float]] = None
    relevance_score: float = 0.0
    access_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchQuery:
    """Memory search query parameters"""
    query_text: str
    namespace: Optional[str] = None
    memory_type: Optional[MemoryType] = None
    max_results: int = 10
    min_relevance_score: float = 0.0
    include_metadata: bool = True
    semantic_search: bool = True


@dataclass
class SearchResult:
    """Memory search result"""
    entries: List[MemoryEntry]
    total_count: int
    search_time_ms: float
    query: SearchQuery


class MemoryBackendInterface(Backend):
    """Interface for memory storage backends"""
    
    @abstractmethod
    async def store(self, entry: MemoryEntry) -> bool:
        """Store a memory entry"""
        pass
    
    @abstractmethod
    async def retrieve(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory entry by ID"""
        pass
    
    @abstractmethod
    async def search(self, query: SearchQuery) -> SearchResult:
        """Search for memory entries"""
        pass
    
    @abstractmethod
    async def delete(self, entry_id: str) -> bool:
        """Delete a memory entry"""
        pass
    
    @abstractmethod
    async def update(self, entry: MemoryEntry) -> bool:
        """Update a memory entry"""
        pass
    
    @abstractmethod
    async def cleanup_expired(self) -> int:
        """Clean up expired entries, return count deleted"""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get backend statistics"""
        pass


class MemoryRepositoryInterface(Repository):
    """Interface for memory repositories"""
    
    @abstractmethod
    async def create_memory(self, namespace: str, memory_type: MemoryType, 
                          content: Any, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new memory entry"""
        pass
    
    @abstractmethod
    async def get_memory(self, memory_id: str) -> Optional[MemoryEntry]:
        """Get memory entry by ID"""
        pass
    
    @abstractmethod
    async def search_memories(self, query: SearchQuery) -> SearchResult:
        """Search for memories"""
        pass
    
    @abstractmethod
    async def update_memory(self, memory_id: str, content: Any, 
                          metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update memory content"""
        pass
    
    @abstractmethod
    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory entry"""
        pass
    
    @abstractmethod
    async def list_namespaces(self) -> List[str]:
        """List all available namespaces"""
        pass
    
    @abstractmethod
    async def clear_namespace(self, namespace: str) -> int:
        """Clear all memories in a namespace, return count deleted"""
        pass


class MemoryManagerInterface(BaseComponent):
    """Interface for the main memory manager"""
    
    @abstractmethod
    async def store_memory(self, namespace: str, memory_type: MemoryType,
                         content: Any, tier: Optional[MemoryTier] = None) -> str:
        """Store memory in appropriate tier"""
        pass
    
    @abstractmethod
    async def retrieve_memory(self, memory_id: str, tier: Optional[MemoryTier] = None) -> Optional[MemoryEntry]:
        """Retrieve memory from any tier"""
        pass
    
    @abstractmethod
    async def search_memories(self, query: SearchQuery, tiers: Optional[List[MemoryTier]] = None) -> SearchResult:
        """Search across memory tiers"""
        pass
    
    @abstractmethod
    async def promote_memory(self, memory_id: str, target_tier: MemoryTier) -> bool:
        """Promote memory to higher tier"""
        pass
    
    @abstractmethod
    async def evict_memory(self, memory_id: str) -> bool:
        """Evict memory from all tiers"""
        pass
    
    @abstractmethod
    async def optimize_storage(self) -> Dict[str, Any]:
        """Optimize memory storage across tiers"""
        pass
    
    @abstractmethod
    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics"""
        pass


class SemanticSearchInterface:
    """Interface for semantic search capabilities"""
    
    @abstractmethod
    async def generate_embeddings(self, text: str) -> List[float]:
        """Generate embeddings for text"""
        pass
    
    @abstractmethod
    async def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Compute similarity between embeddings"""
        pass
    
    @abstractmethod
    async def find_similar(self, query_embedding: List[float], 
                         candidate_embeddings: List[List[float]], 
                         threshold: float = 0.7) -> List[int]:
        """Find similar embeddings above threshold"""
        pass


class CacheInterface:
    """Interface for caching operations"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cache entries"""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        pass


class SessionManagerInterface:
    """Interface for session management"""
    
    @abstractmethod
    async def create_session(self, session_data: Dict[str, Any]) -> str:
        """Create a new session"""
        pass
    
    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        pass
    
    @abstractmethod
    async def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Update session data"""
        pass
    
    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        pass
    
    @abstractmethod
    async def list_sessions(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """List sessions"""
        pass
    
    @abstractmethod
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        pass


class PersistenceManagerInterface:
    """Interface for persistence management across tiers"""
    
    @abstractmethod
    async def backup_data(self, backup_path: str) -> bool:
        """Backup all data to specified path"""
        pass
    
    @abstractmethod
    async def restore_data(self, backup_path: str) -> bool:
        """Restore data from backup"""
        pass
    
    @abstractmethod
    async def migrate_data(self, source_tier: MemoryTier, target_tier: MemoryTier) -> int:
        """Migrate data between tiers"""
        pass
    
    @abstractmethod
    async def validate_integrity(self) -> Dict[str, Any]:
        """Validate data integrity across tiers"""
        pass
    
    @abstractmethod
    async def compact_storage(self) -> Dict[str, Any]:
        """Compact storage to reclaim space"""
        pass