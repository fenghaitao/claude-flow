"""
Comprehensive Help System with Examples and Tutorials.

This module provides an advanced help system with contextual examples,
tutorials, and interactive guidance for Claude-Flow CLI.
"""

from typing import Dict, List, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.layout import Layout
from rich.align import Align
from rich.text import Text
from rich import box


class HelpSystem:
    """
    Advanced help system with examples, tutorials, and interactive guidance.
    """
    
    def __init__(self, console: Console):
        self.console = console
        self.help_data = self._load_help_data()
    
    def _load_help_data(self) -> Dict[str, Any]:
        """Load comprehensive help data."""
        return {
            "categories": {
                "swarm": {
                    "title": "Swarm Intelligence",
                    "description": "Manage AI agent swarms and distributed task coordination",
                    "icon": "🤖",
                    "commands": {
                        "create": {
                            "description": "Create a new swarm session",
                            "usage": "claude-flow swarm create <session_name> [OPTIONS]",
                            "examples": [
                                {
                                    "command": "claude-flow swarm create dev-session --agents 5",
                                    "description": "Create a development swarm with 5 agents"
                                },
                                {
                                    "command": "claude-flow swarm create prod-session --agents 20 --config swarm.json",
                                    "description": "Create production swarm with custom configuration"
                                }
                            ],
                            "options": [
                                ("--agents, -a", "Maximum number of agents (default: 5)"),
                                ("--config, -c", "Configuration file path"),
                                ("--interactive, -i", "Interactive session creation")
                            ]
                        },
                        "spawn": {
                            "description": "Spawn a new agent in the swarm",
                            "usage": "claude-flow swarm spawn <session_id> <agent_name> [OPTIONS]",
                            "examples": [
                                {
                                    "command": "claude-flow swarm spawn sess_001 coder1 --type coder",
                                    "description": "Spawn a specialized coder agent"
                                },
                                {
                                    "command": "claude-flow swarm spawn sess_001 reviewer1 --type reviewer --capabilities 'security,performance'",
                                    "description": "Spawn a reviewer with specific capabilities"
                                }
                            ]
                        }
                    }
                },
                "neural": {
                    "title": "Neural Networks & AI",
                    "description": "Neural network operations and AI-powered analysis",
                    "icon": "🧠",
                    "commands": {
                        "classify": {
                            "description": "Classify tasks using neural networks",
                            "usage": "claude-flow neural classify <task_description> [OPTIONS]",
                            "examples": [
                                {
                                    "command": "claude-flow neural classify 'Implement user authentication'",
                                    "description": "Classify a development task"
                                },
                                {
                                    "command": "claude-flow neural classify 'Fix login bug' --confidence 0.8",
                                    "description": "Classify with minimum confidence threshold"
                                }
                            ]
                        }
                    }
                },
                "memory": {
                    "title": "Memory Management",
                    "description": "Data storage, retrieval, and memory operations",
                    "icon": "💾",
                    "commands": {
                        "store": {
                            "description": "Store data in memory system",
                            "usage": "claude-flow memory store <key> <data> [OPTIONS]",
                            "examples": [
                                {
                                    "command": "claude-flow memory store user_data 'John Doe' --type local",
                                    "description": "Store data in local memory"
                                },
                                {
                                    "command": "claude-flow memory store session_config '{\"timeout\": 300}' --type distributed --ttl 3600",
                                    "description": "Store JSON data with TTL in distributed memory"
                                }
                            ]
                        }
                    }
                },
                "workflow": {
                    "title": "Workflow Automation",
                    "description": "Create and manage automated workflows",
                    "icon": "⚙️",
                    "commands": {
                        "create": {
                            "description": "Create a new workflow",
                            "usage": "claude-flow workflow create <name> [OPTIONS]",
                            "examples": [
                                {
                                    "command": "claude-flow workflow create ci-pipeline --steps deploy.json",
                                    "description": "Create CI/CD pipeline workflow"
                                }
                            ]
                        }
                    }
                }
            },
            "tutorials": {
                "getting_started": {
                    "title": "Getting Started with Claude-Flow",
                    "steps": [
                        {
                            "title": "Initialize Project",
                            "description": "Set up a new Claude-Flow project",
                            "command": "claude-flow interactive setup",
                            "explanation": "This will guide you through project configuration"
                        },
                        {
                            "title": "Create First Swarm",
                            "description": "Create your first agent swarm",
                            "command": "claude-flow swarm create my-first-swarm --agents 3",
                            "explanation": "Creates a swarm with 3 general-purpose agents"
                        },
                        {
                            "title": "Spawn Specialized Agents",
                            "description": "Add specialized agents to your swarm",
                            "command": "claude-flow swarm spawn my-first-swarm coder1 --type coder",
                            "explanation": "Adds a coding specialist to handle development tasks"
                        },
                        {
                            "title": "Assign First Task",
                            "description": "Give the swarm something to work on",
                            "command": "claude-flow swarm assign my-first-swarm 'Create a hello world function'",
                            "explanation": "The swarm will coordinate to complete this task"
                        },
                        {
                            "title": "Monitor Progress",
                            "description": "Watch your swarm in action",
                            "command": "claude-flow swarm status my-first-swarm --watch",
                            "explanation": "Real-time monitoring of swarm activity"
                        }
                    ]
                },
                "advanced_workflows": {
                    "title": "Building Advanced Workflows",
                    "steps": [
                        {
                            "title": "Interactive Workflow Builder",
                            "description": "Use the guided workflow builder",
                            "command": "claude-flow interactive workflow",
                            "explanation": "Step-by-step workflow creation with validation"
                        },
                        {
                            "title": "Add Conditional Logic",
                            "description": "Create workflows with decision points",
                            "command": "# In workflow builder, add condition step",
                            "explanation": "Workflows can branch based on conditions"
                        }
                    ]
                }
            },
            "examples": {
                "common_workflows": [
                    {
                        "title": "Development Team Simulation",
                        "description": "Simulate a complete development team workflow",
                        "commands": [
                            "claude-flow swarm create dev-team --agents 8",
                            "claude-flow swarm spawn dev-team architect1 --type architect",
                            "claude-flow swarm spawn dev-team coder1 --type coder",
                            "claude-flow swarm spawn dev-team coder2 --type coder",
                            "claude-flow swarm spawn dev-team tester1 --type tester",
                            "claude-flow swarm spawn dev-team reviewer1 --type reviewer",
                            "claude-flow swarm assign dev-team 'Build user authentication system' --priority 8",
                            "claude-flow swarm status dev-team --watch"
                        ]
                    },
                    {
                        "title": "Neural-Powered Task Analysis",
                        "description": "Use AI to analyze and optimize task distribution",
                        "commands": [
                            "claude-flow neural classify 'Optimize database queries' --context production",
                            "claude-flow neural estimate 'Implement OAuth2' --type complexity",
                            "claude-flow neural pattern-match 'authentication patterns' --threshold 0.8",
                            "claude-flow neural optimize-assignment agents.json tasks.json"
                        ]
                    }
                ]
            },
            "troubleshooting": {
                "common_issues": [
                    {
                        "issue": "Swarm agents not responding",
                        "solutions": [
                            "Check agent status: claude-flow swarm status <session-id>",
                            "Restart failed agents: claude-flow swarm restart <session-id> <agent-id>",
                            "Check system resources: claude-flow status"
                        ]
                    },
                    {
                        "issue": "Memory operations timing out",
                        "solutions": [
                            "Check memory backend status: claude-flow memory stats",
                            "Optimize memory usage: claude-flow memory optimize",
                            "Verify connection settings in config"
                        ]
                    }
                ]
            }
        }
    
    def show_overview(self):
        """Show help overview."""
        self.console.print("\n[bold blue]📚 Claude-Flow Help System[/bold blue]\n")
        
        # Categories overview
        categories_table = Table(title="Available Commands", box=box.ROUNDED)
        categories_table.add_column("Category", style="cyan", width=20)
        categories_table.add_column("Description", style="white")
        categories_table.add_column("Icon", style="yellow", width=6)
        
        for cat_name, cat_info in self.help_data["categories"].items():
            categories_table.add_row(
                cat_info["title"],
                cat_info["description"],
                cat_info["icon"]
            )
        
        self.console.print(categories_table)
        
        # Quick help tips
        tips = Panel(
            "[bold]Quick Tips:[/bold]\n\n"
            "• Use [cyan]--help[/cyan] with any command for detailed information\n"
            "• Try [cyan]claude-flow interactive setup[/cyan] for guided configuration\n"
            "• Use [cyan]claude-flow help examples[/cyan] to see common workflows\n"
            "• Run [cyan]claude-flow help tutorial[/cyan] for step-by-step guides",
            title="Getting Help",
            border_style="green"
        )
        self.console.print(tips)
    
    def show_command_help(self, category: str, command: Optional[str] = None):
        """Show detailed help for specific command."""
        if category not in self.help_data["categories"]:
            self.console.print(f"[red]Unknown category: {category}[/red]")
            return
        
        cat_data = self.help_data["categories"][category]
        
        if command is None:
            # Show all commands in category
            self.console.print(f"\n[bold]{cat_data['icon']} {cat_data['title']} Commands[/bold]\n")
            
            for cmd_name, cmd_data in cat_data["commands"].items():
                panel_content = (
                    f"[bold]{cmd_data['description']}[/bold]\n\n"
                    f"[cyan]Usage:[/cyan] {cmd_data['usage']}\n\n"
                )
                
                if "examples" in cmd_data:
                    panel_content += "[cyan]Examples:[/cyan]\n"
                    for example in cmd_data["examples"]:
                        panel_content += f"  {example['command']}\n"
                        panel_content += f"  → {example['description']}\n\n"
                
                panel = Panel(
                    panel_content.strip(),
                    title=f"{category} {cmd_name}",
                    border_style="blue"
                )
                self.console.print(panel)
        else:
            # Show specific command
            if command not in cat_data["commands"]:
                self.console.print(f"[red]Unknown command: {category} {command}[/red]")
                return
            
            cmd_data = cat_data["commands"][command]
            self._show_detailed_command_help(category, command, cmd_data)
    
    def _show_detailed_command_help(self, category: str, command: str, cmd_data: Dict[str, Any]):
        """Show detailed help for a specific command."""
        # Command header
        header = Text.assemble(
            (f"{self.help_data['categories'][category]['icon']} ", "yellow"),
            (f"{category} {command}", "bold blue")
        )
        
        self.console.print(Panel(
            Align.center(header),
            style="bold blue"
        ))
        
        # Description
        self.console.print(f"\n[bold]Description:[/bold] {cmd_data['description']}\n")
        
        # Usage
        usage_panel = Panel(
            f"[bold cyan]{cmd_data['usage']}[/bold cyan]",
            title="Usage",
            border_style="cyan"
        )
        self.console.print(usage_panel)
        
        # Options (if available)
        if "options" in cmd_data:
            options_table = Table(title="Options", box=None)
            options_table.add_column("Option", style="cyan")
            options_table.add_column("Description", style="white")
            
            for option, desc in cmd_data["options"]:
                options_table.add_row(option, desc)
            
            self.console.print(options_table)
        
        # Examples
        if "examples" in cmd_data:
            for i, example in enumerate(cmd_data["examples"], 1):
                example_panel = Panel(
                    f"[bold]Command:[/bold]\n"
                    f"[green]{example['command']}[/green]\n\n"
                    f"[bold]Description:[/bold]\n"
                    f"{example['description']}",
                    title=f"Example {i}",
                    border_style="green"
                )
                self.console.print(example_panel)
    
    def show_examples(self):
        """Show example workflows and use cases."""
        self.console.print("\n[bold blue]💡 Claude-Flow Examples[/bold blue]\n")
        
        for example in self.help_data["examples"]["common_workflows"]:
            # Create command sequence display
            commands_text = "\n".join(f"$ {cmd}" for cmd in example["commands"])
            
            example_panel = Panel(
                f"[bold]{example['description']}[/bold]\n\n"
                f"[dim]Commands:[/dim]\n"
                f"[green]{commands_text}[/green]",
                title=example["title"],
                border_style="yellow"
            )
            self.console.print(example_panel)
    
    def show_tutorial(self, tutorial_name: Optional[str] = None):
        """Show interactive tutorials."""
        if tutorial_name is None:
            self._show_tutorial_list()
            return
        
        if tutorial_name not in self.help_data["tutorials"]:
            self.console.print(f"[red]Unknown tutorial: {tutorial_name}[/red]")
            self._show_tutorial_list()
            return
        
        tutorial = self.help_data["tutorials"][tutorial_name]
        self._show_tutorial_steps(tutorial)
    
    def _show_tutorial_list(self):
        """Show available tutorials."""
        self.console.print("\n[bold blue]📖 Available Tutorials[/bold blue]\n")
        
        tutorials_table = Table(box=None)
        tutorials_table.add_column("Tutorial", style="cyan")
        tutorials_table.add_column("Description", style="white")
        
        for name, tutorial in self.help_data["tutorials"].items():
            tutorials_table.add_row(name, tutorial["title"])
        
        self.console.print(tutorials_table)
        self.console.print("\n[dim]Use: claude-flow help tutorial <name>[/dim]")
    
    def _show_tutorial_steps(self, tutorial: Dict[str, Any]):
        """Show tutorial steps."""
        self.console.print(f"\n[bold blue]📖 {tutorial['title']}[/bold blue]\n")
        
        for i, step in enumerate(tutorial["steps"], 1):
            step_panel = Panel(
                f"[bold]{step['description']}[/bold]\n\n"
                f"[cyan]Command:[/cyan]\n"
                f"[green]{step['command']}[/green]\n\n"
                f"[cyan]Explanation:[/cyan]\n"
                f"{step['explanation']}",
                title=f"Step {i}: {step['title']}",
                border_style="blue"
            )
            self.console.print(step_panel)
    
    def show_troubleshooting(self):
        """Show troubleshooting guide."""
        self.console.print("\n[bold blue]🔧 Troubleshooting Guide[/bold blue]\n")
        
        for issue_data in self.help_data["troubleshooting"]["common_issues"]:
            solutions_text = "\n".join(f"• {solution}" for solution in issue_data["solutions"])
            
            issue_panel = Panel(
                f"[bold red]Problem:[/bold red]\n"
                f"{issue_data['issue']}\n\n"
                f"[bold green]Solutions:[/bold green]\n"
                f"{solutions_text}",
                title="Common Issue",
                border_style="yellow"
            )
            self.console.print(issue_panel)
    
    def start_interactive_help(self):
        """Start interactive help session."""
        self.console.print("\n[bold blue]🎯 Interactive Help System[/bold blue]\n")
        
        from rich.prompt import Prompt
        
        while True:
            choice = Prompt.ask(
                "What would you like help with?",
                choices=["commands", "examples", "tutorials", "troubleshooting", "quit"],
                default="commands"
            )
            
            if choice == "quit":
                break
            elif choice == "commands":
                category = Prompt.ask(
                    "Which category?",
                    choices=list(self.help_data["categories"].keys()) + ["all"],
                    default="all"
                )
                if category == "all":
                    self.show_overview()
                else:
                    self.show_command_help(category)
            elif choice == "examples":
                self.show_examples()
            elif choice == "tutorials":
                tutorial = Prompt.ask(
                    "Which tutorial?",
                    choices=list(self.help_data["tutorials"].keys()) + ["list"],
                    default="list"
                )
                if tutorial == "list":
                    self._show_tutorial_list()
                else:
                    self.show_tutorial(tutorial)
            elif choice == "troubleshooting":
                self.show_troubleshooting()
            
            self.console.print("\n" + "="*50 + "\n")
        
        self.console.print("[green]Thanks for using Claude-Flow help![/green]")