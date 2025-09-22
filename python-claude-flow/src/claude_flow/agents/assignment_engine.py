"""
Agent Assignment and Resource Allocation Algorithms for Claude-Flow

This module provides sophisticated algorithms for optimal agent assignment,
resource allocation, and workload balancing in the agent swarm.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

from ..interfaces import TaskDefinition, AgentType
from ...core.interfaces import BaseComponent
from ...core.event_bus import publish_event, EventPriority

logger = logging.getLogger(__name__)


class AssignmentStrategy(Enum):
    """Assignment strategy types"""
    ROUND_ROBIN = "round_robin"
    LOAD_BALANCED = "load_balanced"
    CAPABILITY_FIRST = "capability_first"
    PERFORMANCE_BASED = "performance_based"
    HYBRID = "hybrid"


class ResourceType(Enum):
    """Resource types for allocation"""
    CPU = "cpu"
    MEMORY = "memory"
    NETWORK = "network"
    CONCURRENT_TASKS = "concurrent_tasks"


@dataclass
class AssignmentCandidate:
    """Agent assignment candidate with scoring"""
    agent_id: str
    agent_type: AgentType
    suitability_score: float
    resource_availability: float
    performance_score: float
    workload_factor: float
    assignment_cost: float
    predicted_completion_time: float
    
    def overall_score(self) -> float:
        """Calculate overall assignment score"""
        return (
            self.suitability_score * 0.3 +
            self.resource_availability * 0.25 +
            self.performance_score * 0.2 +
            (1.0 - self.workload_factor) * 0.15 +
            (1.0 / max(self.assignment_cost, 0.1)) * 0.1
        )


@dataclass
class AssignmentResult:
    """Result of agent assignment"""
    agent_id: Optional[str]
    success: bool
    score: float
    assignment_time: datetime
    estimated_completion: Optional[datetime]
    resource_allocation: Dict[str, float]
    constraints_satisfied: bool
    alternatives: List[AssignmentCandidate]


class AgentAssignmentEngine(BaseComponent):
    """
    Advanced agent assignment engine with multiple assignment strategies
    
    Provides intelligent agent selection based on various criteria including
    capability matching, performance history, resource availability, and
    workload balancing.
    """
    
    def __init__(self):
        super().__init__()
        self.assignment_strategy = AssignmentStrategy.HYBRID
        
        # Agent registry and performance tracking
        self.agent_registry: Dict[str, Dict[str, Any]] = {}
        self.performance_history: Dict[str, List[Dict[str, Any]]] = {}
        self.assignment_history: List[Dict[str, Any]] = []
        
        # Assignment algorithms
        self.assignment_algorithms = {
            AssignmentStrategy.ROUND_ROBIN: self._round_robin_assignment,
            AssignmentStrategy.LOAD_BALANCED: self._load_balanced_assignment,
            AssignmentStrategy.CAPABILITY_FIRST: self._capability_first_assignment,
            AssignmentStrategy.PERFORMANCE_BASED: self._performance_based_assignment,
            AssignmentStrategy.HYBRID: self._hybrid_assignment
        }
        
        # Round-robin state
        self.round_robin_index = 0
        
        # Resource allocation tracking
        self.agent_resources: Dict[str, Dict[str, float]] = {}
        self.resource_reservations: Dict[str, Dict[str, float]] = {}
    
    async def _start_implementation(self) -> None:
        """Start the assignment engine"""
        logger.info("Agent Assignment Engine started")
    
    async def _stop_implementation(self) -> None:
        """Stop the assignment engine"""
        logger.info("Agent Assignment Engine stopped")
    
    async def _health_check_implementation(self) -> Dict[str, Any]:
        """Health check for assignment engine"""
        return {
            "registered_agents": len(self.agent_registry),
            "assignment_strategy": self.assignment_strategy.value,
            "total_assignments": len(self.assignment_history),
            "active_reservations": len(self.resource_reservations)
        }
    
    def register_agent(self, agent_id: str, agent_info: Dict[str, Any]) -> None:
        """Register an agent for assignment"""
        self.agent_registry[agent_id] = {
            **agent_info,
            "registration_time": datetime.now(),
            "current_tasks": [],
            "total_assignments": 0,
            "successful_assignments": 0,
            "average_performance": 1.0
        }
        
        # Initialize agent resources
        self.agent_resources[agent_id] = {
            "cpu": agent_info.get("cpu_capacity", 1.0),
            "memory": agent_info.get("memory_capacity", 1.0),
            "network": agent_info.get("network_capacity", 1.0),
            "concurrent_tasks": agent_info.get("max_concurrent_tasks", 3)
        }
        
        logger.info(f"Registered agent {agent_id} for assignment")
    
    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent"""
        self.agent_registry.pop(agent_id, None)
        self.performance_history.pop(agent_id, None)
        self.agent_resources.pop(agent_id, None)
        self.resource_reservations.pop(agent_id, None)
        
        logger.info(f"Unregistered agent {agent_id}")
    
    async def assign_task(self, task: TaskDefinition, constraints: Optional[Dict[str, Any]] = None) -> AssignmentResult:
        """Assign a task to the most suitable agent"""
        try:
            # Apply assignment algorithm
            algorithm = self.assignment_algorithms[self.assignment_strategy]
            candidates = await algorithm(task, constraints or {})
            
            if not candidates:
                return AssignmentResult(
                    agent_id=None,
                    success=False,
                    score=0.0,
                    assignment_time=datetime.now(),
                    estimated_completion=None,
                    resource_allocation={},
                    constraints_satisfied=False,
                    alternatives=[]
                )
            
            # Select best candidate
            best_candidate = max(candidates, key=lambda c: c.overall_score())
            
            # Allocate resources
            allocation_success, allocation = self._allocate_resources(best_candidate.agent_id, task)
            
            if not allocation_success and not constraints.get("allow_resource_violations", False):
                return AssignmentResult(
                    agent_id=None,
                    success=False,
                    score=best_candidate.overall_score(),
                    assignment_time=datetime.now(),
                    estimated_completion=None,
                    resource_allocation={},
                    constraints_satisfied=False,
                    alternatives=candidates[:5]
                )
            
            # Record assignment
            assignment_record = {
                "task_id": task.id,
                "agent_id": best_candidate.agent_id,
                "assignment_time": datetime.now(),
                "score": best_candidate.overall_score(),
                "resource_allocation": allocation,
                "strategy": self.assignment_strategy.value
            }
            self.assignment_history.append(assignment_record)
            
            # Update agent state
            if best_candidate.agent_id in self.agent_registry:
                agent_info = self.agent_registry[best_candidate.agent_id]
                agent_info["current_tasks"].append(task.id)
                agent_info["total_assignments"] += 1
            
            # Estimated completion time
            estimated_completion = datetime.now() + timedelta(seconds=best_candidate.predicted_completion_time)
            
            return AssignmentResult(
                agent_id=best_candidate.agent_id,
                success=True,
                score=best_candidate.overall_score(),
                assignment_time=datetime.now(),
                estimated_completion=estimated_completion,
                resource_allocation=allocation,
                constraints_satisfied=True,
                alternatives=candidates[:5]
            )
            
        except Exception as e:
            logger.error(f"Failed to assign task {task.id}: {e}")
            return AssignmentResult(
                agent_id=None,
                success=False,
                score=0.0,
                assignment_time=datetime.now(),
                estimated_completion=None,
                resource_allocation={},
                constraints_satisfied=False,
                alternatives=[]
            )
    
    async def release_assignment(self, agent_id: str, task_id: str, success: bool, performance_data: Optional[Dict[str, Any]] = None) -> None:
        """Release an assignment and update performance data"""
        # Update agent state
        if agent_id in self.agent_registry:
            agent_info = self.agent_registry[agent_id]
            if task_id in agent_info["current_tasks"]:
                agent_info["current_tasks"].remove(task_id)
            
            if success:
                agent_info["successful_assignments"] += 1
            
            # Update average performance
            total = agent_info["total_assignments"]
            successful = agent_info["successful_assignments"]
            agent_info["average_performance"] = successful / max(total, 1)
        
        # Record performance history
        if agent_id not in self.performance_history:
            self.performance_history[agent_id] = []
        
        performance_record = {
            "task_id": task_id,
            "success": success,
            "timestamp": datetime.now(),
            **(performance_data or {})
        }
        self.performance_history[agent_id].append(performance_record)
        
        # Keep history manageable
        if len(self.performance_history[agent_id]) > 100:
            self.performance_history[agent_id] = self.performance_history[agent_id][-100:]
        
        # Release resources
        self._release_resources(agent_id, task_id)
        
        logger.info(f"Released assignment {task_id} from agent {agent_id} (success: {success})")
    
    # Assignment algorithms
    
    async def _round_robin_assignment(self, task: TaskDefinition, constraints: Dict[str, Any]) -> List[AssignmentCandidate]:
        """Round-robin assignment algorithm"""
        available_agents = [aid for aid, info in self.agent_registry.items() 
                          if self._meets_basic_constraints(aid, info, task, constraints)]
        
        if not available_agents:
            return []
        
        # Select next agent in round-robin order
        agent_id = available_agents[self.round_robin_index % len(available_agents)]
        self.round_robin_index += 1
        
        agent_info = self.agent_registry[agent_id]
        candidate = self._create_assignment_candidate(agent_id, agent_info, task)
        
        return [candidate]
    
    async def _load_balanced_assignment(self, task: TaskDefinition, constraints: Dict[str, Any]) -> List[AssignmentCandidate]:
        """Load-balanced assignment algorithm"""
        candidates = []
        
        for agent_id, agent_info in self.agent_registry.items():
            if not self._meets_basic_constraints(agent_id, agent_info, task, constraints):
                continue
            
            candidate = self._create_assignment_candidate(agent_id, agent_info, task)
            candidates.append(candidate)
        
        # Sort by workload (ascending) and resource availability (descending)
        candidates.sort(key=lambda c: (c.workload_factor, -c.resource_availability))
        
        return candidates
    
    async def _capability_first_assignment(self, task: TaskDefinition, constraints: Dict[str, Any]) -> List[AssignmentCandidate]:
        """Capability-first assignment algorithm"""
        candidates = []
        
        for agent_id, agent_info in self.agent_registry.items():
            if not self._meets_basic_constraints(agent_id, agent_info, task, constraints):
                continue
            
            candidate = self._create_assignment_candidate(agent_id, agent_info, task)
            candidates.append(candidate)
        
        # Sort by capability match (descending)
        candidates.sort(key=lambda c: c.suitability_score, reverse=True)
        
        return candidates
    
    async def _performance_based_assignment(self, task: TaskDefinition, constraints: Dict[str, Any]) -> List[AssignmentCandidate]:
        """Performance-based assignment algorithm"""
        candidates = []
        
        for agent_id, agent_info in self.agent_registry.items():
            if not self._meets_basic_constraints(agent_id, agent_info, task, constraints):
                continue
            
            candidate = self._create_assignment_candidate(agent_id, agent_info, task)
            candidates.append(candidate)
        
        # Sort by performance score (descending)
        candidates.sort(key=lambda c: c.performance_score, reverse=True)
        
        return candidates
    
    async def _hybrid_assignment(self, task: TaskDefinition, constraints: Dict[str, Any]) -> List[AssignmentCandidate]:
        """Hybrid assignment algorithm combining multiple factors"""
        candidates = []
        
        for agent_id, agent_info in self.agent_registry.items():
            if not self._meets_basic_constraints(agent_id, agent_info, task, constraints):
                continue
            
            candidate = self._create_assignment_candidate(agent_id, agent_info, task)
            candidates.append(candidate)
        
        # Sort by overall score (descending)
        candidates.sort(key=lambda c: c.overall_score(), reverse=True)
        
        return candidates
    
    # Helper methods
    
    def _meets_basic_constraints(self, agent_id: str, agent_info: Dict[str, Any], task: TaskDefinition, constraints: Dict[str, Any]) -> bool:
        """Check if agent meets basic assignment constraints"""
        # Check if agent is available
        max_tasks = agent_info.get("max_concurrent_tasks", 3)
        current_tasks = len(agent_info.get("current_tasks", []))
        
        if current_tasks >= max_tasks:
            return False
        
        # Check required agent type
        required_type = constraints.get("required_agent_type")
        if required_type and agent_info.get("type") != required_type:
            return False
        
        # Check excluded agents
        excluded_agents = constraints.get("excluded_agents", [])
        if agent_id in excluded_agents:
            return False
        
        return True
    
    def _create_assignment_candidate(self, agent_id: str, agent_info: Dict[str, Any], task: TaskDefinition) -> AssignmentCandidate:
        """Create assignment candidate with all relevant scores"""
        # Calculate suitability score
        suitability_score = self._calculate_suitability_score(agent_info, task)
        
        # Calculate resource availability
        resource_availability = self._calculate_resource_availability(agent_id)
        
        # Calculate performance score
        performance_score = agent_info.get("average_performance", 1.0)
        
        # Calculate workload factor
        current_tasks = len(agent_info.get("current_tasks", []))
        max_tasks = agent_info.get("max_concurrent_tasks", 3)
        workload_factor = current_tasks / max_tasks
        
        # Calculate assignment cost (simplified)
        assignment_cost = 1.0  # Simplified cost calculation
        
        # Predict completion time
        predicted_time = self._predict_completion_time(agent_id, task)
        
        return AssignmentCandidate(
            agent_id=agent_id,
            agent_type=agent_info.get("type", AgentType.CODER),
            suitability_score=suitability_score,
            resource_availability=resource_availability,
            performance_score=performance_score,
            workload_factor=workload_factor,
            assignment_cost=assignment_cost,
            predicted_completion_time=predicted_time
        )
    
    def _calculate_suitability_score(self, agent_info: Dict[str, Any], task: TaskDefinition) -> float:
        """Calculate how suitable an agent is for a task"""
        score = 0.0
        
        # Agent type compatibility
        agent_type = agent_info.get("type", AgentType.CODER)
        task_type = task.requirements.get("type", "general")
        
        type_compatibility = {
            "architecture": [AgentType.ARCHITECT],
            "design": [AgentType.ARCHITECT],
            "coding": [AgentType.CODER],
            "implementation": [AgentType.CODER],
            "testing": [AgentType.TESTER],
            "debugging": [AgentType.CODER, AgentType.TESTER]
        }
        
        compatible_types = type_compatibility.get(task_type, [AgentType.CODER])
        if agent_type in compatible_types:
            score += 0.5
        else:
            score += 0.1
        
        # Capability matching
        capabilities = agent_info.get("capabilities", [])
        required_domain = task.requirements.get("domain", "general")
        
        for capability in capabilities:
            if isinstance(capability, dict):
                if capability.get("domain") == required_domain:
                    level = capability.get("level", 5)
                    score += (level / 10.0) * 0.5
                    break
        
        return min(score, 1.0)
    
    def _calculate_resource_availability(self, agent_id: str) -> float:
        """Calculate resource availability for an agent"""
        if agent_id not in self.agent_resources:
            return 0.0
        
        resources = self.agent_resources[agent_id]
        reservations = self.resource_reservations.get(agent_id, {})
        
        total_availability = 0.0
        resource_count = 0
        
        for resource_type, capacity in resources.items():
            reserved = reservations.get(resource_type, 0.0)
            available = max(0.0, capacity - reserved)
            availability = available / capacity if capacity > 0 else 0.0
            
            total_availability += availability
            resource_count += 1
        
        return total_availability / max(resource_count, 1)
    
    def _predict_completion_time(self, agent_id: str, task: TaskDefinition) -> float:
        """Predict task completion time for an agent"""
        # Simple prediction based on historical performance
        base_time = 3600.0  # 1 hour default
        
        if agent_id in self.performance_history:
            history = self.performance_history[agent_id]
            if history:
                avg_time = sum(h.get("execution_time", base_time) for h in history[-10:]) / min(len(history), 10)
                return avg_time
        
        return base_time
    
    def _allocate_resources(self, agent_id: str, task: TaskDefinition) -> Tuple[bool, Dict[str, float]]:
        """Allocate resources for a task"""
        if agent_id not in self.agent_resources:
            return False, {}
        
        # Simple resource allocation
        allocation = {
            "cpu": 0.1,  # 10% CPU
            "memory": 0.1,  # 10% memory
            "network": 0.05,  # 5% network
            "concurrent_tasks": 1  # 1 task slot
        }
        
        # Check availability
        resources = self.agent_resources[agent_id]
        reservations = self.resource_reservations.get(agent_id, {})
        
        for resource_type, required in allocation.items():
            capacity = resources.get(resource_type, 0.0)
            reserved = reservations.get(resource_type, 0.0)
            available = capacity - reserved
            
            if available < required:
                return False, {}
        
        # Make reservation
        if agent_id not in self.resource_reservations:
            self.resource_reservations[agent_id] = {}
        
        for resource_type, amount in allocation.items():
            current = self.resource_reservations[agent_id].get(resource_type, 0.0)
            self.resource_reservations[agent_id][resource_type] = current + amount
        
        return True, allocation
    
    def _release_resources(self, agent_id: str, task_id: str) -> None:
        """Release resources for a completed task"""
        # Find the allocation for this task and release it
        for assignment in reversed(self.assignment_history):
            if assignment["agent_id"] == agent_id and assignment["task_id"] == task_id:
                allocation = assignment.get("resource_allocation", {})
                
                if agent_id in self.resource_reservations:
                    for resource_type, amount in allocation.items():
                        current = self.resource_reservations[agent_id].get(resource_type, 0.0)
                        new_amount = max(0.0, current - amount)
                        
                        if new_amount == 0.0:
                            self.resource_reservations[agent_id].pop(resource_type, None)
                        else:
                            self.resource_reservations[agent_id][resource_type] = new_amount
                
                break
    
    def get_assignment_statistics(self) -> Dict[str, Any]:
        """Get assignment statistics"""
        total_assignments = len(self.assignment_history)
        successful_assignments = sum(1 for a in self.assignment_history if a.get("success", False))
        
        return {
            "total_assignments": total_assignments,
            "successful_assignments": successful_assignments,
            "success_rate": successful_assignments / max(total_assignments, 1),
            "active_agents": len(self.agent_registry),
            "assignment_strategy": self.assignment_strategy.value,
            "resource_utilization": self._calculate_global_resource_utilization()
        }
    
    def _calculate_global_resource_utilization(self) -> Dict[str, float]:
        """Calculate global resource utilization"""
        total_resources = {}
        total_reservations = {}
        
        for agent_id, resources in self.agent_resources.items():
            reservations = self.resource_reservations.get(agent_id, {})
            
            for resource_type, capacity in resources.items():
                total_resources[resource_type] = total_resources.get(resource_type, 0.0) + capacity
                total_reservations[resource_type] = total_reservations.get(resource_type, 0.0) + reservations.get(resource_type, 0.0)
        
        utilization = {}
        for resource_type, total in total_resources.items():
            used = total_reservations.get(resource_type, 0.0)
            utilization[resource_type] = (used / total) * 100 if total > 0 else 0.0
        
        return utilization