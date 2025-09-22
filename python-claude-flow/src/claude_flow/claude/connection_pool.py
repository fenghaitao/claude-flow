"""
Connection Pool for Claude AI Client

Provides connection pooling capabilities for the Claude AI client with support for:
- Async connection management
- Connection reuse and recycling
- Pool size management
- Health monitoring
- Connection timeouts
"""

import asyncio
import time
from typing import Optional, Dict, Any, List, Set
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
import logging
from anthropic import AsyncAnthropic

from ..core.interfaces import BaseComponent
from ..config.models import ClaudeConfig


@dataclass
class ConnectionInfo:
    """Information about a pooled connection."""
    client: AsyncAnthropic
    created_at: float
    last_used: float
    in_use: bool = False
    use_count: int = 0
    max_uses: int = 1000  # Recycle after this many uses


class ConnectionPool(BaseComponent):
    """Async connection pool for Claude AI clients."""
    
    def __init__(self, config: ClaudeConfig):
        super().__init__()
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Pool configuration
        self.min_size = config.connection_pool.get('min_size', 2)
        self.max_size = config.connection_pool.get('max_size', 10)
        self.max_idle_time = config.connection_pool.get('max_idle_time', 300)  # 5 minutes
        self.max_connection_age = config.connection_pool.get('max_connection_age', 3600)  # 1 hour
        
        # Pool state
        self._available: asyncio.Queue[ConnectionInfo] = asyncio.Queue()
        self._in_use: Set[ConnectionInfo] = set()
        self._total_connections = 0
        self._lock = asyncio.Lock()
        
        # Monitoring
        self._stats = {
            'created': 0,
            'reused': 0,
            'recycled': 0,
            'timeouts': 0,
            'errors': 0
        }
        
        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        """Initialize the connection pool."""
        await super().initialize()
        
        # Create initial connections
        for _ in range(self.min_size):
            conn_info = await self._create_connection()
            await self._available.put(conn_info)
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        self.logger.info(f"Initialized connection pool with {self.min_size} connections")
    
    async def shutdown(self) -> None:
        """Shutdown the connection pool."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        async with self._lock:
            # Close available connections
            while not self._available.empty():
                conn_info = await self._available.get()
                await self._close_connection(conn_info)
            
            # Close in-use connections (they should be returned by now)
            for conn_info in list(self._in_use):
                await self._close_connection(conn_info)
        
        await super().shutdown()
        self.logger.info("Connection pool shutdown complete")
    
    @asynccontextmanager
    async def get_connection(self, timeout: Optional[float] = None):
        """Get a connection from the pool."""
        conn_info = None
        try:
            conn_info = await self._acquire_connection(timeout)
            yield conn_info.client
        finally:
            if conn_info:
                await self._release_connection(conn_info)
    
    async def _acquire_connection(self, timeout: Optional[float] = None) -> ConnectionInfo:
        """Acquire a connection from the pool."""
        deadline = time.time() + (timeout or 30.0)
        
        while time.time() < deadline:
            # Try to get an available connection
            try:
                conn_info = self._available.get_nowait()
                
                # Check if connection is still valid
                if await self._is_connection_valid(conn_info):
                    async with self._lock:
                        self._in_use.add(conn_info)
                        conn_info.in_use = True
                        conn_info.last_used = time.time()
                        conn_info.use_count += 1
                        self._stats['reused'] += 1
                    
                    return conn_info
                else:
                    # Connection is invalid, close it
                    await self._close_connection(conn_info)
                    continue
                    
            except asyncio.QueueEmpty:
                # No available connections, try to create a new one
                async with self._lock:
                    if self._total_connections < self.max_size:
                        try:
                            conn_info = await self._create_connection()
                            self._in_use.add(conn_info)
                            conn_info.in_use = True
                            conn_info.last_used = time.time()
                            conn_info.use_count += 1
                            return conn_info
                        except Exception as e:
                            self._stats['errors'] += 1
                            self.logger.error(f"Failed to create connection: {e}")
                            raise
            
            # Wait a bit before retrying
            await asyncio.sleep(0.1)
        
        self._stats['timeouts'] += 1
        raise asyncio.TimeoutError("Failed to acquire connection within timeout")
    
    async def _release_connection(self, conn_info: ConnectionInfo) -> None:
        """Release a connection back to the pool."""
        async with self._lock:
            if conn_info in self._in_use:
                self._in_use.remove(conn_info)
                conn_info.in_use = False
                
                # Check if connection should be recycled
                if await self._should_recycle_connection(conn_info):
                    await self._close_connection(conn_info)
                    self._stats['recycled'] += 1
                else:
                    # Return to available pool
                    await self._available.put(conn_info)
    
    async def _create_connection(self) -> ConnectionInfo:
        """Create a new connection."""
        client = AsyncAnthropic(
            api_key=self.config.api_key,
            timeout=self.config.timeout,
            max_retries=0  # We handle retries at a higher level
        )
        
        conn_info = ConnectionInfo(
            client=client,
            created_at=time.time(),
            last_used=time.time()
        )
        
        self._total_connections += 1
        self._stats['created'] += 1
        
        return conn_info
    
    async def _close_connection(self, conn_info: ConnectionInfo) -> None:
        """Close a connection."""
        try:
            # Anthropic client doesn't have explicit close method
            # The connection will be closed when the client is garbage collected
            pass
        except Exception as e:
            self.logger.warning(f"Error closing connection: {e}")
        finally:
            self._total_connections -= 1
    
    async def _is_connection_valid(self, conn_info: ConnectionInfo) -> bool:
        """Check if a connection is still valid."""
        now = time.time()
        
        # Check age
        if now - conn_info.created_at > self.max_connection_age:
            return False
        
        # Check idle time
        if now - conn_info.last_used > self.max_idle_time:
            return False
        
        # Check use count
        if conn_info.use_count >= conn_info.max_uses:
            return False
        
        return True
    
    async def _should_recycle_connection(self, conn_info: ConnectionInfo) -> bool:
        """Check if a connection should be recycled."""
        return not await self._is_connection_valid(conn_info)
    
    async def _cleanup_loop(self) -> None:
        """Periodic cleanup of expired connections."""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                await self._cleanup_expired_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
    
    async def _cleanup_expired_connections(self) -> None:
        """Remove expired connections from the pool."""
        expired_connections = []
        
        # Check available connections
        temp_available = []
        while not self._available.empty():
            try:
                conn_info = self._available.get_nowait()
                if await self._is_connection_valid(conn_info):
                    temp_available.append(conn_info)
                else:
                    expired_connections.append(conn_info)
            except asyncio.QueueEmpty:
                break
        
        # Put valid connections back
        for conn_info in temp_available:
            await self._available.put(conn_info)
        
        # Close expired connections
        for conn_info in expired_connections:
            await self._close_connection(conn_info)
            self._stats['recycled'] += 1
        
        if expired_connections:
            self.logger.debug(f"Cleaned up {len(expired_connections)} expired connections")
        
        # Ensure minimum pool size
        async with self._lock:
            current_available = self._available.qsize()
            needed = max(0, self.min_size - current_available - len(self._in_use))
            
            for _ in range(needed):
                if self._total_connections < self.max_size:
                    try:
                        conn_info = await self._create_connection()
                        await self._available.put(conn_info)
                    except Exception as e:
                        self.logger.error(f"Failed to create connection during cleanup: {e}")
                        break
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        return {
            'total_connections': self._total_connections,
            'available_connections': self._available.qsize(),
            'in_use_connections': len(self._in_use),
            'min_size': self.min_size,
            'max_size': self.max_size,
            **self._stats
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the connection pool."""
        stats = self.get_stats()
        
        health_status = {
            'status': 'healthy',
            'pool_stats': stats,
            'issues': []
        }
        
        # Check for issues
        if stats['total_connections'] == 0:
            health_status['status'] = 'unhealthy'
            health_status['issues'].append('No connections available')
        
        if stats['available_connections'] == 0 and stats['in_use_connections'] >= self.max_size:
            health_status['status'] = 'degraded'
            health_status['issues'].append('Pool at maximum capacity')
        
        error_rate = stats['errors'] / max(1, stats['created'] + stats['reused'])
        if error_rate > 0.1:  # More than 10% error rate
            health_status['status'] = 'degraded'
            health_status['issues'].append(f'High error rate: {error_rate:.2%}')
        
        return health_status