#!/usr/bin/env python3
"""
Test script to verify Python imports work correctly
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all Python imports work correctly"""
    print("🧪 Testing Python imports...")
    
    try:
        # Test core imports
        print("  Testing core imports...")
        from claude_flow.core import config, EventBus, Event, EventType
        print(f"    ✓ Core: config={config.app_name}, EventBus={type(EventBus)}")
        
        # Test main package import
        print("  Testing main package import...")
        from claude_flow import Config, EventBus, Event, EventType
        print(f"    ✓ Main package: Config={type(Config)}")
        
        # Test CLI imports (minimal)
        print("  Testing CLI imports...")
        from claude_flow.cli import __all__
        print(f"    ✓ CLI: {__all__}")
        
        # Test MCP imports (minimal)
        print("  Testing MCP imports...")
        from claude_flow.mcp import __all__
        print(f"    ✓ MCP: {__all__}")
        
        print("\n🎉 All imports successful!")
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
