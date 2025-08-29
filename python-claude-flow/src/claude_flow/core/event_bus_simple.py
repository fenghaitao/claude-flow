"""
Simplified Event Bus for Claude-Flow

This module provides a basic event bus implementation without external dependencies.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
import json


class EventType(Enum):
    """Event types for the system"""
    AGENT_CREATED = "agent_created"
    AGENT_DESTROYED = "agent_destroyed"
    SWARM_COORDINATED = "swarm_coordinated"
    MCP_TOOL_CALLED = "mcp_tool_called"
    CLAUDE_REQUEST = "claude_request"
    MEMORY_UPDATED = "memory_updated"
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"


@dataclass
class Event:
    """Event data structure"""
    type: EventType
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "metadata": self.metadata
        }
    
    def to_json(self) -> str:
        """Convert event to JSON string"""
        return json.dumps(self.to_dict())


class EventBus:
    """Simplified event bus for system-wide communication"""
    
    def __init__(self):
        self._subscribers: Dict[EventType, Set[Callable]] = {}
        self._event_history: List[Event] = []
        self._max_history: int = 1000
        self._running: bool = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
    
    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """Subscribe to an event type"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = set()
        self._subscribers[event_type].add(callback)
    
    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """Unsubscribe from an event type"""
        if event_type in self._subscribers:
            self._subscribers[event_type].discard(callback)
    
    def publish(self, event: Event) -> None:
        """Publish an event to all subscribers"""
        # Add to history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        
        # Notify subscribers
        if event.type in self._subscribers:
            for callback in self._subscribers[event.type]:
                try:
                    callback(event)
                except Exception as e:
                    print(f"Error in event callback: {e}")
    
    async def publish_async(self, event: Event) -> None:
        """Publish an event asynchronously"""
        self.publish(event)
        await asyncio.sleep(0)  # Yield control
    
    def get_history(self, event_type: Optional[EventType] = None, limit: int = 100) -> List[Event]:
        """Get event history"""
        if event_type is None:
            return self._event_history[-limit:]
        return [e for e in self._event_history if e.type == event_type][-limit:]
    
    def clear_history(self) -> None:
        """Clear event history"""
        self._event_history.clear()
    
    def get_subscriber_count(self, event_type: EventType) -> int:
        """Get number of subscribers for an event type"""
        return len(self._subscribers.get(event_type, set()))
    
    def start(self) -> None:
        """Start the event bus"""
        self._running = True
        print("Event bus started")
    
    def stop(self) -> None:
        """Stop the event bus"""
        self._running = False
        print("Event bus stopped")
    
    @property
    def is_running(self) -> bool:
        """Check if event bus is running"""
        return self._running


# Global event bus instance
event_bus = EventBus()

# Convenience functions
def publish_agent_event(event_type: str, agent_id: str, data: Dict[str, Any]) -> None:
    """Publish an agent-related event"""
    event = Event(
        type=EventType.AGENT_CREATED if event_type == "created" else EventType.AGENT_DESTROYED,
        data={"agent_id": agent_id, **data},
        source="agent_manager"
    )
    event_bus.publish(event)

def publish_swarm_event(event_type: str, swarm_id: str, data: Dict[str, Any]) -> None:
    """Publish a swarm-related event"""
    event = Event(
        type=EventType.SWARM_COORDINATED,
        data={"swarm_id": swarm_id, **data},
        source="swarm_coordinator"
    )
    event_bus.publish(event)

def publish_mcp_event(tool_name: str, data: Dict[str, Any]) -> None:
    """Publish an MCP tool call event"""
    event = Event(
        type=EventType.MCP_TOOL_CALLED,
        data={"tool_name": tool_name, **data},
        source="mcp_client"
    )
    event_bus.publish(event)

def publish_claude_event(request_type: str, data: Dict[str, Any]) -> None:
    """Publish a Claude API request event"""
    event = Event(
        type=EventType.CLAUDE_REQUEST,
        data={"request_type": request_type, **data},
        source="claude_client"
    )
    event_bus.publish(event)
