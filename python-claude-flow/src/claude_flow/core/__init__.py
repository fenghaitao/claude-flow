"""
Claude-Flow Core Module

This module provides the core functionality for Claude-Flow.
"""

# Core configuration (enhanced and simple)
from .config_simple import Config as SimpleConfig, config as simple_config
from .config import Config, config, init_config
from .config_models import ClaudeFlowConfig
from .config_manager import ConfigManager

# Core utilities
from .event_bus_simple import EventBus, Event, EventType
from .event_bus import (
    EnhancedEventBus, EnhancedEvent, EventFilter, EventPriority, EventStatus,
    get_event_bus, publish_event, subscribe_to_events
)
from .event_persistence import (
    EventPersistenceManager, get_persistence_manager,
    persist_event, get_persisted_event, query_persisted_events
)

# Export main components
__all__ = [
    'Config',
    'config',
    'SimpleConfig',
    'simple_config',
    'init_config',
    'ClaudeFlowConfig',
    'ConfigManager',
    'EventBus',
    'Event',
    'EventType',
    'EnhancedEventBus',
    'EnhancedEvent',
    'EventFilter',
    'EventPriority',
    'EventStatus',
    'EventPersistenceManager',
    'get_event_bus',
    'get_persistence_manager',
    'publish_event',
    'subscribe_to_events',
    'persist_event',
    'get_persisted_event',
    'query_persisted_events'
]
