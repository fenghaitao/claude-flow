"""
Claude-Flow: Enterprise-grade AI agent orchestration platform

A Python port of the original TypeScript/Node.js implementation.
"""

__version__ = "2.0.0-alpha.90"
__author__ = "rUv"
__license__ = "MIT"

# Import simplified core modules (no external dependencies)
from .core.config_simple import Config, config
from .core.event_bus_simple import EventBus, Event, EventType

# For now, we'll import other modules when they're implemented
# from .agents.agent_manager import AgentManager
# from .swarm.swarm_coordinator import SwarmCoordinator
# from .memory.memory_manager import MemoryManager
# from .mcp.mcp_client import MCPClient

__all__ = [
    "Config",
    "config",
    "EventBus",
    "Event", 
    "EventType",
    # "AgentManager",
    # "SwarmCoordinator",
    # "MemoryManager",
    # "MCPClient",
]
