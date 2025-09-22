"""
Swarm Consensus and Decision-Making Mechanisms for Claude-Flow

This module provides sophisticated consensus algorithms and decision-making
mechanisms for coordinating agent swarms in distributed environments.
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Callable
from enum import Enum
from dataclasses import dataclass, field
import uuid
import hashlib
from collections import defaultdict, Counter

from .session_manager import SessionManager
from ..core.interfaces import BaseComponent
from ..core.event_bus import publish_event, subscribe_to_events, EventFilter, EventPriority

logger = logging.getLogger(__name__)


class ConsensusAlgorithm(Enum):
    """Consensus algorithm types"""
    RAFT = "raft"
    PBFT = "pbft"
    PROOF_OF_STAKE = "proof_of_stake"
    MAJORITY_VOTE = "majority_vote"
    WEIGHTED_CONSENSUS = "weighted_consensus"
    HYBRID = "hybrid"


class VoteType(Enum):
    """Vote types"""
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"
    VETO = "veto"


class ProposalStatus(Enum):
    """Proposal status"""
    PENDING = "pending"
    VOTING = "voting"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    EXPIRED = "expired"


@dataclass
class Vote:
    """Vote information"""
    voter_id: str
    vote_type: VoteType
    weight: float
    timestamp: datetime
    reasoning: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Proposal:
    """Consensus proposal"""
    proposal_id: str
    proposer_id: str
    title: str
    description: str
    proposal_type: str
    data: Dict[str, Any]
    created_at: datetime
    expires_at: Optional[datetime]
    status: ProposalStatus
    votes: List[Vote] = field(default_factory=list)
    execution_callback: Optional[Callable] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConsensusResult:
    """Consensus result"""
    proposal_id: str
    approved: bool
    vote_counts: Dict[VoteType, int]
    vote_weights: Dict[VoteType, float]
    participation_rate: float
    consensus_reached_at: datetime
    execution_status: Optional[str] = None


class SwarmConsensusEngine(BaseComponent):
    """
    Swarm Consensus Engine
    
    Provides distributed consensus and decision-making including:
    - Multiple consensus algorithms (Raft, PBFT, Majority Vote, etc.)
    - Weighted voting based on agent capabilities and reputation
    - Proposal lifecycle management
    - Automatic execution of approved proposals
    - Conflict resolution and deadlock prevention
    """
    
    def __init__(self, session_manager: SessionManager):
        super().__init__()
        self.session_manager = session_manager
        
        # Consensus configuration
        self.default_algorithm = ConsensusAlgorithm.WEIGHTED_CONSENSUS
        self.vote_timeout = timedelta(minutes=10)
        self.min_participation_rate = 0.6  # 60% minimum participation
        self.proposal_expiry = timedelta(hours=24)
        
        # State tracking
        self.active_proposals: Dict[str, Proposal] = {}
        self.consensus_history: List[ConsensusResult] = []
        self.agent_weights: Dict[str, float] = {}
        self.agent_reputation: Dict[str, float] = {}
        
        # Consensus algorithms
        self.consensus_algorithms = {
            ConsensusAlgorithm.RAFT: self._execute_raft_consensus,
            ConsensusAlgorithm.PBFT: self._execute_pbft_consensus,
            ConsensusAlgorithm.MAJORITY_VOTE: self._execute_majority_vote,
            ConsensusAlgorithm.WEIGHTED_CONSENSUS: self._execute_weighted_consensus,
            ConsensusAlgorithm.PROOF_OF_STAKE: self._execute_proof_of_stake,
            ConsensusAlgorithm.HYBRID: self._execute_hybrid_consensus
        }
        
        # Background tasks
        self.background_tasks: Set[asyncio.Task] = set()
        
        # Decision-making rules
        self.decision_rules = {
            "task_assignment": {"algorithm": ConsensusAlgorithm.WEIGHTED_CONSENSUS, "threshold": 0.6},
            "resource_allocation": {"algorithm": ConsensusAlgorithm.MAJORITY_VOTE, "threshold": 0.5},
            "agent_promotion": {"algorithm": ConsensusAlgorithm.PBFT, "threshold": 0.66},
            "system_changes": {"algorithm": ConsensusAlgorithm.RAFT, "threshold": 0.75},
            "emergency_actions": {"algorithm": ConsensusAlgorithm.MAJORITY_VOTE, "threshold": 0.5}
        }
    
    async def _start_implementation(self) -> None:
        """Start the consensus engine"""
        # Initialize agent weights and reputation
        await self._initialize_agent_metrics()
        
        # Setup event subscriptions
        await self._setup_event_subscriptions()
        
        # Start background tasks
        self.background_tasks.add(asyncio.create_task(self._proposal_monitoring_loop()))
        self.background_tasks.add(asyncio.create_task(self._reputation_update_loop()))
        
        logger.info("Swarm Consensus Engine started")
    
    async def _stop_implementation(self) -> None:
        """Stop the consensus engine"""
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        # Complete active proposals
        await self._complete_active_proposals()
        
        logger.info("Swarm Consensus Engine stopped")
    
    async def _health_check_implementation(self) -> Dict[str, Any]:
        """Health check for consensus engine"""
        return {
            "active_proposals": len(self.active_proposals),
            "consensus_history_size": len(self.consensus_history),
            "registered_agents": len(self.agent_weights),
            "background_tasks": len(self.background_tasks)
        }
    
    async def create_proposal(self, proposer_id: str, title: str, description: str,
                            proposal_type: str, data: Dict[str, Any],
                            algorithm: Optional[ConsensusAlgorithm] = None,
                            expires_in: Optional[timedelta] = None,
                            execution_callback: Optional[Callable] = None) -> str:
        """Create a new consensus proposal"""
        try:
            proposal_id = str(uuid.uuid4())
            current_time = datetime.now()
            
            # Determine consensus algorithm
            if not algorithm:
                rule = self.decision_rules.get(proposal_type, {})
                algorithm = rule.get("algorithm", self.default_algorithm)
            
            # Set expiration time
            expires_at = None
            if expires_in:
                expires_at = current_time + expires_in
            elif self.proposal_expiry:
                expires_at = current_time + self.proposal_expiry
            
            # Create proposal
            proposal = Proposal(
                proposal_id=proposal_id,
                proposer_id=proposer_id,
                title=title,
                description=description,
                proposal_type=proposal_type,
                data=data,
                created_at=current_time,
                expires_at=expires_at,
                status=ProposalStatus.PENDING,
                execution_callback=execution_callback,
                metadata={"algorithm": algorithm.value}
            )
            
            # Store proposal
            self.active_proposals[proposal_id] = proposal
            
            # Transition to voting phase
            await self._start_voting_phase(proposal_id)
            
            # Emit proposal created event
            await publish_event(
                "consensus.proposal_created",
                {
                    "proposal_id": proposal_id,
                    "proposer_id": proposer_id,
                    "title": title,
                    "proposal_type": proposal_type,
                    "algorithm": algorithm.value
                },
                priority=EventPriority.HIGH,
                source=f"consensus:{self.id}"
            )
            
            logger.info(f"Created proposal {proposal_id}: {title}")
            return proposal_id
            
        except Exception as e:
            logger.error(f"Failed to create proposal: {e}")
            raise
    
    async def submit_vote(self, proposal_id: str, voter_id: str, vote_type: VoteType,
                         reasoning: Optional[str] = None) -> bool:
        """Submit a vote for a proposal"""
        try:
            if proposal_id not in self.active_proposals:
                logger.warning(f"Proposal {proposal_id} not found")
                return False
            
            proposal = self.active_proposals[proposal_id]
            
            # Check if proposal is in voting phase
            if proposal.status != ProposalStatus.VOTING:
                logger.warning(f"Proposal {proposal_id} is not in voting phase")
                return False
            
            # Check if voter already voted
            for existing_vote in proposal.votes:
                if existing_vote.voter_id == voter_id:
                    logger.warning(f"Voter {voter_id} already voted on proposal {proposal_id}")
                    return False
            
            # Get voter weight
            voter_weight = self.agent_weights.get(voter_id, 1.0)
            
            # Create vote
            vote = Vote(
                voter_id=voter_id,
                vote_type=vote_type,
                weight=voter_weight,
                timestamp=datetime.now(),
                reasoning=reasoning
            )
            
            # Add vote to proposal
            proposal.votes.append(vote)
            
            # Check if consensus is reached
            await self._check_consensus(proposal_id)
            
            # Emit vote submitted event
            await publish_event(
                "consensus.vote_submitted",
                {
                    "proposal_id": proposal_id,
                    "voter_id": voter_id,
                    "vote_type": vote_type.value,
                    "weight": voter_weight
                },
                priority=EventPriority.NORMAL,
                source=f"consensus:{self.id}"
            )
            
            logger.info(f"Vote submitted by {voter_id} for proposal {proposal_id}: {vote_type.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to submit vote: {e}")
            return False
    
    async def get_proposal(self, proposal_id: str) -> Optional[Proposal]:
        """Get proposal by ID"""
        return self.active_proposals.get(proposal_id)
    
    async def list_active_proposals(self) -> List[Proposal]:
        """List all active proposals"""
        return list(self.active_proposals.values())
    
    async def get_consensus_history(self, limit: int = 100) -> List[ConsensusResult]:
        """Get consensus history"""
        return self.consensus_history[-limit:]
    
    async def force_consensus_check(self, proposal_id: str) -> Optional[ConsensusResult]:
        """Force consensus check for a proposal"""
        if proposal_id not in self.active_proposals:
            return None
        
        return await self._check_consensus(proposal_id)
    
    # Private methods
    
    async def _start_voting_phase(self, proposal_id: str) -> None:
        """Start voting phase for a proposal"""
        if proposal_id not in self.active_proposals:
            return
        
        proposal = self.active_proposals[proposal_id]
        proposal.status = ProposalStatus.VOTING
        
        # Emit voting started event
        await publish_event(
            "consensus.voting_started",
            {
                "proposal_id": proposal_id,
                "title": proposal.title,
                "expires_at": proposal.expires_at.isoformat() if proposal.expires_at else None
            },
            priority=EventPriority.HIGH,
            source=f"consensus:{self.id}"
        )
        
        logger.info(f"Started voting phase for proposal {proposal_id}")
    
    async def _check_consensus(self, proposal_id: str) -> Optional[ConsensusResult]:
        """Check if consensus is reached for a proposal"""
        try:
            if proposal_id not in self.active_proposals:
                return None
            
            proposal = self.active_proposals[proposal_id]
            
            # Get consensus algorithm
            algorithm_name = proposal.metadata.get("algorithm", self.default_algorithm.value)
            algorithm = ConsensusAlgorithm(algorithm_name)
            
            # Execute consensus algorithm
            consensus_func = self.consensus_algorithms.get(algorithm)
            if not consensus_func:
                logger.error(f"Unknown consensus algorithm: {algorithm}")
                return None
            
            result = await consensus_func(proposal)
            
            if result:
                # Update proposal status
                proposal.status = ProposalStatus.APPROVED if result.approved else ProposalStatus.REJECTED
                
                # Execute proposal if approved
                if result.approved and proposal.execution_callback:
                    try:
                        await proposal.execution_callback(proposal)
                        result.execution_status = "success"
                        proposal.status = ProposalStatus.EXECUTED
                    except Exception as e:
                        logger.error(f"Failed to execute proposal {proposal_id}: {e}")
                        result.execution_status = "failed"
                
                # Add to history and remove from active
                self.consensus_history.append(result)
                self.active_proposals.pop(proposal_id, None)
                
                # Update agent reputation based on voting
                await self._update_agent_reputation(proposal, result)
                
                # Emit consensus reached event
                await publish_event(
                    "consensus.consensus_reached",
                    {
                        "proposal_id": proposal_id,
                        "approved": result.approved,
                        "participation_rate": result.participation_rate,
                        "execution_status": result.execution_status
                    },
                    priority=EventPriority.HIGH,
                    source=f"consensus:{self.id}"
                )
                
                logger.info(f"Consensus reached for proposal {proposal_id}: {'approved' if result.approved else 'rejected'}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to check consensus for proposal {proposal_id}: {e}")
            return None
    
    # Consensus algorithms
    
    async def _execute_weighted_consensus(self, proposal: Proposal) -> Optional[ConsensusResult]:
        """Execute weighted consensus algorithm"""
        if not proposal.votes:
            return None
        
        # Calculate vote weights
        vote_weights = defaultdict(float)
        total_weight = 0.0
        
        for vote in proposal.votes:
            vote_weights[vote.vote_type] += vote.weight
            total_weight += vote.weight
        
        # Get decision threshold
        threshold = self.decision_rules.get(proposal.proposal_type, {}).get("threshold", 0.6)
        
        # Check if approval threshold is met
        approval_weight = vote_weights[VoteType.APPROVE]
        approval_ratio = approval_weight / total_weight if total_weight > 0 else 0
        
        # Calculate participation rate
        total_eligible_weight = sum(self.agent_weights.values())
        participation_rate = total_weight / total_eligible_weight if total_eligible_weight > 0 else 0
        
        # Check minimum participation
        if participation_rate < self.min_participation_rate:
            return None
        
        # Determine approval
        approved = approval_ratio >= threshold
        
        return ConsensusResult(
            proposal_id=proposal.proposal_id,
            approved=approved,
            vote_counts={vt: sum(1 for v in proposal.votes if v.vote_type == vt) for vt in VoteType},
            vote_weights=dict(vote_weights),
            participation_rate=participation_rate,
            consensus_reached_at=datetime.now()
        )
    
    async def _execute_majority_vote(self, proposal: Proposal) -> Optional[ConsensusResult]:
        """Execute majority vote consensus algorithm"""
        if not proposal.votes:
            return None
        
        # Count votes
        vote_counts = Counter(vote.vote_type for vote in proposal.votes)
        total_votes = len(proposal.votes)
        
        # Calculate participation rate
        total_agents = len(self.agent_weights)
        participation_rate = total_votes / total_agents if total_agents > 0 else 0
        
        # Check minimum participation
        if participation_rate < self.min_participation_rate:
            return None
        
        # Determine approval (simple majority)
        approve_votes = vote_counts[VoteType.APPROVE]
        approved = approve_votes > (total_votes / 2)
        
        return ConsensusResult(
            proposal_id=proposal.proposal_id,
            approved=approved,
            vote_counts=dict(vote_counts),
            vote_weights={vt: float(count) for vt, count in vote_counts.items()},
            participation_rate=participation_rate,
            consensus_reached_at=datetime.now()
        )
    
    async def _execute_raft_consensus(self, proposal: Proposal) -> Optional[ConsensusResult]:
        """Execute Raft consensus algorithm (simplified)"""
        # Simplified Raft implementation - in practice would require leader election
        return await self._execute_majority_vote(proposal)
    
    async def _execute_pbft_consensus(self, proposal: Proposal) -> Optional[ConsensusResult]:
        """Execute PBFT consensus algorithm (simplified)"""
        if not proposal.votes:
            return None
        
        total_votes = len(proposal.votes)
        approve_votes = sum(1 for vote in proposal.votes if vote.vote_type == VoteType.APPROVE)
        
        # PBFT requires 2/3+ approval
        threshold = (2 * total_votes) / 3
        approved = approve_votes > threshold
        
        # Calculate participation rate
        total_agents = len(self.agent_weights)
        participation_rate = total_votes / total_agents if total_agents > 0 else 0
        
        if participation_rate < self.min_participation_rate:
            return None
        
        vote_counts = Counter(vote.vote_type for vote in proposal.votes)
        
        return ConsensusResult(
            proposal_id=proposal.proposal_id,
            approved=approved,
            vote_counts=dict(vote_counts),
            vote_weights={vt: float(count) for vt, count in vote_counts.items()},
            participation_rate=participation_rate,
            consensus_reached_at=datetime.now()
        )
    
    async def _execute_proof_of_stake(self, proposal: Proposal) -> Optional[ConsensusResult]:
        """Execute Proof of Stake consensus algorithm"""
        # Similar to weighted consensus but with stake-based weights
        return await self._execute_weighted_consensus(proposal)
    
    async def _execute_hybrid_consensus(self, proposal: Proposal) -> Optional[ConsensusResult]:
        """Execute hybrid consensus algorithm"""
        # Use different algorithms based on proposal type
        if proposal.proposal_type in ["emergency_actions", "task_assignment"]:
            return await self._execute_majority_vote(proposal)
        elif proposal.proposal_type in ["system_changes", "agent_promotion"]:
            return await self._execute_pbft_consensus(proposal)
        else:
            return await self._execute_weighted_consensus(proposal)
    
    async def _initialize_agent_metrics(self) -> None:
        """Initialize agent weights and reputation"""
        # This would typically load from agent registry
        # For now, set default values
        self.agent_weights = {"default_agent": 1.0}
        self.agent_reputation = {"default_agent": 1.0}
    
    async def _update_agent_reputation(self, proposal: Proposal, result: ConsensusResult) -> None:
        """Update agent reputation based on voting behavior"""
        try:
            # Simple reputation update based on voting with majority
            majority_vote = VoteType.APPROVE if result.approved else VoteType.REJECT
            
            for vote in proposal.votes:
                agent_id = vote.voter_id
                current_rep = self.agent_reputation.get(agent_id, 1.0)
                
                if vote.vote_type == majority_vote:
                    # Voted with majority - small reputation boost
                    self.agent_reputation[agent_id] = min(2.0, current_rep + 0.01)
                else:
                    # Voted against majority - small reputation penalty
                    self.agent_reputation[agent_id] = max(0.1, current_rep - 0.005)
        
        except Exception as e:
            logger.error(f"Failed to update agent reputation: {e}")
    
    async def _proposal_monitoring_loop(self) -> None:
        """Background loop to monitor proposal timeouts"""
        while True:
            try:
                current_time = datetime.now()
                expired_proposals = []
                
                for proposal_id, proposal in self.active_proposals.items():
                    if (proposal.expires_at and current_time > proposal.expires_at and
                        proposal.status in [ProposalStatus.PENDING, ProposalStatus.VOTING]):
                        expired_proposals.append(proposal_id)
                
                # Mark expired proposals
                for proposal_id in expired_proposals:
                    proposal = self.active_proposals[proposal_id]
                    proposal.status = ProposalStatus.EXPIRED
                    
                    # Emit expiration event
                    await publish_event(
                        "consensus.proposal_expired",
                        {"proposal_id": proposal_id, "title": proposal.title},
                        priority=EventPriority.NORMAL,
                        source=f"consensus:{self.id}"
                    )
                    
                    # Remove from active proposals
                    self.active_proposals.pop(proposal_id, None)
                    
                    logger.info(f"Proposal {proposal_id} expired")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Proposal monitoring loop error: {e}")
                await asyncio.sleep(300)
    
    async def _reputation_update_loop(self) -> None:
        """Background loop to update agent reputation"""
        while True:
            try:
                # Periodic reputation decay to prevent permanent reputation damage
                for agent_id in self.agent_reputation:
                    current_rep = self.agent_reputation[agent_id]
                    # Slowly move reputation back toward neutral (1.0)
                    if current_rep > 1.0:
                        self.agent_reputation[agent_id] = max(1.0, current_rep - 0.001)
                    elif current_rep < 1.0:
                        self.agent_reputation[agent_id] = min(1.0, current_rep + 0.001)
                
                await asyncio.sleep(3600)  # Update every hour
                
            except Exception as e:
                logger.error(f"Reputation update loop error: {e}")
                await asyncio.sleep(1800)
    
    async def _complete_active_proposals(self) -> None:
        """Complete or expire all active proposals during shutdown"""
        for proposal_id in list(self.active_proposals.keys()):
            proposal = self.active_proposals[proposal_id]
            proposal.status = ProposalStatus.EXPIRED
            self.active_proposals.pop(proposal_id, None)
            logger.info(f"Expired proposal {proposal_id} during shutdown")
    
    async def _setup_event_subscriptions(self) -> None:
        """Setup event subscriptions for consensus engine"""
        # Subscribe to agent events to update weights and reputation
        agent_filter = EventFilter(
            event_types=["agent.started", "agent.stopped", "agent.task_completed"],
            sources=["agent:*"]
        )
        
        await subscribe_to_events(agent_filter, self._handle_agent_event)
    
    async def _handle_agent_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Handle agent events for consensus management"""
        try:
            agent_id = data.get("agent_id")
            if not agent_id:
                return
            
            if event_type == "agent.started":
                # Initialize agent metrics
                self.agent_weights[agent_id] = 1.0
                self.agent_reputation[agent_id] = 1.0
                
            elif event_type == "agent.stopped":
                # Remove agent from consensus
                self.agent_weights.pop(agent_id, None)
                self.agent_reputation.pop(agent_id, None)
                
            elif event_type == "agent.task_completed":
                # Boost agent weight based on successful task completion
                current_weight = self.agent_weights.get(agent_id, 1.0)
                self.agent_weights[agent_id] = min(2.0, current_weight + 0.01)
        
        except Exception as e:
            logger.error(f"Failed to handle agent event {event_type}: {e}")
    
    def get_consensus_statistics(self) -> Dict[str, Any]:
        """Get consensus statistics"""
        total_consensus = len(self.consensus_history)
        approved_consensus = sum(1 for r in self.consensus_history if r.approved)
        
        algorithm_stats = defaultdict(lambda: {"total": 0, "approved": 0})
        for proposal in self.active_proposals.values():
            algorithm = proposal.metadata.get("algorithm", "unknown")
            algorithm_stats[algorithm]["total"] += 1
        
        for result in self.consensus_history:
            # This would require storing algorithm info in results
            algorithm_stats["unknown"]["total"] += 1
            if result.approved:
                algorithm_stats["unknown"]["approved"] += 1
        
        return {
            "total_consensus_reached": total_consensus,
            "approval_rate": approved_consensus / max(total_consensus, 1),
            "active_proposals": len(self.active_proposals),
            "registered_agents": len(self.agent_weights),
            "algorithm_statistics": dict(algorithm_stats),
            "average_participation_rate": sum(r.participation_rate for r in self.consensus_history) / max(total_consensus, 1)
        }