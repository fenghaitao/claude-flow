"""
Interactive CLI Commands and Wizards.

This module provides interactive command-line wizards, auto-completion,
and guided setup experiences for Claude-Flow.
"""

import asyncio
import json
import os
from typing import Optional, List, Dict, Any, Tuple
import click
from rich.console import Console
from rich.prompt import Prompt, Confirm, IntPrompt, FloatPrompt
from rich.panel import Panel
from rich.table import Table
from rich.progress import track
from rich.tree import Tree
from rich.markdown import Markdown
from rich import print as rprint

from claude_flow.cli.main import async_command
from claude_flow.cli.progress import get_progress_manager

console = Console()
progress_manager = get_progress_manager(console)


class InteractiveWizard:
    """Base class for interactive wizards."""
    
    def __init__(self, console: Console):
        self.console = console
        self.data = {}
    
    async def run(self) -> Dict[str, Any]:
        """Run the wizard and return collected data."""
        raise NotImplementedError
    
    def show_step(self, step_num: int, total_steps: int, title: str):
        """Show current wizard step."""
        progress = f"Step {step_num}/{total_steps}"
        panel = Panel(
            f"[bold]{title}[/bold]\n\n{progress}",
            title="Setup Wizard",
            border_style="blue"
        )
        self.console.print(panel)
    
    def collect_choice(self, 
                      prompt: str, 
                      choices: List[str], 
                      default: Optional[str] = None) -> str:
        """Collect user choice from list."""
        choice_text = " / ".join(choices)
        if default:
            choice_text += f" (default: {default})"
        
        while True:
            value = Prompt.ask(f"{prompt} [{choice_text}]", default=default)
            if value in choices:
                return value
            self.console.print(f"[red]Invalid choice. Please select from: {', '.join(choices)}[/red]")


class ProjectSetupWizard(InteractiveWizard):
    """Interactive project setup wizard."""
    
    async def run(self) -> Dict[str, Any]:
        """Run project setup wizard."""
        self.console.print("\n[bold blue]🚀 Claude-Flow Project Setup Wizard[/bold blue]\n")
        
        # Step 1: Project basics
        self.show_step(1, 5, "Project Information")
        self.data["project_name"] = Prompt.ask("Project name", default="my-claude-flow-project")
        self.data["description"] = Prompt.ask("Project description", default="")
        self.data["author"] = Prompt.ask("Author", default=os.getenv("USER", ""))
        
        # Step 2: Architecture choices
        self.show_step(2, 5, "Architecture Configuration")
        self.data["deployment_type"] = self.collect_choice(
            "Deployment type",
            ["local", "docker", "kubernetes", "cloud"],
            "local"
        )
        
        self.data["memory_backend"] = self.collect_choice(
            "Primary memory backend",
            ["sqlite", "redis", "postgresql", "multi-tier"],
            "sqlite"
        )
        
        # Step 3: Agent configuration
        self.show_step(3, 5, "Agent Configuration")
        self.data["max_agents"] = IntPrompt.ask("Maximum concurrent agents", default=10)
        self.data["default_agent_type"] = self.collect_choice(
            "Default agent type",
            ["general", "architect", "coder", "tester", "reviewer"],
            "general"
        )
        
        # Step 4: Neural network features
        self.show_step(4, 5, "Neural Network Features")
        self.data["enable_neural"] = Confirm.ask("Enable neural network features?", default=True)
        
        if self.data["enable_neural"]:
            self.data["neural_models"] = []
            if Confirm.ask("Enable task classification?", default=True):
                self.data["neural_models"].append("task_classifier")
            if Confirm.ask("Enable complexity estimation?", default=True):
                self.data["neural_models"].append("complexity_estimator")
            if Confirm.ask("Enable pattern matching?", default=True):
                self.data["neural_models"].append("pattern_matcher")
        
        # Step 5: MCP configuration
        self.show_step(5, 5, "MCP Server Configuration")
        self.data["mcp_enabled"] = Confirm.ask("Enable MCP server?", default=True)
        
        if self.data["mcp_enabled"]:
            self.data["mcp_host"] = Prompt.ask("MCP server host", default="localhost")
            self.data["mcp_port"] = IntPrompt.ask("MCP server port", default=8765)
            self.data["mcp_ssl"] = Confirm.ask("Enable SSL/TLS?", default=False)
        
        # Summary
        self.show_summary()
        
        if Confirm.ask("\nProceed with project creation?", default=True):
            await self.create_project()
        
        return self.data
    
    def show_summary(self):
        """Show configuration summary."""
        self.console.print("\n[bold]Configuration Summary:[/bold]")
        
        table = Table(box=None, padding=(0, 2))
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Project Name", self.data["project_name"])
        table.add_row("Deployment", self.data["deployment_type"])
        table.add_row("Memory Backend", self.data["memory_backend"])
        table.add_row("Max Agents", str(self.data["max_agents"]))
        table.add_row("Neural Features", "Enabled" if self.data["enable_neural"] else "Disabled")
        table.add_row("MCP Server", "Enabled" if self.data["mcp_enabled"] else "Disabled")
        
        self.console.print(table)
    
    async def create_project(self):
        """Create project structure."""
        project_name = self.data["project_name"]
        
        with self.console.status(f"[bold green]Creating project '{project_name}'..."):
            # Simulate project creation
            await asyncio.sleep(2)
        
        # Show created structure
        tree = Tree(f"[bold]{project_name}/[/bold]")
        tree.add("config/")
        tree.add("data/")
        tree.add("logs/")
        tree.add("workflows/")
        tree.add("agents/")
        tree.add("claude_flow_config.yaml")
        tree.add("requirements.txt")
        tree.add("README.md")
        
        panel = Panel(
            tree,
            title="Project Created",
            border_style="green"
        )
        self.console.print(panel)


class SwarmSetupWizard(InteractiveWizard):
    """Interactive swarm setup wizard."""
    
    async def run(self) -> Dict[str, Any]:
        """Run swarm setup wizard."""
        self.console.print("\n[bold blue]🤖 Swarm Configuration Wizard[/bold blue]\n")
        
        # Step 1: Swarm basics
        self.show_step(1, 4, "Swarm Configuration")
        self.data["swarm_name"] = Prompt.ask("Swarm session name")
        self.data["max_agents"] = IntPrompt.ask("Maximum agents", default=5)
        
        # Step 2: Agent types
        self.show_step(2, 4, "Agent Specializations")
        self.data["agent_types"] = []
        
        agent_options = ["architect", "coder", "tester", "reviewer", "general"]
        for agent_type in agent_options:
            if Confirm.ask(f"Include {agent_type} agents?", default=True):
                count = IntPrompt.ask(f"Number of {agent_type} agents", default=1)
                self.data["agent_types"].append({"type": agent_type, "count": count})
        
        # Step 3: Coordination strategy
        self.show_step(3, 4, "Coordination Strategy")
        self.data["coordination"] = self.collect_choice(
            "Coordination strategy",
            ["consensus", "leader", "democratic", "hierarchical"],
            "consensus"
        )
        
        self.data["consensus_threshold"] = FloatPrompt.ask(
            "Consensus threshold (0.0-1.0)", 
            default=0.67
        )
        
        # Step 4: Task management
        self.show_step(4, 4, "Task Management")
        self.data["auto_assign"] = Confirm.ask("Enable automatic task assignment?", default=True)
        self.data["priority_based"] = Confirm.ask("Use priority-based scheduling?", default=True)
        self.data["load_balancing"] = Confirm.ask("Enable load balancing?", default=True)
        
        return self.data


class WorkflowBuilderWizard(InteractiveWizard):
    """Interactive workflow builder wizard."""
    
    async def run(self) -> Dict[str, Any]:
        """Run workflow builder wizard."""
        self.console.print("\n[bold blue]⚙️ Workflow Builder Wizard[/bold blue]\n")
        
        # Step 1: Workflow basics
        self.show_step(1, 3, "Workflow Information")
        self.data["name"] = Prompt.ask("Workflow name")
        self.data["description"] = Prompt.ask("Description", default="")
        self.data["version"] = Prompt.ask("Version", default="1.0.0")
        
        # Step 2: Build steps
        self.show_step(2, 3, "Workflow Steps")
        self.data["steps"] = []
        
        while True:
            step_name = Prompt.ask("Step name (or 'done' to finish)")
            if step_name.lower() == "done":
                break
            
            step_type = self.collect_choice(
                "Step type",
                ["task", "condition", "parallel", "sequence", "loop"],
                "task"
            )
            
            step_config = {
                "name": step_name,
                "type": step_type,
                "description": Prompt.ask("Step description", default=""),
                "timeout": IntPrompt.ask("Timeout (seconds)", default=300)
            }
            
            if step_type == "condition":
                step_config["condition"] = Prompt.ask("Condition expression")
            elif step_type == "loop":
                step_config["iterations"] = IntPrompt.ask("Number of iterations", default=1)
            
            self.data["steps"].append(step_config)
        
        # Step 3: Triggers and scheduling
        self.show_step(3, 3, "Triggers and Scheduling")
        self.data["triggers"] = []
        
        if Confirm.ask("Add schedule trigger?", default=False):
            schedule_type = self.collect_choice(
                "Schedule type",
                ["cron", "interval", "event"],
                "interval"
            )
            
            trigger = {"type": schedule_type}
            
            if schedule_type == "cron":
                trigger["expression"] = Prompt.ask("Cron expression", default="0 * * * *")
            elif schedule_type == "interval":
                trigger["interval_minutes"] = IntPrompt.ask("Interval (minutes)", default=60)
            elif schedule_type == "event":
                trigger["event_name"] = Prompt.ask("Event name")
            
            self.data["triggers"].append(trigger)
        
        return self.data


@click.group(name="interactive")
@click.pass_context
def interactive_cli(ctx: click.Context):
    """
    Interactive Commands and Wizards
    
    Guided setup and configuration through interactive wizards
    with auto-completion and help.
    """
    pass


@interactive_cli.command()
@click.option("--output", "-o", type=click.Path(), help="Output directory")
@click.pass_context
@async_command
async def setup(ctx: click.Context, output: Optional[str]):
    """Interactive project setup wizard."""
    wizard = ProjectSetupWizard(console)
    config = await wizard.run()
    
    if output:
        config_path = os.path.join(output, "claude_flow_config.json")
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        console.print(f"[green]Configuration saved to {config_path}[/green]")


@interactive_cli.command()
@click.pass_context
@async_command
async def swarm(ctx: click.Context):
    """Interactive swarm configuration wizard."""
    wizard = SwarmSetupWizard(console)
    config = await wizard.run()
    
    console.print("\n[bold]Swarm Configuration Complete![/bold]")
    console.print(f"Session: {config['swarm_name']}")
    console.print(f"Total agents: {sum(agent['count'] for agent in config['agent_types'])}")


@interactive_cli.command()
@click.option("--output", "-o", type=click.Path(), help="Output workflow file")
@click.pass_context
@async_command
async def workflow(ctx: click.Context, output: Optional[str]):
    """Interactive workflow builder wizard."""
    wizard = WorkflowBuilderWizard(console)
    config = await wizard.run()
    
    if output:
        with open(output, "w") as f:
            json.dump(config, f, indent=2)
        console.print(f"[green]Workflow saved to {output}[/green]")
    else:
        console.print("\n[bold]Generated Workflow:[/bold]")
        console.print_json(data=config)


@interactive_cli.command()
@click.pass_context
def shell(ctx: click.Context):
    """Start interactive Claude-Flow shell."""
    from claude_flow.cli.shell import InteractiveShell
    
    shell = InteractiveShell(console)
    shell.start()


@interactive_cli.command()
@click.argument("command", required=False)
@click.pass_context
def help(ctx: click.Context, command: Optional[str]):
    """Interactive help system with examples."""
    if command:
        show_command_help(command)
    else:
        show_interactive_help()


def show_command_help(command: str):
    """Show help for specific command."""
    help_data = {
        "swarm": {
            "description": "Manage AI agent swarms",
            "examples": [
                "claude-flow swarm create my-session --agents 5",
                "claude-flow swarm spawn my-session agent1 --type coder",
                "claude-flow swarm assign my-session 'Implement user auth'",
                "claude-flow swarm status my-session --watch"
            ]
        },
        "neural": {
            "description": "Neural network and AI operations",
            "examples": [
                "claude-flow neural classify 'Fix the login bug'",
                "claude-flow neural estimate 'Build REST API' --type complexity",
                "claude-flow neural train task_classifier --data training.json"
            ]
        },
        "memory": {
            "description": "Memory and data management",
            "examples": [
                "claude-flow memory store user_data 'key' --type distributed",
                "claude-flow memory search 'authentication' --semantic",
                "claude-flow memory backup --scope all"
            ]
        },
        "workflow": {
            "description": "Workflow management and automation",
            "examples": [
                "claude-flow workflow create ci-pipeline --steps deploy.json",
                "claude-flow workflow execute my-workflow --params config.json",
                "claude-flow workflow status workflow-123 --watch"
            ]
        }
    }
    
    if command in help_data:
        cmd_help = help_data[command]
        
        panel = Panel(
            f"[bold]{command.title()} Commands[/bold]\n\n"
            f"{cmd_help['description']}\n\n"
            f"[bold]Examples:[/bold]\n" +
            "\n".join(f"  {example}" for example in cmd_help["examples"]),
            title="Command Help",
            border_style="blue"
        )
        console.print(panel)
    else:
        console.print(f"[red]No help available for command: {command}[/red]")


def show_interactive_help():
    """Show interactive help overview."""
    console.print("\n[bold blue]🎯 Claude-Flow Interactive Help[/bold blue]\n")
    
    # Command categories
    categories = {
        "Swarm Intelligence": [
            ("swarm create", "Create new agent swarm"),
            ("swarm spawn", "Add agents to swarm"),
            ("swarm assign", "Assign tasks to swarm"),
            ("swarm status", "Monitor swarm status")
        ],
        "Neural Networks": [
            ("neural classify", "Classify tasks with AI"),
            ("neural estimate", "Estimate task complexity"),
            ("neural train", "Train neural models"),
            ("neural predict", "Predict outcomes")
        ],
        "Memory Management": [
            ("memory store", "Store data in memory"),
            ("memory search", "Search stored data"),
            ("memory backup", "Backup memory data"),
            ("memory optimize", "Optimize memory usage")
        ],
        "Workflow Automation": [
            ("workflow create", "Create new workflow"),
            ("workflow execute", "Run workflow"),
            ("workflow schedule", "Schedule workflow"),
            ("workflow monitor", "Monitor execution")
        ]
    }
    
    for category, commands in categories.items():
        tree = Tree(f"[bold cyan]{category}[/bold cyan]")
        for cmd, desc in commands:
            tree.add(f"[white]{cmd}[/white] - {desc}")
        console.print(tree)
        console.print()
    
    # Quick start guide
    quick_start = """
## Quick Start Guide

1. **Initialize Project**
   ```bash
   claude-flow interactive setup
   ```

2. **Create Swarm Session**
   ```bash
   claude-flow swarm create my-session --agents 5
   ```

3. **Run Neural Classification**
   ```bash
   claude-flow neural classify "Implement user authentication"
   ```

4. **Create Workflow**
   ```bash
   claude-flow interactive workflow
   ```

5. **Check System Status**
   ```bash
   claude-flow status
   ```
"""
    
    markdown = Markdown(quick_start)
    panel = Panel(
        markdown,
        title="Quick Start",
        border_style="green"
    )
    console.print(panel)