"""
Base interfaces and abstract classes for Claude-Flow

This module defines the core interfaces that all major components implement,
ensuring consistent behavior and enabling dependency injection.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Union
import uuid


class Status(Enum):
    """Common status enumeration for all components"""
    PENDING = "pending"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass
class BaseConfig:
    """Base configuration class for all components"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourceLimits:
    """Resource limits for components"""
    max_cpu_percent: float = 80.0
    max_memory_mb: int = 512
    max_concurrent_tasks: int = 10
    timeout_seconds: int = 300


class Identifiable(Protocol):
    """Protocol for objects that have an ID"""
    @property
    def id(self) -> str:
        ...


class Configurable(Protocol):
    """Protocol for objects that can be configured"""
    @property
    def config(self) -> BaseConfig:
        ...
    
    async def configure(self, config: BaseConfig) -> None:
        ...


class Lifecycle(Protocol):
    """Protocol for objects with lifecycle management"""
    @property
    def status(self) -> Status:
        ...
    
    async def start(self) -> None:
        ...
    
    async def stop(self) -> None:
        ...
    
    async def restart(self) -> None:
        ...


class HealthCheckable(Protocol):
    """Protocol for objects that can report health status"""
    async def health_check(self) -> Dict[str, Any]:
        ...


class Monitorable(Protocol):
    """Protocol for objects that can be monitored"""
    async def get_metrics(self) -> Dict[str, Union[int, float, str]]:
        ...


class BaseComponent(ABC, Identifiable, Configurable, Lifecycle, HealthCheckable):
    """Abstract base class for all major Claude-Flow components"""
    
    def __init__(self, config: Optional[BaseConfig] = None):
        self._config = config or BaseConfig()
        self._status = Status.PENDING
        self._created_at = datetime.now()
        self._last_health_check: Optional[datetime] = None
        
    @property
    def id(self) -> str:
        return self._config.id
    
    @property
    def config(self) -> BaseConfig:
        return self._config
        
    @property
    def status(self) -> Status:
        return self._status
    
    async def configure(self, config: BaseConfig) -> None:
        """Configure the component"""
        self._config = config
        
    async def start(self) -> None:
        """Start the component"""
        self._status = Status.INITIALIZING
        await self._start_implementation()
        self._status = Status.RUNNING
        
    async def stop(self) -> None:
        """Stop the component"""
        self._status = Status.STOPPING
        await self._stop_implementation()
        self._status = Status.STOPPED
        
    async def restart(self) -> None:
        """Restart the component"""
        if self._status == Status.RUNNING:
            await self.stop()
        await self.start()
        
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        self._last_health_check = datetime.now()
        base_health = {
            "component_id": self.id,
            "component_name": self._config.name,
            "status": self._status.value,
            "uptime_seconds": (datetime.now() - self._created_at).total_seconds(),
            "last_health_check": self._last_health_check.isoformat(),
            "healthy": self._status in [Status.RUNNING, Status.PENDING]
        }
        
        # Add component-specific health data
        specific_health = await self._health_check_implementation()
        return {**base_health, **specific_health}
    
    @abstractmethod
    async def _start_implementation(self) -> None:
        """Component-specific start logic"""
        pass
    
    @abstractmethod
    async def _stop_implementation(self) -> None:
        """Component-specific stop logic"""
        pass
    
    @abstractmethod
    async def _health_check_implementation(self) -> Dict[str, Any]:
        """Component-specific health check logic"""
        pass


class TaskExecutor(Protocol):
    """Protocol for components that can execute tasks"""
    async def execute_task(self, task: Any) -> Any:
        ...


class EventEmitter(Protocol):
    """Protocol for components that emit events"""
    async def emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        ...


class Agent(BaseComponent, TaskExecutor, EventEmitter, Monitorable):
    """Base class for all agent types"""
    
    def __init__(self, config: Optional[BaseConfig] = None):
        super().__init__(config)
        self._current_task: Optional[Any] = None
        self._task_history: List[Any] = []
        self._resource_limits = ResourceLimits()
    
    @property
    def current_task(self) -> Optional[Any]:
        return self._current_task
    
    @property
    def is_busy(self) -> bool:
        return self._current_task is not None
    
    @abstractmethod
    async def execute_task(self, task: Any) -> Any:
        """Execute a specific task"""
        pass
    
    @abstractmethod
    async def emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit an event"""
        pass
    
    @abstractmethod
    async def get_metrics(self) -> Dict[str, Union[int, float, str]]:
        """Get performance metrics"""
        pass


class Repository(Protocol):
    """Protocol for data repository classes"""
    async def create(self, entity: Any) -> Any:
        ...
    
    async def read(self, entity_id: str) -> Optional[Any]:
        ...
    
    async def update(self, entity: Any) -> Any:
        ...
    
    async def delete(self, entity_id: str) -> bool:
        ...
    
    async def list(self, filters: Optional[Dict[str, Any]] = None) -> List[Any]:
        ...


class Backend(BaseComponent):
    """Base class for storage backends"""
    
    @abstractmethod
    async def connect(self) -> None:
        """Connect to the backend"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the backend"""
        pass
    
    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if connected to the backend"""
        pass


class Integration(BaseComponent):
    """Base class for external service integrations"""
    
    @abstractmethod
    async def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """Authenticate with the external service"""
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test connection to the external service"""
        pass


# Type aliases for common patterns
ComponentId = str
TaskId = str
SessionId = str
AgentId = str

# Common exceptions
class ClaudeFlowError(Exception):
    """Base exception for Claude-Flow"""
    pass


class ComponentError(ClaudeFlowError):
    """Exception for component-related errors"""
    def __init__(self, component_id: str, message: str):
        self.component_id = component_id
        super().__init__(f"Component {component_id}: {message}")


class ConfigurationError(ClaudeFlowError):
    """Exception for configuration-related errors"""
    pass


class ValidationError(ClaudeFlowError):
    """Exception for validation errors"""
    pass


class ResourceExhaustedError(ClaudeFlowError):
    """Exception when resources are exhausted"""
    pass