"""
Base Worker Agent Implementation for Claude-Flow

The Base Worker Agent provides common functionality for all specialized worker agents,
including task execution patterns, progress reporting, and learning mechanisms.
"""

import asyncio
import logging
from abc import abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..interfaces import (
    WorkerAgentInterface, TaskDefinition, TaskResult, AgentConfig,
    AgentType, AgentCapability
)
from ...core.interfaces import Status
from ...core.event_bus import publish_event, EventPriority, EventFilter, subscribe_to_events

logger = logging.getLogger(__name__)


class BaseWorkerAgent(WorkerAgentInterface):
    """
    Base Worker Agent - Common functionality for all specialized worker agents
    
    Provides:
    - Task execution patterns
    - Progress reporting
    - Help requests
    - Learning mechanisms
    - Performance tracking
    """
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        
        # Worker-specific state
        self.current_task: Optional[TaskDefinition] = None
        self.task_progress: float = 0.0
        self.learning_history: List[Dict[str, Any]] = []
        self.performance_metrics = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "average_execution_time": 0.0,
            "success_rate": 0.0,
            "learning_improvements": 0
        }
        
        # Specialization-specific attributes (to be set by subclasses)
        self.specialization: str = "general"
        self.preferred_task_types: List[str] = ["general"]
        self.skill_level_mapping: Dict[str, float] = {}
    
    async def _start_implementation(self) -> None:
        """Start the worker agent"""
        # Subscribe to relevant events
        await self._setup_event_subscriptions()
        
        # Initialize performance tracking
        await self._initialize_performance_tracking()
        
        logger.info(f"Worker Agent {self.id} ({self.specialization}) started")
    
    async def _stop_implementation(self) -> None:
        """Stop the worker agent"""
        # Complete any ongoing tasks gracefully
        if self.current_task:
            await self._complete_current_task_gracefully()
        
        logger.info(f"Worker Agent {self.id} ({self.specialization}) stopped")
    
    async def _health_check_implementation(self) -> Dict[str, Any]:
        """Worker agent health check"""
        return {
            "specialization": self.specialization,
            "current_task": self.current_task.id if self.current_task else None,
            "task_progress": self.task_progress,
            "performance_metrics": self.performance_metrics,
            "learning_history_size": len(self.learning_history)
        }
    
    async def execute_task(self, task: TaskDefinition) -> TaskResult:
        """Execute a task using worker agent patterns"""
        start_time = datetime.now()
        
        try:
            # Set current task
            self.current_task = task
            self.task_progress = 0.0
            
            # Emit task started event
            await self.emit_event("task_started", {
                "task_id": task.id,
                "specialization": self.specialization
            })
            
            # Assess task fit first
            fit_score = await self.assess_task_fit(task)
            if fit_score < 0.3:
                logger.warning(f"Low fit score {fit_score:.2f} for task {task.id}")
            
            # Estimate effort
            estimated_effort = await self.estimate_effort(task)
            
            # Execute the task using specialized implementation
            result = await self._execute_specialized_task(task)
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            result.execution_time = execution_time
            
            # Update performance metrics
            if result.success:
                self.performance_metrics["tasks_completed"] += 1
            else:
                self.performance_metrics["tasks_failed"] += 1
            
            self._update_performance_metrics(execution_time)
            
            # Learn from the task
            await self.learn_from_task(task, result)
            
            # Emit completion event
            await self.emit_event("task_completed", {
                "task_id": task.id,
                "success": result.success,
                "execution_time": execution_time,
                "fit_score": fit_score
            })
            
            # Clear current task
            self.current_task = None
            self.task_progress = 0.0
            
            return result
            
        except Exception as e:
            logger.error(f"Worker agent {self.id} failed to execute task {task.id}: {e}")
            
            # Update failure metrics
            self.performance_metrics["tasks_failed"] += 1
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_performance_metrics(execution_time)
            
            # Emit failure event
            await self.emit_event("task_failed", {
                "task_id": task.id,
                "error": str(e),
                "execution_time": execution_time
            })
            
            # Clear current task
            self.current_task = None
            self.task_progress = 0.0
            
            return TaskResult(
                task_id=task.id,
                agent_id=self.id,
                success=False,
                error_message=str(e),
                execution_time=execution_time
            )
    
    async def emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit an event from the worker agent"""
        await publish_event(
            f"agent.{event_type}",
            {**data, "agent_id": self.id, "agent_type": self.config.agent_type},
            priority=EventPriority.NORMAL,
            source=f"agent:{self.id}"
        )
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get worker agent performance metrics"""
        return {
            "performance_metrics": self.performance_metrics,
            "specialization": self.specialization,
            "current_task_progress": self.task_progress,
            "learning_history_size": len(self.learning_history)
        }
    
    # WorkerAgentInterface implementation
    
    async def assess_task_fit(self, task: TaskDefinition) -> float:
        """Assess how well this agent can handle a task"""
        fit_score = 0.0
        
        # 1. Task type compatibility (40% weight)
        task_type = task.requirements.get("type", "general")
        if task_type in self.preferred_task_types:
            fit_score += 0.4
        elif "general" in self.preferred_task_types:
            fit_score += 0.2
        
        # 2. Domain expertise (35% weight)
        domain = task.requirements.get("domain", "general")
        domain_skill = self.skill_level_mapping.get(domain, 0.5)
        fit_score += domain_skill * 0.35
        
        # 3. Current workload (15% weight)
        workload_factor = 1.0 if not self.current_task else 0.3
        fit_score += workload_factor * 0.15
        
        # 4. Historical performance (10% weight)
        success_rate = self.performance_metrics.get("success_rate", 0.5)
        fit_score += success_rate * 0.1
        
        return min(fit_score, 1.0)
    
    async def estimate_effort(self, task: TaskDefinition) -> int:
        """Estimate effort required for a task in seconds"""
        # Base estimation using task complexity and agent expertise
        base_effort = 3600  # 1 hour default
        
        # Factor in task complexity
        complexity_indicators = task.description.lower()
        if any(word in complexity_indicators for word in ["complex", "comprehensive", "full"]):
            base_effort *= 3
        elif any(word in complexity_indicators for word in ["simple", "basic", "quick"]):
            base_effort *= 0.5
        
        # Factor in domain expertise
        domain = task.requirements.get("domain", "general")
        expertise_level = self.skill_level_mapping.get(domain, 0.5)
        effort_multiplier = 2.0 - expertise_level  # Higher expertise = lower effort
        
        estimated_effort = int(base_effort * effort_multiplier)
        
        # Apply specialization-specific estimation
        return await self._estimate_specialized_effort(task, estimated_effort)
    
    async def report_progress(self, task_id: str, progress: float) -> None:
        """Report progress on current task"""
        if self.current_task and self.current_task.id == task_id:
            self.task_progress = max(0.0, min(1.0, progress))
            
            # Emit progress event
            await self.emit_event("task_progress", {
                "task_id": task_id,
                "progress": self.task_progress,
                "timestamp": datetime.now()
            })
    
    async def request_help(self, task_id: str, assistance_type: str) -> None:
        """Request help from other agents"""
        # Emit help request event
        await self.emit_event("help_requested", {
            "task_id": task_id,
            "assistance_type": assistance_type,
            "requesting_agent": self.id,
            "specialization": self.specialization,
            "timestamp": datetime.now()
        })
        
        logger.info(f"Worker agent {self.id} requested help for task {task_id}: {assistance_type}")
    
    async def learn_from_task(self, task: TaskDefinition, result: TaskResult) -> None:
        """Learn from completed task to improve future performance"""
        learning_entry = {
            "task_id": task.id,
            "task_type": task.requirements.get("type", "general"),
            "task_domain": task.requirements.get("domain", "general"),
            "success": result.success,
            "execution_time": result.execution_time,
            "fit_score": await self.assess_task_fit(task),
            "timestamp": datetime.now(),
            "improvements": []
        }
        
        # Analyze performance and identify improvements
        if result.success:
            if result.execution_time and result.execution_time < self.performance_metrics.get("average_execution_time", float('inf')):
                learning_entry["improvements"].append("faster_execution")
                self.performance_metrics["learning_improvements"] += 1
        else:
            # Analyze failure patterns
            if result.error_message:
                learning_entry["error_pattern"] = self._categorize_error(result.error_message)
        
        # Update skill levels based on performance
        domain = task.requirements.get("domain", "general")
        if result.success:
            current_skill = self.skill_level_mapping.get(domain, 0.5)
            self.skill_level_mapping[domain] = min(1.0, current_skill + 0.05)
        else:
            current_skill = self.skill_level_mapping.get(domain, 0.5)
            self.skill_level_mapping[domain] = max(0.1, current_skill - 0.02)
        
        # Store learning entry
        self.learning_history.append(learning_entry)
        
        # Keep learning history manageable (last 100 entries)
        if len(self.learning_history) > 100:
            self.learning_history = self.learning_history[-100:]
        
        # Apply specialization-specific learning
        await self._learn_specialized_patterns(task, result, learning_entry)
    
    # Abstract methods for specialization
    
    @abstractmethod
    async def _execute_specialized_task(self, task: TaskDefinition) -> TaskResult:
        """Execute a task using agent specialization - to be implemented by subclasses"""
        pass
    
    @abstractmethod
    async def _estimate_specialized_effort(self, task: TaskDefinition, base_estimate: int) -> int:
        """Apply specialization-specific effort estimation - to be implemented by subclasses"""
        pass
    
    @abstractmethod
    async def _learn_specialized_patterns(self, task: TaskDefinition, result: TaskResult, learning_entry: Dict[str, Any]) -> None:
        """Learn specialization-specific patterns - to be implemented by subclasses"""
        pass
    
    # Helper methods
    
    def _update_performance_metrics(self, execution_time: float) -> None:
        """Update performance metrics with new task data"""
        total_tasks = self.performance_metrics["tasks_completed"] + self.performance_metrics["tasks_failed"]
        
        if total_tasks > 0:
            # Update success rate
            self.performance_metrics["success_rate"] = self.performance_metrics["tasks_completed"] / total_tasks
            
            # Update average execution time
            current_avg = self.performance_metrics["average_execution_time"]
            if current_avg == 0.0:
                self.performance_metrics["average_execution_time"] = execution_time
            else:
                # Exponential moving average
                self.performance_metrics["average_execution_time"] = 0.9 * current_avg + 0.1 * execution_time
    
    def _categorize_error(self, error_message: str) -> str:
        """Categorize error message for learning purposes"""
        error_lower = error_message.lower()
        
        if "timeout" in error_lower or "time" in error_lower:
            return "timeout"
        elif "permission" in error_lower or "access" in error_lower:
            return "permission"
        elif "not found" in error_lower or "404" in error_lower:
            return "not_found"
        elif "syntax" in error_lower or "parse" in error_lower:
            return "syntax"
        elif "network" in error_lower or "connection" in error_lower:
            return "network"
        else:
            return "unknown"
    
    async def _setup_event_subscriptions(self) -> None:
        """Setup event subscriptions for the worker agent"""
        # Subscribe to help responses
        help_filter = EventFilter(
            event_types=["agent.help_response"],
            sources=["agent:*"],
            metadata={"target_agent": self.id}
        )
        
        await subscribe_to_events(help_filter, self._handle_help_response)
    
    async def _handle_help_response(self, event_type: str, data: Dict[str, Any]) -> None:
        """Handle help response from other agents"""
        try:
            task_id = data.get("task_id")
            assistance_data = data.get("assistance_data", {})
            
            if task_id and self.current_task and self.current_task.id == task_id:
                logger.info(f"Worker agent {self.id} received help for task {task_id}")
                # Process the assistance (implementation depends on specialization)
                await self._process_assistance(assistance_data)
        
        except Exception as e:
            logger.error(f"Failed to handle help response: {e}")
    
    async def _process_assistance(self, assistance_data: Dict[str, Any]) -> None:
        """Process assistance from other agents - to be implemented by subclasses"""
        pass
    
    async def _initialize_performance_tracking(self) -> None:
        """Initialize performance tracking background task"""
        # Start background performance monitoring
        asyncio.create_task(self._performance_monitoring_loop())
    
    async def _performance_monitoring_loop(self) -> None:
        """Background loop for performance monitoring"""
        while self.status == Status.RUNNING:
            try:
                # Emit periodic performance metrics
                await self.emit_event("performance_metrics", {
                    "metrics": self.performance_metrics,
                    "timestamp": datetime.now()
                })
                
                await asyncio.sleep(300)  # Every 5 minutes
            
            except Exception as e:
                logger.error(f"Performance monitoring loop error: {e}")
                await asyncio.sleep(600)  # Wait longer on error
    
    async def _complete_current_task_gracefully(self) -> None:
        """Complete current task gracefully during shutdown"""
        if self.current_task:
            logger.info(f"Gracefully completing task {self.current_task.id} during shutdown")
            # Attempt to complete or save progress
            try:
                # Report current progress
                await self.report_progress(self.current_task.id, self.task_progress)
                
                # If task is near completion, try to finish it
                if self.task_progress > 0.8:
                    # Quick completion attempt
                    await asyncio.wait_for(
                        self._execute_specialized_task(self.current_task),
                        timeout=30.0
                    )
            except Exception as e:
                logger.warning(f"Could not gracefully complete task {self.current_task.id}: {e}")