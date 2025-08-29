"""
Event bus system for Claude-Flow
"""

import asyncio
import json
from typing import Dict, List, Callable, Any, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from .logger import logger


class EventType(Enum):
    """Event types for the system"""
    # Agent events
    AGENT_CREATED = "agent.created"
    AGENT_STARTED = "agent.started"
    AGENT_STOPPED = "agent.stopped"
    AGENT_ERROR = "agent.error"
    AGENT_HEARTBEAT = "agent.heartbeat"
    
    # Swarm events
    SWARM_FORMED = "swarm.formed"
    SWARM_DISSOLVED = "swarm.dissolved"
    SWARM_COORDINATION = "swarm.coordination"
    SWARM_SCALING = "swarm.scaling"
    
    # Memory events
    MEMORY_STORED = "memory.stored"
    MEMORY_RETRIEVED = "memory.retrieved"
    MEMORY_CLEANED = "memory.cleaned"
    
    # MCP events
    MCP_TOOL_CALLED = "mcp.tool_called"
    MCP_TOOL_RESULT = "mcp.tool_result"
    MCP_ERROR = "mcp.error"
    
    # Claude events
    CLAUDE_REQUEST = "claude.request"
    CLAUDE_RESPONSE = "claude.response"
    CLAUDE_ERROR = "claude.error"
    
    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_HEALTH_CHECK = "system.health_check"


@dataclass
class Event:
    """Event data structure"""
    id: str
    type: EventType
    source: str
    timestamp: datetime
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        event_dict = asdict(self)
        event_dict['type'] = self.type.value
        event_dict['timestamp'] = self.timestamp.isoformat()
        return event_dict
    
    def to_json(self) -> str:
        """Convert event to JSON string"""
        return json.dumps(self.to_dict())


class EventBus:
    """Asynchronous event bus for system-wide communication"""
    
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._wildcard_subscribers: List[Callable] = []
        self._event_history: List[Event] = []
        self._max_history = 1000
        self._running = False
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
    
    async def start(self):
        """Start the event bus"""
        if self._running:
            return
        
        self._running = True
        self._loop = asyncio.get_event_loop()
        
        # Start event processing task
        asyncio.create_task(self._process_events())
        logger.info("Event bus started")
    
    async def stop(self):
        """Stop the event bus"""
        if not self._running:
            return
        
        self._running = False
        
        # Wait for event queue to be processed
        while not self._event_queue.empty():
            await asyncio.sleep(0.1)
        
        logger.info("Event bus stopped")
    
    def subscribe(self, event_type: EventType, callback: Callable):
        """Subscribe to specific event type"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)
            logger.debug(f"Subscribed to {event_type.value}")
    
    def subscribe_to_all(self, callback: Callable):
        """Subscribe to all events"""
        if callback not in self._wildcard_subscribers:
            self._wildcard_subscribers.append(callback)
            logger.debug("Subscribed to all events")
    
    def unsubscribe(self, event_type: EventType, callback: Callable):
        """Unsubscribe from specific event type"""
        if event_type in self._subscribers:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)
                logger.debug(f"Unsubscribed from {event_type.value}")
    
    def unsubscribe_from_all(self, callback: Callable):
        """Unsubscribe from all events"""
        if callback in self._wildcard_subscribers:
            self._wildcard_subscribers.remove(callback)
            logger.debug("Unsubscribed from all events")
    
    async def publish(self, event: Event):
        """Publish an event"""
        if not self._running:
            logger.warning("Event bus not running, event dropped", event_id=event.id)
            return
        
        # Add to history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        
        # Add to processing queue
        await self._event_queue.put(event)
        logger.debug(f"Event published: {event.type.value}", event_id=event.id)
    
    async def publish_immediate(self, event: Event):
        """Publish an event and process immediately"""
        if not self._running:
            logger.warning("Event bus not running, event dropped", event_id=event.id)
            return
        
        # Add to history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        
        # Process immediately
        await self._process_event(event)
    
    async def _process_events(self):
        """Process events from the queue"""
        while self._running:
            try:
                event = await self._event_queue.get()
                await self._process_event(event)
                self._event_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing event: {e}")
    
    async def _process_event(self, event: Event):
        """Process a single event"""
        try:
            # Notify specific subscribers
            if event.type in self._subscribers:
                for callback in self._subscribers[event.type]:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(event)
                        else:
                            callback(event)
                    except Exception as e:
                        logger.error(f"Error in event callback: {e}", event_id=event.id)
            
            # Notify wildcard subscribers
            for callback in self._wildcard_subscribers:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    logger.error(f"Error in wildcard callback: {e}", event_id=event.id)
        
        except Exception as e:
            logger.error(f"Error processing event {event.id}: {e}")
    
    def get_event_history(self, event_type: Optional[EventType] = None, limit: int = 100) -> List[Event]:
        """Get event history, optionally filtered by type"""
        if event_type is None:
            return self._event_history[-limit:]
        
        filtered_events = [event for event in self._event_history if event.type == event_type]
        return filtered_events[-limit:]
    
    def get_subscriber_count(self, event_type: Optional[EventType] = None) -> int:
        """Get subscriber count for an event type or total"""
        if event_type is None:
            total = len(self._wildcard_subscribers)
            for subscribers in self._subscribers.values():
                total += len(subscribers)
            return total
        
        return len(self._subscribers.get(event_type, []))
    
    def is_running(self) -> bool:
        """Check if event bus is running"""
        return self._running


# Global event bus instance
event_bus = EventBus()


# Convenience functions for common events
async def publish_agent_event(agent_id: str, event_type: EventType, data: Dict[str, Any]):
    """Publish agent-related event"""
    event = Event(
        id=f"agent_{agent_id}_{event_type.value}_{datetime.now().timestamp()}",
        type=event_type,
        source=f"agent:{agent_id}",
        timestamp=datetime.now(),
        data=data
    )
    await event_bus.publish(event)


async def publish_swarm_event(event_type: EventType, data: Dict[str, Any]):
    """Publish swarm-related event"""
    event = Event(
        id=f"swarm_{event_type.value}_{datetime.now().timestamp()}",
        type=event_type,
        source="swarm:coordinator",
        timestamp=datetime.now(),
        data=data
    )
    await event_bus.publish(event)


async def publish_mcp_event(event_type: EventType, data: Dict[str, Any]):
    """Publish MCP-related event"""
    event = Event(
        id=f"mcp_{event_type.value}_{datetime.now().timestamp()}",
        type=event_type,
        source="mcp:client",
        timestamp=datetime.now(),
        data=data
    )
    await event_bus.publish(event)


async def publish_claude_event(event_type: EventType, data: Dict[str, Any]):
    """Publish Claude-related event"""
    event = Event(
        id=f"claude_{event_type.value}_{datetime.now().timestamp()}",
        type=event_type,
        source="claude:client",
        timestamp=datetime.now(),
        data=data
    )
    await event_bus.publish(event)
