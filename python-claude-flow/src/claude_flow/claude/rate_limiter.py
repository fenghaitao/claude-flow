"""
Rate Limiter for Claude AI Client

Provides rate limiting capabilities with support for:
- Token bucket algorithm
- Sliding window rate limiting
- Per-model rate limits
- Burst handling
- Backoff strategies
"""

import asyncio
import time
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
import logging

from ..core.interfaces import BaseComponent
from ..config.models import ClaudeConfig


@dataclass
class RateLimit:
    """Rate limit configuration."""
    requests_per_minute: int
    tokens_per_minute: int
    burst_allowance: float = 1.5  # Allow 50% burst above normal rate


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""
    capacity: float
    tokens: float
    refill_rate: float  # tokens per second
    last_refill: float = field(default_factory=time.time)
    
    def consume(self, tokens: float) -> bool:
        """Attempt to consume tokens from the bucket."""
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def _refill(self) -> None:
        """Refill the bucket based on time elapsed."""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
    
    def time_until_tokens(self, tokens: float) -> float:
        """Calculate time until enough tokens are available."""
        self._refill()
        
        if self.tokens >= tokens:
            return 0.0
        
        needed = tokens - self.tokens
        return needed / self.refill_rate


@dataclass
class SlidingWindow:
    """Sliding window for tracking request history."""
    window_size: int  # seconds
    max_requests: int
    requests: deque = field(default_factory=deque)
    
    def can_make_request(self) -> bool:
        """Check if a request can be made within the window."""
        now = time.time()
        cutoff = now - self.window_size
        
        # Remove old requests
        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()
        
        return len(self.requests) < self.max_requests
    
    def record_request(self) -> None:
        """Record a new request."""
        now = time.time()
        cutoff = now - self.window_size
        
        # Clean old requests
        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()
        
        self.requests.append(now)
    
    def time_until_available(self) -> float:
        """Calculate time until a slot becomes available."""
        if self.can_make_request():
            return 0.0
        
        if not self.requests:
            return 0.0
        
        oldest_request = self.requests[0]
        return oldest_request + self.window_size - time.time()


class RateLimiter(BaseComponent):
    """Advanced rate limiter for Claude AI requests."""
    
    def __init__(self, config: ClaudeConfig):
        super().__init__()
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Rate limits per model
        self.rate_limits = self._get_rate_limits()
        
        # Token buckets for each model
        self.request_buckets: Dict[str, TokenBucket] = {}
        self.token_buckets: Dict[str, TokenBucket] = {}
        
        # Sliding windows for burst protection
        self.sliding_windows: Dict[str, SlidingWindow] = {}
        
        # Statistics
        self.stats = defaultdict(lambda: {
            'requests_made': 0,
            'requests_limited': 0,
            'tokens_consumed': 0,
            'total_wait_time': 0.0
        })
        
        # Initialize buckets and windows
        self._initialize_limiters()
    
    def _get_rate_limits(self) -> Dict[str, RateLimit]:
        """Get rate limits for different models."""
        defaults = {
            'claude-3-5-sonnet-20241022': RateLimit(1000, 40000),
            'claude-3-5-haiku-20241022': RateLimit(2000, 50000),
            'claude-3-opus-20240229': RateLimit(500, 20000),
            'claude-3-sonnet-20240229': RateLimit(1000, 40000),
            'claude-3-haiku-20240307': RateLimit(2000, 50000),
            'default': RateLimit(1000, 40000)
        }
        
        # Override with config values if provided
        config_limits = self.config.rate_limits or {}
        for model, limits in config_limits.items():
            if isinstance(limits, dict):
                defaults[model] = RateLimit(
                    requests_per_minute=limits.get('requests_per_minute', 1000),
                    tokens_per_minute=limits.get('tokens_per_minute', 40000),
                    burst_allowance=limits.get('burst_allowance', 1.5)
                )
        
        return defaults
    
    def _initialize_limiters(self) -> None:
        """Initialize token buckets and sliding windows."""
        for model, rate_limit in self.rate_limits.items():
            # Request rate limiting (token bucket)
            self.request_buckets[model] = TokenBucket(
                capacity=rate_limit.requests_per_minute * rate_limit.burst_allowance,
                tokens=rate_limit.requests_per_minute * rate_limit.burst_allowance,
                refill_rate=rate_limit.requests_per_minute / 60.0
            )
            
            # Token rate limiting (token bucket)
            self.token_buckets[model] = TokenBucket(
                capacity=rate_limit.tokens_per_minute * rate_limit.burst_allowance,
                tokens=rate_limit.tokens_per_minute * rate_limit.burst_allowance,
                refill_rate=rate_limit.tokens_per_minute / 60.0
            )
            
            # Sliding window for burst protection
            self.sliding_windows[model] = SlidingWindow(
                window_size=60,  # 1 minute window
                max_requests=rate_limit.requests_per_minute
            )
    
    async def acquire(self, model: str, estimated_tokens: int = 1000) -> None:
        """
        Acquire permission to make a request.
        
        Args:
            model: The model being used
            estimated_tokens: Estimated number of tokens for the request
        """
        # Use default limits if model not found
        if model not in self.rate_limits:
            model = 'default'
        
        start_time = time.time()
        
        while True:
            # Check request rate limit
            request_bucket = self.request_buckets[model]
            if not request_bucket.consume(1):
                wait_time = request_bucket.time_until_tokens(1)
                if wait_time > 0:
                    self.logger.debug(f"Request rate limited for {model}, waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                    continue
            
            # Check token rate limit
            token_bucket = self.token_buckets[model]
            if not token_bucket.consume(estimated_tokens):
                wait_time = token_bucket.time_until_tokens(estimated_tokens)
                if wait_time > 0:
                    self.logger.debug(f"Token rate limited for {model}, waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                    continue
            
            # Check sliding window
            sliding_window = self.sliding_windows[model]
            if not sliding_window.can_make_request():
                wait_time = sliding_window.time_until_available()
                if wait_time > 0:
                    self.logger.debug(f"Sliding window rate limited for {model}, waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                    continue
            
            # All checks passed, record the request
            sliding_window.record_request()
            break
        
        # Update statistics
        total_wait_time = time.time() - start_time
        self.stats[model]['requests_made'] += 1
        self.stats[model]['tokens_consumed'] += estimated_tokens
        self.stats[model]['total_wait_time'] += total_wait_time
        
        if total_wait_time > 0.1:  # Consider it limited if we waited more than 100ms
            self.stats[model]['requests_limited'] += 1
    
    def update_token_usage(self, model: str, actual_tokens: int, estimated_tokens: int) -> None:
        """
        Update token usage after getting actual token count from response.
        
        Args:
            model: The model that was used
            actual_tokens: Actual tokens used in the request
            estimated_tokens: Tokens that were reserved
        """
        if model not in self.rate_limits:
            model = 'default'
        
        # Calculate the difference and adjust token bucket
        token_diff = actual_tokens - estimated_tokens
        
        if token_diff != 0:
            token_bucket = self.token_buckets[model]
            if token_diff > 0:
                # We used more tokens than estimated, consume the difference
                token_bucket.consume(token_diff)
            else:
                # We used fewer tokens, refund the difference
                token_bucket.tokens = min(
                    token_bucket.capacity,
                    token_bucket.tokens + abs(token_diff)
                )
        
        # Update statistics
        self.stats[model]['tokens_consumed'] += token_diff
    
    def get_current_limits(self, model: str) -> Dict[str, Any]:
        """Get current rate limit status for a model."""
        if model not in self.rate_limits:
            model = 'default'
        
        request_bucket = self.request_buckets[model]
        token_bucket = self.token_buckets[model]
        sliding_window = self.sliding_windows[model]
        
        return {
            'model': model,
            'request_bucket': {
                'available_tokens': request_bucket.tokens,
                'capacity': request_bucket.capacity,
                'refill_rate': request_bucket.refill_rate
            },
            'token_bucket': {
                'available_tokens': token_bucket.tokens,
                'capacity': token_bucket.capacity,
                'refill_rate': token_bucket.refill_rate
            },
            'sliding_window': {
                'current_requests': len(sliding_window.requests),
                'max_requests': sliding_window.max_requests,
                'window_size': sliding_window.window_size
            }
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        return dict(self.stats)
    
    def reset_stats(self) -> None:
        """Reset statistics."""
        self.stats.clear()
    
    async def wait_for_capacity(self, model: str, tokens: int) -> float:
        """
        Calculate how long to wait for sufficient capacity.
        
        Args:
            model: The model to check
            tokens: Number of tokens needed
            
        Returns:
            Wait time in seconds
        """
        if model not in self.rate_limits:
            model = 'default'
        
        request_bucket = self.request_buckets[model]
        token_bucket = self.token_buckets[model]
        sliding_window = self.sliding_windows[model]
        
        wait_times = [
            request_bucket.time_until_tokens(1),
            token_bucket.time_until_tokens(tokens),
            sliding_window.time_until_available()
        ]
        
        return max(wait_times)
    
    def can_make_request(self, model: str, tokens: int) -> bool:
        """
        Check if a request can be made immediately.
        
        Args:
            model: The model to check
            tokens: Number of tokens needed
            
        Returns:
            True if request can be made immediately
        """
        if model not in self.rate_limits:
            model = 'default'
        
        request_bucket = self.request_buckets[model]
        token_bucket = self.token_buckets[model]
        sliding_window = self.sliding_windows[model]
        
        request_bucket._refill()
        token_bucket._refill()
        
        return (
            request_bucket.tokens >= 1 and
            token_bucket.tokens >= tokens and
            sliding_window.can_make_request()
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the rate limiter."""
        health_status = {
            'status': 'healthy',
            'limiters': {},
            'stats': self.get_stats(),
            'issues': []
        }
        
        for model in self.rate_limits:
            limits = self.get_current_limits(model)
            health_status['limiters'][model] = limits
            
            # Check for potential issues
            request_utilization = 1 - (limits['request_bucket']['available_tokens'] / 
                                     limits['request_bucket']['capacity'])
            token_utilization = 1 - (limits['token_bucket']['available_tokens'] / 
                                   limits['token_bucket']['capacity'])
            
            if request_utilization > 0.9:
                health_status['issues'].append(f'{model}: High request utilization ({request_utilization:.1%})')
            
            if token_utilization > 0.9:
                health_status['issues'].append(f'{model}: High token utilization ({token_utilization:.1%})')
        
        if health_status['issues']:
            health_status['status'] = 'degraded'
        
        return health_status