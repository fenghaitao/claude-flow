"""
Logging system for Claude-Flow
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme
from .config import config


class Logger:
    """Enhanced logger with rich formatting and structured logging"""
    
    def __init__(self, name: str = "claude-flow", level: Optional[str] = None):
        self.name = name
        self.logger = logging.getLogger(name)
        
        # Set log level
        log_level = level or config.logging.level
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup logging handlers"""
        # Console handler with rich formatting
        console = Console(theme=Theme({
            "info": "cyan",
            "warning": "yellow",
            "error": "red",
            "critical": "red bold",
            "debug": "dim"
        }))
        
        console_handler = RichHandler(
            console=console,
            show_time=True,
            show_path=True,
            markup=True
        )
        console_handler.setLevel(logging.INFO)
        
        # File handler for persistent logging
        if config.logging.file:
            log_file = Path(config.logging.file)
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=config.logging.max_size,
                backupCount=config.logging.backup_count
            )
            file_handler.setLevel(logging.DEBUG)
            
            # File formatter
            file_formatter = logging.Formatter(
                fmt=config.logging.format,
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
        
        # Console formatter
        console_formatter = logging.Formatter(
            fmt="%(message)s",
            datefmt="%H:%M:%S"
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self.logger.error(message, extra=kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self.logger.critical(message, extra=kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log exception with traceback"""
        self.logger.exception(message, extra=kwargs)
    
    def log_structured(self, level: str, message: str, data: Dict[str, Any]):
        """Log structured data"""
        log_method = getattr(self.logger, level.lower())
        log_method(f"{message} | {data}")
    
    def log_agent_action(self, agent_id: str, action: str, details: Dict[str, Any]):
        """Log agent-specific actions"""
        self.info(f"Agent {agent_id}: {action}", agent_id=agent_id, action=action, **details)
    
    def log_swarm_event(self, event_type: str, event_data: Dict[str, Any]):
        """Log swarm coordination events"""
        self.info(f"Swarm Event: {event_type}", event_type=event_type, **event_data)
    
    def log_mcp_call(self, tool: str, params: Dict[str, Any], result: Any):
        """Log MCP tool calls"""
        self.debug(f"MCP Tool: {tool}", tool=tool, params=params, result=result)
    
    def log_claude_request(self, model: str, prompt_length: int, response_length: int):
        """Log Claude API requests"""
        self.info(f"Claude Request: {model}", model=model, prompt_length=prompt_length, response_length=response_length)
    
    def set_level(self, level: str):
        """Set logging level"""
        self.logger.setLevel(getattr(logging, level.upper()))
    
    def add_handler(self, handler: logging.Handler):
        """Add custom logging handler"""
        self.logger.addHandler(handler)
    
    def remove_handler(self, handler: logging.Handler):
        """Remove logging handler"""
        self.logger.removeHandler(handler)


# Global logger instance
logger = Logger()


def get_logger(name: str) -> Logger:
    """Get logger instance by name"""
    return Logger(name)


# Convenience functions
def debug(message: str, **kwargs):
    """Global debug log"""
    logger.debug(message, **kwargs)


def info(message: str, **kwargs):
    """Global info log"""
    logger.info(message, **kwargs)


def warning(message: str, **kwargs):
    """Global warning log"""
    logger.warning(message, **kwargs)


def error(message: str, **kwargs):
    """Global error log"""
    logger.error(message, **kwargs)


def critical(message: str, **kwargs):
    """Global critical log"""
    logger.critical(message, **kwargs)


def exception(message: str, **kwargs):
    """Global exception log"""
    logger.exception(message, **kwargs)
