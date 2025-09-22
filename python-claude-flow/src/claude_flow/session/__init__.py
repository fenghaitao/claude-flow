"""
Session Management for Claude-Flow

This module provides comprehensive session management including:
- Persistent session storage with SQLite
- Session state tracking and recovery
- Event recording and replay
- Participant management
- Checkpoint creation and restoration
- Swarm consensus and decision-making
"""

from .session_manager import (
    SessionManager,
    SessionStatus,
    SessionType,
    SessionParticipant,
    SessionState,
    SessionEvent
)
from .recovery_engine import (
    SessionRecoveryEngine,
    RecoveryStrategy,
    CheckpointType,
    RecoveryPlan,
    CheckpointMetadata
)
from .consensus_engine import (
    SwarmConsensusEngine,
    ConsensusAlgorithm,
    VoteType,
    ProposalStatus,
    Vote,
    Proposal,
    ConsensusResult
)

__all__ = [
    "SessionManager",
    "SessionStatus", 
    "SessionType",
    "SessionParticipant",
    "SessionState",
    "SessionEvent",
    "SessionRecoveryEngine",
    "RecoveryStrategy",
    "CheckpointType",
    "RecoveryPlan",
    "CheckpointMetadata",
    "SwarmConsensusEngine",
    "ConsensusAlgorithm",
    "VoteType",
    "ProposalStatus",
    "Vote",
    "Proposal",
    "ConsensusResult"
]