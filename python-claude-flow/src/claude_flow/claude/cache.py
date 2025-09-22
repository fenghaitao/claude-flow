"""
Response Cache and Token Management for Claude AI Client

Provides intelligent caching and token management with:
- LRU cache with TTL support
- Token usage tracking and estimation
- Cache invalidation strategies
- Persistent cache storage
- Token optimization
"""

import asyncio
import hashlib
import json
import time
import sqlite3
from typing import Optional, Dict, Any, List, Tuple, Union
from dataclasses import dataclass, field, asdict
from collections import OrderedDict
from datetime import datetime, timedelta
import logging
import aiosqlite

from ..core.interfaces import BaseComponent


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    data: Any
    created_at: float
    last_accessed: float
    access_count: int = 0
    ttl: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl
    
    def size_estimate(self) -> int:
        """Estimate memory size of the cache entry."""
        return len(json.dumps(self.data, default=str).encode('utf-8'))


@dataclass
class TokenUsage:
    """Token usage tracking."""
    input_tokens: int
    output_tokens: int
    total_tokens: int
    model: str
    timestamp: float
    request_id: Optional[str] = None
    cached: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class LRUCache:
    """LRU cache with TTL support."""
    
    def __init__(self, max_size: int = 1000, default_ttl: Optional[float] = None):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._total_size = 0
        self._max_memory_mb = 500  # 500MB max memory usage
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        
        # Check if expired
        if entry.is_expired():
            self.delete(key)
            return None
        
        # Update access info
        entry.last_accessed = time.time()
        entry.access_count += 1
        
        # Move to end (most recently used)
        self._cache.move_to_end(key)
        
        return entry.data
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None, metadata: Optional[Dict] = None) -> None:
        """Set value in cache."""
        now = time.time()
        ttl = ttl or self.default_ttl
        
        # Create cache entry
        entry = CacheEntry(
            key=key,
            data=value,
            created_at=now,
            last_accessed=now,
            ttl=ttl,
            metadata=metadata or {}
        )
        
        # Remove old entry if exists
        if key in self._cache:
            old_entry = self._cache[key]
            self._total_size -= old_entry.size_estimate()
            del self._cache[key]
        
        # Add new entry
        self._cache[key] = entry
        self._total_size += entry.size_estimate()
        
        # Enforce size limits
        self._enforce_limits()
    
    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        if key in self._cache:
            entry = self._cache[key]
            self._total_size -= entry.size_estimate()
            del self._cache[key]
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._total_size = 0
    
    def _enforce_limits(self) -> None:
        """Enforce cache size and memory limits."""
        # Remove expired entries first
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        for key in expired_keys:
            self.delete(key)
        
        # Enforce max size (LRU eviction)
        while len(self._cache) > self.max_size:
            oldest_key = next(iter(self._cache))
            self.delete(oldest_key)
        
        # Enforce memory limit
        max_memory_bytes = self._max_memory_mb * 1024 * 1024
        while self._total_size > max_memory_bytes and self._cache:
            oldest_key = next(iter(self._cache))
            self.delete(oldest_key)
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_access_count = sum(entry.access_count for entry in self._cache.values())
        
        return {
            'size': len(self._cache),
            'max_size': self.max_size,
            'memory_usage_mb': self._total_size / (1024 * 1024),
            'max_memory_mb': self._max_memory_mb,
            'total_access_count': total_access_count,
            'hit_rate': 0.0,  # Will be calculated by ResponseCache
            'expired_entries': sum(1 for entry in self._cache.values() if entry.is_expired())
        }


class ResponseCache(BaseComponent):
    """Intelligent response cache with persistence and token management."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Cache configuration
        self.max_size = self.config.get('max_size', 1000)
        self.default_ttl = self.config.get('default_ttl', 3600)  # 1 hour
        self.enable_persistence = self.config.get('enable_persistence', True)
        self.db_path = self.config.get('db_path', 'claude_cache.db')
        
        # In-memory cache
        self.cache = LRUCache(self.max_size, self.default_ttl)
        
        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'tokens_saved': 0,
            'requests_cached': 0
        }
        
        # Database connection
        self.db: Optional[aiosqlite.Connection] = None
    
    async def initialize(self) -> None:
        """Initialize the cache."""
        await super().initialize()
        
        if self.enable_persistence:
            await self._init_database()
            await self._load_from_database()
        
        self.logger.info(f"Response cache initialized with {len(self.cache._cache)} entries")
    
    async def shutdown(self) -> None:
        """Shutdown the cache."""
        if self.enable_persistence and self.db:
            await self._save_to_database()
            await self.db.close()
        
        await super().shutdown()
        self.logger.info("Response cache shutdown")
    
    async def _init_database(self) -> None:
        """Initialize SQLite database for persistence."""
        self.db = await aiosqlite.connect(self.db_path)
        
        await self.db.execute('''
            CREATE TABLE IF NOT EXISTS cache_entries (
                key TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at REAL NOT NULL,
                last_accessed REAL NOT NULL,
                access_count INTEGER DEFAULT 0,
                ttl REAL,
                metadata TEXT
            )
        ''')
        
        await self.db.execute('''
            CREATE TABLE IF NOT EXISTS token_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model TEXT NOT NULL,
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                total_tokens INTEGER NOT NULL,
                timestamp REAL NOT NULL,
                request_id TEXT,
                cached INTEGER DEFAULT 0
            )
        ''')
        
        await self.db.commit()
    
    async def _load_from_database(self) -> None:
        """Load cache entries from database."""
        if not self.db:
            return
        
        cursor = await self.db.execute('''
            SELECT key, data, created_at, last_accessed, access_count, ttl, metadata
            FROM cache_entries
            WHERE (ttl IS NULL OR (? - created_at) < ttl)
            ORDER BY last_accessed DESC
            LIMIT ?
        ''', (time.time(), self.max_size))
        
        rows = await cursor.fetchall()
        
        for row in rows:
            key, data_json, created_at, last_accessed, access_count, ttl, metadata_json = row
            
            try:
                data = json.loads(data_json)
                metadata = json.loads(metadata_json) if metadata_json else {}
                
                entry = CacheEntry(
                    key=key,
                    data=data,
                    created_at=created_at,
                    last_accessed=last_accessed,
                    access_count=access_count,
                    ttl=ttl,
                    metadata=metadata
                )
                
                if not entry.is_expired():
                    self.cache._cache[key] = entry
                    self.cache._total_size += entry.size_estimate()
                
            except (json.JSONDecodeError, Exception) as e:
                self.logger.warning(f"Failed to load cache entry {key}: {e}")
    
    async def _save_to_database(self) -> None:
        """Save cache entries to database."""
        if not self.db:
            return
        
        # Clear old entries
        await self.db.execute('DELETE FROM cache_entries')
        
        # Save current entries
        for entry in self.cache._cache.values():
            if not entry.is_expired():
                await self.db.execute('''
                    INSERT INTO cache_entries 
                    (key, data, created_at, last_accessed, access_count, ttl, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    entry.key,
                    json.dumps(entry.data, default=str),
                    entry.created_at,
                    entry.last_accessed,
                    entry.access_count,
                    entry.ttl,
                    json.dumps(entry.metadata)
                ))
        
        await self.db.commit()
    
    def _generate_cache_key(self, request_data: Dict[str, Any]) -> str:
        """Generate cache key from request data."""
        # Normalize request data for consistent caching
        normalized = {
            'model': request_data.get('model'),
            'messages': request_data.get('messages'),
            'temperature': request_data.get('temperature'),
            'max_tokens': request_data.get('max_tokens'),
            'system': request_data.get('system')
        }
        
        # Create hash of normalized data
        data_str = json.dumps(normalized, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode('utf-8')).hexdigest()
    
    async def get(self, request_data: Dict[str, Any]) -> Optional[Any]:
        """Get cached response for request."""
        cache_key = self._generate_cache_key(request_data)
        result = self.cache.get(cache_key)
        
        if result is not None:
            self.stats['hits'] += 1
            # Track tokens saved
            if 'usage' in result:
                self.stats['tokens_saved'] += result['usage'].get('total_tokens', 0)
        else:
            self.stats['misses'] += 1
        
        return result
    
    async def set(self, request_data: Dict[str, Any], response_data: Any, 
                 ttl: Optional[float] = None) -> None:
        """Cache response for request."""
        cache_key = self._generate_cache_key(request_data)
        
        # Add caching metadata
        metadata = {
            'model': request_data.get('model'),
            'cached_at': time.time(),
            'request_hash': cache_key[:16]  # Short hash for debugging
        }
        
        self.cache.set(cache_key, response_data, ttl, metadata)
        self.stats['sets'] += 1
        self.stats['requests_cached'] += 1
    
    async def delete(self, request_data: Dict[str, Any]) -> bool:
        """Delete cached response."""
        cache_key = self._generate_cache_key(request_data)
        deleted = self.cache.delete(cache_key)
        
        if deleted:
            self.stats['deletes'] += 1
        
        return deleted
    
    async def clear(self) -> None:
        """Clear all cached responses."""
        self.cache.clear()
        
        if self.enable_persistence and self.db:
            await self.db.execute('DELETE FROM cache_entries')
            await self.db.commit()
        
        # Reset stats except historical data
        cache_stats = ['hits', 'misses', 'sets', 'deletes']
        for stat in cache_stats:
            self.stats[stat] = 0
    
    async def record_token_usage(self, usage: TokenUsage) -> None:
        """Record token usage for analytics."""
        if self.enable_persistence and self.db:
            await self.db.execute('''
                INSERT INTO token_usage 
                (model, input_tokens, output_tokens, total_tokens, timestamp, request_id, cached)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                usage.model,
                usage.input_tokens,
                usage.output_tokens,
                usage.total_tokens,
                usage.timestamp,
                usage.request_id,
                1 if usage.cached else 0
            ))
            await self.db.commit()
    
    async def get_token_usage_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get token usage statistics."""
        if not self.enable_persistence or not self.db:
            return {'error': 'Persistence not enabled'}
        
        cutoff_time = time.time() - (hours * 3600)
        
        # Total usage
        cursor = await self.db.execute('''
            SELECT 
                SUM(input_tokens) as total_input,
                SUM(output_tokens) as total_output,
                SUM(total_tokens) as total_tokens,
                COUNT(*) as total_requests,
                SUM(CASE WHEN cached = 1 THEN total_tokens ELSE 0 END) as cached_tokens,
                SUM(CASE WHEN cached = 1 THEN 1 ELSE 0 END) as cached_requests
            FROM token_usage 
            WHERE timestamp >= ?
        ''', (cutoff_time,))
        
        row = await cursor.fetchone()
        total_input, total_output, total_tokens, total_requests, cached_tokens, cached_requests = row
        
        # Usage by model
        cursor = await self.db.execute('''
            SELECT model, SUM(total_tokens) as tokens, COUNT(*) as requests
            FROM token_usage 
            WHERE timestamp >= ?
            GROUP BY model
            ORDER BY tokens DESC
        ''', (cutoff_time,))
        
        model_usage = await cursor.fetchall()
        
        # Calculate savings
        token_savings = cached_tokens or 0
        request_savings = cached_requests or 0
        savings_rate = token_savings / max(1, total_tokens or 0)
        
        return {
            'period_hours': hours,
            'total_usage': {
                'input_tokens': total_input or 0,
                'output_tokens': total_output or 0,
                'total_tokens': total_tokens or 0,
                'total_requests': total_requests or 0
            },
            'cache_savings': {
                'tokens_saved': token_savings,
                'requests_cached': request_savings,
                'savings_rate': savings_rate,
                'estimated_cost_savings': self._estimate_cost_savings(token_savings)
            },
            'model_breakdown': [
                {'model': model, 'tokens': tokens, 'requests': requests}
                for model, tokens, requests in model_usage
            ]
        }
    
    def _estimate_cost_savings(self, tokens_saved: int) -> Dict[str, float]:
        """Estimate cost savings from cached tokens."""
        # Rough cost estimates (per 1M tokens)
        cost_estimates = {
            'claude-3-5-sonnet-20241022': {'input': 3.0, 'output': 15.0},
            'claude-3-5-haiku-20241022': {'input': 0.25, 'output': 1.25},
            'claude-3-opus-20240229': {'input': 15.0, 'output': 75.0},
            'default': {'input': 3.0, 'output': 15.0}
        }
        
        # Assume 50/50 split between input and output tokens
        input_tokens = tokens_saved * 0.5
        output_tokens = tokens_saved * 0.5
        
        default_cost = cost_estimates['default']
        input_cost_saved = (input_tokens / 1_000_000) * default_cost['input']
        output_cost_saved = (output_tokens / 1_000_000) * default_cost['output']
        
        return {
            'total_usd': input_cost_saved + output_cost_saved,
            'input_usd': input_cost_saved,
            'output_usd': output_cost_saved
        }
    
    async def optimize_cache(self) -> Dict[str, Any]:
        """Optimize cache by removing less useful entries."""
        initial_size = len(self.cache._cache)
        
        # Remove expired entries
        expired_keys = [
            key for key, entry in self.cache._cache.items()
            if entry.is_expired()
        ]
        for key in expired_keys:
            self.cache.delete(key)
        
        # Remove least accessed entries if over capacity
        if len(self.cache._cache) > self.max_size * 0.8:  # 80% threshold
            entries_by_access = sorted(
                self.cache._cache.items(),
                key=lambda x: (x[1].access_count, x[1].last_accessed)
            )
            
            # Remove bottom 20%
            to_remove = int(len(entries_by_access) * 0.2)
            for key, _ in entries_by_access[:to_remove]:
                self.cache.delete(key)
        
        final_size = len(self.cache._cache)
        
        return {
            'initial_size': initial_size,
            'final_size': final_size,
            'removed_expired': len(expired_keys),
            'removed_lru': initial_size - final_size - len(expired_keys),
            'memory_usage_mb': self.cache._total_size / (1024 * 1024)
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        hit_rate = 0.0
        total_requests = self.stats['hits'] + self.stats['misses']
        if total_requests > 0:
            hit_rate = self.stats['hits'] / total_requests
        
        return {
            **self.stats.copy(),
            'hit_rate': hit_rate,
            'total_requests': total_requests,
            'cache_stats': self.cache.stats(),
            'persistence_enabled': self.enable_persistence
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the cache."""
        stats = self.get_stats()
        cache_stats = stats['cache_stats']
        
        health_status = {
            'status': 'healthy',
            'cache_size': cache_stats['size'],
            'memory_usage_mb': cache_stats['memory_usage_mb'],
            'hit_rate': stats['hit_rate'],
            'issues': []
        }
        
        # Check for issues
        if cache_stats['memory_usage_mb'] > cache_stats['max_memory_mb'] * 0.9:
            health_status['status'] = 'degraded'
            health_status['issues'].append('High memory usage')
        
        if stats['hit_rate'] < 0.1 and stats['total_requests'] > 100:
            health_status['status'] = 'degraded'
            health_status['issues'].append('Low cache hit rate')
        
        if self.enable_persistence and not self.db:
            health_status['status'] = 'degraded'
            health_status['issues'].append('Database connection lost')
        
        return health_status