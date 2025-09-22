"""
Agent orchestration system for Claude-Flow

This module provides the agent orchestration framework including:
- Queen Agent: Master coordinator for task management
- Worker Agents: Specialized agents for specific tasks
- Assignment Engine: Intelligent task assignment
- Lifecycle Manager: Agent health and fault tolerance
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .queen.queen_agent import QueenAgent
    from .workers.architect_agent import ArchitectAgent
    from .workers.coder_agent import CoderAgent
    from .workers.tester_agent import TesterAgent
    from .assignment_engine import AgentAssignmentEngine
    from .lifecycle_manager import AgentLifecycleManager

__all__ = [
    "QueenAgent",
    "ArchitectAgent", 
    "CoderAgent",
    "TesterAgent",
    "AgentAssignmentEngine",
    "AgentLifecycleManager",
]

# Lazy imports to avoid circular dependencies
def __getattr__(name: str):
    if name == "QueenAgent":
        from .queen.queen_agent import QueenAgent
        return QueenAgent
    elif name == "ArchitectAgent":
        from .workers.architect_agent import ArchitectAgent
        return ArchitectAgent
    elif name == "CoderAgent":
        from .workers.coder_agent import CoderAgent
        return CoderAgent
    elif name == "TesterAgent":
        from .workers.tester_agent import TesterAgent
        return TesterAgent
    elif name == "AgentAssignmentEngine":
        from .assignment_engine import AgentAssignmentEngine
        return AgentAssignmentEngine
    elif name == "AgentLifecycleManager":
        from .lifecycle_manager import AgentLifecycleManager
        return AgentLifecycleManager
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")