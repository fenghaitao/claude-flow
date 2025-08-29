"""
Basic tests for Claude-Flow Python port
"""

import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil

from claude_flow.core.config import Config
from claude_flow.core.logger import Logger, get_logger
from claude_flow.core.event_bus import EventBus, EventType, Event


class TestConfig:
    """Test configuration management"""
    
    def test_config_creation(self):
        """Test basic config creation"""
        config = Config()
        assert config.app_name == "claude-flow"
        assert config.version == "2.0.0-alpha.90"
        assert config.environment == "development"
    
    def test_config_validation(self):
        """Test config validation"""
        config = Config()
        errors = config.validate()
        
        # Should have error for missing Claude API key
        assert any("CLAUDE_API_KEY" in error for error in errors)
    
    def test_config_save_load(self, tmp_path):
        """Test config save and load"""
        config = Config()
        config.base_dir = tmp_path
        
        # Save config
        config_path = tmp_path / "test_config.json"
        config.save(config_path)
        
        # Load config
        loaded_config = Config.load(config_path)
        assert loaded_config.app_name == config.app_name
        assert loaded_config.version == config.version
    
    def test_feature_flags(self):
        """Test feature flag management"""
        config = Config()
        
        # Test default flags
        assert config.get_feature_flag("swarm_coordination") is True
        
        # Test setting flags
        config.set_feature_flag("test_feature", False)
        assert config.get_feature_flag("test_feature") is False


class TestLogger:
    """Test logging system"""
    
    def test_logger_creation(self):
        """Test logger creation"""
        logger = Logger("test-logger")
        assert logger.name == "test-logger"
    
    def test_logger_methods(self):
        """Test logger methods"""
        logger = Logger("test-logger")
        
        # These should not raise exceptions
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
    
    def test_get_logger(self):
        """Test get_logger function"""
        logger = get_logger("test-get-logger")
        assert isinstance(logger, Logger)


class TestEventBus:
    """Test event bus system"""
    
    @pytest.fixture
    def event_bus(self):
        """Create event bus for testing"""
        return EventBus()
    
    @pytest.mark.asyncio
    async def test_event_bus_lifecycle(self, event_bus):
        """Test event bus start/stop"""
        # Start
        await event_bus.start()
        assert event_bus.is_running() is True
        
        # Stop
        await event_bus.stop()
        assert event_bus.is_running() is False
    
    @pytest.mark.asyncio
    async def test_event_subscription(self, event_bus):
        """Test event subscription"""
        await event_bus.start()
        
        events_received = []
        
        def event_handler(event):
            events_received.append(event)
        
        # Subscribe to specific event type
        event_bus.subscribe(EventType.AGENT_CREATED, event_handler)
        
        # Publish event
        test_event = Event(
            id="test_001",
            type=EventType.AGENT_CREATED,
            source="test",
            timestamp=Event.now(),
            data={"test": "data"}
        )
        
        await event_bus.publish(test_event)
        
        # Wait for event processing
        await asyncio.sleep(0.1)
        
        assert len(events_received) == 1
        assert events_received[0].id == "test_001"
        
        await event_bus.stop()
    
    @pytest.mark.asyncio
    async def test_wildcard_subscription(self, event_bus):
        """Test wildcard event subscription"""
        await event_bus.start()
        
        events_received = []
        
        def event_handler(event):
            events_received.append(event)
        
        # Subscribe to all events
        event_bus.subscribe_to_all(event_handler)
        
        # Publish multiple event types
        event1 = Event(
            id="test_001",
            type=EventType.AGENT_CREATED,
            source="test",
            timestamp=Event.now(),
            data={"test": "data1"}
        )
        
        event2 = Event(
            id="test_002",
            type=EventType.AGENT_STARTED,
            source="test",
            timestamp=Event.now(),
            data={"test": "data2"}
        )
        
        await event_bus.publish(event1)
        await event_bus.publish(event2)
        
        # Wait for event processing
        await asyncio.sleep(0.1)
        
        assert len(events_received) == 2
        
        await event_bus.stop()


class TestEvent:
    """Test event data structure"""
    
    def test_event_creation(self):
        """Test event creation"""
        event = Event(
            id="test_001",
            type=EventType.AGENT_CREATED,
            source="test",
            timestamp=Event.now(),
            data={"test": "data"}
        )
        
        assert event.id == "test_001"
        assert event.type == EventType.AGENT_CREATED
        assert event.source == "test"
        assert event.data["test"] == "data"
    
    def test_event_serialization(self):
        """Test event serialization"""
        event = Event(
            id="test_001",
            type=EventType.AGENT_CREATED,
            source="test",
            timestamp=Event.now(),
            data={"test": "data"}
        )
        
        # Test to_dict
        event_dict = event.to_dict()
        assert event_dict["id"] == "test_001"
        assert event_dict["type"] == "agent.created"
        
        # Test to_json
        event_json = event.to_json()
        assert "test_001" in event_json
        assert "agent.created" in event_json


# Add missing method to Event class
def now():
    """Get current timestamp"""
    from datetime import datetime
    return datetime.now()

Event.now = staticmethod(now)


if __name__ == "__main__":
    # Run basic tests
    pytest.main([__file__, "-v"])
