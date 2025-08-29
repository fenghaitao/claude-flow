"""
Claude-Flow Core Module

This module provides the core functionality for Claude-Flow.
"""

# Core configuration
from .config_simple import Config, config

# Core utilities
from .event_bus_simple import EventBus, Event, EventType

# Export main components
__all__ = [
    'Config',
    'config',
    'EventBus',
    'Event',
    'EventType'
]
