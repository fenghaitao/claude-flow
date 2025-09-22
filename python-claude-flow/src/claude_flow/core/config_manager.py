"""
Configuration Manager for Claude-Flow

This module provides hierarchical configuration management with support for:
- Environment variables
- Configuration files (YAML, JSON, TOML)
- Default values
- Validation using Pydantic models
- Hot reloading
- Configuration merging and overrides
"""

import os
import json
import yaml
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Type
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # Fallback for older Python versions
    except ImportError:
        tomllib = None

from .config_models import ClaudeFlowConfig
from .interfaces import BaseComponent, ConfigurationError


logger = logging.getLogger(__name__)


class ConfigFileHandler(FileSystemEventHandler):
    """File system event handler for configuration file changes"""
    
    def __init__(self, config_manager: 'ConfigManager'):
        self.config_manager = config_manager
        
    def on_modified(self, event):
        """Handle file modification events"""
        if not event.is_directory and event.src_path in self.config_manager._watched_files:
            logger.info(f"Configuration file changed: {event.src_path}")
            asyncio.create_task(self.config_manager.reload_config())


class ConfigManager(BaseComponent):
    """
    Hierarchical configuration manager with validation and hot reloading
    
    Configuration priority (highest to lowest):
    1. Environment variables
    2. Command line arguments
    3. Configuration files (in order of loading)
    4. Default values
    """
    
    def __init__(self, config_class: Type[ClaudeFlowConfig] = ClaudeFlowConfig):
        super().__init__()
        self._config_class = config_class
        self._config: Optional[ClaudeFlowConfig] = None
        self._config_sources: List[Dict[str, Any]] = []
        self._config_files: List[Path] = []
        self._watched_files: Set[str] = set()
        self._observer: Optional[Observer] = None
        self._hot_reload_enabled = False
        self._override_data: Dict[str, Any] = {}
        self._last_reload: Optional[datetime] = None
        
    @property
    def config(self) -> ClaudeFlowConfig:
        """Get the current configuration"""
        if self._config is None:
            raise ConfigurationError("Configuration not loaded. Call load_config() first.")
        return self._config
    
    async def _start_implementation(self) -> None:
        """Start the configuration manager"""
        await self.load_config()
        
    async def _stop_implementation(self) -> None:
        """Stop the configuration manager"""
        await self.stop_hot_reload()
        
    async def _health_check_implementation(self) -> Dict[str, Any]:
        """Perform health check"""
        return {
            "config_loaded": self._config is not None,
            "config_files_count": len(self._config_files),
            "hot_reload_enabled": self._hot_reload_enabled,
            "last_reload": self._last_reload.isoformat() if self._last_reload else None,
            "config_sources": len(self._config_sources)
        }
    
    def add_config_file(self, file_path: Union[str, Path], required: bool = True) -> 'ConfigManager':
        """
        Add a configuration file to be loaded
        
        Args:
            file_path: Path to configuration file
            required: Whether the file is required to exist
            
        Returns:
            Self for method chaining
        """
        path = Path(file_path)
        
        if required and not path.exists():
            raise ConfigurationError(f"Required configuration file not found: {path}")
        
        if path.exists():
            self._config_files.append(path)
            logger.info(f"Added configuration file: {path}")
        
        return self
    
    def add_config_directory(self, dir_path: Union[str, Path], 
                           pattern: str = "*.yaml", recursive: bool = False) -> 'ConfigManager':
        """
        Add all configuration files from a directory
        
        Args:
            dir_path: Directory path
            pattern: File pattern to match
            recursive: Search subdirectories
            
        Returns:
            Self for method chaining
        """
        path = Path(dir_path)
        
        if not path.exists() or not path.is_dir():
            logger.warning(f"Configuration directory not found: {path}")
            return self
        
        if recursive:
            files = path.rglob(pattern)
        else:
            files = path.glob(pattern)
        
        for file_path in sorted(files):
            if file_path.is_file():
                self._config_files.append(file_path)
                logger.info(f"Added configuration file from directory: {file_path}")
        
        return self
    
    def set_override(self, key: str, value: Any) -> 'ConfigManager':
        """
        Set a configuration override
        
        Args:
            key: Configuration key (supports nested keys with dots)
            value: Value to set
            
        Returns:
            Self for method chaining
        """
        keys = key.split('.')
        current = self._override_data
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
        logger.info(f"Set configuration override: {key} = {value}")
        
        return self
    
    def _load_file(self, file_path: Path) -> Dict[str, Any]:
        """Load configuration from a file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            suffix = file_path.suffix.lower()
            
            if suffix in ['.yaml', '.yml']:
                data = yaml.safe_load(content)
            elif suffix == '.json':
                data = json.loads(content)
            elif suffix == '.toml' and tomllib:
                data = tomllib.loads(content)
            else:
                raise ConfigurationError(f"Unsupported configuration file format: {suffix}")
            
            logger.info(f"Loaded configuration from: {file_path}")
            return data or {}
            
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration file {file_path}: {e}")
    
    def _load_environment_variables(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        config_data = {}
        prefix = "CLAUDE_FLOW_"
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Remove prefix and convert to lowercase
                config_key = key[len(prefix):].lower()
                
                # Convert nested keys (CLAUDE_FLOW_DATABASE__HOST -> database.host)
                config_key = config_key.replace('__', '.')
                
                # Try to parse as JSON for complex values
                try:
                    parsed_value = json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    # Keep as string if not valid JSON
                    parsed_value = value
                
                # Set nested value
                keys = config_key.split('.')
                current = config_data
                
                for k in keys[:-1]:
                    if k not in current:
                        current[k] = {}
                    current = current[k]
                
                current[keys[-1]] = parsed_value
        
        if config_data:
            logger.info(f"Loaded {len(config_data)} configuration values from environment variables")
        
        return config_data
    
    def _merge_configs(self, *configs: Dict[str, Any]) -> Dict[str, Any]:
        """Merge multiple configuration dictionaries"""
        result = {}
        
        for config in configs:
            if not config:
                continue
            
            for key, value in config.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    # Recursively merge nested dictionaries
                    result[key] = self._merge_configs(result[key], value)
                else:
                    # Override with new value
                    result[key] = value
        
        return result
    
    async def load_config(self, validate: bool = True) -> ClaudeFlowConfig:
        """
        Load configuration from all sources
        
        Args:
            validate: Whether to validate the configuration
            
        Returns:
            Loaded and validated configuration
        """
        try:
            # Start with empty configuration
            merged_config = {}
            self._config_sources.clear()
            
            # 1. Load configuration files (in order)
            for file_path in self._config_files:
                if file_path.exists():
                    file_config = self._load_file(file_path)
                    merged_config = self._merge_configs(merged_config, file_config)
                    self._config_sources.append({
                        "type": "file",
                        "source": str(file_path),
                        "data": file_config
                    })
            
            # 2. Load environment variables
            env_config = self._load_environment_variables()
            if env_config:
                merged_config = self._merge_configs(merged_config, env_config)
                self._config_sources.append({
                    "type": "environment",
                    "source": "environment_variables",
                    "data": env_config
                })
            
            # 3. Apply overrides
            if self._override_data:
                merged_config = self._merge_configs(merged_config, self._override_data)
                self._config_sources.append({
                    "type": "override",
                    "source": "programmatic_overrides",
                    "data": self._override_data
                })
            
            # 4. Create and validate configuration
            if validate:
                self._config = self._config_class(**merged_config)
            else:
                # Create without validation for debugging
                self._config = self._config_class.construct(**merged_config)
            
            self._last_reload = datetime.now()
            
            logger.info(f"Configuration loaded successfully from {len(self._config_sources)} sources")
            
            return self._config
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise ConfigurationError(f"Configuration loading failed: {e}")
    
    async def reload_config(self) -> ClaudeFlowConfig:
        """Reload configuration from all sources"""
        logger.info("Reloading configuration...")
        return await self.load_config()
    
    def validate_config(self) -> bool:
        """Validate the current configuration"""
        if self._config is None:
            return False
        
        try:
            # Re-validate by creating a new instance
            data = self._config.dict()
            self._config_class(**data)
            return True
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
    
    async def start_hot_reload(self, debounce_seconds: float = 1.0) -> None:
        """
        Start hot reloading of configuration files
        
        Args:
            debounce_seconds: Delay before reloading after file change
        """
        if self._hot_reload_enabled:
            logger.warning("Hot reload is already enabled")
            return
        
        if not self._config_files:
            logger.warning("No configuration files to watch for hot reload")
            return
        
        # Set up file system observer
        self._observer = Observer()
        handler = ConfigFileHandler(self)
        
        # Watch directories containing config files
        watched_dirs = set()
        
        for file_path in self._config_files:
            dir_path = file_path.parent
            if dir_path not in watched_dirs:
                self._observer.schedule(handler, str(dir_path), recursive=False)
                watched_dirs.add(dir_path)
            
            self._watched_files.add(str(file_path))
        
        self._observer.start()
        self._hot_reload_enabled = True
        
        logger.info(f"Hot reload enabled for {len(self._config_files)} configuration files")
    
    async def stop_hot_reload(self) -> None:
        """Stop hot reloading"""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
        
        self._hot_reload_enabled = False
        self._watched_files.clear()
        
        logger.info("Hot reload disabled")
    
    def get_config_sources(self) -> List[Dict[str, Any]]:
        """Get information about configuration sources"""
        return self._config_sources.copy()
    
    def export_config(self, file_path: Union[str, Path], 
                     format: str = "yaml", exclude_sensitive: bool = True) -> None:
        """
        Export current configuration to a file
        
        Args:
            file_path: Output file path
            format: Output format (yaml, json, toml)
            exclude_sensitive: Whether to exclude sensitive data
        """
        if self._config is None:
            raise ConfigurationError("No configuration loaded to export")
        
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = self._config.to_dict(exclude_sensitive=exclude_sensitive)
        
        try:
            with open(path, 'w', encoding='utf-8') as f:
                if format.lower() in ['yaml', 'yml']:
                    yaml.dump(data, f, default_flow_style=False, indent=2)
                elif format.lower() == 'json':
                    json.dump(data, f, indent=2, default=str)
                elif format.lower() == 'toml' and tomllib:
                    import tomli_w
                    tomli_w.dump(data, f)
                else:
                    raise ValueError(f"Unsupported export format: {format}")
            
            logger.info(f"Configuration exported to: {path}")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to export configuration: {e}")
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get a specific configuration value using dot notation
        
        Args:
            key: Configuration key (e.g., 'database.host')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        if self._config is None:
            return default
        
        keys = key.split('.')
        current = self._config.dict()
        
        try:
            for k in keys:
                current = current[k]
            return current
        except (KeyError, TypeError):
            return default
    
    def set_config_value(self, key: str, value: Any, reload: bool = False) -> None:
        """
        Set a configuration value (runtime override)
        
        Args:
            key: Configuration key using dot notation
            value: Value to set
            reload: Whether to reload configuration after setting
        """
        self.set_override(key, value)
        
        if reload:
            asyncio.create_task(self.reload_config())


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config() -> ClaudeFlowConfig:
    """Get the current configuration"""
    return get_config_manager().config


async def initialize_config(config_files: Optional[List[str]] = None,
                          hot_reload: bool = False) -> ClaudeFlowConfig:
    """
    Initialize the global configuration
    
    Args:
        config_files: List of configuration file paths
        hot_reload: Enable hot reloading
        
    Returns:
        Loaded configuration
    """
    manager = get_config_manager()
    
    # Add default configuration files if none specified
    if config_files is None:
        config_files = [
            "config/default.yaml",
            "config/local.yaml",
            ".claude-flow.yaml"
        ]
    
    # Add configuration files
    for file_path in config_files:
        manager.add_config_file(file_path, required=False)
    
    # Load configuration
    config = await manager.load_config()
    
    # Start hot reload if requested
    if hot_reload:
        await manager.start_hot_reload()
    
    return config