"""
Progress Management with Rich - Advanced Progress Bars and Status Displays.

This module provides comprehensive progress tracking, status displays,
and visual feedback for long-running operations.
"""

import asyncio
import time
from typing import Optional, Dict, Any, List, Callable
from contextlib import asynccontextmanager
from rich.console import Console
from rich.progress import (
    Progress, BarColumn, TextColumn, TimeRemainingColumn, 
    SpinnerColumn, MofNCompleteColumn, PercentageColumn,
    TaskID, ProgressColumn
)
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich.align import Align
from rich import box


class TransferSpeedColumn(ProgressColumn):
    """Custom column showing transfer speed."""
    
    def render(self, task):
        speed = task.fields.get("speed")
        if speed is None:
            return Text("", style="progress.percentage")
        return Text(f"{speed:.1f} it/s", style="bright_blue")


class ETAColumn(ProgressColumn):
    """Custom column showing estimated time of arrival."""
    
    def render(self, task):
        if task.remaining is None or task.speed is None or task.speed == 0:
            return Text("", style="progress.remaining")
        
        eta_seconds = task.remaining / task.speed
        if eta_seconds < 60:
            return Text(f"~{eta_seconds:.0f}s", style="bright_green")
        elif eta_seconds < 3600:
            return Text(f"~{eta_seconds/60:.1f}m", style="bright_green")
        else:
            return Text(f"~{eta_seconds/3600:.1f}h", style="bright_green")


class ProgressManager:
    """
    Advanced progress management with Rich integration.
    """
    
    def __init__(self, console: Console):
        self.console = console
        self.progress_instances: Dict[str, Progress] = {}
        self.active_tasks: Dict[str, TaskID] = {}
        self.layouts: Dict[str, Layout] = {}
        
    def create_progress(self, 
                       progress_id: str,
                       columns: Optional[List[ProgressColumn]] = None,
                       **kwargs) -> Progress:
        """Create a new progress instance."""
        if columns is None:
            columns = [
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                PercentageColumn(),
                MofNCompleteColumn(),
                TransferSpeedColumn(),
                ETAColumn(),
                TimeRemainingColumn()
            ]
        
        progress = Progress(*columns, console=self.console, **kwargs)
        self.progress_instances[progress_id] = progress
        return progress
    
    def get_progress(self, progress_id: str) -> Optional[Progress]:
        """Get existing progress instance."""
        return self.progress_instances.get(progress_id)
    
    def remove_progress(self, progress_id: str) -> None:
        """Remove progress instance."""
        if progress_id in self.progress_instances:
            del self.progress_instances[progress_id]
        if progress_id in self.active_tasks:
            del self.active_tasks[progress_id]
    
    @asynccontextmanager
    async def progress_context(self, 
                              progress_id: str,
                              description: str,
                              total: Optional[int] = None,
                              **kwargs):
        """Context manager for progress tracking."""
        progress = self.create_progress(progress_id, **kwargs)
        
        with progress:
            task_id = progress.add_task(description, total=total)
            self.active_tasks[progress_id] = task_id
            
            try:
                yield progress, task_id
            finally:
                progress.remove_task(task_id)
                self.remove_progress(progress_id)
    
    def create_multi_progress_layout(self, title: str) -> Layout:
        """Create layout for multiple progress bars."""
        layout = Layout()
        
        # Header
        header = Panel(
            Align.center(Text(title, style="bold bright_blue")),
            box=box.ROUNDED,
            padding=(1, 2),
            style="bright_blue"
        )
        
        # Progress area
        progress_area = Layout(name="progress")
        
        # Footer
        footer = Layout(size=3, name="footer")
        
        layout.split_column(
            Layout(header, name="header", size=5),
            progress_area,
            footer
        )
        
        return layout
    
    def show_operation_progress(self,
                               title: str,
                               operations: List[Dict[str, Any]],
                               update_callback: Optional[Callable] = None):
        """Show progress for multiple operations."""
        layout = self.create_multi_progress_layout(title)
        
        # Create progress for each operation
        progress_bars = {}
        for i, op in enumerate(operations):
            progress = Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                PercentageColumn(),
                TransferSpeedColumn(),
                console=self.console
            )
            
            task_id = progress.add_task(
                op.get("description", f"Operation {i+1}"),
                total=op.get("total", 100)
            )
            
            progress_bars[f"op_{i}"] = {
                "progress": progress,
                "task_id": task_id,
                "operation": op
            }
        
        # Update layout with progress bars
        progress_layout = Layout()
        progress_parts = []
        
        for pb_data in progress_bars.values():
            progress_parts.append(Layout(pb_data["progress"]))
        
        progress_layout.split_column(*progress_parts)
        layout["progress"].update(progress_layout)
        
        return layout, progress_bars
    
    async def simulate_work_with_progress(self,
                                        description: str,
                                        total_steps: int = 100,
                                        step_delay: float = 0.1,
                                        variable_speed: bool = False) -> None:
        """Simulate work with progress visualization."""
        async with self.progress_context("work_sim", description, total_steps) as (progress, task_id):
            for i in range(total_steps):
                # Variable speed simulation
                if variable_speed:
                    delay = step_delay * (0.5 + (i % 10) * 0.1)
                else:
                    delay = step_delay
                
                await asyncio.sleep(delay)
                
                # Update speed calculation
                speed = 1.0 / delay if delay > 0 else 1.0
                progress.update(task_id, advance=1, speed=speed)
    
    def create_status_dashboard(self, 
                               title: str,
                               status_data: Dict[str, Any]) -> Panel:
        """Create a status dashboard panel."""
        table = Table(box=None, padding=(0, 1))
        table.add_column("Component", style="cyan", width=20)
        table.add_column("Status", style="white", width=15)
        table.add_column("Details", style="dim white")
        
        for component, info in status_data.items():
            if isinstance(info, dict):
                status = info.get("status", "Unknown")
                details = info.get("details", "")
                
                # Color code status
                if status.lower() in ["running", "active", "ok"]:
                    status = f"[green]{status}[/green]"
                elif status.lower() in ["warning", "degraded"]:
                    status = f"[yellow]{status}[/yellow]"
                elif status.lower() in ["error", "failed", "down"]:
                    status = f"[red]{status}[/red]"
                
                table.add_row(component.title(), status, str(details))
            else:
                table.add_row(component.title(), str(info), "")
        
        return Panel(
            table,
            title=title,
            border_style="bright_blue",
            padding=(1, 2)
        )
    
    def create_metrics_panel(self, 
                           metrics: Dict[str, Any],
                           title: str = "Metrics") -> Panel:
        """Create metrics display panel."""
        table = Table(box=None, show_header=False)
        table.add_column("Metric", style="cyan", width=25)
        table.add_column("Value", style="bright_white", justify="right")
        
        for metric, value in metrics.items():
            # Format different types of values
            if isinstance(value, float):
                if 0 <= value <= 1:
                    formatted_value = f"{value:.1%}"
                else:
                    formatted_value = f"{value:.2f}"
            elif isinstance(value, int):
                if value > 1000000:
                    formatted_value = f"{value/1000000:.1f}M"
                elif value > 1000:
                    formatted_value = f"{value/1000:.1f}K"
                else:
                    formatted_value = str(value)
            else:
                formatted_value = str(value)
            
            table.add_row(metric.replace("_", " ").title(), formatted_value)
        
        return Panel(
            table,
            title=title,
            border_style="bright_green",
            padding=(1, 2)
        )
    
    async def show_live_dashboard(self,
                                 title: str,
                                 data_callback: Callable,
                                 refresh_rate: float = 1.0,
                                 duration: Optional[float] = None):
        """Show live updating dashboard."""
        layout = Layout()
        
        start_time = time.time()
        
        with Live(layout, console=self.console, refresh_per_second=refresh_rate) as live:
            try:
                while True:
                    # Get fresh data
                    data = await data_callback()
                    
                    # Update layout
                    if "status" in data:
                        status_panel = self.create_status_dashboard(
                            "System Status", 
                            data["status"]
                        )
                    else:
                        status_panel = Panel("No status data", title="Status")
                    
                    if "metrics" in data:
                        metrics_panel = self.create_metrics_panel(
                            data["metrics"],
                            "Performance Metrics"
                        )
                    else:
                        metrics_panel = Panel("No metrics data", title="Metrics")
                    
                    # Create header
                    header = Panel(
                        Align.center(Text(title, style="bold bright_blue")),
                        style="bright_blue"
                    )
                    
                    # Update layout
                    layout.split_column(
                        Layout(header, size=3),
                        Layout().split_row(status_panel, metrics_panel)
                    )
                    
                    # Check duration
                    if duration and (time.time() - start_time) >= duration:
                        break
                    
                    await asyncio.sleep(1.0 / refresh_rate)
                    
            except KeyboardInterrupt:
                pass
    
    def create_progress_spinner(self, message: str) -> Progress:
        """Create a simple spinner progress."""
        return Progress(
            SpinnerColumn(),
            TextColumn(f"[progress.description]{message}"),
            console=self.console,
            transient=True
        )
    
    @asynccontextmanager
    async def spinner(self, message: str):
        """Context manager for spinner."""
        progress = self.create_progress_spinner(message)
        with progress:
            task_id = progress.add_task("", total=None)
            try:
                yield progress
            finally:
                progress.remove_task(task_id)


# Global progress manager instance
_progress_manager: Optional[ProgressManager] = None


def get_progress_manager(console: Optional[Console] = None) -> ProgressManager:
    """Get global progress manager instance."""
    global _progress_manager
    if _progress_manager is None:
        if console is None:
            console = Console()
        _progress_manager = ProgressManager(console)
    return _progress_manager