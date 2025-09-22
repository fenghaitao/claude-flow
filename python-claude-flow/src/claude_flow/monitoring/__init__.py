"""
Claude-Flow Monitoring Package.

Comprehensive monitoring, metrics collection, and health checking
for enterprise deployment and observability.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .prometheus_metrics import PrometheusMetrics, MetricConfig
    from .health import HealthMonitor, HealthCheck, SystemStatus
    from .dashboards import Dashboard, AlertManager
    from .tracing import (
        TracingManager, LoggingManager, ObservabilityManager,
        StructuredLogger, TraceContext, LogEntry
    )

__all__ = [
    "PrometheusMetrics",
    "MetricConfig", 
    "HealthMonitor",
    "HealthCheck",
    "SystemStatus",
    "Dashboard",
    "AlertManager",
    "TracingManager",
    "LoggingManager",
    "ObservabilityManager",
    "StructuredLogger",
    "TraceContext",
    "LogEntry",
    "get_logger",
    "trace_span",
    "async_trace_span",
    "trace_function",
    "setup_observability",
    "get_observability"
]

def __getattr__(name: str):
    """Lazy import for monitoring components."""
    if name == "PrometheusMetrics":
        from .prometheus_metrics import PrometheusMetrics
        return PrometheusMetrics
    elif name == "MetricConfig":
        from .prometheus_metrics import MetricConfig
        return MetricConfig
    elif name == "HealthMonitor":
        from .health import HealthMonitor
        return HealthMonitor
    elif name == "HealthCheck":
        from .health import HealthCheck
        return HealthCheck
    elif name == "SystemStatus":
        from .health import SystemStatus
        return SystemStatus
    elif name == "Dashboard":
        from .dashboards import Dashboard
        return Dashboard
    elif name == "AlertManager":
        from .dashboards import AlertManager
        return AlertManager
    elif name == "TracingManager":
        from .tracing import TracingManager
        return TracingManager
    elif name == "LoggingManager":
        from .tracing import LoggingManager
        return LoggingManager
    elif name == "ObservabilityManager":
        from .tracing import ObservabilityManager
        return ObservabilityManager
    elif name == "StructuredLogger":
        from .tracing import StructuredLogger
        return StructuredLogger
    elif name == "TraceContext":
        from .tracing import TraceContext
        return TraceContext
    elif name == "LogEntry":
        from .tracing import LogEntry
        return LogEntry
    elif name == "get_logger":
        from .tracing import get_logger
        return get_logger
    elif name == "trace_span":
        from .tracing import trace_span
        return trace_span
    elif name == "async_trace_span":
        from .tracing import async_trace_span
        return async_trace_span
    elif name == "trace_function":
        from .tracing import trace_function
        return trace_function
    elif name == "setup_observability":
        from .tracing import setup_observability
        return setup_observability
    elif name == "get_observability":
        from .tracing import get_observability
        return get_observability
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")