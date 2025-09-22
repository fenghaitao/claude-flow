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

# Enterprise modules (lazy imports to avoid circular dependencies)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .agents import AgentManager, QueenAgent
    from .swarm import SwarmCoordinator
    from .memory import MemoryManager
    from .neural import NeuralEngine
    from .integrations import ClaudeClient
    from .monitoring import MetricsCollector
    from .deployment import DockerManager
    from .mcp.mcp_client import MCPClient

__all__ = [
    "Config",
    "config",
    "EventBus",
    "Event", 
    "EventType",
    "AgentManager",
    "QueenAgent",
    "SwarmCoordinator",
    "MemoryManager",
    "NeuralEngine",
    "ClaudeClient",
    "MetricsCollector",
    "DockerManager",
    "MCPClient",
]

# Lazy imports to avoid circular dependencies
def __getattr__(name: str):
    if name == "AgentManager":
        from .agents import AgentManager
        return AgentManager
    elif name == "QueenAgent":
        from .agents import QueenAgent
        return QueenAgent
    elif name == "SwarmCoordinator":
        from .swarm import SwarmCoordinator
        return SwarmCoordinator
    elif name == "MemoryManager":
        from .memory import MemoryManager
        return MemoryManager
    elif name == "NeuralEngine":
        from .neural import NeuralEngine
        return NeuralEngine
    elif name == "ClaudeClient":
        from .integrations import ClaudeClient
        return ClaudeClient
    elif name == "MetricsCollector":
        from .monitoring import MetricsCollector
        return MetricsCollector
    elif name == "DockerManager":
        from .deployment import DockerManager
        return DockerManager
    elif name == "MCPClient":
        from .mcp.mcp_client import MCPClient
        return MCPClient
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
