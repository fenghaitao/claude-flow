"""
Integration interfaces for Claude-Flow

This module defines interfaces for external service integrations including
MCP protocol, Claude AI, GitHub, and other external services.
"""

from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable
from ..core.interfaces import Integration, BaseComponent


class MCPToolCategory(Enum):
    """Categories of MCP tools"""
    SWARM = "swarm"
    NEURAL = "neural"
    MEMORY = "memory"
    PERFORMANCE = "performance"
    WORKFLOW = "workflow"
    GITHUB = "github"
    DAA = "daa"
    SYSTEM = "system"


class IntegrationStatus(Enum):
    """Status of integrations"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"


@dataclass
class MCPTool:
    """Represents an MCP tool"""
    id: str
    name: str
    description: str
    category: MCPToolCategory
    parameters: Dict[str, Any] = field(default_factory=dict)
    required_permissions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPToolResult:
    """Result of MCP tool execution"""
    tool_id: str
    success: bool
    result_data: Any = None
    error_message: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPServer:
    """Represents an MCP server"""
    id: str
    name: str
    url: str
    protocol: str = "websocket"
    authentication: Dict[str, Any] = field(default_factory=dict)
    available_tools: List[MCPTool] = field(default_factory=list)
    status: IntegrationStatus = IntegrationStatus.DISCONNECTED
    metadata: Dict[str, Any] = field(default_factory=dict)


class MCPClientInterface(BaseComponent):
    """Interface for MCP (Model Context Protocol) client"""
    
    @abstractmethod
    async def connect_to_server(self, server_config: MCPServer) -> bool:
        """Connect to an MCP server"""
        pass
    
    @abstractmethod
    async def disconnect_from_server(self, server_id: str) -> bool:
        """Disconnect from an MCP server"""
        pass
    
    @abstractmethod
    async def discover_tools(self, server_id: str) -> List[MCPTool]:
        """Discover available tools on a server"""
        pass
    
    @abstractmethod
    async def execute_tool(self, server_id: str, tool_id: str, 
                         parameters: Dict[str, Any]) -> MCPToolResult:
        """Execute a tool on a server"""
        pass
    
    @abstractmethod
    async def list_servers(self) -> List[MCPServer]:
        """List all connected servers"""
        pass
    
    @abstractmethod
    async def get_server_status(self, server_id: str) -> Dict[str, Any]:
        """Get status of a specific server"""
        pass
    
    @abstractmethod
    async def register_tool_handler(self, tool_id: str, 
                                  handler: Callable[[Dict[str, Any]], Any]) -> bool:
        """Register a custom handler for a tool"""
        pass


class ClaudeClientInterface(Integration):
    """Interface for Claude AI integration"""
    
    @abstractmethod
    async def send_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Send a message to Claude and get response"""
        pass
    
    @abstractmethod
    async def send_conversation(self, messages: List[Dict[str, str]]) -> str:
        """Send a conversation to Claude"""
        pass
    
    @abstractmethod
    async def analyze_code(self, code: str, analysis_type: str) -> Dict[str, Any]:
        """Have Claude analyze code"""
        pass
    
    @abstractmethod
    async def generate_code(self, specification: Dict[str, Any]) -> str:
        """Have Claude generate code from specification"""
        pass
    
    @abstractmethod
    async def review_design(self, design: Dict[str, Any]) -> Dict[str, Any]:
        """Have Claude review a system design"""
        pass
    
    @abstractmethod
    async def get_usage_stats(self) -> Dict[str, Any]:
        """Get API usage statistics"""
        pass


class GitHubClientInterface(Integration):
    """Interface for GitHub integration"""
    
    @abstractmethod
    async def clone_repository(self, repo_url: str, local_path: str) -> bool:
        """Clone a repository"""
        pass
    
    @abstractmethod
    async def create_branch(self, repo_path: str, branch_name: str) -> bool:
        """Create a new branch"""
        pass
    
    @abstractmethod
    async def commit_changes(self, repo_path: str, message: str, 
                           files: Optional[List[str]] = None) -> str:
        """Commit changes to repository"""
        pass
    
    @abstractmethod
    async def create_pull_request(self, repo_path: str, title: str, 
                                description: str, source_branch: str, 
                                target_branch: str = "main") -> str:
        """Create a pull request"""
        pass
    
    @abstractmethod
    async def get_repository_info(self, repo_url: str) -> Dict[str, Any]:
        """Get repository information"""
        pass
    
    @abstractmethod
    async def list_issues(self, repo_url: str, state: str = "open") -> List[Dict[str, Any]]:
        """List repository issues"""
        pass
    
    @abstractmethod
    async def create_issue(self, repo_url: str, title: str, 
                         description: str, labels: Optional[List[str]] = None) -> str:
        """Create a new issue"""
        pass


class DockerClientInterface(Integration):
    """Interface for Docker integration"""
    
    @abstractmethod
    async def build_image(self, dockerfile_path: str, image_name: str, 
                        build_args: Optional[Dict[str, str]] = None) -> bool:
        """Build a Docker image"""
        pass
    
    @abstractmethod
    async def run_container(self, image_name: str, container_name: str,
                          environment: Optional[Dict[str, str]] = None,
                          ports: Optional[Dict[str, str]] = None) -> str:
        """Run a Docker container"""
        pass
    
    @abstractmethod
    async def stop_container(self, container_id: str) -> bool:
        """Stop a running container"""
        pass
    
    @abstractmethod
    async def list_containers(self, all_containers: bool = False) -> List[Dict[str, Any]]:
        """List Docker containers"""
        pass
    
    @abstractmethod
    async def get_container_logs(self, container_id: str, lines: int = 100) -> str:
        """Get container logs"""
        pass
    
    @abstractmethod
    async def push_image(self, image_name: str, registry: Optional[str] = None) -> bool:
        """Push image to registry"""
        pass


class ConnectionPoolInterface:
    """Interface for connection pooling"""
    
    @abstractmethod
    async def acquire_connection(self, service_type: str) -> Any:
        """Acquire a connection from the pool"""
        pass
    
    @abstractmethod
    async def release_connection(self, connection: Any, service_type: str) -> None:
        """Release a connection back to the pool"""
        pass
    
    @abstractmethod
    async def get_pool_stats(self, service_type: str) -> Dict[str, Any]:
        """Get connection pool statistics"""
        pass
    
    @abstractmethod
    async def close_all_connections(self, service_type: Optional[str] = None) -> None:
        """Close all connections in pool(s)"""
        pass


class RateLimiterInterface:
    """Interface for rate limiting"""
    
    @abstractmethod
    async def check_limit(self, operation: str, identifier: str) -> bool:
        """Check if operation is within rate limits"""
        pass
    
    @abstractmethod
    async def record_operation(self, operation: str, identifier: str) -> None:
        """Record an operation for rate limiting"""
        pass
    
    @abstractmethod
    async def get_remaining_quota(self, operation: str, identifier: str) -> int:
        """Get remaining quota for operation"""
        pass
    
    @abstractmethod
    async def reset_quota(self, operation: str, identifier: str) -> None:
        """Reset quota for operation"""
        pass


class RetryManagerInterface:
    """Interface for retry logic management"""
    
    @abstractmethod
    async def execute_with_retry(self, operation: Callable, max_retries: int = 3,
                               backoff_factor: float = 2.0) -> Any:
        """Execute operation with retry logic"""
        pass
    
    @abstractmethod
    async def get_retry_stats(self, operation_name: str) -> Dict[str, Any]:
        """Get retry statistics for an operation"""
        pass


class CacheManagerInterface:
    """Interface for response caching"""
    
    @abstractmethod
    async def get_cached_response(self, key: str) -> Optional[Any]:
        """Get cached response"""
        pass
    
    @abstractmethod
    async def cache_response(self, key: str, response: Any, ttl: int = 3600) -> bool:
        """Cache a response"""
        pass
    
    @abstractmethod
    async def invalidate_cache(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern"""
        pass
    
    @abstractmethod
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        pass


class IntegrationManagerInterface(BaseComponent):
    """Interface for managing all integrations"""
    
    @abstractmethod
    async def register_integration(self, integration_type: str, 
                                 integration: Integration) -> bool:
        """Register an integration"""
        pass
    
    @abstractmethod
    async def get_integration(self, integration_type: str) -> Optional[Integration]:
        """Get an integration by type"""
        pass
    
    @abstractmethod
    async def list_integrations(self) -> Dict[str, IntegrationStatus]:
        """List all integrations and their status"""
        pass
    
    @abstractmethod
    async def test_all_integrations(self) -> Dict[str, bool]:
        """Test all registered integrations"""
        pass
    
    @abstractmethod
    async def reload_integration(self, integration_type: str) -> bool:
        """Reload a specific integration"""
        pass


class WebhookManagerInterface:
    """Interface for webhook management"""
    
    @abstractmethod
    async def register_webhook(self, event_type: str, url: str, 
                             secret: Optional[str] = None) -> str:
        """Register a webhook, return webhook ID"""
        pass
    
    @abstractmethod
    async def trigger_webhook(self, webhook_id: str, data: Dict[str, Any]) -> bool:
        """Trigger a webhook with data"""
        pass
    
    @abstractmethod
    async def list_webhooks(self) -> List[Dict[str, Any]]:
        """List all registered webhooks"""
        pass
    
    @abstractmethod
    async def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook"""
        pass


class APIGatewayInterface(BaseComponent):
    """Interface for API gateway functionality"""
    
    @abstractmethod
    async def route_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Route incoming request to appropriate service"""
        pass
    
    @abstractmethod
    async def authenticate_request(self, request: Dict[str, Any]) -> bool:
        """Authenticate incoming request"""
        pass
    
    @abstractmethod
    async def log_request(self, request: Dict[str, Any], response: Dict[str, Any]) -> None:
        """Log request and response"""
        pass
    
    @abstractmethod
    async def get_api_stats(self) -> Dict[str, Any]:
        """Get API usage statistics"""
        pass