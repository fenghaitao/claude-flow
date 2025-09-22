"""
Unit tests for event bus system.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import List, Dict, Any

from claude_flow.events.bus import EventBus, Event, EventSubscription
from claude_flow.events.models import EventType, EventPriority
from claude_flow.config.models import EventConfig


class TestEvent:
    """Test Event model."""
    
    def test_event_creation(self):
        """Test basic event creation."""
        event = Event(
            type=EventType.TASK_CREATED,
            data={"task_id": "123", "description": "Test task"},
            source="test_agent",
            priority=EventPriority.HIGH
        )
        
        assert event.type == EventType.TASK_CREATED
        assert event.data["task_id"] == "123"
        assert event.source == "test_agent"
        assert event.priority == EventPriority.HIGH
        assert event.id is not None
        assert event.timestamp > 0
    
    def test_event_defaults(self):
        """Test event with default values."""
        event = Event(
            type=EventType.AGENT_STARTED,
            data={"agent_id": "worker_1"}
        )
        
        assert event.type == EventType.AGENT_STARTED
        assert event.source == "system"
        assert event.priority == EventPriority.NORMAL
        assert event.tags == []
        assert event.metadata == {}
    
    def test_event_serialization(self):
        """Test event serialization/deserialization."""
        original = Event(
            type=EventType.TASK_COMPLETED,
            data={"task_id": "456", "result": "success"},
            source="worker_agent",
            tags=["important", "user_task"],
            metadata={"user_id": "user123"}
        )
        
        # Serialize to dict
        event_dict = original.to_dict()
        assert event_dict["type"] == "task_completed"
        assert event_dict["data"]["task_id"] == "456"
        assert event_dict["source"] == "worker_agent"
        assert "important" in event_dict["tags"]
        
        # Deserialize from dict
        restored = Event.from_dict(event_dict)
        assert restored.id == original.id
        assert restored.type == original.type
        assert restored.data == original.data
        assert restored.source == original.source
        assert restored.tags == original.tags


class TestEventSubscription:
    """Test EventSubscription model."""
    
    def test_subscription_creation(self):
        """Test event subscription creation."""
        handler = AsyncMock()
        subscription = EventSubscription(
            event_type=EventType.TASK_CREATED,
            handler=handler,
            filter_func=lambda e: e.data.get("priority") == "high"
        )
        
        assert subscription.event_type == EventType.TASK_CREATED
        assert subscription.handler == handler
        assert subscription.filter_func is not None
        assert subscription.id is not None
    
    def test_subscription_matches(self):
        """Test event matching logic."""
        subscription = EventSubscription(
            event_type=EventType.TASK_CREATED,
            handler=AsyncMock(),
            filter_func=lambda e: e.data.get("priority") == "high"
        )
        
        # Matching event
        matching_event = Event(
            type=EventType.TASK_CREATED,
            data={"priority": "high", "task_id": "123"}
        )
        assert subscription.matches(matching_event) is True
        
        # Non-matching type
        wrong_type_event = Event(
            type=EventType.TASK_COMPLETED,
            data={"priority": "high", "task_id": "123"}
        )
        assert subscription.matches(wrong_type_event) is False
        
        # Non-matching filter
        wrong_filter_event = Event(
            type=EventType.TASK_CREATED,
            data={"priority": "low", "task_id": "123"}
        )
        assert subscription.matches(wrong_filter_event) is False


class TestEventBus:
    """Test EventBus functionality."""
    
    @pytest.fixture
    async def event_bus(self):
        """Create event bus for testing."""
        config = EventConfig(
            max_queue_size=100,
            persistence_enabled=False,
            replay_enabled=False
        )
        bus = EventBus(config)
        await bus.initialize()
        yield bus
        await bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_event_bus_initialization(self):
        """Test event bus initialization."""
        config = EventConfig()
        bus = EventBus(config)
        
        assert bus.config == config
        assert bus._subscriptions == {}
        assert bus._event_queue is None
        
        await bus.initialize()
        assert bus._event_queue is not None
        assert bus._running is True
        
        await bus.shutdown()
        assert bus._running is False
    
    @pytest.mark.asyncio
    async def test_publish_event(self, event_bus):
        """Test publishing an event."""
        event = Event(
            type=EventType.TASK_CREATED,
            data={"task_id": "test_123"}
        )
        
        # Publish event
        await event_bus.publish(event)
        
        # Event should be in queue
        assert event_bus._event_queue.qsize() == 1
    
    @pytest.mark.asyncio
    async def test_subscribe_and_receive(self, event_bus):
        """Test subscribing to events and receiving them."""
        received_events = []
        
        async def handler(event: Event):
            received_events.append(event)
        
        # Subscribe to task events
        subscription_id = await event_bus.subscribe(
            EventType.TASK_CREATED,
            handler
        )
        
        assert subscription_id is not None
        assert EventType.TASK_CREATED in event_bus._subscriptions
        
        # Publish matching event
        event = Event(
            type=EventType.TASK_CREATED,
            data={"task_id": "test_456"}
        )
        await event_bus.publish(event)
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Should have received the event
        assert len(received_events) == 1
        assert received_events[0].data["task_id"] == "test_456"
    
    @pytest.mark.asyncio
    async def test_unsubscribe(self, event_bus):
        """Test unsubscribing from events."""
        received_events = []
        
        async def handler(event: Event):
            received_events.append(event)
        
        # Subscribe
        subscription_id = await event_bus.subscribe(
            EventType.TASK_CREATED,
            handler
        )
        
        # Publish event (should be received)
        await event_bus.publish(Event(
            type=EventType.TASK_CREATED,
            data={"task_id": "before_unsub"}
        ))
        
        # Unsubscribe
        await event_bus.unsubscribe(subscription_id)
        
        # Publish another event (should not be received)
        await event_bus.publish(Event(
            type=EventType.TASK_CREATED,
            data={"task_id": "after_unsub"}
        ))
        
        await asyncio.sleep(0.1)
        
        # Should only have received first event
        assert len(received_events) == 1
        assert received_events[0].data["task_id"] == "before_unsub"
    
    @pytest.mark.asyncio
    async def test_filtered_subscription(self, event_bus):
        """Test subscription with filter function."""
        high_priority_events = []
        
        async def handler(event: Event):
            high_priority_events.append(event)
        
        # Subscribe only to high priority events
        await event_bus.subscribe(
            EventType.TASK_CREATED,
            handler,
            filter_func=lambda e: e.priority == EventPriority.HIGH
        )
        
        # Publish high priority event
        await event_bus.publish(Event(
            type=EventType.TASK_CREATED,
            data={"task_id": "high_priority"},
            priority=EventPriority.HIGH
        ))
        
        # Publish normal priority event
        await event_bus.publish(Event(
            type=EventType.TASK_CREATED,
            data={"task_id": "normal_priority"},
            priority=EventPriority.NORMAL
        ))
        
        await asyncio.sleep(0.1)
        
        # Should only receive high priority event
        assert len(high_priority_events) == 1
        assert high_priority_events[0].data["task_id"] == "high_priority"
    
    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, event_bus):
        """Test multiple subscribers to same event type."""
        handler1_events = []
        handler2_events = []
        
        async def handler1(event: Event):
            handler1_events.append(event)
        
        async def handler2(event: Event):
            handler2_events.append(event)
        
        # Subscribe both handlers
        await event_bus.subscribe(EventType.TASK_CREATED, handler1)
        await event_bus.subscribe(EventType.TASK_CREATED, handler2)
        
        # Publish event
        event = Event(
            type=EventType.TASK_CREATED,
            data={"task_id": "multi_sub_test"}
        )
        await event_bus.publish(event)
        
        await asyncio.sleep(0.1)
        
        # Both handlers should receive the event
        assert len(handler1_events) == 1
        assert len(handler2_events) == 1
        assert handler1_events[0].data["task_id"] == "multi_sub_test"
        assert handler2_events[0].data["task_id"] == "multi_sub_test"
    
    @pytest.mark.asyncio
    async def test_priority_queue_ordering(self, event_bus):
        """Test that events are processed by priority."""
        received_events = []
        
        async def handler(event: Event):
            received_events.append(event)
        
        # Subscribe to all events
        await event_bus.subscribe(EventType.TASK_CREATED, handler)
        
        # Publish events with different priorities
        await event_bus.publish(Event(
            type=EventType.TASK_CREATED,
            data={"order": "third"},
            priority=EventPriority.LOW
        ))
        
        await event_bus.publish(Event(
            type=EventType.TASK_CREATED,
            data={"order": "first"},
            priority=EventPriority.CRITICAL
        ))
        
        await event_bus.publish(Event(
            type=EventType.TASK_CREATED,
            data={"order": "second"},
            priority=EventPriority.HIGH
        ))
        
        await asyncio.sleep(0.1)
        
        # Should be processed in priority order
        assert len(received_events) == 3
        assert received_events[0].data["order"] == "first"   # CRITICAL
        assert received_events[1].data["order"] == "second"  # HIGH
        assert received_events[2].data["order"] == "third"   # LOW
    
    @pytest.mark.asyncio
    async def test_error_handling(self, event_bus):
        """Test error handling in event processing."""
        successful_events = []
        
        async def failing_handler(event: Event):
            if event.data.get("should_fail"):
                raise ValueError("Handler error")
        
        async def successful_handler(event: Event):
            successful_events.append(event)
        
        # Subscribe both handlers
        await event_bus.subscribe(EventType.TASK_CREATED, failing_handler)
        await event_bus.subscribe(EventType.TASK_CREATED, successful_handler)
        
        # Publish event that will cause failure
        await event_bus.publish(Event(
            type=EventType.TASK_CREATED,
            data={"should_fail": True, "task_id": "error_test"}
        ))
        
        await asyncio.sleep(0.1)
        
        # Successful handler should still receive event despite other handler failing
        assert len(successful_events) == 1
        assert successful_events[0].data["task_id"] == "error_test"
    
    @pytest.mark.asyncio
    async def test_queue_size_limit(self):
        """Test event queue size limit."""
        config = EventConfig(max_queue_size=2)
        bus = EventBus(config)
        await bus.initialize()
        
        try:
            # Fill queue to capacity
            await bus.publish(Event(type=EventType.TASK_CREATED, data={"id": "1"}))
            await bus.publish(Event(type=EventType.TASK_CREATED, data={"id": "2"}))
            
            # Queue should be at capacity
            assert bus._event_queue.qsize() == 2
            
            # Publishing another event should handle queue full condition
            await bus.publish(Event(type=EventType.TASK_CREATED, data={"id": "3"}))
            
        finally:
            await bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_get_stats(self, event_bus):
        """Test getting event bus statistics."""
        # Subscribe a handler
        async def handler(event: Event):
            pass
        
        await event_bus.subscribe(EventType.TASK_CREATED, handler)
        
        # Publish some events
        for i in range(3):
            await event_bus.publish(Event(
                type=EventType.TASK_CREATED,
                data={"task_id": f"test_{i}"}
            ))
        
        await asyncio.sleep(0.1)
        
        stats = await event_bus.get_stats()
        
        assert "total_events_published" in stats
        assert "total_events_processed" in stats
        assert "active_subscriptions" in stats
        assert "queue_size" in stats
        
        assert stats["total_events_published"] >= 3
        assert stats["active_subscriptions"] >= 1


@pytest.mark.integration
class TestEventBusIntegration:
    """Integration tests for event bus with persistence."""
    
    @pytest.mark.asyncio
    async def test_event_persistence(self, temp_dir):
        """Test event persistence functionality."""
        config = EventConfig(
            persistence_enabled=True,
            persistence_path=str(temp_dir / "events.db")
        )
        
        bus = EventBus(config)
        await bus.initialize()
        
        try:
            # Publish events
            events = [
                Event(type=EventType.TASK_CREATED, data={"id": "1"}),
                Event(type=EventType.TASK_COMPLETED, data={"id": "2"}),
                Event(type=EventType.AGENT_STARTED, data={"id": "3"})
            ]
            
            for event in events:
                await bus.publish(event)
            
            await asyncio.sleep(0.2)
            
            # Events should be persisted
            persisted_events = await bus.get_persisted_events()
            assert len(persisted_events) >= 3
            
        finally:
            await bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_event_replay(self, temp_dir):
        """Test event replay functionality."""
        config = EventConfig(
            persistence_enabled=True,
            replay_enabled=True,
            persistence_path=str(temp_dir / "replay_events.db")
        )
        
        # First bus instance - publish events
        bus1 = EventBus(config)
        await bus1.initialize()
        
        original_events = [
            Event(type=EventType.TASK_CREATED, data={"replay_test": "1"}),
            Event(type=EventType.TASK_CREATED, data={"replay_test": "2"})
        ]
        
        for event in original_events:
            await bus1.publish(event)
        
        await asyncio.sleep(0.1)
        await bus1.shutdown()
        
        # Second bus instance - replay events
        bus2 = EventBus(config)
        replayed_events = []
        
        async def replay_handler(event: Event):
            replayed_events.append(event)
        
        await bus2.initialize()
        await bus2.subscribe(EventType.TASK_CREATED, replay_handler)
        
        # Replay events
        await bus2.replay_events()
        await asyncio.sleep(0.1)
        
        try:
            # Should have received replayed events
            assert len(replayed_events) >= 2
            replay_data = [e.data.get("replay_test") for e in replayed_events]
            assert "1" in replay_data
            assert "2" in replay_data
            
        finally:
            await bus2.shutdown()