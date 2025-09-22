"""
Tool Registry for MCP protocol - manages tool discovery, registration, and execution.
"""

import asyncio
import inspect
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass
from claude_flow.core.interfaces import BaseComponent


@dataclass
class ToolDefinition:
    """Tool definition with metadata."""
    name: str
    handler: Callable
    input_schema: Dict[str, Any]
    description: str
    category: Optional[str] = None
    version: Optional[str] = "1.0.0"
    async_handler: bool = True


class ToolRegistry(BaseComponent):
    """
    Registry for managing MCP tools with discovery and execution capabilities.
    """
    
    def __init__(self, name: str = "tool_registry"):
        super().__init__(name)
        self.tools: Dict[str, ToolDefinition] = {}
        self.categories: Dict[str, List[str]] = {}
        self.execution_stats: Dict[str, Dict[str, Any]] = {}
    
    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize tool registry."""
        config = config or {}
        
        # Initialize execution stats tracking
        self.execution_stats = {}
        
        await self.logger.info("Tool registry initialized")
    
    async def register_tool(self, name: str, handler: Callable, 
                          input_schema: Dict[str, Any], description: str = "",
                          category: Optional[str] = None, version: str = "1.0.0") -> None:
        """Register a tool with the registry."""
        # Check if handler is async
        is_async = inspect.iscoroutinefunction(handler)
        
        # Create tool definition
        tool_def = ToolDefinition(
            name=name,
            handler=handler,
            input_schema=input_schema,
            description=description or f"Tool: {name}",
            category=category,
            version=version,
            async_handler=is_async
        )
        
        # Register tool
        self.tools[name] = tool_def
        
        # Update category index
        if category:
            if category not in self.categories:
                self.categories[category] = []
            if name not in self.categories[category]:
                self.categories[category].append(name)
        
        # Initialize stats
        self.execution_stats[name] = {
            "calls": 0,
            "successes": 0,
            "failures": 0,
            "total_duration": 0.0,
            "avg_duration": 0.0
        }
        
        await self.logger.info(f"Registered tool '{name}' in category '{category or 'default'}'")
    
    async def unregister_tool(self, name: str) -> None:
        """Unregister a tool from the registry."""
        if name not in self.tools:
            await self.logger.warning(f"Tool '{name}' not found for unregistration")
            return
        
        tool_def = self.tools[name]
        
        # Remove from tools
        del self.tools[name]
        
        # Remove from category index
        if tool_def.category and tool_def.category in self.categories:
            if name in self.categories[tool_def.category]:
                self.categories[tool_def.category].remove(name)
                
                # Clean up empty categories
                if not self.categories[tool_def.category]:
                    del self.categories[tool_def.category]
        
        # Remove stats
        if name in self.execution_stats:
            del self.execution_stats[name]
        
        await self.logger.info(f"Unregistered tool '{name}'")
    
    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool with given arguments."""
        if name not in self.tools:
            raise ValueError(f"Tool '{name}' not found")
        
        tool_def = self.tools[name]
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Update stats - increment calls
            self.execution_stats[name]["calls"] += 1
            
            await self.logger.debug(f"Executing tool '{name}' with arguments: {arguments}")
            
            # Validate arguments against schema
            validated_args = await self._validate_arguments(name, arguments)
            
            # Execute tool
            if tool_def.async_handler:
                result = await tool_def.handler(**validated_args)
            else:
                # Run sync handler in thread pool
                result = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: tool_def.handler(**validated_args)
                )
            
            # Calculate execution time
            duration = asyncio.get_event_loop().time() - start_time
            
            # Update success stats
            stats = self.execution_stats[name]
            stats["successes"] += 1
            stats["total_duration"] += duration
            stats["avg_duration"] = stats["total_duration"] / stats["calls"]
            
            await self.logger.debug(f"Tool '{name}' executed successfully in {duration:.3f}s")
            
            # Format result
            return {
                "content": [
                    {
                        "type": "text",
                        "text": str(result) if not isinstance(result, dict) else result.get("content", str(result))
                    }
                ],
                "isError": False,
                "execution_time": duration
            }
            
        except Exception as e:
            # Calculate execution time for failed execution
            duration = asyncio.get_event_loop().time() - start_time
            
            # Update failure stats
            stats = self.execution_stats[name]
            stats["failures"] += 1
            stats["total_duration"] += duration
            stats["avg_duration"] = stats["total_duration"] / stats["calls"]
            
            await self.logger.error(f"Tool '{name}' execution failed: {e}")
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error executing tool '{name}': {str(e)}"
                    }
                ],
                "isError": True,
                "execution_time": duration
            }
    
    async def _validate_arguments(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Validate tool arguments against schema."""
        tool_def = self.tools[tool_name]
        schema = tool_def.input_schema
        
        # Basic validation - check required properties
        if "properties" in schema:
            required = schema.get("required", [])
            for field in required:
                if field not in arguments:
                    raise ValueError(f"Missing required argument '{field}' for tool '{tool_name}'")
        
        # For now, return arguments as-is
        # In a real implementation, you'd use jsonschema or similar for full validation
        return arguments
    
    async def list_tools(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all registered tools or tools in a specific category."""
        if category and category not in self.categories:
            return []
        
        tool_names = self.categories.get(category, list(self.tools.keys())) if category else list(self.tools.keys())
        
        tools = []
        for name in tool_names:
            tool_def = self.tools[name]
            tools.append({
                "name": name,
                "description": tool_def.description,
                "inputSchema": tool_def.input_schema,
                "category": tool_def.category,
                "version": tool_def.version
            })
        
        return tools
    
    async def get_tool_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific tool."""
        if name not in self.tools:
            return None
        
        tool_def = self.tools[name]
        stats = self.execution_stats[name]
        
        return {
            "name": name,
            "description": tool_def.description,
            "inputSchema": tool_def.input_schema,
            "category": tool_def.category,
            "version": tool_def.version,
            "async_handler": tool_def.async_handler,
            "stats": stats.copy()
        }
    
    async def get_categories(self) -> List[str]:
        """Get list of all tool categories."""
        return list(self.categories.keys())
    
    async def get_tools_by_category(self, category: str) -> List[str]:
        """Get list of tool names in a specific category."""
        return self.categories.get(category, []).copy()
    
    async def get_execution_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get execution statistics for all tools."""
        return {name: stats.copy() for name, stats in self.execution_stats.items()}
    
    async def discover_tools(self, module_path: str) -> List[str]:
        """Discover and register tools from a module."""
        # This would be implemented to automatically discover tools
        # from Python modules with specific decorators or naming conventions
        await self.logger.info(f"Tool discovery from {module_path} not yet implemented")
        return []
    
    async def validate_tool_schema(self, name: str, schema: Dict[str, Any]) -> bool:
        """Validate a tool's input schema."""
        try:
            # Basic schema validation
            required_fields = ["type", "properties"]
            for field in required_fields:
                if field not in schema:
                    await self.logger.error(f"Tool '{name}' schema missing '{field}'")
                    return False
            
            if schema["type"] != "object":
                await self.logger.error(f"Tool '{name}' schema must be of type 'object'")
                return False
            
            return True
            
        except Exception as e:
            await self.logger.error(f"Error validating schema for tool '{name}': {e}")
            return False