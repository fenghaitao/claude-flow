"""
Unit tests for configuration models and management.
"""

import os
import tempfile
from pathlib import Path
import pytest
from pydantic import ValidationError

from claude_flow.config.models import (
    ClaudeConfig, DatabaseConfig, MemoryConfig, AgentConfig, 
    EventConfig, ClaudeFlowConfig
)
from claude_flow.config.manager import ConfigurationManager


class TestClaudeConfig:
    """Test ClaudeConfig model."""
    
    def test_claude_config_valid(self):
        """Test valid Claude configuration."""
        config = ClaudeConfig(
            api_key="test-key",
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            timeout=60.0
        )
        
        assert config.api_key == "test-key"
        assert config.model == "claude-3-5-sonnet-20241022"
        assert config.max_tokens == 4096
        assert config.timeout == 60.0
    
    def test_claude_config_defaults(self):
        """Test default values in Claude configuration."""
        config = ClaudeConfig(api_key="test-key")
        
        assert config.model == "claude-3-5-sonnet-20241022"
        assert config.max_tokens == 4096
        assert config.timeout == 60.0
        assert config.temperature == 0.7
    
    def test_claude_config_invalid_api_key(self):
        """Test validation error for missing API key."""
        with pytest.raises(ValidationError) as exc_info:
            ClaudeConfig()
        
        assert "api_key" in str(exc_info.value)
    
    def test_claude_config_invalid_max_tokens(self):
        """Test validation error for invalid max_tokens."""
        with pytest.raises(ValidationError):
            ClaudeConfig(api_key="test", max_tokens=0)
        
        with pytest.raises(ValidationError):
            ClaudeConfig(api_key="test", max_tokens=200001)
    
    def test_claude_config_invalid_temperature(self):
        """Test validation error for invalid temperature."""
        with pytest.raises(ValidationError):
            ClaudeConfig(api_key="test", temperature=-0.1)
        
        with pytest.raises(ValidationError):
            ClaudeConfig(api_key="test", temperature=2.1)


class TestDatabaseConfig:
    """Test DatabaseConfig model."""
    
    def test_database_config_valid(self):
        """Test valid database configuration."""
        config = DatabaseConfig(
            sqlite={"path": "test.db"},
            redis={"host": "localhost", "port": 6379},
            postgres={"host": "localhost", "database": "test"}
        )
        
        assert config.sqlite["path"] == "test.db"
        assert config.redis["host"] == "localhost"
        assert config.postgres["database"] == "test"
    
    def test_database_config_defaults(self):
        """Test default database configuration."""
        config = DatabaseConfig()
        
        assert "path" in config.sqlite
        assert config.sqlite["enable_wal"] is True
        assert config.redis["host"] == "localhost"
        assert config.postgres is None


class TestMemoryConfig:
    """Test MemoryConfig model."""
    
    def test_memory_config_valid(self):
        """Test valid memory configuration."""
        config = MemoryConfig(
            max_entries=5000,
            ttl_seconds=7200,
            enable_compression=True
        )
        
        assert config.max_entries == 5000
        assert config.ttl_seconds == 7200
        assert config.enable_compression is True
    
    def test_memory_config_defaults(self):
        """Test default memory configuration."""
        config = MemoryConfig()
        
        assert config.max_entries == 10000
        assert config.ttl_seconds == 3600
        assert config.enable_compression is False


class TestAgentConfig:
    """Test AgentConfig model."""
    
    def test_agent_config_valid(self):
        """Test valid agent configuration."""
        config = AgentConfig(
            max_workers=8,
            heartbeat_interval=5.0,
            task_timeout=120.0
        )
        
        assert config.max_workers == 8
        assert config.heartbeat_interval == 5.0
        assert config.task_timeout == 120.0
    
    def test_agent_config_defaults(self):
        """Test default agent configuration."""
        config = AgentConfig()
        
        assert config.max_workers == 4
        assert config.heartbeat_interval == 10.0
        assert config.task_timeout == 300.0


class TestEventConfig:
    """Test EventConfig model."""
    
    def test_event_config_valid(self):
        """Test valid event configuration."""
        config = EventConfig(
            max_queue_size=500,
            persistence_enabled=False,
            replay_enabled=False
        )
        
        assert config.max_queue_size == 500
        assert config.persistence_enabled is False
        assert config.replay_enabled is False
    
    def test_event_config_defaults(self):
        """Test default event configuration."""
        config = EventConfig()
        
        assert config.max_queue_size == 1000
        assert config.persistence_enabled is True
        assert config.replay_enabled is True


class TestClaudeFlowConfig:
    """Test main ClaudeFlowConfig model."""
    
    def test_claude_flow_config_valid(self):
        """Test valid complete configuration."""
        claude_config = ClaudeConfig(api_key="test-key")
        config = ClaudeFlowConfig(claude=claude_config)
        
        assert config.claude.api_key == "test-key"
        assert isinstance(config.database, DatabaseConfig)
        assert isinstance(config.memory, MemoryConfig)
        assert isinstance(config.agents, AgentConfig)
        assert isinstance(config.events, EventConfig)
    
    def test_claude_flow_config_minimal(self):
        """Test minimal configuration with just Claude API key."""
        config = ClaudeFlowConfig(
            claude=ClaudeConfig(api_key="test-key")
        )
        
        # Should have all default sub-configs
        assert config.claude.api_key == "test-key"
        assert config.database.sqlite["enable_wal"] is True
        assert config.memory.max_entries == 10000
        assert config.agents.max_workers == 4
        assert config.events.max_queue_size == 1000


class TestConfigurationManager:
    """Test ConfigurationManager functionality."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary directory for config files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def test_load_from_file(self, temp_config_dir):
        """Test loading configuration from file."""
        config_file = temp_config_dir / "config.yaml"
        config_content = """
        claude:
          api_key: "test-api-key"
          model: "claude-3-opus-20240229"
          max_tokens: 2048
        
        database:
          sqlite:
            path: "custom.db"
        
        memory:
          max_entries: 5000
        """
        config_file.write_text(config_content)
        
        manager = ConfigurationManager()
        config = manager.load_from_file(config_file)
        
        assert config.claude.api_key == "test-api-key"
        assert config.claude.model == "claude-3-opus-20240229"
        assert config.claude.max_tokens == 2048
        assert config.database.sqlite["path"] == "custom.db"
        assert config.memory.max_entries == 5000
    
    def test_load_from_env(self):
        """Test loading configuration from environment variables."""
        os.environ["CLAUDE_API_KEY"] = "env-api-key"
        os.environ["CLAUDE_MODEL"] = "claude-3-haiku-20240307"
        os.environ["MAX_WORKERS"] = "8"
        
        try:
            manager = ConfigurationManager()
            config = manager.load_from_env()
            
            assert config.claude.api_key == "env-api-key"
            assert config.claude.model == "claude-3-haiku-20240307"
            assert config.agents.max_workers == 8
        finally:
            # Clean up environment variables
            os.environ.pop("CLAUDE_API_KEY", None)
            os.environ.pop("CLAUDE_MODEL", None)
            os.environ.pop("MAX_WORKERS", None)
    
    def test_merge_configs(self):
        """Test merging multiple configurations."""
        base_config = ClaudeFlowConfig(
            claude=ClaudeConfig(api_key="base-key", max_tokens=1000)
        )
        
        override_config = ClaudeFlowConfig(
            claude=ClaudeConfig(api_key="override-key", model="claude-3-opus-20240229"),
            memory=MemoryConfig(max_entries=5000)
        )
        
        manager = ConfigurationManager()
        merged = manager.merge_configs(base_config, override_config)
        
        # Override should take precedence for claude settings
        assert merged.claude.api_key == "override-key"
        assert merged.claude.model == "claude-3-opus-20240229"
        assert merged.claude.max_tokens == 1000  # From base
        
        # Memory config should be from override
        assert merged.memory.max_entries == 5000
    
    def test_validate_config(self):
        """Test configuration validation."""
        manager = ConfigurationManager()
        
        # Valid config should pass
        valid_config = ClaudeFlowConfig(
            claude=ClaudeConfig(api_key="test-key")
        )
        assert manager.validate_config(valid_config) is True
        
        # Invalid config should fail
        invalid_config = ClaudeFlowConfig(
            claude=ClaudeConfig(api_key="test-key", max_tokens=0)
        )
        assert manager.validate_config(invalid_config) is False
    
    def test_get_config_schema(self):
        """Test getting configuration schema."""
        manager = ConfigurationManager()
        schema = manager.get_config_schema()
        
        assert "properties" in schema
        assert "claude" in schema["properties"]
        assert "database" in schema["properties"]
        assert "memory" in schema["properties"]
        assert "agents" in schema["properties"]
        assert "events" in schema["properties"]


@pytest.mark.integration
class TestConfigurationIntegration:
    """Integration tests for configuration system."""
    
    def test_full_config_lifecycle(self, temp_config_dir):
        """Test complete configuration lifecycle."""
        # Create config file
        config_file = temp_config_dir / "full_config.yaml"
        config_content = """
        claude:
          api_key: "integration-test-key"
          model: "claude-3-5-sonnet-20241022"
          max_tokens: 8192
          temperature: 0.5
          rate_limits:
            claude-3-5-sonnet-20241022:
              requests_per_minute: 500
              tokens_per_minute: 20000
        
        database:
          sqlite:
            path: "integration.db"
            enable_wal: false
          redis:
            host: "localhost"
            port: 6379
            db: 1
        
        memory:
          max_entries: 15000
          ttl_seconds: 7200
          enable_compression: true
        
        agents:
          max_workers: 6
          heartbeat_interval: 15.0
          task_timeout: 600.0
        
        events:
          max_queue_size: 2000
          persistence_enabled: true
          replay_enabled: true
        """
        config_file.write_text(config_content)
        
        # Load and validate
        manager = ConfigurationManager()
        config = manager.load_from_file(config_file)
        
        assert manager.validate_config(config) is True
        
        # Verify all settings
        assert config.claude.api_key == "integration-test-key"
        assert config.claude.model == "claude-3-5-sonnet-20241022"
        assert config.claude.max_tokens == 8192
        assert config.claude.temperature == 0.5
        
        assert config.database.sqlite["path"] == "integration.db"
        assert config.database.sqlite["enable_wal"] is False
        assert config.database.redis["db"] == 1
        
        assert config.memory.max_entries == 15000
        assert config.memory.ttl_seconds == 7200
        assert config.memory.enable_compression is True
        
        assert config.agents.max_workers == 6
        assert config.agents.heartbeat_interval == 15.0
        assert config.agents.task_timeout == 600.0
        
        assert config.events.max_queue_size == 2000
        assert config.events.persistence_enabled is True
        assert config.events.replay_enabled is True