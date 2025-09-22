"""
Swarm coordination system for Claude-Flow

This module provides swarm intelligence and coordination capabilities:
- Swarm orchestrator for multi-agent coordination
- Consensus mechanisms for decision making
- Task distribution and load balancing
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .swarm_coordinator import SwarmCoordinator
    from .consensus_engine import ConsensusEngine
    from .task_distributor import TaskDistributor

__all__ = [
    "SwarmCoordinator",
    "ConsensusEngine",
    "TaskDistributor",
]

# Lazy imports to avoid circular dependencies  
def __getattr__(name: str):
    if name == "SwarmCoordinator":
        from .swarm_coordinator import SwarmCoordinator
        return SwarmCoordinator
    elif name == "ConsensusEngine":
        from .consensus_engine import ConsensusEngine
        return ConsensusEngine
    elif name == "TaskDistributor":
        from .task_distributor import TaskDistributor
        return TaskDistributor
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")