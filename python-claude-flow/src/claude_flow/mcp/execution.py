"""
Async tool execution pipeline with error handling and monitoring.
"""

import asyncio
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Union, Awaitable
from queue import Queue
import threading

from claude_flow.core.interfaces import BaseComponent
from .tools import ToolRegistry


class ExecutionStatus(str, Enum):
    """Tool execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class ExecutionContext:
    """Context for tool execution."""
    request_id: str
    tool_name: str
    arguments: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    timeout: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Result of tool execution."""
    request_id: str
    tool_name: str
    status: ExecutionStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ToolExecutionPipeline(BaseComponent):
    """
    Async tool execution pipeline with error handling, retries, and monitoring.
    """
    
    def __init__(self, name: str = "tool_execution_pipeline", 
                 registry: Optional[ToolRegistry] = None,
                 max_concurrent_executions: int = 100,
                 default_timeout: float = 30.0):
        super().__init__(name)
        self.registry = registry or ToolRegistry()
        self.max_concurrent_executions = max_concurrent_executions
        self.default_timeout = default_timeout
        
        # Execution tracking
        self.active_executions: Dict[str, ExecutionContext] = {}
        self.execution_history: List[ExecutionResult] = []
        self.execution_queue: asyncio.Queue = asyncio.Queue()
        
        # Thread pool for sync tool execution
        self.thread_pool = ThreadPoolExecutor(max_workers=max_concurrent_executions)
        
        # Pipeline control
        self.is_running = False
        self.worker_tasks: List[asyncio.Task] = []
        
        # Monitoring
        self.stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "avg_execution_time": 0.0,
            "current_queue_size": 0
        }
    
    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the execution pipeline."""
        config = config or {}
        
        # Initialize registry
        await self.registry.initialize()
        
        # Configure pipeline
        self.max_concurrent_executions = config.get("max_concurrent_executions", self.max_concurrent_executions)
        self.default_timeout = config.get("default_timeout", self.default_timeout)
        
        await self.logger.info("Tool execution pipeline initialized")
    
    async def start(self) -> None:
        """Start the execution pipeline."""
        if self.is_running:
            await self.logger.warning("Pipeline is already running")
            return
        
        self.is_running = True
        
        # Start worker tasks
        for i in range(self.max_concurrent_executions):
            task = asyncio.create_task(self._execution_worker(f"worker-{i}"))
            self.worker_tasks.append(task)
        
        await self.logger.info(f"Started execution pipeline with {len(self.worker_tasks)} workers")
    
    async def stop(self) -> None:
        """Stop the execution pipeline."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Cancel all worker tasks
        for task in self.worker_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        
        # Shutdown thread pool
        self.thread_pool.shutdown(wait=True)
        
        self.worker_tasks.clear()
        await self.logger.info("Execution pipeline stopped")
    
    async def execute_tool(self, request_id: str, tool_name: str, 
                          arguments: Dict[str, Any], 
                          timeout: Optional[float] = None,
                          max_retries: int = 3,
                          metadata: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """
        Execute a tool asynchronously.
        """
        # Create execution context
        context = ExecutionContext(
            request_id=request_id,
            tool_name=tool_name,
            arguments=arguments,
            timeout=timeout or self.default_timeout,
            max_retries=max_retries,
            metadata=metadata or {}
        )
        
        # Add to queue
        await self.execution_queue.put(context)
        self.stats["current_queue_size"] = self.execution_queue.qsize()
        
        await self.logger.debug(f"Queued tool execution: {tool_name} (request: {request_id})")
        
        # For immediate execution (bypass queue), we could implement a direct execution path
        # For now, we'll return a pending result and the actual result will be available via monitoring
        return ExecutionResult(
            request_id=request_id,
            tool_name=tool_name,
            status=ExecutionStatus.PENDING
        )
    
    async def _execution_worker(self, worker_id: str) -> None:
        """Worker task for processing tool executions."""
        await self.logger.debug(f"Execution worker {worker_id} started")
        
        while self.is_running:
            try:
                # Get next execution context
                context = await asyncio.wait_for(
                    self.execution_queue.get(), 
                    timeout=1.0
                )
                
                self.stats["current_queue_size"] = self.execution_queue.qsize()
                
                # Execute tool
                result = await self._execute_with_error_handling(context)
                
                # Store result
                self.execution_history.append(result)
                
                # Update stats
                self._update_execution_stats(result)
                
                await self.logger.debug(f"Worker {worker_id} completed execution: {context.tool_name}")
                
            except asyncio.TimeoutError:
                # No work available, continue
                continue
            except asyncio.CancelledError:
                await self.logger.debug(f"Worker {worker_id} cancelled")
                break
            except Exception as e:
                await self.logger.error(f"Worker {worker_id} error: {e}")
    
    async def _execute_with_error_handling(self, context: ExecutionContext) -> ExecutionResult:
        """Execute tool with comprehensive error handling."""
        start_time = time.time()
        
        # Track active execution
        self.active_executions[context.request_id] = context
        
        try:
            await self.logger.debug(f"Executing tool: {context.tool_name}")
            
            # Execute with timeout and retries
            result = await self._execute_with_retries(context)
            
            execution_time = time.time() - start_time
            
            return ExecutionResult(
                request_id=context.request_id,
                tool_name=context.tool_name,
                status=ExecutionStatus.COMPLETED,
                result=result,
                execution_time=execution_time,
                retry_count=context.retry_count,
                metadata=context.metadata
            )
            
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            await self.logger.error(f"Tool execution timeout: {context.tool_name}")
            
            return ExecutionResult(
                request_id=context.request_id,
                tool_name=context.tool_name,
                status=ExecutionStatus.TIMEOUT,
                error="Execution timeout",
                execution_time=execution_time,
                retry_count=context.retry_count,
                metadata=context.metadata
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Tool execution failed: {str(e)}"
            await self.logger.error(f"{error_msg}\n{traceback.format_exc()}")
            
            return ExecutionResult(
                request_id=context.request_id,
                tool_name=context.tool_name,
                status=ExecutionStatus.FAILED,
                error=error_msg,
                execution_time=execution_time,
                retry_count=context.retry_count,
                metadata=context.metadata
            )
            
        finally:
            # Remove from active executions
            if context.request_id in self.active_executions:
                del self.active_executions[context.request_id]
    
    async def _execute_with_retries(self, context: ExecutionContext) -> Any:
        """Execute tool with retry logic."""
        last_error = None
        
        for attempt in range(context.max_retries + 1):
            try:
                context.retry_count = attempt
                
                # Execute tool with timeout
                if context.timeout:
                    result = await asyncio.wait_for(
                        self._execute_tool_direct(context),
                        timeout=context.timeout
                    )
                else:
                    result = await self._execute_tool_direct(context)
                
                return result
                
            except Exception as e:
                last_error = e
                
                if attempt < context.max_retries:
                    wait_time = min(2 ** attempt, 10)  # Exponential backoff, max 10s
                    await self.logger.warning(
                        f"Tool execution attempt {attempt + 1} failed for {context.tool_name}, "
                        f"retrying in {wait_time}s: {str(e)}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    await self.logger.error(
                        f"Tool execution failed after {context.max_retries + 1} attempts: {context.tool_name}"
                    )
        
        # If we get here, all retries failed
        raise last_error
    
    async def _execute_tool_direct(self, context: ExecutionContext) -> Any:
        """Execute tool directly through registry."""
        # Check if tool exists
        if context.tool_name not in self.registry.tools:
            raise ValueError(f"Tool not found: {context.tool_name}")
        
        # Get tool definition
        tool_def = self.registry.tools[context.tool_name]
        
        # Execute based on handler type
        if tool_def.async_handler:
            # Async handler
            return await tool_def.handler(**context.arguments)
        else:
            # Sync handler - run in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.thread_pool,
                lambda: tool_def.handler(**context.arguments)
            )
    
    def _update_execution_stats(self, result: ExecutionResult) -> None:
        """Update execution statistics."""
        self.stats["total_executions"] += 1
        
        if result.status == ExecutionStatus.COMPLETED:
            self.stats["successful_executions"] += 1
        else:
            self.stats["failed_executions"] += 1
        
        # Update average execution time
        total_time = self.stats["avg_execution_time"] * (self.stats["total_executions"] - 1)
        total_time += result.execution_time
        self.stats["avg_execution_time"] = total_time / self.stats["total_executions"]
    
    async def get_execution_status(self, request_id: str) -> Optional[ExecutionResult]:
        """Get status of a specific execution."""
        # Check active executions
        if request_id in self.active_executions:
            context = self.active_executions[request_id]
            return ExecutionResult(
                request_id=request_id,
                tool_name=context.tool_name,
                status=ExecutionStatus.RUNNING,
                metadata=context.metadata
            )
        
        # Check execution history
        for result in reversed(self.execution_history):
            if result.request_id == request_id:
                return result
        
        return None
    
    async def cancel_execution(self, request_id: str) -> bool:
        """Cancel a pending or running execution."""
        # For simplicity, we'll only support cancelling pending executions
        # In a full implementation, you'd need more sophisticated cancellation
        if request_id in self.active_executions:
            await self.logger.info(f"Cancelling execution: {request_id}")
            # Implementation would involve cancelling the actual task
            return True
        
        return False
    
    async def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        return {
            **self.stats.copy(),
            "active_executions": len(self.active_executions),
            "queue_size": self.execution_queue.qsize(),
            "worker_count": len(self.worker_tasks),
            "is_running": self.is_running
        }
    
    async def get_recent_executions(self, limit: int = 100) -> List[ExecutionResult]:
        """Get recent execution results."""
        return self.execution_history[-limit:]
    
    async def clear_execution_history(self) -> None:
        """Clear execution history."""
        self.execution_history.clear()
        await self.logger.info("Execution history cleared")


class ToolExecutionManager(BaseComponent):
    """
    High-level manager for tool execution with multiple pipelines.
    """
    
    def __init__(self, name: str = "tool_execution_manager"):
        super().__init__(name)
        self.pipelines: Dict[str, ToolExecutionPipeline] = {}
        self.default_pipeline: Optional[ToolExecutionPipeline] = None
    
    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize execution manager."""
        config = config or {}
        
        # Create default pipeline
        self.default_pipeline = ToolExecutionPipeline("default_pipeline")
        await self.default_pipeline.initialize(config.get("default_pipeline", {}))
        await self.default_pipeline.start()
        
        self.pipelines["default"] = self.default_pipeline
        
        await self.logger.info("Tool execution manager initialized")
    
    async def create_pipeline(self, name: str, config: Optional[Dict[str, Any]] = None) -> ToolExecutionPipeline:
        """Create a new execution pipeline."""
        if name in self.pipelines:
            raise ValueError(f"Pipeline '{name}' already exists")
        
        pipeline = ToolExecutionPipeline(f"pipeline_{name}")
        await pipeline.initialize(config or {})
        await pipeline.start()
        
        self.pipelines[name] = pipeline
        await self.logger.info(f"Created pipeline: {name}")
        
        return pipeline
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any],
                          pipeline_name: str = "default", **kwargs) -> ExecutionResult:
        """Execute tool on specified pipeline."""
        if pipeline_name not in self.pipelines:
            raise ValueError(f"Pipeline '{pipeline_name}' not found")
        
        pipeline = self.pipelines[pipeline_name]
        request_id = f"{pipeline_name}_{tool_name}_{time.time()}"
        
        return await pipeline.execute_tool(request_id, tool_name, arguments, **kwargs)
    
    async def stop_all_pipelines(self) -> None:
        """Stop all execution pipelines."""
        for pipeline in self.pipelines.values():
            await pipeline.stop()
        
        self.pipelines.clear()
        self.default_pipeline = None
        await self.logger.info("All pipelines stopped")