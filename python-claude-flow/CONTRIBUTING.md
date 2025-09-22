# Contributing to Claude-Flow

Thank you for your interest in contributing to Claude-Flow! This document provides guidelines and information for contributors.

## 🤝 How to Contribute

We welcome contributions of all kinds:
- 🐛 Bug reports and fixes
- ✨ New features and enhancements
- 📚 Documentation improvements
- 🧪 Tests and test coverage
- 🎨 UI/UX improvements
- 🌍 Translations and internationalization
- 💡 Ideas and feature requests

## 🚀 Quick Start for Contributors

### 1. Development Environment Setup

```bash
# Fork and clone the repository
git clone https://github.com/your-username/python-claude-flow.git
cd python-claude-flow

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration
```

### 2. Running Tests

```bash
# Run all tests
make test

# Run specific test categories
make test-unit
make test-integration
make test-e2e

# Run with coverage
make test-coverage

# Run linting
make lint

# Run security checks
make security-check
```

### 3. Development Workflow

```bash
# Create a feature branch
git checkout -b feature/your-feature-name

# Make your changes
# ... code, test, commit ...

# Run tests before committing
make test

# Commit with conventional commit message
git commit -m "feat: add new agent type for data analysis"

# Push to your fork
git push origin feature/your-feature-name

# Create a Pull Request
```

## 📋 Contribution Guidelines

### Code Style and Standards

#### Python Code Style
- Follow [PEP 8](https://pep8.org/) style guide
- Use [Black](https://black.readthedocs.io/) for code formatting
- Use [isort](https://isort.readthedocs.io/) for import sorting
- Maximum line length: 88 characters (Black default)

#### Type Hints
- Use type hints for all function parameters and return values
- Import types from `typing` module when needed
- Use `Optional[T]` for nullable types

```python
from typing import Dict, List, Optional, Union
from pathlib import Path

async def process_data(
    data: List[Dict[str, Union[str, int]]], 
    output_path: Optional[Path] = None
) -> Dict[str, Any]:
    """Process data and return results."""
    # Implementation here
    pass
```

#### Docstrings
- Use Google-style docstrings for all public functions and classes
- Include type information, parameter descriptions, and examples

```python
def create_agent(agent_type: str, config: Dict[str, Any]) -> Agent:
    """Create a new agent with the specified type and configuration.
    
    Args:
        agent_type: The type of agent to create (e.g., 'coder', 'architect')
        config: Configuration dictionary for the agent
        
    Returns:
        A new Agent instance configured with the provided settings
        
    Raises:
        ValueError: If agent_type is not supported
        ConfigError: If config is invalid
        
    Example:
        >>> agent = create_agent('coder', {'language': 'python'})
        >>> agent.type
        'coder'
    """
```

### Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/) for consistent commit messages:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

#### Types:
- `feat`: New features
- `fix`: Bug fixes
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or modifying tests
- `chore`: Maintenance tasks

#### Examples:
```bash
feat(agents): add new data analyst agent type
fix(memory): resolve memory leak in SQLite connection pool
docs(api): update REST API documentation with new endpoints
test(core): add unit tests for event bus functionality
refactor(neural): optimize task classification performance
```

### Testing Requirements

#### Test Coverage
- Maintain minimum 90% test coverage
- All new features must include tests
- Bug fixes should include regression tests

#### Test Types
- **Unit Tests**: Test individual functions and classes
- **Integration Tests**: Test component interactions
- **End-to-End Tests**: Test complete workflows
- **Performance Tests**: Test system performance and scalability

#### Test Structure
```python
import pytest
from unittest.mock import Mock, patch

from claude_flow.core.agents import Agent
from claude_flow.core.tasks import Task


class TestAgent:
    """Test suite for Agent class."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        return {"type": "test", "max_tasks": 5}
    
    @pytest.fixture
    def agent(self, mock_config):
        """Create test agent instance."""
        return Agent(mock_config)
    
    def test_agent_creation(self, agent, mock_config):
        """Test agent creation with valid config."""
        assert agent.type == mock_config["type"]
        assert agent.max_tasks == mock_config["max_tasks"]
    
    @pytest.mark.asyncio
    async def test_agent_task_execution(self, agent):
        """Test agent task execution."""
        task = Task(title="Test task", type="test")
        result = await agent.execute_task(task)
        assert result.status == "completed"
    
    def test_invalid_config_raises_error(self):
        """Test that invalid config raises appropriate error."""
        with pytest.raises(ValueError, match="Invalid agent type"):
            Agent({"type": "invalid"})
```

### Documentation Standards

#### Code Documentation
- All public APIs must be documented
- Include usage examples for complex features
- Keep documentation up-to-date with code changes

#### User Documentation
- Write clear, concise user guides
- Include practical examples and tutorials
- Use proper markdown formatting
- Test all code examples

#### API Documentation
- Use OpenAPI/Swagger specifications
- Include request/response examples
- Document error codes and handling

### Security Considerations

#### Secure Coding Practices
- Validate all input data
- Use parameterized queries for database operations
- Sanitize user inputs to prevent injection attacks
- Follow OWASP security guidelines

#### API Security
- Implement proper authentication and authorization
- Use HTTPS for all communications
- Implement rate limiting and input validation
- Log security-relevant events

#### Dependency Security
- Regularly update dependencies
- Use security scanning tools
- Avoid dependencies with known vulnerabilities

## 🐛 Bug Reports

### Before Submitting a Bug Report
1. Check if the bug has already been reported
2. Ensure you're using the latest version
3. Try to reproduce the issue consistently
4. Gather relevant information (logs, configuration, etc.)

### Bug Report Template
```markdown
**Bug Description**
A clear description of the bug

**Steps to Reproduce**
1. Go to '...'
2. Click on '....'
3. See error

**Expected Behavior**
What you expected to happen

**Actual Behavior**
What actually happened

**Environment**
- Claude-Flow Version: [e.g., 1.0.0]
- Python Version: [e.g., 3.11.5]
- Operating System: [e.g., Ubuntu 22.04]
- Docker Version: [if applicable]

**Additional Context**
- Error logs
- Configuration files
- Screenshots (if applicable)
```

## ✨ Feature Requests

### Feature Request Template
```markdown
**Feature Summary**
Brief description of the feature

**Problem Statement**
What problem does this feature solve?

**Proposed Solution**
Detailed description of the proposed feature

**Alternatives Considered**
Other solutions you've considered

**Use Cases**
How would this feature be used?

**Implementation Notes**
Technical considerations or suggestions
```

## 🏗️ Development Areas

### High-Priority Areas
1. **Agent Development**: New agent types and capabilities
2. **Neural Network Integration**: Enhanced AI model integration
3. **Performance Optimization**: Scalability and efficiency improvements
4. **Security Enhancements**: Security features and compliance
5. **Documentation**: User guides, tutorials, and examples

### Getting Started Areas
- **Documentation Improvements**: Great for first-time contributors
- **Test Coverage**: Adding tests for existing functionality
- **Bug Fixes**: Small, well-defined issues
- **Example Projects**: Real-world usage examples

## 🔍 Code Review Process

### Pull Request Requirements
- [ ] Code follows style guidelines
- [ ] Tests pass and coverage is maintained
- [ ] Documentation is updated
- [ ] Commit messages follow convention
- [ ] No merge conflicts
- [ ] PR description is clear and complete

### Review Checklist
- **Functionality**: Does the code work as intended?
- **Code Quality**: Is the code clean and maintainable?
- **Performance**: Are there any performance implications?
- **Security**: Are there any security concerns?
- **Tests**: Are tests adequate and meaningful?
- **Documentation**: Is documentation complete and accurate?

### Review Process
1. **Automated Checks**: CI/CD pipeline runs tests and linting
2. **Peer Review**: At least one team member reviews the code
3. **Maintainer Review**: Core maintainer provides final approval
4. **Merge**: Changes are merged into main branch

## 🎯 Development Guidelines

### Architecture Principles
- **Modularity**: Keep components loosely coupled
- **Testability**: Design for easy testing
- **Observability**: Include logging and metrics
- **Error Handling**: Implement comprehensive error handling
- **Documentation**: Code should be self-documenting

### Performance Considerations
- **Async/Await**: Use async patterns for I/O operations
- **Resource Management**: Properly manage connections and resources
- **Caching**: Implement intelligent caching strategies
- **Database**: Optimize database queries and connections
- **Memory**: Monitor and optimize memory usage

### Adding New Features

#### 1. Agent Types
```python
# src/claude_flow/agents/custom_agent.py
from ..core.interfaces import BaseAgent

class CustomAgent(BaseAgent):
    """Custom agent for specific tasks."""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.agent_type = "custom"
    
    async def execute_task(self, task: Task) -> TaskResult:
        """Execute a task using custom logic."""
        # Implementation here
        pass
```

#### 2. MCP Tools
```python
# src/claude_flow/mcp/tools/custom_tool.py
from ..interfaces import MCPTool

class CustomTool(MCPTool):
    """Custom MCP tool implementation."""
    
    name = "custom_tool"
    description = "Performs custom operations"
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the custom tool."""
        # Implementation here
        pass
```

#### 3. Neural Network Models
```python
# src/claude_flow/neural/models/custom_model.py
from ..interfaces import NeuralModel

class CustomModel(NeuralModel):
    """Custom neural network model."""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
    
    async def predict(self, input_data: Any) -> Any:
        """Make predictions using the model."""
        # Implementation here
        pass
```

## 🧪 Testing Guidelines

### Test Organization
```
tests/
├── unit/                    # Unit tests
│   ├── test_agents.py
│   ├── test_memory.py
│   └── test_neural.py
├── integration/             # Integration tests
│   ├── test_agent_coordination.py
│   └── test_memory_persistence.py
├── e2e/                    # End-to-end tests
│   ├── test_complete_workflows.py
│   └── test_api_endpoints.py
├── performance/            # Performance tests
│   ├── test_load_testing.py
│   └── test_scalability.py
└── fixtures/               # Test data and fixtures
    ├── sample_data.json
    └── mock_responses.py
```

### Testing Best Practices
- Use descriptive test names
- Test both happy path and edge cases
- Mock external dependencies
- Use fixtures for test data
- Clean up after tests

## 📚 Documentation Guidelines

### Documentation Structure
```
docs/
├── guides/                 # User guides
├── api/                   # API documentation  
├── architecture/          # System architecture
├── examples/              # Usage examples
├── deployment/            # Deployment guides
└── development/           # Development guides
```

### Writing Guidelines
- Use clear, concise language
- Include practical examples
- Structure content logically
- Use proper markdown formatting
- Keep documentation current

## 🚀 Release Process

### Version Numbering
We follow [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Steps
1. **Update Version**: Bump version in relevant files
2. **Update Changelog**: Document changes since last release
3. **Create Release Branch**: `release/vX.Y.Z`
4. **Run Tests**: Ensure all tests pass
5. **Create Tag**: Git tag with version number
6. **Build Artifacts**: Docker images, Python packages
7. **Deploy**: Release to package repositories
8. **Announce**: Update documentation and notify community

## 💬 Communication

### Community Channels
- **GitHub Discussions**: Technical discussions and Q&A
- **GitHub Issues**: Bug reports and feature requests
- **Discord**: Real-time community chat
- **Twitter**: Updates and announcements

### Getting Help
- **Documentation**: Check existing documentation first
- **Search Issues**: Look for similar problems/questions
- **Ask Questions**: Use GitHub Discussions for questions
- **Community Chat**: Join Discord for real-time help

## 🏆 Recognition

### Contributor Recognition
- Contributors are acknowledged in release notes
- Major contributors are listed in CONTRIBUTORS.md
- Regular contributors may be invited to join the core team

### Types of Contributions
- **Code**: Direct contributions to the codebase
- **Documentation**: Improvements to documentation
- **Community**: Helping other users and contributors
- **Testing**: Improving test coverage and quality
- **Ideas**: Suggesting features and improvements

## 📄 License

By contributing to Claude-Flow, you agree that your contributions will be licensed under the same [MIT License](LICENSE) that covers the project.

## ❓ Questions?

If you have questions about contributing, please:
1. Check this document for answers
2. Search existing GitHub issues and discussions
3. Ask in GitHub Discussions
4. Contact the maintainers directly

Thank you for contributing to Claude-Flow! 🙏