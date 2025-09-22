"""
Swarm Intelligence CLI Commands.

This module provides command-line interface for swarm operations,
agent management, and distributed task coordination.
"""

import asyncio
import json
from typing import Optional, List, Dict, Any
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich import print as rprint

from claude_flow.cli.main import async_command
from claude_flow.cli.progress import ProgressManager
from claude_flow.mcp.tools.swarm_tools import (
    create_swarm_session, spawn_swarm_agent, assign_swarm_task,
    get_swarm_status, coordinate_swarm_agents
)

console = Console()


@click.group(name="swarm")
@click.pass_context
def swarm_cli(ctx: click.Context):
    """
    Swarm Intelligence Commands
    
    Manage AI agent swarms, coordinate distributed tasks, and monitor
    swarm performance across the Claude-Flow platform.
    """
    pass


@swarm_cli.command()
@click.argument("session_name")
@click.option("--agents", "-a", type=int, default=5, help="Maximum number of agents")
@click.option("--config", "-c", type=click.Path(exists=True), help="Session configuration file")
@click.option("--interactive", "-i", is_flag=True, help="Interactive session creation")
@click.pass_context
@async_command
async def create(ctx: click.Context, session_name: str, agents: int, 
                config: Optional[str], interactive: bool):
    """Create a new swarm session."""
    console = ctx.obj["console"]
    
    if interactive:
        agents = int(Prompt.ask("Number of agents", default=str(agents)))
        session_desc = Prompt.ask("Session description", default="")
    
    session_config = {}
    if config:
        with open(config, 'r') as f:
            session_config = json.load(f)
    
    with console.status(f"[bold green]Creating swarm session '{session_name}'..."):
        result = await create_swarm_session(
            session_name=session_name,
            max_agents=agents,
            session_config=session_config
        )
    
    if result["success"]:
        session = result["session"]
        
        # Display session info
        panel = Panel(
            f"[bold green]Session Created Successfully[/bold green]\n\n"
            f"[cyan]Session ID:[/cyan] {session['session_id']}\n"
            f"[cyan]Name:[/cyan] {session['name']}\n"
            f"[cyan]Max Agents:[/cyan] {session['max_agents']}\n"
            f"[cyan]Status:[/cyan] {session['status']}\n"
            f"[cyan]Created:[/cyan] {session['created_at']}",
            title="Swarm Session",
            border_style="green"
        )
        console.print(panel)
    else:
        console.print(f"[red]Error:[/red] {result['error']}")


@swarm_cli.command()
@click.argument("session_id")
@click.argument("agent_name")
@click.option("--type", "agent_type", type=click.Choice(["architect", "coder", "tester", "reviewer", "general"]),
              default="general", help="Agent specialization type")
@click.option("--capabilities", "-cap", multiple=True, help="Agent capabilities")
@click.pass_context
@async_command
async def spawn(ctx: click.Context, session_id: str, agent_name: str, 
               agent_type: str, capabilities: List[str]):
    """Spawn a new agent in the swarm."""
    console = ctx.obj["console"]
    
    with console.status(f"[bold green]Spawning agent '{agent_name}'..."):
        result = await spawn_swarm_agent(
            session_id=session_id,
            agent_type=agent_type,
            agent_name=agent_name,
            capabilities=list(capabilities) if capabilities else None
        )
    
    if result["success"]:
        agent = result["agent"]
        
        table = Table(title=f"Agent '{agent_name}' Spawned", box=None)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Agent ID", agent["agent_id"])
        table.add_row("Type", agent["type"])
        table.add_row("Status", agent["status"])
        table.add_row("Capabilities", ", ".join(agent["capabilities"]))
        table.add_row("Created", agent["created_at"])
        
        console.print(table)
    else:
        console.print(f"[red]Error:[/red] {result['error']}")


@swarm_cli.command()
@click.argument("session_id")
@click.argument("task_description")
@click.option("--type", "task_type", default="general", help="Task type")
@click.option("--priority", "-p", type=int, default=5, help="Task priority (1-10)")
@click.option("--deadline", "-d", help="Task deadline (ISO format)")
@click.pass_context
@async_command
async def assign(ctx: click.Context, session_id: str, task_description: str,
                task_type: str, priority: int, deadline: Optional[str]):
    """Assign a task to the swarm."""
    console = ctx.obj["console"]
    
    with console.status(f"[bold green]Assigning task to swarm..."):
        result = await assign_swarm_task(
            session_id=session_id,
            task_description=task_description,
            task_type=task_type,
            priority=priority,
            deadline=deadline
        )
    
    if result["success"]:
        task = result["task"]
        
        panel = Panel(
            f"[bold green]Task Assigned Successfully[/bold green]\n\n"
            f"[cyan]Task ID:[/cyan] {task['task_id']}\n"
            f"[cyan]Type:[/cyan] {task['type']}\n"
            f"[cyan]Priority:[/cyan] {task['priority']}\n"
            f"[cyan]Status:[/cyan] {task['status']}\n"
            f"[cyan]Description:[/cyan] {task['description']}",
            title="Task Assignment",
            border_style="blue"
        )
        console.print(panel)
    else:
        console.print(f"[red]Error:[/red] {result['error']}")


@swarm_cli.command()
@click.argument("session_id")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.option("--watch", "-w", is_flag=True, help="Watch mode - continuously update status")
@click.pass_context
@async_command
async def status(ctx: click.Context, session_id: str, output_format: str, watch: bool):
    """Get swarm session status."""
    console = ctx.obj["console"]
    
    async def show_status():
        result = await get_swarm_status(session_id)
        
        if not result["success"]:
            console.print(f"[red]Error:[/red] {result['error']}")
            return
        
        status_data = result["status"]
        
        if output_format == "json":
            console.print_json(data=status_data)
            return
        
        # Create status tables
        session_table = Table(title=f"Session {session_id} Status", box=None)
        session_table.add_column("Metric", style="cyan")
        session_table.add_column("Value", style="white")
        
        session_table.add_row("Status", status_data["status"])
        session_table.add_row("Last Updated", status_data["last_updated"])
        
        console.print(session_table)
        
        # Agents status
        agents_table = Table(title="Agents", box=None)
        agents_table.add_column("Status", style="cyan")
        agents_table.add_column("Count", style="white")
        
        for status_type, count in status_data["agents"].items():
            agents_table.add_row(status_type.title(), str(count))
        
        console.print(agents_table)
        
        # Tasks status
        tasks_table = Table(title="Tasks", box=None)
        tasks_table.add_column("Status", style="cyan")
        tasks_table.add_column("Count", style="white")
        
        for status_type, count in status_data["tasks"].items():
            tasks_table.add_row(status_type.title(), str(count))
        
        console.print(tasks_table)
        
        # Performance metrics
        perf_table = Table(title="Performance", box=None)
        perf_table.add_column("Metric", style="cyan")
        perf_table.add_column("Value", style="white")
        
        for metric, value in status_data["performance"].items():
            if isinstance(value, float):
                value = f"{value:.2f}"
            perf_table.add_row(metric.replace("_", " ").title(), str(value))
        
        console.print(perf_table)
    
    if watch:
        try:
            while True:
                console.clear()
                await show_status()
                await asyncio.sleep(5)
        except KeyboardInterrupt:
            console.print("\n[yellow]Monitoring stopped.[/yellow]")
    else:
        await show_status()


@swarm_cli.command()
@click.argument("session_id")
@click.argument("agents", nargs=-1, required=True)
@click.option("--strategy", "-s", type=click.Choice(["consensus", "leader", "democratic"]),
              default="consensus", help="Coordination strategy")
@click.pass_context
@async_command
async def coordinate(ctx: click.Context, session_id: str, agents: List[str], strategy: str):
    """Coordinate multiple agents for complex tasks."""
    console = ctx.obj["console"]
    
    with console.status(f"[bold green]Coordinating {len(agents)} agents..."):
        result = await coordinate_swarm_agents(
            session_id=session_id,
            coordination_strategy=strategy,
            target_agents=list(agents)
        )
    
    if result["success"]:
        coordination = result["coordination"]
        
        panel = Panel(
            f"[bold green]Coordination Initiated[/bold green]\n\n"
            f"[cyan]Coordination ID:[/cyan] {coordination['coordination_id']}\n"
            f"[cyan]Strategy:[/cyan] {coordination['strategy']}\n"
            f"[cyan]Target Agents:[/cyan] {len(coordination['target_agents'])}\n"
            f"[cyan]Status:[/cyan] {coordination['status']}\n"
            f"[cyan]Progress:[/cyan] {coordination['coordination_progress']:.1%}",
            title="Agent Coordination",
            border_style="blue"
        )
        console.print(panel)
    else:
        console.print(f"[red]Error:[/red] {result['error']}")


@swarm_cli.command()
@click.option("--all", "-a", "list_all", is_flag=True, help="List all sessions")
@click.option("--active", is_flag=True, help="List only active sessions")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
@async_command
async def list(ctx: click.Context, list_all: bool, active: bool, output_format: str):
    """List swarm sessions."""
    console = ctx.obj["console"]
    
    # Mock session list
    sessions = [
        {"id": "sess_001", "name": "dev-session", "status": "active", "agents": 5, "tasks": 12},
        {"id": "sess_002", "name": "test-session", "status": "paused", "agents": 3, "tasks": 8},
        {"id": "sess_003", "name": "prod-session", "status": "active", "agents": 10, "tasks": 25}
    ]
    
    if active:
        sessions = [s for s in sessions if s["status"] == "active"]
    
    if output_format == "json":
        console.print_json(data=sessions)
        return
    
    table = Table(title="Swarm Sessions", box=None)
    table.add_column("Session ID", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Status", style="green")
    table.add_column("Agents", style="blue")
    table.add_column("Tasks", style="yellow")
    
    for session in sessions:
        status_style = "green" if session["status"] == "active" else "yellow"
        table.add_row(
            session["id"],
            session["name"],
            f"[{status_style}]{session['status']}[/{status_style}]",
            str(session["agents"]),
            str(session["tasks"])
        )
    
    console.print(table)