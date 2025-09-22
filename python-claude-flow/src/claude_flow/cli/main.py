"""
Main CLI entry point for Claude-Flow.

This module provides the main Click CLI application with Rich styling
and comprehensive command organization.
"""

import asyncio
import sys
from typing import Optional, Dict, Any
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint

from claude_flow.core.config import ConfigManager
from claude_flow.core.logger import setup_logging
from claude_flow.cli.progress import ProgressManager
from claude_flow.cli.help import HelpSystem

# Initialize Rich console
console = Console()
progress_manager = ProgressManager(console)
help_system = HelpSystem(console)


class AsyncClickGroup(click.Group):
    """Custom Click Group that supports async commands."""
    
    def __call__(self, *args, **kwargs):
        """Handle async command execution."""
        return super().__call__(*args, **kwargs)


class RichClickContext(click.Context):
    """Enhanced Click context with Rich integration."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.console = console
        self.progress = progress_manager


def async_command(f):
    """Decorator to make Click commands async."""
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper


def print_banner():
    """Print the Claude-Flow banner."""
    banner = Text.assemble(
        ("Claude", "bold blue"),
        ("-", "white"),
        ("Flow", "bold green"),
        (" ", "white"),
        ("Enterprise AI Agent Orchestration Platform", "dim white")
    )
    
    panel = Panel(
        banner,
        style="bold",
        border_style="bright_blue",
        padding=(1, 2)
    )
    console.print(panel)


def print_version_info():
    """Print version and system information."""
    from claude_flow import __version__
    
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="white")
    
    table.add_row("Version", __version__)
    table.add_row("Python", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    table.add_row("Platform", sys.platform)
    
    console.print("\n[bold]System Information[/bold]")
    console.print(table)


@click.group(cls=AsyncClickGroup, context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--config", "-c", type=click.Path(exists=True), help="Configuration file path")
@click.option("--verbose", "-v", count=True, help="Increase verbosity (-v, -vv, -vvv)")
@click.option("--quiet", "-q", is_flag=True, help="Suppress output")
@click.option("--no-color", is_flag=True, help="Disable colored output")
@click.option("--format", "output_format", type=click.Choice(["json", "yaml", "table", "text"]), 
              default="table", help="Output format")
@click.version_option(version="1.0.0", prog_name="claude-flow")
@click.pass_context
def claude_flow_cli(ctx: click.Context, config: Optional[str], verbose: int, 
                   quiet: bool, no_color: bool, output_format: str):
    """
    Claude-Flow: Enterprise AI Agent Orchestration Platform
    
    A comprehensive platform for managing AI agents, workflows, and neural networks
    with advanced swarm intelligence capabilities.
    
    Examples:
        claude-flow swarm create my-session --agents 5
        claude-flow neural classify "Implement user authentication"
        claude-flow memory search "user data" --type semantic
        claude-flow workflow execute my-workflow --params config.json
    """
    # Initialize context
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet
    ctx.obj["no_color"] = no_color
    ctx.obj["output_format"] = output_format
    ctx.obj["console"] = console
    ctx.obj["progress"] = progress_manager
    
    # Configure Rich console
    if no_color:
        console.no_color = True
    
    # Setup logging based on verbosity
    if verbose >= 3:
        log_level = "DEBUG"
    elif verbose == 2:
        log_level = "INFO"
    elif verbose == 1:
        log_level = "WARNING"
    else:
        log_level = "ERROR"
    
    if not quiet:
        setup_logging(level=log_level)
    
    # Load configuration
    if config:
        ctx.obj["config_path"] = config
    
    # Print banner for main command
    if ctx.invoked_subcommand is None and not quiet:
        print_banner()
        print_version_info()


@claude_flow_cli.command()
@click.pass_context
@async_command
async def status(ctx: click.Context):
    """Show system status and health information."""
    console = ctx.obj["console"]
    
    with console.status("[bold green]Checking system status..."):
        # Mock status check
        await asyncio.sleep(1)
    
    # System status table
    status_table = Table(title="Claude-Flow System Status", box=None)
    status_table.add_column("Component", style="cyan")
    status_table.add_column("Status", style="white")
    status_table.add_column("Details", style="dim white")
    
    # Mock status data
    components = [
        ("Core Engine", "✅ Running", "All systems operational"),
        ("MCP Server", "✅ Running", "87 tools loaded"),
        ("Memory System", "✅ Running", "SQLite, Redis, PostgreSQL"),
        ("Neural Engine", "✅ Running", "4 models loaded"),
        ("Agent Pool", "✅ Running", "5 agents active"),
        ("Event Bus", "✅ Running", "Real-time messaging"),
        ("Workflow Engine", "✅ Running", "12 workflows active")
    ]
    
    for component, status, details in components:
        status_table.add_row(component, status, details)
    
    console.print(status_table)
    
    # Resource usage
    resource_table = Table(title="Resource Usage", box=None)
    resource_table.add_column("Resource", style="cyan")
    resource_table.add_column("Usage", style="white")
    resource_table.add_column("Limit", style="dim white")
    
    resources = [
        ("CPU", "45%", "8 cores"),
        ("Memory", "2.1 GB", "16 GB"),
        ("Disk", "125 GB", "1 TB"),
        ("Network", "1.2 MB/s", "1 GB/s")
    ]
    
    for resource, usage, limit in resources:
        resource_table.add_row(resource, usage, limit)
    
    console.print(resource_table)


@claude_flow_cli.command()
@click.option("--interactive", "-i", is_flag=True, help="Start interactive shell")
@click.option("--examples", "-e", is_flag=True, help="Show usage examples")
@click.pass_context
def help(ctx: click.Context, interactive: bool, examples: bool):
    """Show comprehensive help and usage information."""
    console = ctx.obj["console"]
    
    if interactive:
        # Start interactive help system
        help_system.start_interactive_help()
    elif examples:
        help_system.show_examples()
    else:
        help_system.show_overview()


@claude_flow_cli.command()
@click.option("--output", "-o", type=click.Path(), help="Output file for configuration")
@click.option("--format", "config_format", type=click.Choice(["yaml", "json", "toml"]), 
              default="yaml", help="Configuration format")
@click.pass_context
def init(ctx: click.Context, output: Optional[str], config_format: str):
    """Initialize Claude-Flow configuration."""
    console = ctx.obj["console"]
    
    config_content = generate_default_config(config_format)
    
    if output:
        with open(output, "w") as f:
            f.write(config_content)
        console.print(f"[green]Configuration written to {output}[/green]")
    else:
        console.print("[bold]Default Configuration:[/bold]")
        console.print(config_content)


def generate_default_config(format_type: str) -> str:
    """Generate default configuration in specified format."""
    if format_type == "yaml":
        return """
# Claude-Flow Configuration
app:
  name: "claude-flow"
  version: "1.0.0"
  debug: false

core:
  log_level: "INFO"
  max_workers: 10
  timeout: 30

mcp:
  server:
    host: "localhost"
    port: 8765
    ssl_enabled: false
  tools:
    discovery_paths: ["./tools", "./plugins"]
    auto_register: true

swarm:
  max_agents: 20
  coordination_timeout: 300
  consensus_threshold: 0.67

neural:
  models_path: "./models"
  cache_enabled: true
  batch_size: 32

memory:
  sqlite:
    path: "./data/memory.db"
  redis:
    host: "localhost"
    port: 6379
  postgres:
    host: "localhost"
    port: 5432
    database: "claude_flow"

workflow:
  max_concurrent: 10
  default_timeout: 3600
  retry_count: 3
"""
    elif format_type == "json":
        return """{
  "app": {
    "name": "claude-flow",
    "version": "1.0.0",
    "debug": false
  },
  "core": {
    "log_level": "INFO",
    "max_workers": 10,
    "timeout": 30
  },
  "mcp": {
    "server": {
      "host": "localhost",
      "port": 8765,
      "ssl_enabled": false
    },
    "tools": {
      "discovery_paths": ["./tools", "./plugins"],
      "auto_register": true
    }
  }
}"""
    else:  # toml
        return """
[app]
name = "claude-flow"
version = "1.0.0" 
debug = false

[core]
log_level = "INFO"
max_workers = 10
timeout = 30

[mcp.server]
host = "localhost"
port = 8765
ssl_enabled = false

[mcp.tools]
discovery_paths = ["./tools", "./plugins"]
auto_register = true
"""


# Import command groups
from claude_flow.cli.commands import swarm, neural, memory, system, workflow, mcp, interactive

# Add command groups
claude_flow_cli.add_command(swarm.swarm_cli)
claude_flow_cli.add_command(neural.neural_cli)
claude_flow_cli.add_command(memory.memory_cli)
claude_flow_cli.add_command(system.system_cli)
claude_flow_cli.add_command(workflow.workflow_cli)
claude_flow_cli.add_command(mcp.mcp_cli)
claude_flow_cli.add_command(interactive.interactive_cli)


if __name__ == "__main__":
    claude_flow_cli()