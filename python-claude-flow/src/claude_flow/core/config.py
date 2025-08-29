"""
Configuration management for Claude-Flow
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class DatabaseConfig(BaseModel):
    """Database configuration settings"""
    type: str = "sqlite"
    path: str = ".swarm/memory.db"
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    pool_size: int = 10
    max_overflow: int = 20


class MCPConfig(BaseModel):
    """MCP (Model Context Protocol) configuration"""
    enabled: bool = True
    server_url: str = "ws://localhost:3000"
    api_key: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    tools: List[str] = Field(default_factory=list)


class ClaudeConfig(BaseModel):
    """Claude AI configuration"""
    api_key: Optional[str] = None
    model: str = "claude-3-sonnet-20240229"
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 60
    base_url: str = "https://api.anthropic.com"


class SwarmConfig(BaseModel):
    """Swarm coordination configuration"""
    max_agents: int = 10
    heartbeat_interval: int = 30
    health_check_interval: int = 60
    auto_restart: bool = True
    resource_limits: Dict[str, Any] = Field(default_factory=dict)


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = None
    max_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


class Config(BaseModel):
    """Main configuration class"""
    
    # Core settings
    app_name: str = "claude-flow"
    version: str = "2.0.0-alpha.90"
    environment: str = "development"
    debug: bool = False
    
    # Paths
    base_dir: Path = Field(default_factory=lambda: Path.cwd())
    config_dir: Path = Field(default_factory=lambda: Path.cwd() / ".claude-flow")
    swarm_dir: Path = Field(default_factory=lambda: Path.cwd() / ".swarm")
    memory_dir: Path = Field(default_factory=lambda: Path.cwd() / ".swarm" / "memory")
    
    # Component configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    claude: ClaudeConfig = Field(default_factory=ClaudeConfig)
    swarm: SwarmConfig = Field(default_factory=SwarmConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    # Feature flags
    features: Dict[str, bool] = Field(default_factory=lambda: {
        "swarm_coordination": True,
        "memory_persistence": True,
        "mcp_integration": True,
        "claude_integration": True,
        "auto_scaling": True,
        "health_monitoring": True,
    })
    
    class Config:
        arbitrary_types_allowed = True
    
    def __init__(self, **data):
        super().__init__(**data)
        self._load_environment_vars()
        self._create_directories()
    
    def _load_environment_vars(self):
        """Load configuration from environment variables"""
        # Claude configuration
        if api_key := os.getenv("CLAUDE_API_KEY"):
            self.claude.api_key = api_key
        
        if model := os.getenv("CLAUDE_MODEL"):
            self.claude.model = model
        
        # MCP configuration
        if mcp_url := os.getenv("MCP_SERVER_URL"):
            self.mcp.server_url = mcp_url
        
        if mcp_key := os.getenv("MCP_API_KEY"):
            self.mcp.api_key = mcp_key
        
        # Database configuration
        if db_path := os.getenv("DATABASE_PATH"):
            self.database.path = db_path
        
        # Logging configuration
        if log_level := os.getenv("LOG_LEVEL"):
            self.logging.level = log_level.upper()
        
        # Environment
        if env := os.getenv("ENVIRONMENT"):
            self.environment = env
        
        # Debug mode
        if debug := os.getenv("DEBUG"):
            self.debug = debug.lower() in ("true", "1", "yes")
    
    def _create_directories(self):
        """Create necessary directories if they don't exist"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.swarm_dir.mkdir(parents=True, exist_ok=True)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
    
    def save(self, path: Optional[Path] = None) -> None:
        """Save configuration to file"""
        if path is None:
            path = self.config_dir / "config.json"
        
        with open(path, 'w') as f:
            json.dump(self.dict(), f, indent=2, default=str)
    
    @classmethod
    def load(cls, path: Optional[Path] = None) -> 'Config':
        """Load configuration from file"""
        if path is None:
            path = Path.cwd() / ".claude-flow" / "config.json"
        
        if path.exists():
            with open(path, 'r') as f:
                data = json.load(f)
                return cls(**data)
        
        return cls()
    
    def get_feature_flag(self, feature: str) -> bool:
        """Get feature flag value"""
        return self.features.get(feature, False)
    
    def set_feature_flag(self, feature: str, enabled: bool) -> None:
        """Set feature flag value"""
        self.features[feature] = enabled
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        # Check required API keys
        if self.claude.api_key is None:
            errors.append("CLAUDE_API_KEY is required")
        
        # Check database path
        if self.database.type == "sqlite":
            db_path = Path(self.database.path)
            if not db_path.parent.exists():
                errors.append(f"Database directory does not exist: {db_path.parent}")
        
        # Check MCP configuration
        if self.mcp.enabled and not self.mcp.server_url:
            errors.append("MCP server URL is required when MCP is enabled")
        
        return errors


# Global configuration instance
config = Config.load()
