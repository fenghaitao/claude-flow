#!/usr/bin/env python3
"""
Claude-Flow Python Demo

This script demonstrates the basic functionality of the Python port.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def demo_config():
    """Demonstrate configuration functionality"""
    print("🔧 Configuration Demo")
    print("-" * 30)
    
    from claude_flow.core.config_simple import config
    
    print(f"App: {config.app_name} v{config.version}")
    print(f"Description: {config.description}")
    print(f"Base Directory: {config.base_dir}")
    print(f"Swarm Directory: {config.swarm_dir}")
    
    # Feature flags
    print(f"\nFeature Flags:")
    print(f"  Swarm Coordination: {config.get_feature_flag('swarm_coordination')}")
    print(f"  Hive Mind: {config.get_feature_flag('hive_mind')}")
    print(f"  Neural Networks: {config.get_feature_flag('neural_networks')}")
    
    # Set a new feature flag
    config.set_feature_flag('demo_mode', True)
    print(f"  Demo Mode: {config.get_feature_flag('demo_mode')}")
    
    # Validation
    errors = config.validate()
    print(f"\nConfiguration Validation:")
    if errors:
        for error in errors:
            print(f"  ❌ {error}")
    else:
        print("  ✅ Configuration is valid")
    
    return config

def demo_event_bus():
    """Demonstrate event bus functionality"""
    print("\n🚌 Event Bus Demo")
    print("-" * 30)
    
    from claude_flow.core.event_bus_simple import event_bus, Event, EventType
    
    # Start the event bus
    event_bus.start()
    print(f"Event bus running: {event_bus.is_running}")
    
    # Subscribe to events
    def agent_event_handler(event):
        print(f"  📡 Agent event: {event.type.value} - {event.data}")
    
    def swarm_event_handler(event):
        print(f"  📡 Swarm event: {event.type.value} - {event.data}")
    
    event_bus.subscribe(EventType.AGENT_CREATED, agent_event_handler)
    event_bus.subscribe(EventType.SWARM_COORDINATED, swarm_event_handler)
    
    print(f"Subscribers: Agent={event_bus.get_subscriber_count(EventType.AGENT_CREATED)}, Swarm={event_bus.get_subscriber_count(EventType.SWARM_COORDINATED)}")
    
    # Publish some events
    print("\nPublishing events...")
    from claude_flow.core.event_bus_simple import publish_agent_event, publish_swarm_event
    
    publish_agent_event("created", "agent-001", {"name": "Demo Agent", "type": "worker"})
    publish_swarm_event("coordinated", "swarm-001", {"size": 5, "status": "active"})
    
    # Check history
    history = event_bus.get_history()
    print(f"\nEvent History: {len(history)} events")
    for event in history[-2:]:  # Show last 2 events
        print(f"  📅 {event.timestamp.strftime('%H:%M:%S')} - {event.type.value}")
    
    # Stop the event bus
    event_bus.stop()
    print(f"Event bus stopped: {not event_bus.is_running}")

def demo_package_structure():
    """Demonstrate the package structure"""
    print("\n📁 Package Structure Demo")
    print("-" * 30)
    
    import claude_flow
    
    print(f"Package: {claude_flow.__name__}")
    print(f"Version: {claude_flow.__version__}")
    print(f"Author: {claude_flow.__author__}")
    print(f"License: {claude_flow.__license__}")
    
    print(f"\nAvailable components:")
    for component in claude_flow.__all__:
        print(f"  • {component}")
    
    # Test core components
    from claude_flow import Config, EventBus, Event, EventType
    print(f"\nCore components loaded:")
    print(f"  • Config: {type(Config)}")
    print(f"  • EventBus: {type(EventBus)}")
    print(f"  • Event: {type(Event)}")
    print(f"  • EventType: {type(EventType)}")

def main():
    """Main demonstration function"""
    print("🌊 Claude-Flow Python - Demonstration")
    print("=" * 50)
    print("This demonstrates the working Python implementation")
    print("with simplified modules (no external dependencies).")
    print()
    
    try:
        # Demo configuration
        config = demo_config()
        
        # Demo event bus
        demo_event_bus()
        
        # Demo package structure
        demo_package_structure()
        
        print("\n🎉 Demo completed successfully!")
        print("\nThe Python implementation is working correctly.")
        print("You can now:")
        print("  1. Install dependencies for full functionality")
        print("  2. Run the CLI interface")
        print("  3. Use the full feature set")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
