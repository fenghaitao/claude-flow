"""
Retry Logic with Exponential Backoff for Claude AI Client

Provides robust retry mechanisms for handling transient failures:
- Exponential backoff with jitter
- Circuit breaker pattern
- Different retry strategies for different error types
- Request idempotency handling
"""

import asyncio
import random
import time
from typing import Optional, Dict, Any, Callable, TypeVar, Awaitable, List
from dataclasses import dataclass, field
from enum import Enum
import logging
from anthropic import APIError, RateLimitError, InternalServerError

from ..core.interfaces import BaseComponent


T = TypeVar('T')


class RetryStrategy(Enum):
    """Different retry strategies."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    NO_RETRY = "no_retry"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_range: float = 0.1  # 10% jitter
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    
    # Circuit breaker settings
    circuit_breaker_enabled: bool = True
    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds
    
    # Error-specific configurations
    rate_limit_retry: bool = True
    rate_limit_max_delay: float = 300.0  # 5 minutes
    internal_error_retry: bool = True
    timeout_retry: bool = True
    network_error_retry: bool = True


@dataclass
class RetryAttempt:
    """Information about a retry attempt."""
    attempt_number: int
    error: Exception
    delay: float
    timestamp: float


class CircuitBreaker:
    """Circuit breaker for preventing cascading failures."""
    
    def __init__(self, config: RetryConfig):
        self.config = config
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half_open
        self.logger = logging.getLogger(__name__)
    
    def can_execute(self) -> bool:
        """Check if the circuit breaker allows execution."""
        if not self.config.circuit_breaker_enabled:
            return True
        
        if self.state == "closed":
            return True
        elif self.state == "open":
            # Check if recovery timeout has passed
            if time.time() - self.last_failure_time > self.config.recovery_timeout:
                self.state = "half_open"
                self.logger.info("Circuit breaker transitioning to half-open state")
                return True
            return False
        elif self.state == "half_open":
            return True
        
        return False
    
    def record_success(self) -> None:
        """Record a successful execution."""
        if self.state == "half_open":
            self.state = "closed"
            self.failure_count = 0
            self.logger.info("Circuit breaker reset to closed state")
    
    def record_failure(self) -> None:
        """Record a failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.config.failure_threshold:
            if self.state != "open":
                self.state = "open"
                self.logger.warning(f"Circuit breaker opened after {self.failure_count} failures")


class RetryManager(BaseComponent):
    """Advanced retry manager with circuit breaker and backoff strategies."""
    
    def __init__(self, config: RetryConfig = None):
        super().__init__()
        self.config = config or RetryConfig()
        self.logger = logging.getLogger(__name__)
        
        # Circuit breaker
        self.circuit_breaker = CircuitBreaker(self.config)
        
        # Statistics
        self.stats = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'total_retries': 0,
            'circuit_breaker_opens': 0,
            'max_retries_exceeded': 0,
            'retry_by_error_type': {},
            'average_retry_delay': 0.0
        }
        
        # Retry history for analysis
        self.retry_history: List[RetryAttempt] = []
        self.max_history_size = 1000
    
    async def execute_with_retry(self, 
                                func: Callable[..., Awaitable[T]], 
                                *args, 
                                **kwargs) -> T:
        """
        Execute a function with retry logic.
        
        Args:
            func: Async function to execute
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            Result of the function execution
            
        Raises:
            Exception: The last exception if all retries are exhausted
        """
        self.stats['total_executions'] += 1
        
        # Check circuit breaker
        if not self.circuit_breaker.can_execute():
            raise Exception("Circuit breaker is open")
        
        last_exception = None
        total_delay = 0.0
        
        for attempt in range(self.config.max_attempts):
            try:
                result = await func(*args, **kwargs)
                
                # Record success
                self.circuit_breaker.record_success()
                self.stats['successful_executions'] += 1
                
                if attempt > 0:
                    self.stats['total_retries'] += attempt
                    # Update average retry delay
                    if self.stats['total_retries'] > 0:
                        self.stats['average_retry_delay'] = total_delay / self.stats['total_retries']
                
                return result
                
            except Exception as e:
                last_exception = e
                self.circuit_breaker.record_failure()
                
                # Determine if we should retry this error
                if not self._should_retry_error(e):
                    self.logger.debug(f"Not retrying error type: {type(e).__name__}")
                    break
                
                # If this is the last attempt, don't delay
                if attempt == self.config.max_attempts - 1:
                    break
                
                # Calculate delay and wait
                delay = self._calculate_delay(attempt, e)
                total_delay += delay
                
                # Record retry attempt
                retry_attempt = RetryAttempt(
                    attempt_number=attempt + 1,
                    error=e,
                    delay=delay,
                    timestamp=time.time()
                )
                self._record_retry_attempt(retry_attempt)
                
                self.logger.debug(
                    f"Attempt {attempt + 1} failed with {type(e).__name__}: {e}. "
                    f"Retrying in {delay:.2f}s"
                )
                
                await asyncio.sleep(delay)
        
        # All retries exhausted
        self.stats['failed_executions'] += 1
        if self.config.max_attempts > 1:
            self.stats['max_retries_exceeded'] += 1
        
        self.logger.error(
            f"All {self.config.max_attempts} attempts failed. "
            f"Last error: {type(last_exception).__name__}: {last_exception}"
        )
        
        raise last_exception
    
    def _should_retry_error(self, error: Exception) -> bool:
        """Determine if an error should be retried."""
        error_type = type(error).__name__
        
        # Update error statistics
        if error_type not in self.stats['retry_by_error_type']:
            self.stats['retry_by_error_type'][error_type] = 0
        self.stats['retry_by_error_type'][error_type] += 1
        
        # Rate limit errors
        if isinstance(error, RateLimitError):
            return self.config.rate_limit_retry
        
        # Internal server errors
        if isinstance(error, InternalServerError):
            return self.config.internal_error_retry
        
        # Timeout errors
        if isinstance(error, (asyncio.TimeoutError, TimeoutError)):
            return self.config.timeout_retry
        
        # Network errors
        if "connection" in str(error).lower() or "network" in str(error).lower():
            return self.config.network_error_retry
        
        # API errors that are likely temporary
        if isinstance(error, APIError):
            # Don't retry client errors (4xx) except rate limits
            if hasattr(error, 'status_code'):
                status_code = error.status_code
                if 400 <= status_code < 500 and status_code != 429:
                    return False
            return True
        
        # Default: don't retry unknown errors
        return False
    
    def _calculate_delay(self, attempt: int, error: Exception) -> float:
        """Calculate delay for the next retry attempt."""
        if self.config.strategy == RetryStrategy.NO_RETRY:
            return 0.0
        
        # Special handling for rate limit errors
        if isinstance(error, RateLimitError):
            # Try to extract retry-after header if available
            if hasattr(error, 'response') and error.response:
                retry_after = error.response.headers.get('retry-after')
                if retry_after:
                    try:
                        delay = float(retry_after)
                        return min(delay, self.config.rate_limit_max_delay)
                    except ValueError:
                        pass
            
            # Exponential backoff for rate limits with higher base delay
            delay = self.config.base_delay * (self.config.exponential_base ** attempt) * 2
            delay = min(delay, self.config.rate_limit_max_delay)
        else:
            # Standard delay calculation
            if self.config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
                delay = self.config.base_delay * (self.config.exponential_base ** attempt)
            elif self.config.strategy == RetryStrategy.LINEAR_BACKOFF:
                delay = self.config.base_delay * (attempt + 1)
            elif self.config.strategy == RetryStrategy.FIXED_DELAY:
                delay = self.config.base_delay
            else:
                delay = self.config.base_delay
            
            delay = min(delay, self.config.max_delay)
        
        # Add jitter if enabled
        if self.config.jitter:
            jitter_amount = delay * self.config.jitter_range
            jitter = random.uniform(-jitter_amount, jitter_amount)
            delay += jitter
        
        return max(0, delay)
    
    def _record_retry_attempt(self, attempt: RetryAttempt) -> None:
        """Record a retry attempt for analysis."""
        self.retry_history.append(attempt)
        
        # Limit history size
        if len(self.retry_history) > self.max_history_size:
            self.retry_history = self.retry_history[-self.max_history_size:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get retry manager statistics."""
        success_rate = 0.0
        if self.stats['total_executions'] > 0:
            success_rate = self.stats['successful_executions'] / self.stats['total_executions']
        
        return {
            **self.stats.copy(),
            'success_rate': success_rate,
            'circuit_breaker_state': self.circuit_breaker.state,
            'circuit_breaker_failure_count': self.circuit_breaker.failure_count,
            'config': {
                'max_attempts': self.config.max_attempts,
                'base_delay': self.config.base_delay,
                'max_delay': self.config.max_delay,
                'strategy': self.config.strategy.value,
                'circuit_breaker_enabled': self.config.circuit_breaker_enabled
            }
        }
    
    def reset_stats(self) -> None:
        """Reset all statistics."""
        self.stats = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'total_retries': 0,
            'circuit_breaker_opens': 0,
            'max_retries_exceeded': 0,
            'retry_by_error_type': {},
            'average_retry_delay': 0.0
        }
        self.retry_history.clear()
    
    def reset_circuit_breaker(self) -> None:
        """Manually reset the circuit breaker."""
        self.circuit_breaker.state = "closed"
        self.circuit_breaker.failure_count = 0
        self.circuit_breaker.last_failure_time = 0
        self.logger.info("Circuit breaker manually reset")
    
    def get_recent_failures(self, minutes: int = 10) -> List[RetryAttempt]:
        """Get recent failure attempts within the specified time window."""
        cutoff_time = time.time() - (minutes * 60)
        return [
            attempt for attempt in self.retry_history
            if attempt.timestamp >= cutoff_time
        ]
    
    def analyze_failure_patterns(self) -> Dict[str, Any]:
        """Analyze failure patterns to identify issues."""
        if not self.retry_history:
            return {"message": "No retry history available"}
        
        # Group failures by error type
        error_patterns = {}
        recent_failures = self.get_recent_failures(60)  # Last hour
        
        for attempt in recent_failures:
            error_type = type(attempt.error).__name__
            if error_type not in error_patterns:
                error_patterns[error_type] = {
                    'count': 0,
                    'total_delay': 0.0,
                    'timestamps': []
                }
            
            error_patterns[error_type]['count'] += 1
            error_patterns[error_type]['total_delay'] += attempt.delay
            error_patterns[error_type]['timestamps'].append(attempt.timestamp)
        
        # Calculate average delays and frequencies
        for error_type, data in error_patterns.items():
            data['average_delay'] = data['total_delay'] / data['count']
            data['frequency_per_hour'] = data['count']
        
        return {
            'recent_failure_count': len(recent_failures),
            'error_patterns': error_patterns,
            'circuit_breaker_state': self.circuit_breaker.state,
            'recommendations': self._get_recommendations(error_patterns)
        }
    
    def _get_recommendations(self, error_patterns: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on failure patterns."""
        recommendations = []
        
        for error_type, data in error_patterns.items():
            if data['count'] > 10:  # More than 10 failures in the last hour
                recommendations.append(
                    f"High frequency of {error_type} errors ({data['count']}/hour). "
                    f"Consider increasing base delay or implementing circuit breaker."
                )
            
            if data['average_delay'] > 30:  # Average delay over 30 seconds
                recommendations.append(
                    f"{error_type} errors causing long delays (avg: {data['average_delay']:.1f}s). "
                    f"Consider reducing max_delay or implementing timeout."
                )
        
        if self.circuit_breaker.state == "open":
            recommendations.append(
                "Circuit breaker is open. Check underlying service health and consider manual reset."
            )
        
        return recommendations
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the retry manager."""
        recent_failures = self.get_recent_failures(10)
        failure_rate = len(recent_failures) / max(1, self.stats['total_executions'])
        
        health_status = {
            'status': 'healthy',
            'circuit_breaker_state': self.circuit_breaker.state,
            'recent_failure_count': len(recent_failures),
            'failure_rate': failure_rate,
            'issues': []
        }
        
        # Check for issues
        if self.circuit_breaker.state == "open":
            health_status['status'] = 'unhealthy'
            health_status['issues'].append('Circuit breaker is open')
        
        if failure_rate > 0.5:  # More than 50% failure rate
            health_status['status'] = 'degraded'
            health_status['issues'].append(f'High failure rate: {failure_rate:.1%}')
        
        if len(recent_failures) > 20:  # More than 20 failures in 10 minutes
            health_status['status'] = 'degraded'
            health_status['issues'].append('High failure frequency')
        
        return health_status