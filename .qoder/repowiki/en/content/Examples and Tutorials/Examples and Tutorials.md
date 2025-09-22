# Examples and Tutorials

<cite>
**Referenced Files in This Document**   
- [examples/README.md](file://examples/README.md)
- [examples/01-configurations/README.md](file://examples/01-configurations/README.md)
- [examples/02-workflows/README.md](file://examples/02-workflows/README.md)
- [examples/03-demos/README.md](file://examples/03-demos/README.md)
- [examples/04-testing/README.md](file://examples/04-testing/README.md)
- [examples/05-swarm-apps/README.md](file://examples/05-swarm-apps/README.md)
- [examples/06-tutorials/README.md](file://examples/06-tutorials/README.md)
- [examples/hello-world.js](file://examples/hello-world.js)
- [examples/quick-start.sh](file://examples/quick-start.sh)
- [examples/development-workflow.json](file://examples/development-workflow.json)
- [examples/research-workflow.yaml](file://examples/research-workflow.yaml)
- [examples/batch-config-simple.json](file://examples/batch-config-simple.json)
- [examples/claude-api-error-handling.ts](file://examples/claude-api-error-handling.ts)
- [examples/prompt-copier-demo.ts](file://examples/prompt-copier-demo.ts)
- [examples/git-checkpoint-demo.md](file://examples/git-checkpoint-demo.md)
- [python-claude-flow/examples/basic_usage.py](file://python-claude-flow/examples/basic_usage.py) - *Added in recent commit*
- [python-claude-flow/demo.py](file://python-claude-flow/demo.py) - *Added in recent commit*
- [python-claude-flow/README.md](file://python-claude-flow/README.md) - *Updated in recent commit*
</cite>

## Update Summary
**Changes Made**   
- Added new section on Python implementation and usage
- Updated introduction to reflect Python port availability
- Enhanced Getting Started section with Python examples
- Added references to new Python files and demo scripts
- Updated document sources to include new Python implementation files

## Table of Contents
1. [Introduction](#introduction)
2. [Getting Started with Claude-Flow](#getting-started-with-claude-flow)
3. [Building Full-Stack Applications](#building-full-stack-applications)
4. [Conducting Research and Analysis](#conducting-research-and-analysis)
5. [Performing Security Audits](#performing-security-audits)
6. [Developing Custom Agents](#developing-custom-agents)
7. [Common Issues and Troubleshooting](#common-issues-and-troubleshooting)
8. [Performance Considerations and Optimization](#performance-considerations-and-optimization)

## Introduction

The **Claude-Flow** platform enables developers to create intelligent, multi-agent workflows for automating complex software development tasks. This tutorial section provides practical guidance on leveraging the system's capabilities across various domains, from application development to research and security. The examples are organized into categories that reflect real-world use cases, allowing users to progressively build expertise.

The repository's `examples/` directory is structured to support learning and experimentation, with dedicated folders for configurations, workflows, demos, testing, swarm-created applications, and tutorials. While specific tutorial files are currently minimal, the existing examples provide a solid foundation for understanding system capabilities.

With the recent addition of the Python implementation, users now have access to a comprehensive Python port of Claude-Flow, enabling integration with Python-based workflows and applications. The Python implementation includes full feature parity with the Node.js version, including the hive-mind agent coordination, event-driven architecture, and multi-tier memory system.

**Section sources**
- [examples/README.md](file://examples/README.md)
- [python-claude-flow/README.md](file://python-claude-flow/README.md) - *Updated in recent commit*

## Getting Started with Claude-Flow

To begin using Claude-Flow, start with the basic configuration and simple execution patterns. The system can be invoked via command line with specific configuration files that define agent behavior, coordination modes, and task parameters.

### Basic Configuration Setup

The `01-configurations` directory contains configuration templates for different use cases. A minimal configuration might look like this:

```json
{
  "swarm": {
    "mode": "basic",
    "agents": [
      {
        "role": "developer",
        "capabilities": ["code-generation", "testing"],
        "personality": "detailed"
      }
    ],
    "workflow": {
      "type": "sequential",
      "maxIterations": 3
    }
  }
}
```

This configuration defines a single developer agent operating in sequential mode with a maximum of three iteration cycles.

### Running Your First Task

Execute a simple task using the CLI:

```bash
./claude-flow swarm create "Create a simple hello world script" --config ./examples/01-configurations/basic/simple-config.json
```

Alternatively, use the quick-start script provided in the examples directory:

```bash
./examples/quick-start.sh
```

This script demonstrates the basic invocation pattern and can be modified for custom tasks.

### Hello World Example

The `hello-world.js` example demonstrates a simple output generation task:

```javascript
console.log("Hello from Claude-Flow generated code!");
module.exports = () => "Hello World";
```

This basic example can be extended to include more complex functionality as users become familiar with the system.

### Python Implementation

The Python port of Claude-Flow provides a comprehensive implementation with full feature parity. To get started with the Python version:

```bash
# Clone the repository
git clone https://github.com/claude-flow/python-claude-flow.git
cd python-claude-flow

# Install dependencies
pip install -r requirements.txt

# Run the basic usage example
python examples/basic_usage.py
```

The `basic_usage.py` example demonstrates key components of the Python implementation:

```python
#!/usr/bin/env python3
"""
Basic usage example for Claude-Flow Python port
"""

import asyncio
from claude_flow.core.config import config
from claude_flow.core.logger import logger
from claude_flow.core.event_bus import event_bus, EventType, publish_agent_event

async def main():
    # Configuration management
    print(f"App Name: {config.app_name}")
    print(f"Version: {config.version}")
    print(f"Environment: {config.environment}")
    
    # Event bus system
    await event_bus.start()
    await publish_agent_event(
        agent_id="example_agent_001",
        event_type=EventType.AGENT_CREATED,
        data={"name": "Example Agent", "type": "worker"}
    )
    
    # MCP client integration
    if config.mcp.enabled:
        connected = await mcp_client.connect()
        if connected:
            tools = mcp_client.get_tools()
            print(f"Found {len(tools)} MCP tools")

if __name__ == "__main__":
    asyncio.run(main())
```

The demo script provides a simplified demonstration of the core components:

```python
#!/usr/bin/env python3
"""
Claude-Flow Python Demo
"""

def demo_config():
    from claude_flow.core.config_simple import config
    print(f"App: {config.app_name} v{config.version}")
    print(f"Base Directory: {config.base_dir}")
    
    # Feature flags
    print(f"Swarm Coordination: {config.get_feature_flag('swarm_coordination')}")

def demo_event_bus():
    from claude_flow.core.event_bus_simple import event_bus, EventType
    event_bus.start()
    
    def agent_event_handler(event):
        print(f"Agent event: {event.type.value} - {event.data}")
    
    event_bus.subscribe(EventType.AGENT_CREATED, agent_event_handler)
    event_bus.stop()

if __name__ == "__main__":
    demo_config()
    demo_event_bus()
```

**Section sources**
- [examples/01-configurations/README.md](file://examples/01-configurations/README.md)
- [examples/hello-world.js](file://examples/hello-world.js)
- [examples/quick-start.sh](file://examples/quick-start.sh)
- [examples/batch-config-simple.json](file://examples/batch-config-simple.json)
- [python-claude-flow/examples/basic_usage.py](file://python-claude-flow/examples/basic_usage.py) - *Added in recent commit*
- [python-claude-flow/demo.py](file://python-claude-flow/demo.py) - *Added in recent commit*

## Building Full-Stack Applications

Claude-Flow can generate complete full-stack applications through its swarm intelligence system. The `05-swarm-apps` directory is designed to store applications created by the system, though specific examples are not yet populated.

### Application Generation Workflow

To generate a full-stack application, use a development workflow configuration:

```json
{
  "swarm": {
    "mode": "development",
    "agents": [
      {
        "role": "frontend-developer",
        "skills": ["react", "ui-design"]
      },
      {
        "role": "backend-developer",
        "skills": ["nodejs", "rest-api"]
      },
      {
        "role": "devops-engineer",
        "skills": ["docker", "deployment"]
      }
    ],
    "workflow": {
      "type": "parallel",
      "synchronization": "gated"
    }
  }
}
```

Execute with:

```bash
./claude-flow swarm create "Build a task management application with React frontend and Node.js backend" --config ./examples/development-workflow.json
```

### REST API Example

The `rest-api-simple` example directory (though empty) indicates support for REST API generation. A typical API endpoint might be generated as:

```javascript
// Generated API endpoint
app.get('/api/tasks', authenticate, async (req, res) => {
  try {
    const tasks = await TaskModel.find({ user: req.user.id });
    res.json({ success: true, data: tasks });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});
```

The system would automatically generate accompanying tests, documentation, and deployment configurations.

**Section sources**
- [examples/development-workflow.json](file://examples/development-workflow.json)
- [examples/05-swarm-apps/README.md](file://examples/05-swarm-apps/README.md)

## Conducting Research and Analysis

Claude-Flow supports research-oriented tasks through specialized workflow configurations and analysis capabilities.

### Research Workflow Configuration

Use the research workflow template to conduct systematic investigations:

```yaml
swarm:
  mode: research
  agents:
    - role: researcher
      specialties:
        - literature-review
        - data-analysis
        - hypothesis-testing
  workflow:
    type: hierarchical
    phases:
      - phase: problem-definition
        duration: 2h
      - phase: data-collection
        duration: 4h
      - phase: analysis
        duration: 6h
      - phase: reporting
        duration: 2h
```

Run the research workflow:

```bash
./claude-flow swarm create "Analyze trends in AI development frameworks" --config ./examples/research-workflow.yaml
```

### Data Pipeline Example

The `data-pipeline` example directory suggests support for data processing workflows. A typical pipeline might include:

```javascript
// Data extraction
const extractData = async (source) => {
  // Implementation generated by Claude-Flow
};

// Data transformation
const transformData = (rawData) => {
  // Implementation generated by Claude-Flow
};

// Data loading
const loadData = async (processedData, destination) => {
  // Implementation generated by Claude-Flow
};

// Orchestration
const runPipeline = async () => {
  const rawData = await extractData('source-api');
  const processedData = transformData(rawData);
  await loadData(processedData, 'data-warehouse');
};
```

**Section sources**
- [examples/research-workflow.yaml](file://examples/research-workflow.yaml)
- [examples/02-workflows/README.md](file://examples/02-workflows/README.md)

## Performing Security Audits

Security analysis can be conducted using specialized agent configurations and validation workflows.

### Security Audit Configuration

Create a security-focused configuration:

```json
{
  "swarm": {
    "mode": "security-audit",
    "agents": [
      {
        "role": "security-analyst",
        "capabilities": [
          "vulnerability-scanning",
          "code-review",
          "penetration-testing-simulation"
        ]
      }
    ],
    "workflow": {
      "type": "comprehensive",
      "checks": [
        "dependency-vulnerabilities",
        "authentication-flaws",
        "input-validation",
        "configuration-security"
      ]
    }
  }
}
```

Execute a security audit:

```bash
./claude-flow swarm audit ./target-project --config ./examples/security-config.json
```

### Error Handling Example

The `claude-api-error-handling.ts` example demonstrates proper error management:

```typescript
// Generated error handling pattern
interface ErrorResponse {
  success: false;
  error: {
    code: string;
    message: string;
    details?: any;
  };
}

const handleApiError = (error: any): ErrorResponse => {
  if (error instanceof ValidationError) {
    return {
      success: false,
      error: {
        code: 'VALIDATION_ERROR',
        message: 'Invalid input parameters',
        details: error.validationDetails
      }
    };
  }
  
  return {
    success: false,
    error: {
      code: 'INTERNAL_ERROR',
      message: 'An unexpected error occurred'
    }
  };
};
```

**Section sources**
- [examples/claude-api-error-handling.ts](file://examples/claude-api-error-handling.ts)
- [examples/04-testing/README.md](file://examples/04-testing/README.md)

## Developing Custom Agents

Custom agent development allows users to extend the system's capabilities for specialized domains.

### Agent Customization

Create custom agents by defining their roles and capabilities:

```json
{
  "swarm": {
    "mode": "custom",
    "agents": [
      {
        "role": "database-specialist",
        "personality": "precise",
        "expertise": [
          "query-optimization",
          "schema-design",
          "index-strategy"
        ],
        "tools": [
          "sql-analyzer",
          "performance-profiler"
        ]
      }
    ]
  }
}
```

### Agent Communication Example

The `prompt-copier-demo.ts` example illustrates agent-to-agent communication patterns:

```typescript
// Generated agent communication pattern
class AgentMessenger {
  private messageQueue: Message[] = [];
  
  send(targetAgent: string, content: AgentMessage) {
    this.messageQueue.push({
      to: targetAgent,
      from: this.agentId,
      content,
      timestamp: new Date()
    });
  }
  
  processMessages() {
    // Implementation generated by Claude-Flow
  }
}
```

### Git Integration

The `git-checkpoint-demo.md` example demonstrates version control integration:

```markdown
# Git Checkpoint Workflow

1. Initialize repository: `git init`
2. Make changes through Claude-Flow swarm
3. Create checkpoint: `git add . && git commit -m "Swarm checkpoint: feature implementation"`
4. Push to remote: `git push origin main`
```

**Section sources**
- [examples/prompt-copier-demo.ts](file://examples/prompt-copier-demo.ts)
- [examples/git-checkpoint-demo.md](file://examples/git-checkpoint-demo.md)
- [examples/06-tutorials/README.md](file://examples/06-tutorials/README.md)

## Common Issues and Troubleshooting

Users may encounter various issues when working with Claude-Flow. This section addresses common problems and their solutions.

### Configuration Issues

**Problem**: Configuration file not found
**Solution**: Ensure the path to the configuration file is correct relative to the execution directory:

```bash
# Correct usage
./claude-flow swarm create "task" --config ./examples/01-configurations/basic/simple-config.json
```

### Permission Errors

**Problem**: Shell scripts not executable
**Solution**: Make scripts executable:

```bash
chmod +x examples/quick-start.sh
./examples/quick-start.sh
```

### Memory and Performance Issues

**Problem**: High memory usage during swarm execution
**Solution**: Monitor memory usage and adjust swarm size:

```bash
# Check memory store
cat memory/memory-store.json | jq '.usage'

# Limit agent count in configuration
{
  "swarm": {
    "maxAgents": 3
  }
}
```

### Dependency Problems

**Problem**: Missing dependencies
**Solution**: Install required packages:

```bash
npm install
# or
pnpm install
```

**Section sources**
- [examples/README.md](file://examples/README.md)
- [memory/memory-store.json](file://memory/memory-store.json)

## Performance Considerations and Optimization

Optimizing Claude-Flow performance involves configuration tuning, resource management, and workflow design.

### Configuration Optimization

Use appropriate coordination modes for your use case:

```json
{
  "swarm": {
    "mode": "optimized",
    "coordination": "parallel",  // Use "sequential" for dependent tasks
    "batchSize": 5,              // Optimize batch processing
    "timeout": 300               // Set appropriate timeouts
  }
}
```

### Resource Management

Monitor system resources using built-in tools:

```bash
# Run performance monitoring
./scripts/performance-monitor.js --interval 1000
```

### Workflow Efficiency

Design efficient workflows by minimizing unnecessary iterations:

```json
{
  "workflow": {
    "maxIterations": 3,
    "earlyTermination": true,
    "validationThreshold": 0.95
  }
}
```

### Caching Strategies

Implement caching to improve performance:

```json
{
  "cache": {
    "enabled": true,
    "ttl": 3600,
    "strategy": "lru",
    "maxSize": 100
  }
}
```

**Section sources**
- [examples/batch-config-advanced.json](file://examples/batch-config-advanced.json)
- [scripts/performance-monitor.js](file://scripts/performance-monitor.js)