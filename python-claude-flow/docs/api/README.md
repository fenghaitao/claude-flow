# Claude-Flow API Documentation

This directory contains comprehensive API documentation for the Claude-Flow platform.

## 📚 Documentation Structure

### Core APIs
- **[Sessions API](sessions.md)** - Session management and lifecycle
- **[Tasks API](tasks.md)** - Task creation, assignment, and monitoring
- **[Agents API](agents.md)** - Agent management and coordination
- **[Events API](events.md)** - Event system and real-time updates
- **[Memory API](memory.md)** - Memory management and retrieval

### Specialized APIs
- **[Neural API](neural.md)** - Neural network and AI model integration
- **[MCP API](mcp.md)** - Model Context Protocol tools and management
- **[Monitoring API](monitoring.md)** - Metrics, health checks, and observability

### WebSocket APIs
- **[Real-time API](websocket.md)** - WebSocket endpoints for live updates
- **[Streaming API](streaming.md)** - Streaming responses and data feeds

### Authentication & Security
- **[Authentication](auth.md)** - API authentication and authorization
- **[Rate Limiting](rate-limiting.md)** - API rate limiting and quotas

## 🚀 Quick Start

### Base URL
```
Development: http://localhost:8000
Production: https://api.claude-flow.example.com
```

### Authentication
```bash
# Get an API token
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'

# Use the token in requests
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/sessions
```

### Interactive Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Spec**: http://localhost:8000/openapi.json

## 📊 API Overview

### Core Endpoints Summary

| Resource | Endpoint | Methods | Description |
|----------|----------|---------|-------------|
| Sessions | `/api/v1/sessions` | GET, POST | Manage AI coordination sessions |
| Tasks | `/api/v1/tasks` | GET, POST, PUT, DELETE | Task lifecycle management |
| Agents | `/api/v1/agents` | GET, POST | Agent status and coordination |
| Events | `/api/v1/events` | GET, POST | Event system access |
| Memory | `/api/v1/memory` | GET, POST, DELETE | Memory storage and retrieval |
| Neural | `/api/v1/neural` | POST | AI model inference |
| MCP | `/api/v1/mcp` | GET, POST | Tool execution and management |

### Status Codes

| Code | Status | Description |
|------|--------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request data |
| 401 | Unauthorized | Authentication required |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Service temporarily unavailable |

### Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The request data is invalid",
    "details": {
      "field": "title",
      "reason": "This field is required"
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_123456789"
  }
}
```

## 🔄 Common Patterns

### Pagination
```json
{
  "items": [...],
  "pagination": {
    "page": 1,
    "size": 20,
    "total": 150,
    "pages": 8,
    "has_next": true,
    "has_prev": false
  }
}
```

### Filtering and Sorting
```bash
# Filter by status
GET /api/v1/tasks?status=pending&status=running

# Sort by creation date
GET /api/v1/tasks?sort=created_at:desc

# Combine filters and sorting
GET /api/v1/tasks?type=analysis&status=completed&sort=updated_at:desc&page=2&size=50
```

### Field Selection
```bash
# Select specific fields
GET /api/v1/tasks?fields=id,title,status,created_at

# Include relationships
GET /api/v1/tasks?include=agent,session
```

## 📝 Request/Response Examples

### Creating a Session
```bash
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "Data Analysis Project",
    "description": "Analyzing customer behavior data",
    "config": {
      "max_agents": 5,
      "timeout": 3600
    }
  }'
```

Response:
```json
{
  "id": "sess_123456789",
  "name": "Data Analysis Project",
  "description": "Analyzing customer behavior data",
  "status": "active",
  "config": {
    "max_agents": 5,
    "timeout": 3600
  },
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "agents": [],
  "tasks": []
}
```

### Creating a Task
```bash
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "session_id": "sess_123456789",
    "title": "Analyze customer segments",
    "description": "Identify customer segments from purchase data",
    "type": "analysis",
    "priority": "high",
    "data": {
      "dataset_url": "s3://bucket/customer_data.csv",
      "analysis_type": "clustering",
      "output_format": "report"
    }
  }'
```

Response:
```json
{
  "id": "task_987654321",
  "session_id": "sess_123456789",
  "title": "Analyze customer segments",
  "description": "Identify customer segments from purchase data",
  "type": "analysis",
  "status": "pending",
  "priority": "high",
  "assigned_agent": null,
  "data": {
    "dataset_url": "s3://bucket/customer_data.csv",
    "analysis_type": "clustering",
    "output_format": "report"
  },
  "result": null,
  "created_at": "2024-01-15T10:35:00Z",
  "updated_at": "2024-01-15T10:35:00Z",
  "completed_at": null
}
```

## 🔄 WebSocket Connections

### Task Updates
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/tasks/task_987654321');

ws.onmessage = function(event) {
  const update = JSON.parse(event.data);
  console.log('Task update:', update);
  // Handle status changes, progress updates, etc.
};

ws.onopen = function(event) {
  console.log('Connected to task updates');
};
```

### Agent Status
```javascript
const agentWs = new WebSocket('ws://localhost:8000/ws/agents');

agentWs.onmessage = function(event) {
  const status = JSON.parse(event.data);
  console.log('Agent status:', status);
  // Handle agent availability, load, etc.
};
```

## 🔍 Advanced Features

### Bulk Operations
```bash
# Create multiple tasks
curl -X POST http://localhost:8000/api/v1/tasks/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "tasks": [
      {"title": "Task 1", "type": "analysis"},
      {"title": "Task 2", "type": "generation"}
    ]
  }'

# Update multiple tasks
curl -X PUT http://localhost:8000/api/v1/tasks/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "updates": [
      {"id": "task_1", "status": "cancelled"},
      {"id": "task_2", "priority": "low"}
    ]
  }'
```

### Async Operations
```bash
# Start long-running operation
curl -X POST http://localhost:8000/api/v1/tasks/task_123/analyze \
  -H "Prefer: respond-async"

# Response includes operation ID
{
  "operation_id": "op_456789",
  "status": "accepted",
  "estimated_completion": "2024-01-15T11:30:00Z"
}

# Check operation status
curl http://localhost:8000/api/v1/operations/op_456789
```

### Conditional Requests
```bash
# Use ETags for caching
curl -H "If-None-Match: \"abc123\"" \
  http://localhost:8000/api/v1/tasks/task_123

# Conditional updates
curl -X PUT http://localhost:8000/api/v1/tasks/task_123 \
  -H "If-Match: \"abc123\"" \
  -d '{"status": "completed"}'
```

## 📊 Monitoring and Observability

### Health Checks
```bash
# Basic health check
GET /health

# Detailed health status
GET /health/status

# Readiness probe
GET /health/ready

# Liveness probe
GET /health/live
```

### Metrics
```bash
# Prometheus metrics
GET /metrics

# Custom metrics summary
GET /api/v1/metrics/summary

# Agent performance metrics
GET /api/v1/metrics/agents

# Task metrics
GET /api/v1/metrics/tasks
```

## 🔐 Security Considerations

### API Keys
- Store API keys securely
- Rotate keys regularly
- Use environment variables, not hardcoded values
- Implement proper key scoping

### Rate Limiting
- Default: 100 requests per minute per API key
- Burst allowance: 200 requests
- Rate limit headers included in responses
- Implement exponential backoff

### Data Protection
- All data encrypted in transit (TLS 1.3)
- Sensitive data encrypted at rest
- PII handling compliant with regulations
- Audit logging for all API access

## 🚀 SDKs and Libraries

### Python SDK
```python
from claude_flow import ClaudeFlowClient

client = ClaudeFlowClient(
    api_key="your_api_key",
    base_url="https://api.claude-flow.com"
)

# Create session
session = await client.sessions.create(
    name="My Session",
    description="Test session"
)

# Create task
task = await client.tasks.create(
    session_id=session.id,
    title="Analyze data",
    type="analysis"
)
```

### JavaScript SDK
```javascript
import { ClaudeFlowClient } from '@claude-flow/js-sdk';

const client = new ClaudeFlowClient({
  apiKey: 'your_api_key',
  baseUrl: 'https://api.claude-flow.com'
});

// Create session
const session = await client.sessions.create({
  name: 'My Session',
  description: 'Test session'
});

// Create task
const task = await client.tasks.create({
  sessionId: session.id,
  title: 'Analyze data',
  type: 'analysis'
});
```

## 📖 Additional Resources

- **[API Changelog](changelog.md)** - Version history and changes
- **[Migration Guide](migration.md)** - Upgrading between versions
- **[Best Practices](best-practices.md)** - Recommended usage patterns
- **[Examples](examples/)** - Code examples and tutorials
- **[Postman Collection](postman/)** - Import into Postman for testing

## 🤝 Support

For API support and questions:
- **Documentation**: https://docs.claude-flow.com/api
- **Community**: https://community.claude-flow.com
- **Issues**: https://github.com/claude-flow/python-claude-flow/issues
- **Email**: api-support@claude-flow.com