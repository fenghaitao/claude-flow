# 🌊 Claude-Flow Python Port

This is a Python port of the original TypeScript/Node.js Claude-Flow implementation. It maintains the same functionality while providing a Python-native experience.

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+** (3.11+ recommended)
- **pip** or **conda** package manager
- **Claude API Key** from Anthropic

### Installation

#### Option 1: Install from source
```bash
# Clone the repository
git clone https://github.com/ruvnet/claude-code-flow.git
cd claude-code-flow

# Install in development mode
pip install -e .

# Or install with all dependencies
pip install -e ".[dev,ui]"
```

#### Option 2: Install dependencies only
```bash
# Install required packages
pip install -r requirements.txt
```

### Configuration

1. **Set your Claude API key:**
```bash
export CLAUDE_API_KEY="your_api_key_here"
```

2. **Or create a `.env` file:**
```bash
# Copy the template
cp .env.example .env

# Edit with your API key
CLAUDE_API_KEY=your_api_key_here
```

3. **Initialize Claude-Flow:**
```bash
python -m claude_flow.cli.main init
```

## 🎯 Usage

### Basic Commands

```bash
# Show help
python -m claude_flow.cli.main --help

# Check status
python -m claude_flow.cli.main status

# Health check
python -m claude_flow.cli.main health
```

### Swarm Coordination

```bash
# Coordinate a swarm for a task
python -m claude_flow.cli.main swarm coordinate "build a REST API" --claude

# Show swarm status
python -m claude_flow.cli.main swarm status

# Show agent information
python -m claude_flow.cli.main swarm status --agents
```

### Hive-Mind Management

```bash
# Spawn a new hive-mind
python -m claude_flow.cli.main hive-mind spawn "Enterprise project management" --claude

# Interactive wizard
python -m claude_flow.cli.main hive-mind wizard
```

### Memory Management

```bash
# Query memory
python -m claude_flow.cli.main memory query "API endpoints"

# Show recent memories
python -m claude_flow.cli.main memory query --recent
```

### MCP Integration

```bash
# Show MCP status
python -m claude_flow.cli.main mcp status

# List available tools
python -m claude_flow.cli.main mcp status --list
```

## 🏗️ Architecture

### Core Components

- **Configuration Management**: Environment-based configuration with validation
- **Event Bus**: Asynchronous event system for component communication
- **Logging**: Structured logging with rich console output
- **MCP Client**: Model Context Protocol integration
- **CLI Interface**: Click-based command-line interface

### Key Features

- **Swarm Coordination**: Multi-agent task execution
- **Hive-Mind**: Persistent project coordination
- **Memory System**: Persistent storage and retrieval
- **MCP Integration**: Tool discovery and execution
- **Claude AI**: Direct integration with Anthropic's Claude

## 🔧 Development

### Project Structure

```
src/claude_flow/
├── __init__.py          # Package initialization
├── cli/                 # Command-line interface
│   ├── main.py         # Main CLI entry point
│   └── commands.py     # Command definitions
├── core/               # Core functionality
│   ├── config.py       # Configuration management
│   ├── logger.py       # Logging system
│   └── event_bus.py    # Event system
├── mcp/                # MCP integration
│   └── mcp_client.py   # MCP client
├── agents/             # Agent management (TODO)
├── swarm/              # Swarm coordination (TODO)
├── memory/             # Memory system (TODO)
└── neural/             # Neural networks (TODO)
```

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=claude_flow

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
```

### Code Quality

```bash
# Format code
black src/

# Lint code
flake8 src/

# Type checking
mypy src/
```

## 🔌 Integration

### Using as a Library

```python
from claude_flow.core.config import config
from claude_flow.core.logger import logger
from claude_flow.core.event_bus import event_bus
from claude_flow.mcp.mcp_client import mcp_client

# Start event bus
await event_bus.start()

# Connect to MCP server
await mcp_client.connect()

# Use components
logger.info("Claude-Flow initialized")
```

### Event System

```python
from claude_flow.core.event_bus import EventType, publish_agent_event

# Publish events
await publish_agent_event(
    agent_id="agent_001",
    event_type=EventType.AGENT_STARTED,
    data={"status": "running"}
)
```

## 🚧 Status

### ✅ Implemented

- Core configuration system
- Logging with rich output
- Event bus system
- CLI framework with Click
- MCP client (basic)
- Basic command structure

### 🚧 In Progress

- Agent management system
- Swarm coordination
- Memory persistence
- Neural network integration

### 📋 TODO

- Complete agent lifecycle management
- Implement swarm algorithms
- Add memory database integration
- Neural network acceleration
- Docker integration
- GitHub integration
- Performance monitoring

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run quality checks
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- **Original Repository**: [ruvnet/claude-code-flow](https://github.com/ruvnet/claude-code-flow)
- **Documentation**: [GitHub README](https://github.com/ruvnet/claude-code-flow#readme)
- **Issues**: [GitHub Issues](https://github.com/ruvnet/claude-code-flow/issues)

## 🆘 Support

- **Discord**: [Agentics Foundation](https://discord.com/invite/dfxmpwkG2D)
- **GitHub**: [Issues](https://github.com/ruvnet/claude-code-flow/issues)
- **Email**: info@ruv.net

---

**Note**: This is an alpha release. Features may change and bugs may exist. Please report issues and contribute improvements!
