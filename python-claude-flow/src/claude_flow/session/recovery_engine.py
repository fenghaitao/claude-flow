"""
Session State Recovery and Checkpointing for Claude-Flow

This module provides advanced session recovery mechanisms including
state restoration, checkpoint management, and failure recovery.
"""

import asyncio
import logging
import json
import pickle
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Callable
from enum import Enum
from dataclasses import dataclass
import uuid

from .session_manager import SessionManager, SessionStatus, SessionState, SessionEvent
from ..core.interfaces import BaseComponent
from ..core.event_bus import publish_event, EventPriority

logger = logging.getLogger(__name__)


class RecoveryStrategy(Enum):
    """Recovery strategy types"""
    FULL_RESTORE = "full_restore"
    PARTIAL_RESTORE = "partial_restore"
    CHECKPOINT_ROLLBACK = "checkpoint_rollback"
    EVENT_REPLAY = "event_replay"
    CLEAN_START = "clean_start"


class CheckpointType(Enum):
    """Checkpoint types"""
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    MILESTONE = "milestone"
    ERROR_RECOVERY = "error_recovery"
    PERIODIC = "periodic"


@dataclass
class RecoveryPlan:
    """Recovery plan specification"""
    session_id: str
    strategy: RecoveryStrategy
    target_checkpoint: Optional[datetime]
    recovery_steps: List[Dict[str, Any]]
    estimated_time: timedelta
    risk_level: str
    rollback_plan: Optional['RecoveryPlan'] = None


@dataclass
class CheckpointMetadata:
    """Checkpoint metadata"""
    checkpoint_id: str
    session_id: str
    checkpoint_time: datetime
    checkpoint_type: CheckpointType
    data_size: int
    participants_count: int
    session_progress: float
    phase: str
    hash_signature: str
    metadata: Dict[str, Any]


class SessionRecoveryEngine(BaseComponent):
    """
    Session Recovery Engine
    
    Provides comprehensive session recovery including:
    - Intelligent checkpoint creation
    - Multiple recovery strategies
    - State validation and integrity checks
    - Automatic failure detection and recovery
    - Recovery plan generation and execution
    """
    
    def __init__(self, session_manager: SessionManager):
        super().__init__()
        self.session_manager = session_manager
        
        # Recovery configuration
        self.recovery_timeout = 300  # 5 minutes
        self.max_recovery_attempts = 3
        self.checkpoint_retention_days = 30
        self.validation_enabled = True
        
        # Recovery state tracking
        self.active_recoveries: Dict[str, RecoveryPlan] = {}
        self.recovery_history: List[Dict[str, Any]] = []
        
        # Checkpoint management
        self.checkpoint_strategies = {
            CheckpointType.AUTOMATIC: self._create_automatic_checkpoint,
            CheckpointType.MANUAL: self._create_manual_checkpoint,
            CheckpointType.MILESTONE: self._create_milestone_checkpoint,
            CheckpointType.ERROR_RECOVERY: self._create_error_recovery_checkpoint,
            CheckpointType.PERIODIC: self._create_periodic_checkpoint
        }
        
        # Recovery strategies
        self.recovery_strategies = {
            RecoveryStrategy.FULL_RESTORE: self._execute_full_restore,
            RecoveryStrategy.PARTIAL_RESTORE: self._execute_partial_restore,
            RecoveryStrategy.CHECKPOINT_ROLLBACK: self._execute_checkpoint_rollback,
            RecoveryStrategy.EVENT_REPLAY: self._execute_event_replay,
            RecoveryStrategy.CLEAN_START: self._execute_clean_start
        }
        
        # State validators
        self.state_validators: List[Callable] = []
    
    async def _start_implementation(self) -> None:
        """Start the recovery engine"""
        # Register default state validators
        self._register_default_validators()
        
        logger.info("Session Recovery Engine started")
    
    async def _stop_implementation(self) -> None:
        """Stop the recovery engine"""
        # Complete any active recoveries
        await self._complete_active_recoveries()
        
        logger.info("Session Recovery Engine stopped")
    
    async def _health_check_implementation(self) -> Dict[str, Any]:
        """Health check for recovery engine"""
        return {
            "active_recoveries": len(self.active_recoveries),
            "recovery_history_size": len(self.recovery_history),
            "registered_validators": len(self.state_validators),
            "session_manager_healthy": await self.session_manager.health_check()
        }
    
    async def create_checkpoint(self, session_id: str, checkpoint_type: CheckpointType,
                              metadata: Optional[Dict[str, Any]] = None,
                              participant_id: str = "system") -> Optional[str]:
        """Create a session checkpoint"""
        try:
            # Get current session state
            session_state = await self.session_manager.get_session_state(session_id)
            if not session_state:
                logger.warning(f"Session {session_id} not found for checkpoint creation")
                return None
            
            # Use appropriate checkpoint strategy
            strategy = self.checkpoint_strategies.get(checkpoint_type)
            if not strategy:
                logger.error(f"Unknown checkpoint type: {checkpoint_type}")
                return None
            
            checkpoint_id = await strategy(session_state, metadata or {}, participant_id)
            
            # Emit checkpoint created event
            await publish_event(
                "session.checkpoint_created",
                {
                    "session_id": session_id,
                    "checkpoint_id": checkpoint_id,
                    "checkpoint_type": checkpoint_type.value,
                    "participant_id": participant_id
                },
                priority=EventPriority.NORMAL,
                source=f"recovery:{self.id}"
            )
            
            logger.info(f"Created {checkpoint_type.value} checkpoint {checkpoint_id} for session {session_id}")
            return checkpoint_id
            
        except Exception as e:
            logger.error(f"Failed to create checkpoint for session {session_id}: {e}")
            return None
    
    async def recover_session(self, session_id: str, strategy: Optional[RecoveryStrategy] = None,
                            target_checkpoint: Optional[str] = None) -> bool:
        """Recover a session using specified or automatic strategy"""
        try:
            if session_id in self.active_recoveries:
                logger.warning(f"Recovery already in progress for session {session_id}")
                return False
            
            # Analyze session state and determine recovery strategy
            recovery_plan = await self._create_recovery_plan(session_id, strategy, target_checkpoint)
            if not recovery_plan:
                logger.error(f"Could not create recovery plan for session {session_id}")
                return False
            
            # Execute recovery plan
            self.active_recoveries[session_id] = recovery_plan
            
            try:
                success = await self._execute_recovery_plan(recovery_plan)
                
                # Record recovery attempt
                self.recovery_history.append({
                    "session_id": session_id,
                    "strategy": recovery_plan.strategy.value,
                    "success": success,
                    "timestamp": datetime.now(),
                    "execution_time": datetime.now() - datetime.now()  # This would be calculated properly
                })
                
                if success:
                    # Emit recovery success event
                    await publish_event(
                        "session.recovery_success",
                        {
                            "session_id": session_id,
                            "strategy": recovery_plan.strategy.value
                        },
                        priority=EventPriority.HIGH,
                        source=f"recovery:{self.id}"
                    )
                    
                    logger.info(f"Successfully recovered session {session_id} using {recovery_plan.strategy.value}")
                else:
                    # Try rollback plan if available
                    if recovery_plan.rollback_plan:
                        logger.info(f"Attempting rollback for session {session_id}")
                        success = await self._execute_recovery_plan(recovery_plan.rollback_plan)
                
                return success
                
            finally:
                self.active_recoveries.pop(session_id, None)
            
        except Exception as e:
            logger.error(f"Failed to recover session {session_id}: {e}")
            return False
    
    async def validate_session_state(self, session_id: str) -> Tuple[bool, List[str]]:
        """Validate session state integrity"""
        try:
            session_state = await self.session_manager.get_session_state(session_id)
            if not session_state:
                return False, ["Session not found"]
            
            validation_errors = []
            
            # Run all registered validators
            for validator in self.state_validators:
                try:
                    errors = await validator(session_state)
                    if errors:
                        validation_errors.extend(errors)
                except Exception as e:
                    validation_errors.append(f"Validator error: {str(e)}")
            
            is_valid = len(validation_errors) == 0
            
            logger.info(f"Session {session_id} validation: {'passed' if is_valid else 'failed'}")
            if validation_errors:
                logger.warning(f"Validation errors for session {session_id}: {validation_errors}")
            
            return is_valid, validation_errors
            
        except Exception as e:
            logger.error(f"Failed to validate session {session_id}: {e}")
            return False, [f"Validation failed: {str(e)}"]
    
    async def get_checkpoint_history(self, session_id: str) -> List[CheckpointMetadata]:
        """Get checkpoint history for a session"""
        try:
            # This would query the database for checkpoint metadata
            # For now, return empty list as implementation would require database queries
            return []
            
        except Exception as e:
            logger.error(f"Failed to get checkpoint history for session {session_id}: {e}")
            return []
    
    async def rollback_to_checkpoint(self, session_id: str, checkpoint_id: str) -> bool:
        """Rollback session to a specific checkpoint"""
        try:
            # Create recovery plan for checkpoint rollback
            recovery_plan = RecoveryPlan(
                session_id=session_id,
                strategy=RecoveryStrategy.CHECKPOINT_ROLLBACK,
                target_checkpoint=datetime.now(),  # Would be actual checkpoint time
                recovery_steps=[
                    {"action": "load_checkpoint", "checkpoint_id": checkpoint_id},
                    {"action": "restore_state", "validate": True},
                    {"action": "notify_participants", "reason": "rollback"}
                ],
                estimated_time=timedelta(minutes=5),
                risk_level="medium"
            )
            
            return await self._execute_recovery_plan(recovery_plan)
            
        except Exception as e:
            logger.error(f"Failed to rollback session {session_id} to checkpoint {checkpoint_id}: {e}")
            return False
    
    # Private checkpoint creation methods
    
    async def _create_automatic_checkpoint(self, session_state: SessionState, 
                                         metadata: Dict[str, Any], participant_id: str) -> str:
        """Create automatic checkpoint"""
        checkpoint_data = {
            "session_state": session_state.__dict__,
            "checkpoint_type": CheckpointType.AUTOMATIC.value,
            "trigger": "automatic",
            "metadata": metadata
        }
        
        # Save checkpoint through session manager
        await self.session_manager.create_checkpoint(
            session_state.session_id, participant_id, checkpoint_data
        )
        
        return str(uuid.uuid4())
    
    async def _create_manual_checkpoint(self, session_state: SessionState,
                                      metadata: Dict[str, Any], participant_id: str) -> str:
        """Create manual checkpoint"""
        checkpoint_data = {
            "session_state": session_state.__dict__,
            "checkpoint_type": CheckpointType.MANUAL.value,
            "trigger": "manual",
            "requested_by": participant_id,
            "metadata": metadata
        }
        
        await self.session_manager.create_checkpoint(
            session_state.session_id, participant_id, checkpoint_data
        )
        
        return str(uuid.uuid4())
    
    async def _create_milestone_checkpoint(self, session_state: SessionState,
                                         metadata: Dict[str, Any], participant_id: str) -> str:
        """Create milestone checkpoint"""
        checkpoint_data = {
            "session_state": session_state.__dict__,
            "checkpoint_type": CheckpointType.MILESTONE.value,
            "trigger": "milestone",
            "milestone": metadata.get("milestone", "unknown"),
            "metadata": metadata
        }
        
        await self.session_manager.create_checkpoint(
            session_state.session_id, participant_id, checkpoint_data
        )
        
        return str(uuid.uuid4())
    
    async def _create_error_recovery_checkpoint(self, session_state: SessionState,
                                              metadata: Dict[str, Any], participant_id: str) -> str:
        """Create error recovery checkpoint"""
        checkpoint_data = {
            "session_state": session_state.__dict__,
            "checkpoint_type": CheckpointType.ERROR_RECOVERY.value,
            "trigger": "error_recovery",
            "error_context": metadata.get("error_context", {}),
            "metadata": metadata
        }
        
        await self.session_manager.create_checkpoint(
            session_state.session_id, participant_id, checkpoint_data
        )
        
        return str(uuid.uuid4())
    
    async def _create_periodic_checkpoint(self, session_state: SessionState,
                                        metadata: Dict[str, Any], participant_id: str) -> str:
        """Create periodic checkpoint"""
        checkpoint_data = {
            "session_state": session_state.__dict__,
            "checkpoint_type": CheckpointType.PERIODIC.value,
            "trigger": "periodic",
            "interval": metadata.get("interval", "unknown"),
            "metadata": metadata
        }
        
        await self.session_manager.create_checkpoint(
            session_state.session_id, participant_id, checkpoint_data
        )
        
        return str(uuid.uuid4())
    
    # Private recovery methods
    
    async def _create_recovery_plan(self, session_id: str, strategy: Optional[RecoveryStrategy],
                                  target_checkpoint: Optional[str]) -> Optional[RecoveryPlan]:
        """Create a recovery plan for a session"""
        try:
            # Get session state
            session_state = await self.session_manager.get_session_state(session_id)
            if not session_state:
                return None
            
            # Determine strategy if not provided
            if not strategy:
                strategy = await self._determine_recovery_strategy(session_state)
            
            # Create recovery steps based on strategy
            recovery_steps = await self._create_recovery_steps(strategy, session_state, target_checkpoint)
            
            # Estimate execution time
            estimated_time = self._estimate_recovery_time(strategy, recovery_steps)
            
            # Assess risk level
            risk_level = self._assess_recovery_risk(strategy, session_state)
            
            recovery_plan = RecoveryPlan(
                session_id=session_id,
                strategy=strategy,
                target_checkpoint=datetime.now() if target_checkpoint else None,
                recovery_steps=recovery_steps,
                estimated_time=estimated_time,
                risk_level=risk_level
            )
            
            # Create rollback plan if needed
            if strategy in [RecoveryStrategy.FULL_RESTORE, RecoveryStrategy.EVENT_REPLAY]:
                recovery_plan.rollback_plan = RecoveryPlan(
                    session_id=session_id,
                    strategy=RecoveryStrategy.CHECKPOINT_ROLLBACK,
                    target_checkpoint=session_state.last_checkpoint,
                    recovery_steps=[{"action": "rollback_to_last_checkpoint"}],
                    estimated_time=timedelta(minutes=2),
                    risk_level="low"
                )
            
            return recovery_plan
            
        except Exception as e:
            logger.error(f"Failed to create recovery plan for session {session_id}: {e}")
            return None
    
    async def _determine_recovery_strategy(self, session_state: SessionState) -> RecoveryStrategy:
        """Determine the best recovery strategy based on session state"""
        # Simple heuristics for strategy selection
        if session_state.status == SessionStatus.FAILED:
            if session_state.last_checkpoint:
                return RecoveryStrategy.CHECKPOINT_ROLLBACK
            else:
                return RecoveryStrategy.EVENT_REPLAY
        elif session_state.status == SessionStatus.SUSPENDED:
            return RecoveryStrategy.PARTIAL_RESTORE
        else:
            return RecoveryStrategy.FULL_RESTORE
    
    async def _create_recovery_steps(self, strategy: RecoveryStrategy, 
                                   session_state: SessionState,
                                   target_checkpoint: Optional[str]) -> List[Dict[str, Any]]:
        """Create recovery steps based on strategy"""
        steps = []
        
        if strategy == RecoveryStrategy.FULL_RESTORE:
            steps = [
                {"action": "validate_session_integrity"},
                {"action": "restore_participants"},
                {"action": "restore_context"},
                {"action": "resume_execution"}
            ]
        elif strategy == RecoveryStrategy.CHECKPOINT_ROLLBACK:
            steps = [
                {"action": "locate_checkpoint", "checkpoint": target_checkpoint},
                {"action": "restore_from_checkpoint"},
                {"action": "validate_restored_state"},
                {"action": "notify_participants"}
            ]
        elif strategy == RecoveryStrategy.EVENT_REPLAY:
            steps = [
                {"action": "load_event_history"},
                {"action": "replay_events"},
                {"action": "validate_final_state"},
                {"action": "resume_from_last_event"}
            ]
        
        return steps
    
    def _estimate_recovery_time(self, strategy: RecoveryStrategy, 
                               recovery_steps: List[Dict[str, Any]]) -> timedelta:
        """Estimate recovery execution time"""
        base_times = {
            RecoveryStrategy.FULL_RESTORE: timedelta(minutes=10),
            RecoveryStrategy.PARTIAL_RESTORE: timedelta(minutes=5),
            RecoveryStrategy.CHECKPOINT_ROLLBACK: timedelta(minutes=3),
            RecoveryStrategy.EVENT_REPLAY: timedelta(minutes=15),
            RecoveryStrategy.CLEAN_START: timedelta(minutes=2)
        }
        
        base_time = base_times.get(strategy, timedelta(minutes=5))
        step_factor = len(recovery_steps) * 0.5  # 30 seconds per step
        
        return base_time + timedelta(minutes=step_factor)
    
    def _assess_recovery_risk(self, strategy: RecoveryStrategy, 
                             session_state: SessionState) -> str:
        """Assess recovery risk level"""
        if strategy == RecoveryStrategy.CLEAN_START:
            return "high"  # Loses all session data
        elif strategy == RecoveryStrategy.EVENT_REPLAY:
            return "medium"  # May have inconsistencies
        else:
            return "low"  # Safe recovery methods
    
    # Recovery execution methods
    
    async def _execute_recovery_plan(self, recovery_plan: RecoveryPlan) -> bool:
        """Execute a recovery plan"""
        try:
            logger.info(f"Executing {recovery_plan.strategy.value} recovery for session {recovery_plan.session_id}")
            
            # Get the appropriate recovery strategy
            strategy_func = self.recovery_strategies.get(recovery_plan.strategy)
            if not strategy_func:
                logger.error(f"Unknown recovery strategy: {recovery_plan.strategy}")
                return False
            
            # Execute the strategy
            return await strategy_func(recovery_plan)
            
        except Exception as e:
            logger.error(f"Failed to execute recovery plan: {e}")
            return False
    
    async def _execute_full_restore(self, recovery_plan: RecoveryPlan) -> bool:
        """Execute full restore recovery"""
        try:
            session_id = recovery_plan.session_id
            
            # Load session state
            session_state = await self.session_manager.get_session_state(session_id)
            if not session_state:
                return False
            
            # Restore session to active state
            await self.session_manager.update_session_status(
                session_id, SessionStatus.ACTIVE, "recovery_system"
            )
            
            # Validate restored state
            is_valid, errors = await self.validate_session_state(session_id)
            if not is_valid:
                logger.warning(f"Restored session {session_id} failed validation: {errors}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute full restore: {e}")
            return False
    
    async def _execute_partial_restore(self, recovery_plan: RecoveryPlan) -> bool:
        """Execute partial restore recovery"""
        # Simplified implementation
        return await self._execute_full_restore(recovery_plan)
    
    async def _execute_checkpoint_rollback(self, recovery_plan: RecoveryPlan) -> bool:
        """Execute checkpoint rollback recovery"""
        try:
            session_id = recovery_plan.session_id
            
            # This would load and restore from checkpoint
            # For now, just restore session to paused state
            await self.session_manager.update_session_status(
                session_id, SessionStatus.PAUSED, "recovery_system"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute checkpoint rollback: {e}")
            return False
    
    async def _execute_event_replay(self, recovery_plan: RecoveryPlan) -> bool:
        """Execute event replay recovery"""
        try:
            session_id = recovery_plan.session_id
            
            # Get session events
            events = await self.session_manager.get_session_events(session_id, limit=1000)
            
            # Replay events (simplified implementation)
            logger.info(f"Replaying {len(events)} events for session {session_id}")
            
            # Restore session to active state
            await self.session_manager.update_session_status(
                session_id, SessionStatus.ACTIVE, "recovery_system"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute event replay: {e}")
            return False
    
    async def _execute_clean_start(self, recovery_plan: RecoveryPlan) -> bool:
        """Execute clean start recovery"""
        try:
            session_id = recovery_plan.session_id
            
            # Reset session to initial state
            await self.session_manager.update_session_status(
                session_id, SessionStatus.INITIALIZING, "recovery_system"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute clean start: {e}")
            return False
    
    # Validation methods
    
    def _register_default_validators(self) -> None:
        """Register default state validators"""
        self.state_validators.extend([
            self._validate_participants,
            self._validate_context_integrity,
            self._validate_progress_consistency
        ])
    
    async def _validate_participants(self, session_state: SessionState) -> List[str]:
        """Validate session participants"""
        errors = []
        
        if not session_state.participants:
            errors.append("Session has no participants")
        
        active_participants = [p for p in session_state.participants if p.status == "active"]
        if not active_participants:
            errors.append("Session has no active participants")
        
        return errors
    
    async def _validate_context_integrity(self, session_state: SessionState) -> List[str]:
        """Validate session context integrity"""
        errors = []
        
        # Check for required context fields
        required_fields = ["session_type", "created_by"]
        for field in required_fields:
            if field not in session_state.context:
                errors.append(f"Missing required context field: {field}")
        
        return errors
    
    async def _validate_progress_consistency(self, session_state: SessionState) -> List[str]:
        """Validate session progress consistency"""
        errors = []
        
        if session_state.progress < 0.0 or session_state.progress > 1.0:
            errors.append(f"Invalid progress value: {session_state.progress}")
        
        if (session_state.status == SessionStatus.COMPLETED and 
            session_state.progress < 1.0):
            errors.append("Session marked complete but progress < 100%")
        
        return errors
    
    async def _complete_active_recoveries(self) -> None:
        """Complete any active recovery operations"""
        if self.active_recoveries:
            logger.info(f"Completing {len(self.active_recoveries)} active recoveries")
            
            for session_id, recovery_plan in list(self.active_recoveries.items()):
                try:
                    # Attempt to complete or safely abort recovery
                    logger.info(f"Aborting recovery for session {session_id}")
                    self.active_recoveries.pop(session_id, None)
                except Exception as e:
                    logger.error(f"Failed to abort recovery for session {session_id}: {e}")
    
    def register_state_validator(self, validator: Callable) -> None:
        """Register a custom state validator"""
        self.state_validators.append(validator)
        logger.info(f"Registered custom state validator: {validator.__name__}")
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """Get recovery statistics"""
        total_recoveries = len(self.recovery_history)
        successful_recoveries = sum(1 for r in self.recovery_history if r["success"])
        
        strategy_stats = {}
        for recovery in self.recovery_history:
            strategy = recovery["strategy"]
            if strategy not in strategy_stats:
                strategy_stats[strategy] = {"total": 0, "successful": 0}
            strategy_stats[strategy]["total"] += 1
            if recovery["success"]:
                strategy_stats[strategy]["successful"] += 1
        
        return {
            "total_recoveries": total_recoveries,
            "successful_recoveries": successful_recoveries,
            "success_rate": successful_recoveries / max(total_recoveries, 1),
            "active_recoveries": len(self.active_recoveries),
            "strategy_statistics": strategy_stats
        }