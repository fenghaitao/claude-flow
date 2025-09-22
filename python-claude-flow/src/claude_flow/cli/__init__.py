"""
CLI Package for Claude-Flow - Advanced Command Line Interface.

This module provides a comprehensive CLI interface using Click framework
with Rich styling, progress bars, and interactive features.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .main import claude_flow_cli
    from .commands import swarm, neural, memory, system, workflow, mcp
    from .interactive import InteractiveShell
    from .progress import ProgressManager
    from .help import HelpSystem

__all__ = [
    "claude_flow_cli",
    "swarm",
    "neural", 
    "memory",
    "system",
    "workflow",
    "mcp",
    "InteractiveShell",
    "ProgressManager",
    "HelpSystem"
]

def __getattr__(name: str):
    """Lazy import for CLI components."""
    if name == "claude_flow_cli":
        from .main import claude_flow_cli
        return claude_flow_cli
    elif name == "InteractiveShell":
        from .interactive import InteractiveShell
        return InteractiveShell
    elif name == "ProgressManager":
        from .progress import ProgressManager
        return ProgressManager
    elif name == "HelpSystem":
        from .help import HelpSystem
        return HelpSystem
    elif name in ["swarm", "neural", "memory", "system", "workflow", "mcp"]:
        from .commands import __getattr__ as cmd_getattr
        return cmd_getattr(name)
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")