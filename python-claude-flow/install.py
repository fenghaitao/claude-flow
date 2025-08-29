#!/usr/bin/env python3
"""
Installation script for Claude-Flow Python version
"""

import subprocess
import sys
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"   ✓ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ {description} failed: {e}")
        if e.stdout:
            print(f"   stdout: {e.stdout}")
        if e.stderr:
            print(f"   stderr: {e.stderr}")
        return False

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    
    # Check if pip is available
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ pip not found. Please install pip first.")
        return False
    
    # Install dependencies
    if not run_command(f"{sys.executable} -m pip install -r requirements.txt", "Installing requirements"):
        return False
    
    print("✅ Dependencies installed successfully!")
    return True

def install_package():
    """Install the package in development mode"""
    print("🔧 Installing package...")
    
    if not run_command(f"{sys.executable} -m pip install -e .", "Installing package in development mode"):
        return False
    
    print("✅ Package installed successfully!")
    return True

def test_installation():
    """Test if installation was successful"""
    print("🧪 Testing installation...")
    
    if not run_command(f"{sys.executable} test_imports.py", "Running import tests"):
        return False
    
    print("✅ Installation test passed!")
    return True

def main():
    """Main installation function"""
    print("🌊 Claude-Flow Python Installation")
    print("=" * 40)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} detected")
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Failed to install dependencies")
        sys.exit(1)
    
    # Install package
    if not install_package():
        print("❌ Failed to install package")
        sys.exit(1)
    
    # Test installation
    if not test_installation():
        print("❌ Installation test failed")
        sys.exit(1)
    
    print("\n🎉 Installation completed successfully!")
    print("\nNext steps:")
    print("1. Set your CLAUDE_API_KEY environment variable")
    print("2. Run: python -m claude_flow.cli.main init")
    print("3. Run: python -m claude_flow.cli.main --help")
    print("\nFor more information, see README.md")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Installation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Installation failed: {e}")
        sys.exit(1)
