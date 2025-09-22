"""
Prometheus Metrics Collection for Claude-Flow.

Provides comprehensive metrics collection and export for monitoring
system performance, agent behavior, and operational health.
"""

import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
import asyncio
import logging
from prometheus_client import (
    Counter, Histogram, Gauge, Summary, Info,
    CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST,
    start_http_server
)

from ..core.interfaces import BaseComponent


@dataclass
class MetricConfig:
    """Configuration for metrics collection."""
    enabled: bool = True
    export_port: int = 8000
    export_interval: float = 15.0  # seconds
    namespace: str = "claude_flow"
    labels: Dict[str, str] = field(default_factory=dict)
    
    # Metric retention
    histogram_buckets: List[float] = field(default_factory=lambda: [
        0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0
    ])
    
    # Collection settings
    collect_system_metrics: bool = True
    collect_agent_metrics: bool = True
    collect_claude_metrics: bool = True
    collect_memory_metrics: bool = True
    collect_event_metrics: bool = True


class PrometheusMetrics(BaseComponent):
    """Prometheus metrics collector and exporter."""
    
    def __init__(self, config: MetricConfig):
        super().__init__()
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Create custom registry
        self.registry = CollectorRegistry()
        
        # System metrics
        self.system_info = Info(
            'claude_flow_system_info',
            'System information',
            registry=self.registry
        )
        
        self.uptime_seconds = Gauge(
            'claude_flow_uptime_seconds',
            'System uptime in seconds',
            registry=self.registry
        )
        
        # Agent metrics
        self.agents_total = Gauge(
            'claude_flow_agents_total',
            'Total number of agents',
            ['type', 'state'],
            registry=self.registry
        )
        
        self.tasks_total = Counter(
            'claude_flow_tasks_total',
            'Total number of tasks processed',
            ['agent_type', 'status'],
            registry=self.registry
        )
        
        self.task_duration_seconds = Histogram(
            'claude_flow_task_duration_seconds',
            'Task execution duration in seconds',
            ['agent_type', 'task_type'],
            buckets=config.histogram_buckets,
            registry=self.registry
        )
        
        self.agent_utilization = Gauge(
            'claude_flow_agent_utilization_ratio',
            'Agent utilization ratio (0-1)',
            ['agent_id', 'agent_type'],
            registry=self.registry
        )
        
        # Claude AI metrics
        self.claude_requests_total = Counter(
            'claude_flow_claude_requests_total',
            'Total Claude API requests',
            ['model', 'status'],
            registry=self.registry
        )
        
        self.claude_request_duration_seconds = Histogram(
            'claude_flow_claude_request_duration_seconds',
            'Claude API request duration in seconds',
            ['model'],
            buckets=config.histogram_buckets,
            registry=self.registry
        )
        
        self.claude_tokens_total = Counter(
            'claude_flow_claude_tokens_total',
            'Total tokens used',
            ['model', 'type'],  # type: input/output
            registry=self.registry
        )
        
        self.claude_rate_limits = Gauge(
            'claude_flow_claude_rate_limit_remaining',
            'Remaining rate limit capacity',
            ['model', 'limit_type'],  # limit_type: requests/tokens
            registry=self.registry
        )
        
        # Memory metrics
        self.memory_entries_total = Gauge(
            'claude_flow_memory_entries_total',
            'Total number of memory entries',
            ['storage_type'],
            registry=self.registry
        )
        
        self.memory_size_bytes = Gauge(
            'claude_flow_memory_size_bytes',
            'Memory storage size in bytes',
            ['storage_type'],
            registry=self.registry
        )
        
        self.memory_operations_total = Counter(
            'claude_flow_memory_operations_total',
            'Total memory operations',
            ['operation', 'status'],
            registry=self.registry
        )
        
        self.memory_search_duration_seconds = Histogram(
            'claude_flow_memory_search_duration_seconds',
            'Memory search duration in seconds',
            ['search_type'],
            buckets=config.histogram_buckets,
            registry=self.registry
        )
        
        # Event metrics
        self.events_total = Counter(
            'claude_flow_events_total',
            'Total events processed',
            ['event_type', 'status'],
            registry=self.registry
        )
        
        self.event_queue_size = Gauge(
            'claude_flow_event_queue_size',
            'Current event queue size',
            registry=self.registry
        )
        
        self.event_processing_duration_seconds = Histogram(
            'claude_flow_event_processing_duration_seconds',
            'Event processing duration in seconds',
            ['event_type'],
            buckets=config.histogram_buckets,
            registry=self.registry
        )
        
        # System resource metrics
        self.cpu_usage_percent = Gauge(
            'claude_flow_cpu_usage_percent',
            'CPU usage percentage',
            registry=self.registry
        )
        
        self.memory_usage_bytes = Gauge(
            'claude_flow_memory_usage_bytes',
            'Memory usage in bytes',
            ['type'],  # type: rss, vms, shared
            registry=self.registry
        )
        
        self.disk_usage_bytes = Gauge(
            'claude_flow_disk_usage_bytes',
            'Disk usage in bytes',
            ['path'],
            registry=self.registry
        )
        
        # HTTP server for metrics export
        self.http_server = None
        self.start_time = time.time()
        
        # Background tasks
        self._metrics_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        """Initialize metrics collection."""
        await super().initialize()
        
        if not self.config.enabled:
            self.logger.info("Metrics collection disabled")
            return
        
        # Set system info
        self.system_info.info({
            'version': '1.0.0',  # Could be retrieved from package
            'python_version': '.'.join(map(str, __import__('sys').version_info[:3])),
            'namespace': self.config.namespace
        })
        
        # Start HTTP server for metrics export
        try:
            self.http_server = start_http_server(
                self.config.export_port,
                registry=self.registry
            )
            self.logger.info(f"Metrics server started on port {self.config.export_port}")
        except Exception as e:
            self.logger.error(f"Failed to start metrics server: {e}")
        
        # Start background metrics collection
        self._metrics_task = asyncio.create_task(self._collect_system_metrics())
        
        self.logger.info("Prometheus metrics initialized")
    
    async def shutdown(self) -> None:
        """Shutdown metrics collection."""
        if self._metrics_task:
            self._metrics_task.cancel()
            try:
                await self._metrics_task
            except asyncio.CancelledError:
                pass
        
        if self.http_server:
            self.http_server.shutdown()
        
        await super().shutdown()
        self.logger.info("Prometheus metrics shutdown")
    
    async def _collect_system_metrics(self) -> None:
        """Continuously collect system metrics."""
        while True:
            try:
                if self.config.collect_system_metrics:
                    await self._update_system_metrics()
                
                await asyncio.sleep(self.config.export_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error collecting system metrics: {e}")
                await asyncio.sleep(self.config.export_interval)
    
    async def _update_system_metrics(self) -> None:
        """Update system resource metrics."""
        try:
            import psutil
            
            # Update uptime
            self.uptime_seconds.set(time.time() - self.start_time)
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=None)
            self.cpu_usage_percent.set(cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.memory_usage_bytes.labels(type='rss').set(memory.used)
            self.memory_usage_bytes.labels(type='available').set(memory.available)
            self.memory_usage_bytes.labels(type='total').set(memory.total)
            
            # Disk usage for current directory
            disk = psutil.disk_usage('.')
            self.disk_usage_bytes.labels(path='.').set(disk.used)
            
        except ImportError:
            self.logger.warning("psutil not available, skipping system metrics")
        except Exception as e:
            self.logger.error(f"Error updating system metrics: {e}")
    
    # Agent metrics methods
    def record_agent_state_change(self, agent_id: str, agent_type: str, old_state: str, new_state: str) -> None:
        """Record agent state change."""
        if not self.config.collect_agent_metrics:
            return
        
        # Decrement old state count
        if old_state:
            self.agents_total.labels(type=agent_type, state=old_state).dec()
        
        # Increment new state count
        self.agents_total.labels(type=agent_type, state=new_state).inc()
    
    def record_task_completion(self, agent_type: str, task_type: str, status: str, duration: float) -> None:
        """Record task completion."""
        if not self.config.collect_agent_metrics:
            return
        
        self.tasks_total.labels(agent_type=agent_type, status=status).inc()
        self.task_duration_seconds.labels(agent_type=agent_type, task_type=task_type).observe(duration)
    
    def update_agent_utilization(self, agent_id: str, agent_type: str, utilization: float) -> None:
        """Update agent utilization metric."""
        if not self.config.collect_agent_metrics:
            return
        
        self.agent_utilization.labels(agent_id=agent_id, agent_type=agent_type).set(utilization)
    
    # Claude AI metrics methods
    def record_claude_request(self, model: str, status: str, duration: float, 
                             input_tokens: int = 0, output_tokens: int = 0) -> None:
        """Record Claude API request."""
        if not self.config.collect_claude_metrics:
            return
        
        self.claude_requests_total.labels(model=model, status=status).inc()
        self.claude_request_duration_seconds.labels(model=model).observe(duration)
        
        if input_tokens > 0:
            self.claude_tokens_total.labels(model=model, type='input').inc(input_tokens)
        if output_tokens > 0:
            self.claude_tokens_total.labels(model=model, type='output').inc(output_tokens)
    
    def update_claude_rate_limits(self, model: str, requests_remaining: int, tokens_remaining: int) -> None:
        """Update Claude rate limit metrics."""
        if not self.config.collect_claude_metrics:
            return
        
        self.claude_rate_limits.labels(model=model, limit_type='requests').set(requests_remaining)
        self.claude_rate_limits.labels(model=model, limit_type='tokens').set(tokens_remaining)
    
    # Memory metrics methods
    def record_memory_operation(self, operation: str, status: str, duration: float = 0) -> None:
        """Record memory operation."""
        if not self.config.collect_memory_metrics:
            return
        
        self.memory_operations_total.labels(operation=operation, status=status).inc()
        
        if duration > 0 and operation == 'search':
            self.memory_search_duration_seconds.labels(search_type=operation).observe(duration)
    
    def update_memory_stats(self, storage_type: str, entry_count: int, size_bytes: int) -> None:
        """Update memory storage statistics."""
        if not self.config.collect_memory_metrics:
            return
        
        self.memory_entries_total.labels(storage_type=storage_type).set(entry_count)
        self.memory_size_bytes.labels(storage_type=storage_type).set(size_bytes)
    
    # Event metrics methods
    def record_event(self, event_type: str, status: str, processing_duration: float = 0) -> None:
        """Record event processing."""
        if not self.config.collect_event_metrics:
            return
        
        self.events_total.labels(event_type=event_type, status=status).inc()
        
        if processing_duration > 0:
            self.event_processing_duration_seconds.labels(event_type=event_type).observe(processing_duration)
    
    def update_event_queue_size(self, size: int) -> None:
        """Update event queue size."""
        if not self.config.collect_event_metrics:
            return
        
        self.event_queue_size.set(size)
    
    # Export methods
    def get_metrics_data(self) -> str:
        """Get metrics data in Prometheus format."""
        return generate_latest(self.registry).decode('utf-8')
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get human-readable metrics summary."""
        summary = {
            'timestamp': time.time(),
            'uptime_seconds': time.time() - self.start_time,
            'metrics_enabled': self.config.enabled,
            'export_port': self.config.export_port
        }
        
        if self.config.enabled:
            # Add metric counts
            summary.update({
                'total_agents': sum(
                    metric.labels(type=t, state=s)._value.get()
                    for metric in [self.agents_total]
                    for t in ['queen', 'architect', 'coder', 'tester']
                    for s in ['idle', 'busy', 'error']
                    if hasattr(metric.labels(type=t, state=s)._value, 'get')
                ),
                'total_tasks': sum(
                    metric.labels(agent_type=at, status=st)._value.get()
                    for metric in [self.tasks_total]
                    for at in ['queen', 'architect', 'coder', 'tester']
                    for st in ['completed', 'failed']
                    if hasattr(metric.labels(agent_type=at, status=st)._value, 'get')
                ),
                'total_events': sum(
                    metric.labels(event_type=et, status=st)._value.get()
                    for metric in [self.events_total]
                    for et in ['task_created', 'task_completed', 'agent_started']
                    for st in ['success', 'error']
                    if hasattr(metric.labels(event_type=et, status=st)._value, 'get')
                )
            })
        
        return summary


class MetricsMiddleware:
    """Middleware for automatic metrics collection."""
    
    def __init__(self, metrics: PrometheusMetrics):
        self.metrics = metrics
    
    async def measure_async_function(self, func_name: str, category: str, func: Callable, *args, **kwargs):
        """Measure async function execution."""
        start_time = time.time()
        status = 'success'
        
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            status = 'error'
            raise
        finally:
            duration = time.time() - start_time
            
            # Record appropriate metrics based on category
            if category == 'agent':
                self.metrics.record_task_completion(
                    agent_type=kwargs.get('agent_type', 'unknown'),
                    task_type=func_name,
                    status=status,
                    duration=duration
                )
            elif category == 'claude':
                self.metrics.record_claude_request(
                    model=kwargs.get('model', 'unknown'),
                    status=status,
                    duration=duration
                )
            elif category == 'memory':
                self.metrics.record_memory_operation(
                    operation=func_name,
                    status=status,
                    duration=duration
                )
            elif category == 'event':
                self.metrics.record_event(
                    event_type=func_name,
                    status=status,
                    processing_duration=duration
                )
    
    def measure_sync_function(self, func_name: str, category: str, func: Callable, *args, **kwargs):
        """Measure sync function execution."""
        start_time = time.time()
        status = 'success'
        
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            status = 'error'
            raise
        finally:
            duration = time.time() - start_time
            
            # Record metrics similar to async version
            if category == 'memory':
                self.metrics.record_memory_operation(
                    operation=func_name,
                    status=status,
                    duration=duration
                )


def metrics_decorator(category: str, func_name: Optional[str] = None):
    """Decorator for automatic metrics collection."""
    def decorator(func):
        nonlocal func_name
        if func_name is None:
            func_name = func.__name__
        
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                # Get metrics instance from first argument if it's a component
                if args and hasattr(args[0], 'metrics') and isinstance(args[0].metrics, PrometheusMetrics):
                    middleware = MetricsMiddleware(args[0].metrics)
                    return await middleware.measure_async_function(func_name, category, func, *args, **kwargs)
                else:
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                # Get metrics instance from first argument if it's a component
                if args and hasattr(args[0], 'metrics') and isinstance(args[0].metrics, PrometheusMetrics):
                    middleware = MetricsMiddleware(args[0].metrics)
                    return middleware.measure_sync_function(func_name, category, func, *args, **kwargs)
                else:
                    return func(*args, **kwargs)
            return sync_wrapper
    
    return decorator