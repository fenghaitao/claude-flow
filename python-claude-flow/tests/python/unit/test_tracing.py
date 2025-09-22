"""
Tests for the tracing and logging system.
"""

import asyncio
import json
import logging
import os
import tempfile
import uuid
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from claude_flow.core.config import ConfigManager
from claude_flow.monitoring.tracing import (
    TracingManager,
    LoggingManager,
    ObservabilityManager,
    StructuredLogger,
    TraceContext,
    LogEntry,
    LogLevel,
    SpanKind,
    get_logger,
    trace_span,
    async_trace_span,
    trace_function,
    setup_observability
)


class TestStructuredLogger:
    """Test the structured logger."""
    
    def test_logger_creation(self):
        """Test logger creation."""
        logger = StructuredLogger("test.logger")
        assert logger.name == "test.logger"
        assert logger.logger is not None
    
    def test_logging_methods(self):
        """Test different logging methods."""
        logger = StructuredLogger("test.logger")
        
        # These shouldn't raise exceptions
        logger.debug("Debug message", extra_field="debug_value")
        logger.info("Info message", extra_field="info_value")
        logger.warning("Warning message", extra_field="warning_value")
        logger.error("Error message", extra_field="error_value")
        logger.critical("Critical message", extra_field="critical_value")
    
    def test_logging_with_exception(self):
        """Test logging with exception information."""
        logger = StructuredLogger("test.logger")
        
        try:
            raise ValueError("Test exception")
        except Exception as e:
            logger.error("An error occurred", exception=e)
            logger.critical("A critical error occurred", exception=e)


class TestTracingManager:
    """Test the tracing manager."""
    
    @pytest.fixture
    def config_manager(self):
        """Create a test configuration manager."""
        config_data = {
            "tracing": {
                "service_name": "test-service",
                "service_version": "1.0.0",
                "environment": "test",
                "console_export": True,
                "auto_instrument": False,
                "sample_rate": 1.0
            }
        }
        return ConfigManager(config_data)
    
    @pytest.fixture
    def tracing_manager(self, config_manager):
        """Create a test tracing manager."""
        return TracingManager(config_manager)
    
    @pytest.mark.asyncio
    async def test_initialization(self, tracing_manager):
        """Test tracing manager initialization."""
        await tracing_manager.initialize()
        
        assert tracing_manager.tracer_provider is not None
        assert tracing_manager.tracer is not None
        assert tracing_manager.service_name == "test-service"
    
    @pytest.mark.asyncio
    async def test_trace_span_context_manager(self, tracing_manager):
        """Test trace span context manager."""
        await tracing_manager.initialize()
        
        with tracing_manager.trace_span("test.operation") as span:
            assert span is not None
            span.set_attribute("test.attribute", "test_value")
    
    @pytest.mark.asyncio
    async def test_async_trace_span_context_manager(self, tracing_manager):
        """Test async trace span context manager."""
        await tracing_manager.initialize()
        
        async with tracing_manager.async_trace_span("test.async_operation") as span:
            assert span is not None
            span.set_attribute("test.attribute", "test_value")
            await asyncio.sleep(0.001)  # Simulate async work
    
    @pytest.mark.asyncio
    async def test_trace_function_decorator_sync(self, tracing_manager):
        """Test trace function decorator for sync functions."""
        await tracing_manager.initialize()
        
        @tracing_manager.trace_function("test.sync_function")
        def test_sync_function(x, y):
            return x + y
        
        result = test_sync_function(1, 2)
        assert result == 3
    
    @pytest.mark.asyncio
    async def test_trace_function_decorator_async(self, tracing_manager):
        """Test trace function decorator for async functions."""
        await tracing_manager.initialize()
        
        @tracing_manager.trace_function("test.async_function")
        async def test_async_function(x, y):
            await asyncio.sleep(0.001)
            return x + y
        
        result = await test_async_function(1, 2)
        assert result == 3
    
    @pytest.mark.asyncio
    async def test_baggage_operations(self, tracing_manager):
        """Test baggage operations."""
        await tracing_manager.initialize()
        
        tracing_manager.set_baggage("user_id", "12345")
        tracing_manager.set_baggage("session_id", "abcdef")
        
        user_id = tracing_manager.get_baggage("user_id")
        session_id = tracing_manager.get_baggage("session_id")
        
        assert user_id == "12345"
        assert session_id == "abcdef"
    
    @pytest.mark.asyncio
    async def test_trace_context_retrieval(self, tracing_manager):
        """Test trace context retrieval."""
        await tracing_manager.initialize()
        
        with tracing_manager.trace_span("test.context") as span:
            tracing_manager.set_baggage("test_key", "test_value")
            
            context = tracing_manager.get_current_trace_context()
            
            assert context is not None
            assert context.service_name == "test-service"
            assert "test_key" in context.baggage
            assert context.baggage["test_key"] == "test_value"


class TestLoggingManager:
    """Test the logging manager."""
    
    @pytest.fixture
    def temp_log_file(self):
        """Create a temporary log file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            yield f.name
        
        # Cleanup
        try:
            os.unlink(f.name)
        except OSError:
            pass
    
    @pytest.fixture
    def config_manager(self, temp_log_file):
        """Create a test configuration manager."""
        config_data = {
            "logging": {
                "level": "DEBUG",
                "format": "json",
                "file": temp_log_file,
                "max_file_size": 1024 * 1024,
                "backup_count": 3,
                "include_trace_info": True,
                "correlation_id": True
            }
        }
        return ConfigManager(config_data)
    
    @pytest.fixture
    def logging_manager(self, config_manager):
        """Create a test logging manager."""
        return LoggingManager(config_manager)
    
    @pytest.mark.asyncio
    async def test_initialization(self, logging_manager):
        """Test logging manager initialization."""
        await logging_manager.initialize()
        assert logging_manager.logger is not None
    
    @pytest.mark.asyncio
    async def test_logger_creation(self, logging_manager):
        """Test logger creation and retrieval."""
        await logging_manager.initialize()
        
        logger1 = logging_manager.get_logger("test.module1")
        logger2 = logging_manager.get_logger("test.module2")
        logger1_again = logging_manager.get_logger("test.module1")
        
        assert logger1 is not None
        assert logger2 is not None
        assert logger1 is logger1_again  # Should return same instance
        assert logger1 is not logger2
    
    @pytest.mark.asyncio
    async def test_log_file_creation(self, logging_manager, temp_log_file):
        """Test that log file is created and written to."""
        await logging_manager.initialize()
        
        logger = logging_manager.get_logger("test.logger")
        logger.info("Test log message", test_field="test_value")
        
        # Force flush
        logging.getLogger().handlers[1].flush()  # File handler
        
        # Check that file exists and has content
        log_path = Path(temp_log_file)
        assert log_path.exists()
        assert log_path.stat().st_size > 0


class TestObservabilityManager:
    """Test the observability manager."""
    
    @pytest.fixture
    def config_manager(self):
        """Create a test configuration manager."""
        config_data = {
            "tracing": {
                "service_name": "test-service",
                "console_export": True,
                "auto_instrument": False
            },
            "logging": {
                "level": "INFO",
                "format": "json",
                "include_trace_info": True
            }
        }
        return ConfigManager(config_data)
    
    @pytest.fixture
    def observability_manager(self, config_manager):
        """Create a test observability manager."""
        return ObservabilityManager(config_manager)
    
    @pytest.mark.asyncio
    async def test_initialization(self, observability_manager):
        """Test observability manager initialization."""
        await observability_manager.initialize()
        
        assert observability_manager.tracing_manager is not None
        assert observability_manager.logging_manager is not None
        assert observability_manager.logger is not None
    
    @pytest.mark.asyncio
    async def test_integrated_logging_and_tracing(self, observability_manager):
        """Test integrated logging and tracing."""
        await observability_manager.initialize()
        
        logger = observability_manager.get_logger("test.integration")
        
        with observability_manager.trace_span("test.integrated_operation") as span:
            logger.info("Starting operation")
            span.set_attribute("operation.type", "test")
            
            logger.info("Operation in progress", step="middle")
            
            logger.info("Operation completed")
    
    @pytest.mark.asyncio
    async def test_convenience_functions(self, observability_manager):
        """Test convenience functions."""
        await observability_manager.initialize()
        
        # Test trace_function decorator
        @observability_manager.trace_function("test.decorated_function")
        def test_function():
            return "success"
        
        result = test_function()
        assert result == "success"
        
        # Test async trace_function decorator
        @observability_manager.trace_function("test.async_decorated_function")
        async def test_async_function():
            await asyncio.sleep(0.001)
            return "async_success"
        
        result = await test_async_function()
        assert result == "async_success"


class TestGlobalFunctions:
    """Test global convenience functions."""
    
    @pytest.fixture
    def config_manager(self):
        """Create a test configuration manager."""
        config_data = {
            "tracing": {
                "service_name": "test-global",
                "console_export": True,
                "auto_instrument": False
            },
            "logging": {
                "level": "INFO",
                "format": "json"
            }
        }
        return ConfigManager(config_data)
    
    @pytest.mark.asyncio
    async def test_setup_observability(self, config_manager):
        """Test global observability setup."""
        observability = setup_observability(config_manager)
        await observability.initialize()
        
        assert observability is not None
        
        # Test global logger function
        logger = get_logger("test.global")
        assert logger is not None
        
        logger.info("Test global logging")
    
    def test_global_functions_without_setup(self):
        """Test global functions work without setup (fallback mode)."""
        # This should not raise exceptions
        logger = get_logger("test.fallback")
        logger.info("Fallback logging")
        
        # Trace functions should return no-op managers
        with trace_span("test.noop"):
            pass
        
        @trace_function("test.noop_function")
        def test_func():
            return "noop"
        
        result = test_func()
        assert result == "noop"


class TestTraceContext:
    """Test trace context data structure."""
    
    def test_trace_context_creation(self):
        """Test trace context creation."""
        context = TraceContext(
            trace_id="12345678901234567890123456789012",
            span_id="1234567890123456"
        )
        
        assert context.trace_id == "12345678901234567890123456789012"
        assert context.span_id == "1234567890123456"
        assert context.correlation_id is not None
        assert context.service_name == "claude-flow"
    
    def test_trace_context_with_custom_values(self):
        """Test trace context with custom values."""
        context = TraceContext(
            trace_id="abcdef123456789012345678901234ab",
            span_id="abcdef1234567890",
            user_id="user123",
            session_id="session456",
            service_name="custom-service"
        )
        
        assert context.user_id == "user123"
        assert context.session_id == "session456"
        assert context.service_name == "custom-service"


class TestLogEntry:
    """Test log entry data structure."""
    
    def test_log_entry_creation(self):
        """Test log entry creation."""
        from datetime import datetime, timezone
        
        now = datetime.now(timezone.utc)
        entry = LogEntry(
            timestamp=now,
            level=LogLevel.INFO,
            message="Test message",
            logger_name="test.logger"
        )
        
        assert entry.timestamp == now
        assert entry.level == LogLevel.INFO
        assert entry.message == "Test message"
        assert entry.logger_name == "test.logger"
        assert entry.service_name == "claude-flow"
    
    def test_log_entry_with_trace_info(self):
        """Test log entry with trace information."""
        from datetime import datetime, timezone
        
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc),
            level=LogLevel.ERROR,
            message="Error message",
            logger_name="test.error",
            trace_id="trace123",
            span_id="span456",
            correlation_id="corr789",
            user_id="user123"
        )
        
        assert entry.trace_id == "trace123"
        assert entry.span_id == "span456"
        assert entry.correlation_id == "corr789"
        assert entry.user_id == "user123"


@pytest.mark.integration
class TestTracingIntegration:
    """Integration tests for tracing system."""
    
    @pytest.fixture
    def config_manager(self):
        """Create a test configuration manager."""
        config_data = {
            "tracing": {
                "service_name": "integration-test",
                "environment": "test",
                "console_export": True,
                "auto_instrument": False,
                "sample_rate": 1.0
            },
            "logging": {
                "level": "DEBUG",
                "format": "json"
            }
        }
        return ConfigManager(config_data)
    
    @pytest.mark.asyncio
    async def test_full_observability_workflow(self, config_manager):
        """Test a complete observability workflow."""
        # Setup observability
        observability = setup_observability(config_manager)
        await observability.initialize()
        
        logger = get_logger("integration.test")
        
        # Simulate a complex operation with nested spans
        with trace_span("integration.main_operation") as main_span:
            logger.info("Starting main operation")
            main_span.set_attribute("operation.type", "integration_test")
            
            # Nested operation 1
            with trace_span("integration.sub_operation_1") as sub_span1:
                logger.info("Sub operation 1", operation_id="sub1")
                sub_span1.set_attribute("sub_operation.id", "1")
                await asyncio.sleep(0.01)
            
            # Nested operation 2
            async with async_trace_span("integration.sub_operation_2") as sub_span2:
                logger.info("Sub operation 2", operation_id="sub2")
                sub_span2.set_attribute("sub_operation.id", "2")
                await asyncio.sleep(0.01)
            
            # Simulated error handling
            try:
                raise ValueError("Simulated error")
            except Exception as e:
                logger.error("An error occurred during operation", exception=e)
                main_span.set_attribute("error.occurred", True)
            
            logger.info("Main operation completed")
        
        # Test decorated functions
        @trace_function("integration.decorated_sync")
        def sync_operation(x: int) -> int:
            logger.info("Sync operation", input_value=x)
            return x * 2
        
        @trace_function("integration.decorated_async")
        async def async_operation(x: int) -> int:
            logger.info("Async operation", input_value=x)
            await asyncio.sleep(0.001)
            return x * 3
        
        sync_result = sync_operation(5)
        async_result = await async_operation(7)
        
        assert sync_result == 10
        assert async_result == 21
        
        logger.info("Integration test completed", 
                   sync_result=sync_result, 
                   async_result=async_result)