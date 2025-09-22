"""
Anthropic Claude AI Client with Async Support.

This module provides a comprehensive async client for Anthropic's Claude AI
with enterprise features like connection pooling, rate limiting, and caching.
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Union, AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import httpx
from anthropic import AsyncAnthropic, APIError, RateLimitError
from anthropic.types import Message, MessageParam

from claude_flow.core.interfaces import BaseComponent
from claude_flow.config.models import ClaudeConfig
from .connection_pool import ConnectionPool
from .rate_limiter import RateLimiter
from .cache import ResponseCache
from .retry import RetryManager


@dataclass
class ClaudeRequest:
    """Claude API request configuration."""
    model: str = "claude-3-5-sonnet-20241022"
    max_tokens: int = 4096
    temperature: float = 0.7
    system: Optional[str] = None
    messages: List[MessageParam] = field(default_factory=list)
    stream: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClaudeResponse:
    """Claude API response wrapper."""
    content: str
    model: str
    usage: Dict[str, int]
    response_time_ms: float
    cached: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_response: Optional[Any] = None


class ClaudeClient(BaseComponent):
    """
    Enterprise-grade async Claude AI client with advanced features.
    """
    
    def __init__(self, config: ClaudeConfig):
        super().__init__()
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize connection pool and rate limiter
        self.connection_pool = ConnectionPool(config)
        self.rate_limiter = RateLimiter(config)
        self.cache = ResponseCache(config.cache if hasattr(config, 'cache') else {})
        self.retry_manager = RetryManager(config.retry if hasattr(config, 'retry') else None)
        
        # Response cache
        self._cache: Dict[str, ClaudeResponse] = {}
        self._cache_timestamps: Dict[str, float] = {}
        
        # Performance metrics
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'cache_hits': 0,
            'total_tokens_used': 0,
            'average_response_time': 0.0,
            'error_rate': 0.0
        }
    
    async def initialize(self) -> None:
        """Initialize Claude client and dependencies."""
        await super().initialize()
        
        if not self.config.api_key:
            raise ValueError("Claude API key is required")
        
        # Initialize enterprise features
        await self.connection_pool.initialize()
        await self.rate_limiter.initialize()
        await self.cache.initialize()
        await self.retry_manager.initialize()
        
        self.logger.info("Claude AI client initialized with full enterprise features")
    
    async def shutdown(self) -> None:
        """Close client and cleanup resources."""
        # Shutdown enterprise features
        await self.connection_pool.shutdown()
        await self.rate_limiter.shutdown()
        await self.cache.shutdown()
        await self.retry_manager.shutdown()
        
        await super().shutdown()
        self.logger.info("Claude AI client shutdown")
    
    async def chat(self, 
                   messages: Union[str, List[MessageParam]],
                   model: Optional[str] = None,
                   max_tokens: Optional[int] = None,
                   temperature: Optional[float] = None,
                   system: Optional[str] = None,
                   stream: bool = False,
                   use_cache: Optional[bool] = None,
                   **kwargs) -> Union[ClaudeResponse, AsyncIterator[str]]:
        """
        Send chat completion request to Claude.
        """
        # Prepare request
        request = ClaudeRequest(
            model=model or self.default_model,
            max_tokens=max_tokens or self.default_max_tokens,
            temperature=temperature or 0.7,
            system=system,
            messages=self._prepare_messages(messages),
            stream=stream,
            metadata=kwargs.get("metadata", {})
        )
        
        # Check cache first (if enabled and not streaming)
        use_cache = use_cache if use_cache is not None else (self.enable_caching and not stream)
        if use_cache:
            cached_response = await self.cache.get(request)
            if cached_response:
                self.stats["cached_responses"] += 1
                return cached_response
        
        # Rate limiting check
        await self.rate_limiter.acquire()
        
        try:
            # Execute request with retry logic
            if self.enable_retry:
                response = await self.retry_manager.execute_with_retry(
                    self._execute_request, request
                )
            else:
                response = await self._execute_request(request)
            
            # Cache response (if applicable)
            if use_cache and not stream:
                await self.cache.set(request, response)
            
            # Update statistics
            self._update_stats(response, success=True)
            
            return response
            
        except Exception as e:
            self._update_stats(None, success=False)
            await self.logger.error(f"Claude API request failed: {e}")
            raise
    
    async def _execute_request(self, request: ClaudeRequest) -> Union[ClaudeResponse, AsyncIterator[str]]:
        """Execute the actual API request."""
        start_time = time.time()
        
        try:
            if request.stream:
                return await self._execute_streaming_request(request, start_time)
            else:
                return await self._execute_standard_request(request, start_time)
                
        except RateLimitError as e:
            self.stats["rate_limited_requests"] += 1
            await self.logger.warning(f"Rate limited: {e}")
            raise
        except APIError as e:
            await self.logger.error(f"Claude API error: {e}")
            raise
    
    async def _execute_standard_request(self, request: ClaudeRequest, start_time: float) -> ClaudeResponse:
        """Execute standard (non-streaming) request."""
        # Prepare message parameters
        message_params = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": request.messages
        }
        
        if request.system:
            message_params["system"] = request.system
        
        # Make API call
        response = await self.client.messages.create(**message_params)
        
        # Calculate response time
        response_time_ms = (time.time() - start_time) * 1000
        
        # Extract content
        content = ""
        if response.content:
            for block in response.content:
                if block.type == "text":
                    content += block.text
        
        # Create response object
        claude_response = ClaudeResponse(
            content=content,
            model=response.model,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            },
            response_time_ms=response_time_ms,
            metadata=request.metadata,
            raw_response=response
        )
        
        return claude_response
    
    async def _execute_streaming_request(self, request: ClaudeRequest, start_time: float) -> AsyncIterator[str]:
        """Execute streaming request."""
        message_params = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": request.messages,
            "stream": True
        }
        
        if request.system:
            message_params["system"] = request.system
        
        async with self.client.messages.stream(**message_params) as stream:
            async for chunk in stream:
                if chunk.type == "content_block_delta":
                    if chunk.delta.type == "text_delta":
                        yield chunk.delta.text
    
    def _prepare_messages(self, messages: Union[str, List[MessageParam]]) -> List[MessageParam]:
        """Prepare messages for API call."""
        if isinstance(messages, str):
            return [{"role": "user", "content": messages}]
        return messages
    
    def _update_stats(self, response: Optional[ClaudeResponse], success: bool) -> None:
        """Update client statistics."""
        self.stats["total_requests"] += 1
        
        if success:
            self.stats["successful_requests"] += 1
            if response:
                # Update token usage
                self.stats["total_tokens_used"] += response.usage.get("total_tokens", 0)
                
                # Update average response time
                total_time = self.stats["avg_response_time_ms"] * (self.stats["successful_requests"] - 1)
                total_time += response.response_time_ms
                self.stats["avg_response_time_ms"] = total_time / self.stats["successful_requests"]
        else:
            self.stats["failed_requests"] += 1
    
    async def generate_text(self, 
                          prompt: str,
                          model: Optional[str] = None,
                          max_tokens: Optional[int] = None,
                          temperature: Optional[float] = None,
                          system: Optional[str] = None) -> str:
        """Simple text generation interface."""
        response = await self.chat(
            messages=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system
        )
        return response.content
    
    async def analyze_text(self, 
                         text: str,
                         analysis_type: str = "general",
                         custom_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Analyze text using Claude."""
        if custom_prompt:
            prompt = custom_prompt.format(text=text)
        else:
            prompts = {
                "sentiment": "Analyze the sentiment of the following text: {text}",
                "summary": "Provide a concise summary of the following text: {text}",
                "keywords": "Extract key topics and keywords from the following text: {text}",
                "general": "Analyze the following text and provide insights: {text}"
            }
            prompt = prompts.get(analysis_type, prompts["general"]).format(text=text)
        
        response = await self.generate_text(prompt)
        
        return {
            "analysis_type": analysis_type,
            "input_text": text,
            "analysis": response,
            "model": self.default_model,
            "timestamp": datetime.now().isoformat()
        }
    
    async def classify_task(self, 
                          task_description: str,
                          categories: Optional[List[str]] = None) -> Dict[str, Any]:
        """Classify a task using Claude."""
        if categories:
            category_list = ", ".join(categories)
            prompt = f"""
            Classify the following task into one of these categories: {category_list}
            
            Task: {task_description}
            
            Respond with just the category name and a confidence score (0-1).
            """
        else:
            prompt = f"""
            Classify the following task by type and provide a confidence score:
            
            Task: {task_description}
            
            Consider categories like: coding, testing, documentation, design, deployment, debugging, analysis
            """
        
        response = await self.generate_text(prompt)
        
        return {
            "task": task_description,
            "classification": response,
            "categories": categories,
            "model": self.default_model,
            "timestamp": datetime.now().isoformat()
        }
    
    async def estimate_complexity(self, 
                                task_description: str,
                                context: Optional[str] = None) -> Dict[str, Any]:
        """Estimate task complexity using Claude."""
        prompt = f"""
        Estimate the complexity of the following task on a scale of 1-10 (1=very simple, 10=extremely complex).
        Provide reasoning for your estimate.
        
        Task: {task_description}
        """
        
        if context:
            prompt += f"\nContext: {context}"
        
        response = await self.generate_text(prompt)
        
        return {
            "task": task_description,
            "context": context,
            "complexity_analysis": response,
            "model": self.default_model,
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        return {
            **self.stats.copy(),
            "connection_pool_stats": await self.connection_pool.get_stats(),
            "rate_limiter_stats": await self.rate_limiter.get_stats(),
            "cache_stats": await self.cache.get_stats(),
            "client_status": "connected" if self.client else "disconnected"
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            # Simple test request
            response = await self.generate_text("Hello", max_tokens=10)
            
            return {
                "status": "healthy",
                "api_accessible": True,
                "response_received": bool(response),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "api_accessible": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# Global client instance
_claude_client: Optional[ClaudeClient] = None


async def get_claude_client(api_key: Optional[str] = None) -> ClaudeClient:
    """Get global Claude client instance."""
    global _claude_client
    if _claude_client is None:
        _claude_client = ClaudeClient(api_key=api_key)
        await _claude_client.initialize()
    return _claude_client