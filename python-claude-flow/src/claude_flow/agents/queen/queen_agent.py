"""
Queen Agent Implementation for Claude-Flow

The Queen Agent serves as the master coordinator for all agent activities,
responsible for task decomposition, agent assignment, conflict resolution,
and swarm monitoring.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

from ..interfaces import (
    QueenAgentInterface, TaskDefinition, TaskResult, AgentConfig, 
    TaskPriority, AgentType, AgentCapability
)
from ...core.interfaces import Agent, BaseConfig, Status
from ...core.event_bus import publish_event, EventPriority, EventFilter, subscribe_to_events
from ...core.config import get_config

logger = logging.getLogger(__name__)


class TaskDecomposer:
    """
    Intelligent task decomposition engine
    
    Analyzes complex tasks and breaks them down into manageable subtasks
    that can be distributed to specialized worker agents.
    """
    
    def __init__(self):
        self.decomposition_rules = {
            "code_development": self._decompose_code_task,
            "system_design": self._decompose_design_task,
            "testing": self._decompose_testing_task,
            "research": self._decompose_research_task,
            "deployment": self._decompose_deployment_task,
            "default": self._decompose_generic_task
        }
    
    async def decompose_task(self, task: TaskDefinition) -> List[TaskDefinition]:
        """
        Decompose a complex task into subtasks
        
        Args:
            task: The task to decompose
            
        Returns:
            List of subtasks
        """
        # Determine task category
        task_category = self._classify_task(task)
        
        # Get appropriate decomposition strategy
        decomposer = self.decomposition_rules.get(task_category, self.decomposition_rules["default"])
        
        # Decompose the task
        subtasks = await decomposer(task)
        
        # Set dependencies between subtasks
        self._set_task_dependencies(subtasks)
        
        logger.info(f"Decomposed task {task.id} into {len(subtasks)} subtasks")
        return subtasks
    
    def _classify_task(self, task: TaskDefinition) -> str:
        """Classify task type based on description and requirements"""
        description = task.description.lower()
        
        if any(keyword in description for keyword in ["code", "implement", "develop", "program"]):
            return "code_development"
        elif any(keyword in description for keyword in ["design", "architecture", "plan"]):
            return "system_design"
        elif any(keyword in description for keyword in ["test", "verify", "validate"]):
            return "testing"
        elif any(keyword in description for keyword in ["research", "analyze", "study"]):
            return "research"
        elif any(keyword in description for keyword in ["deploy", "install", "configure"]):
            return "deployment"
        else:
            return "default"
    
    async def _decompose_code_task(self, task: TaskDefinition) -> List[TaskDefinition]:
        """Decompose code development tasks"""
        subtasks = []
        
        # 1. Requirements analysis
        subtasks.append(TaskDefinition(
            id=f"{task.id}_req",
            description=f"Analyze requirements for: {task.description}",
            requirements={"type": "research", "domain": "requirements"},
            priority=TaskPriority.HIGH,
            metadata={"parent_task": task.id, "phase": "requirements"}
        ))
        
        # 2. Design
        subtasks.append(TaskDefinition(
            id=f"{task.id}_design",
            description=f"Design solution for: {task.description}",
            requirements={"type": "design", "domain": "architecture"},
            priority=TaskPriority.HIGH,
            dependencies=[f"{task.id}_req"],
            metadata={"parent_task": task.id, "phase": "design"}
        ))
        
        # 3. Implementation
        subtasks.append(TaskDefinition(
            id=f"{task.id}_impl",
            description=f"Implement solution for: {task.description}",
            requirements={"type": "coding", "domain": "implementation"},
            priority=TaskPriority.NORMAL,
            dependencies=[f"{task.id}_design"],
            metadata={"parent_task": task.id, "phase": "implementation"}
        ))
        
        # 4. Testing
        subtasks.append(TaskDefinition(
            id=f"{task.id}_test",
            description=f"Test implementation for: {task.description}",
            requirements={"type": "testing", "domain": "quality_assurance"},
            priority=TaskPriority.NORMAL,
            dependencies=[f"{task.id}_impl"],
            metadata={"parent_task": task.id, "phase": "testing"}
        ))
        
        return subtasks
    
    async def _decompose_design_task(self, task: TaskDefinition) -> List[TaskDefinition]:
        """Decompose system design tasks"""
        subtasks = []
        
        # 1. Requirements gathering
        subtasks.append(TaskDefinition(
            id=f"{task.id}_gather",
            description=f"Gather requirements for: {task.description}",
            requirements={"type": "research", "domain": "requirements"},
            priority=TaskPriority.HIGH,
            metadata={"parent_task": task.id, "phase": "requirements"}
        ))
        
        # 2. Architecture design
        subtasks.append(TaskDefinition(
            id=f"{task.id}_arch",
            description=f"Design architecture for: {task.description}",
            requirements={"type": "design", "domain": "architecture"},
            priority=TaskPriority.HIGH,
            dependencies=[f"{task.id}_gather"],
            metadata={"parent_task": task.id, "phase": "architecture"}
        ))
        
        # 3. Detailed design
        subtasks.append(TaskDefinition(
            id=f"{task.id}_detail",
            description=f"Create detailed design for: {task.description}",
            requirements={"type": "design", "domain": "detailed_design"},
            priority=TaskPriority.NORMAL,
            dependencies=[f"{task.id}_arch"],
            metadata={"parent_task": task.id, "phase": "detailed_design"}
        ))
        
        return subtasks
    
    async def _decompose_testing_task(self, task: TaskDefinition) -> List[TaskDefinition]:
        """Decompose testing tasks"""
        subtasks = []
        
        # 1. Test planning
        subtasks.append(TaskDefinition(
            id=f"{task.id}_plan",
            description=f"Plan tests for: {task.description}",
            requirements={"type": "testing", "domain": "test_planning"},
            priority=TaskPriority.HIGH,
            metadata={"parent_task": task.id, "phase": "planning"}
        ))
        
        # 2. Test implementation
        subtasks.append(TaskDefinition(
            id=f"{task.id}_impl",
            description=f"Implement tests for: {task.description}",
            requirements={"type": "testing", "domain": "test_implementation"},
            priority=TaskPriority.NORMAL,
            dependencies=[f"{task.id}_plan"],
            metadata={"parent_task": task.id, "phase": "implementation"}
        ))
        
        # 3. Test execution
        subtasks.append(TaskDefinition(
            id=f"{task.id}_exec",
            description=f"Execute tests for: {task.description}",
            requirements={"type": "testing", "domain": "test_execution"},
            priority=TaskPriority.NORMAL,
            dependencies=[f"{task.id}_impl"],
            metadata={"parent_task": task.id, "phase": "execution"}
        ))
        
        return subtasks
    
    async def _decompose_research_task(self, task: TaskDefinition) -> List[TaskDefinition]:
        """Decompose research tasks"""
        subtasks = []
        
        # 1. Information gathering
        subtasks.append(TaskDefinition(
            id=f"{task.id}_gather",
            description=f"Gather information for: {task.description}",
            requirements={"type": "research", "domain": "information_gathering"},
            priority=TaskPriority.HIGH,
            metadata={"parent_task": task.id, "phase": "gathering"}
        ))
        
        # 2. Analysis
        subtasks.append(TaskDefinition(
            id=f"{task.id}_analyze",
            description=f"Analyze findings for: {task.description}",
            requirements={"type": "research", "domain": "analysis"},
            priority=TaskPriority.NORMAL,
            dependencies=[f"{task.id}_gather"],
            metadata={"parent_task": task.id, "phase": "analysis"}
        ))
        
        # 3. Synthesis
        subtasks.append(TaskDefinition(
            id=f"{task.id}_synthesize",
            description=f"Synthesize results for: {task.description}",
            requirements={"type": "research", "domain": "synthesis"},
            priority=TaskPriority.NORMAL,
            dependencies=[f"{task.id}_analyze"],
            metadata={"parent_task": task.id, "phase": "synthesis"}
        ))
        
        return subtasks
    
    async def _decompose_deployment_task(self, task: TaskDefinition) -> List[TaskDefinition]:
        """Decompose deployment tasks"""
        subtasks = []
        
        # 1. Environment preparation
        subtasks.append(TaskDefinition(
            id=f"{task.id}_prep",
            description=f"Prepare environment for: {task.description}",
            requirements={"type": "devops", "domain": "environment_setup"},
            priority=TaskPriority.HIGH,
            metadata={"parent_task": task.id, "phase": "preparation"}
        ))
        
        # 2. Deployment
        subtasks.append(TaskDefinition(
            id=f"{task.id}_deploy",
            description=f"Deploy solution for: {task.description}",
            requirements={"type": "devops", "domain": "deployment"},
            priority=TaskPriority.HIGH,
            dependencies=[f"{task.id}_prep"],
            metadata={"parent_task": task.id, "phase": "deployment"}
        ))
        
        # 3. Verification
        subtasks.append(TaskDefinition(
            id=f"{task.id}_verify",
            description=f"Verify deployment for: {task.description}",
            requirements={"type": "testing", "domain": "deployment_verification"},
            priority=TaskPriority.NORMAL,
            dependencies=[f"{task.id}_deploy"],
            metadata={"parent_task": task.id, "phase": "verification"}
        ))
        
        return subtasks
    
    async def _decompose_generic_task(self, task: TaskDefinition) -> List[TaskDefinition]:
        """Decompose generic tasks"""
        # For generic tasks, create a simple decomposition
        subtasks = []
        
        # 1. Analysis
        subtasks.append(TaskDefinition(
            id=f"{task.id}_analyze",
            description=f"Analyze requirements for: {task.description}",
            requirements={"type": "research", "domain": "analysis"},
            priority=TaskPriority.HIGH,
            metadata={"parent_task": task.id, "phase": "analysis"}
        ))
        
        # 2. Execution
        subtasks.append(TaskDefinition(
            id=f"{task.id}_execute",
            description=f"Execute: {task.description}",
            requirements={"type": "general", "domain": "execution"},
            priority=TaskPriority.NORMAL,
            dependencies=[f"{task.id}_analyze"],
            metadata={"parent_task": task.id, "phase": "execution"}
        ))
        
        # 3. Validation
        subtasks.append(TaskDefinition(
            id=f"{task.id}_validate",
            description=f"Validate results for: {task.description}",
            requirements={"type": "testing", "domain": "validation"},
            priority=TaskPriority.NORMAL,
            dependencies=[f"{task.id}_execute"],
            metadata={"parent_task": task.id, "phase": "validation"}
        ))
        
        return subtasks
    
    def _set_task_dependencies(self, subtasks: List[TaskDefinition]) -> None:
        """Set up dependencies between subtasks"""
        # Dependencies are already set in the individual decomposer methods
        # This method can be extended for more complex dependency logic
        pass


class AgentAssigner:
    """
    Intelligent agent assignment system
    
    Matches tasks with the most suitable available agents based on
    capabilities, workload, and performance history.
    """
    
    def __init__(self):
        self.agent_registry: Dict[str, Dict[str, Any]] = {}
        self.assignment_history: List[Dict[str, Any]] = []
    
    def register_agent(self, agent_id: str, agent_info: Dict[str, Any]) -> None:
        """Register an agent in the assignment system"""
        self.agent_registry[agent_id] = {
            **agent_info,
            "current_tasks": [],
            "performance_score": 1.0,
            "last_assigned": None,
            "total_tasks": 0,
            "successful_tasks": 0
        }
        logger.info(f"Registered agent {agent_id} for assignment")
    
    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent from the assignment system"""
        if agent_id in self.agent_registry:
            del self.agent_registry[agent_id]
            logger.info(f"Unregistered agent {agent_id}")
    
    async def assign_task(self, task: TaskDefinition) -> Optional[str]:
        """
        Assign a task to the most suitable agent
        
        Args:
            task: Task to assign
            
        Returns:
            Agent ID if assignment successful, None otherwise
        """
        suitable_agents = self._find_suitable_agents(task)
        
        if not suitable_agents:
            logger.warning(f"No suitable agents found for task {task.id}")
            return None
        
        # Rank agents by suitability score
        ranked_agents = sorted(suitable_agents, key=lambda x: x[1], reverse=True)
        
        # Try to assign to the best available agent
        for agent_id, score in ranked_agents:
            if await self._attempt_assignment(agent_id, task):
                self._record_assignment(agent_id, task, score)
                logger.info(f"Assigned task {task.id} to agent {agent_id} (score: {score:.2f})")
                return agent_id
        
        logger.warning(f"Failed to assign task {task.id} to any agent")
        return None
    
    def _find_suitable_agents(self, task: TaskDefinition) -> List[Tuple[str, float]]:
        """Find agents suitable for a task with suitability scores"""
        suitable_agents = []
        
        for agent_id, agent_info in self.agent_registry.items():
            score = self._calculate_suitability_score(agent_info, task)
            if score > 0.3:  # Minimum suitability threshold
                suitable_agents.append((agent_id, score))
        
        return suitable_agents
    
    def _calculate_suitability_score(self, agent_info: Dict[str, Any], task: TaskDefinition) -> float:
        """Calculate how suitable an agent is for a task"""
        score = 0.0
        
        # 1. Capability match (40% weight)
        capability_score = self._score_capability_match(agent_info, task)
        score += capability_score * 0.4
        
        # 2. Workload factor (25% weight)
        workload_score = self._score_workload(agent_info)
        score += workload_score * 0.25
        
        # 3. Performance history (20% weight)
        performance_score = agent_info.get("performance_score", 1.0)
        score += min(performance_score, 2.0) * 0.2
        
        # 4. Specialization bonus (10% weight)
        specialization_score = self._score_specialization(agent_info, task)
        score += specialization_score * 0.1
        
        # 5. Availability bonus (5% weight)
        availability_score = 1.0 if len(agent_info.get("current_tasks", [])) == 0 else 0.5
        score += availability_score * 0.05
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _score_capability_match(self, agent_info: Dict[str, Any], task: TaskDefinition) -> float:
        """Score how well agent capabilities match task requirements"""
        capabilities = agent_info.get("capabilities", [])
        required_type = task.requirements.get("type", "general")
        required_domain = task.requirements.get("domain", "general")
        
        # Check for exact capability match
        for capability in capabilities:
            if (isinstance(capability, dict) and 
                capability.get("domain") == required_domain):
                return capability.get("level", 5) / 10.0
            elif (hasattr(capability, 'domain') and 
                  capability.domain == required_domain):
                return capability.level / 10.0
        
        # Check for type match
        agent_type = agent_info.get("type", AgentType.CODER)
        type_compatibility = {
            "research": [AgentType.RESEARCHER],
            "design": [AgentType.ARCHITECT],
            "coding": [AgentType.CODER],
            "testing": [AgentType.TESTER],
            "devops": [AgentType.DEVOPS],
            "security": [AgentType.SECURITY]
        }
        
        compatible_types = type_compatibility.get(required_type, [])
        if agent_type in compatible_types:
            return 0.7
        
        return 0.3  # Basic compatibility
    
    def _score_workload(self, agent_info: Dict[str, Any]) -> float:
        """Score based on current workload (lower workload = higher score)"""
        current_tasks = len(agent_info.get("current_tasks", []))
        max_tasks = agent_info.get("max_concurrent_tasks", 3)
        
        if current_tasks >= max_tasks:
            return 0.0  # Overloaded
        
        utilization = current_tasks / max_tasks
        return 1.0 - utilization
    
    def _score_specialization(self, agent_info: Dict[str, Any], task: TaskDefinition) -> float:
        """Score based on agent specialization"""
        specialization = agent_info.get("specialization")
        required_domain = task.requirements.get("domain", "general")
        
        if specialization and specialization in required_domain:
            return 1.0
        
        return 0.5
    
    async def _attempt_assignment(self, agent_id: str, task: TaskDefinition) -> bool:
        """Attempt to assign task to agent"""
        # In a real implementation, this would communicate with the agent
        # For now, we'll assume assignment is successful if agent is available
        agent_info = self.agent_registry.get(agent_id)
        if not agent_info:
            return False
        
        current_tasks = agent_info.get("current_tasks", [])
        max_tasks = agent_info.get("max_concurrent_tasks", 3)
        
        if len(current_tasks) >= max_tasks:
            return False
        
        # Add task to agent's current tasks
        current_tasks.append(task.id)
        agent_info["last_assigned"] = datetime.now()
        
        return True
    
    def _record_assignment(self, agent_id: str, task: TaskDefinition, score: float) -> None:
        """Record assignment for future analysis"""
        assignment_record = {
            "agent_id": agent_id,
            "task_id": task.id,
            "task_type": task.requirements.get("type", "general"),
            "suitability_score": score,
            "assigned_at": datetime.now(),
            "priority": task.priority
        }
        
        self.assignment_history.append(assignment_record)
        
        # Update agent stats
        agent_info = self.agent_registry[agent_id]
        agent_info["total_tasks"] += 1
    
    def update_agent_performance(self, agent_id: str, task_id: str, success: bool) -> None:
        """Update agent performance based on task completion"""
        if agent_id not in self.agent_registry:
            return
        
        agent_info = self.agent_registry[agent_id]
        
        # Remove task from current tasks
        current_tasks = agent_info.get("current_tasks", [])
        if task_id in current_tasks:
            current_tasks.remove(task_id)
        
        # Update performance score
        if success:
            agent_info["successful_tasks"] = agent_info.get("successful_tasks", 0) + 1
        
        # Calculate new performance score (exponential moving average)
        total_tasks = agent_info.get("total_tasks", 1)
        successful_tasks = agent_info.get("successful_tasks", 0)
        success_rate = successful_tasks / max(total_tasks, 1)
        
        current_score = agent_info.get("performance_score", 1.0)
        new_score = 0.8 * current_score + 0.2 * (2.0 * success_rate)  # Blend with current
        agent_info["performance_score"] = max(0.1, min(2.0, new_score))  # Clamp between 0.1 and 2.0
        
        logger.debug(f"Updated performance for agent {agent_id}: {new_score:.2f}")


class QueenAgent(Agent, QueenAgentInterface):
    """
    Queen Agent - Master coordinator for all agent activities
    
    The Queen Agent is responsible for:
    - Task decomposition and planning
    - Agent recruitment and assignment
    - Conflict resolution
    - Swarm monitoring and coordination
    - Performance optimization
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        base_config = config or AgentConfig(
            name="Queen Agent",
            agent_type=AgentType.QUEEN,
            capabilities=[
                AgentCapability(name="task_coordination", level=10, domain="management"),
                AgentCapability(name="agent_management", level=10, domain="management"),
                AgentCapability(name="conflict_resolution", level=9, domain="management"),
                AgentCapability(name="resource_allocation", level=9, domain="management")
            ]
        )
        super().__init__(base_config)
        
        # Core components
        self.task_decomposer = TaskDecomposer()
        self.agent_assigner = AgentAssigner()
        
        # State tracking
        self.active_tasks: Dict[str, TaskDefinition] = {}
        self.task_results: Dict[str, TaskResult] = {}
        self.agent_registry: Dict[str, Dict[str, Any]] = {}
        self.swarm_health: Dict[str, Any] = {}
        
        # Performance metrics
        self.coordination_stats = {
            "tasks_coordinated": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "agents_managed": 0,
            "conflicts_resolved": 0
        }
    
    async def _start_implementation(self) -> None:
        """Start the Queen Agent"""
        # Subscribe to relevant events
        await self._setup_event_subscriptions()
        
        # Initialize swarm monitoring
        await self._initialize_swarm_monitoring()
        
        logger.info(f"Queen Agent {self.id} started")
    
    async def _stop_implementation(self) -> None:
        """Stop the Queen Agent"""
        # Clean up any ongoing operations
        await self._cleanup_operations()
        
        logger.info(f"Queen Agent {self.id} stopped")
    
    async def _health_check_implementation(self) -> Dict[str, Any]:
        """Queen Agent health check"""
        return {
            "active_tasks": len(self.active_tasks),
            "registered_agents": len(self.agent_registry),
            "coordination_stats": self.coordination_stats,
            "swarm_health": self.swarm_health
        }
    
    async def execute_task(self, task: TaskDefinition) -> TaskResult:
        """Execute a task through coordination and delegation"""
        try:
            result = await self.coordinate_task(task)
            return result
        except Exception as e:
            logger.error(f"Failed to execute task {task.id}: {e}")
            return TaskResult(
                task_id=task.id,
                agent_id=self.id,
                success=False,
                error_message=str(e)
            )
    
    async def emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit an event from the Queen Agent"""
        await publish_event(
            f"queen.{event_type}",
            {**data, "queen_id": self.id},
            priority=EventPriority.HIGH,
            source=f"queen:{self.id}"
        )
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get Queen Agent performance metrics"""
        return {
            "coordination_stats": self.coordination_stats,
            "active_tasks": len(self.active_tasks),
            "registered_agents": len(self.agent_registry),
            "swarm_health_score": self._calculate_swarm_health_score()
        }
    
    # QueenAgentInterface implementation
    
    async def coordinate_task(self, task: TaskDefinition) -> TaskResult:
        """Coordinate execution of a complex task"""
        self.coordination_stats["tasks_coordinated"] += 1
        
        try:
            # Store task
            self.active_tasks[task.id] = task
            
            # Emit task started event
            await self.emit_event("task_started", {"task": task.__dict__})
            
            # Check if task needs decomposition
            if self._needs_decomposition(task):
                subtasks = await self.task_decomposer.decompose_task(task)
                
                # Coordinate subtasks
                subtask_results = []
                for subtask in subtasks:
                    # Check dependencies
                    if await self._dependencies_satisfied(subtask, subtask_results):
                        result = await self._execute_subtask(subtask)
                        subtask_results.append(result)
                        
                        if not result.success:
                            # Handle subtask failure
                            await self._handle_subtask_failure(subtask, result)
                
                # Aggregate results
                final_result = self._aggregate_subtask_results(task, subtask_results)
            else:
                # Execute task directly
                final_result = await self._execute_single_task(task)
            
            # Update stats
            if final_result.success:
                self.coordination_stats["tasks_completed"] += 1
            else:
                self.coordination_stats["tasks_failed"] += 1
            
            # Clean up
            self.active_tasks.pop(task.id, None)
            self.task_results[task.id] = final_result
            
            # Emit completion event
            await self.emit_event("task_completed", {
                "task_id": task.id,
                "success": final_result.success,
                "execution_time": final_result.execution_time
            })
            
            return final_result
            
        except Exception as e:
            logger.error(f"Task coordination failed for {task.id}: {e}")
            self.coordination_stats["tasks_failed"] += 1
            
            error_result = TaskResult(
                task_id=task.id,
                agent_id=self.id,
                success=False,
                error_message=str(e)
            )
            
            self.task_results[task.id] = error_result
            return error_result
    
    async def assign_task(self, task: TaskDefinition, agent_id: str) -> bool:
        """Assign a task to a specific agent"""
        try:
            # Verify agent exists and is available
            if agent_id not in self.agent_registry:
                logger.error(f"Agent {agent_id} not found in registry")
                return False
            
            # Update task assignment
            task.assigned_agent_id = agent_id
            
            # Record assignment
            self.agent_assigner._record_assignment(agent_id, task, 1.0)
            
            # Emit assignment event
            await self.emit_event("task_assigned", {
                "task_id": task.id,
                "agent_id": agent_id
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to assign task {task.id} to agent {agent_id}: {e}")
            return False
    
    async def recruit_agents(self, requirements: Dict[str, Any]) -> List[str]:
        """Recruit agents based on requirements"""
        recruited_agents = []
        
        try:
            required_count = requirements.get("count", 1)
            required_type = requirements.get("type")
            required_capabilities = requirements.get("capabilities", [])
            
            # Find suitable agents from registry
            for agent_id, agent_info in self.agent_registry.items():
                if len(recruited_agents) >= required_count:
                    break
                
                # Check type match
                if required_type and agent_info.get("type") != required_type:
                    continue
                
                # Check capabilities
                agent_capabilities = agent_info.get("capabilities", [])
                if required_capabilities and not self._has_required_capabilities(
                    agent_capabilities, required_capabilities
                ):
                    continue
                
                recruited_agents.append(agent_id)
            
            logger.info(f"Recruited {len(recruited_agents)} agents for requirements: {requirements}")
            return recruited_agents
            
        except Exception as e:
            logger.error(f"Failed to recruit agents: {e}")
            return []
    
    async def resolve_conflict(self, agents: List[str], issue: str) -> Dict[str, Any]:
        """Resolve conflicts between agents"""
        self.coordination_stats["conflicts_resolved"] += 1
        
        try:
            resolution = {
                "conflict_id": str(uuid4()),
                "agents": agents,
                "issue": issue,
                "resolution": "pending",
                "resolved_at": None
            }
            
            # Implement conflict resolution logic based on issue type
            if "resource" in issue.lower():
                resolution["resolution"] = await self._resolve_resource_conflict(agents)
            elif "priority" in issue.lower():
                resolution["resolution"] = await self._resolve_priority_conflict(agents)
            else:
                resolution["resolution"] = await self._resolve_generic_conflict(agents, issue)
            
            resolution["resolved_at"] = datetime.now()
            
            # Emit conflict resolution event
            await self.emit_event("conflict_resolved", resolution)
            
            logger.info(f"Resolved conflict {resolution['conflict_id']} between agents {agents}")
            return resolution
            
        except Exception as e:
            logger.error(f"Failed to resolve conflict between agents {agents}: {e}")
            return {
                "conflict_id": str(uuid4()),
                "agents": agents,
                "issue": issue,
                "resolution": "failed",
                "error": str(e),
                "resolved_at": datetime.now()
            }
    
    async def monitor_swarm(self) -> Dict[str, Any]:
        """Monitor the health and performance of the agent swarm"""
        try:
            swarm_status = {
                "timestamp": datetime.now(),
                "total_agents": len(self.agent_registry),
                "active_agents": self._count_active_agents(),
                "idle_agents": self._count_idle_agents(),
                "overloaded_agents": self._count_overloaded_agents(),
                "average_performance": self._calculate_average_performance(),
                "task_throughput": self._calculate_task_throughput(),
                "swarm_health_score": self._calculate_swarm_health_score(),
                "alerts": self._generate_swarm_alerts()
            }
            
            # Update swarm health cache
            self.swarm_health = swarm_status
            
            # Emit monitoring event
            await self.emit_event("swarm_monitored", swarm_status)
            
            return swarm_status
            
        except Exception as e:
            logger.error(f"Failed to monitor swarm: {e}")
            return {
                "timestamp": datetime.now(),
                "error": str(e),
                "swarm_health_score": 0.0
            }
    
    # Helper methods
    
    def _needs_decomposition(self, task: TaskDefinition) -> bool:
        """Determine if a task needs decomposition"""
        # Check task complexity indicators
        description = task.description.lower()
        
        # Tasks that typically need decomposition
        complex_keywords = [
            "implement", "build", "create system", "develop application",
            "design architecture", "full stack", "end-to-end", "complete"
        ]
        
        if any(keyword in description for keyword in complex_keywords):
            return True
        
        # Check estimated effort
        estimated_effort = task.metadata.get("estimated_effort_hours", 0)
        if estimated_effort > 8:  # More than 1 day of work
            return True
        
        # Check if task has complex requirements
        requirements = task.requirements
        if isinstance(requirements, dict) and len(requirements) > 3:
            return True
        
        return False
    
    async def _dependencies_satisfied(self, task: TaskDefinition, completed_results: List[TaskResult]) -> bool:
        """Check if task dependencies are satisfied"""
        if not task.dependencies:
            return True
        
        completed_task_ids = {result.task_id for result in completed_results if result.success}
        
        for dependency in task.dependencies:
            if dependency not in completed_task_ids:
                return False
        
        return True
    
    async def _execute_subtask(self, subtask: TaskDefinition) -> TaskResult:
        """Execute a subtask by assigning it to an agent"""
        try:
            # Find and assign agent
            assigned_agent = await self.agent_assigner.assign_task(subtask)
            
            if not assigned_agent:
                return TaskResult(
                    task_id=subtask.id,
                    agent_id=self.id,
                    success=False,
                    error_message="No suitable agent available"
                )
            
            # In a real implementation, this would communicate with the assigned agent
            # For now, simulate task execution
            await asyncio.sleep(0.1)  # Simulate processing time
            
            # Create mock result (in real implementation, this would come from the agent)
            result = TaskResult(
                task_id=subtask.id,
                agent_id=assigned_agent,
                success=True,
                result_data={"status": "completed", "output": f"Subtask {subtask.id} completed"}
            )
            
            # Update agent performance
            self.agent_assigner.update_agent_performance(assigned_agent, subtask.id, True)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute subtask {subtask.id}: {e}")
            return TaskResult(
                task_id=subtask.id,
                agent_id=self.id,
                success=False,
                error_message=str(e)
            )
    
    async def _handle_subtask_failure(self, subtask: TaskDefinition, result: TaskResult) -> None:
        """Handle subtask failure"""
        logger.warning(f"Subtask {subtask.id} failed: {result.error_message}")
        
        # Emit failure event
        await self.emit_event("subtask_failed", {
            "subtask_id": subtask.id,
            "agent_id": result.agent_id,
            "error": result.error_message
        })
        
        # Update agent performance
        if result.agent_id:
            self.agent_assigner.update_agent_performance(result.agent_id, subtask.id, False)
    
    def _aggregate_subtask_results(self, parent_task: TaskDefinition, subtask_results: List[TaskResult]) -> TaskResult:
        """Aggregate subtask results into final result"""
        successful_subtasks = [r for r in subtask_results if r.success]
        failed_subtasks = [r for r in subtask_results if not r.success]
        
        # Determine overall success
        success = len(failed_subtasks) == 0
        
        # Aggregate result data
        result_data = {
            "subtask_results": [r.__dict__ for r in subtask_results],
            "successful_subtasks": len(successful_subtasks),
            "failed_subtasks": len(failed_subtasks),
            "completion_rate": len(successful_subtasks) / len(subtask_results) if subtask_results else 0
        }
        
        # Aggregate errors
        error_message = None
        if failed_subtasks:
            errors = [r.error_message for r in failed_subtasks if r.error_message]
            error_message = "; ".join(errors)
        
        return TaskResult(
            task_id=parent_task.id,
            agent_id=self.id,
            success=success,
            result_data=result_data,
            error_message=error_message
        )
    
    async def _execute_single_task(self, task: TaskDefinition) -> TaskResult:
        """Execute a single task without decomposition"""
        try:
            # Find and assign agent
            assigned_agent = await self.agent_assigner.assign_task(task)
            
            if not assigned_agent:
                return TaskResult(
                    task_id=task.id,
                    agent_id=self.id,
                    success=False,
                    error_message="No suitable agent available"
                )
            
            # In a real implementation, this would communicate with the assigned agent
            # For now, simulate task execution
            await asyncio.sleep(0.1)  # Simulate processing time
            
            # Create mock result
            result = TaskResult(
                task_id=task.id,
                agent_id=assigned_agent,
                success=True,
                result_data={"status": "completed", "output": f"Task {task.id} completed"}
            )
            
            # Update agent performance
            self.agent_assigner.update_agent_performance(assigned_agent, task.id, True)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute single task {task.id}: {e}")
            return TaskResult(
                task_id=task.id,
                agent_id=self.id,
                success=False,
                error_message=str(e)
            )
    
    def _has_required_capabilities(self, agent_capabilities: List[Any], required_capabilities: List[Any]) -> bool:
        """Check if agent has required capabilities"""
        for required in required_capabilities:
            found = False
            for agent_cap in agent_capabilities:
                if isinstance(agent_cap, dict):
                    if agent_cap.get("name") == required.get("name"):
                        found = True
                        break
                elif hasattr(agent_cap, 'name') and hasattr(required, 'name'):
                    if agent_cap.name == required.name:
                        found = True
                        break
            
            if not found:
                return False
        
        return True
    
    async def _resolve_resource_conflict(self, agents: List[str]) -> str:
        """Resolve resource conflicts between agents"""
        # Implement resource allocation algorithm
        # For now, return a simple resolution
        return f"Resource conflict resolved by reallocating resources among {len(agents)} agents"
    
    async def _resolve_priority_conflict(self, agents: List[str]) -> str:
        """Resolve priority conflicts between agents"""
        # Implement priority resolution algorithm
        # For now, return a simple resolution
        return f"Priority conflict resolved by establishing clear priority queue for {len(agents)} agents"
    
    async def _resolve_generic_conflict(self, agents: List[str], issue: str) -> str:
        """Resolve generic conflicts between agents"""
        # Implement generic conflict resolution
        return f"Generic conflict '{issue}' resolved through agent coordination and communication"
    
    def _count_active_agents(self) -> int:
        """Count agents that are currently working on tasks"""
        active_count = 0
        for agent_info in self.agent_registry.values():
            if agent_info.get("current_tasks"):
                active_count += 1
        return active_count
    
    def _count_idle_agents(self) -> int:
        """Count agents that are idle (no current tasks)"""
        idle_count = 0
        for agent_info in self.agent_registry.values():
            if not agent_info.get("current_tasks"):
                idle_count += 1
        return idle_count
    
    def _count_overloaded_agents(self) -> int:
        """Count agents that are overloaded (too many tasks)"""
        overloaded_count = 0
        for agent_info in self.agent_registry.values():
            current_tasks = len(agent_info.get("current_tasks", []))
            max_tasks = agent_info.get("max_concurrent_tasks", 3)
            if current_tasks >= max_tasks:
                overloaded_count += 1
        return overloaded_count
    
    def _calculate_average_performance(self) -> float:
        """Calculate average performance score across all agents"""
        if not self.agent_registry:
            return 0.0
        
        total_score = sum(
            agent_info.get("performance_score", 1.0)
            for agent_info in self.agent_registry.values()
        )
        
        return total_score / len(self.agent_registry)
    
    def _calculate_task_throughput(self) -> float:
        """Calculate task completion throughput"""
        # Simple throughput calculation based on recent completions
        # In a real implementation, this would track completions over time
        completed_tasks = self.coordination_stats["tasks_completed"]
        total_tasks = self.coordination_stats["tasks_coordinated"]
        
        if total_tasks == 0:
            return 0.0
        
        return completed_tasks / total_tasks
    
    def _calculate_swarm_health_score(self) -> float:
        """Calculate overall swarm health score"""
        if not self.agent_registry:
            return 0.0
        
        # Factors contributing to swarm health
        factors = []
        
        # 1. Agent availability (30%)
        total_agents = len(self.agent_registry)
        active_agents = self._count_active_agents()
        overloaded_agents = self._count_overloaded_agents()
        
        availability_score = 1.0 - (overloaded_agents / max(total_agents, 1))
        factors.append((availability_score, 0.3))
        
        # 2. Performance average (40%)
        avg_performance = self._calculate_average_performance()
        performance_score = min(avg_performance / 2.0, 1.0)  # Normalize to 0-1
        factors.append((performance_score, 0.4))
        
        # 3. Task throughput (20%)
        throughput_score = self._calculate_task_throughput()
        factors.append((throughput_score, 0.2))
        
        # 4. Resource utilization (10%)
        if total_agents > 0:
            utilization = active_agents / total_agents
            utilization_score = min(utilization * 1.5, 1.0)  # Optimal around 70%
        else:
            utilization_score = 0.0
        factors.append((utilization_score, 0.1))
        
        # Calculate weighted score
        health_score = sum(score * weight for score, weight in factors)
        return min(max(health_score, 0.0), 1.0)  # Clamp to 0-1
    
    def _generate_swarm_alerts(self) -> List[Dict[str, Any]]:
        """Generate alerts based on swarm health"""
        alerts = []
        
        # Check for overloaded agents
        overloaded_count = self._count_overloaded_agents()
        if overloaded_count > 0:
            alerts.append({
                "type": "overload",
                "severity": "warning",
                "message": f"{overloaded_count} agent(s) are overloaded",
                "timestamp": datetime.now()
            })
        
        # Check for low performance
        avg_performance = self._calculate_average_performance()
        if avg_performance < 0.7:
            alerts.append({
                "type": "performance",
                "severity": "warning",
                "message": f"Average agent performance is low: {avg_performance:.2f}",
                "timestamp": datetime.now()
            })
        
        # Check for low throughput
        throughput = self._calculate_task_throughput()
        if throughput < 0.6:
            alerts.append({
                "type": "throughput",
                "severity": "info",
                "message": f"Task completion rate is low: {throughput:.2f}",
                "timestamp": datetime.now()
            })
        
        return alerts
    
    async def _setup_event_subscriptions(self) -> None:
        """Setup event subscriptions for the Queen Agent"""
        # Subscribe to agent events
        agent_filter = EventFilter(
            event_types=["agent.started", "agent.stopped", "agent.task_completed", "agent.task_failed"],
            sources=["agent:*"]
        )
        
        await subscribe_to_events(agent_filter, self._handle_agent_event)
        
        # Subscribe to task events
        task_filter = EventFilter(
            event_types=["task.created", "task.updated", "task.completed"],
            sources=["task:*"]
        )
        
        await subscribe_to_events(task_filter, self._handle_task_event)
    
    async def _handle_agent_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Handle agent-related events"""
        try:
            if event_type == "agent.started":
                await self._handle_agent_started(data)
            elif event_type == "agent.stopped":
                await self._handle_agent_stopped(data)
            elif event_type == "agent.task_completed":
                await self._handle_agent_task_completed(data)
            elif event_type == "agent.task_failed":
                await self._handle_agent_task_failed(data)
        
        except Exception as e:
            logger.error(f"Failed to handle agent event {event_type}: {e}")
    
    async def _handle_task_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Handle task-related events"""
        try:
            if event_type == "task.created":
                await self._handle_task_created(data)
            elif event_type == "task.updated":
                await self._handle_task_updated(data)
            elif event_type == "task.completed":
                await self._handle_task_completed(data)
        
        except Exception as e:
            logger.error(f"Failed to handle task event {event_type}: {e}")
    
    async def _handle_agent_started(self, data: Dict[str, Any]) -> None:
        """Handle agent started event"""
        agent_id = data.get("agent_id")
        if agent_id:
            # Register agent in assigner
            self.agent_assigner.register_agent(agent_id, data)
            # Store in registry
            self.agent_registry[agent_id] = data
            self.coordination_stats["agents_managed"] = len(self.agent_registry)
            logger.info(f"Registered agent {agent_id}")
    
    async def _handle_agent_stopped(self, data: Dict[str, Any]) -> None:
        """Handle agent stopped event"""
        agent_id = data.get("agent_id")
        if agent_id:
            # Unregister agent
            self.agent_assigner.unregister_agent(agent_id)
            self.agent_registry.pop(agent_id, None)
            self.coordination_stats["agents_managed"] = len(self.agent_registry)
            logger.info(f"Unregistered agent {agent_id}")
    
    async def _handle_agent_task_completed(self, data: Dict[str, Any]) -> None:
        """Handle agent task completed event"""
        agent_id = data.get("agent_id")
        task_id = data.get("task_id")
        
        if agent_id and task_id:
            self.agent_assigner.update_agent_performance(agent_id, task_id, True)
    
    async def _handle_agent_task_failed(self, data: Dict[str, Any]) -> None:
        """Handle agent task failed event"""
        agent_id = data.get("agent_id")
        task_id = data.get("task_id")
        
        if agent_id and task_id:
            self.agent_assigner.update_agent_performance(agent_id, task_id, False)
    
    async def _handle_task_created(self, data: Dict[str, Any]) -> None:
        """Handle task created event"""
        # Task creation handling logic
        pass
    
    async def _handle_task_updated(self, data: Dict[str, Any]) -> None:
        """Handle task updated event"""
        # Task update handling logic
        pass
    
    async def _handle_task_completed(self, data: Dict[str, Any]) -> None:
        """Handle task completed event"""
        # Task completion handling logic
        pass
    
    async def _initialize_swarm_monitoring(self) -> None:
        """Initialize swarm monitoring background task"""
        # Start background monitoring task
        asyncio.create_task(self._swarm_monitoring_loop())
    
    async def _swarm_monitoring_loop(self) -> None:
        """Background loop for continuous swarm monitoring"""
        while self.status == Status.RUNNING:
            try:
                await self.monitor_swarm()
                await asyncio.sleep(30)  # Monitor every 30 seconds
            except Exception as e:
                logger.error(f"Swarm monitoring loop error: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _cleanup_operations(self) -> None:
        """Clean up any ongoing operations during shutdown"""
        # Cancel any ongoing tasks
        for task_id in list(self.active_tasks.keys()):
            logger.info(f"Cleaning up active task {task_id}")
            self.active_tasks.pop(task_id, None)