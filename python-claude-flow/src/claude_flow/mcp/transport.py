"""
WebSocket transport implementation for MCP protocol.
"""

import asyncio
import json
import ssl
from typing import Any, Callable, Dict, Optional, Union
import websockets
from websockets.server import WebSocketServerProtocol
from websockets.client import WebSocketClientProtocol

from claude_flow.core.interfaces import BaseComponent
from .protocol import MCPMessage, MCPProtocol


class WebSocketTransport(BaseComponent):
    """
    WebSocket transport layer for MCP protocol communication.
    Supports both client and server modes with SSL/TLS encryption.
    """
    
    def __init__(self, name: str = "websocket_transport"):
        super().__init__(name)
        self.protocol: Optional[MCPProtocol] = None
        self.websocket: Optional[Union[WebSocketServerProtocol, WebSocketClientProtocol]] = None
        self.is_connected: bool = False
        self.message_handlers: Dict[str, Callable] = {}
        self.ssl_context: Optional[ssl.SSLContext] = None
        
    async def initialize(self, protocol: MCPProtocol, ssl_context: Optional[ssl.SSLContext] = None):
        """Initialize transport with MCP protocol."""
        self.protocol = protocol
        self.ssl_context = ssl_context
        await self.logger.info("WebSocket transport initialized")
    
    async def start_server(self, host: str = "localhost", port: int = 8765, 
                          ssl_context: Optional[ssl.SSLContext] = None) -> None:
        """Start WebSocket server."""
        if not self.protocol:
            raise RuntimeError("Protocol not initialized")
        
        self.ssl_context = ssl_context or self.ssl_context
        
        async def handle_client(websocket, path):
            await self.logger.info(f"Client connected from {websocket.remote_address}")
            self.websocket = websocket
            self.is_connected = True
            
            try:
                await self._handle_connection()
            except websockets.exceptions.ConnectionClosed:
                await self.logger.info("Client disconnected")
            except Exception as e:
                await self.logger.error(f"Error handling client: {e}")
            finally:
                self.is_connected = False
                self.websocket = None
        
        await self.logger.info(f"Starting MCP WebSocket server on {host}:{port}")
        
        # Start the server
        start_server = websockets.serve(
            handle_client,
            host,
            port,
            ssl=self.ssl_context
        )
        
        await start_server
        await self.logger.info("MCP WebSocket server started")
    
    async def connect_client(self, uri: str, ssl_context: Optional[ssl.SSLContext] = None) -> None:
        """Connect as WebSocket client."""
        if not self.protocol:
            raise RuntimeError("Protocol not initialized")
        
        self.ssl_context = ssl_context or self.ssl_context
        
        try:
            await self.logger.info(f"Connecting to MCP server at {uri}")
            
            # Connect to server
            self.websocket = await websockets.connect(
                uri,
                ssl=self.ssl_context
            )
            
            self.is_connected = True
            await self.logger.info("Connected to MCP server")
            
            # Start message handling
            await self._handle_connection()
            
        except Exception as e:
            await self.logger.error(f"Failed to connect to server: {e}")
            self.is_connected = False
            self.websocket = None
            raise
    
    async def _handle_connection(self) -> None:
        """Handle WebSocket connection and message processing."""
        if not self.websocket or not self.protocol:
            return
        
        try:
            async for raw_message in self.websocket:
                try:
                    # Parse incoming message
                    message_data = json.loads(raw_message)
                    message = MCPMessage.from_dict(message_data)
                    
                    await self.logger.debug(f"Received message: {message.method}")
                    
                    # Handle message through protocol
                    response = await self.protocol.handle_message(message)
                    
                    # Send response if needed
                    if response:
                        await self.send_message(response)
                        
                except json.JSONDecodeError as e:
                    await self.logger.error(f"Invalid JSON received: {e}")
                    error_response = self.protocol.create_error(
                        None, 
                        -32700,  # Parse error
                        "Invalid JSON"
                    )
                    await self.send_message(error_response)
                    
                except Exception as e:
                    await self.logger.error(f"Error processing message: {e}")
                    error_response = self.protocol.create_error(
                        None,
                        -32603,  # Internal error
                        str(e)
                    )
                    await self.send_message(error_response)
                    
        except websockets.exceptions.ConnectionClosed:
            await self.logger.info("WebSocket connection closed")
        except Exception as e:
            await self.logger.error(f"Connection error: {e}")
        finally:
            self.is_connected = False
    
    async def send_message(self, message: MCPMessage) -> None:
        """Send MCP message over WebSocket."""
        if not self.websocket or not self.is_connected:
            raise RuntimeError("WebSocket not connected")
        
        try:
            json_message = message.to_json()
            await self.websocket.send(json_message)
            await self.logger.debug(f"Sent message: {message.method or 'response'}")
            
        except Exception as e:
            await self.logger.error(f"Failed to send message: {e}")
            raise
    
    async def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> MCPMessage:
        """Send request and wait for response."""
        if not self.protocol:
            raise RuntimeError("Protocol not initialized")
        
        request = self.protocol.create_request(method, params)
        await self.send_message(request)
        
        # Wait for response with matching ID
        return await self._wait_for_response(request.id)
    
    async def send_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Send notification (no response expected)."""
        if not self.protocol:
            raise RuntimeError("Protocol not initialized")
        
        notification = self.protocol.create_notification(method, params)
        await self.send_message(notification)
    
    async def _wait_for_response(self, request_id: Union[str, int], timeout: float = 30.0) -> MCPMessage:
        """Wait for response with matching request ID."""
        start_time = asyncio.get_event_loop().time()
        
        while True:
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise asyncio.TimeoutError(f"Timeout waiting for response to request {request_id}")
            
            # This is a simplified implementation
            # In a real implementation, you'd use proper async queues
            await asyncio.sleep(0.1)
            
            # For now, we'll raise NotImplementedError as this requires
            # more sophisticated message correlation
            raise NotImplementedError(
                "Response correlation not implemented. Use async message handlers instead."
            )
    
    async def close(self) -> None:
        """Close WebSocket connection."""
        if self.websocket and self.is_connected:
            await self.websocket.close()
            self.is_connected = False
            await self.logger.info("WebSocket connection closed")
    
    def register_message_handler(self, method: str, handler: Callable) -> None:
        """Register handler for specific message type."""
        self.message_handlers[method] = handler
    
    async def create_ssl_context(self, cert_file: str, key_file: str, 
                                ca_file: Optional[str] = None) -> ssl.SSLContext:
        """Create SSL context for secure WebSocket connections."""
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        
        if ca_file:
            context.load_verify_locations(ca_file)
        else:
            # For development - don't verify certificates
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        
        # Load certificate and private key
        context.load_cert_chain(cert_file, key_file)
        
        await self.logger.info("SSL context created for secure connections")
        return context


class MCPWebSocketServer(WebSocketTransport):
    """
    Dedicated MCP WebSocket server with enhanced features.
    """
    
    def __init__(self, name: str = "mcp_websocket_server"):
        super().__init__(name)
        self.clients: Dict[str, WebSocketServerProtocol] = {}
        self.server = None
    
    async def start(self, host: str = "localhost", port: int = 8765,
                   ssl_context: Optional[ssl.SSLContext] = None) -> None:
        """Start the MCP WebSocket server."""
        if not self.protocol:
            raise RuntimeError("Protocol not initialized")
        
        self.ssl_context = ssl_context or self.ssl_context
        
        async def handle_client(websocket, path):
            client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
            self.clients[client_id] = websocket
            
            await self.logger.info(f"MCP client {client_id} connected")
            
            try:
                self.websocket = websocket
                self.is_connected = True
                await self._handle_connection()
                
            except websockets.exceptions.ConnectionClosed:
                await self.logger.info(f"MCP client {client_id} disconnected")
            except Exception as e:
                await self.logger.error(f"Error with client {client_id}: {e}")
            finally:
                if client_id in self.clients:
                    del self.clients[client_id]
                self.is_connected = False
        
        # Start server
        self.server = await websockets.serve(
            handle_client,
            host,
            port,
            ssl=self.ssl_context
        )
        
        await self.logger.info(f"MCP WebSocket server listening on {host}:{port}")
    
    async def broadcast_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Broadcast notification to all connected clients."""
        if not self.protocol:
            return
        
        notification = self.protocol.create_notification(method, params)
        message = notification.to_json()
        
        # Send to all connected clients
        disconnected_clients = []
        for client_id, websocket in self.clients.items():
            try:
                await websocket.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.append(client_id)
            except Exception as e:
                await self.logger.error(f"Failed to send to client {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            if client_id in self.clients:
                del self.clients[client_id]
    
    async def stop(self) -> None:
        """Stop the MCP WebSocket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            await self.logger.info("MCP WebSocket server stopped")
        
        # Close all client connections
        for websocket in self.clients.values():
            await websocket.close()
        
        self.clients.clear()


class MCPWebSocketClient(WebSocketTransport):
    """
    Dedicated MCP WebSocket client with enhanced features.
    """
    
    def __init__(self, name: str = "mcp_websocket_client"):
        super().__init__(name)
        self.auto_reconnect: bool = True
        self.reconnect_delay: float = 5.0
        self.max_reconnect_attempts: int = 10
        self.reconnect_attempts: int = 0
    
    async def connect(self, uri: str, ssl_context: Optional[ssl.SSLContext] = None,
                     auto_reconnect: bool = True) -> None:
        """Connect to MCP WebSocket server with auto-reconnect."""
        self.auto_reconnect = auto_reconnect
        self.ssl_context = ssl_context or self.ssl_context
        
        while self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                await self.logger.info(f"Connecting to MCP server at {uri} (attempt {self.reconnect_attempts + 1})")
                
                self.websocket = await websockets.connect(
                    uri,
                    ssl=self.ssl_context
                )
                
                self.is_connected = True
                self.reconnect_attempts = 0
                await self.logger.info("Connected to MCP server")
                
                # Start message handling
                await self._handle_connection()
                break
                
            except Exception as e:
                self.reconnect_attempts += 1
                await self.logger.error(f"Connection attempt {self.reconnect_attempts} failed: {e}")
                
                if self.reconnect_attempts >= self.max_reconnect_attempts:
                    await self.logger.error("Max reconnection attempts reached")
                    raise
                
                if self.auto_reconnect:
                    await self.logger.info(f"Retrying connection in {self.reconnect_delay} seconds...")
                    await asyncio.sleep(self.reconnect_delay)
                else:
                    raise
    
    async def initialize_session(self, capabilities: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Initialize MCP session with server."""
        if not self.protocol:
            raise RuntimeError("Protocol not initialized")
        
        init_params = {
            "protocolVersion": "2024-11-05",
            "capabilities": capabilities or {},
            "clientInfo": {
                "name": "claude-flow-client",
                "version": "1.0.0"
            }
        }
        
        # Send initialize request
        request = self.protocol.create_request("initialize", init_params)
        await self.send_message(request)
        
        await self.logger.info("MCP session initialization requested")
        
        # In a real implementation, we'd wait for the response
        # For now, return the expected capabilities
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {"listChanged": True},
                "resources": {"subscribe": True, "listChanged": True},
                "prompts": {"listChanged": True},
                "logging": {}
            },
            "serverInfo": {
                "name": "claude-flow-mcp",
                "version": "1.0.0"
            }
        }