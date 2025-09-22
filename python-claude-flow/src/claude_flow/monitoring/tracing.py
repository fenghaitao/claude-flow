"""
Distributed tracing and logging system for Claude-Flow.

This module provides comprehensive distributed tracing with OpenTelemetry,
structured logging with correlation IDs, and enterprise-grade observability.
"""

import asyncio
import json
import logging
import time
import traceback
import uuid
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from typing import Any, Dict, List, Optional, Union, AsyncGenerator, Iterator
from pathlib import Path

import structlog
from opentelemetry import trace, baggage
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.instrumentation.asyncio import AsyncioInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import Status, StatusCode
from opentelemetry.util.http import get_excluded_urls

from ..core.interfaces import BaseComponent
from ..core.config import ConfigManager


class LogLevel(str, Enum):
    """Log level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class SpanKind(str, Enum):
    """Span kind enumeration."""
    INTERNAL = "INTERNAL"
    SERVER = "SERVER"
    CLIENT = "CLIENT"
    PRODUCER = "PRODUCER"
    CONSUMER = "CONSUMER"


@dataclass
class TraceContext:
    """Trace context information."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    service_name: str = "claude-flow"
    operation_name: Optional[str] = None
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: Dict[str, Any] = field(default_factory=dict)
    baggage: Dict[str, str] = field(default_factory=dict)


@dataclass
class LogEntry:
    """Structured log entry."""
    timestamp: datetime
    level: LogLevel
    message: str
    logger_name: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    service_name: str = "claude-flow"
    module: Optional[str] = None
    function: Optional[str] = None
    line_number: Optional[int] = None
    exception: Optional[str] = None
    stack_trace: Optional[str] = None
    extra_data: Dict[str, Any] = field(default_factory=dict)


class StructuredLogger:
    """Structured logger with correlation ID support."""
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self._setup_structured_logging()
    
    def _setup_structured_logging(self) -> None:
        """Setup structured logging configuration."""
        # Configure structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        # Get the structured logger
        self.logger = structlog.get_logger(self.name)
    
    def _get_trace_context(self) -> Dict[str, Any]:
        """Get current trace context."""
        context = {}
        
        # Get OpenTelemetry context
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            span_context = current_span.get_span_context()
            context.update({
                "trace_id": format(span_context.trace_id, "032x"),
                "span_id": format(span_context.span_id, "016x"),
            })
        
        # Get baggage
        bag = baggage.get_all()
        if bag:
            context["baggage"] = bag
        
        return context
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self.logger.debug(message, **self._get_trace_context(), **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self.logger.info(message, **self._get_trace_context(), **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self.logger.warning(message, **self._get_trace_context(), **kwargs)
    
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs) -> None:
        """Log error message."""
        context = self._get_trace_context()
        if exception:
            context["exception"] = str(exception)
            context["exception_type"] = type(exception).__name__
        self.logger.error(message, **context, **kwargs)
    
    def critical(self, message: str, exception: Optional[Exception] = None, **kwargs) -> None:
        """Log critical message."""
        context = self._get_trace_context()
        if exception:
            context["exception"] = str(exception)
            context["exception_type"] = type(exception).__name__
        self.logger.critical(message, **context, **kwargs)


class TracingManager(BaseComponent):
    """Distributed tracing manager with OpenTelemetry."""
    
    def __init__(self, config: ConfigManager):
        super().__init__(config)
        self.tracer_provider: Optional[TracerProvider] = None
        self.tracer = None
        self.span_processors: List[BatchSpanProcessor] = []
        self.logger = StructuredLogger(__name__)
        
        # Configuration
        self.service_name = self.config.get("tracing.service_name", "claude-flow")
        self.service_version = self.config.get("tracing.service_version", "1.0.0")
        self.environment = self.config.get("tracing.environment", "development")
        
        # Exporters
        self.jaeger_endpoint = self.config.get("tracing.jaeger.endpoint")
        self.otlp_endpoint = self.config.get("tracing.otlp.endpoint")
        self.console_export = self.config.get("tracing.console_export", False)
        
        # Sampling
        self.sample_rate = self.config.get("tracing.sample_rate", 1.0)
        
        # Instrumentation
        self.auto_instrument = self.config.get("tracing.auto_instrument", True)
    
    async def initialize(self) -> None:
        """Initialize the tracing system."""
        try:
            self._setup_tracer_provider()
            self._setup_exporters()
            self._setup_instrumentation()
            
            self.logger.info(
                "Tracing system initialized",
                service_name=self.service_name,
                exporters=self._get_active_exporters()
            )
            
        except Exception as e:
            self.logger.error("Failed to initialize tracing system", exception=e)
            raise
    
    def _setup_tracer_provider(self) -> None:
        """Setup the tracer provider with resource information."""
        resource = Resource.create({
            "service.name": self.service_name,
            "service.version": self.service_version,
            "deployment.environment": self.environment,
            "telemetry.sdk.language": "python",
            "telemetry.sdk.name": "opentelemetry",
        })
        
        self.tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(self.tracer_provider)
        
        # Set B3 propagator for distributed tracing
        set_global_textmap(B3MultiFormat())
        
        # Get tracer
        self.tracer = trace.get_tracer(__name__)
    
    def _setup_exporters(self) -> None:
        """Setup span exporters."""
        exporters = []
        
        # Console exporter for development
        if self.console_export:
            console_exporter = ConsoleSpanExporter()
            console_processor = BatchSpanProcessor(console_exporter)
            self.tracer_provider.add_span_processor(console_processor)
            self.span_processors.append(console_processor)
            exporters.append("console")
        
        # Jaeger exporter
        if self.jaeger_endpoint:
            jaeger_exporter = JaegerExporter(
                agent_host_name=self.jaeger_endpoint.split(":")[0],
                agent_port=int(self.jaeger_endpoint.split(":")[1]) if ":" in self.jaeger_endpoint else 14268,
                collector_endpoint=f"http://{self.jaeger_endpoint}/api/traces",
            )
            jaeger_processor = BatchSpanProcessor(jaeger_exporter)
            self.tracer_provider.add_span_processor(jaeger_processor)
            self.span_processors.append(jaeger_processor)
            exporters.append("jaeger")
        
        # OTLP exporter
        if self.otlp_endpoint:
            otlp_exporter = OTLPSpanExporter(endpoint=self.otlp_endpoint)
            otlp_processor = BatchSpanProcessor(otlp_exporter)
            self.tracer_provider.add_span_processor(otlp_processor)
            self.span_processors.append(otlp_processor)
            exporters.append("otlp")
        
        if not exporters:
            self.logger.warning("No span exporters configured")
    
    def _setup_instrumentation(self) -> None:
        """Setup automatic instrumentation."""
        if not self.auto_instrument:
            return
        
        try:
            # HTTP client instrumentation
            RequestsInstrumentor().instrument()
            AioHttpClientInstrumentor().instrument()
            
            # Asyncio instrumentation
            AsyncioInstrumentor().instrument()
            
            # Logging instrumentation
            LoggingInstrumentor().instrument(set_logging_format=True)
            
            # Database instrumentation
            SQLAlchemyInstrumentor().instrument()
            
            self.logger.info("Automatic instrumentation enabled")
            
        except Exception as e:
            self.logger.warning("Failed to setup some instrumentations", exception=e)
    
    def _get_active_exporters(self) -> List[str]:
        """Get list of active exporters."""
        exporters = []
        if self.console_export:
            exporters.append("console")
        if self.jaeger_endpoint:
            exporters.append("jaeger")
        if self.otlp_endpoint:
            exporters.append("otlp")
        return exporters
    
    @contextmanager
    def trace_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
        set_status_on_exception: bool = True
    ) -> Iterator[trace.Span]:
        """Create a traced span context manager."""
        if not self.tracer:
            # If tracing is not initialized, yield a no-op span
            yield trace.NonRecordingSpan(trace.INVALID_SPAN_CONTEXT)
            return
        
        span_kind_map = {
            SpanKind.INTERNAL: trace.SpanKind.INTERNAL,
            SpanKind.SERVER: trace.SpanKind.SERVER,
            SpanKind.CLIENT: trace.SpanKind.CLIENT,
            SpanKind.PRODUCER: trace.SpanKind.PRODUCER,
            SpanKind.CONSUMER: trace.SpanKind.CONSUMER,
        }
        
        with self.tracer.start_as_current_span(
            name,
            kind=span_kind_map.get(kind, trace.SpanKind.INTERNAL)
        ) as span:
            try:
                # Set attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                yield span
                
            except Exception as e:
                if set_status_on_exception:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                raise
    
    @asynccontextmanager
    async def async_trace_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
        set_status_on_exception: bool = True
    ) -> AsyncGenerator[trace.Span, None]:
        """Create an async traced span context manager."""
        if not self.tracer:
            # If tracing is not initialized, yield a no-op span
            yield trace.NonRecordingSpan(trace.INVALID_SPAN_CONTEXT)
            return
        
        span_kind_map = {
            SpanKind.INTERNAL: trace.SpanKind.INTERNAL,
            SpanKind.SERVER: trace.SpanKind.SERVER,
            SpanKind.CLIENT: trace.SpanKind.CLIENT,
            SpanKind.PRODUCER: trace.SpanKind.PRODUCER,
            SpanKind.CONSUMER: trace.SpanKind.CONSUMER,
        }
        
        with self.tracer.start_as_current_span(
            name,
            kind=span_kind_map.get(kind, trace.SpanKind.INTERNAL)
        ) as span:
            try:
                # Set attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                yield span
                
            except Exception as e:
                if set_status_on_exception:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                raise
    
    def trace_function(
        self,
        name: Optional[str] = None,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None
    ):
        """Decorator to trace function calls."""
        def decorator(func):
            span_name = name or f"{func.__module__}.{func.__qualname__}"
            
            if asyncio.iscoroutinefunction(func):
                @wraps(func)
                async def async_wrapper(*args, **kwargs):
                    async with self.async_trace_span(span_name, kind, attributes) as span:
                        # Add function metadata
                        span.set_attribute("function.name", func.__name__)
                        span.set_attribute("function.module", func.__module__)
                        
                        return await func(*args, **kwargs)
                return async_wrapper
            else:
                @wraps(func)
                def sync_wrapper(*args, **kwargs):
                    with self.trace_span(span_name, kind, attributes) as span:
                        # Add function metadata
                        span.set_attribute("function.name", func.__name__)
                        span.set_attribute("function.module", func.__module__)
                        
                        return func(*args, **kwargs)
                return sync_wrapper
        
        return decorator
    
    def set_baggage(self, key: str, value: str) -> None:
        """Set baggage for cross-service context propagation."""
        baggage.set_baggage(key, value)
    
    def get_baggage(self, key: str) -> Optional[str]:
        """Get baggage value."""
        return baggage.get_baggage(key)
    
    def get_current_trace_context(self) -> Optional[TraceContext]:
        """Get current trace context."""
        current_span = trace.get_current_span()
        if not current_span or not current_span.is_recording():
            return None
        
        span_context = current_span.get_span_context()
        
        return TraceContext(
            trace_id=format(span_context.trace_id, "032x"),
            span_id=format(span_context.span_id, "016x"),
            baggage=baggage.get_all() or {},
            service_name=self.service_name
        )
    
    async def cleanup(self) -> None:
        """Cleanup tracing resources."""
        try:
            # Shutdown span processors
            for processor in self.span_processors:
                processor.shutdown()
            
            self.logger.info("Tracing system cleaned up")
            
        except Exception as e:
            self.logger.error("Error during tracing cleanup", exception=e)


class LoggingManager(BaseComponent):
    """Centralized logging manager with correlation ID support."""
    
    def __init__(self, config: ConfigManager):
        super().__init__(config)
        self.loggers: Dict[str, StructuredLogger] = {}
        
        # Configuration
        self.log_level = self.config.get("logging.level", "INFO")
        self.log_format = self.config.get("logging.format", "json")
        self.log_file = self.config.get("logging.file")
        self.max_file_size = self.config.get("logging.max_file_size", 10 * 1024 * 1024)  # 10MB
        self.backup_count = self.config.get("logging.backup_count", 5)
        
        # Structured logging configuration
        self.include_trace_info = self.config.get("logging.include_trace_info", True)
        self.log_correlation_id = self.config.get("logging.correlation_id", True)
    
    async def initialize(self) -> None:
        """Initialize the logging system."""
        try:
            self._setup_root_logger()
            self.logger = self.get_logger(__name__)
            
            self.logger.info(
                "Logging system initialized",
                log_level=self.log_level,
                log_format=self.log_format,
                log_file=self.log_file
            )
            
        except Exception as e:
            print(f"Failed to initialize logging system: {e}")
            raise
    
    def _setup_root_logger(self) -> None:
        """Setup root logger configuration."""
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.log_level.upper()))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, self.log_level.upper()))
        
        if self.log_format == "json":
            formatter = logging.Formatter(
                '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
                '"logger": "%(name)s", "message": "%(message)s"}'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # File handler if configured
        if self.log_file:
            from logging.handlers import RotatingFileHandler
            
            log_path = Path(self.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = RotatingFileHandler(
                self.log_file,
                maxBytes=self.max_file_size,
                backupCount=self.backup_count
            )
            file_handler.setLevel(getattr(logging, self.log_level.upper()))
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
    
    def get_logger(self, name: str) -> StructuredLogger:
        """Get or create a structured logger."""
        if name not in self.loggers:
            config = {
                "include_trace_info": self.include_trace_info,
                "correlation_id": self.log_correlation_id,
                "level": self.log_level,
                "format": self.log_format
            }
            self.loggers[name] = StructuredLogger(name, config)
        
        return self.loggers[name]
    
    def set_correlation_id(self, correlation_id: str) -> None:
        """Set correlation ID for all loggers."""
        # This would be implemented using context variables
        # for thread-safe correlation ID handling
        pass
    
    async def cleanup(self) -> None:
        """Cleanup logging resources."""
        try:
            # Flush all handlers
            for handler in logging.getLogger().handlers:
                handler.flush()
            
            print("Logging system cleaned up")
            
        except Exception as e:
            print(f"Error during logging cleanup: {e}")


class ObservabilityManager(BaseComponent):
    """Combined observability manager for tracing and logging."""
    
    def __init__(self, config: ConfigManager):
        super().__init__(config)
        self.tracing_manager = TracingManager(config)
        self.logging_manager = LoggingManager(config)
        self.logger = None
    
    async def initialize(self) -> None:
        """Initialize observability systems."""
        try:
            # Initialize logging first
            await self.logging_manager.initialize()
            self.logger = self.logging_manager.get_logger(__name__)
            
            # Initialize tracing
            await self.tracing_manager.initialize()
            
            self.logger.info("Observability system initialized")
            
        except Exception as e:
            if self.logger:
                self.logger.error("Failed to initialize observability system", exception=e)
            else:
                print(f"Failed to initialize observability system: {e}")
            raise
    
    def get_logger(self, name: str) -> StructuredLogger:
        """Get a structured logger."""
        return self.logging_manager.get_logger(name)
    
    def trace_span(self, *args, **kwargs):
        """Create a traced span."""
        return self.tracing_manager.trace_span(*args, **kwargs)
    
    def async_trace_span(self, *args, **kwargs):
        """Create an async traced span."""
        return self.tracing_manager.async_trace_span(*args, **kwargs)
    
    def trace_function(self, *args, **kwargs):
        """Decorator to trace function calls."""
        return self.tracing_manager.trace_function(*args, **kwargs)
    
    async def cleanup(self) -> None:
        """Cleanup observability resources."""
        try:
            if self.tracing_manager:
                await self.tracing_manager.cleanup()
            
            if self.logging_manager:
                await self.logging_manager.cleanup()
                
        except Exception as e:
            print(f"Error during observability cleanup: {e}")


# Global observability instance
_observability_manager: Optional[ObservabilityManager] = None


def get_observability() -> Optional[ObservabilityManager]:
    """Get the global observability manager."""
    return _observability_manager


def setup_observability(config: ConfigManager) -> ObservabilityManager:
    """Setup global observability manager."""
    global _observability_manager
    _observability_manager = ObservabilityManager(config)
    return _observability_manager


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance."""
    if _observability_manager:
        return _observability_manager.get_logger(name)
    else:
        # Fallback to basic structured logger
        return StructuredLogger(name)


def trace_span(*args, **kwargs):
    """Create a traced span (global convenience function)."""
    if _observability_manager:
        return _observability_manager.trace_span(*args, **kwargs)
    else:
        # Return a no-op context manager
        @contextmanager
        def noop_span():
            yield None
        return noop_span()


def async_trace_span(*args, **kwargs):
    """Create an async traced span (global convenience function)."""
    if _observability_manager:
        return _observability_manager.async_trace_span(*args, **kwargs)
    else:
        # Return a no-op async context manager
        @asynccontextmanager
        async def noop_async_span():
            yield None
        return noop_async_span()


def trace_function(*args, **kwargs):
    """Decorator to trace function calls (global convenience function)."""
    if _observability_manager:
        return _observability_manager.trace_function(*args, **kwargs)
    else:
        # Return a no-op decorator
        def noop_decorator(func):
            return func
        return noop_decorator