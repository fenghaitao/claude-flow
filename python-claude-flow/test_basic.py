#!/usr/bin/env python3
"""
Basic test script for Claude-Flow Python version (no external dependencies)
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_basic_functionality():
    """Test basic functionality without external dependencies"""
    print("🧪 Testing basic Python functionality...")
    
    try:
        # Test simplified config
        print("  Testing simplified config...")
        from claude_flow.core.config_simple import config
        print(f"    ✓ Config loaded: {config.app_name} v{config.version}")
        
        # Test feature flags
        print("  Testing feature flags...")
        assert config.get_feature_flag("swarm_coordination") is True
        config.set_feature_flag("test_feature", False)
        assert config.get_feature_flag("test_feature") is False
        print("    ✓ Feature flags working")
        
        # Test validation
        print("  Testing validation...")
        errors = config.validate()
        assert "CLAUDE_API_KEY is required" in errors
        print("    ✓ Validation working")
        
        # Test directory creation
        print("  Testing directory creation...")
        config._create_directories()
        assert config.config_dir.exists()
        print("    ✓ Directory creation working")
        
        print("\n🎉 Basic functionality test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_package_structure():
    """Test that package structure is correct"""
    print("\n📁 Testing package structure...")
    
    try:
        # Check if __init__.py files exist
        init_files = [
            "src/claude_flow/__init__.py",
            "src/claude_flow/core/__init__.py",
            "src/claude_flow/cli/__init__.py",
            "src/claude_flow/mcp/__init__.py"
        ]
        
        for init_file in init_files:
            if Path(init_file).exists():
                print(f"    ✓ {init_file}")
            else:
                print(f"    ❌ {init_file} missing")
                return False
        
        # Check if core modules exist
        core_modules = [
            "src/claude_flow/core/config.py",
            "src/claude_flow/core/logger.py",
            "src/claude_flow/core/event_bus.py"
        ]
        
        for module in core_modules:
            if Path(module).exists():
                print(f"    ✓ {module}")
            else:
                print(f"    ⚠ {module} (optional)")
        
        print("    ✓ Package structure looks good")
        return True
        
    except Exception as e:
        print(f"❌ Package structure test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🌊 Claude-Flow Python - Basic Test")
    print("=" * 40)
    
    # Test package structure
    if not test_package_structure():
        print("❌ Package structure test failed")
        return False
    
    # Test basic functionality
    if not test_basic_functionality():
        print("❌ Basic functionality test failed")
        return False
    
    print("\n🎉 All tests passed!")
    print("\nThe Python implementation is working correctly.")
    print("You can now install dependencies and run the full version.")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
