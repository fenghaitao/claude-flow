#!/bin/bash

echo "🌊 Claude-Flow Python Installation"
echo "========================================"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.8+ first."
    exit 1
fi

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.8+ is required. Found: $python_version"
    exit 1
fi

echo "✅ Python $python_version detected"
echo

# Install dependencies
echo "📦 Installing dependencies..."
if ! python3 -m pip install -r requirements.txt; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Install package
echo "🔧 Installing package..."
if ! python3 -m pip install -e .; then
    echo "❌ Failed to install package"
    exit 1
fi

# Test installation
echo "🧪 Testing installation..."
if ! python3 test_imports.py; then
    echo "❌ Installation test failed"
    exit 1
fi

echo
echo "🎉 Installation completed successfully!"
echo
echo "Next steps:"
echo "1. Set your CLAUDE_API_KEY environment variable"
echo "2. Run: python3 -m claude_flow.cli.main init"
echo "3. Run: python3 -m claude_flow.cli.main --help"
echo
echo "For more information, see README.md"
echo
