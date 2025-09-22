"""
MCP Server implementation with tool registration and management.
"""

import asyncio
from typing import Any, Dict, List, Optional, Callable
from claude_flow.core.interfaces import BaseComponent
from .protocol import MCPProtocol, MCPTool, MCPResource, MCPPrompt
from .transport import MCPWebSocketServer
from .tools import ToolRegistry


class MCPServer(BaseComponent):
    """
    MCP Server that manages tools, resources, and prompts.
    """
    
    def __init__(self, name: str = "mcp_server", host: str = "localhost", port: int = 8765):
        super().__init__(name)
        self.host = host
        self.port = port
        self.protocol = MCPProtocol("mcp_server_protocol")
        self.transport = MCPWebSocketServer("mcp_server_transport")
        self.tool_registry = ToolRegistry("mcp_tool_registry")
        self.is_running = False
        self.resource_handlers: Dict[str, Callable] = {}
        self.prompt_handlers: Dict[str, Callable] = {}
    
    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize MCP server."""
        capabilities = {
            "tools": {"listChanged": True},
            "resources": {"subscribe": True, "listChanged": True},
            "prompts": {"listChanged": True},
            "logging": {}
        }
        
        await self.protocol.initialize(capabilities)
        await self.transport.initialize(self.protocol)
        await self.tool_registry.initialize()
        
        # Connect handlers
        self.protocol._execute_tool = self.tool_registry.execute_tool
        self.protocol._read_resource = self._handle_resource_read
        self.protocol._execute_prompt = self._handle_prompt_execution
        
        await self.logger.info("MCP server initialized")
    
    async def start(self) -> None:
        """Start the MCP server."""
        if self.is_running:
            return
        
        await self.transport.start(self.host, self.port)
        self.is_running = True
        await self.logger.info(f"MCP server started on {self.host}:{self.port}")
    
    async def stop(self) -> None:
        """Stop the MCP server."""
        if not self.is_running:
            return
        
        await self.transport.stop()
        self.is_running = False
        await self.logger.info("MCP server stopped")
    
    async def register_tool(self, tool: MCPTool, handler: Callable) -> None:
        """Register a tool with handler."""
        self.protocol.register_tool(tool)
        await self.tool_registry.register_tool(tool.name, handler, tool.input_schema)
        await self.logger.info(f"Registered tool: {tool.name}")
        
        # Notify clients
        if self.is_running:
            await self.transport.broadcast_notification(
                "notifications/tools/listChanged",
                {"tools": [t.to_dict() for t in self.protocol.tools.values()]}
            )
    
    async def register_resource(self, resource: MCPResource, handler: Callable) -> None:
        """Register a resource with handler."""
        self.protocol.register_resource(resource)
        self.resource_handlers[resource.uri] = handler
        await self.logger.info(f"Registered resource: {resource.uri}")
    
    async def register_prompt(self, prompt: MCPPrompt, handler: Callable) -> None:
        """Register a prompt with handler."""
        self.protocol.register_prompt(prompt)
        self.prompt_handlers[prompt.name] = handler
        await self.logger.info(f"Registered prompt: {prompt.name}")
    
    async def _handle_resource_read(self, uri: str) -> Dict[str, Any]:
        """Handle resource read."""
        if uri not in self.resource_handlers:
            raise ValueError(f"No handler for resource: {uri}")
        
        handler = self.resource_handlers[uri]
        content = await handler(uri)
        return {"uri": uri, "mimeType": "text/plain", "text": content}
    
    async def _handle_prompt_execution(self, prompt_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompt execution."""
        if prompt_name not in self.prompt_handlers:
            raise ValueError(f"No handler for prompt: {prompt_name}")
        
        handler = self.prompt_handlers[prompt_name]
        result = await handler(prompt_name, arguments)
        return {"description": f"Executed prompt: {prompt_name}", "messages": result}
    
    async def get_server_info(self) -> Dict[str, Any]:
        """Get server information."""
        return {
            "name": "claude-flow-mcp-server",
            "version": "1.0.0",
            "host": self.host,
            "port": self.port,
            "is_running": self.is_running,
            "tools_count": len(self.protocol.tools),
            "resources_count": len(self.protocol.resources),
            "prompts_count": len(self.protocol.prompts)
        }