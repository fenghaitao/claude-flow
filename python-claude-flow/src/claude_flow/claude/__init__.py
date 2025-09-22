"""
Claude AI Integration Package.

This package provides comprehensive integration with Anthropic's Claude AI,
including async client, connection pooling, rate limiting, and caching.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .client import ClaudeClient
    from .connection_pool import ConnectionPool
    from .rate_limiter import RateLimiter
    from .cache import ResponseCache
    from .retry import RetryManager

__all__ = [
    "ClaudeClient",
    "ConnectionPool",
    "RateLimiter",
    "ResponseCache",
    "RetryManager"
]

def __getattr__(name: str):
    """Lazy import for Claude AI integration components."""
    if name == "ClaudeClient":
        from .client import ClaudeClient
        return ClaudeClient
    elif name == "ConnectionPool":
        from .connection_pool import ConnectionPool
        return ConnectionPool
    elif name == "RateLimiter":
        from .rate_limiter import RateLimiter
        return RateLimiter
    elif name == "ResponseCache":
        from .cache import ResponseCache
        return ResponseCache
    elif name == "RetryManager":
        from .retry import RetryManager
        return RetryManager
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")