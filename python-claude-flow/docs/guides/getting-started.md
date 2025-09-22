# Getting Started with Claude-Flow

Welcome to Claude-Flow! This guide will help you get up and running with the enterprise AI agent orchestration platform in just a few minutes.

## What is Claude-Flow?

Claude-Flow is an enterprise-grade platform that orchestrates AI agents to work together on complex tasks. Think of it as a "hive mind" where different AI agents collaborate, each with their own specializations, to solve problems that would be difficult for a single AI to handle alone.

### Key Concepts

- **🧠 Agents**: Specialized AI workers (Coder, Architect, Tester, etc.)
- **👑 Queen Agent**: Central coordinator that assigns tasks and manages resources
- **📋 Sessions**: Containers that group related tasks and agents
- **🎯 Tasks**: Individual work items assigned to agents
- **🔄 Events**: Real-time communication between components
- **🧮 Memory**: Persistent storage for knowledge and context

## Quick Start

### Prerequisites

Before you begin, ensure you have:
- Python 3.11 or higher
- Docker and Docker Compose
- An Anthropic API key (get one at [console.anthropic.com](https://console.anthropic.com))

### Installation Options

#### Option 1: Docker Compose (Recommended for Beginners)

1. **Download and Setup**
   ```bash
   git clone https://github.com/claude-flow/python-claude-flow.git
   cd python-claude-flow
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   nano .env
   ```

3. **Start the Platform**
   ```bash
   docker-compose up -d
   ```

4. **Verify Installation**
   ```bash
   # Check if services are running
   docker-compose ps
   
   # View logs
   docker-compose logs claude-flow
   ```

#### Option 2: Python Installation

1. **Install Package**
   ```bash
   pip install claude-flow
   ```

2. **Setup Configuration**
   ```bash
   claude-flow init
   # Follow the interactive setup wizard
   ```

3. **Start Services**
   ```bash
   claude-flow start
   ```

### First Steps

#### 1. Access the Platform

Once running, you can access:
- **Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Monitoring Dashboard**: http://localhost:3000 (admin/admin123)

#### 2. Create Your First Session

A session is like a workspace where agents collaborate on related tasks.

**Using the CLI:**
```bash
claude-flow session create "My First Project" \
  --description "Learning how to use Claude-Flow"
```

**Using Python:**
```python
from claude_flow import ClaudeFlow

# Initialize the platform
platform = ClaudeFlow()
await platform.start()

# Create a session
session = await platform.create_session(
    name="My First Project",
    description="Learning how to use Claude-Flow"
)

print(f"Created session: {session.id}")
```

**Using the REST API:**
```bash
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My First Project",
    "description": "Learning how to use Claude-Flow"
  }'
```

#### 3. Assign Your First Task

Now let's give the agents something to do!

**Using the CLI:**
```bash
claude-flow task create \
  --session <session-id> \
  --title "Write a Python function to calculate fibonacci numbers" \
  --type "development" \
  --priority "normal"
```

**Using Python:**
```python
from claude_flow import Task

# Create a task
task = Task(
    title="Write a Python function to calculate fibonacci numbers",
    description="Create an efficient fibonacci implementation with tests",
    type="development",
    priority="normal",
    data={
        "language": "python",
        "include_tests": True,
        "optimization": "recursive_with_memoization"
    }
)

# Assign to session
result = await session.assign_task(task)
print(f"Task assigned to: {result.assigned_agent.type}")
```

#### 4. Monitor Progress

Watch your agents work in real-time!

**Using the CLI:**
```bash
# Watch task progress
claude-flow task watch <task-id>

# Check agent status
claude-flow agents status

# View session overview
claude-flow session status <session-id>
```

**Using Python:**
```python
# Watch task progress
async for update in task.watch_progress():
    print(f"Progress: {update.progress}% - {update.message}")
    if update.status == "completed":
        break

# Get final result
result = await task.get_result()
print("Generated code:")
print(result.output.code)
print("\nGenerated tests:")
print(result.output.tests)
```

**Using WebSocket:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/tasks/task_123');
ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log(`Status: ${update.status}, Progress: ${update.progress}%`);
};
```

## Understanding the Agent Types

Claude-Flow comes with several specialized agent types:

### 👑 Queen Agent
- **Role**: Central coordinator and task dispatcher
- **Responsibilities**: Analyzes incoming tasks, selects appropriate agents, monitors progress
- **When to use**: Automatically handles complex multi-step tasks

### 🏗️ Architect Agent
- **Role**: System design and architecture planning
- **Responsibilities**: Creates technical designs, analyzes requirements, plans implementation
- **When to use**: For system design, code review, architecture decisions

```python
# Example: Ask architect to design a system
task = Task(
    title="Design a microservices architecture for e-commerce",
    type="architecture",
    data={
        "requirements": ["high_availability", "scalability", "security"],
        "constraints": ["budget_conscious", "cloud_native"],
        "output_format": "diagrams_and_documentation"
    }
)
```

### 💻 Coder Agent
- **Role**: Code generation and implementation
- **Responsibilities**: Writes code, implements features, fixes bugs
- **When to use**: For any coding tasks across multiple languages

```python
# Example: Generate a REST API
task = Task(
    title="Create a REST API for user management",
    type="development",
    data={
        "language": "python",
        "framework": "fastapi",
        "features": ["CRUD", "authentication", "validation"],
        "database": "postgresql"
    }
)
```

### 🧪 Tester Agent
- **Role**: Quality assurance and testing
- **Responsibilities**: Writes tests, performs QA, validates implementations
- **When to use**: For test generation, code validation, quality checks

```python
# Example: Generate comprehensive tests
task = Task(
    title="Create test suite for payment processing module",
    type="testing",
    data={
        "test_types": ["unit", "integration", "end_to_end"],
        "coverage_target": 95,
        "frameworks": ["pytest", "mock"]
    }
)
```

### 🔍 Analyzer Agent
- **Role**: Data analysis and insights
- **Responsibilities**: Analyzes data, generates reports, finds patterns
- **When to use**: For data analysis, reporting, pattern recognition

```python
# Example: Analyze customer data
task = Task(
    title="Analyze customer behavior patterns",
    type="analysis",
    data={
        "dataset_path": "/data/customers.csv",
        "analysis_type": "behavioral_segmentation",
        "output_format": "report_with_visualizations"
    }
)
```

### 📝 Writer Agent
- **Role**: Content creation and documentation
- **Responsibilities**: Writes documentation, creates content, generates reports
- **When to use**: For documentation, content creation, report generation

```python
# Example: Generate documentation
task = Task(
    title="Create API documentation",
    type="documentation",
    data={
        "source_code_path": "/src/api",
        "format": "openapi_3",
        "include_examples": True,
        "target_audience": "developers"
    }
)
```

## Common Use Cases and Examples

### 1. Building a Complete Web Application

Let's build a todo application from scratch:

```python
# Create a session for the project
session = await platform.create_session(
    name="Todo App Development",
    description="Build a complete todo application with React frontend and Python backend"
)

# Step 1: Architecture planning
arch_task = Task(
    title="Design todo app architecture",
    type="architecture",
    data={
        "requirements": ["web_frontend", "rest_api", "database", "authentication"],
        "tech_stack": "react_python_postgresql"
    }
)
await session.assign_task(arch_task)

# Step 2: Backend development
backend_task = Task(
    title="Implement todo API backend",
    type="development",
    data={
        "language": "python",
        "framework": "fastapi",
        "features": ["crud_operations", "user_auth", "task_management"],
        "database": "postgresql"
    },
    depends_on=[arch_task.id]  # Wait for architecture
)
await session.assign_task(backend_task)

# Step 3: Frontend development
frontend_task = Task(
    title="Build React frontend",
    type="development",
    data={
        "language": "javascript",
        "framework": "react",
        "features": ["task_list", "add_task", "edit_task", "delete_task", "user_login"]
    },
    depends_on=[backend_task.id]  # Wait for backend API
)
await session.assign_task(frontend_task)

# Step 4: Testing
test_task = Task(
    title="Create comprehensive test suite",
    type="testing",
    data={
        "test_types": ["unit", "integration", "e2e"],
        "components": ["backend_api", "frontend_components"]
    },
    depends_on=[backend_task.id, frontend_task.id]
)
await session.assign_task(test_task)

# Step 5: Documentation
docs_task = Task(
    title="Generate project documentation",
    type="documentation",
    data={
        "include": ["api_docs", "setup_guide", "user_manual"],
        "format": "markdown"
    },
    depends_on=[test_task.id]
)
await session.assign_task(docs_task)

# Monitor overall progress
async for update in session.watch_progress():
    print(f"Project progress: {update.completed_tasks}/{update.total_tasks} tasks completed")
    if update.status == "completed":
        print("Todo app development completed!")
        break
```

### 2. Data Analysis Pipeline

Analyze sales data and generate insights:

```python
# Create analysis session
session = await platform.create_session(
    name="Sales Data Analysis",
    description="Comprehensive analysis of Q4 sales data"
)

# Step 1: Data cleaning and preparation
clean_task = Task(
    title="Clean and prepare sales data",
    type="analysis",
    data={
        "dataset_path": "/data/sales_q4.csv",
        "operations": ["remove_duplicates", "handle_missing_values", "normalize_dates"],
        "output_format": "cleaned_dataset"
    }
)

# Step 2: Exploratory analysis
explore_task = Task(
    title="Perform exploratory data analysis",
    type="analysis",
    data={
        "focus_areas": ["sales_trends", "product_performance", "geographic_distribution"],
        "visualizations": True,
        "statistical_summary": True
    },
    depends_on=[clean_task.id]
)

# Step 3: Advanced analytics
advanced_task = Task(
    title="Advanced sales analytics",
    type="analysis",
    data={
        "techniques": ["customer_segmentation", "forecasting", "correlation_analysis"],
        "time_period": "quarterly",
        "prediction_horizon": "3_months"
    },
    depends_on=[explore_task.id]
)

# Step 4: Report generation
report_task = Task(
    title="Generate executive sales report",
    type="documentation",
    data={
        "sections": ["executive_summary", "key_findings", "recommendations", "appendices"],
        "include_visualizations": True,
        "target_audience": "executives"
    },
    depends_on=[advanced_task.id]
)

# Assign all tasks
for task in [clean_task, explore_task, advanced_task, report_task]:
    await session.assign_task(task)
```

### 3. Code Review and Optimization

Review and improve existing code:

```python
# Code review session
session = await platform.create_session(
    name="Code Review and Optimization",
    description="Review and optimize the user authentication module"
)

# Step 1: Code analysis
analysis_task = Task(
    title="Analyze authentication code",
    type="architecture",
    data={
        "code_path": "/src/auth",
        "focus_areas": ["security", "performance", "maintainability"],
        "standards": ["pep8", "security_best_practices"]
    }
)

# Step 2: Security review
security_task = Task(
    title="Security vulnerability assessment",
    type="analysis",
    data={
        "scan_types": ["static_analysis", "dependency_check", "pattern_matching"],
        "security_standards": ["owasp_top10", "authentication_best_practices"]
    },
    depends_on=[analysis_task.id]
)

# Step 3: Performance optimization
optimization_task = Task(
    title="Optimize authentication performance",
    type="development",
    data={
        "optimization_targets": ["database_queries", "caching", "session_management"],
        "performance_goals": {"response_time": "<100ms", "throughput": ">1000_rps"}
    },
    depends_on=[analysis_task.id]
)

# Step 4: Enhanced testing
testing_task = Task(
    title="Create comprehensive auth tests",
    type="testing",
    data={
        "test_types": ["unit", "integration", "security", "performance"],
        "coverage_target": 98,
        "include_edge_cases": True
    },
    depends_on=[optimization_task.id]
)
```

## Best Practices

### 1. Session Organization
- **Use descriptive names**: Make session names clear and specific
- **Group related tasks**: Keep related work in the same session
- **Set appropriate timeouts**: Configure realistic timeouts for your workload
- **Use metadata**: Add project IDs, team info, and tags for organization

```python
session = await platform.create_session(
    name="E-commerce Platform - User Management Module",
    description="Implementation of user registration, authentication, and profile management",
    config={
        "max_agents": 5,
        "timeout": 7200,  # 2 hours
        "auto_assign": True
    },
    metadata={
        "project_id": "ecom_2024",
        "team": "backend_team",
        "sprint": "sprint_15",
        "tags": ["user_management", "authentication", "high_priority"]
    }
)
```

### 2. Task Design
- **Be specific**: Provide clear, detailed task descriptions
- **Include context**: Add relevant data and requirements
- **Set dependencies**: Use task dependencies for ordered execution
- **Choose appropriate types**: Use the right task type for your need

```python
# Good task example
task = Task(
    title="Implement user registration API endpoint",
    description="Create a POST /api/users/register endpoint with validation, password hashing, and email verification",
    type="development",
    priority="high",
    data={
        "framework": "fastapi",
        "validation_rules": {
            "email": "valid_email_format",
            "password": "min_8_chars_with_special",
            "username": "alphanumeric_3_to_30_chars"
        },
        "security_requirements": ["bcrypt_hashing", "rate_limiting", "input_sanitization"],
        "response_format": "json_with_user_id_and_token",
        "error_handling": ["duplicate_email", "weak_password", "invalid_input"]
    }
)
```

### 3. Monitoring and Debugging
- **Use real-time monitoring**: Subscribe to WebSocket updates
- **Check logs regularly**: Monitor agent logs for issues
- **Set up alerts**: Configure alerts for failures or long-running tasks
- **Use tracing**: Enable distributed tracing for complex workflows

```python
# Monitor session with detailed logging
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def monitor_session(session):
    async for update in session.watch_progress():
        logger.info(f"Session {session.name}: {update.completed_tasks}/{update.total_tasks} tasks completed")
        
        if update.event_type == "task_failed":
            logger.error(f"Task failed: {update.task_id} - {update.error_message}")
            # Implement retry logic or notifications
        
        elif update.event_type == "agent_error":
            logger.warning(f"Agent error: {update.agent_id} - {update.error}")
            # Check agent status and restart if needed

# Run monitoring in background
asyncio.create_task(monitor_session(session))
```

## Next Steps

Now that you've mastered the basics, here are some advanced topics to explore:

### 📚 Learn More
- **[Advanced Configuration](advanced-configuration.md)** - Customize agents and system behavior
- **[Custom Agents](custom-agents.md)** - Create your own specialized agents
- **[Memory Management](memory-management.md)** - Understand the memory system
- **[Neural Networks](neural-networks.md)** - Leverage AI for task classification and optimization

### 🚀 Deploy to Production
- **[Production Deployment](../deployment/production.md)** - Deploy with Kubernetes and monitoring
- **[Security Guide](../security/README.md)** - Secure your Claude-Flow installation
- **[Performance Tuning](../operations/performance.md)** - Optimize for your workload

### 🛠️ Integrate and Extend
- **[API Integration](../integrations/README.md)** - Integrate with external systems
- **[Custom Tools](../development/custom-tools.md)** - Build your own MCP tools
- **[Webhooks](../integrations/webhooks.md)** - React to events in external systems

### 🤝 Community and Support
- **[Community Forum](https://community.claude-flow.com)** - Ask questions and share knowledge
- **[GitHub Discussions](https://github.com/claude-flow/python-claude-flow/discussions)** - Technical discussions
- **[Examples Repository](https://github.com/claude-flow/examples)** - Real-world examples and templates

## Troubleshooting

### Common Issues

#### Agents Not Starting
```bash
# Check agent status
claude-flow agents status

# View logs
docker-compose logs claude-flow

# Restart specific agent type
claude-flow agents restart --type coder
```

#### Tasks Stuck in Pending
```bash
# Check available agents
claude-flow agents list --status active

# Increase agent capacity
claude-flow config set agents.max_workers 10

# Force task reassignment
claude-flow task reassign <task-id>
```

#### API Connection Issues
```bash
# Test API connectivity
curl http://localhost:8000/health

# Check authentication
claude-flow auth check

# Verify configuration
claude-flow config show
```

#### Memory Issues
```bash
# Check memory usage
claude-flow memory stats

# Clear cache if needed
claude-flow memory clear --type cache

# Optimize memory settings
claude-flow config set memory.max_size 2GB
```

### Getting Help

If you run into issues:

1. **Check the logs**: Most issues are logged with helpful error messages
2. **Review configuration**: Ensure your settings are correct for your environment
3. **Consult documentation**: Check the specific guide for your use case
4. **Ask the community**: Post questions in our community forum
5. **Report bugs**: Open an issue on GitHub if you find a bug

Remember: Claude-Flow is designed to be self-healing and robust, but like any complex system, it may need occasional attention. The monitoring and logging systems will help you identify and resolve issues quickly.

Happy orchestrating! 🎉