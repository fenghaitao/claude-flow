"""
Pydantic configuration models for Claude-Flow

This module defines comprehensive configuration schemas using Pydantic for
validation, serialization, and documentation of all configuration options.
"""

import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator, root_validator
from pydantic.networks import AnyUrl, PostgresDsn


class LogLevel(str, Enum):
    """Logging levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Environment(str, Enum):
    """Application environments"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class DatabaseBackend(str, Enum):
    """Supported database backends"""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    REDIS = "redis"


class DeploymentMode(str, Enum):
    """Deployment modes"""
    STANDALONE = "standalone"
    DISTRIBUTED = "distributed"
    KUBERNETES = "kubernetes"
    DOCKER_SWARM = "docker_swarm"


# Base Configuration Models
class BaseConfig(BaseModel):
    """Base configuration with common fields"""
    
    class Config:
        """Pydantic configuration"""
        env_prefix = "CLAUDE_FLOW_"
        case_sensitive = False
        validate_assignment = True
        arbitrary_types_allowed = True
        use_enum_values = True


class DatabaseConfig(BaseConfig):
    """Database configuration"""
    backend: DatabaseBackend = DatabaseBackend.SQLITE
    url: Optional[str] = Field(None, description="Database connection URL")
    host: str = Field("localhost", description="Database host")
    port: int = Field(5432, ge=1, le=65535, description="Database port")
    database: str = Field("claude_flow", description="Database name")
    username: Optional[str] = Field(None, description="Database username")
    password: Optional[str] = Field(None, description="Database password")
    pool_size: int = Field(10, ge=1, le=100, description="Connection pool size")
    max_overflow: int = Field(20, ge=0, le=100, description="Max overflow connections")
    pool_timeout: int = Field(30, ge=1, description="Pool timeout in seconds")
    ssl_mode: Optional[str] = Field(None, description="SSL mode for connections")
    
    @validator("url", pre=True, always=True)
    def validate_url(cls, v, values):
        """Generate URL if not provided"""
        if v:
            return v
        
        backend = values.get("backend", DatabaseBackend.SQLITE)
        if backend == DatabaseBackend.SQLITE:
            return f"sqlite:///claude_flow.db"
        elif backend == DatabaseBackend.POSTGRESQL:
            host = values.get("host", "localhost")
            port = values.get("port", 5432)
            database = values.get("database", "claude_flow")
            username = values.get("username", "postgres")
            password = values.get("password", "")
            return f"postgresql://{username}:{password}@{host}:{port}/{database}"
        elif backend == DatabaseBackend.REDIS:
            host = values.get("host", "localhost")
            port = values.get("port", 6379)
            return f"redis://{host}:{port}/0"
        
        return v


class RedisConfig(BaseConfig):
    """Redis configuration"""
    host: str = Field("localhost", description="Redis host")
    port: int = Field(6379, ge=1, le=65535, description="Redis port")
    db: int = Field(0, ge=0, le=15, description="Redis database number")
    password: Optional[str] = Field(None, description="Redis password")
    ssl: bool = Field(False, description="Use SSL connection")
    pool_size: int = Field(10, ge=1, description="Connection pool size")
    socket_timeout: int = Field(5, ge=1, description="Socket timeout in seconds")
    socket_connect_timeout: int = Field(5, ge=1, description="Socket connect timeout")
    retry_on_timeout: bool = Field(True, description="Retry on timeout")
    health_check_interval: int = Field(30, ge=1, description="Health check interval")


class ClaudeConfig(BaseConfig):
    """Claude AI configuration"""
    api_key: str = Field(..., description="Claude API key")
    api_base: str = Field("https://api.anthropic.com", description="Claude API base URL")
    model: str = Field("claude-3-sonnet-20240229", description="Default Claude model")
    max_tokens: int = Field(4096, ge=1, le=100000, description="Maximum tokens per request")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    timeout: int = Field(60, ge=1, description="Request timeout in seconds")
    max_retries: int = Field(3, ge=0, description="Maximum retry attempts")
    retry_delay: float = Field(1.0, ge=0.1, description="Retry delay in seconds")
    rate_limit_requests: int = Field(50, ge=1, description="Rate limit requests per minute")
    rate_limit_tokens: int = Field(100000, ge=1, description="Rate limit tokens per minute")
    
    @validator("api_key")
    def validate_api_key(cls, v):
        """Validate API key format"""
        if not v or not v.startswith("sk-"):
            raise ValueError("Invalid Claude API key format")
        return v


class GitHubConfig(BaseConfig):
    """GitHub integration configuration"""
    token: Optional[str] = Field(None, description="GitHub personal access token")
    username: Optional[str] = Field(None, description="GitHub username")
    organization: Optional[str] = Field(None, description="GitHub organization")
    api_base: str = Field("https://api.github.com", description="GitHub API base URL")
    timeout: int = Field(30, ge=1, description="Request timeout in seconds")
    max_retries: int = Field(3, ge=0, description="Maximum retry attempts")
    rate_limit: int = Field(5000, ge=1, description="Rate limit per hour")


class MCPConfig(BaseConfig):
    """MCP (Model Context Protocol) configuration"""
    enabled: bool = Field(True, description="Enable MCP integration")
    servers: List[Dict[str, Any]] = Field(default_factory=list, description="MCP server configurations")
    discovery_timeout: int = Field(10, ge=1, description="Tool discovery timeout")
    execution_timeout: int = Field(300, ge=1, description="Tool execution timeout")
    max_concurrent_tools: int = Field(10, ge=1, description="Maximum concurrent tool executions")
    retry_attempts: int = Field(3, ge=0, description="Tool execution retry attempts")


class AgentConfig(BaseConfig):
    """Agent system configuration"""
    max_agents: int = Field(50, ge=1, le=1000, description="Maximum number of agents")
    default_timeout: int = Field(300, ge=1, description="Default agent timeout in seconds")
    heartbeat_interval: int = Field(30, ge=1, description="Agent heartbeat interval")
    resource_check_interval: int = Field(60, ge=1, description="Resource check interval")
    max_memory_mb: int = Field(512, ge=64, description="Maximum memory per agent in MB")
    max_cpu_percent: float = Field(80.0, ge=1.0, le=100.0, description="Maximum CPU usage per agent")
    spawn_timeout: int = Field(30, ge=1, description="Agent spawn timeout")
    termination_timeout: int = Field(10, ge=1, description="Agent termination timeout")


class SwarmConfig(BaseConfig):
    """Swarm coordination configuration"""
    enabled: bool = Field(True, description="Enable swarm coordination")
    max_swarm_size: int = Field(20, ge=1, le=100, description="Maximum swarm size")
    coordination_timeout: int = Field(120, ge=1, description="Coordination timeout")
    consensus_threshold: float = Field(0.6, ge=0.1, le=1.0, description="Consensus threshold")
    task_distribution_strategy: str = Field("load_balanced", description="Task distribution strategy")
    failure_tolerance: int = Field(2, ge=0, description="Number of agent failures to tolerate")


class MemoryConfig(BaseConfig):
    """Memory system configuration"""
    enabled: bool = Field(True, description="Enable memory system")
    default_ttl: int = Field(86400, ge=1, description="Default TTL for memory entries")
    max_entries: int = Field(100000, ge=1, description="Maximum memory entries")
    cleanup_interval: int = Field(3600, ge=1, description="Cleanup interval in seconds")
    compression_enabled: bool = Field(True, description="Enable memory compression")
    semantic_search_enabled: bool = Field(True, description="Enable semantic search")
    embedding_model: str = Field("all-MiniLM-L6-v2", description="Embedding model name")
    similarity_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Similarity threshold")


class NeuralConfig(BaseConfig):
    """Neural network configuration"""
    enabled: bool = Field(True, description="Enable neural networks")
    device: str = Field("auto", description="Device for neural computations (cpu/cuda/auto)")
    model_cache_dir: str = Field("./models", description="Model cache directory")
    training_enabled: bool = Field(True, description="Enable model training")
    auto_train: bool = Field(False, description="Enable automatic training")
    batch_size: int = Field(32, ge=1, description="Training batch size")
    learning_rate: float = Field(0.001, ge=0.0001, le=1.0, description="Learning rate")
    max_epochs: int = Field(100, ge=1, description="Maximum training epochs")


class MonitoringConfig(BaseConfig):
    """Monitoring and metrics configuration"""
    enabled: bool = Field(True, description="Enable monitoring")
    metrics_enabled: bool = Field(True, description="Enable metrics collection")
    prometheus_enabled: bool = Field(True, description="Enable Prometheus metrics")
    prometheus_port: int = Field(9090, ge=1024, le=65535, description="Prometheus metrics port")
    health_check_enabled: bool = Field(True, description="Enable health checks")
    health_check_port: int = Field(8080, ge=1024, le=65535, description="Health check port")
    metrics_retention_days: int = Field(30, ge=1, description="Metrics retention in days")
    alert_webhook_url: Optional[str] = Field(None, description="Alert webhook URL")


class LoggingConfig(BaseConfig):
    """Logging configuration"""
    level: LogLevel = Field(LogLevel.INFO, description="Logging level")
    format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )
    file_enabled: bool = Field(True, description="Enable file logging")
    file_path: str = Field("./logs/claude_flow.log", description="Log file path")
    file_max_bytes: int = Field(10485760, ge=1024, description="Max log file size in bytes")  # 10MB
    file_backup_count: int = Field(5, ge=1, description="Number of backup log files")
    console_enabled: bool = Field(True, description="Enable console logging")
    structured_logging: bool = Field(True, description="Enable structured JSON logging")
    
    @validator("file_path")
    def validate_file_path(cls, v):
        """Ensure log directory exists"""
        log_path = Path(v)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        return str(log_path)


class SecurityConfig(BaseConfig):
    """Security configuration"""
    encryption_enabled: bool = Field(True, description="Enable data encryption")
    secret_key: Optional[str] = Field(None, description="Secret key for encryption")
    api_key_rotation_days: int = Field(90, ge=1, description="API key rotation interval")
    session_timeout: int = Field(3600, ge=60, description="Session timeout in seconds")
    max_login_attempts: int = Field(5, ge=1, description="Maximum login attempts")
    password_min_length: int = Field(8, ge=6, description="Minimum password length")
    require_2fa: bool = Field(False, description="Require two-factor authentication")
    
    @validator("secret_key", pre=True, always=True)
    def generate_secret_key(cls, v):
        """Generate secret key if not provided"""
        if not v:
            import secrets
            return secrets.token_urlsafe(32)
        return v


class PerformanceConfig(BaseConfig):
    """Performance configuration"""
    max_workers: int = Field(4, ge=1, description="Maximum worker threads")
    queue_size: int = Field(1000, ge=1, description="Task queue size")
    batch_processing: bool = Field(True, description="Enable batch processing")
    cache_enabled: bool = Field(True, description="Enable caching")
    cache_ttl: int = Field(3600, ge=1, description="Cache TTL in seconds")
    profiling_enabled: bool = Field(False, description="Enable performance profiling")
    gc_threshold: int = Field(700, ge=1, description="Garbage collection threshold")


class DeploymentConfig(BaseConfig):
    """Deployment configuration"""
    mode: DeploymentMode = Field(DeploymentMode.STANDALONE, description="Deployment mode")
    docker_enabled: bool = Field(False, description="Enable Docker support")
    kubernetes_enabled: bool = Field(False, description="Enable Kubernetes support")
    scaling_enabled: bool = Field(False, description="Enable auto-scaling")
    min_replicas: int = Field(1, ge=1, description="Minimum replicas")
    max_replicas: int = Field(10, ge=1, description="Maximum replicas")
    health_check_path: str = Field("/health", description="Health check endpoint path")
    readiness_probe_delay: int = Field(30, ge=1, description="Readiness probe delay")
    liveness_probe_delay: int = Field(60, ge=1, description="Liveness probe delay")


# Main Configuration Model
class ClaudeFlowConfig(BaseConfig):
    """Main Claude-Flow configuration"""
    
    # Application settings
    app_name: str = Field("Claude-Flow", description="Application name")
    version: str = Field("2.0.0-alpha.90", description="Application version")
    environment: Environment = Field(Environment.DEVELOPMENT, description="Application environment")
    debug: bool = Field(False, description="Enable debug mode")
    
    # Core directories
    data_dir: str = Field("./data", description="Data directory")
    config_dir: str = Field("./config", description="Configuration directory")
    logs_dir: str = Field("./logs", description="Logs directory")
    temp_dir: str = Field("./temp", description="Temporary files directory")
    
    # Feature flags
    experimental_features: bool = Field(False, description="Enable experimental features")
    telemetry_enabled: bool = Field(True, description="Enable telemetry")
    auto_update: bool = Field(False, description="Enable automatic updates")
    
    # Component configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    claude: ClaudeConfig = Field(default_factory=lambda: ClaudeConfig(api_key="sk-placeholder"))
    github: GitHubConfig = Field(default_factory=GitHubConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    agents: AgentConfig = Field(default_factory=AgentConfig)
    swarm: SwarmConfig = Field(default_factory=SwarmConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    neural: NeuralConfig = Field(default_factory=NeuralConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    deployment: DeploymentConfig = Field(default_factory=DeploymentConfig)
    
    @root_validator
    def validate_directories(cls, values):
        """Ensure all directories exist"""
        directories = ["data_dir", "config_dir", "logs_dir", "temp_dir"]
        for dir_key in directories:
            if dir_key in values:
                Path(values[dir_key]).mkdir(parents=True, exist_ok=True)
        return values
    
    @validator("environment")
    def validate_environment_settings(cls, v, values):
        """Validate environment-specific settings"""
        if v == Environment.PRODUCTION:
            # Production-specific validations
            if values.get("debug", False):
                raise ValueError("Debug mode should be disabled in production")
            if not values.get("security", {}).get("encryption_enabled", True):
                raise ValueError("Encryption must be enabled in production")
        return v
    
    def get_database_url(self) -> str:
        """Get the database connection URL"""
        return self.database.url
    
    def get_redis_url(self) -> str:
        """Get the Redis connection URL"""
        auth = f":{self.redis.password}@" if self.redis.password else ""
        scheme = "rediss" if self.redis.ssl else "redis"
        return f"{scheme}://{auth}{self.redis.host}:{self.redis.port}/{self.redis.db}"
    
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment == Environment.DEVELOPMENT
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment == Environment.PRODUCTION
    
    def to_dict(self, exclude_sensitive: bool = True) -> Dict[str, Any]:
        """Convert to dictionary, optionally excluding sensitive data"""
        data = self.dict()
        
        if exclude_sensitive:
            # Remove sensitive fields
            sensitive_fields = [
                ["claude", "api_key"],
                ["github", "token"],
                ["database", "password"],
                ["redis", "password"],
                ["security", "secret_key"],
            ]
            
            for field_path in sensitive_fields:
                current = data
                for key in field_path[:-1]:
                    if key in current:
                        current = current[key]
                    else:
                        break
                else:
                    if field_path[-1] in current:
                        current[field_path[-1]] = "***REDACTED***"
        
        return data
    
    class Config:
        """Pydantic configuration"""
        env_prefix = "CLAUDE_FLOW_"
        case_sensitive = False
        validate_assignment = True
        arbitrary_types_allowed = True
        use_enum_values = True
        extra = "forbid"  # Prevent extra fields
        schema_extra = {
            "example": {
                "app_name": "Claude-Flow",
                "environment": "development",
                "debug": True,
                "claude": {
                    "api_key": "sk-your-api-key-here",
                    "model": "claude-3-sonnet-20240229"
                },
                "agents": {
                    "max_agents": 10,
                    "max_memory_mb": 512
                },
                "database": {
                    "backend": "sqlite",
                    "url": "sqlite:///claude_flow.db"
                }
            }
        }