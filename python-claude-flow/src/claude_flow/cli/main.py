#!/usr/bin/env python3
"""
Claude-Flow CLI - Main entry point
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional
import click

# Use simplified modules (no external dependencies)
from ..core.config_simple import config, Config
from ..core.event_bus_simple import event_bus

# Simple console output (no rich dependency)
def print_simple(text, style=""):
    """Simple print function without rich dependency"""
    print(text)

def print_banner():
    """Print the Claude-Flow banner"""
    print("=" * 60)
    print("🌊 Claude-Flow v2.0.0 Alpha")
    print("Enterprise-grade AI Agent Orchestration Platform")
    print("=" * 60)


def print_version(ctx, param, value):
    """Print version and exit"""
    if not value or ctx.resilient_parsing:
        return
    
    version_info = f"Claude-Flow v{config.version}"
    print_simple(version_info)
    ctx.exit()


@click.group()
@click.option(
    '--version',
    is_flag=True,
    callback=print_version,
    expose_value=False,
    is_eager=True,
    help='Show version and exit'
)
def main():
    """
    🌊 Claude-Flow: Enterprise-grade AI agent orchestration platform
    
    A Python port of the original TypeScript/Node.js implementation.
    """
    # Print banner
    print_banner()
    
    # Set log level
    log_level = 'INFO'
    print_simple(f"✓ Log level set to {log_level}")
    
    # Validate configuration
    errors = config.validate()
    if errors:
        print_simple("Configuration errors:")
        for error in errors:
            print_simple(f"  • {error}")
        print_simple("\nPlease check your configuration and environment variables.")
        sys.exit(1)
    
    # Start event bus
    event_bus.start()
    
    print_simple("✓ Configuration loaded successfully")
    print_simple("✓ Event bus started")


@main.command()
@click.option(
    '--force',
    is_flag=True,
    help='Force initialization even if already initialized'
)
def init(force: bool):
    """Initialize Claude-Flow in the current directory"""
    print_simple("Initializing Claude-Flow...")
    
    try:
        # Create directories
        print_simple("Creating directories...")
        config._create_directories()
        
        # Save configuration
        print_simple("Saving configuration...")
        config.save()
        
        # Create .gitignore
        print_simple("Creating .gitignore...")
        gitignore_path = Path.cwd() / ".gitignore"
        if not gitignore_path.exists() or force:
            gitignore_content = """# Claude-Flow
.claude-flow/
.swarm/
*.db
*.log
.env
"""
            gitignore_path.write_text(gitignore_content)
        
        # Create environment template
        print_simple("Creating environment template...")
        env_template_path = Path.cwd() / ".env.example"
        if not env_template_path.exists() or force:
            env_content = """# Claude-Flow Environment Variables
# Copy this file to .env and fill in your values

# Claude API Configuration
CLAUDE_API_KEY=your_claude_api_key_here
CLAUDE_MODEL=claude-3-sonnet-20240229

# MCP Configuration
MCP_SERVER_URL=ws://localhost:3000
MCP_API_KEY=your_mcp_api_key_here

# Database Configuration
DATABASE_PATH=.swarm/memory.db

# Logging Configuration
LOG_LEVEL=INFO
DEBUG=false

# Environment
ENVIRONMENT=development
"""
            env_template_path.write_text(env_content)
        
        print_simple("\n✓ Claude-Flow initialized successfully!")
        print_simple(f"\nConfiguration directory: {config.config_dir}")
        print_simple(f"Swarm directory: {config.swarm_dir}")
        print_simple(f"\nNext steps:")
        print_simple("1. Copy .env.example to .env and fill in your API keys")
        print_simple("2. Run 'claude-flow swarm --help' to see available commands")
        print_simple("3. Run 'claude-flow hive-mind --help' for advanced features")
        
    except Exception as e:
        print_simple(f"\n✗ Initialization failed: {e}")
        sys.exit(1)


@main.command()
def status():
    """Show Claude-Flow status and configuration"""
    print_simple("Configuration Status:")
    print_simple("-" * 30)
    
    # Check Claude API key
    claude_status = "✓ Configured" if config.claude.api_key else "✗ Missing API Key"
    print_simple(f"Claude API Key: {'***' if config.claude.api_key else 'Not set'} - {claude_status}")
    
    # Check MCP configuration
    mcp_status = "✓ Enabled" if config.mcp.server_url else "✗ Disabled"
    print_simple(f"MCP Integration: {'Enabled' if config.mcp.server_url else 'Disabled'} - {mcp_status}")
    
    # Check directories
    dirs_status = "✓ Ready" if config.config_dir.exists() else "✗ Not initialized"
    print_simple(f"Directories: {config.config_dir} - {dirs_status}")
    
    print_simple("\nFeature Flags:")
    print_simple("-" * 20)
    
    for feature, enabled in config._feature_flags.items():
        status = "✓ Enabled" if enabled else "✗ Disabled"
        print_simple(f"{feature.replace('_', ' ').title()}: {status}")
    
    # Event bus status
    event_status = "✓ Running" if event_bus.is_running else "✗ Stopped"
    print_simple(f"\nEvent Bus: {event_status}")
    
    if event_bus.is_running:
        subscriber_count = sum(len(event_bus._subscribers.get(et, set())) for et in event_bus._subscribers)
        print_simple(f"Active Subscribers: {subscriber_count}")


@main.command()
def health():
    """Perform system health check"""
    print_simple("Performing health check...")
    
    # Check configuration
    print_simple("Checking configuration...")
    config_errors = config.validate()
    if config_errors:
        print_simple("✗ Configuration errors found:")
        for error in config_errors:
            print_simple(f"  • {error}")
    else:
        print_simple("✓ Configuration is valid")
    
    # Check directories
    print_simple("Checking directories...")
    dir_errors = []
    for path_name, path in [
        ("Config", config.config_dir),
        ("Swarm", config.swarm_dir),
        ("Data", config.data_dir)
    ]:
        if not path.exists():
            dir_errors.append(f"{path_name} directory missing: {path}")
    
    if dir_errors:
        print_simple("✗ Directory errors found:")
        for error in dir_errors:
            print_simple(f"  • {error}")
    else:
        print_simple("✓ All directories exist")
    
    # Check event bus
    print_simple("Checking event bus...")
    if event_bus.is_running:
        print_simple("✓ Event bus is running")
    else:
        print_simple("✗ Event bus is not running")
    
    # Check API connectivity
    print_simple("Checking API connectivity...")
    print_simple("⚠ API connectivity check not implemented yet")
    
    # Summary
    if config_errors or dir_errors:
        print_simple("\n✗ Health check failed with errors")
        sys.exit(1)
    else:
        print_simple("\n✓ Health check passed")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print_simple("\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print_simple(f"\nFatal error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        if event_bus.is_running:
            event_bus.stop()
