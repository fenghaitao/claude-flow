# Claude-Flow: Enterprise AI Agent Orchestration Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-supported-blue.svg)](https://www.docker.com/)
[![Kubernetes](https://img.shields.io/badge/kubernetes-ready-green.svg)](https://kubernetes.io/)

A powerful, enterprise-grade AI agent orchestration platform that enables intelligent automation through coordinated AI agents with hive-mind capabilities, neural pattern recognition, and comprehensive observability.

## 🚀 Features

### Core Capabilities
- **🧠 Hive-Mind Agent Coordination**: Queen/Worker architecture with intelligent task distribution
- **🔄 Event-Driven Architecture**: Async event bus with priority queues and replay capabilities
- **🗄️ Multi-Tier Memory System**: SQLite, Redis, and PostgreSQL for different persistence needs
- **🧮 Neural Pattern Recognition**: Task classification, complexity estimation, and pattern matching
- **🔌 MCP Protocol Integration**: 87 pre-built tools across 6 categories
- **📊 Enterprise Monitoring**: Prometheus metrics, Grafana dashboards, and distributed tracing
- **☁️ Cloud-Native Deployment**: Docker, Kubernetes, and Helm chart support

### Agent Specializations
- **👑 Queen Agent**: Central coordinator with task assignment and resource allocation
- **🏗️ Architect Agent**: System design and code analysis capabilities
- **💻 Coder Agent**: Code generation and debugging across multiple languages
- **🧪 Tester Agent**: Test generation and quality assurance automation
- **🔍 Analyzer Agent**: Data analysis and insight generation
- **📝 Writer Agent**: Documentation and content creation

### Enterprise Features
- **🔐 Security**: RBAC, network policies, and secret management
- **📈 Scalability**: Horizontal pod autoscaling and load balancing
- **🔍 Observability**: OpenTelemetry tracing, structured logging, and health checks
- **🛠️ DevOps Ready**: CI/CD integration, backup strategies, and monitoring

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Deployment](#deployment)
- [Monitoring](#monitoring)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Git

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/claude-flow/python-claude-flow.git
   cd python-claude-flow
   ```

2. **Set up environment**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

4. **Start with Docker Compose**
   ```bash
   docker-compose up -d
   ```

5. **Access the platform**
   - Web UI: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Grafana Dashboard: http://localhost:3000 (admin/admin123)
   - Jaeger Tracing: http://localhost:16686

## 📦 Installation

### Option 1: Docker Compose (Recommended for Development)

```bash
# Clone and start
git clone https://github.com/claude-flow/python-claude-flow.git
cd python-claude-flow
cp .env.example .env
# Edit .env with your configuration
docker-compose up -d
```

### Option 2: Python Package Installation

```bash
pip install claude-flow
```

### Option 3: Kubernetes Deployment

```bash
# Using Helm (Recommended for Production)
helm repo add claude-flow https://charts.claude-flow.io
helm install claude-flow claude-flow/claude-flow --values values.yaml

# Or using kubectl
kubectl apply -f k8s/
```

## ⚙️ Configuration

### Environment Variables

```bash
# Core Configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/claudeflow
REDIS_URL=redis://localhost:6379/0

# AI Services
ANTHROPIC_API_KEY=your_anthropic_key_here
OPENAI_API_KEY=your_openai_key_here  # Optional

# Security
SECRET_KEY=your_secret_key_here
JWT_SECRET=your_jwt_secret_here

# Monitoring
JAEGER_ENDPOINT=localhost:14268
PROMETHEUS_GATEWAY=localhost:9091
```

### Configuration Files

The platform supports hierarchical configuration loading:

1. **config/config.yaml** - Base configuration
2. **config/config.{environment}.yaml** - Environment-specific overrides
3. **Environment variables** - Runtime overrides

Example configuration:

```yaml
# config/config.yaml
database:
  pool_size: 20
  timeout: 30

agents:
  max_workers: 10
  task_timeout: 300

monitoring:
  prometheus:
    enabled: true
    port: 9090
  jaeger:
    enabled: true
    endpoint: "localhost:14268"
```

## 🎯 Usage

### CLI Interface

```bash
# Start the platform
claude-flow start

# Create a new session
claude-flow session create "My AI Project"

# Assign a task to agents
claude-flow task create \
  --title "Build a web scraper" \
  --type "development" \
  --priority high \
  --data '{"language": "python", "target": "news sites"}'

# Monitor agent status
claude-flow agents status

# View session history
claude-flow session list

# Export session data
claude-flow session export <session-id> --format json
```

### Python API

```python
from claude_flow import ClaudeFlow, Task, Agent

# Initialize the platform
platform = ClaudeFlow(config_path="config/config.yaml")
await platform.start()

# Create a session
session = await platform.create_session(
    name="AI Development Project",
    description="Building an intelligent automation system"
)

# Create and assign a task
task = Task(
    title="Generate API documentation",
    type="documentation",
    priority="high",
    data={
        "source_code_path": "/app/src",
        "output_format": "markdown",
        "include_examples": True
    }
)

result = await session.assign_task(task)
print(f"Task assigned to: {result.assigned_agent}")

# Monitor progress
async for update in session.watch_progress():
    print(f"Progress: {update.progress}% - {update.message}")

# Get results
final_result = await task.get_result()
print(f"Generated documentation: {final_result.output}")
```

### REST API

```bash
# Create a session
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"name": "My Session", "description": "Test session"}'

# Assign a task
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-uuid",
    "title": "Analyze data",
    "type": "analysis",
    "data": {"dataset": "/path/to/data.csv"}
  }'

# Get task status
curl http://localhost:8000/api/v1/tasks/{task_id}/status

# List all agents
curl http://localhost:8000/api/v1/agents
```

## 📚 API Reference

### Core Endpoints

#### Sessions
- `POST /api/v1/sessions` - Create a new session
- `GET /api/v1/sessions` - List all sessions
- `GET /api/v1/sessions/{id}` - Get session details
- `PUT /api/v1/sessions/{id}` - Update session
- `DELETE /api/v1/sessions/{id}` - Delete session

#### Tasks
- `POST /api/v1/tasks` - Create a new task
- `GET /api/v1/tasks` - List tasks with filtering
- `GET /api/v1/tasks/{id}` - Get task details
- `PUT /api/v1/tasks/{id}` - Update task
- `POST /api/v1/tasks/{id}/cancel` - Cancel task

#### Agents
- `GET /api/v1/agents` - List all agents
- `GET /api/v1/agents/{id}` - Get agent details
- `POST /api/v1/agents/{id}/assign` - Assign task to agent
- `GET /api/v1/agents/{id}/status` - Get agent status

#### Monitoring
- `GET /health` - Health check endpoint
- `GET /health/ready` - Readiness probe
- `GET /health/live` - Liveness probe
- `GET /metrics` - Prometheus metrics
- `GET /api/v1/metrics/summary` - System metrics summary

### WebSocket Endpoints

```javascript
// Real-time task updates
const ws = new WebSocket('ws://localhost:8000/ws/tasks/{task_id}');
ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log('Task update:', update);
};

// Agent status monitoring
const agentWs = new WebSocket('ws://localhost:8000/ws/agents');
agentWs.onmessage = (event) => {
  const status = JSON.parse(event.data);
  console.log('Agent status:', status);
};
```

## 🚀 Deployment

### Development Environment

```bash
# Start with Docker Compose
docker-compose up -d

# Or start individual services
docker-compose up -d postgres redis
python -m claude_flow.cli.main server --reload
```

### Production Deployment

#### Option 1: Docker Swarm

```bash
# Deploy to Docker Swarm
docker stack deploy -c docker-compose.prod.yml claude-flow
```

#### Option 2: Kubernetes

```bash
# Using Helm (Recommended)
helm repo add claude-flow https://charts.claude-flow.io
helm install claude-flow claude-flow/claude-flow \
  --values production-values.yaml \
  --namespace claude-flow \
  --create-namespace

# Using kubectl
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/database.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/ingress.yaml
```

#### Option 3: Cloud Platforms

**AWS EKS**
```bash
# Install with AWS Load Balancer Controller
helm install claude-flow claude-flow/claude-flow \
  --set loadBalancer.enabled=true \
  --set loadBalancer.annotations."service\.beta\.kubernetes\.io/aws-load-balancer-type"="nlb"
```

**Google GKE**
```bash
# Install with Google Cloud Load Balancer
helm install claude-flow claude-flow/claude-flow \
  --set ingress.className="gce" \
  --set ingress.annotations."kubernetes\.io/ingress\.global-static-ip-name"="claude-flow-ip"
```

**Azure AKS**
```bash
# Install with Azure Application Gateway
helm install claude-flow claude-flow/claude-flow \
  --set ingress.className="azure/application-gateway"
```

### Environment Configuration

#### Development
```yaml
# values-dev.yaml
replicas: 1
resources:
  limits:
    memory: "1Gi"
    cpu: "500m"
postgresql:
  enabled: true
monitoring:
  enabled: true
```

#### Staging
```yaml
# values-staging.yaml
replicas: 2
resources:
  limits:
    memory: "2Gi"
    cpu: "1000m"
ingress:
  enabled: true
  hosts:
    - staging.claude-flow.example.com
```

#### Production
```yaml
# values-prod.yaml
replicas: 5
autoscaling:
  enabled: true
  maxReplicas: 20
resources:
  limits:
    memory: "4Gi"
    cpu: "2000m"
ingress:
  enabled: true
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
  hosts:
    - claude-flow.example.com
```

## 📊 Monitoring

### Metrics and Dashboards

The platform provides comprehensive monitoring through:

- **Prometheus Metrics**: System metrics, agent performance, task statistics
- **Grafana Dashboards**: Pre-built dashboards for system overview and deep-dive analysis
- **Jaeger Tracing**: Distributed tracing for request flow analysis
- **Health Checks**: Kubernetes-ready health endpoints

### Key Metrics

```prometheus
# Agent metrics
claude_flow_agents_total{type="queen"} 1
claude_flow_agents_active{type="coder"} 3
claude_flow_tasks_assigned_total 1250
claude_flow_tasks_completed_total 1180

# Performance metrics
claude_flow_request_duration_seconds_bucket{le="0.1"} 45
claude_flow_request_duration_seconds_bucket{le="0.5"} 120
claude_flow_claude_api_calls_total{model="claude-3-sonnet"} 890

# System metrics
claude_flow_database_connections_active 15
claude_flow_memory_usage_bytes 2.1e+09
```

### Alerting Rules

```yaml
# alerts.yaml
groups:
- name: claude_flow
  rules:
  - alert: HighErrorRate
    expr: rate(claude_flow_requests_total{status=~"5.."}[5m]) > 0.05
    labels:
      severity: warning
    annotations:
      summary: "High error rate detected"
      
  - alert: AgentDown
    expr: claude_flow_agents_active < 1
    labels:
      severity: critical
    annotations:
      summary: "No active agents available"
```

## 🛠️ Development

### Setting Up Development Environment

```bash
# Clone and setup
git clone https://github.com/claude-flow/python-claude-flow.git
cd python-claude-flow

# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests
make test

# Start development server
make dev
```

### Project Structure

```
claude-flow/
├── src/claude_flow/           # Main application code
│   ├── core/                  # Core interfaces and base classes
│   ├── agents/                # Agent implementations
│   ├── events/                # Event system
│   ├── memory/                # Memory management
│   ├── neural/                # Neural network components
│   ├── mcp/                   # MCP protocol implementation
│   ├── cli/                   # Command-line interface
│   ├── api/                   # REST API endpoints
│   └── monitoring/            # Observability components
├── tests/                     # Test suite
├── k8s/                       # Kubernetes manifests
├── helm/                      # Helm charts
├── config/                    # Configuration files
└── docs/                      # Documentation
```

### Testing

```bash
# Run all tests
make test

# Run specific test categories
make test-unit
make test-integration
make test-e2e
make test-performance

# Run with coverage
make test-coverage

# Run linting
make lint

# Run security checks
make security-check
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run the test suite (`make test`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Create a Pull Request

### Code Style

- Follow PEP 8 for Python code
- Use type hints for all functions
- Write docstrings for all public APIs
- Maintain test coverage above 90%
- Use conventional commits for commit messages

## 🔧 Configuration Reference

### Complete Configuration Options

```yaml
# config/config.yaml - Complete configuration reference
environment: production
debug: false
log_level: INFO

# Database configuration
database:
  url: postgresql://user:pass@host:5432/db
  pool_size: 20
  max_overflow: 0
  pool_timeout: 30
  pool_recycle: 3600
  echo: false

# Redis configuration
redis:
  url: redis://host:6379/0
  max_connections: 50
  retry_on_timeout: true
  socket_timeout: 30
  decode_responses: true

# Claude AI configuration
claude:
  api_key: ""
  model: claude-3-sonnet-20240229
  max_tokens: 4096
  timeout: 30
  max_retries: 3
  base_url: https://api.anthropic.com

# Agent configuration
agents:
  max_workers: 10
  task_timeout: 300
  coordination_interval: 10
  heartbeat_interval: 30
  max_memory_usage: 1073741824  # 1GB

# Event system configuration
events:
  max_queue_size: 10000
  batch_size: 100
  flush_interval: 5
  persistence_enabled: true

# Memory system configuration
memory:
  sqlite:
    path: data/memory.db
    wal_mode: true
  redis:
    ttl: 3600
    max_size: 1000
  semantic_search:
    enabled: true
    model: all-MiniLM-L6-v2

# Neural network configuration
neural:
  task_classification:
    model: distilbert-base-uncased
    cache_size: 1000
  complexity_estimation:
    model: gradient_boosting
    features: 20
  pattern_matching:
    similarity_threshold: 0.8

# MCP protocol configuration
mcp:
  enabled: true
  port: 9000
  max_connections: 100
  tools:
    discovery_enabled: true
    categories:
      - swarm
      - neural
      - memory
      - system
      - external
      - utility

# API configuration
api:
  host: 0.0.0.0
  port: 8000
  cors_origins:
    - http://localhost:3000
    - https://app.claude-flow.com
  rate_limiting:
    enabled: true
    requests_per_minute: 100

# Monitoring configuration
monitoring:
  prometheus:
    enabled: true
    port: 9090
    path: /metrics
  jaeger:
    enabled: true
    endpoint: localhost:14268
    service_name: claude-flow
  health_checks:
    enabled: true
    interval: 30

# Security configuration
security:
  cors_origins:
    - https://app.claude-flow.com
  allowed_hosts:
    - claude-flow.com
    - api.claude-flow.com
  csrf_protection: true
  rate_limiting:
    enabled: true
    requests_per_minute: 100

# Tracing configuration
tracing:
  enabled: true
  service_name: claude-flow
  service_version: 1.0.0
  sample_rate: 0.1
  jaeger:
    endpoint: localhost:14268

# Logging configuration
logging:
  level: INFO
  format: json
  include_trace_info: true
  file: logs/claude-flow.log
  max_file_size: 10485760  # 10MB
  backup_count: 5
```

## 🐛 Troubleshooting

### Common Issues

#### Database Connection Issues
```bash
# Check database connectivity
claude-flow db check

# Run database migrations
claude-flow db migrate

# Reset database (development only)
claude-flow db reset --force
```

#### Agent Not Starting
```bash
# Check agent logs
kubectl logs -f deployment/claude-flow-app -n claude-flow

# Restart agents
claude-flow agents restart

# Check resource usage
kubectl top pods -n claude-flow
```

#### Memory Issues
```bash
# Clear memory cache
claude-flow memory clear --type cache

# Check memory usage
claude-flow memory stats

# Optimize memory settings
claude-flow memory optimize
```

### Performance Tuning

```yaml
# High-performance configuration
agents:
  max_workers: 20
database:
  pool_size: 50
redis:
  max_connections: 100
neural:
  batch_size: 32
  cache_size: 5000
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Support

- **Documentation**: https://docs.claude-flow.com
- **Community**: https://community.claude-flow.com
- **Issues**: https://github.com/claude-flow/python-claude-flow/issues
- **Discussions**: https://github.com/claude-flow/python-claude-flow/discussions
- **Email**: support@claude-flow.com

## 🙏 Acknowledgments

- [Anthropic](https://www.anthropic.com/) for Claude AI
- [OpenTelemetry](https://opentelemetry.io/) for observability
- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
- [Pydantic](https://pydantic-docs.helpmanual.io/) for data validation

---

**Built with ❤️ by the Claude-Flow Team**