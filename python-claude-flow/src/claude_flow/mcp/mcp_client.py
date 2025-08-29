"""
MCP (Model Context Protocol) client for Claude-Flow
"""

import asyncio
import json
import websockets
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

from ..core.config import config
from ..core.logger import logger
from ..core.event_bus import event_bus, EventType, publish_mcp_event


class MCPMessageType(Enum):
    """MCP message types"""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"


@dataclass
class MCPMessage:
    """MCP message structure"""
    id: str
    method: str
    params: Dict[str, Any]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        return {
            "id": self.id,
            "method": self.method,
            "params": self.params,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class MCPTool:
    """MCP tool definition"""
    name: str
    description: str
    inputSchema: Dict[str, Any]
    outputSchema: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None


class MCPClient:
    """MCP client for connecting to MCP servers"""
    
    def __init__(self, server_url: Optional[str] = None, api_key: Optional[str] = None):
        self.server_url = server_url or config.mcp.server_url
        self.api_key = api_key or config.mcp.api_key
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.connected = False
        self.tools: List[MCPTool] = []
        self.message_handlers: Dict[str, Callable] = {}
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.retry_count = 0
        self.max_retries = config.mcp.max_retries
        
    async def connect(self) -> bool:
        """Connect to MCP server"""
        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            self.websocket = await websockets.connect(
                self.server_url,
                extra_headers=headers,
                ping_interval=30,
                ping_timeout=10
            )
            
            self.connected = True
            self.retry_count = 0
            
            # Start message handling
            asyncio.create_task(self._handle_messages())
            
            # Discover available tools
            await self._discover_tools()
            
            logger.info(f"Connected to MCP server: {self.server_url}")
            await publish_mcp_event(EventType.MCP_TOOL_CALLED, {
                "action": "connected",
                "server_url": self.server_url
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from MCP server"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        
        self.connected = False
        logger.info("Disconnected from MCP server")
    
    async def _discover_tools(self):
        """Discover available tools from MCP server"""
        try:
            # Request tool list
            response = await self._send_request("tools/list", {})
            
            if response and "tools" in response:
                self.tools = []
                for tool_data in response["tools"]:
                    tool = MCPTool(
                        name=tool_data.get("name", ""),
                        description=tool_data.get("description", ""),
                        inputSchema=tool_data.get("inputSchema", {}),
                        outputSchema=tool_data.get("outputSchema"),
                        parameters=tool_data.get("parameters")
                    )
                    self.tools.append(tool)
                
                logger.info(f"Discovered {len(self.tools)} MCP tools")
                
        except Exception as e:
            logger.error(f"Failed to discover tools: {e}")
    
    async def _send_request(self, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send request to MCP server"""
        if not self.connected or not self.websocket:
            raise ConnectionError("Not connected to MCP server")
        
        request_id = f"req_{datetime.now().timestamp()}_{self.retry_count}"
        message = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params
        }
        
        # Create future for response
        future = asyncio.Future()
        self.pending_requests[request_id] = future
        
        try:
            await self.websocket.send(json.dumps(message))
            
            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=config.mcp.timeout)
            
            # Clean up
            del self.pending_requests[request_id]
            
            return response
            
        except asyncio.TimeoutError:
            # Clean up
            if request_id in self.pending_requests:
                del self.pending_requests[request_id]
            raise TimeoutError(f"Request timeout: {method}")
        
        except Exception as e:
            # Clean up
            if request_id in self.pending_requests:
                del self.pending_requests[request_id]
            raise e
    
    async def _handle_messages(self):
        """Handle incoming messages from MCP server"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._process_message(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON message: {e}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
        
        except websockets.exceptions.ConnectionClosed:
            logger.warning("MCP connection closed")
            self.connected = False
            await self._handle_reconnection()
        
        except Exception as e:
            logger.error(f"Error in message handler: {e}")
            self.connected = False
    
    async def _process_message(self, data: Dict[str, Any]):
        """Process incoming MCP message"""
        message_type = data.get("jsonrpc")
        
        if message_type == "2.0":
            # Handle JSON-RPC 2.0 message
            if "id" in data:
                # This is a response to a request
                request_id = data["id"]
                if request_id in self.pending_requests:
                    future = self.pending_requests[request_id]
                    if not future.done():
                        if "error" in data:
                            future.set_exception(Exception(data["error"]))
                        else:
                            future.set_result(data.get("result"))
                else:
                    logger.warning(f"Unknown request ID: {request_id}")
            
            elif "method" in data:
                # This is a notification or request
                method = data["method"]
                params = data.get("params", {})
                
                # Handle method
                await self._handle_method(method, params)
        
        else:
            logger.warning(f"Unknown message type: {message_type}")
    
    async def _handle_method(self, method: str, params: Dict[str, Any]):
        """Handle incoming method calls"""
        try:
            if method == "tools/call":
                # Tool call notification
                tool_name = params.get("name", "unknown")
                tool_params = params.get("arguments", {})
                
                logger.info(f"Tool called: {tool_name}")
                await publish_mcp_event(EventType.MCP_TOOL_CALLED, {
                    "tool": tool_name,
                    "params": tool_params
                })
                
                # Execute tool if handler exists
                if tool_name in self.message_handlers:
                    try:
                        result = await self.message_handlers[tool_name](tool_params)
                        
                        # Send result back
                        await self._send_notification("tools/result", {
                            "name": tool_name,
                            "result": result
                        })
                        
                    except Exception as e:
                        logger.error(f"Error executing tool {tool_name}: {e}")
                        await self._send_notification("tools/error", {
                            "name": tool_name,
                            "error": str(e)
                        })
                
                else:
                    logger.warning(f"No handler for tool: {tool_name}")
            
            elif method == "ping":
                # Respond to ping
                await self._send_notification("pong", {})
            
            else:
                logger.info(f"Unhandled method: {method}")
        
        except Exception as e:
            logger.error(f"Error handling method {method}: {e}")
    
    async def _send_notification(self, method: str, params: Dict[str, Any]):
        """Send notification to MCP server"""
        if not self.connected or not self.websocket:
            return
        
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        
        try:
            await self.websocket.send(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
    
    async def _handle_reconnection(self):
        """Handle reconnection logic"""
        if self.retry_count < self.max_retries:
            self.retry_count += 1
            logger.info(f"Attempting reconnection {self.retry_count}/{self.max_retries}")
            
            await asyncio.sleep(min(2 ** self.retry_count, 30))  # Exponential backoff
            
            if await self.connect():
                logger.info("Reconnection successful")
            else:
                await self._handle_reconnection()
        else:
            logger.error("Max reconnection attempts reached")
    
    def register_tool_handler(self, tool_name: str, handler: Callable):
        """Register handler for a specific tool"""
        self.message_handlers[tool_name] = handler
        logger.info(f"Registered handler for tool: {tool_name}")
    
    def unregister_tool_handler(self, tool_name: str):
        """Unregister tool handler"""
        if tool_name in self.message_handlers:
            del self.message_handlers[tool_name]
            logger.info(f"Unregistered handler for tool: {tool_name}")
    
    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Optional[Any]:
        """Call a specific tool on the MCP server"""
        try:
            response = await self._send_request("tools/call", {
                "name": tool_name,
                "arguments": params
            })
            
            await publish_mcp_event(EventType.MCP_TOOL_RESULT, {
                "tool": tool_name,
                "params": params,
                "result": response
            })
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to call tool {tool_name}: {e}")
            await publish_mcp_event(EventType.MCP_ERROR, {
                "tool": tool_name,
                "error": str(e)
            })
            raise e
    
    def get_tools(self) -> List[MCPTool]:
        """Get list of available tools"""
        return self.tools.copy()
    
    def get_tool(self, tool_name: str) -> Optional[MCPTool]:
        """Get specific tool by name"""
        for tool in self.tools:
            if tool.name == tool_name:
                return tool
        return None
    
    def is_connected(self) -> bool:
        """Check if connected to MCP server"""
        return self.connected
    
    async def health_check(self) -> bool:
        """Perform health check on MCP connection"""
        try:
            if not self.connected:
                return False
            
            # Send ping
            await self._send_request("ping", {})
            return True
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


# Global MCP client instance
mcp_client = MCPClient()


# Convenience functions
async def connect_mcp(server_url: Optional[str] = None, api_key: Optional[str] = None) -> bool:
    """Connect to MCP server"""
    return await mcp_client.connect(server_url, api_key)


async def disconnect_mcp():
    """Disconnect from MCP server"""
    await mcp_client.disconnect()


def register_tool_handler(tool_name: str, handler: Callable):
    """Register tool handler"""
    mcp_client.register_tool_handler(tool_name, handler)


async def call_mcp_tool(tool_name: str, params: Dict[str, Any]) -> Optional[Any]:
    """Call MCP tool"""
    return await mcp_client.call_tool(tool_name, params)


def get_mcp_tools() -> List[MCPTool]:
    """Get available MCP tools"""
    return mcp_client.get_tools()
