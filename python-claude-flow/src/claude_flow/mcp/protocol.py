"""
MCP protocol core definitions and message types.
"""

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from claude_flow.core.interfaces import BaseComponent


class MCPMessageType(str, Enum):
    """MCP message types following the protocol specification."""
    
    # Connection lifecycle
    INITIALIZE = "initialize"
    INITIALIZED = "initialized"
    SHUTDOWN = "shutdown"
    
    # Tool operations
    TOOLS_LIST = "tools/list"
    TOOLS_CALL = "tools/call"
    
    # Resource operations
    RESOURCES_LIST = "resources/list"
    RESOURCES_READ = "resources/read"
    RESOURCES_SUBSCRIBE = "resources/subscribe"
    RESOURCES_UNSUBSCRIBE = "resources/unsubscribe"
    
    # Prompt operations
    PROMPTS_LIST = "prompts/list"
    PROMPTS_GET = "prompts/get"
    
    # Logging
    LOGGING_SET_LEVEL = "logging/setLevel"
    
    # Notifications
    NOTIFICATION = "notification"
    PROGRESS = "progress"
    
    # Error responses
    ERROR = "error"


class MCPErrorCode(int, Enum):
    """Standard MCP error codes."""
    
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    
    # MCP-specific errors
    TOOL_NOT_FOUND = -32000
    TOOL_EXECUTION_ERROR = -32001
    RESOURCE_NOT_FOUND = -32002
    PROMPT_NOT_FOUND = -32003
    UNAUTHORIZED = -32004


@dataclass
class MCPMessage:
    """Base MCP message structure."""
    
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.id is None and self.method:
            self.id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        data = {"jsonrpc": self.jsonrpc}
        
        if self.id is not None:
            data["id"] = self.id
        if self.method:
            data["method"] = self.method
        if self.params is not None:
            data["params"] = self.params
        if self.result is not None:
            data["result"] = self.result
        if self.error is not None:
            data["error"] = self.error
            
        return data
    
    def to_json(self) -> str:
        """Convert message to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPMessage":
        """Create message from dictionary."""
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            id=data.get("id"),
            method=data.get("method"),
            params=data.get("params"),
            result=data.get("result"),
            error=data.get("error")
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "MCPMessage":
        """Create message from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class MCPTool:
    """MCP tool definition."""
    
    name: str
    description: str
    input_schema: Dict[str, Any]
    category: Optional[str] = None
    version: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tool to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "category": self.category,
            "version": self.version
        }


@dataclass
class MCPResource:
    """MCP resource definition."""
    
    uri: str
    name: str
    description: Optional[str] = None
    mime_type: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert resource to dictionary."""
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type
        }


@dataclass
class MCPPrompt:
    """MCP prompt template definition."""
    
    name: str
    description: str
    arguments: Optional[List[Dict[str, Any]]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert prompt to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "arguments": self.arguments or []
        }


class MCPProtocol(BaseComponent):
    """
    Core MCP protocol implementation with message handling.
    """
    
    def __init__(self, name: str = "mcp_protocol"):
        super().__init__(name)
        self.session_id: Optional[str] = None
        self.capabilities: Dict[str, Any] = {}
        self.tools: Dict[str, MCPTool] = {}
        self.resources: Dict[str, MCPResource] = {}
        self.prompts: Dict[str, MCPPrompt] = {}
        
    async def initialize(self, capabilities: Dict[str, Any]) -> None:
        """Initialize MCP session with capabilities."""
        self.session_id = str(uuid.uuid4())
        self.capabilities = capabilities
        await self.logger.info(f"MCP protocol initialized with session {self.session_id}")
    
    def create_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> MCPMessage:
        """Create a request message."""
        return MCPMessage(
            method=method,
            params=params
        )
    
    def create_response(self, request_id: Union[str, int], result: Any) -> MCPMessage:
        """Create a response message."""
        return MCPMessage(
            id=request_id,
            result=result
        )
    
    def create_error(self, request_id: Union[str, int], code: MCPErrorCode, 
                    message: str, data: Optional[Any] = None) -> MCPMessage:
        """Create an error response."""
        error = {
            "code": code.value,
            "message": message
        }
        if data is not None:
            error["data"] = data
            
        return MCPMessage(
            id=request_id,
            error=error
        )
    
    def create_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> MCPMessage:
        """Create a notification message (no response expected)."""
        return MCPMessage(
            method=method,
            params=params
        )
    
    async def handle_message(self, message: MCPMessage) -> Optional[MCPMessage]:
        """
        Handle incoming MCP message and return response if needed.
        """
        try:
            if not message.method:
                if message.id:
                    return self.create_error(
                        message.id, 
                        MCPErrorCode.INVALID_REQUEST,
                        "Missing method in request"
                    )
                return None
            
            # Handle different message types
            if message.method == MCPMessageType.INITIALIZE:
                return await self._handle_initialize(message)
            elif message.method == MCPMessageType.TOOLS_LIST:
                return await self._handle_tools_list(message)
            elif message.method == MCPMessageType.TOOLS_CALL:
                return await self._handle_tools_call(message)
            elif message.method == MCPMessageType.RESOURCES_LIST:
                return await self._handle_resources_list(message)
            elif message.method == MCPMessageType.RESOURCES_READ:
                return await self._handle_resources_read(message)
            elif message.method == MCPMessageType.PROMPTS_LIST:
                return await self._handle_prompts_list(message)
            elif message.method == MCPMessageType.PROMPTS_GET:
                return await self._handle_prompts_get(message)
            else:
                if message.id:
                    return self.create_error(
                        message.id,
                        MCPErrorCode.METHOD_NOT_FOUND,
                        f"Method not found: {message.method}"
                    )
                return None
                
        except Exception as e:
            await self.logger.error(f"Error handling message: {e}")
            if message.id:
                return self.create_error(
                    message.id,
                    MCPErrorCode.INTERNAL_ERROR,
                    str(e)
                )
            return None
    
    async def _handle_initialize(self, message: MCPMessage) -> MCPMessage:
        """Handle initialize request."""
        params = message.params or {}
        client_capabilities = params.get("capabilities", {})
        
        # Initialize with client capabilities
        await self.initialize(client_capabilities)
        
        # Return server capabilities
        server_capabilities = {
            "tools": {"listChanged": True},
            "resources": {"subscribe": True, "listChanged": True},
            "prompts": {"listChanged": True},
            "logging": {}
        }
        
        return self.create_response(message.id, {
            "protocolVersion": "2024-11-05",
            "capabilities": server_capabilities,
            "serverInfo": {
                "name": "claude-flow-mcp",
                "version": "1.0.0"
            }
        })
    
    async def _handle_tools_list(self, message: MCPMessage) -> MCPMessage:
        """Handle tools list request."""
        tools_list = [tool.to_dict() for tool in self.tools.values()]
        return self.create_response(message.id, {"tools": tools_list})
    
    async def _handle_tools_call(self, message: MCPMessage) -> MCPMessage:
        """Handle tool call request."""
        params = message.params or {}
        tool_name = params.get("name")
        tool_arguments = params.get("arguments", {})
        
        if not tool_name:
            return self.create_error(
                message.id,
                MCPErrorCode.INVALID_PARAMS,
                "Missing tool name"
            )
        
        if tool_name not in self.tools:
            return self.create_error(
                message.id,
                MCPErrorCode.TOOL_NOT_FOUND,
                f"Tool not found: {tool_name}"
            )
        
        try:
            # Tool execution will be handled by the tool registry
            result = await self._execute_tool(tool_name, tool_arguments)
            return self.create_response(message.id, result)
        except Exception as e:
            return self.create_error(
                message.id,
                MCPErrorCode.TOOL_EXECUTION_ERROR,
                f"Tool execution failed: {str(e)}"
            )
    
    async def _handle_resources_list(self, message: MCPMessage) -> MCPMessage:
        """Handle resources list request."""
        resources_list = [resource.to_dict() for resource in self.resources.values()]
        return self.create_response(message.id, {"resources": resources_list})
    
    async def _handle_resources_read(self, message: MCPMessage) -> MCPMessage:
        """Handle resource read request."""
        params = message.params or {}
        resource_uri = params.get("uri")
        
        if not resource_uri:
            return self.create_error(
                message.id,
                MCPErrorCode.INVALID_PARAMS,
                "Missing resource URI"
            )
        
        if resource_uri not in self.resources:
            return self.create_error(
                message.id,
                MCPErrorCode.RESOURCE_NOT_FOUND,
                f"Resource not found: {resource_uri}"
            )
        
        try:
            # Resource reading will be implemented by specific handlers
            content = await self._read_resource(resource_uri)
            return self.create_response(message.id, {"contents": [content]})
        except Exception as e:
            return self.create_error(
                message.id,
                MCPErrorCode.INTERNAL_ERROR,
                f"Failed to read resource: {str(e)}"
            )
    
    async def _handle_prompts_list(self, message: MCPMessage) -> MCPMessage:
        """Handle prompts list request."""
        prompts_list = [prompt.to_dict() for prompt in self.prompts.values()]
        return self.create_response(message.id, {"prompts": prompts_list})
    
    async def _handle_prompts_get(self, message: MCPMessage) -> MCPMessage:
        """Handle prompt get request."""
        params = message.params or {}
        prompt_name = params.get("name")
        prompt_arguments = params.get("arguments", {})
        
        if not prompt_name:
            return self.create_error(
                message.id,
                MCPErrorCode.INVALID_PARAMS,
                "Missing prompt name"
            )
        
        if prompt_name not in self.prompts:
            return self.create_error(
                message.id,
                MCPErrorCode.PROMPT_NOT_FOUND,
                f"Prompt not found: {prompt_name}"
            )
        
        try:
            # Prompt execution will be handled by prompt handlers
            result = await self._execute_prompt(prompt_name, prompt_arguments)
            return self.create_response(message.id, result)
        except Exception as e:
            return self.create_error(
                message.id,
                MCPErrorCode.INTERNAL_ERROR,
                f"Failed to execute prompt: {str(e)}"
            )
    
    async def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool (to be implemented by tool registry)."""
        raise NotImplementedError("Tool execution must be implemented by tool registry")
    
    async def _read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource (to be implemented by resource handlers)."""
        raise NotImplementedError("Resource reading must be implemented by resource handlers")
    
    async def _execute_prompt(self, prompt_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a prompt (to be implemented by prompt handlers)."""
        raise NotImplementedError("Prompt execution must be implemented by prompt handlers")
    
    def register_tool(self, tool: MCPTool) -> None:
        """Register a tool with the protocol."""
        self.tools[tool.name] = tool
    
    def register_resource(self, resource: MCPResource) -> None:
        """Register a resource with the protocol."""
        self.resources[resource.uri] = resource
    
    def register_prompt(self, prompt: MCPPrompt) -> None:
        """Register a prompt with the protocol."""
        self.prompts[prompt.name] = prompt