# Hive-Mind API

<cite>
**Referenced Files in This Document**   
- [docker-compose.hive-mind.yml](file://docker/docker-compose.hive-mind.yml)
- [README.md](file://README.md)
- [CLI_USAGE.md](file://benchmark/CLI_USAGE.md)
- [NON_INTERACTIVE_COMMANDS.md](file://benchmark/NON_INTERACTIVE_COMMANDS.md)
- [REAL_EXECUTION.md](file://benchmark/REAL_EXECUTION.md)
- [api_reference.md](file://benchmark/docs/api_reference.md)
- [quick-start.md](file://benchmark/docs/quick-start.md)
- [coordination-modes.md](file://benchmark/docs/coordination-modes.md)
- [basic-usage.md](file://benchmark/docs/basic-usage.md)
- [config.go](file://benchmark/config/non_interactive_defaults.yaml)
- [run_real_benchmarks.py](file://benchmark/run_real_benchmarks.py)
- [hive-mind-load-test.py](file://benchmark/scripts/hive-mind-load-test.py)
- [swarm_performance_suite.py](file://benchmark/scripts/swarm_performance_suite.py)
- [development-workflow.json](file://examples/development-workflow.json)
- [research-workflow.yaml](file://examples/research-workflow.yaml)
- [batch-config-advanced.json](file://examples/batch-config-advanced.json)
- [package.json](file://package.json)
- [memory-store.json](file://memory/memory-store.json)
- [state.json](file://swarm-memory/state.json)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)

## Introduction
The Hive-Mind API provides a RESTful interface for orchestrating distributed agent swarms in the agentic workflow system. This documentation details the endpoints for swarm initialization, agent management, task distribution, and status monitoring. The system enables coordinated execution of AI agents across various coordination modes including centralized, hierarchical, and mesh topologies. The API supports authentication, rate limiting, and comprehensive error handling for robust production deployment.

## Project Structure
The project follows a modular structure with distinct directories for different concerns. The core orchestration logic resides in the benchmark directory, which contains the primary implementation of the Hive-Mind system. Configuration files are centralized in dedicated directories, while examples provide practical usage patterns. The src directory contains the main application code organized by functional domains such as coordination, swarm management, and API interfaces.

```mermaid
graph TB
subgraph "Core System"
B[benchmark] --> BD[docs]
B --> BS[scripts]
B --> BC[config]
B --> BR[reports]
B --> BH[hive-mind-benchmarks]
end
subgraph "Configuration"
C[config] --> NIC[non_interactive_defaults.yaml]
end
subgraph "Examples"
E[examples] --> EC[01-configurations]
E --> EW[02-workflows]
E --> ED[03-demos]
end
subgraph "Infrastructure"
D[docker] --> DC[docker-compose.hive-mind.yml]
end
subgraph "Data Storage"
M[memory] --> MS[memory-store.json]
SM[swarm-memory] --> SS[state.json]
end
B --> C
B --> E
B --> D
B --> M
B --> SM
```

**Diagram sources**
- [docker-compose.hive-mind.yml](file://docker/docker-compose.hive-mind.yml)
- [non_interactive_defaults.yaml](file://benchmark/config/non_interactive_defaults.yaml)
- [memory-store.json](file://memory/memory-store.json)
- [state.json](file://swarm-memory/state.json)

**Section sources**
- [README.md](file://README.md)
- [package.json](file://package.json)

## Core Components
The Hive-Mind system consists of several core components that work together to enable distributed agent orchestration. The coordination engine manages agent swarms and task distribution, while the memory subsystem maintains state across sessions. The API gateway exposes RESTful endpoints for external interaction, and the configuration manager handles system settings and defaults. The benchmarking framework provides performance measurement and optimization capabilities.

**Section sources**
- [api_reference.md](file://benchmark/docs/api_reference.md)
- [coordination-modes.md](file://benchmark/docs/coordination-modes.md)
- [basic-usage.md](file://benchmark/docs/basic-usage.md)

## Architecture Overview
The Hive-Mind system follows a microservices architecture with clear separation of concerns. The orchestration layer manages swarm lifecycle and task distribution, while agent nodes execute assigned tasks. The API layer provides RESTful interfaces for external systems to interact with the swarm. A centralized configuration service manages system-wide settings, and a distributed memory system maintains state across components.

```mermaid
graph TD
Client[External Client] --> API[API Gateway]
API --> Orchestrator[Swarm Orchestrator]
API --> Config[Configuration Service]
API --> Monitor[Performance Monitor]
Orchestrator --> Agent1[Agent Node 1]
Orchestrator --> Agent2[Agent Node 2]
Orchestrator --> AgentN[Agent Node N]
Config --> Defaults[Default Configurations]
Monitor --> Metrics[Performance Metrics]
Monitor --> Logs[Execution Logs]
Agent1 --> Memory[Distributed Memory]
Agent2 --> Memory
AgentN --> Memory
Memory --> Persistence[State Persistence]
style API fill:#4CAF50,stroke:#388E3C
style Orchestrator fill:#2196F3,stroke:#1976D2
style Config fill:#FF9800,stroke:#F57C00
style Monitor fill:#9C27B0,stroke:#7B1FA2
```

**Diagram sources**
- [docker-compose.hive-mind.yml](file://docker/docker-compose.hive-mind.yml)
- [run_real_benchmarks.py](file://benchmark/run_real_benchmarks.py)
- [swarm_performance_suite.py](file://benchmark/scripts/swarm_performance_suite.py)

## Detailed Component Analysis

### API Gateway Analysis
The API gateway serves as the entry point for all external interactions with the Hive-Mind system. It handles authentication, request validation, rate limiting, and routing to appropriate backend services. The gateway exposes RESTful endpoints for swarm management, agent control, and monitoring.

```mermaid
sequenceDiagram
participant Client as "External Client"
participant Gateway as "API Gateway"
participant Auth as "Authentication Service"
participant Swarm as "Swarm Orchestrator"
participant Agent as "Agent Manager"
participant Monitor as "Monitoring Service"
Client->>Gateway : POST /api/v1/swarms
Gateway->>Auth : Validate API Key
Auth-->>Gateway : Authentication Result
Gateway->>Gateway : Validate Request Body
Gateway->>Swarm : Create Swarm Instance
Swarm-->>Gateway : Swarm ID
Gateway->>Client : 201 Created {swarmId}
Client->>Gateway : GET /api/v1/swarms/{id}
Gateway->>Auth : Validate API Key
Auth-->>Gateway : Authentication Result
Gateway->>Swarm : Get Swarm Status
Swarm-->>Gateway : Swarm Status
Gateway->>Client : 200 OK {status}
```

**Diagram sources**
- [api_reference.md](file://benchmark/docs/api_reference.md)
- [CLI_USAGE.md](file://benchmark/CLI_USAGE.md)

#### Authentication and Security
The API implements token-based authentication with API keys for secure access control. Each request must include a valid API key in the Authorization header. The system supports role-based access control with different permission levels for various operations.

```mermaid
flowchart TD
Start([Request Received]) --> ExtractAuth["Extract Authorization Header"]
ExtractAuth --> HasAuth{"Header Present?"}
HasAuth --> |No| Return401["Return 401 Unauthorized"]
HasAuth --> |Yes| ParseKey["Parse API Key"]
ParseKey --> ValidateKey["Validate Key Format"]
ValidateKey --> KeyValid{"Key Valid?"}
KeyValid --> |No| Return403["Return 403 Forbidden"]
KeyValid --> |Yes| CheckPermissions["Check Permissions"]
CheckPermissions --> PermValid{"Sufficient Permissions?"}
PermValid --> |No| Return403
PermValid --> |Yes| ProcessRequest["Process Request"]
ProcessRequest --> Return200["Return 200 OK"]
Return401 --> End([Response Sent])
Return403 --> End
Return200 --> End
```

**Diagram sources**
- [NON_INTERACTIVE_COMMANDS.md](file://benchmark/NON_INTERACTIVE_COMMANDS.md)
- [REAL_EXECUTION.md](file://benchmark/REAL_EXECUTION.md)

### Swarm Orchestration Analysis
The swarm orchestration component manages the lifecycle of agent swarms, including initialization, scaling, and termination. It handles task distribution among agents and monitors their status and performance.

```mermaid
classDiagram
class SwarmOrchestrator {
+string swarmId
+SwarmStatus status
+int agentCount
+CoordinationMode mode
+initialize(config) Swarm
+addAgent(agentConfig) Agent
+removeAgent(agentId) boolean
+distributeTask(task) Assignment
+monitorAgents() StatusReport
+terminate() boolean
}
class AgentManager {
+string agentId
+AgentStatus status
+ResourceMetrics metrics
+executeTask(task) ExecutionResult
+heartbeat() boolean
+updateConfiguration(config) boolean
}
class TaskDistributor {
+DistributionStrategy strategy
+assignTask(task, agents) Assignment
+balanceLoad() LoadDistribution
+handleFailover(failedAgent) RecoveryPlan
}
SwarmOrchestrator --> AgentManager : "manages"
SwarmOrchestrator --> TaskDistributor : "uses"
TaskDistributor --> AgentManager : "assigns to"
```

**Diagram sources**
- [run_real_benchmarks.py](file://benchmark/run_real_benchmarks.py)
- [hive-mind-load-test.py](file://benchmark/scripts/hive-mind-load-test.py)

## Dependency Analysis
The Hive-Mind system has a well-defined dependency structure with clear boundaries between components. The API layer depends on the orchestration and monitoring services, while the orchestration layer depends on the agent management and configuration systems. External dependencies are minimized and managed through the package.json file.

```mermaid
graph LR
API[API Gateway] --> Orchestrator[Swarm Orchestrator]
API --> Config[Configuration Service]
API --> Monitor[Monitoring Service]
Orchestrator --> Agents[Agent Manager]
Orchestrator --> Memory[Distributed Memory]
Config --> Defaults[Default Configurations]
Monitor --> Metrics[Performance Metrics]
Monitor --> Logs[Execution Logs]
Agents --> Memory
Memory --> Persistence[State Storage]
style API fill:#4CAF50,stroke:#388E3C
style Orchestrator fill:#2196F3,stroke:#1976D2
style Config fill:#FF9800,stroke:#F57C00
style Monitor fill:#9C27B0,stroke:#7B1FA2
style Agents fill:#03A9F4,stroke:#0288D1
style Memory fill:#00BCD4,stroke:#0097A7
style Persistence fill:#009688,stroke:#00796B
```

**Diagram sources**
- [package.json](file://package.json)
- [docker-compose.hive-mind.yml](file://docker/docker-compose.hive-mind.yml)
- [non_interactive_defaults.yaml](file://benchmark/config/non_interactive_defaults.yaml)

**Section sources**
- [package.json](file://package.json)
- [docker-compose.hive-mind.yml](file://docker/docker-compose.hive-mind.yml)

## Performance Considerations
The Hive-Mind system implements several performance optimizations to handle high-frequency requests and large-scale swarms. Rate limiting is enforced on all endpoints to prevent abuse, with configurable limits based on client tier. Caching is implemented for frequently accessed resources such as swarm status and agent configurations. The system supports horizontal scaling of agent nodes to handle increased load.

**Section sources**
- [swarm_performance_suite.py](file://benchmark/scripts/swarm_performance_suite.py)
- [hive-mind-load-test.py](file://benchmark/scripts/hive-mind-load-test.py)

## Troubleshooting Guide
Common issues in the Hive-Mind system typically relate to authentication failures, resource exhaustion, or network connectivity problems. Error responses follow a standardized format with clear error codes and descriptive messages to facilitate debugging. The system logs detailed information about request processing and error conditions.

**Section sources**
- [REAL_EXECUTION.md](file://benchmark/REAL_EXECUTION.md)
- [regression-report.md](file://regression-report.md)

## Conclusion
The Hive-Mind API provides a comprehensive interface for orchestrating distributed agent swarms with robust security, performance, and reliability features. The system's modular architecture enables flexible deployment and scaling, while the well-documented API facilitates integration with external systems. The extensive benchmarking and monitoring capabilities ensure optimal performance and reliability in production environments.