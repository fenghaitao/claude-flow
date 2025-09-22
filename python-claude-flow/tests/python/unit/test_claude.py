"""
Unit tests for Claude AI client and related components.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from anthropic import RateLimitError, APIError

from claude_flow.claude.client import ClaudeClient, ClaudeRequest, ClaudeResponse
from claude_flow.claude.rate_limiter import RateLimiter, RateLimit, TokenBucket
from claude_flow.claude.cache import ResponseCache, CacheEntry, LRUCache
from claude_flow.claude.retry import RetryManager, RetryConfig, CircuitBreaker
from claude_flow.config.models import ClaudeConfig


class TestClaudeRequest:
    """Test ClaudeRequest model."""
    
    def test_request_creation(self):
        """Test basic request creation."""
        request = ClaudeRequest(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2048,
            temperature=0.5
        )
        
        assert request.model == "claude-3-5-sonnet-20241022"
        assert request.max_tokens == 2048
        assert request.temperature == 0.5
        assert request.messages == []
        assert request.stream is False
    
    def test_request_defaults(self):
        """Test request with default values."""
        request = ClaudeRequest()
        
        assert request.model == "claude-3-5-sonnet-20241022"
        assert request.max_tokens == 4096
        assert request.temperature == 0.7
        assert request.system is None


class TestClaudeResponse:
    """Test ClaudeResponse model."""
    
    def test_response_creation(self):
        """Test basic response creation."""
        response = ClaudeResponse(
            content="Test response content",
            model="claude-3-5-sonnet-20241022",
            usage={"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
            response_time_ms=150.5
        )
        
        assert response.content == "Test response content"
        assert response.model == "claude-3-5-sonnet-20241022"
        assert response.usage["total_tokens"] == 30
        assert response.response_time_ms == 150.5
        assert response.cached is False


class TestTokenBucket:
    """Test TokenBucket rate limiting."""
    
    def test_token_bucket_creation(self):
        """Test token bucket initialization."""
        bucket = TokenBucket(
            capacity=100.0,
            tokens=100.0,
            refill_rate=10.0
        )
        
        assert bucket.capacity == 100.0
        assert bucket.tokens == 100.0
        assert bucket.refill_rate == 10.0
    
    def test_token_consumption(self):
        """Test token consumption."""
        bucket = TokenBucket(capacity=100.0, tokens=100.0, refill_rate=10.0)
        
        # Should be able to consume available tokens
        assert bucket.consume(50.0) is True
        assert bucket.tokens == 50.0
        
        # Should not be able to consume more than available
        assert bucket.consume(60.0) is False
        assert bucket.tokens == 50.0
    
    def test_token_refill(self):
        """Test token bucket refill."""
        import time
        
        bucket = TokenBucket(capacity=100.0, tokens=0.0, refill_rate=10.0)
        bucket.last_refill = time.time() - 1.0  # 1 second ago
        
        # Should refill 10 tokens (10 tokens/second * 1 second)
        bucket._refill()
        assert bucket.tokens == 10.0
    
    def test_time_until_tokens(self):
        """Test calculating time until tokens available."""
        bucket = TokenBucket(capacity=100.0, tokens=0.0, refill_rate=10.0)
        
        # Need 20 tokens, refill rate is 10/second, should take 2 seconds
        wait_time = bucket.time_until_tokens(20.0)
        assert wait_time == 2.0


class TestRateLimiter:
    """Test RateLimiter functionality."""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter for testing."""
        config = ClaudeConfig(
            api_key="test-key",
            rate_limits={
                "claude-3-5-sonnet-20241022": {
                    "requests_per_minute": 60,
                    "tokens_per_minute": 6000
                }
            }
        )
        return RateLimiter(config)
    
    @pytest.mark.asyncio
    async def test_rate_limiter_initialization(self, rate_limiter):
        """Test rate limiter initialization."""
        await rate_limiter.initialize()
        
        assert "claude-3-5-sonnet-20241022" in rate_limiter.request_buckets
        assert "claude-3-5-sonnet-20241022" in rate_limiter.token_buckets
        assert "claude-3-5-sonnet-20241022" in rate_limiter.sliding_windows
        
        await rate_limiter.shutdown()
    
    @pytest.mark.asyncio
    async def test_acquire_permission(self, rate_limiter):
        """Test acquiring permission for requests."""
        await rate_limiter.initialize()
        
        try:
            # Should be able to acquire permission initially
            await rate_limiter.acquire("claude-3-5-sonnet-20241022", 100)
            
            # Stats should be updated
            stats = rate_limiter.get_stats()
            assert stats["claude-3-5-sonnet-20241022"]["requests_made"] == 1
            assert stats["claude-3-5-sonnet-20241022"]["tokens_consumed"] == 100
            
        finally:
            await rate_limiter.shutdown()
    
    def test_should_retry_error(self, rate_limiter):
        """Test error retry logic."""
        # Rate limit errors should be retried
        assert rate_limiter._should_retry_error(RateLimitError("Rate limited")) is True
        
        # Some API errors should be retried
        assert rate_limiter._should_retry_error(APIError("Internal server error")) is True
        
        # Timeout errors should be retried
        assert rate_limiter._should_retry_error(asyncio.TimeoutError()) is True


class TestLRUCache:
    """Test LRU cache functionality."""
    
    def test_cache_creation(self):
        """Test cache initialization."""
        cache = LRUCache(max_size=100, default_ttl=3600)
        
        assert cache.max_size == 100
        assert cache.default_ttl == 3600
        assert len(cache._cache) == 0
    
    def test_cache_set_get(self):
        """Test setting and getting values."""
        cache = LRUCache(max_size=10)
        
        # Set value
        cache.set("key1", "value1")
        
        # Get value
        value = cache.get("key1")
        assert value == "value1"
        
        # Get non-existent key
        assert cache.get("nonexistent") is None
    
    def test_cache_lru_eviction(self):
        """Test LRU eviction."""
        cache = LRUCache(max_size=2)
        
        # Fill cache
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        # Access key1 to make it recently used
        cache.get("key1")
        
        # Add new key, should evict key2 (least recently used)
        cache.set("key3", "value3")
        
        assert cache.get("key1") == "value1"  # Should still exist
        assert cache.get("key2") is None      # Should be evicted
        assert cache.get("key3") == "value3"  # Should exist
    
    def test_cache_ttl_expiration(self):
        """Test TTL expiration."""
        import time
        
        cache = LRUCache(max_size=10, default_ttl=0.1)  # 100ms TTL
        
        # Set value with short TTL
        cache.set("key1", "value1")
        
        # Should be available immediately
        assert cache.get("key1") == "value1"
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Should be expired
        assert cache.get("key1") is None


class TestResponseCache:
    """Test ResponseCache functionality."""
    
    @pytest.fixture
    async def response_cache(self, temp_dir):
        """Create response cache for testing."""
        config = {
            "max_size": 100,
            "default_ttl": 3600,
            "enable_persistence": True,
            "db_path": str(temp_dir / "test_cache.db")
        }
        cache = ResponseCache(config)
        await cache.initialize()
        yield cache
        await cache.shutdown()
    
    @pytest.mark.asyncio
    async def test_cache_set_get(self, response_cache):
        """Test caching responses."""
        request_data = {
            "model": "claude-3-5-sonnet-20241022",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 100
        }
        
        response_data = {
            "content": "Hello! How can I help you?",
            "usage": {"total_tokens": 50}
        }
        
        # Cache response
        await response_cache.set(request_data, response_data)
        
        # Retrieve response
        cached = await response_cache.get(request_data)
        
        assert cached is not None
        assert cached["content"] == "Hello! How can I help you?"
        assert cached["usage"]["total_tokens"] == 50
    
    @pytest.mark.asyncio
    async def test_cache_key_generation(self, response_cache):
        """Test cache key generation consistency."""
        request1 = {
            "model": "claude-3-5-sonnet-20241022",
            "messages": [{"role": "user", "content": "Test"}],
            "temperature": 0.7
        }
        
        request2 = {
            "temperature": 0.7,
            "model": "claude-3-5-sonnet-20241022",
            "messages": [{"role": "user", "content": "Test"}]
        }
        
        # Same content, different order should generate same key
        key1 = response_cache._generate_cache_key(request1)
        key2 = response_cache._generate_cache_key(request2)
        
        assert key1 == key2
    
    @pytest.mark.asyncio
    async def test_cache_stats(self, response_cache):
        """Test cache statistics."""
        request_data = {
            "model": "claude-3-5-sonnet-20241022",
            "messages": [{"role": "user", "content": "Stats test"}]
        }
        
        # Miss
        result = await response_cache.get(request_data)
        assert result is None
        
        # Set
        await response_cache.set(request_data, {"content": "Response"})
        
        # Hit
        result = await response_cache.get(request_data)
        assert result is not None
        
        stats = response_cache.get_stats()
        assert stats["hits"] >= 1
        assert stats["misses"] >= 1
        assert stats["sets"] >= 1


class TestCircuitBreaker:
    """Test CircuitBreaker functionality."""
    
    def test_circuit_breaker_creation(self):
        """Test circuit breaker initialization."""
        from claude_flow.claude.retry import RetryConfig
        
        config = RetryConfig(
            circuit_breaker_enabled=True,
            failure_threshold=3,
            recovery_timeout=30.0
        )
        
        breaker = CircuitBreaker(config)
        
        assert breaker.state == "closed"
        assert breaker.failure_count == 0
    
    def test_circuit_breaker_states(self):
        """Test circuit breaker state transitions."""
        from claude_flow.claude.retry import RetryConfig
        
        config = RetryConfig(failure_threshold=2, recovery_timeout=1.0)
        breaker = CircuitBreaker(config)
        
        # Initially closed
        assert breaker.can_execute() is True
        assert breaker.state == "closed"
        
        # Record failures
        breaker.record_failure()
        assert breaker.state == "closed"  # Still closed
        
        breaker.record_failure()
        assert breaker.state == "open"    # Now open
        assert breaker.can_execute() is False
        
        # Record success should reset
        breaker.record_success()
        assert breaker.state == "closed"
        assert breaker.failure_count == 0


class TestRetryManager:
    """Test RetryManager functionality."""
    
    @pytest.fixture
    def retry_manager(self):
        """Create retry manager for testing."""
        config = RetryConfig(
            max_attempts=3,
            base_delay=0.01,  # Very short delays for testing
            max_delay=0.1
        )
        return RetryManager(config)
    
    @pytest.mark.asyncio
    async def test_successful_execution(self, retry_manager):
        """Test successful function execution."""
        await retry_manager.initialize()
        
        async def successful_func():
            return "success"
        
        result = await retry_manager.execute_with_retry(successful_func)
        
        assert result == "success"
        
        stats = retry_manager.get_stats()
        assert stats["successful_executions"] == 1
        assert stats["total_retries"] == 0
        
        await retry_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_retry_on_failure(self, retry_manager):
        """Test retrying on transient failures."""
        await retry_manager.initialize()
        
        attempt_count = 0
        
        async def failing_then_success():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise APIError("Temporary error")
            return "success_after_retries"
        
        result = await retry_manager.execute_with_retry(failing_then_success)
        
        assert result == "success_after_retries"
        assert attempt_count == 3
        
        stats = retry_manager.get_stats()
        assert stats["successful_executions"] == 1
        assert stats["total_retries"] >= 2
        
        await retry_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, retry_manager):
        """Test behavior when max retries exceeded."""
        await retry_manager.initialize()
        
        async def always_fails():
            raise APIError("Permanent error")
        
        with pytest.raises(APIError):
            await retry_manager.execute_with_retry(always_fails)
        
        stats = retry_manager.get_stats()
        assert stats["failed_executions"] == 1
        assert stats["max_retries_exceeded"] == 1
        
        await retry_manager.shutdown()


@pytest.mark.integration  
class TestClaudeClientIntegration:
    """Integration tests for Claude client components."""
    
    @pytest.fixture
    async def claude_client(self, claude_config, temp_dir):
        """Create Claude client for testing."""
        # Update config for testing
        claude_config.cache = {
            "max_size": 10,
            "default_ttl": 60,
            "enable_persistence": True,
            "db_path": str(temp_dir / "claude_cache.db")
        }
        
        client = ClaudeClient(claude_config)
        await client.initialize()
        yield client
        await client.shutdown()
    
    @pytest.mark.asyncio
    async def test_client_initialization(self, claude_client):
        """Test complete client initialization."""
        assert claude_client.connection_pool is not None
        assert claude_client.rate_limiter is not None
        assert claude_client.cache is not None
        assert claude_client.retry_manager is not None
    
    @pytest.mark.asyncio
    @pytest.mark.claude
    async def test_real_api_call(self, test_config, claude_client):
        """Test real API call if enabled."""
        if not test_config.use_real_claude:
            pytest.skip("Real Claude API testing disabled")
        
        # Update client with real API key
        claude_client.config.api_key = test_config.claude_api_key
        
        try:
            response = await claude_client.chat(
                messages="Hello, please respond with just 'Hello!'",
                max_tokens=10
            )
            
            assert isinstance(response, ClaudeResponse)
            assert response.content
            assert response.usage["total_tokens"] > 0
            
        except Exception as e:
            pytest.skip(f"Real API test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_health_check(self, claude_client):
        """Test client health check."""
        with patch.object(claude_client, 'chat') as mock_chat:
            mock_chat.return_value = ClaudeResponse(
                content="Hello",
                model="claude-3-5-sonnet-20241022",
                usage={"total_tokens": 5},
                response_time_ms=100
            )
            
            health = await claude_client.health_check()
            
            assert health["status"] == "healthy"
            assert health["api_accessible"] is True
    
    @pytest.mark.asyncio
    async def test_get_stats(self, claude_client):
        """Test getting client statistics."""
        stats = await claude_client.get_stats()
        
        assert "connection_pool_stats" in stats
        assert "rate_limiter_stats" in stats
        assert "cache_stats" in stats
        assert "client_status" in stats