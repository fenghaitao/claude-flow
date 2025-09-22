"""
MCP Client implementation for connecting to MCP servers.
"""

import asyncio
from typing import Any, Dict, List, Optional, Callable
from claude_flow.core.interfaces import BaseComponent
from .protocol import MCPProtocol, MCPMessage
from .transport import MCPWebSocketClient


class MCPClient(BaseComponent):
    """
    MCP Client for connecting to and communicating with MCP servers.
    """
    
    def __init__(self, name: str = "mcp_client"):
        super().__init__(name)
        self.protocol = MCPProtocol("mcp_client_protocol")
        self.transport = MCPWebSocketClient("mcp_client_transport")
        self.is_connected = False
        self.server_capabilities: Dict[str, Any] = {}
        self.available_tools: List[Dict[str, Any]] = []
        self.available_resources: List[Dict[str, Any]] = []
        self.available_prompts: List[Dict[str, Any]] = []
    
    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize MCP client."""
        config = config or {}
        
        # Client capabilities
        capabilities = {
            "experimental": {},
            "sampling": {}
        }
        
        await self.protocol.initialize(capabilities)
        await self.transport.initialize(self.protocol)
        
        await self.logger.info("MCP client initialized")
    
    async def connect(self, uri: str, auto_reconnect: bool = True) -> None:
        """Connect to MCP server."""
        try:
            await self.transport.connect(uri, auto_reconnect=auto_reconnect)
            
            # Initialize session
            init_result = await self.transport.initialize_session({
                "experimental": {},
                "sampling": {}
            })
            
            self.server_capabilities = init_result.get("capabilities", {})
            self.is_connected = True
            
            await self.logger.info(f"Connected to MCP server at {uri}")
            
            # Load available tools, resources, and prompts
            await self._refresh_server_capabilities()
            
        except Exception as e:
            await self.logger.error(f"Failed to connect to MCP server: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from MCP server."""
        if self.is_connected:
            await self.transport.close()
            self.is_connected = False
            await self.logger.info("Disconnected from MCP server")
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from server."""
        if not self.is_connected:
            raise RuntimeError("Not connected to server")
        
        try:
            request = self.protocol.create_request("tools/list")
            await self.transport.send_message(request)
            
            # In a real implementation, we'd wait for the response
            # For now, return cached tools
            return self.available_tools
            
        except Exception as e:
            await self.logger.error(f"Failed to list tools: {e}")
            raise
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the server."""
        if not self.is_connected:
            raise RuntimeError("Not connected to server")
        
        try:
            request = self.protocol.create_request("tools/call", {
                "name": tool_name,
                "arguments": arguments
            })
            
            await self.transport.send_message(request)
            
            # In a real implementation, we'd wait for and return the response
            # For now, return a mock response
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Tool {tool_name} executed successfully with arguments: {arguments}"
                    }
                ],
                "isError": False
            }
            
        except Exception as e:
            await self.logger.error(f"Failed to call tool {tool_name}: {e}")
            raise
    
    async def list_resources(self) -> List[Dict[str, Any]]:
        """List available resources from server."""
        if not self.is_connected:
            raise RuntimeError("Not connected to server")
        
        try:
            request = self.protocol.create_request("resources/list")
            await self.transport.send_message(request)
            
            return self.available_resources
            
        except Exception as e:
            await self.logger.error(f"Failed to list resources: {e}")
            raise
    
    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource from the server."""
        if not self.is_connected:
            raise RuntimeError("Not connected to server")
        
        try:
            request = self.protocol.create_request("resources/read", {"uri": uri})
            await self.transport.send_message(request)
            
            # Mock response
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "text/plain",
                        "text": f"Content of resource: {uri}"
                    }
                ]
            }
            
        except Exception as e:
            await self.logger.error(f"Failed to read resource {uri}: {e}")
            raise
    
    async def list_prompts(self) -> List[Dict[str, Any]]:
        """List available prompts from server."""
        if not self.is_connected:
            raise RuntimeError("Not connected to server")
        
        try:
            request = self.protocol.create_request("prompts/list")
            await self.transport.send_message(request)
            
            return self.available_prompts
            
        except Exception as e:
            await self.logger.error(f"Failed to list prompts: {e}")
            raise
    
    async def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get a prompt from the server."""
        if not self.is_connected:
            raise RuntimeError("Not connected to server")
        
        try:
            params = {"name": name}
            if arguments:
                params["arguments"] = arguments
            
            request = self.protocol.create_request("prompts/get", params)
            await self.transport.send_message(request)
            
            # Mock response
            return {
                "description": f"Prompt: {name}",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": f"Executed prompt {name} with arguments: {arguments or {}}"
                        }
                    }
                ]
            }
            
        except Exception as e:
            await self.logger.error(f"Failed to get prompt {name}: {e}")
            raise
    
    async def _refresh_server_capabilities(self) -> None:
        """Refresh available tools, resources, and prompts from server."""
        try:
            # This would normally involve actual requests to the server
            # For now, we'll set empty lists
            self.available_tools = []
            self.available_resources = []
            self.available_prompts = []
            
            await self.logger.debug("Refreshed server capabilities")
            
        except Exception as e:
            await self.logger.error(f"Failed to refresh server capabilities: {e}")
    
    async def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information."""
        return {
            "is_connected": self.is_connected,
            "server_capabilities": self.server_capabilities,
            "tools_count": len(self.available_tools),
            "resources_count": len(self.available_resources),
            "prompts_count": len(self.available_prompts)
        }