"""
Enhanced Event Bus System for Claude-Flow

This module provides a comprehensive asynchronous event bus with:
- Queue management and prioritization
- Event filtering and subscriptions
- Persistence and replay capabilities
- Error handling and retry mechanisms
- Performance monitoring and metrics
"""

import asyncio
import json
import logging
from asyncio import Queue, Event as AsyncEvent
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union
from uuid import uuid4
from weakref import WeakSet
import time

from .interfaces import BaseComponent
from .event_bus_simple import Event, EventType as SimpleEventType

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    """Event priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4
    EMERGENCY = 5


class EventStatus(Enum):
    """Event processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


@dataclass
class EventFilter:
    """Event filter configuration"""
    event_types: Optional[Set[str]] = None
    sources: Optional[Set[str]] = None
    priority: Optional[EventPriority] = None
    custom_filters: Optional[Dict[str, Any]] = None
    
    def matches(self, event: 'EnhancedEvent') -> bool:
        """Check if event matches this filter"""
        if self.event_types and event.event_type not in self.event_types:
            return False
        
        if self.sources and event.source not in self.sources:
            return False
        
        if self.priority and event.priority != self.priority:
            return False
        
        if self.custom_filters:
            for key, value in self.custom_filters.items():
                if key not in event.data or event.data[key] != value:
                    return False
        
        return True


@dataclass
class Subscription:
    """Event subscription configuration"""
    id: str
    handler: Callable
    filter: EventFilter
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    async def handle_event(self, event: 'EnhancedEvent') -> bool:
        """Handle an event with error handling and retries"""
        retries = 0
        last_error = None
        
        while retries <= self.max_retries:
            try:
                if asyncio.iscoroutinefunction(self.handler):
                    if self.timeout:
                        await asyncio.wait_for(self.handler(event), timeout=self.timeout)
                    else:
                        await self.handler(event)
                else:
                    self.handler(event)
                
                return True
                
            except asyncio.TimeoutError:
                last_error = f"Handler timeout after {self.timeout} seconds"
                logger.warning(f"Event handler timeout for subscription {self.id}: {last_error}")
                break
                
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Event handler error for subscription {self.id} (attempt {retries + 1}): {e}")
                
                if retries < self.max_retries:
                    retries += 1
                    await asyncio.sleep(self.retry_delay * retries)  # Exponential backoff
                else:
                    break
        
        logger.error(f"Event handler failed for subscription {self.id} after {retries} retries: {last_error}")
        return False


@dataclass
class EnhancedEvent(Event):
    """Enhanced event with additional metadata"""
    event_id: str = field(default_factory=lambda: str(uuid4()))
    priority: EventPriority = EventPriority.NORMAL
    status: EventStatus = EventStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    correlation_id: Optional[str] = None
    parent_event_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def to_simple_event(self) -> Event:
        """Convert to simple event for backward compatibility"""
        return Event(
            type=self.type,
            data=self.data,
            timestamp=self.timestamp,
            source=self.source,
            metadata=self.metadata
        )
    
    def is_expired(self) -> bool:
        """Check if event has expired"""
        return self.expires_at is not None and datetime.now() > self.expires_at
    
    def processing_time(self) -> Optional[float]:
        """Get event processing time in seconds"""
        if self.processing_started_at and self.processing_completed_at:
            return (self.processing_completed_at - self.processing_started_at).total_seconds()
        return None


class EventQueue:
    """Priority-based event queue"""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self._queues = {priority: Queue() for priority in EventPriority}
        self._size = 0
        self._not_empty = AsyncEvent()
        
    async def put(self, event: EnhancedEvent) -> bool:
        """Put event in queue based on priority"""
        if self._size >= self.max_size:
            logger.warning("Event queue is full, dropping event")
            return False
        
        try:
            await self._queues[event.priority].put(event)
            self._size += 1
            self._not_empty.set()
            return True
        except Exception as e:
            logger.error(f"Failed to queue event: {e}")
            return False
    
    async def get(self) -> Optional[EnhancedEvent]:
        """Get next event from queue (highest priority first)"""
        while self._size == 0:
            self._not_empty.clear()
            await self._not_empty.wait()
        
        # Check queues in priority order (highest first)
        for priority in sorted(EventPriority, key=lambda x: x.value, reverse=True):
            queue = self._queues[priority]
            if not queue.empty():
                try:
                    event = await queue.get()
                    self._size -= 1
                    return event
                except Exception as e:
                    logger.error(f"Failed to get event from queue: {e}")
        
        return None
    
    def size(self) -> int:
        """Get current queue size"""
        return self._size
    
    def is_full(self) -> bool:
        """Check if queue is full"""
        return self._size >= self.max_size


class EventProcessor:
    """Asynchronous event processor"""
    
    def __init__(self, worker_count: int = 4):
        self.worker_count = worker_count
        self.workers: List[asyncio.Task] = []
        self.running = False
        self.processed_count = 0
        self.failed_count = 0
        self.start_time: Optional[datetime] = None
        
    async def start(self, event_queue: EventQueue, subscriptions: Dict[str, Subscription]):
        """Start event processing workers"""
        if self.running:
            return
        
        self.running = True
        self.start_time = datetime.now()
        
        for i in range(self.worker_count):
            worker = asyncio.create_task(self._worker(f"worker-{i}", event_queue, subscriptions))
            self.workers.append(worker)
        
        logger.info(f"Started {self.worker_count} event processing workers")
    
    async def stop(self):
        """Stop event processing workers"""
        self.running = False
        
        for worker in self.workers:
            worker.cancel()
        
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
        
        self.workers.clear()
        logger.info("Stopped event processing workers")
    
    async def _worker(self, worker_id: str, event_queue: EventQueue, subscriptions: Dict[str, Subscription]):
        """Event processing worker"""
        logger.debug(f"Event worker {worker_id} started")
        
        while self.running:
            try:
                event = await event_queue.get()
                if event is None:
                    continue
                
                # Check if event has expired
                if event.is_expired():
                    logger.debug(f"Dropping expired event: {event.event_id}")
                    continue
                
                # Process event
                event.status = EventStatus.PROCESSING
                event.processing_started_at = datetime.now()
                
                success = await self._process_event(event, subscriptions)
                
                event.processing_completed_at = datetime.now()
                
                if success:
                    event.status = EventStatus.COMPLETED
                    self.processed_count += 1
                else:
                    event.status = EventStatus.FAILED
                    self.failed_count += 1
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                self.failed_count += 1
        
        logger.debug(f"Event worker {worker_id} stopped")
    
    async def _process_event(self, event: EnhancedEvent, subscriptions: Dict[str, Subscription]) -> bool:
        """Process a single event"""
        matching_subscriptions = [
            sub for sub in subscriptions.values()
            if sub.filter.matches(event)
        ]
        
        if not matching_subscriptions:
            logger.debug(f"No matching subscriptions for event: {event.event_id}")
            return True
        
        # Process all matching subscriptions
        results = await asyncio.gather(
            *[sub.handle_event(event) for sub in matching_subscriptions],
            return_exceptions=True
        )
        
        # Check if all handlers succeeded
        success_count = sum(1 for result in results if result is True)
        total_count = len(results)
        
        if success_count == total_count:
            logger.debug(f"Event {event.event_id} processed successfully by {total_count} handlers")
            return True
        else:
            logger.warning(f"Event {event.event_id} failed in {total_count - success_count}/{total_count} handlers")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        
        return {
            "worker_count": self.worker_count,
            "running": self.running,
            "processed_count": self.processed_count,
            "failed_count": self.failed_count,
            "success_rate": self.processed_count / max(1, self.processed_count + self.failed_count),
            "uptime_seconds": uptime,
            "events_per_second": self.processed_count / max(1, uptime)
        }


class EventHistory:
    """Event history storage with rotation"""
    
    def __init__(self, max_events: int = 100000, max_age_hours: int = 24):
        self.max_events = max_events
        self.max_age = timedelta(hours=max_age_hours)
        self.events: deque = deque(maxlen=max_events)
        self.events_by_id: Dict[str, EnhancedEvent] = {}
        
    def add_event(self, event: EnhancedEvent):
        """Add event to history"""
        self.events.append(event)
        self.events_by_id[event.event_id] = event
        self._cleanup_old_events()
    
    def get_event(self, event_id: str) -> Optional[EnhancedEvent]:
        """Get event by ID"""
        return self.events_by_id.get(event_id)
    
    def get_events(self, filter: Optional[EventFilter] = None, 
                  limit: int = 100) -> List[EnhancedEvent]:
        """Get events matching filter"""
        filtered_events = []
        
        for event in reversed(self.events):
            if filter is None or filter.matches(event):
                filtered_events.append(event)
                if len(filtered_events) >= limit:
                    break
        
        return filtered_events
    
    def _cleanup_old_events(self):
        """Remove old events"""
        cutoff_time = datetime.now() - self.max_age
        
        while self.events and self.events[0].timestamp < cutoff_time:
            old_event = self.events.popleft()
            self.events_by_id.pop(old_event.event_id, None)


class EnhancedEventBus(BaseComponent):
    """
    Enhanced asynchronous event bus with comprehensive features
    
    Features:
    - Priority-based event queuing
    - Async event processing with workers
    - Event filtering and subscriptions
    - Event history and replay
    - Performance monitoring
    - Error handling and retries
    """
    
    def __init__(self, worker_count: int = 4, queue_size: int = 10000):
        super().__init__()
        self.worker_count = worker_count
        self.queue = EventQueue(max_size=queue_size)
        self.processor = EventProcessor(worker_count=worker_count)
        self.subscriptions: Dict[str, Subscription] = {}
        self.history = EventHistory()
        self._lock = asyncio.Lock()
        
    async def _start_implementation(self) -> None:
        """Start the event bus"""
        await self.processor.start(self.queue, self.subscriptions)
        logger.info("Enhanced event bus started")
    
    async def _stop_implementation(self) -> None:
        """Stop the event bus"""
        await self.processor.stop()
        logger.info("Enhanced event bus stopped")
    
    async def _health_check_implementation(self) -> Dict[str, Any]:
        """Health check implementation"""
        stats = self.processor.get_stats()
        return {
            "queue_size": self.queue.size(),
            "queue_full": self.queue.is_full(),
            "subscriptions_count": len(self.subscriptions),
            "history_size": len(self.history.events),
            **stats
        }
    
    async def publish(self, event_type: str, data: Dict[str, Any], 
                     priority: EventPriority = EventPriority.NORMAL,
                     source: Optional[str] = None,
                     correlation_id: Optional[str] = None,
                     expires_in: Optional[int] = None) -> str:
        """
        Publish an event to the bus
        
        Args:
            event_type: Type of event
            data: Event data
            priority: Event priority
            source: Event source
            correlation_id: Correlation ID for tracking
            expires_in: Expiration time in seconds
            
        Returns:
            Event ID
        """
        event = EnhancedEvent(
            type=event_type,
            data=data,
            priority=priority,
            source=source or "unknown",
            correlation_id=correlation_id,
            expires_at=datetime.now() + timedelta(seconds=expires_in) if expires_in else None
        )
        
        # Add to history
        self.history.add_event(event)
        
        # Queue for processing
        success = await self.queue.put(event)
        
        if not success:
            logger.error(f"Failed to queue event: {event.event_id}")
            event.status = EventStatus.FAILED
            event.error_message = "Queue full"
        
        logger.debug(f"Published event: {event.event_id} (type: {event_type}, priority: {priority.name})")
        return event.event_id
    
    async def subscribe(self, event_filter: EventFilter, handler: Callable,
                       max_retries: int = 3, retry_delay: float = 1.0,
                       timeout: Optional[float] = None) -> str:
        """
        Subscribe to events matching filter
        
        Args:
            event_filter: Event filter configuration
            handler: Event handler function
            max_retries: Maximum retry attempts
            retry_delay: Retry delay in seconds
            timeout: Handler timeout in seconds
            
        Returns:
            Subscription ID
        """
        subscription = Subscription(
            id=str(uuid4()),
            handler=handler,
            filter=event_filter,
            max_retries=max_retries,
            retry_delay=retry_delay,
            timeout=timeout
        )
        
        async with self._lock:
            self.subscriptions[subscription.id] = subscription
        
        logger.info(f"Added subscription: {subscription.id}")
        return subscription.id
    
    async def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from events
        
        Args:
            subscription_id: Subscription ID to remove
            
        Returns:
            True if subscription was removed
        """
        async with self._lock:
            removed = self.subscriptions.pop(subscription_id, None)
        
        if removed:
            logger.info(f"Removed subscription: {subscription_id}")
            return True
        else:
            logger.warning(f"Subscription not found: {subscription_id}")
            return False
    
    async def get_event_history(self, filter: Optional[EventFilter] = None,
                               limit: int = 100) -> List[EnhancedEvent]:
        """Get event history matching filter"""
        return self.history.get_events(filter, limit)
    
    async def replay_events(self, filter: EventFilter, 
                           from_time: Optional[datetime] = None,
                           to_time: Optional[datetime] = None) -> int:
        """
        Replay historical events
        
        Args:
            filter: Event filter for replay
            from_time: Start time for replay
            to_time: End time for replay
            
        Returns:
            Number of events replayed
        """
        events = self.history.get_events(filter, limit=10000)
        replayed_count = 0
        
        for event in events:
            # Check time bounds
            if from_time and event.timestamp < from_time:
                continue
            if to_time and event.timestamp > to_time:
                continue
            
            # Create new event for replay
            replay_event = EnhancedEvent(
                type=event.type,
                data=event.data,
                priority=event.priority,
                source=f"replay:{event.source}",
                correlation_id=event.correlation_id,
                parent_event_id=event.event_id
            )
            
            await self.queue.put(replay_event)
            replayed_count += 1
        
        logger.info(f"Replayed {replayed_count} events")
        return replayed_count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        base_stats = self.processor.get_stats()
        
        return {
            **base_stats,
            "queue_size": self.queue.size(),
            "queue_max_size": self.queue.max_size,
            "subscriptions_count": len(self.subscriptions),
            "history_size": len(self.history.events),
            "history_max_size": self.history.max_events
        }


# Global event bus instance
_event_bus: Optional[EnhancedEventBus] = None


def get_event_bus() -> EnhancedEventBus:
    """Get the global event bus instance"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EnhancedEventBus()
    return _event_bus


async def publish_event(event_type: str, data: Dict[str, Any], 
                       priority: EventPriority = EventPriority.NORMAL,
                       **kwargs) -> str:
    """Publish an event to the global event bus"""
    return await get_event_bus().publish(event_type, data, priority, **kwargs)


async def subscribe_to_events(event_filter: EventFilter, handler: Callable, **kwargs) -> str:
    """Subscribe to events on the global event bus"""
    return await get_event_bus().subscribe(event_filter, handler, **kwargs)


# Convenience functions for specific event types
async def publish_agent_event(agent_id: str, event_type: str, data: Dict[str, Any]) -> str:
    """Publish an agent-related event"""
    return await publish_event(
        f"agent.{event_type}",
        {**data, "agent_id": agent_id},
        source=f"agent:{agent_id}"
    )


async def publish_swarm_event(swarm_id: str, event_type: str, data: Dict[str, Any]) -> str:
    """Publish a swarm-related event"""
    return await publish_event(
        f"swarm.{event_type}",
        {**data, "swarm_id": swarm_id},
        source=f"swarm:{swarm_id}"
    )


async def publish_system_event(event_type: str, data: Dict[str, Any], 
                              priority: EventPriority = EventPriority.HIGH) -> str:
    """Publish a system-related event"""
    return await publish_event(
        f"system.{event_type}",
        data,
        priority=priority,
        source="system"
    )