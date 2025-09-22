"""
Agent-specific interfaces and base classes for Claude-Flow

This module defines interfaces and abstract classes specific to the agent system,
including Queen Agents, Worker Agents, and Agent Managers.
"""

from abc import abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from ..core.interfaces import Agent, BaseConfig, ResourceLimits


class AgentType(Enum):
    """Types of agents in the system"""
    QUEEN = "queen"
    ARCHITECT = "architect"
    CODER = "coder"
    TESTER = "tester"
    RESEARCHER = "researcher"
    SECURITY = "security"
    DEVOPS = "devops"


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4
    EMERGENCY = 5


@dataclass
class TaskDefinition:
    """Definition of a task to be executed"""
    id: str
    description: str
    requirements: Dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    estimated_duration: Optional[int] = None  # seconds
    dependencies: List[str] = field(default_factory=list)
    assigned_agent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    """Result of task execution"""
    task_id: str
    agent_id: str
    success: bool
    result_data: Any = None
    error_message: Optional[str] = None
    execution_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentCapability:
    """Represents an agent's capability"""
    name: str
    level: int  # 1-10 scale
    domain: str
    description: str = ""


@dataclass
class AgentConfig(BaseConfig):
    """Configuration specific to agents"""
    agent_type: AgentType = AgentType.CODER
    capabilities: List[AgentCapability] = field(default_factory=list)
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)
    specialization: Optional[str] = None
    max_concurrent_tasks: int = 3


class QueenAgentInterface(Agent):
    """Interface for Queen Agents - master coordinators"""
    
    @abstractmethod
    async def coordinate_task(self, task: TaskDefinition) -> TaskResult:
        """Coordinate execution of a complex task"""
        pass
    
    @abstractmethod
    async def assign_task(self, task: TaskDefinition, agent_id: str) -> bool:
        """Assign a task to a specific agent"""
        pass
    
    @abstractmethod
    async def recruit_agents(self, requirements: Dict[str, Any]) -> List[str]:
        """Recruit agents based on requirements"""
        pass
    
    @abstractmethod
    async def resolve_conflict(self, agents: List[str], issue: str) -> Dict[str, Any]:
        """Resolve conflicts between agents"""
        pass
    
    @abstractmethod
    async def monitor_swarm(self) -> Dict[str, Any]:
        """Monitor the health and performance of the swarm"""
        pass


class WorkerAgentInterface(Agent):
    """Interface for Worker Agents - specialized task executors"""
    
    @abstractmethod
    async def assess_task_fit(self, task: TaskDefinition) -> float:
        """Assess how well this agent can handle a task (0.0-1.0)"""
        pass
    
    @abstractmethod
    async def estimate_effort(self, task: TaskDefinition) -> int:
        """Estimate effort required for a task in seconds"""
        pass
    
    @abstractmethod
    async def report_progress(self, task_id: str, progress: float) -> None:
        """Report progress on current task (0.0-1.0)"""
        pass
    
    @abstractmethod
    async def request_help(self, task_id: str, assistance_type: str) -> None:
        """Request help from other agents"""
        pass
    
    @abstractmethod
    async def learn_from_task(self, task: TaskDefinition, result: TaskResult) -> None:
        """Learn from completed task to improve future performance"""
        pass


class AgentManagerInterface:
    """Interface for Agent Managers - lifecycle and resource management"""
    
    @abstractmethod
    async def spawn_agent(self, config: AgentConfig) -> str:
        """Spawn a new agent with given configuration"""
        pass
    
    @abstractmethod
    async def terminate_agent(self, agent_id: str) -> bool:
        """Terminate an agent"""
        pass
    
    @abstractmethod
    async def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Get status information for an agent"""
        pass
    
    @abstractmethod
    async def list_agents(self, agent_type: Optional[AgentType] = None) -> List[Dict[str, Any]]:
        """List all agents, optionally filtered by type"""
        pass
    
    @abstractmethod
    async def allocate_resources(self, agent_id: str, resources: ResourceLimits) -> bool:
        """Allocate resources to an agent"""
        pass
    
    @abstractmethod
    async def monitor_resources(self) -> Dict[str, Any]:
        """Monitor resource usage across all agents"""
        pass


class SpecializedAgentInterface(WorkerAgentInterface):
    """Base interface for specialized worker agents"""
    
    @abstractmethod
    async def get_specialization_info(self) -> Dict[str, Any]:
        """Get information about this agent's specialization"""
        pass
    
    @abstractmethod
    async def validate_task_compatibility(self, task: TaskDefinition) -> bool:
        """Validate if task is compatible with agent's specialization"""
        pass


class ArchitectAgentInterface(SpecializedAgentInterface):
    """Interface for Architect Agents - system design and planning"""
    
    @abstractmethod
    async def design_system(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Design system architecture based on requirements"""
        pass
    
    @abstractmethod
    async def review_architecture(self, design: Dict[str, Any]) -> Dict[str, Any]:
        """Review and provide feedback on system architecture"""
        pass
    
    @abstractmethod
    async def plan_implementation(self, design: Dict[str, Any]) -> List[TaskDefinition]:
        """Create implementation plan from design"""
        pass


class CoderAgentInterface(SpecializedAgentInterface):
    """Interface for Coder Agents - code generation and implementation"""
    
    @abstractmethod
    async def generate_code(self, specification: Dict[str, Any]) -> str:
        """Generate code based on specification"""
        pass
    
    @abstractmethod
    async def refactor_code(self, code: str, improvements: List[str]) -> str:
        """Refactor existing code with improvements"""
        pass
    
    @abstractmethod
    async def debug_code(self, code: str, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """Debug code and provide fix suggestions"""
        pass


class TesterAgentInterface(SpecializedAgentInterface):
    """Interface for Tester Agents - quality assurance and validation"""
    
    @abstractmethod
    async def generate_tests(self, code: str, test_type: str) -> List[str]:
        """Generate tests for given code"""
        pass
    
    @abstractmethod
    async def execute_tests(self, tests: List[str]) -> Dict[str, Any]:
        """Execute tests and return results"""
        pass
    
    @abstractmethod
    async def validate_quality(self, artifact: Any) -> Dict[str, Any]:
        """Validate quality of an artifact"""
        pass


class ResearcherAgentInterface(SpecializedAgentInterface):
    """Interface for Researcher Agents - information gathering and analysis"""
    
    @abstractmethod
    async def research_topic(self, topic: str, scope: Dict[str, Any]) -> Dict[str, Any]:
        """Research a specific topic within given scope"""
        pass
    
    @abstractmethod
    async def analyze_requirements(self, requirements: List[str]) -> Dict[str, Any]:
        """Analyze and clarify requirements"""
        pass
    
    @abstractmethod
    async def gather_information(self, sources: List[str]) -> Dict[str, Any]:
        """Gather information from specified sources"""
        pass


class SecurityAgentInterface(SpecializedAgentInterface):
    """Interface for Security Agents - security scanning and compliance"""
    
    @abstractmethod
    async def scan_vulnerabilities(self, target: Any) -> Dict[str, Any]:
        """Scan for security vulnerabilities"""
        pass
    
    @abstractmethod
    async def check_compliance(self, artifact: Any, standards: List[str]) -> Dict[str, Any]:
        """Check compliance with security standards"""
        pass
    
    @abstractmethod
    async def recommend_fixes(self, vulnerabilities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Recommend fixes for identified vulnerabilities"""
        pass


class DevOpsAgentInterface(SpecializedAgentInterface):
    """Interface for DevOps Agents - deployment and infrastructure"""
    
    @abstractmethod
    async def deploy_application(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy application with given configuration"""
        pass
    
    @abstractmethod
    async def manage_infrastructure(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Manage infrastructure operations"""
        pass
    
    @abstractmethod
    async def monitor_deployment(self, deployment_id: str) -> Dict[str, Any]:
        """Monitor deployment status and health"""
        pass