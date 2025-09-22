"""
Agent Lifecycle Management and Fault Tolerance for Claude-Flow

This module provides comprehensive lifecycle management for agents including
startup, shutdown, health monitoring, fault detection, and recovery mechanisms.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from enum import Enum
from dataclasses import dataclass
import traceback

from ..interfaces import AgentConfig, AgentType
from ...core.interfaces import BaseComponent, Status
from ...core.event_bus import publish_event, subscribe_to_events, EventFilter, EventPriority

logger = logging.getLogger(__name__)


class AgentHealthStatus(Enum):
    """Agent health status types"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class FaultType(Enum):
    """Types of faults that can occur"""
    TASK_FAILURE = "task_failure"
    TIMEOUT = "timeout"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    COMMUNICATION_FAILURE = "communication_failure"
    CONFIGURATION_ERROR = "configuration_error"
    DEPENDENCY_FAILURE = "dependency_failure"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class AgentHealthMetrics:
    """Health metrics for an agent"""
    agent_id: str
    status: AgentHealthStatus
    last_heartbeat: datetime
    response_time: float
    error_rate: float
    task_success_rate: float
    resource_utilization: Dict[str, float]
    uptime: timedelta
    restart_count: int
    last_error: Optional[str] = None


@dataclass
class FaultEvent:
    """Fault event information"""
    agent_id: str
    fault_type: FaultType
    severity: str
    timestamp: datetime
    description: str
    context: Dict[str, Any]
    resolved: bool = False
    resolution_time: Optional[datetime] = None


class AgentLifecycleManager(BaseComponent):
    """
    Agent Lifecycle Manager
    
    Manages the complete lifecycle of agents including:
    - Agent registration and startup
    - Health monitoring and heartbeat tracking
    - Fault detection and recovery
    - Graceful shutdown and cleanup
    - Performance monitoring
    """
    
    def __init__(self):
        super().__init__()
        
        # Agent registry and state tracking
        self.managed_agents: Dict[str, Dict[str, Any]] = {}
        self.agent_health: Dict[str, AgentHealthMetrics] = {}
        self.fault_history: List[FaultEvent] = []
        
        # Lifecycle configuration
        self.heartbeat_interval = 30  # seconds
        self.health_check_interval = 60  # seconds
        self.fault_threshold = 3  # consecutive failures before marking unhealthy
        self.restart_delay = 5  # seconds before restart attempt
        self.max_restart_attempts = 3
        
        # Monitoring tasks
        self.monitoring_tasks: Set[asyncio.Task] = set()
        
        # Fault tolerance policies
        self.fault_policies = {
            FaultType.TASK_FAILURE: {"auto_restart": False, "escalate_after": 5},
            FaultType.TIMEOUT: {"auto_restart": True, "escalate_after": 3},
            FaultType.RESOURCE_EXHAUSTION: {"auto_restart": True, "escalate_after": 2},
            FaultType.COMMUNICATION_FAILURE: {"auto_restart": True, "escalate_after": 3},
            FaultType.CONFIGURATION_ERROR: {"auto_restart": False, "escalate_after": 1},
            FaultType.DEPENDENCY_FAILURE: {"auto_restart": True, "escalate_after": 2}
        }
        
        # Recovery strategies
        self.recovery_strategies = {
            "restart_agent": self._restart_agent,
            "reallocate_tasks": self._reallocate_agent_tasks,
            "reduce_load": self._reduce_agent_load,
            "escalate_to_human": self._escalate_to_human
        }
    
    async def _start_implementation(self) -> None:
        """Start the lifecycle manager"""
        # Subscribe to agent events
        await self._setup_event_subscriptions()
        
        # Start monitoring tasks
        self.monitoring_tasks.add(asyncio.create_task(self._health_monitoring_loop()))
        self.monitoring_tasks.add(asyncio.create_task(self._fault_detection_loop()))
        
        logger.info("Agent Lifecycle Manager started")
    
    async def _stop_implementation(self) -> None:
        """Stop the lifecycle manager"""
        # Cancel monitoring tasks
        for task in self.monitoring_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.monitoring_tasks:
            await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)
        
        # Perform graceful shutdown of all managed agents
        await self._shutdown_all_agents()
        
        logger.info("Agent Lifecycle Manager stopped")
    
    async def _health_check_implementation(self) -> Dict[str, Any]:
        """Health check for lifecycle manager"""
        healthy_agents = sum(1 for metrics in self.agent_health.values() 
                           if metrics.status == AgentHealthStatus.HEALTHY)
        total_agents = len(self.managed_agents)
        
        return {
            "managed_agents": total_agents,
            "healthy_agents": healthy_agents,
            "unhealthy_agents": total_agents - healthy_agents,
            "active_faults": len([f for f in self.fault_history if not f.resolved]),
            "monitoring_tasks": len(self.monitoring_tasks)
        }
    
    async def register_agent(self, agent_id: str, agent_config: AgentConfig, agent_instance: Any) -> bool:
        """Register an agent for lifecycle management"""
        try:
            # Register agent
            self.managed_agents[agent_id] = {
                "config": agent_config,
                "instance": agent_instance,
                "registration_time": datetime.now(),
                "start_time": None,
                "restart_count": 0,
                "last_heartbeat": datetime.now(),
                "status": Status.STOPPED
            }
            
            # Initialize health metrics
            self.agent_health[agent_id] = AgentHealthMetrics(
                agent_id=agent_id,
                status=AgentHealthStatus.UNKNOWN,
                last_heartbeat=datetime.now(),
                response_time=0.0,
                error_rate=0.0,
                task_success_rate=1.0,
                resource_utilization={},
                uptime=timedelta(0),
                restart_count=0
            )
            
            # Start the agent
            await self._start_agent(agent_id)
            
            logger.info(f"Registered and started agent {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register agent {agent_id}: {e}")
            return False
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent from lifecycle management"""
        try:
            if agent_id in self.managed_agents:
                # Stop the agent gracefully
                await self._stop_agent(agent_id)
                
                # Clean up records
                del self.managed_agents[agent_id]
                self.agent_health.pop(agent_id, None)
                
                # Remove from fault history
                self.fault_history = [f for f in self.fault_history if f.agent_id != agent_id]
                
                logger.info(f"Unregistered agent {agent_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to unregister agent {agent_id}: {e}")
            return False
    
    async def _start_agent(self, agent_id: str) -> bool:
        """Start an agent"""
        try:
            if agent_id not in self.managed_agents:
                return False
            
            agent_info = self.managed_agents[agent_id]
            agent_instance = agent_info["instance"]
            
            # Start the agent
            await agent_instance.start()
            
            # Update state
            agent_info["status"] = Status.RUNNING
            agent_info["start_time"] = datetime.now()
            
            # Update health metrics
            if agent_id in self.agent_health:
                self.agent_health[agent_id].status = AgentHealthStatus.HEALTHY
                self.agent_health[agent_id].last_heartbeat = datetime.now()
            
            # Emit event
            await publish_event(
                "agent.started",
                {"agent_id": agent_id, "timestamp": datetime.now()},
                priority=EventPriority.HIGH,
                source=f"lifecycle:{self.id}"
            )
            
            logger.info(f"Started agent {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start agent {agent_id}: {e}")
            await self._handle_fault(agent_id, FaultType.CONFIGURATION_ERROR, str(e))
            return False
    
    async def _stop_agent(self, agent_id: str) -> bool:
        """Stop an agent gracefully"""
        try:
            if agent_id not in self.managed_agents:
                return False
            
            agent_info = self.managed_agents[agent_id]
            agent_instance = agent_info["instance"]
            
            # Stop the agent
            await agent_instance.stop()
            
            # Update state
            agent_info["status"] = Status.STOPPED
            
            # Update health metrics
            if agent_id in self.agent_health:
                self.agent_health[agent_id].status = AgentHealthStatus.UNKNOWN
            
            # Emit event
            await publish_event(
                "agent.stopped",
                {"agent_id": agent_id, "timestamp": datetime.now()},
                priority=EventPriority.NORMAL,
                source=f"lifecycle:{self.id}"
            )
            
            logger.info(f"Stopped agent {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop agent {agent_id}: {e}")
            return False
    
    async def _restart_agent(self, agent_id: str) -> bool:
        """Restart an agent"""
        try:
            if agent_id not in self.managed_agents:
                return False
            
            agent_info = self.managed_agents[agent_id]
            
            # Check restart limits
            if agent_info["restart_count"] >= self.max_restart_attempts:
                logger.error(f"Agent {agent_id} exceeded maximum restart attempts")
                await self._handle_fault(agent_id, FaultType.UNKNOWN_ERROR, "Maximum restart attempts exceeded")
                return False
            
            logger.info(f"Restarting agent {agent_id}")
            
            # Stop the agent
            await self._stop_agent(agent_id)
            
            # Wait before restart
            await asyncio.sleep(self.restart_delay)
            
            # Start the agent
            success = await self._start_agent(agent_id)
            
            if success:
                agent_info["restart_count"] += 1
                self.agent_health[agent_id].restart_count += 1
                
                # Emit event
                await publish_event(
                    "agent.restarted",
                    {"agent_id": agent_id, "restart_count": agent_info["restart_count"]},
                    priority=EventPriority.HIGH,
                    source=f"lifecycle:{self.id}"
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to restart agent {agent_id}: {e}")
            return False
    
    async def _health_monitoring_loop(self) -> None:
        """Background health monitoring loop"""
        while self.status == Status.RUNNING:
            try:
                await self._check_all_agents_health()
                await asyncio.sleep(self.health_check_interval)
            except Exception as e:
                logger.error(f"Health monitoring loop error: {e}")
                await asyncio.sleep(self.health_check_interval * 2)
    
    async def _fault_detection_loop(self) -> None:
        """Background fault detection loop"""
        while self.status == Status.RUNNING:
            try:
                await self._detect_and_handle_faults()
                await asyncio.sleep(30)  # Check for faults every 30 seconds
            except Exception as e:
                logger.error(f"Fault detection loop error: {e}")
                await asyncio.sleep(60)
    
    async def _check_all_agents_health(self) -> None:
        """Check health of all managed agents"""
        for agent_id in list(self.managed_agents.keys()):
            await self._check_agent_health(agent_id)
    
    async def _check_agent_health(self, agent_id: str) -> AgentHealthStatus:
        """Check health of a specific agent"""
        try:
            if agent_id not in self.managed_agents:
                return AgentHealthStatus.UNKNOWN
            
            agent_info = self.managed_agents[agent_id]
            agent_instance = agent_info["instance"]
            health_metrics = self.agent_health[agent_id]
            
            # Perform health check
            start_time = datetime.now()
            health_data = await agent_instance.health_check()
            response_time = (datetime.now() - start_time).total_seconds()
            
            # Update metrics
            health_metrics.last_heartbeat = datetime.now()
            health_metrics.response_time = response_time
            
            # Calculate uptime
            if agent_info["start_time"]:
                health_metrics.uptime = datetime.now() - agent_info["start_time"]
            
            # Determine health status
            if response_time > 5.0:  # Slow response
                health_metrics.status = AgentHealthStatus.DEGRADED
            elif health_data.get("status") == "error":
                health_metrics.status = AgentHealthStatus.UNHEALTHY
            else:
                health_metrics.status = AgentHealthStatus.HEALTHY
            
            return health_metrics.status
            
        except asyncio.TimeoutError:
            logger.warning(f"Health check timeout for agent {agent_id}")
            await self._handle_fault(agent_id, FaultType.TIMEOUT, "Health check timeout")
            return AgentHealthStatus.CRITICAL
            
        except Exception as e:
            logger.error(f"Health check failed for agent {agent_id}: {e}")
            await self._handle_fault(agent_id, FaultType.COMMUNICATION_FAILURE, str(e))
            return AgentHealthStatus.CRITICAL
    
    async def _detect_and_handle_faults(self) -> None:
        """Detect and handle agent faults"""
        current_time = datetime.now()
        
        for agent_id, health_metrics in self.agent_health.items():
            # Check for stale heartbeat
            time_since_heartbeat = current_time - health_metrics.last_heartbeat
            if time_since_heartbeat > timedelta(seconds=self.heartbeat_interval * 2):
                await self._handle_fault(
                    agent_id, 
                    FaultType.COMMUNICATION_FAILURE, 
                    f"No heartbeat for {time_since_heartbeat.total_seconds()} seconds"
                )
            
            # Check error rate
            if health_metrics.error_rate > 0.5:  # 50% error rate threshold
                await self._handle_fault(
                    agent_id,
                    FaultType.TASK_FAILURE,
                    f"High error rate: {health_metrics.error_rate:.2%}"
                )
            
            # Check resource utilization
            for resource, utilization in health_metrics.resource_utilization.items():
                if utilization > 0.95:  # 95% utilization threshold
                    await self._handle_fault(
                        agent_id,
                        FaultType.RESOURCE_EXHAUSTION,
                        f"High {resource} utilization: {utilization:.2%}"
                    )
    
    async def _handle_fault(self, agent_id: str, fault_type: FaultType, description: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Handle a detected fault"""
        try:
            # Create fault event
            fault_event = FaultEvent(
                agent_id=agent_id,
                fault_type=fault_type,
                severity=self._determine_fault_severity(fault_type),
                timestamp=datetime.now(),
                description=description,
                context=context or {}
            )
            
            # Record fault
            self.fault_history.append(fault_event)
            
            # Update agent health
            if agent_id in self.agent_health:
                self.agent_health[agent_id].status = AgentHealthStatus.UNHEALTHY
                self.agent_health[agent_id].last_error = description
            
            # Emit fault event
            await publish_event(
                "agent.fault_detected",
                {
                    "agent_id": agent_id,
                    "fault_type": fault_type.value,
                    "severity": fault_event.severity,
                    "description": description
                },
                priority=EventPriority.HIGH,
                source=f"lifecycle:{self.id}"
            )
            
            # Apply fault policy
            policy = self.fault_policies.get(fault_type, {"auto_restart": False, "escalate_after": 1})
            
            # Count recent faults of this type
            recent_faults = [f for f in self.fault_history 
                           if f.agent_id == agent_id 
                           and f.fault_type == fault_type 
                           and (datetime.now() - f.timestamp) < timedelta(minutes=10)]
            
            if len(recent_faults) >= policy["escalate_after"]:
                await self._escalate_fault(agent_id, fault_event)
            elif policy["auto_restart"]:
                await self._restart_agent(agent_id)
            
            logger.warning(f"Fault detected for agent {agent_id}: {fault_type.value} - {description}")
            
        except Exception as e:
            logger.error(f"Failed to handle fault for agent {agent_id}: {e}")
    
    def _determine_fault_severity(self, fault_type: FaultType) -> str:
        """Determine fault severity based on type"""
        severity_mapping = {
            FaultType.TASK_FAILURE: "medium",
            FaultType.TIMEOUT: "medium",
            FaultType.RESOURCE_EXHAUSTION: "high",
            FaultType.COMMUNICATION_FAILURE: "high",
            FaultType.CONFIGURATION_ERROR: "high",
            FaultType.DEPENDENCY_FAILURE: "medium",
            FaultType.UNKNOWN_ERROR: "high"
        }
        return severity_mapping.get(fault_type, "medium")
    
    async def _escalate_fault(self, agent_id: str, fault_event: FaultEvent) -> None:
        """Escalate a fault to higher-level recovery mechanisms"""
        logger.error(f"Escalating fault for agent {agent_id}: {fault_event.fault_type.value}")
        
        # Try recovery strategies in order
        strategies = ["reallocate_tasks", "reduce_load", "restart_agent", "escalate_to_human"]
        
        for strategy in strategies:
            try:
                recovery_func = self.recovery_strategies.get(strategy)
                if recovery_func:
                    success = await recovery_func(agent_id)
                    if success:
                        logger.info(f"Recovery strategy '{strategy}' successful for agent {agent_id}")
                        break
            except Exception as e:
                logger.error(f"Recovery strategy '{strategy}' failed for agent {agent_id}: {e}")
        
        # Emit escalation event
        await publish_event(
            "agent.fault_escalated",
            {
                "agent_id": agent_id,
                "fault_type": fault_event.fault_type.value,
                "severity": fault_event.severity,
                "escalation_time": datetime.now()
            },
            priority=EventPriority.CRITICAL,
            source=f"lifecycle:{self.id}"
        )
    
    async def _reallocate_agent_tasks(self, agent_id: str) -> bool:
        """Reallocate tasks from a faulty agent"""
        # This would interface with the assignment engine to reallocate tasks
        # For now, just emit an event requesting reallocation
        await publish_event(
            "agent.task_reallocation_requested",
            {"agent_id": agent_id, "reason": "fault_recovery"},
            priority=EventPriority.HIGH,
            source=f"lifecycle:{self.id}"
        )
        return True
    
    async def _reduce_agent_load(self, agent_id: str) -> bool:
        """Reduce load on a struggling agent"""
        # This would interface with the assignment engine to reduce load
        await publish_event(
            "agent.load_reduction_requested",
            {"agent_id": agent_id, "reason": "fault_recovery"},
            priority=EventPriority.HIGH,
            source=f"lifecycle:{self.id}"
        )
        return True
    
    async def _escalate_to_human(self, agent_id: str) -> bool:
        """Escalate to human intervention"""
        await publish_event(
            "agent.human_intervention_required",
            {"agent_id": agent_id, "timestamp": datetime.now()},
            priority=EventPriority.CRITICAL,
            source=f"lifecycle:{self.id}"
        )
        return True
    
    async def _setup_event_subscriptions(self) -> None:
        """Setup event subscriptions for lifecycle management"""
        # Subscribe to agent events
        agent_filter = EventFilter(
            event_types=["agent.task_completed", "agent.task_failed", "agent.heartbeat"],
            sources=["agent:*"]
        )
        
        await subscribe_to_events(agent_filter, self._handle_agent_event)
    
    async def _handle_agent_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Handle agent-related events"""
        try:
            agent_id = data.get("agent_id")
            if not agent_id or agent_id not in self.agent_health:
                return
            
            health_metrics = self.agent_health[agent_id]
            
            if event_type == "agent.task_completed":
                # Update success rate
                health_metrics.task_success_rate = min(1.0, health_metrics.task_success_rate + 0.01)
                health_metrics.error_rate = max(0.0, health_metrics.error_rate - 0.01)
                
            elif event_type == "agent.task_failed":
                # Update error rate
                health_metrics.error_rate = min(1.0, health_metrics.error_rate + 0.05)
                health_metrics.task_success_rate = max(0.0, health_metrics.task_success_rate - 0.01)
                
            elif event_type == "agent.heartbeat":
                # Update heartbeat
                health_metrics.last_heartbeat = datetime.now()
                
        except Exception as e:
            logger.error(f"Failed to handle agent event {event_type}: {e}")
    
    async def _shutdown_all_agents(self) -> None:
        """Gracefully shutdown all managed agents"""
        logger.info("Shutting down all managed agents")
        
        shutdown_tasks = []
        for agent_id in list(self.managed_agents.keys()):
            task = asyncio.create_task(self._stop_agent(agent_id))
            shutdown_tasks.append(task)
        
        if shutdown_tasks:
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)
    
    def get_agent_status(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Get status of agents"""
        if agent_id:
            # Single agent status
            if agent_id not in self.managed_agents:
                return {}
            
            agent_info = self.managed_agents[agent_id]
            health_metrics = self.agent_health.get(agent_id)
            
            return {
                "agent_id": agent_id,
                "status": agent_info["status"].value if hasattr(agent_info["status"], "value") else str(agent_info["status"]),
                "health": health_metrics.__dict__ if health_metrics else {},
                "restart_count": agent_info["restart_count"],
                "uptime": str(health_metrics.uptime) if health_metrics else "unknown"
            }
        
        else:
            # All agents status
            agents_status = {}
            for agent_id in self.managed_agents:
                agents_status[agent_id] = self.get_agent_status(agent_id)
            
            return {
                "agents": agents_status,
                "summary": {
                    "total_agents": len(self.managed_agents),
                    "healthy_agents": len([a for a in self.agent_health.values() if a.status == AgentHealthStatus.HEALTHY]),
                    "active_faults": len([f for f in self.fault_history if not f.resolved])
                }
            }