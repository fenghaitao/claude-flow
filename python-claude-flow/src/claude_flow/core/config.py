"""
Enhanced configuration module for Claude-Flow

This module provides the complete configuration system with Pydantic validation,
environment variable support, and file-based configuration loading.
"""

import os
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from .config_models import ClaudeFlowConfig
from .config_manager import ConfigManager, get_config_manager, initialize_config
import logging

logger = logging.getLogger(__name__)


class Config:
    """
    Enhanced configuration class with full Pydantic validation
    
    This replaces the simplified config_simple.py while maintaining compatibility.
    """
    
    def __init__(self):
        self._manager: Optional[ConfigManager] = None
        self._config: Optional[ClaudeFlowConfig] = None
        self._initialized = False
    
    @property
    def manager(self) -> ConfigManager:
        """Get the configuration manager"""
        if self._manager is None:
            self._manager = get_config_manager()
        return self._manager
    
    @property
    def data(self) -> ClaudeFlowConfig:
        """Get the configuration data"""
        if not self._initialized:
            raise RuntimeError("Configuration not initialized. Call initialize() first.")
        return self.manager.config
    
    @property
    def version(self) -> str:
        """Get the application version"""
        try:
            return self.data.version
        except:
            return "2.0.0-alpha.90"
    
    @property
    def app_name(self) -> str:
        """Get the application name"""
        try:
            return self.data.app_name
        except:
            return "Claude-Flow"
    
    @property
    def environment(self) -> str:
        """Get the current environment"""
        try:
            return self.data.environment.value
        except:
            return "development"
    
    @property
    def debug(self) -> bool:
        """Check if debug mode is enabled"""
        try:
            return self.data.debug
        except:
            return False
    
    async def initialize(self, 
                        config_files: Optional[List[str]] = None,
                        auto_discover: bool = True,
                        hot_reload: bool = False) -> ClaudeFlowConfig:
        """
        Initialize the configuration system
        
        Args:
            config_files: List of configuration file paths
            auto_discover: Automatically discover configuration files
            hot_reload: Enable hot reloading of configuration files
            
        Returns:
            Loaded configuration
        """
        try:
            # Auto-discover configuration files if enabled
            if auto_discover:
                discovered_files = self._discover_config_files()
                if config_files:
                    config_files.extend(discovered_files)
                else:
                    config_files = discovered_files
            
            # Initialize configuration
            self._config = await initialize_config(
                config_files=config_files,
                hot_reload=hot_reload
            )
            
            self._initialized = True
            
            logger.info(f"Configuration initialized successfully")
            logger.info(f"Environment: {self._config.environment.value}")
            logger.info(f"Debug mode: {self._config.debug}")
            
            return self._config
            
        except Exception as e:
            logger.error(f"Configuration initialization failed: {e}")
            raise
    
    def _discover_config_files(self) -> List[str]:
        """Discover configuration files in standard locations"""
        potential_files = [
            # Current directory
            "claude-flow.yaml",
            "claude-flow.yml", 
            "claude-flow.json",
            ".claude-flow.yaml",
            ".claude-flow.yml",
            ".claude-flow.json",
            
            # Config directory
            "config/default.yaml",
            "config/default.yml",
            "config/local.yaml",
            "config/local.yml",
            "config/development.yaml",
            "config/production.yaml",
            "config/staging.yaml",
            
            # Home directory
            os.path.expanduser("~/.claude-flow.yaml"),
            os.path.expanduser("~/.config/claude-flow/config.yaml"),
            
            # System-wide
            "/etc/claude-flow/config.yaml",
        ]
        
        discovered = []
        for file_path in potential_files:
            if Path(file_path).exists():
                discovered.append(file_path)
                logger.debug(f"Discovered configuration file: {file_path}")
        
        return discovered
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation
        
        Args:
            key: Configuration key (e.g., 'database.host')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        if not self._initialized:
            return default
        
        return self.manager.get_config_value(key, default)
    
    def set(self, key: str, value: Any, reload: bool = False) -> None:
        """
        Set a configuration value (runtime override)
        
        Args:
            key: Configuration key using dot notation
            value: Value to set
            reload: Whether to reload configuration after setting
        """
        if not self._initialized:
            raise RuntimeError("Configuration not initialized")
        
        self.manager.set_config_value(key, value, reload)
    
    def reload(self) -> None:
        """Reload configuration from all sources"""
        if not self._initialized:
            raise RuntimeError("Configuration not initialized")
        
        asyncio.create_task(self.manager.reload_config())
    
    def export(self, file_path: str, format: str = "yaml", exclude_sensitive: bool = True) -> None:
        """
        Export current configuration to a file
        
        Args:
            file_path: Output file path
            format: Output format (yaml, json, toml)
            exclude_sensitive: Whether to exclude sensitive data
        """
        if not self._initialized:
            raise RuntimeError("Configuration not initialized")
        
        self.manager.export_config(file_path, format, exclude_sensitive)
    
    def validate(self) -> bool:
        """Validate the current configuration"""
        if not self._initialized:
            return False
        
        return self.manager.validate_config()
    
    def get_sources(self) -> List[Dict[str, Any]]:
        """Get information about configuration sources"""
        if not self._initialized:
            return []
        
        return self.manager.get_config_sources()
    
    def to_dict(self, exclude_sensitive: bool = True) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        if not self._initialized:
            return {}
        
        return self.data.to_dict(exclude_sensitive=exclude_sensitive)
    
    # Backward compatibility properties
    @property
    def claude_api_key(self) -> str:
        """Get Claude API key"""
        return self.get("claude.api_key", "")
    
    @property
    def database_url(self) -> str:
        """Get database URL"""
        return self.get("database.url", "sqlite:///claude_flow.db")
    
    @property
    def redis_url(self) -> str:
        """Get Redis URL"""
        if not self._initialized:
            return "redis://localhost:6379/0"
        return self.data.get_redis_url()
    
    @property
    def log_level(self) -> str:
        """Get log level"""
        return self.get("logging.level", "INFO")
    
    @property
    def max_agents(self) -> int:
        """Get maximum number of agents"""
        return self.get("agents.max_agents", 50)


# Global configuration instance
config = Config()


# Utility functions for easy access
def get_config() -> Config:
    """Get the global configuration instance"""
    return config


def get_value(key: str, default: Any = None) -> Any:
    """Get a configuration value"""
    return config.get(key, default)


def set_value(key: str, value: Any, reload: bool = False) -> None:
    """Set a configuration value"""
    config.set(key, value, reload)


async def init_config(config_files: Optional[List[str]] = None,
                     hot_reload: bool = False) -> ClaudeFlowConfig:
    """
    Initialize the configuration system
    
    Args:
        config_files: List of configuration file paths
        hot_reload: Enable hot reloading
        
    Returns:
        Loaded configuration
    """
    return await config.initialize(config_files=config_files, hot_reload=hot_reload)


# Environment variable helpers
def load_env_file(file_path: str = ".env") -> None:
    """
    Load environment variables from a .env file
    
    Args:
        file_path: Path to the .env file
    """
    env_file = Path(file_path)
    
    if not env_file.exists():
        logger.debug(f"Environment file not found: {file_path}")
        return
    
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse key=value
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    # Set environment variable if not already set
                    if key not in os.environ:
                        os.environ[key] = value
                        logger.debug(f"Loaded environment variable: {key}")
                else:
                    logger.warning(f"Invalid line in {file_path}:{line_num}: {line}")
        
        logger.info(f"Loaded environment variables from: {file_path}")
        
    except Exception as e:
        logger.error(f"Failed to load environment file {file_path}: {e}")


def setup_environment():
    """Setup environment by loading .env files in order of priority"""
    env_files = [
        ".env.local",      # Local overrides (highest priority)
        f".env.{os.getenv('CLAUDE_FLOW_ENVIRONMENT', 'development')}",  # Environment-specific
        ".env"             # Default (lowest priority)
    ]
    
    # Load in reverse order so higher priority files override lower priority
    for env_file in reversed(env_files):
        load_env_file(env_file)


# Auto-setup environment on import
setup_environment()


# Create default configuration directories
def ensure_config_directories():
    """Ensure configuration directories exist"""
    directories = [
        "config",
        "data",
        "logs",
        "temp"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True, parents=True)


# Ensure directories on import
ensure_config_directories()