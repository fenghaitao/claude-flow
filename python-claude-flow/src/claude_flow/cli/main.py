#!/usr/bin/env python3
"""
Claude-Flow CLI - Main entry point
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional
import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..core.config import config, Config
from ..core.logger import logger
from ..core.event_bus import event_bus
from .commands import cli_group

console = Console()


def print_banner():
    """Print the Claude-Flow banner"""
    banner_text = Text("🌊 Claude-Flow v2.0.0 Alpha", style="bold cyan")
    subtitle = Text("Enterprise-grade AI Agent Orchestration Platform", style="dim")
    
    panel = Panel(
        f"{banner_text}\n{subtitle}",
        border_style="cyan",
        padding=(1, 2)
    )
    console.print(panel)


def print_version(ctx, param, value):
    """Print version and exit"""
    if not value or ctx.resilient_parsing:
        return
    
    version_info = f"Claude-Flow v{config.version}"
    console.print(f"[bold cyan]{version_info}[/bold cyan]")
    ctx.exit()


@click.group(cls=cli_group)
@click.option(
    '--version',
    is_flag=True,
    callback=print_version,
    expose_value=False,
    is_eager=True,
    help='Show version and exit'
)
@click.option(
    '--config',
    '-c',
    type=click.Path(exists=True, path_type=Path),
    help='Path to configuration file'
)
@click.option(
    '--verbose',
    '-v',
    is_flag=True,
    help='Enable verbose logging'
)
@click.option(
    '--debug',
    is_flag=True,
    help='Enable debug mode'
)
@click.option(
    '--log-level',
    type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']),
    default='INFO',
    help='Set log level'
)
def main(config_file: Optional[Path], verbose: bool, debug: bool, log_level: str):
    """
    🌊 Claude-Flow: Enterprise-grade AI agent orchestration platform
    
    A Python port of the original TypeScript/Node.js implementation.
    """
    # Print banner
    print_banner()
    
    # Load custom config if specified
    if config_file:
        try:
            global_config = Config.load(config_file)
            # Update global config with custom values
            for key, value in global_config.dict().items():
                if hasattr(config, key):
                    setattr(config, key, value)
        except Exception as e:
            console.print(f"[red]Error loading config file: {e}[/red]")
            sys.exit(1)
    
    # Set log level
    if verbose:
        log_level = 'DEBUG'
    if debug:
        log_level = 'DEBUG'
        config.debug = True
    
    logger.set_level(log_level)
    
    # Validate configuration
    errors = config.validate()
    if errors:
        console.print("[red]Configuration errors:[/red]")
        for error in errors:
            console.print(f"  [red]• {error}[/red]")
        console.print("\n[yellow]Please check your configuration and environment variables.[/yellow]")
        sys.exit(1)
    
    # Start event bus
    asyncio.run(event_bus.start())
    
    console.print(f"[green]✓[/green] Configuration loaded successfully")
    console.print(f"[green]✓[/green] Event bus started")
    console.print(f"[green]✓[/green] Log level set to {log_level}")


@main.command()
@click.option(
    '--force',
    is_flag=True,
    help='Force initialization even if already initialized'
)
def init(force: bool):
    """Initialize Claude-Flow in the current directory"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Initializing Claude-Flow...", total=4)
        
        try:
            # Create directories
            progress.update(task, description="Creating directories...")
            config.config_dir.mkdir(parents=True, exist_ok=True)
            config.swarm_dir.mkdir(parents=True, exist_ok=True)
            config.memory_dir.mkdir(parents=True, exist_ok=True)
            progress.advance(task)
            
            # Save configuration
            progress.update(task, description="Saving configuration...")
            config.save()
            progress.advance(task)
            
            # Create .gitignore
            progress.update(task, description="Creating .gitignore...")
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
            progress.advance(task)
            
            # Create environment template
            progress.update(task, description="Creating environment template...")
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
            progress.advance(task)
            
            console.print("\n[green]✓[/green] Claude-Flow initialized successfully!")
            console.print(f"\n[cyan]Configuration directory:[/cyan] {config.config_dir}")
            console.print(f"[cyan]Swarm directory:[/cyan] {config.swarm_dir}")
            console.print(f"[cyan]Memory directory:[/cyan] {config.memory_dir}")
            console.print(f"\n[yellow]Next steps:[/yellow]")
            console.print("1. Copy .env.example to .env and fill in your API keys")
            console.print("2. Run 'claude-flow swarm --help' to see available commands")
            console.print("3. Run 'claude-flow hive-mind --help' for advanced features")
            
        except Exception as e:
            console.print(f"\n[red]✗[/red] Initialization failed: {e}")
            logger.exception("Initialization failed")
            sys.exit(1)


@main.command()
def status():
    """Show Claude-Flow status and configuration"""
    # Configuration status
    config_table = Table(title="Configuration Status")
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="green")
    config_table.add_column("Status", style="yellow")
    
    # Check Claude API key
    claude_status = "✓ Configured" if config.claude.api_key else "✗ Missing API Key"
    config_table.add_row("Claude API Key", "***" if config.claude.api_key else "Not set", claude_status)
    
    # Check MCP configuration
    mcp_status = "✓ Enabled" if config.mcp.enabled else "✗ Disabled"
    config_table.add_row("MCP Integration", "Enabled" if config.mcp.enabled else "Disabled", mcp_status)
    
    # Check database
    db_path = Path(config.database.path)
    db_status = "✓ Ready" if db_path.parent.exists() else "✗ Directory missing"
    config_table.add_row("Database", str(config.database.path), db_status)
    
    # Check directories
    dirs_status = "✓ Ready" if config.config_dir.exists() else "✗ Not initialized"
    config_table.add_row("Directories", str(config.config_dir), dirs_status)
    
    console.print(config_table)
    
    # Feature flags
    features_table = Table(title="Feature Flags")
    features_table.add_column("Feature", style="cyan")
    features_table.add_column("Status", style="green")
    
    for feature, enabled in config.features.items():
        status = "✓ Enabled" if enabled else "✗ Disabled"
        features_table.add_row(feature.replace("_", " ").title(), status)
    
    console.print(features_table)
    
    # Event bus status
    event_status = "✓ Running" if event_bus.is_running() else "✗ Stopped"
    console.print(f"\n[cyan]Event Bus:[/cyan] {event_status}")
    
    if event_bus.is_running():
        subscriber_count = event_bus.get_subscriber_count()
        console.print(f"[cyan]Active Subscribers:[/cyan] {subscriber_count}")


@main.command()
def health():
    """Perform system health check"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Performing health check...", total=5)
        
        # Check configuration
        progress.update(task, description="Checking configuration...")
        config_errors = config.validate()
        if config_errors:
            console.print(f"\n[red]✗[/red] Configuration errors found:")
            for error in config_errors:
                console.print(f"  [red]• {error}[/red]")
        else:
            console.print(f"\n[green]✓[/green] Configuration is valid")
        progress.advance(task)
        
        # Check directories
        progress.update(task, description="Checking directories...")
        dir_errors = []
        for path_name, path in [
            ("Config", config.config_dir),
            ("Swarm", config.swarm_dir),
            ("Memory", config.memory_dir)
        ]:
            if not path.exists():
                dir_errors.append(f"{path_name} directory missing: {path}")
        
        if dir_errors:
            console.print(f"\n[red]✗[/red] Directory errors found:")
            for error in dir_errors:
                console.print(f"  [red]• {error}[/red]")
        else:
            console.print(f"\n[green]✓[/green] All directories exist")
        progress.advance(task)
        
        # Check event bus
        progress.update(task, description="Checking event bus...")
        if event_bus.is_running():
            console.print(f"\n[green]✓[/green] Event bus is running")
        else:
            console.print(f"\n[red]✗[/red] Event bus is not running")
        progress.advance(task)
        
        # Check API connectivity
        progress.update(task, description="Checking API connectivity...")
        # TODO: Implement actual API connectivity checks
        console.print(f"\n[yellow]⚠[/yellow] API connectivity check not implemented yet")
        progress.advance(task)
        
        # Check database
        progress.update(task, description="Checking database...")
        db_path = Path(config.database.path)
        if db_path.exists():
            console.print(f"\n[green]✓[/green] Database file exists")
        else:
            console.print(f"\n[yellow]⚠[/yellow] Database file does not exist (will be created on first use)")
        progress.advance(task)
    
    # Summary
    if config_errors or dir_errors:
        console.print(f"\n[red]Health check failed with errors[/red]")
        sys.exit(1)
    else:
        console.print(f"\n[green]✓[/green] Health check passed")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Fatal error: {e}[/red]")
        logger.exception("Fatal error in main")
        sys.exit(1)
    finally:
        # Cleanup
        if event_bus.is_running():
            asyncio.run(event_bus.stop())
