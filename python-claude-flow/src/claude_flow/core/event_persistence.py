"""
Event Persistence System for Claude-Flow

This module provides persistent storage and replay capabilities for events,
including database storage, event journaling, and replay mechanisms.
"""

import asyncio
import json
import sqlite3
import aiosqlite
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import logging

from .event_bus import EnhancedEvent, EventFilter, EventPriority, EventStatus
from .interfaces import BaseComponent

logger = logging.getLogger(__name__)


class EventJournal:
    """
    Event journal for write-ahead logging of events
    
    Provides immediate persistence of events to disk before processing
    for disaster recovery and debugging purposes.
    """
    
    def __init__(self, journal_path: Union[str, Path] = "./data/event_journal.jsonl"):
        self.journal_path = Path(journal_path)
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        
    async def append_event(self, event: EnhancedEvent) -> bool:
        """Append event to journal file"""
        try:
            event_data = {
                "event_id": event.event_id,
                "type": event.type,
                "data": event.data,
                "priority": event.priority.name,
                "status": event.status.name,
                "source": event.source,
                "timestamp": event.timestamp.isoformat(),
                "correlation_id": event.correlation_id,
                "parent_event_id": event.parent_event_id,
                "retry_count": event.retry_count,
                "metadata": event.metadata
            }
            
            async with self._lock:
                with open(self.journal_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(event_data) + '\n')
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to append event to journal: {e}")
            return False
    
    async def read_events(self, from_timestamp: Optional[datetime] = None,
                         to_timestamp: Optional[datetime] = None,
                         limit: int = 1000) -> List[Dict[str, Any]]:
        """Read events from journal file"""
        events = []
        
        try:
            if not self.journal_path.exists():
                return events
            
            with open(self.journal_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if len(events) >= limit:
                        break
                    
                    try:
                        event_data = json.loads(line.strip())
                        event_timestamp = datetime.fromisoformat(event_data['timestamp'])
                        
                        # Apply time filters
                        if from_timestamp and event_timestamp < from_timestamp:
                            continue
                        if to_timestamp and event_timestamp > to_timestamp:
                            continue
                        
                        events.append(event_data)
                        
                    except (json.JSONDecodeError, ValueError) as e:
                        logger.warning(f"Invalid journal entry at line {line_num}: {e}")
                        continue
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to read events from journal: {e}")
            return []
    
    async def cleanup_old_events(self, retention_days: int = 30) -> int:
        """Remove old events from journal"""
        if not self.journal_path.exists():
            return 0
        
        cutoff_time = datetime.now() - timedelta(days=retention_days)
        kept_events = []
        removed_count = 0
        
        try:
            with open(self.journal_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        event_data = json.loads(line.strip())
                        event_timestamp = datetime.fromisoformat(event_data['timestamp'])
                        
                        if event_timestamp >= cutoff_time:
                            kept_events.append(line)
                        else:
                            removed_count += 1
                            
                    except (json.JSONDecodeError, ValueError):
                        # Keep invalid lines to avoid data loss
                        kept_events.append(line)
            
            # Rewrite journal with kept events
            async with self._lock:
                with open(self.journal_path, 'w', encoding='utf-8') as f:
                    f.writelines(kept_events)
            
            logger.info(f"Cleaned up {removed_count} old events from journal")
            return removed_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup journal: {e}")
            return 0


class EventDatabase:
    """
    SQLite database for persistent event storage
    
    Provides structured storage, indexing, and querying capabilities
    for events with full ACID properties.
    """
    
    def __init__(self, db_path: Union[str, Path] = "./data/events.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize database schema"""
        if self._initialized:
            return
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS events (
                        event_id TEXT PRIMARY KEY,
                        event_type TEXT NOT NULL,
                        priority INTEGER NOT NULL,
                        status INTEGER NOT NULL,
                        source TEXT,
                        correlation_id TEXT,
                        parent_event_id TEXT,
                        retry_count INTEGER DEFAULT 0,
                        max_retries INTEGER DEFAULT 3,
                        timestamp TEXT NOT NULL,
                        expires_at TEXT,
                        processing_started_at TEXT,
                        processing_completed_at TEXT,
                        error_message TEXT,
                        data TEXT NOT NULL,
                        metadata TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes for performance
                await db.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_events_status ON events(status)")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_events_source ON events(source)")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_events_correlation ON events(correlation_id)")
                
                await db.commit()
            
            self._initialized = True
            logger.info(f"Event database initialized: {self.db_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize event database: {e}")
            raise
    
    async def store_event(self, event: EnhancedEvent) -> bool:
        """Store event in database"""
        try:
            await self.initialize()
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO events (
                        event_id, event_type, priority, status, source,
                        correlation_id, parent_event_id, retry_count, max_retries,
                        timestamp, expires_at, processing_started_at, processing_completed_at,
                        error_message, data, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.event_id,
                    event.type,
                    event.priority.value,
                    event.status.value,
                    event.source,
                    event.correlation_id,
                    event.parent_event_id,
                    event.retry_count,
                    event.max_retries,
                    event.timestamp.isoformat(),
                    event.expires_at.isoformat() if event.expires_at else None,
                    event.processing_started_at.isoformat() if event.processing_started_at else None,
                    event.processing_completed_at.isoformat() if event.processing_completed_at else None,
                    event.error_message,
                    json.dumps(event.data),
                    json.dumps(event.metadata)
                ))
                
                await db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store event {event.event_id}: {e}")
            return False
    
    async def get_event(self, event_id: str) -> Optional[EnhancedEvent]:
        """Get event by ID"""
        try:
            await self.initialize()
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT * FROM events WHERE event_id = ?",
                    (event_id,)
                )
                row = await cursor.fetchone()
                
                if row:
                    return self._row_to_event(row)
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to get event {event_id}: {e}")
            return None
    
    async def query_events(self, filter: Optional[EventFilter] = None,
                          from_timestamp: Optional[datetime] = None,
                          to_timestamp: Optional[datetime] = None,
                          limit: int = 100) -> List[EnhancedEvent]:
        """Query events with filters"""
        try:
            await self.initialize()
            
            query = "SELECT * FROM events WHERE 1=1"
            params = []
            
            # Add time filters
            if from_timestamp:
                query += " AND timestamp >= ?"
                params.append(from_timestamp.isoformat())
            
            if to_timestamp:
                query += " AND timestamp <= ?"
                params.append(to_timestamp.isoformat())
            
            # Add event filter conditions
            if filter:
                if filter.event_types:
                    placeholders = ','.join('?' * len(filter.event_types))
                    query += f" AND event_type IN ({placeholders})"
                    params.extend(filter.event_types)
                
                if filter.sources:
                    placeholders = ','.join('?' * len(filter.sources))
                    query += f" AND source IN ({placeholders})"
                    params.extend(filter.sources)
                
                if filter.priority:
                    query += " AND priority = ?"
                    params.append(filter.priority.value)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(query, params)
                rows = await cursor.fetchall()
                
                events = []
                for row in rows:
                    event = self._row_to_event(row)
                    if event:
                        # Apply custom filters if specified
                        if filter and filter.custom_filters:
                            if not all(
                                key in event.data and event.data[key] == value
                                for key, value in filter.custom_filters.items()
                            ):
                                continue
                        
                        events.append(event)
                
                return events
                
        except Exception as e:
            logger.error(f"Failed to query events: {e}")
            return []
    
    async def update_event_status(self, event_id: str, status: EventStatus,
                                 error_message: Optional[str] = None) -> bool:
        """Update event status"""
        try:
            await self.initialize()
            
            async with aiosqlite.connect(self.db_path) as db:
                if status == EventStatus.PROCESSING:
                    await db.execute("""
                        UPDATE events 
                        SET status = ?, processing_started_at = CURRENT_TIMESTAMP
                        WHERE event_id = ?
                    """, (status.value, event_id))
                elif status in [EventStatus.COMPLETED, EventStatus.FAILED]:
                    await db.execute("""
                        UPDATE events 
                        SET status = ?, processing_completed_at = CURRENT_TIMESTAMP, error_message = ?
                        WHERE event_id = ?
                    """, (status.value, error_message, event_id))
                else:
                    await db.execute("""
                        UPDATE events 
                        SET status = ?, error_message = ?
                        WHERE event_id = ?
                    """, (status.value, error_message, event_id))
                
                await db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update event status {event_id}: {e}")
            return False
    
    async def cleanup_old_events(self, retention_days: int = 30) -> int:
        """Remove old events from database"""
        try:
            await self.initialize()
            
            cutoff_time = datetime.now() - timedelta(days=retention_days)
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM events WHERE timestamp < ?",
                    (cutoff_time.isoformat(),)
                )
                await db.commit()
                
                removed_count = cursor.rowcount
                logger.info(f"Cleaned up {removed_count} old events from database")
                return removed_count
                
        except Exception as e:
            logger.error(f"Failed to cleanup old events: {e}")
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            await self.initialize()
            
            async with aiosqlite.connect(self.db_path) as db:
                # Total events
                cursor = await db.execute("SELECT COUNT(*) FROM events")
                total_events = (await cursor.fetchone())[0]
                
                # Events by status
                cursor = await db.execute("""
                    SELECT status, COUNT(*) FROM events GROUP BY status
                """)
                status_counts = {row[0]: row[1] for row in await cursor.fetchall()}
                
                # Events by type
                cursor = await db.execute("""
                    SELECT event_type, COUNT(*) FROM events GROUP BY event_type
                """)
                type_counts = dict(await cursor.fetchall())
                
                # Recent activity (last 24 hours)
                cutoff_time = datetime.now() - timedelta(hours=24)
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM events WHERE timestamp >= ?",
                    (cutoff_time.isoformat(),)
                )
                recent_events = (await cursor.fetchone())[0]
                
                return {
                    "total_events": total_events,
                    "status_counts": status_counts,
                    "type_counts": type_counts,
                    "recent_events_24h": recent_events
                }
                
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}
    
    def _row_to_event(self, row) -> Optional[EnhancedEvent]:
        """Convert database row to EnhancedEvent"""
        try:
            return EnhancedEvent(
                event_id=row[0],
                type=row[1],
                priority=EventPriority(row[2]),
                status=EventStatus(row[3]),
                source=row[4],
                correlation_id=row[5],
                parent_event_id=row[6],
                retry_count=row[7],
                max_retries=row[8],
                timestamp=datetime.fromisoformat(row[9]),
                expires_at=datetime.fromisoformat(row[10]) if row[10] else None,
                processing_started_at=datetime.fromisoformat(row[11]) if row[11] else None,
                processing_completed_at=datetime.fromisoformat(row[12]) if row[12] else None,
                error_message=row[13],
                data=json.loads(row[14]),
                metadata=json.loads(row[15]) if row[15] else {}
            )
        except Exception as e:
            logger.error(f"Failed to convert row to event: {e}")
            return None


class EventPersistenceManager(BaseComponent):
    """
    Event persistence manager coordinating journal and database storage
    
    Provides unified interface for event persistence with both
    immediate journaling and structured database storage.
    """
    
    def __init__(self, journal_path: Optional[str] = None, 
                 db_path: Optional[str] = None,
                 enable_journal: bool = True,
                 enable_database: bool = True):
        super().__init__()
        self.enable_journal = enable_journal
        self.enable_database = enable_database
        
        if enable_journal:
            self.journal = EventJournal(journal_path) if journal_path else EventJournal()
        
        if enable_database:
            self.database = EventDatabase(db_path) if db_path else EventDatabase()
        
        self._cleanup_interval = 3600  # 1 hour
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def _start_implementation(self) -> None:
        """Start the persistence manager"""
        if self.enable_database:
            await self.database.initialize()
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        
        logger.info("Event persistence manager started")
    
    async def _stop_implementation(self) -> None:
        """Stop the persistence manager"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Event persistence manager stopped")
    
    async def _health_check_implementation(self) -> Dict[str, Any]:
        """Health check implementation"""
        health = {
            "journal_enabled": self.enable_journal,
            "database_enabled": self.enable_database
        }
        
        if self.enable_journal:
            health["journal_exists"] = self.journal.journal_path.exists()
        
        if self.enable_database:
            health["database_exists"] = self.database.db_path.exists()
            try:
                stats = await self.database.get_stats()
                health["database_stats"] = stats
            except Exception:
                health["database_error"] = True
        
        return health
    
    async def persist_event(self, event: EnhancedEvent) -> bool:
        """Persist event to configured storages"""
        success = True
        
        # Write to journal first for immediate persistence
        if self.enable_journal:
            journal_success = await self.journal.append_event(event)
            if not journal_success:
                logger.error(f"Failed to journal event: {event.event_id}")
                success = False
        
        # Store in database for structured queries
        if self.enable_database:
            db_success = await self.database.store_event(event)
            if not db_success:
                logger.error(f"Failed to store event in database: {event.event_id}")
                success = False
        
        return success
    
    async def get_event(self, event_id: str) -> Optional[EnhancedEvent]:
        """Get event by ID (database preferred, fallback to journal)"""
        if self.enable_database:
            event = await self.database.get_event(event_id)
            if event:
                return event
        
        # Fallback to journal search (less efficient)
        if self.enable_journal:
            events = await self.journal.read_events(limit=10000)
            for event_data in events:
                if event_data.get('event_id') == event_id:
                    return self._dict_to_event(event_data)
        
        return None
    
    async def query_events(self, filter: Optional[EventFilter] = None,
                          from_timestamp: Optional[datetime] = None,
                          to_timestamp: Optional[datetime] = None,
                          limit: int = 100) -> List[EnhancedEvent]:
        """Query events with filters"""
        if self.enable_database:
            return await self.database.query_events(filter, from_timestamp, to_timestamp, limit)
        
        # Fallback to journal
        if self.enable_journal:
            events_data = await self.journal.read_events(from_timestamp, to_timestamp, limit)
            events = []
            
            for event_data in events_data:
                event = self._dict_to_event(event_data)
                if event and (filter is None or filter.matches(event)):
                    events.append(event)
                    if len(events) >= limit:
                        break
            
            return events
        
        return []
    
    async def update_event_status(self, event_id: str, status: EventStatus,
                                 error_message: Optional[str] = None) -> bool:
        """Update event status"""
        if self.enable_database:
            return await self.database.update_event_status(event_id, status, error_message)
        
        return False  # Journal is append-only
    
    async def cleanup_old_events(self, retention_days: int = 30) -> Dict[str, int]:
        """Cleanup old events from all storages"""
        results = {}
        
        if self.enable_journal:
            journal_removed = await self.journal.cleanup_old_events(retention_days)
            results["journal_removed"] = journal_removed
        
        if self.enable_database:
            db_removed = await self.database.cleanup_old_events(retention_days)
            results["database_removed"] = db_removed
        
        return results
    
    async def _periodic_cleanup(self) -> None:
        """Periodic cleanup task"""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self.cleanup_old_events()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup task error: {e}")
    
    def _dict_to_event(self, event_data: Dict[str, Any]) -> Optional[EnhancedEvent]:
        """Convert dictionary to EnhancedEvent"""
        try:
            return EnhancedEvent(
                event_id=event_data['event_id'],
                type=event_data['type'],
                data=event_data['data'],
                priority=EventPriority[event_data['priority']],
                status=EventStatus[event_data['status']],
                source=event_data['source'],
                timestamp=datetime.fromisoformat(event_data['timestamp']),
                correlation_id=event_data.get('correlation_id'),
                parent_event_id=event_data.get('parent_event_id'),
                retry_count=event_data.get('retry_count', 0),
                metadata=event_data.get('metadata', {})
            )
        except Exception as e:
            logger.error(f"Failed to convert dict to event: {e}")
            return None


# Global persistence manager instance
_persistence_manager: Optional[EventPersistenceManager] = None


def get_persistence_manager() -> EventPersistenceManager:
    """Get the global persistence manager instance"""
    global _persistence_manager
    if _persistence_manager is None:
        _persistence_manager = EventPersistenceManager()
    return _persistence_manager


async def persist_event(event: EnhancedEvent) -> bool:
    """Persist event using global persistence manager"""
    return await get_persistence_manager().persist_event(event)


async def get_persisted_event(event_id: str) -> Optional[EnhancedEvent]:
    """Get persisted event by ID"""
    return await get_persistence_manager().get_event(event_id)


async def query_persisted_events(**kwargs) -> List[EnhancedEvent]:
    """Query persisted events"""
    return await get_persistence_manager().query_events(**kwargs)