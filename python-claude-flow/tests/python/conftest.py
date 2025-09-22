"""
Pytest configuration and fixtures for Claude-Flow testing.
"""

import asyncio
import os
import sys
import tempfile
import shutil
from pathlib import Path
from typing import AsyncGenerator, Generator, Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock
import pytest
import pytest_asyncio
from pydantic import BaseModel

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from claude_flow.config.models import ClaudeFlowConfig, ClaudeConfig
from claude_flow.core.interfaces import BaseComponent
from claude_flow.events.bus import EventBus


class TestConfig(BaseModel):
    """Test-specific configuration."""
    test_env: str = "test"
    claude_api_key: str = "test-key-fake"
    temp_dir: Optional[Path] = None
    use_real_claude: bool = False
    use_real_redis: bool = False
    use_real_postgres: bool = False


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_config() -> TestConfig:
    """Test configuration with environment overrides."""
    return TestConfig(
        claude_api_key=os.getenv("CLAUDE_API_KEY", "test-key-fake"),
        use_real_claude=os.getenv("USE_REAL_CLAUDE", "false").lower() == "true",
        use_real_redis=os.getenv("USE_REAL_REDIS", "false").lower() == "true",
        use_real_postgres=os.getenv("USE_REAL_POSTGRES", "false").lower() == "true"
    )


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    temp_path = Path(tempfile.mkdtemp())
    try:
        yield temp_path
    finally:
        shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
async def claude_config(test_config: TestConfig, temp_dir: Path) -> ClaudeConfig:
    """Claude configuration for testing."""
    return ClaudeConfig(
        api_key=test_config.claude_api_key,
        model="claude-3-5-haiku-20241022",
        max_tokens=1000,
        timeout=30.0,
        rate_limits={
            "claude-3-5-haiku-20241022": {
                "requests_per_minute": 100,
                "tokens_per_minute": 10000
            }
        }
    )


@pytest.fixture
async def claude_flow_config(claude_config: ClaudeConfig, temp_dir: Path) -> ClaudeFlowConfig:
    """Main configuration for testing."""
    return ClaudeFlowConfig(
        claude=claude_config,
        database={
            "sqlite": {
                "path": str(temp_dir / "test.db"),
                "enable_wal": False,
                "timeout": 10.0
            }
        }
    )


@pytest.fixture
async def event_bus(claude_flow_config: ClaudeFlowConfig) -> AsyncGenerator[EventBus, None]:
    """Event bus instance for testing."""
    bus = EventBus(claude_flow_config.events)
    await bus.initialize()
    try:
        yield bus
    finally:
        await bus.shutdown()


@pytest.fixture
def mock_claude_client():
    """Mock Claude client for testing."""
    mock = AsyncMock()
    mock.chat.return_value.content = "Test response"
    mock.chat.return_value.usage = {"total_tokens": 100}
    mock.health_check.return_value = {"status": "healthy"}
    return mock


# Markers for test organization
pytestmark = [
    pytest.mark.asyncio
]