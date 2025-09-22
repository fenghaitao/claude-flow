"""
Persistent Session Management for Claude-Flow

This module provides comprehensive session management with SQLite backend,
including session creation, persistence, state tracking, and recovery mechanisms.
"""

import asyncio
import logging
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Union
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
import uuid
import pickle
import aiosqlite

from ..core.interfaces import BaseComponent, Status
from ..core.event_bus import publish_event, subscribe_to_events, EventFilter, EventPriority

logger = logging.getLogger(__name__)


class SessionStatus(Enum):
    """Session status types"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class SessionType(Enum):
    """Session types"""
    AGENT_COLLABORATION = "agent_collaboration"
    TASK_EXECUTION = "task_execution"
    SWARM_COORDINATION = "swarm_coordination"
    WORKFLOW_PROCESSING = "workflow_processing"
    RESEARCH_SESSION = "research_session"
    DEVELOPMENT_SESSION = "development_session"


@dataclass
class SessionParticipant:
    """Session participant information"""
    participant_id: str
    participant_type: str  # agent, user, system
    role: str
    joined_at: datetime
    last_active: datetime
    status: str = "active"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionState:
    """Session state snapshot"""
    session_id: str
    status: SessionStatus
    participants: List[SessionParticipant]
    context: Dict[str, Any]
    progress: float
    last_checkpoint: Optional[datetime]
    current_phase: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionEvent:
    """Session event record"""
    event_id: str
    session_id: str
    participant_id: str
    event_type: str
    timestamp: datetime
    data: Dict[str, Any]
    sequence_number: int


class SessionManager(BaseComponent):
    """
    Session Manager with SQLite persistence
    
    Provides comprehensive session management including:
    - Session creation and lifecycle management
    - Persistent state storage with SQLite
    - Session recovery and restoration
    - Event tracking and replay
    - Participant management
    - State checkpointing
    """
    
    def __init__(self, database_path: Optional[str] = None):
        super().__init__()
        
        # Database configuration
        self.database_path = database_path or "sessions.db"
        self.db_pool_size = 10
        
        # Session registry
        self.active_sessions: Dict[str, SessionState] = {}
        self.session_locks: Dict[str, asyncio.Lock] = {}
        
        # Configuration
        self.checkpoint_interval = 300  # 5 minutes
        self.max_session_duration = timedelta(hours=24)
        self.cleanup_interval = 3600  # 1 hour
        self.max_events_per_session = 10000
        
        # Background tasks
        self.background_tasks: Set[asyncio.Task] = set()
        
        # Event sequence tracking
        self.session_sequences: Dict[str, int] = {}
    
    async def _start_implementation(self) -> None:
        """Start the session manager"""
        # Initialize database
        await self._initialize_database()
        
        # Load active sessions from database
        await self._load_active_sessions()
        
        # Setup event subscriptions
        await self._setup_event_subscriptions()
        
        # Start background tasks
        self.background_tasks.add(asyncio.create_task(self._checkpoint_loop()))
        self.background_tasks.add(asyncio.create_task(self._cleanup_loop()))
        
        logger.info(f"Session Manager started with database: {self.database_path}")
    
    async def _stop_implementation(self) -> None:
        """Stop the session manager"""
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        # Save all active sessions
        await self._save_all_sessions()
        
        logger.info("Session Manager stopped")
    
    async def _health_check_implementation(self) -> Dict[str, Any]:
        """Health check for session manager"""
        try:
            # Check database connectivity
            async with aiosqlite.connect(self.database_path) as db:
                await db.execute("SELECT 1")
            
            db_healthy = True
        except Exception:
            db_healthy = False
        
        return {
            "database_healthy": db_healthy,
            "active_sessions": len(self.active_sessions),
            "background_tasks": len(self.background_tasks),
            "database_path": self.database_path
        }
    
    async def create_session(self, session_type: SessionType, initiator_id: str, 
                           context: Optional[Dict[str, Any]] = None, 
                           metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new session"""
        try:
            session_id = str(uuid.uuid4())
            current_time = datetime.now()
            
            # Create initial participant
            initiator = SessionParticipant(
                participant_id=initiator_id,
                participant_type="agent",  # Default to agent, can be overridden
                role="initiator",
                joined_at=current_time,
                last_active=current_time
            )
            
            # Create session state
            session_state = SessionState(
                session_id=session_id,
                status=SessionStatus.INITIALIZING,
                participants=[initiator],
                context=context or {},
                progress=0.0,
                last_checkpoint=None,
                current_phase="initialization",
                metadata=metadata or {}
            )
            
            # Store in memory
            self.active_sessions[session_id] = session_state
            self.session_locks[session_id] = asyncio.Lock()
            self.session_sequences[session_id] = 0
            
            # Persist to database
            await self._save_session(session_state)
            
            # Record creation event
            await self._record_session_event(
                session_id=session_id,
                participant_id=initiator_id,
                event_type="session_created",
                data={
                    "session_type": session_type.value,
                    "initiator_id": initiator_id,
                    "context": context,
                    "metadata": metadata
                }
            )
            
            # Emit session created event
            await publish_event(
                "session.created",
                {
                    "session_id": session_id,
                    "session_type": session_type.value,
                    "initiator_id": initiator_id
                },
                priority=EventPriority.NORMAL,
                source=f"session:{self.id}"
            )
            
            logger.info(f"Created session {session_id} of type {session_type.value}")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise
    
    async def join_session(self, session_id: str, participant_id: str, 
                          participant_type: str = "agent", role: str = "participant") -> bool:
        """Add a participant to a session"""
        try:
            if session_id not in self.active_sessions:
                # Try to load from database
                await self._load_session(session_id)
            
            if session_id not in self.active_sessions:
                logger.warning(f"Session {session_id} not found")
                return False
            
            async with self.session_locks[session_id]:
                session_state = self.active_sessions[session_id]
                
                # Check if participant already exists
                for participant in session_state.participants:
                    if participant.participant_id == participant_id:
                        participant.last_active = datetime.now()
                        participant.status = "active"
                        await self._save_session(session_state)
                        return True
                
                # Add new participant
                participant = SessionParticipant(
                    participant_id=participant_id,
                    participant_type=participant_type,
                    role=role,
                    joined_at=datetime.now(),
                    last_active=datetime.now()
                )
                
                session_state.participants.append(participant)
                await self._save_session(session_state)
                
                # Record join event
                await self._record_session_event(
                    session_id=session_id,
                    participant_id=participant_id,
                    event_type="participant_joined",
                    data={
                        "participant_type": participant_type,
                        "role": role
                    }
                )
            
            logger.info(f"Participant {participant_id} joined session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to join session {session_id}: {e}")
            return False
    
    async def leave_session(self, session_id: str, participant_id: str) -> bool:
        """Remove a participant from a session"""
        try:
            if session_id not in self.active_sessions:
                return False
            
            async with self.session_locks[session_id]:
                session_state = self.active_sessions[session_id]
                
                # Find and update participant
                for participant in session_state.participants:
                    if participant.participant_id == participant_id:
                        participant.status = "left"
                        participant.last_active = datetime.now()
                        break
                
                await self._save_session(session_state)
                
                # Record leave event
                await self._record_session_event(
                    session_id=session_id,
                    participant_id=participant_id,
                    event_type="participant_left",
                    data={}
                )
            
            logger.info(f"Participant {participant_id} left session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to leave session {session_id}: {e}")
            return False
    
    async def update_session_status(self, session_id: str, status: SessionStatus, 
                                  participant_id: Optional[str] = None) -> bool:
        """Update session status"""
        try:
            if session_id not in self.active_sessions:
                await self._load_session(session_id)
            
            if session_id not in self.active_sessions:
                return False
            
            async with self.session_locks[session_id]:
                session_state = self.active_sessions[session_id]
                old_status = session_state.status
                session_state.status = status
                
                await self._save_session(session_state)
                
                # Record status change event
                await self._record_session_event(
                    session_id=session_id,
                    participant_id=participant_id or "system",
                    event_type="status_changed",
                    data={
                        "old_status": old_status.value,
                        "new_status": status.value
                    }
                )
            
            # Emit status change event
            await publish_event(
                "session.status_changed",
                {
                    "session_id": session_id,
                    "old_status": old_status.value,
                    "new_status": status.value
                },
                priority=EventPriority.NORMAL,
                source=f"session:{self.id}"
            )
            
            logger.info(f"Session {session_id} status changed from {old_status.value} to {status.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update session status {session_id}: {e}")
            return False
    
    async def update_session_context(self, session_id: str, context_updates: Dict[str, Any], 
                                   participant_id: str) -> bool:
        """Update session context"""
        try:
            if session_id not in self.active_sessions:
                await self._load_session(session_id)
            
            if session_id not in self.active_sessions:
                return False
            
            async with self.session_locks[session_id]:
                session_state = self.active_sessions[session_id]
                
                # Update context
                session_state.context.update(context_updates)
                
                # Update participant's last active time
                for participant in session_state.participants:
                    if participant.participant_id == participant_id:
                        participant.last_active = datetime.now()
                        break
                
                await self._save_session(session_state)
                
                # Record context update event
                await self._record_session_event(
                    session_id=session_id,
                    participant_id=participant_id,
                    event_type="context_updated",
                    data={"updates": context_updates}
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update session context {session_id}: {e}")
            return False
    
    async def create_checkpoint(self, session_id: str, participant_id: str, 
                              checkpoint_data: Optional[Dict[str, Any]] = None) -> bool:
        """Create a session checkpoint"""
        try:
            if session_id not in self.active_sessions:
                await self._load_session(session_id)
            
            if session_id not in self.active_sessions:
                return False
            
            async with self.session_locks[session_id]:
                session_state = self.active_sessions[session_id]
                checkpoint_time = datetime.now()
                
                # Update checkpoint time
                session_state.last_checkpoint = checkpoint_time
                
                await self._save_session(session_state)
                
                # Save checkpoint data separately
                if checkpoint_data:
                    await self._save_checkpoint(session_id, checkpoint_time, checkpoint_data)
                
                # Record checkpoint event
                await self._record_session_event(
                    session_id=session_id,
                    participant_id=participant_id,
                    event_type="checkpoint_created",
                    data={"checkpoint_time": checkpoint_time.isoformat()}
                )
            
            logger.info(f"Created checkpoint for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create checkpoint for session {session_id}: {e}")
            return False
    
    async def get_session_state(self, session_id: str) -> Optional[SessionState]:
        """Get current session state"""
        try:
            if session_id not in self.active_sessions:
                await self._load_session(session_id)
            
            return self.active_sessions.get(session_id)
            
        except Exception as e:
            logger.error(f"Failed to get session state {session_id}: {e}")
            return None
    
    async def get_session_events(self, session_id: str, limit: int = 100, 
                                offset: int = 0) -> List[SessionEvent]:
        """Get session events"""
        try:
            async with aiosqlite.connect(self.database_path) as db:
                cursor = await db.execute("""
                    SELECT event_id, session_id, participant_id, event_type, 
                           timestamp, data, sequence_number
                    FROM session_events 
                    WHERE session_id = ? 
                    ORDER BY sequence_number DESC 
                    LIMIT ? OFFSET ?
                """, (session_id, limit, offset))
                
                rows = await cursor.fetchall()
                events = []
                
                for row in rows:
                    events.append(SessionEvent(
                        event_id=row[0],
                        session_id=row[1],
                        participant_id=row[2],
                        event_type=row[3],
                        timestamp=datetime.fromisoformat(row[4]),
                        data=json.loads(row[5]),
                        sequence_number=row[6]
                    ))
                
                return events
            
        except Exception as e:
            logger.error(f"Failed to get session events {session_id}: {e}")
            return []
    
    async def list_sessions(self, status_filter: Optional[SessionStatus] = None, 
                           limit: int = 50) -> List[Dict[str, Any]]:
        """List sessions with optional status filter"""
        try:
            query = """
                SELECT session_id, status, created_at, updated_at, context, metadata
                FROM sessions
            """
            params = []
            
            if status_filter:
                query += " WHERE status = ?"
                params.append(status_filter.value)
            
            query += " ORDER BY updated_at DESC LIMIT ?"
            params.append(limit)
            
            async with aiosqlite.connect(self.database_path) as db:
                cursor = await db.execute(query, params)
                rows = await cursor.fetchall()
                
                sessions = []
                for row in rows:
                    sessions.append({
                        "session_id": row[0],
                        "status": row[1],
                        "created_at": row[2],
                        "updated_at": row[3],
                        "context": json.loads(row[4]) if row[4] else {},
                        "metadata": json.loads(row[5]) if row[5] else {}
                    })
                
                return sessions
            
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []
    
    # Private methods
    
    async def _initialize_database(self) -> None:
        """Initialize SQLite database schema"""
        try:
            async with aiosqlite.connect(self.database_path) as db:
                # Sessions table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        status TEXT NOT NULL,
                        participants TEXT NOT NULL,
                        context TEXT,
                        progress REAL DEFAULT 0.0,
                        last_checkpoint TEXT,
                        current_phase TEXT,
                        metadata TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                
                # Session events table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS session_events (
                        event_id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        participant_id TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        data TEXT NOT NULL,
                        sequence_number INTEGER NOT NULL,
                        FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                    )
                """)
                
                # Session checkpoints table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS session_checkpoints (
                        checkpoint_id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        checkpoint_time TEXT NOT NULL,
                        checkpoint_data BLOB,
                        FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                    )
                """)
                
                # Create indexes
                await db.execute("CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at)")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_events_session ON session_events(session_id)")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_events_sequence ON session_events(session_id, sequence_number)")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_checkpoints_session ON session_checkpoints(session_id)")
                
                await db.commit()
            
            logger.info("Database schema initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def _save_session(self, session_state: SessionState) -> None:
        """Save session state to database"""
        try:
            current_time = datetime.now().isoformat()
            
            async with aiosqlite.connect(self.database_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO sessions 
                    (session_id, status, participants, context, progress, 
                     last_checkpoint, current_phase, metadata, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 
                            COALESCE((SELECT created_at FROM sessions WHERE session_id = ?), ?), ?)
                """, (
                    session_state.session_id,
                    session_state.status.value,
                    json.dumps([p.__dict__ for p in session_state.participants], default=str),
                    json.dumps(session_state.context),
                    session_state.progress,
                    session_state.last_checkpoint.isoformat() if session_state.last_checkpoint else None,
                    session_state.current_phase,
                    json.dumps(session_state.metadata),
                    session_state.session_id,
                    current_time,
                    current_time
                ))
                
                await db.commit()
            
        except Exception as e:
            logger.error(f"Failed to save session {session_state.session_id}: {e}")
            raise
    
    async def _load_session(self, session_id: str) -> bool:
        """Load session from database"""
        try:
            async with aiosqlite.connect(self.database_path) as db:
                cursor = await db.execute("""
                    SELECT session_id, status, participants, context, progress, 
                           last_checkpoint, current_phase, metadata
                    FROM sessions WHERE session_id = ?
                """, (session_id,))
                
                row = await cursor.fetchone()
                if not row:
                    return False
                
                # Parse participants
                participants_data = json.loads(row[2])
                participants = []
                for p_data in participants_data:
                    participants.append(SessionParticipant(
                        participant_id=p_data["participant_id"],
                        participant_type=p_data["participant_type"],
                        role=p_data["role"],
                        joined_at=datetime.fromisoformat(p_data["joined_at"]),
                        last_active=datetime.fromisoformat(p_data["last_active"]),
                        status=p_data.get("status", "active"),
                        metadata=p_data.get("metadata", {})
                    ))
                
                # Create session state
                session_state = SessionState(
                    session_id=row[0],
                    status=SessionStatus(row[1]),
                    participants=participants,
                    context=json.loads(row[3]) if row[3] else {},
                    progress=row[4],
                    last_checkpoint=datetime.fromisoformat(row[5]) if row[5] else None,
                    current_phase=row[6],
                    metadata=json.loads(row[7]) if row[7] else {}
                )
                
                # Store in memory
                self.active_sessions[session_id] = session_state
                if session_id not in self.session_locks:
                    self.session_locks[session_id] = asyncio.Lock()
                
                return True
            
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return False
    
    async def _load_active_sessions(self) -> None:
        """Load all active sessions from database"""
        try:
            active_statuses = [SessionStatus.ACTIVE.value, SessionStatus.PAUSED.value]
            
            async with aiosqlite.connect(self.database_path) as db:
                cursor = await db.execute("""
                    SELECT session_id FROM sessions 
                    WHERE status IN ({})
                """.format(','.join(['?'] * len(active_statuses))), active_statuses)
                
                rows = await cursor.fetchall()
                
                for row in rows:
                    session_id = row[0]
                    await self._load_session(session_id)
            
            logger.info(f"Loaded {len(self.active_sessions)} active sessions")
            
        except Exception as e:
            logger.error(f"Failed to load active sessions: {e}")
    
    async def _record_session_event(self, session_id: str, participant_id: str, 
                                   event_type: str, data: Dict[str, Any]) -> None:
        """Record a session event"""
        try:
            event_id = str(uuid.uuid4())
            timestamp = datetime.now()
            sequence_number = self.session_sequences.get(session_id, 0) + 1
            self.session_sequences[session_id] = sequence_number
            
            async with aiosqlite.connect(self.database_path) as db:
                await db.execute("""
                    INSERT INTO session_events 
                    (event_id, session_id, participant_id, event_type, timestamp, data, sequence_number)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    event_id,
                    session_id,
                    participant_id,
                    event_type,
                    timestamp.isoformat(),
                    json.dumps(data),
                    sequence_number
                ))
                
                await db.commit()
            
        except Exception as e:
            logger.error(f"Failed to record session event: {e}")
    
    async def _save_checkpoint(self, session_id: str, checkpoint_time: datetime, 
                             checkpoint_data: Dict[str, Any]) -> None:
        """Save checkpoint data"""
        try:
            checkpoint_id = str(uuid.uuid4())
            
            async with aiosqlite.connect(self.database_path) as db:
                await db.execute("""
                    INSERT INTO session_checkpoints 
                    (checkpoint_id, session_id, checkpoint_time, checkpoint_data)
                    VALUES (?, ?, ?, ?)
                """, (
                    checkpoint_id,
                    session_id,
                    checkpoint_time.isoformat(),
                    pickle.dumps(checkpoint_data)
                ))
                
                await db.commit()
            
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
    
    async def _checkpoint_loop(self) -> None:
        """Background checkpoint creation loop"""
        while self.status == Status.RUNNING:
            try:
                # Create checkpoints for active sessions
                for session_id, session_state in list(self.active_sessions.items()):
                    if session_state.status == SessionStatus.ACTIVE:
                        last_checkpoint = session_state.last_checkpoint
                        if (not last_checkpoint or 
                            (datetime.now() - last_checkpoint).seconds > self.checkpoint_interval):
                            
                            await self.create_checkpoint(session_id, "system", {"auto_checkpoint": True})
                
                await asyncio.sleep(self.checkpoint_interval)
                
            except Exception as e:
                logger.error(f"Checkpoint loop error: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup loop"""
        while self.status == Status.RUNNING:
            try:
                await self._cleanup_old_sessions()
                await asyncio.sleep(self.cleanup_interval)
                
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(300)
    
    async def _cleanup_old_sessions(self) -> None:
        """Clean up old and inactive sessions"""
        try:
            cutoff_time = datetime.now() - self.max_session_duration
            
            # Archive old completed sessions
            async with aiosqlite.connect(self.database_path) as db:
                await db.execute("""
                    UPDATE sessions 
                    SET status = ? 
                    WHERE status IN (?, ?) AND updated_at < ?
                """, (
                    SessionStatus.ARCHIVED.value,
                    SessionStatus.COMPLETED.value,
                    SessionStatus.FAILED.value,
                    cutoff_time.isoformat()
                ))
                
                await db.commit()
            
            # Remove archived sessions from memory
            to_remove = []
            for session_id, session_state in self.active_sessions.items():
                if session_state.status == SessionStatus.ARCHIVED:
                    to_remove.append(session_id)
            
            for session_id in to_remove:
                self.active_sessions.pop(session_id, None)
                self.session_locks.pop(session_id, None)
                self.session_sequences.pop(session_id, None)
            
            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} archived sessions")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old sessions: {e}")
    
    async def _save_all_sessions(self) -> None:
        """Save all active sessions to database"""
        try:
            for session_state in self.active_sessions.values():
                await self._save_session(session_state)
            
            logger.info(f"Saved {len(self.active_sessions)} active sessions")
            
        except Exception as e:
            logger.error(f"Failed to save all sessions: {e}")
    
    async def _setup_event_subscriptions(self) -> None:
        """Setup event subscriptions for session management"""
        # Subscribe to agent and task events
        event_filter = EventFilter(
            event_types=["agent.task_completed", "agent.task_failed", "agent.status_changed"],
            sources=["agent:*"]
        )
        
        await subscribe_to_events(event_filter, self._handle_agent_event)
    
    async def _handle_agent_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Handle agent-related events for session tracking"""
        try:
            agent_id = data.get("agent_id")
            if not agent_id:
                return
            
            # Find sessions with this agent as participant
            for session_id, session_state in self.active_sessions.items():
                for participant in session_state.participants:
                    if participant.participant_id == agent_id:
                        # Record agent event in session
                        await self._record_session_event(
                            session_id=session_id,
                            participant_id=agent_id,
                            event_type=f"agent.{event_type.split('.', 1)[1]}",
                            data=data
                        )
                        break
        
        except Exception as e:
            logger.error(f"Failed to handle agent event {event_type}: {e}")