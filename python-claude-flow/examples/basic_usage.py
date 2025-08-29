#!/usr/bin/env python3
"""
Basic usage example for Claude-Flow Python port
"""

import asyncio
import os
from pathlib import Path

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_flow.core.config import config
from claude_flow.core.logger import logger, info, error
from claude_flow.core.event_bus import event_bus, EventType, publish_agent_event
from claude_flow.mcp.mcp_client import mcp_client


async def main():
    """Main example function"""
    print("🌊 Claude-Flow Python Port - Basic Usage Example")
    print("=" * 50)
    
    # 1. Configuration
    print("\n1. Configuration Management")
    print("-" * 30)
    
    # Show current config
    print(f"App Name: {config.app_name}")
    print(f"Version: {config.version}")
    print(f"Environment: {config.environment}")
    print(f"Claude API Key: {'✓ Set' if config.claude.api_key else '✗ Missing'}")
    
    # Validate configuration
    errors = config.validate()
    if errors:
        print(f"\nConfiguration errors found:")
        for error in errors:
            print(f"  • {error}")
        print("\nPlease set CLAUDE_API_KEY environment variable")
        return
    else:
        print("✓ Configuration is valid")
    
    # 2. Logging
    print("\n2. Logging System")
    print("-" * 30)
    
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # Use convenience functions
    info("Using convenience function for info")
    error("Using convenience function for error")
    
    print("✓ Logging system working")
    
    # 3. Event Bus
    print("\n3. Event Bus System")
    print("-" * 30)
    
    # Start event bus
    await event_bus.start()
    print("✓ Event bus started")
    
    # Subscribe to events
    events_received = []
    
    def event_handler(event):
        events_received.append(event)
        print(f"  📡 Received event: {event.type.value} from {event.source}")
    
    event_bus.subscribe(EventType.AGENT_CREATED, event_handler)
    event_bus.subscribe(EventType.AGENT_STARTED, event_handler)
    
    print("✓ Event handlers registered")
    
    # Publish some events
    await publish_agent_event(
        agent_id="example_agent_001",
        event_type=EventType.AGENT_CREATED,
        data={"name": "Example Agent", "type": "worker"}
    )
    
    await publish_agent_event(
        agent_id="example_agent_001",
        event_type=EventType.AGENT_STARTED,
        data={"status": "running", "timestamp": "2024-01-15T10:00:00Z"}
    )
    
    # Wait for events to be processed
    await asyncio.sleep(0.5)
    
    print(f"✓ {len(events_received)} events processed")
    
    # 4. MCP Client
    print("\n4. MCP Client")
    print("-" * 30)
    
    if config.mcp.enabled:
        print(f"MCP Server URL: {config.mcp.server_url}")
        
        # Try to connect (this will fail if no server is running)
        try:
            connected = await mcp_client.connect()
            if connected:
                print("✓ Connected to MCP server")
                
                # Get available tools
                tools = mcp_client.get_tools()
                print(f"✓ Found {len(tools)} MCP tools")
                
                # Disconnect
                await mcp_client.disconnect()
                print("✓ Disconnected from MCP server")
            else:
                print("⚠ Could not connect to MCP server (this is expected if no server is running)")
        except Exception as e:
            print(f"⚠ MCP connection failed: {e} (this is expected if no server is running)")
    else:
        print("MCP integration is disabled")
    
    # 5. Feature Flags
    print("\n5. Feature Flags")
    print("-" * 30)
    
    features = [
        "swarm_coordination",
        "memory_persistence", 
        "mcp_integration",
        "claude_integration",
        "auto_scaling",
        "health_monitoring"
    ]
    
    for feature in features:
        status = "✓ Enabled" if config.get_feature_flag(feature) else "✗ Disabled"
        print(f"{feature.replace('_', ' ').title()}: {status}")
    
    # 6. Cleanup
    print("\n6. Cleanup")
    print("-" * 30)
    
    # Stop event bus
    await event_bus.stop()
    print("✓ Event bus stopped")
    
    print("\n🎉 Basic usage example completed successfully!")
    print("\nNext steps:")
    print("1. Set CLAUDE_API_KEY environment variable")
    print("2. Run 'python -m claude_flow.cli.main init' to initialize")
    print("3. Explore the CLI commands with 'python -m claude_flow.cli.main --help'")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
