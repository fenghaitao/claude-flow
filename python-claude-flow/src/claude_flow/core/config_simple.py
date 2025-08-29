"""
Simplified Configuration for Claude-Flow

This module provides basic configuration management without external dependencies.
"""

import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime


class DatabaseConfig:
    """Database configuration"""
    
    def __init__(self):
        self.host: str = "localhost"
        self.port: int = 5432
        self.name: str = "claude_flow"
        self.user: str = "claude_flow"
        self.password: str = ""
        self.ssl_mode: str = "prefer"
        self.max_connections: int = 20
        self.connection_timeout: int = 30
        self.statement_timeout: int = 300
        self.idle_in_transaction_timeout: int = 300


class MCPConfig:
    """MCP (Model Context Protocol) configuration"""
    
    def __init__(self):
        self.server_url: str = "ws://localhost:3000"
        self.api_key: str = ""
        self.timeout: int = 30
        self.max_retries: int = 3
        self.retry_delay: float = 1.0
        self.heartbeat_interval: int = 30
        self.auto_reconnect: bool = True
        self.max_message_size: int = 1024 * 1024  # 1MB


class ClaudeConfig:
    """Claude AI configuration"""
    
    def __init__(self):
        self.api_key: str = ""
        self.model: str = "claude-3-sonnet-20240229"
        self.max_tokens: int = 4096
        self.temperature: float = 0.7
        self.top_p: float = 0.9
        self.frequency_penalty: float = 0.0
        self.presence_penalty: float = 0.0
        self.timeout: int = 60
        self.max_retries: int = 3
        self.retry_delay: float = 1.0


class SwarmConfig:
    """Swarm coordination configuration"""
    
    def __init__(self):
        self.max_agents: int = 100
        self.coordination_interval: float = 1.0
        self.heartbeat_timeout: float = 30.0
        self.election_timeout: float = 150.0
        self.max_retries: int = 3
        self.retry_delay: float = 1.0
        self.load_balancing: bool = True
        self.fault_tolerance: bool = True
        self.auto_scaling: bool = True


class LoggingConfig:
    """Logging configuration"""
    
    def __init__(self):
        self.level: str = "INFO"
        self.format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        self.file: Optional[str] = None
        self.max_size: int = 10 * 1024 * 1024  # 10MB
        self.backup_count: int = 5
        self.console_output: bool = True
        self.file_output: bool = False
        self.structured_logging: bool = True


class Config:
    """Main configuration class"""
    
    def __init__(self):
        # Application info
        self.app_name: str = "Claude-Flow"
        self.version: str = "1.0.0"
        self.description: str = "Enterprise-grade AI agent orchestration platform"
        
        # Base directories
        self.base_dir: Path = Path.home() / ".claude-flow"
        self.config_dir: Path = self.base_dir / "config"
        self.data_dir: Path = self.base_dir / "data"
        self.logs_dir: Path = self.base_dir / "logs"
        self.cache_dir: Path = self.base_dir / "cache"
        self.swarm_dir: Path = self.base_dir / "swarm"
        
        # Sub-configurations
        self.database = DatabaseConfig()
        self.mcp = MCPConfig()
        self.claude = ClaudeConfig()
        self.swarm = SwarmConfig()
        self.logging = LoggingConfig()
        
        # Feature flags
        self._feature_flags: Dict[str, bool] = {
            "swarm_coordination": True,
            "hive_mind": True,
            "neural_networks": True,
            "mcp_tools": True,
            "memory_persistence": True,
            "auto_scaling": True,
            "fault_tolerance": True,
            "load_balancing": True,
            "monitoring": True,
            "analytics": True
        }
        
        # Load environment variables
        self._load_env_vars()
        
        # Create directories
        self._create_directories()
    
    def _load_env_vars(self) -> None:
        """Load configuration from environment variables"""
        # Claude API
        if os.getenv("CLAUDE_API_KEY"):
            self.claude.api_key = os.getenv("CLAUDE_API_KEY")
        
        # MCP
        if os.getenv("MCP_SERVER_URL"):
            self.mcp.server_url = os.getenv("MCP_SERVER_URL")
        if os.getenv("MCP_API_KEY"):
            self.mcp.api_key = os.getenv("MCP_API_KEY")
        
        # Database
        if os.getenv("DB_HOST"):
            self.database.host = os.getenv("DB_HOST")
        if os.getenv("DB_PORT"):
            self.database.port = int(os.getenv("DB_PORT"))
        if os.getenv("DB_NAME"):
            self.database.name = os.getenv("DB_NAME")
        if os.getenv("DB_USER"):
            self.database.user = os.getenv("DB_USER")
        if os.getenv("DB_PASSWORD"):
            self.database.password = os.getenv("DB_PASSWORD")
        
        # Logging
        if os.getenv("LOG_LEVEL"):
            self.logging.level = os.getenv("LOG_LEVEL")
    
    def _create_directories(self) -> None:
        """Create necessary directories"""
        for directory in [self.config_dir, self.data_dir, self.logs_dir, self.cache_dir, self.swarm_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def save(self, file_path: Optional[Union[str, Path]] = None) -> None:
        """Save configuration to file"""
        if file_path is None:
            file_path = self.config_dir / "config.json"
        
        config_data = {
            "app_name": self.app_name,
            "version": self.version,
            "description": self.description,
            "database": {
                "host": self.database.host,
                "port": self.database.port,
                "name": self.database.name,
                "user": self.database.user,
                "ssl_mode": self.database.ssl_mode,
                "max_connections": self.database.max_connections,
                "connection_timeout": self.database.connection_timeout,
                "statement_timeout": self.database.statement_timeout,
                "idle_in_transaction_timeout": self.database.idle_in_transaction_timeout
            },
            "mcp": {
                "server_url": self.mcp.server_url,
                "timeout": self.mcp.timeout,
                "max_retries": self.mcp.max_retries,
                "retry_delay": self.mcp.retry_delay,
                "heartbeat_interval": self.mcp.heartbeat_interval,
                "auto_reconnect": self.mcp.auto_reconnect,
                "max_message_size": self.mcp.max_message_size
            },
            "claude": {
                "model": self.claude.model,
                "max_tokens": self.claude.max_tokens,
                "temperature": self.claude.temperature,
                "top_p": self.claude.top_p,
                "frequency_penalty": self.claude.frequency_penalty,
                "presence_penalty": self.claude.presence_penalty,
                "timeout": self.claude.timeout,
                "max_retries": self.claude.max_retries,
                "retry_delay": self.claude.retry_delay
            },
            "swarm": {
                "max_agents": self.swarm.max_agents,
                "coordination_interval": self.swarm.coordination_interval,
                "heartbeat_timeout": self.swarm.heartbeat_timeout,
                "election_timeout": self.swarm.election_timeout,
                "max_retries": self.swarm.max_retries,
                "retry_delay": self.swarm.retry_delay,
                "load_balancing": self.swarm.load_balancing,
                "fault_tolerance": self.swarm.fault_tolerance,
                "auto_scaling": self.swarm.auto_scaling
            },
            "logging": {
                "level": self.logging.level,
                "format": self.logging.format,
                "file": self.logging.file,
                "max_size": self.logging.max_size,
                "backup_count": self.logging.backup_count,
                "console_output": self.logging.console_output,
                "file_output": self.logging.file_output,
                "structured_logging": self.logging.structured_logging
            },
            "feature_flags": self._feature_flags.copy(),
            "last_updated": datetime.now().isoformat()
        }
        
        with open(file_path, 'w') as f:
            json.dump(config_data, f, indent=2)
    
    def load(self, file_path: Union[str, Path]) -> None:
        """Load configuration from file"""
        with open(file_path, 'r') as f:
            config_data = json.load(f)
        
        # Update configuration from loaded data
        if "database" in config_data:
            db_data = config_data["database"]
            for key, value in db_data.items():
                if hasattr(self.database, key):
                    setattr(self.database, key, value)
        
        if "mcp" in config_data:
            mcp_data = config_data["mcp"]
            for key, value in mcp_data.items():
                if hasattr(self.mcp, key):
                    setattr(self.mcp, key, value)
        
        if "claude" in config_data:
            claude_data = config_data["claude"]
            for key, value in claude_data.items():
                if hasattr(self.claude, key):
                    setattr(self.claude, key, value)
        
        if "swarm" in config_data:
            swarm_data = config_data["swarm"]
            for key, value in swarm_data.items():
                if hasattr(self.swarm, key):
                    setattr(self.swarm, key, value)
        
        if "logging" in config_data:
            logging_data = config_data["logging"]
            for key, value in logging_data.items():
                if hasattr(self.logging, key):
                    setattr(self.logging, key, value)
        
        if "feature_flags" in config_data:
            self._feature_flags.update(config_data["feature_flags"])
    
    def get_feature_flag(self, flag_name: str) -> bool:
        """Get a feature flag value"""
        return self._feature_flags.get(flag_name, False)
    
    def set_feature_flag(self, flag_name: str, value: bool) -> None:
        """Set a feature flag value"""
        self._feature_flags[flag_name] = value
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        # Check required fields
        if not self.claude.api_key:
            errors.append("CLAUDE_API_KEY is required")
        
        if not self.mcp.api_key:
            errors.append("MCP_API_KEY is required")
        
        # Validate ranges
        if not (0 <= self.claude.temperature <= 2):
            errors.append("Claude temperature must be between 0 and 2")
        
        if not (0 <= self.claude.top_p <= 1):
            errors.append("Claude top_p must be between 0 and 1")
        
        if self.swarm.max_agents <= 0:
            errors.append("Swarm max_agents must be positive")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "app_name": self.app_name,
            "version": self.version,
            "description": self.description,
            "base_dir": str(self.base_dir),
            "config_dir": str(self.config_dir),
            "data_dir": str(self.data_dir),
            "logs_dir": str(self.logs_dir),
            "cache_dir": str(self.cache_dir),
            "swarm_dir": str(self.swarm_dir),
            "feature_flags": self._feature_flags.copy()
        }


# Global configuration instance
config = Config()
