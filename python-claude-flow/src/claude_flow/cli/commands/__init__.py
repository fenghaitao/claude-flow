"""
CLI Commands Package - Command Groups for Different Modules.

This package organizes CLI commands into logical groups corresponding 
to the major Claude-Flow components.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .swarm import swarm_cli
    from .neural import neural_cli
    from .memory import memory_cli
    from .system import system_cli
    from .workflow import workflow_cli
    from .mcp import mcp_cli
    from .interactive import interactive_cli

__all__ = [
    "swarm_cli",
    "neural_cli",
    "memory_cli", 
    "system_cli",
    "workflow_cli",
    "mcp_cli",
    "interactive_cli"
]

def __getattr__(name: str):
    """Lazy import for command modules."""
    if name == "swarm":
        from .swarm import swarm_cli
        return swarm_cli
    elif name == "neural":
        from .neural import neural_cli
        return neural_cli
    elif name == "memory":
        from .memory import memory_cli
        return memory_cli
    elif name == "system":
        from .system import system_cli
        return system_cli
    elif name == "workflow":
        from .workflow import workflow_cli
        return workflow_cli
    elif name == "mcp":
        from .mcp import mcp_cli
        return mcp_cli
    elif name == "interactive":
        from .interactive import interactive_cli
        return interactive_cli
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")