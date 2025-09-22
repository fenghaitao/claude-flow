"""
Semantic search and memory retrieval system for Claude-Flow.

This module provides advanced semantic search capabilities with support for
vector similarity, hybrid search combining text and semantic matching,
and intelligent query expansion and refinement.
"""

import asyncio
import json
import logging
import math
import numpy as np
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

from claude_flow.core.interfaces import MemoryBackend, MemoryEntry, MemoryKey, BaseComponent
from claude_flow.core.config_models import ClaudeFlowConfig


logger = logging.getLogger(__name__)


@dataclass
class SearchQuery:
    """Represents a search query with multiple search modes."""
    text: str = ""
    embedding: Optional[List[float]] = None
    namespace: Optional[str] = None
    tags: Set[str] = field(default_factory=set)
    date_range: Optional[Tuple[datetime, datetime]] = None
    min_access_count: int = 0
    max_results: int = 10
    include_expired: bool = False
    search_mode: str = "hybrid"  # "text", "semantic", "hybrid"
    boost_recent: bool = True
    boost_frequent: bool = True


@dataclass
class SearchResult:
    """Represents a search result with relevance scoring."""
    key: MemoryKey
    entry: MemoryEntry
    relevance_score: float
    text_score: float = 0.0
    semantic_score: float = 0.0
    recency_score: float = 0.0
    frequency_score: float = 0.0
    tag_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "key": self.key.to_string(),
            "relevance_score": self.relevance_score,
            "text_score": self.text_score,
            "semantic_score": self.semantic_score,
            "recency_score": self.recency_score,
            "frequency_score": self.frequency_score,
            "tag_score": self.tag_score,
            "entry_summary": {
                "created_at": self.entry.created_at.isoformat(),
                "updated_at": self.entry.updated_at.isoformat(),
                "access_count": self.entry.access_count,
                "tags": list(self.entry.tags)
            }
        }


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""
    
    @abstractmethod
    async def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for the given text."""
        pass
    
    @abstractmethod
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        pass


class SimpleEmbeddingProvider(EmbeddingProvider):
    """Simple embedding provider using basic text features."""
    
    def __init__(self, dimensions: int = 384):
        self.dimensions = dimensions
    
    async def get_embedding(self, text: str) -> List[float]:
        """Generate a simple hash-based embedding."""
        # Simple feature extraction (in real implementation, use proper embeddings)
        words = text.lower().split()
        embedding = [0.0] * self.dimensions
        
        for i, word in enumerate(words):
            hash_val = hash(word) % self.dimensions
            embedding[hash_val] += 1.0 / (i + 1)  # Position weighting
        
        # Normalize
        norm = math.sqrt(sum(x * x for x in embedding))
        if norm > 0:
            embedding = [x / norm for x in embedding]
        
        return embedding
    
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        return [await self.get_embedding(text) for text in texts]


class SemanticSearchEngine(BaseComponent):
    """
    Advanced semantic search engine for memory retrieval.
    
    Features:
    - Hybrid text and semantic search
    - Vector similarity computation
    - Query expansion and refinement
    - Multi-backend search coordination
    - Relevance scoring with multiple factors
    - Search result ranking and filtering
    """
    
    def __init__(
        self,
        embedding_provider: Optional[EmbeddingProvider] = None,
        similarity_threshold: float = 0.7,
        max_query_expansion: int = 5
    ):
        super().__init__()
        self.embedding_provider = embedding_provider or SimpleEmbeddingProvider()
        self.similarity_threshold = similarity_threshold
        self.max_query_expansion = max_query_expansion
        
        # Search backends (will be registered)
        self.backends: List[MemoryBackend] = []
        
        # Search statistics
        self._search_count = 0
        self._avg_search_time = 0.0
        self._cache_hits = 0
        
        # Query cache (simple in-memory cache)
        self._query_cache: Dict[str, Tuple[List[SearchResult], datetime]] = {}
        self._cache_ttl = timedelta(minutes=10)
        
    async def initialize(self) -> None:
        """Initialize the semantic search engine."""
        self._initialized = True
        logger.info("Semantic search engine initialized")
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        self._query_cache.clear()
        self._initialized = False
        logger.info("Semantic search engine cleaned up")
    
    def register_backend(self, backend: MemoryBackend) -> None:
        """Register a memory backend for searching."""
        if backend not in self.backends:
            self.backends.append(backend)
            logger.debug(f"Registered backend: {type(backend).__name__}")
    
    def unregister_backend(self, backend: MemoryBackend) -> None:
        """Unregister a memory backend."""
        if backend in self.backends:
            self.backends.remove(backend)
            logger.debug(f"Unregistered backend: {type(backend).__name__}")
    
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform semantic search across all registered backends."""
        start_time = datetime.now()
        
        try:
            # Check cache first
            cache_key = self._get_cache_key(query)
            cached_results = self._get_cached_results(cache_key)
            if cached_results:
                self._cache_hits += 1
                return cached_results
            
            # Generate embedding for semantic search if needed
            if query.search_mode in ("semantic", "hybrid") and not query.embedding:
                if query.text:
                    query.embedding = await self.embedding_provider.get_embedding(query.text)
            
            # Search across all backends
            all_results = []
            
            for backend in self.backends:
                try:
                    backend_results = await self._search_backend(backend, query)
                    all_results.extend(backend_results)
                except Exception as e:
                    logger.warning(f"Backend search failed for {type(backend).__name__}: {e}")
            
            # Remove duplicates (same key from different backends)
            unique_results = self._deduplicate_results(all_results)
            
            # Score and rank results
            scored_results = await self._score_results(unique_results, query)
            
            # Sort by relevance score
            scored_results.sort(key=lambda r: r.relevance_score, reverse=True)
            
            # Apply limit
            final_results = scored_results[:query.max_results]
            
            # Cache results
            self._cache_results(cache_key, final_results)
            
            # Update statistics
            search_time = (datetime.now() - start_time).total_seconds()
            self._update_search_stats(search_time)
            
            logger.debug(f"Search completed: {len(final_results)} results in {search_time:.3f}s")
            return final_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    async def _search_backend(self, backend: MemoryBackend, query: SearchQuery) -> List[Tuple[MemoryKey, MemoryEntry, float]]:
        """Search a specific backend."""
        # Convert SearchQuery to backend-specific parameters
        search_tags = query.tags if query.tags else None
        
        # Use backend's search method
        results = await backend.search(
            query=query.text,
            namespace=query.namespace,
            tags=search_tags,
            limit=query.max_results * 2,  # Get more for better ranking
            offset=0
        )
        
        # Filter results based on query criteria
        filtered_results = []
        for key, entry, score in results:
            # Date range filter
            if query.date_range:
                start_date, end_date = query.date_range
                if not (start_date <= entry.created_at <= end_date):
                    continue
            
            # Access count filter
            if entry.access_count < query.min_access_count:
                continue
            
            # Expiration filter
            if not query.include_expired and entry.expires_at:
                if datetime.now() > entry.expires_at:
                    continue
            
            filtered_results.append((key, entry, score))
        
        return filtered_results
    
    def _deduplicate_results(self, results: List[Tuple[MemoryKey, MemoryEntry, float]]) -> List[Tuple[MemoryKey, MemoryEntry, float]]:
        """Remove duplicate results based on memory key."""
        seen_keys = set()
        unique_results = []
        
        for key, entry, score in results:
            key_str = key.to_string()
            if key_str not in seen_keys:
                seen_keys.add(key_str)
                unique_results.append((key, entry, score))
        
        return unique_results
    
    async def _score_results(self, results: List[Tuple[MemoryKey, MemoryEntry, float]], query: SearchQuery) -> List[SearchResult]:
        """Score and rank search results."""
        scored_results = []
        
        for key, entry, initial_score in results:
            # Text search score (from backend)
            text_score = initial_score if query.search_mode in ("text", "hybrid") else 0.0
            
            # Semantic similarity score
            semantic_score = 0.0
            if query.search_mode in ("semantic", "hybrid") and query.embedding and entry.embedding:
                semantic_score = self._cosine_similarity(query.embedding, entry.embedding)
            
            # Recency score
            recency_score = 0.0
            if query.boost_recent:
                days_old = (datetime.now() - entry.created_at).days
                recency_score = max(0.0, 1.0 - (days_old / 365.0))  # Decay over a year
            
            # Frequency score
            frequency_score = 0.0
            if query.boost_frequent:
                frequency_score = min(1.0, entry.access_count / 100.0)  # Cap at 100 accesses
            
            # Tag matching score
            tag_score = 0.0
            if query.tags and entry.tags:
                matching_tags = query.tags.intersection(entry.tags)
                tag_score = len(matching_tags) / len(query.tags) if query.tags else 0.0
            
            # Combined relevance score
            relevance_score = self._calculate_relevance_score(
                text_score, semantic_score, recency_score, frequency_score, tag_score, query
            )
            
            result = SearchResult(
                key=key,
                entry=entry,
                relevance_score=relevance_score,
                text_score=text_score,
                semantic_score=semantic_score,
                recency_score=recency_score,
                frequency_score=frequency_score,
                tag_score=tag_score
            )
            
            scored_results.append(result)
        
        return scored_results
    
    def _calculate_relevance_score(
        self,
        text_score: float,
        semantic_score: float,
        recency_score: float,
        frequency_score: float,
        tag_score: float,
        query: SearchQuery
    ) -> float:
        """Calculate the final relevance score."""
        # Weight factors based on search mode
        if query.search_mode == "text":
            weights = {"text": 0.8, "semantic": 0.0, "recency": 0.1, "frequency": 0.05, "tag": 0.05}
        elif query.search_mode == "semantic":
            weights = {"text": 0.0, "semantic": 0.8, "recency": 0.1, "frequency": 0.05, "tag": 0.05}
        else:  # hybrid
            weights = {"text": 0.4, "semantic": 0.4, "recency": 0.1, "frequency": 0.05, "tag": 0.05}
        
        # Apply boosts
        if not query.boost_recent:
            weights["recency"] = 0.0
        if not query.boost_frequent:
            weights["frequency"] = 0.0
        
        # Normalize weights
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}
        
        # Calculate weighted score
        relevance_score = (
            weights["text"] * text_score +
            weights["semantic"] * semantic_score +
            weights["recency"] * recency_score +
            weights["frequency"] * frequency_score +
            weights["tag"] * tag_score
        )
        
        return relevance_score
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        try:
            if len(vec1) != len(vec2):
                return 0.0
            
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            norm1 = math.sqrt(sum(a * a for a in vec1))
            norm2 = math.sqrt(sum(a * a for a in vec2))
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return dot_product / (norm1 * norm2)
            
        except Exception:
            return 0.0
    
    def _get_cache_key(self, query: SearchQuery) -> str:
        """Generate cache key for query."""
        key_data = {
            "text": query.text,
            "namespace": query.namespace,
            "tags": sorted(list(query.tags)) if query.tags else [],
            "search_mode": query.search_mode,
            "max_results": query.max_results,
            "min_access_count": query.min_access_count,
            "include_expired": query.include_expired,
            "boost_recent": query.boost_recent,
            "boost_frequent": query.boost_frequent
        }
        
        if query.date_range:
            key_data["date_range"] = [
                query.date_range[0].isoformat(),
                query.date_range[1].isoformat()
            ]
        
        return str(hash(json.dumps(key_data, sort_keys=True)))
    
    def _get_cached_results(self, cache_key: str) -> Optional[List[SearchResult]]:
        """Get cached search results if valid."""
        if cache_key in self._query_cache:
            results, cached_at = self._query_cache[cache_key]
            if datetime.now() - cached_at < self._cache_ttl:
                return results
            else:
                # Remove expired cache entry
                del self._query_cache[cache_key]
        
        return None
    
    def _cache_results(self, cache_key: str, results: List[SearchResult]) -> None:
        """Cache search results."""
        self._query_cache[cache_key] = (results, datetime.now())
        
        # Clean up old cache entries (simple LRU-like cleanup)
        if len(self._query_cache) > 1000:
            # Remove oldest 20% of entries
            sorted_entries = sorted(
                self._query_cache.items(),
                key=lambda x: x[1][1]
            )
            
            for key, _ in sorted_entries[:200]:
                del self._query_cache[key]
    
    def _update_search_stats(self, search_time: float) -> None:
        """Update search performance statistics."""
        self._search_count += 1
        self._avg_search_time = (
            (self._avg_search_time * (self._search_count - 1) + search_time) / self._search_count
        )
    
    async def suggest_query_expansion(self, query: str) -> List[str]:
        """Suggest query expansions based on related terms."""
        # Simple query expansion (in real implementation, use proper NLP)
        words = query.lower().split()
        suggestions = []
        
        # Add synonyms or related terms (placeholder implementation)
        synonym_map = {
            "code": ["programming", "script", "function", "algorithm"],
            "error": ["bug", "issue", "problem", "exception"],
            "data": ["information", "content", "record", "entry"],
            "user": ["person", "individual", "account", "profile"],
            "system": ["application", "platform", "service", "infrastructure"]
        }
        
        for word in words:
            if word in synonym_map:
                suggestions.extend(synonym_map[word][:2])  # Add up to 2 synonyms
        
        return suggestions[:self.max_query_expansion]
    
    async def get_search_statistics(self) -> Dict[str, Any]:
        """Get search engine statistics."""
        return {
            "total_searches": self._search_count,
            "avg_search_time_seconds": self._avg_search_time,
            "cache_size": len(self._query_cache),
            "cache_hits": self._cache_hits,
            "cache_hit_ratio": self._cache_hits / max(1, self._search_count),
            "registered_backends": len(self.backends),
            "backend_types": [type(backend).__name__ for backend in self.backends]
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            # Test embedding generation
            test_embedding = await self.embedding_provider.get_embedding("test")
            
            # Test backend connectivity
            backend_health = []
            for backend in self.backends:
                try:
                    if hasattr(backend, 'health_check'):
                        backend_status = await backend.health_check()
                        backend_health.append({
                            "backend": type(backend).__name__,
                            "status": backend_status.get("status", "unknown")
                        })
                    else:
                        backend_health.append({
                            "backend": type(backend).__name__,
                            "status": "no_health_check"
                        })
                except Exception as e:
                    backend_health.append({
                        "backend": type(backend).__name__,
                        "status": "unhealthy",
                        "error": str(e)
                    })
            
            return {
                "status": "healthy",
                "embedding_provider": type(self.embedding_provider).__name__,
                "embedding_dimensions": len(test_embedding),
                "backends": backend_health,
                "cache_size": len(self._query_cache),
                "total_searches": self._search_count
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }