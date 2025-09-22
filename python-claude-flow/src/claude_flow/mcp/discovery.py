"""
Tool discovery and registration system for MCP protocol.
"""

import asyncio
import importlib
import importlib.util
import inspect
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Type, get_type_hints
from dataclasses import dataclass, field
import pkgutil

from claude_flow.core.interfaces import BaseComponent
from .tools import ToolRegistry, ToolDefinition
from .protocol import MCPTool


@dataclass
class ToolDiscoveryConfig:
    """Configuration for tool discovery."""
    search_paths: List[str] = field(default_factory=list)
    module_patterns: List[str] = field(default_factory=lambda: ["*_tools", "*_mcp", "tools_*"])
    function_patterns: List[str] = field(default_factory=lambda: ["mcp_*", "tool_*", "*_tool"])
    auto_register: bool = True
    validate_schemas: bool = True


class ToolDecorator:
    """Decorator for marking functions as MCP tools."""
    
    def __init__(self, name: Optional[str] = None, description: str = "", 
                 category: Optional[str] = None, version: str = "1.0.0",
                 input_schema: Optional[Dict[str, Any]] = None):
        self.name = name
        self.description = description
        self.category = category
        self.version = version
        self.input_schema = input_schema
    
    def __call__(self, func: Callable) -> Callable:
        """Mark function as MCP tool."""
        # Store tool metadata on function
        func._mcp_tool = True
        func._mcp_name = self.name or func.__name__
        func._mcp_description = self.description or func.__doc__ or f"Tool: {func.__name__}"
        func._mcp_category = self.category
        func._mcp_version = self.version
        func._mcp_input_schema = self.input_schema or self._generate_schema_from_signature(func)
        
        return func
    
    def _generate_schema_from_signature(self, func: Callable) -> Dict[str, Any]:
        """Generate JSON schema from function signature."""
        try:
            sig = inspect.signature(func)
            type_hints = get_type_hints(func)
            
            properties = {}
            required = []
            
            for param_name, param in sig.parameters.items():
                if param_name in ['self', 'cls']:
                    continue
                
                param_type = type_hints.get(param_name, str)
                
                # Convert Python types to JSON schema types
                if param_type == str:
                    json_type = "string"
                elif param_type == int:
                    json_type = "integer"
                elif param_type == float:
                    json_type = "number"
                elif param_type == bool:
                    json_type = "boolean"
                elif param_type == list:
                    json_type = "array"
                elif param_type == dict:
                    json_type = "object"
                else:
                    json_type = "string"  # Default fallback
                
                properties[param_name] = {
                    "type": json_type,
                    "description": f"Parameter: {param_name}"
                }
                
                # Mark as required if no default value
                if param.default == inspect.Parameter.empty:
                    required.append(param_name)
            
            return {
                "type": "object",
                "properties": properties,
                "required": required
            }
            
        except Exception:
            # Fallback schema
            return {
                "type": "object",
                "properties": {},
                "required": []
            }


# Global decorator instance
mcp_tool = ToolDecorator


class ToolDiscoverySystem(BaseComponent):
    """
    Advanced tool discovery and registration system for MCP.
    """
    
    def __init__(self, name: str = "tool_discovery", registry: Optional[ToolRegistry] = None):
        super().__init__(name)
        self.registry = registry or ToolRegistry()
        self.config = ToolDiscoveryConfig()
        self.discovered_tools: Dict[str, ToolDefinition] = {}
        self.discovery_cache: Dict[str, List[str]] = {}
    
    async def initialize(self, config: Optional[ToolDiscoveryConfig] = None) -> None:
        """Initialize tool discovery system."""
        if config:
            self.config = config
        
        await self.registry.initialize()
        await self.logger.info("Tool discovery system initialized")
    
    async def discover_tools(self, search_paths: Optional[List[str]] = None) -> List[str]:
        """Discover tools from specified paths or default locations."""
        search_paths = search_paths or self.config.search_paths
        discovered = []
        
        # Add default search paths if none provided
        if not search_paths:
            search_paths = self._get_default_search_paths()
        
        for path in search_paths:
            try:
                path_tools = await self._discover_from_path(path)
                discovered.extend(path_tools)
                await self.logger.info(f"Discovered {len(path_tools)} tools from {path}")
            except Exception as e:
                await self.logger.error(f"Error discovering tools from {path}: {e}")
        
        await self.logger.info(f"Total tools discovered: {len(discovered)}")
        return discovered
    
    async def _discover_from_path(self, path: str) -> List[str]:
        """Discover tools from a specific path."""
        discovered = []
        
        if os.path.isfile(path) and path.endswith('.py'):
            # Single Python file
            discovered.extend(await self._discover_from_file(path))
        elif os.path.isdir(path):
            # Directory - search for Python modules
            discovered.extend(await self._discover_from_directory(path))
        else:
            # Try as module name
            discovered.extend(await self._discover_from_module(path))
        
        return discovered
    
    async def _discover_from_file(self, file_path: str) -> List[str]:
        """Discover tools from a Python file."""
        discovered = []
        
        try:
            # Load module from file
            spec = importlib.util.spec_from_file_location("tools_module", file_path)
            if not spec or not spec.loader:
                return discovered
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find tool functions
            tools = self._extract_tools_from_module(module)
            discovered.extend(await self._register_discovered_tools(tools))
            
        except Exception as e:
            await self.logger.error(f"Error loading tools from file {file_path}: {e}")
        
        return discovered
    
    async def _discover_from_directory(self, directory: str) -> List[str]:
        """Discover tools from a directory."""
        discovered = []
        
        try:
            # Walk through directory
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.endswith('.py') and not file.startswith('__'):
                        file_path = os.path.join(root, file)
                        file_tools = await self._discover_from_file(file_path)
                        discovered.extend(file_tools)
        
        except Exception as e:
            await self.logger.error(f"Error discovering from directory {directory}: {e}")
        
        return discovered
    
    async def _discover_from_module(self, module_name: str) -> List[str]:
        """Discover tools from a module name."""
        discovered = []
        
        try:
            # Import module
            module = importlib.import_module(module_name)
            
            # Find tool functions
            tools = self._extract_tools_from_module(module)
            discovered.extend(await self._register_discovered_tools(tools))
            
        except ImportError as e:
            await self.logger.warning(f"Could not import module {module_name}: {e}")
        except Exception as e:
            await self.logger.error(f"Error discovering from module {module_name}: {e}")
        
        return discovered
    
    def _extract_tools_from_module(self, module) -> List[Callable]:
        """Extract tool functions from a module."""
        tools = []
        
        for name in dir(module):
            obj = getattr(module, name)
            
            # Check if it's a decorated MCP tool
            if self._is_mcp_tool(obj):
                tools.append(obj)
            # Check if it matches naming patterns
            elif self._matches_tool_patterns(name) and callable(obj):
                tools.append(obj)
        
        return tools
    
    def _is_mcp_tool(self, obj) -> bool:
        """Check if object is a decorated MCP tool."""
        return hasattr(obj, '_mcp_tool') and obj._mcp_tool
    
    def _matches_tool_patterns(self, name: str) -> bool:
        """Check if name matches tool patterns."""
        import fnmatch
        
        for pattern in self.config.function_patterns:
            if fnmatch.fnmatch(name, pattern):
                return True
        return False
    
    async def _register_discovered_tools(self, tools: List[Callable]) -> List[str]:
        """Register discovered tools with the registry."""
        registered = []
        
        for tool_func in tools:
            try:
                tool_name = await self._register_tool_function(tool_func)
                if tool_name:
                    registered.append(tool_name)
            except Exception as e:
                await self.logger.error(f"Error registering tool {tool_func.__name__}: {e}")
        
        return registered
    
    async def _register_tool_function(self, func: Callable) -> Optional[str]:
        """Register a single tool function."""
        # Get tool metadata
        if hasattr(func, '_mcp_tool'):
            # Decorated tool
            name = func._mcp_name
            description = func._mcp_description
            category = func._mcp_category
            version = func._mcp_version
            input_schema = func._mcp_input_schema
        else:
            # Undecorated tool - generate metadata
            name = func.__name__
            description = func.__doc__ or f"Tool: {name}"
            category = "discovered"
            version = "1.0.0"
            input_schema = ToolDecorator()._generate_schema_from_signature(func)
        
        # Validate schema if required
        if self.config.validate_schemas:
            if not await self.registry.validate_tool_schema(name, input_schema):
                await self.logger.error(f"Invalid schema for tool {name}, skipping registration")
                return None
        
        # Register with registry
        if self.config.auto_register:
            await self.registry.register_tool(
                name=name,
                handler=func,
                input_schema=input_schema,
                description=description,
                category=category,
                version=version
            )
            
            await self.logger.debug(f"Auto-registered tool: {name}")
            return name
        else:
            # Store for manual registration
            self.discovered_tools[name] = ToolDefinition(
                name=name,
                handler=func,
                input_schema=input_schema,
                description=description,
                category=category,
                version=version,
                async_handler=inspect.iscoroutinefunction(func)
            )
            
            await self.logger.debug(f"Discovered tool: {name} (not auto-registered)")
            return name
    
    def _get_default_search_paths(self) -> List[str]:
        """Get default search paths for tool discovery."""
        paths = []
        
        # Current working directory
        paths.append(os.getcwd())
        
        # Common tool locations
        common_paths = [
            "tools",
            "mcp_tools",
            "claude_flow/tools",
            "src/tools",
            "lib/tools"
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                paths.append(os.path.abspath(path))
        
        return paths
    
    async def register_pending_tools(self) -> List[str]:
        """Register all discovered but not yet registered tools."""
        registered = []
        
        for name, tool_def in self.discovered_tools.items():
            try:
                await self.registry.register_tool(
                    name=tool_def.name,
                    handler=tool_def.handler,
                    input_schema=tool_def.input_schema,
                    description=tool_def.description,
                    category=tool_def.category,
                    version=tool_def.version
                )
                registered.append(name)
                await self.logger.info(f"Registered pending tool: {name}")
            except Exception as e:
                await self.logger.error(f"Error registering pending tool {name}: {e}")
        
        # Clear registered tools from pending
        for name in registered:
            del self.discovered_tools[name]
        
        return registered
    
    async def get_discovery_report(self) -> Dict[str, Any]:
        """Get report of tool discovery activities."""
        return {
            "discovered_tools": len(self.discovered_tools),
            "registered_tools": len(self.registry.tools),
            "categories": await self.registry.get_categories(),
            "pending_tools": list(self.discovered_tools.keys()),
            "config": {
                "search_paths": self.config.search_paths,
                "auto_register": self.config.auto_register,
                "validate_schemas": self.config.validate_schemas
            }
        }
    
    async def reload_tools(self, module_name: str) -> List[str]:
        """Reload tools from a specific module."""
        try:
            # Reload the module
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
            
            # Rediscover tools
            return await self._discover_from_module(module_name)
            
        except Exception as e:
            await self.logger.error(f"Error reloading tools from {module_name}: {e}")
            return []


# Example tool implementations for testing
@mcp_tool(name="echo", description="Echo back the input text", category="utility")
async def echo_tool(text: str) -> str:
    """Echo back the provided text."""
    return f"Echo: {text}"


@mcp_tool(name="add_numbers", description="Add two numbers together", category="math")
async def add_numbers_tool(a: int, b: int) -> int:
    """Add two numbers and return the result."""
    return a + b


@mcp_tool(name="list_files", description="List files in a directory", category="filesystem")
async def list_files_tool(path: str = ".") -> List[str]:
    """List files in the specified directory."""
    try:
        return os.listdir(path)
    except Exception as e:
        return [f"Error: {str(e)}"]