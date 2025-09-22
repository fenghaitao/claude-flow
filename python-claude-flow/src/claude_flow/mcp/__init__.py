"""
Model Context Protocol (MCP) implementation for Claude-Flow.

This module provides a comprehensive MCP implementation with WebSocket transport,
tool discovery, registration, and execution capabilities.

Features:
- Complete MCP 2024-11-05 protocol compliance
- 87 enterprise-grade tools across 6+ categories
- WebSocket transport with SSL/TLS support
- Advanced tool discovery and registration
- Async execution pipeline with error handling
- Comprehensive monitoring and statistics
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .protocol import MCPProtocol
    from .server import MCPServer
    from .client import MCPClient
    from .transport import WebSocketTransport
    from .tools import ToolRegistry
    from .discovery import ToolDiscoverySystem
    from .execution import ToolExecutionPipeline
    from .tools import mcp_tools_registry

__all__ = [
    "MCPProtocol",
    "MCPServer", 
    "MCPClient",
    "WebSocketTransport",
    "ToolRegistry",
    "ToolDiscoverySystem",
    "ToolExecutionPipeline",
    "mcp_tools_registry"
]

def __getattr__(name: str):
    """Lazy import for MCP components."""
    if name == "MCPProtocol":
        from .protocol import MCPProtocol
        return MCPProtocol
    elif name == "MCPServer":
        from .server import MCPServer
        return MCPServer
    elif name == "MCPClient":
        from .client import MCPClient
        return MCPClient
    elif name == "WebSocketTransport":
        from .transport import WebSocketTransport
        return WebSocketTransport
    elif name == "ToolRegistry":
        from .tools import ToolRegistry
        return ToolRegistry
    elif name == "ToolDiscoverySystem":
        from .discovery import ToolDiscoverySystem
        return ToolDiscoverySystem
    elif name == "ToolExecutionPipeline":
        from .execution import ToolExecutionPipeline
        return ToolExecutionPipeline
    elif name == "mcp_tools_registry":
        from .tools import mcp_tools_registry
        return mcp_tools_registry
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")}