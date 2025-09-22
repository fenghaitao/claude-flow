# Swarm Commands

<cite>
**Referenced Files in This Document**   
- [src/swarm/coordinator.ts](file://src/swarm/coordinator.ts)
- [src/mcp/swarm-tools.ts](file://src/mcp/swarm-tools.ts)
- [src/swarm/types.ts](file://src/swarm/types.ts)
- [src/swarm/executor.ts](file://src/swarm/executor.ts)
- [src/swarm/strategies/auto.ts](file://src/swarm/strategies/auto.ts)
- [src/swarm/json-output-aggregator.ts](file://src/swarm/json-output-aggregator.ts)
- [src/coordination/swarm-coordinator.ts](file://src/coordination/swarm-coordinator.ts)
- [src/coordination/swarm-monitor.ts](file://src/coordination/swarm-monitor.ts)
</cite>

## Table of Contents
1. [Swarm Commands](#swarm-commands)
2. [Core Architecture](#core-architecture)
3. [Swarm Lifecycle Management](#swarm-lifecycle-management)
4. [Task Execution and Coordination](#task-execution-and-coordination)
5. [Agent Management and Capabilities](#agent-management-and-capabilities)
6. [Swarm Strategies and Intelligence](#swarm-strategies-and-intelligence)
7. [Monitoring and Metrics](#monitoring-and-metrics)
8. [Result Aggregation and Output](#result-aggregation-and-output)
9. [MCP Integration and Tooling](#mcp-integration-and-tooling)
10. [Error Handling and Resilience](#error-handling-and-resilience)

## Core Architecture

The swarm system is built around a modular architecture that enables distributed agent coordination, intelligent task management, and comprehensive monitoring. At its core, the system implements a hybrid coordination model that combines centralized control with distributed execution capabilities.

The primary architectural components include:

- **SwarmCoordinator**: The central orchestrator that manages swarm lifecycle, agent coordination, and task distribution
- **TaskExecutor**: Responsible for executing individual tasks with resource management and timeout protection
- **SwarmMonitor**: Provides real-time monitoring of agent health, system performance, and alerting
- **AutoStrategy**: Implements intelligent task decomposition and agent selection using ML-inspired heuristics
- **SwarmJsonOutputAggregator**: Collects and formats results for non-interactive execution modes
- **MCP Tools**: Provides integration with the Multi-agent Collaboration Protocol for cross-system interoperability

```mermaid
graph TB
subgraph "Swarm Core"
Coordinator[SwarmCoordinator]
Executor[TaskExecutor]
Monitor[SwarmMonitor]
Strategy[AutoStrategy]
Aggregator[SwarmJsonOutputAggregator]
end
subgraph "Integration Layer"
MCP[MCP Tools]
CLI[Command Line Interface]
API[REST API]
end
subgraph "Agents"
A1[Agent 1]
A2[Agent 2]
A3[Agent 3]
An[Agent N]
end
Coordinator --> Executor
Coordinator --> Monitor
Coordinator --> Strategy
Coordinator --> Aggregator
Coordinator --> A1
Coordinator --> A2
Coordinator --> A3
Coordinator --> An
MCP --> Coordinator
CLI --> Coordinator
API --> Coordinator
Monitor --> A1
Monitor --> A2
Monitor --> A3
Monitor --> An
style Coordinator fill:#4CAF50,stroke:#388E3C
style Executor fill:#2196F3,stroke:#1976D2
style Monitor fill:#FF9800,stroke:#F57C00
style Strategy fill:#9C27B0,stroke:#7B1FA2
style Aggregator fill:#00BCD4,stroke:#0097A7
```

**Diagram sources**
- [src/swarm/coordinator.ts](file://src/swarm/coordinator.ts#L1-L50)
- [src/swarm/executor.ts](file://src/swarm/executor.ts#L1-L50)
- [src/coordination/swarm-monitor.ts](file://src/coordination/swarm-monitor.ts#L1-L50)

**Section sources**
- [src/swarm/coordinator.ts](file://src/swarm/coordinator.ts#L1-L100)
- [src/coordination/swarm-coordinator.ts](file://src/coordination/swarm-coordinator.ts#L1-L100)

## Swarm Lifecycle Management

The swarm lifecycle is managed through a well-defined state machine that ensures proper initialization, execution, and cleanup of swarm operations. The `SwarmCoordinator` class implements the primary lifecycle methods that control the swarm's operational state.

### Initialization Process

The initialization process begins with the `initialize()` method, which performs several critical setup tasks:

1. Validates the swarm configuration
2. Initializes subsystems (monitoring, scheduling, memory management)
3. Starts background processes (heartbeat, monitoring, cleanup)
4. Sets the initial state to "executing"

```mermaid
sequenceDiagram
participant User
participant Coordinator
participant Subsystems
participant Events
User->>Coordinator : initialize()
Coordinator->>Coordinator : Validate configuration
alt Configuration invalid
Coordinator->>User : Throw error
else Configuration valid
Coordinator->>Subsystems : Initialize subsystems
Subsystems-->>Coordinator : Ready
Coordinator->>Coordinator : Start background processes
Coordinator->>Coordinator : Set isRunning = true
Coordinator->>Coordinator : Set startTime
Coordinator->>Coordinator : Emit swarm.started event
Coordinator->>User : Return success
end
```

**Diagram sources**
- [src/swarm/coordinator.ts](file://src/swarm/coordinator.ts#L150-L250)

**Section sources**
- [src/swarm/coordinator.ts](file://src/swarm/coordinator.ts#L150-L300)

### Shutdown and Cleanup

The shutdown process is handled by the `shutdown()` method, which ensures graceful termination of all swarm components:

1. Stops background processes
2. Gracefully terminates all running agents
3. Completes any pending tasks
4. Saves the final swarm state
5. Emits a completion event with metrics

The shutdown process is designed to be resilient, with proper error handling to ensure that critical cleanup operations are completed even if individual components fail.

```typescript
async shutdown(): Promise<void> {
  if (!this._isRunning) {
    return;
  }

  this.logger.info('Shutting down swarm coordinator...');
  this.status = 'paused';

  try {
    // Stop background processes
    this.stopBackgroundProcesses();

    // Gracefully stop all agents
    await this.stopAllAgents();

    // Complete any running tasks
    await this.completeRunningTasks();

    // Save final state
    await this.saveState();

    this._isRunning = false;
    this.endTime = new Date();
    this.status = 'completed';
  } catch (error) {
    this.logger.error('Error during swarm coordinator shutdown', { error });
    throw error;
  }
}
```

**Section sources**
- [src/swarm/coordinator.ts](file://src/swarm/coordinator.ts#L250-L300)

## Task Execution and Coordination

The task execution system is designed to handle complex workflows with intelligent resource management, timeout protection, and comprehensive monitoring.

### Task Executor Architecture

The `TaskExecutor` class is responsible for executing individual tasks with robust error handling and resource management. It implements several key features:

- **Timeout Protection**: Tasks are executed with configurable timeout limits
- **Resource Monitoring**: Tracks CPU, memory, disk, and network usage
- **Process Management**: Manages child processes and handles termination
- **Retry Mechanisms**: Supports configurable retry attempts for failed tasks
- **Sandboxing**: Optional sandboxed execution for security

```mermaid
classDiagram
class TaskExecutor {
+logger : Logger
+config : ExecutionConfig
+activeExecutions : Map~string, ExecutionSession~
+resourceMonitor : ResourceMonitor
+processPool : ProcessPool
+initialize() : Promise~void~
+shutdown() : Promise~void~
+executeTask(task, agent, options) : Promise~ExecutionResult~
+stopExecution(sessionId, reason) : Promise~void~
+executeClaudeTask(task, agent, options) : Promise~ExecutionResult~
}
class ExecutionSession {
+id : string
+task : TaskDefinition
+agent : AgentState
+context : ExecutionContext
+config : ExecutionConfig
+logger : Logger
+startTime : Date
+process : ChildProcess | null
+result : ExecutionResult | null
+start() : Promise~ExecutionResult~
+stop(reason) : Promise~void~
+monitorResources() : void
}
class ExecutionConfig {
+timeoutMs : number
+retryAttempts : number
+killTimeout : number
+resourceLimits : ExecutionResources
+sandboxed : boolean
+logLevel : string
+captureOutput : boolean
+streamOutput : boolean
+enableMetrics : boolean
}
class ExecutionResult {
+success : boolean
+output : string
+error? : string
+exitCode : number
+duration : number
+resourcesUsed : ResourceUsage
+artifacts : Record~string, any~
+metadata : Record~string, any~
}
TaskExecutor --> ExecutionSession : "creates"
TaskExecutor --> ResourceMonitor : "uses"
TaskExecutor --> ProcessPool : "uses"
ExecutionSession --> ChildProcess : "spawns"
```

**Diagram sources**
- [src/swarm/executor.ts](file://src/swarm/executor.ts#L1-L100)

**Section sources**
- [src/swarm/executor.ts](file://src/swarm/executor.ts#L1-L300)

### Execution Workflow

The task execution workflow follows a structured process to ensure reliability and proper resource management:

```mermaid
flowchart TD
Start([Execute Task]) --> CreateSession["Create Execution Session"]
CreateSession --> SetupMonitoring["Setup Resource Monitoring"]
SetupMonitoring --> ExecuteWithTimeout["Execute with Timeout Protection"]
ExecuteWithTimeout --> CheckResult{"Execution Successful?"}
CheckResult --> |Yes| Cleanup["Cleanup Execution"]
CheckResult --> |No| HandleError["Handle Error"]
HandleError --> Cleanup
Cleanup --> EmitEvent["Emit Task Completion Event"]
EmitEvent --> End([Return Result])
style Start fill:#4CAF50,stroke:#388E3C
style End fill:#4CAF50,stroke:#388E3C
style CheckResult fill:#FFEB3B,stroke:#FBC02D
```

**Section sources**
- [src/swarm/executor.ts](file://src/swarm/executor.ts#L300-L500)

## Agent Management and Capabilities

The swarm system supports a diverse set of agent types, each with specialized capabilities and roles within the coordination framework.

### Agent Types and Roles

The system defines multiple agent types through the `AgentType` union type, including:

- **Coordinator**: Orchestrates and manages other agents
- **Researcher**: Performs research and data gathering
- **Coder**: Writes and maintains code
- **Analyst**: Analyzes data and generates insights
- **Architect**: Designs system architecture and solutions
- **Tester**: Tests and validates functionality
- **Reviewer**: Reviews and validates work
- **Optimizer**: Optimizes performance and efficiency
- **Documenter**: Creates and maintains documentation
- **Monitor**: Monitors system health and performance
- **Specialist**: Domain-specific specialized agent

Each agent type has specific capabilities that determine its suitability for different task types.

### Agent State Management

The `AgentState` interface defines the comprehensive state model for agents, including:

- **Identification**: Unique ID, name, and type
- **Status**: Current operational state (idle, busy, error, etc.)
- **Capabilities**: Detailed capability matrix
- **Metrics**: Performance and resource usage metrics
- **Configuration**: Behavioral and resource limits
- **Environment**: Runtime environment and tool access
- **Relationships**: Parent, child, and collaborator agents

```typescript
interface AgentState {
  id: AgentId;
  name: string;
  type: AgentType;
  status: AgentStatus;
  capabilities: AgentCapabilities;
  metrics: AgentMetrics;
  currentTask?: TaskId;
  workload: number;
  health: number;
  config: AgentConfig;
  environment: AgentEnvironment;
  endpoints: string[];
  lastHeartbeat: Date;
  taskHistory: TaskId[];
  errorHistory: AgentError[];
  parentAgent?: AgentId;
  childAgents: AgentId[];
  collaborators: AgentId[];
}
```

**Section sources**
- [src/swarm/types.ts](file://src/swarm/types.ts#L50-L200)

## Swarm Strategies and Intelligence

The swarm system implements intelligent coordination strategies, with the `AutoStrategy` class providing advanced task decomposition and agent selection capabilities.

### Auto Strategy Implementation

The `AutoStrategy` class extends the `BaseStrategy` and implements ML-inspired heuristics for intelligent swarm coordination:

```mermaid
classDiagram
class AutoStrategy {
+mlHeuristics : MLHeuristics
+decompositionCache : Map~string, DecompositionResult~
+patternCache : Map~string, TaskPattern[]~
+performanceHistory : Map~string, number[]~
+decomposeObjective(objective) : Promise~DecompositionResult~
+selectAgentForTask(task, agents) : Promise~string | null~
+optimizeTaskSchedule(tasks, agents) : Promise~AgentAllocation[]~
+detectPatternsAsync(description) : Promise~TaskPattern[]~
+analyzeTaskTypesAsync(description) : Promise~string[]~
+estimateComplexityAsync(description) : Promise~number~
+generateTasksWithBatching(objective, patterns, types, complexity) : Promise~TaskDefinition[]~
}
class BaseStrategy {
+config : any
+metrics : StrategyMetrics
+decomposeObjective(objective) : Promise~DecompositionResult~
+selectAgentForTask(task, agents) : Promise~string | null~
+optimizeTaskSchedule(tasks, agents) : Promise~AgentAllocation[]~
}
AutoStrategy --|> BaseStrategy
```

**Diagram sources**
- [src/swarm/strategies/auto.ts](file://src/swarm/strategies/auto.ts#L1-L50)

**Section sources**
- [src/swarm/strategies/auto.ts](file://src/swarm/strategies/auto.ts#L1-L300)

### Intelligent Task Decomposition

The auto strategy implements sophisticated task decomposition using multiple parallel analysis techniques:

1. **Pattern Detection**: Identifies common task patterns in the objective description
2. **Task Type Analysis**: Classifies the types of tasks required
3. **Complexity Estimation**: Estimates the overall complexity of the objective
4. **Batch Generation**: Creates optimized task batches based on dependencies

The decomposition process is cached to improve performance for recurring objectives.

```typescript
async decomposeObjective(objective: SwarmObjective): Promise<DecompositionResult> {
  const startTime = Date.now();
  const cacheKey = this.getCacheKey(objective);

  // Check cache first
  if (this.decompositionCache.has(cacheKey)) {
    this.metrics.cacheHitRate = (this.metrics.cacheHitRate + 1) / 2;
    return this.decompositionCache.get(cacheKey)!;
  }

  // Parallel pattern detection and task type analysis
  const [detectedPatterns, taskTypes, complexity] = await Promise.all([
    this.detectPatternsAsync(objective.description),
    this.analyzeTaskTypesAsync(objective.description),
    this.estimateComplexityAsync(objective.description),
  ]);

  // Generate tasks based on detected patterns and strategy
  const tasks = await this.generateTasksWithBatching(
    objective,
    detectedPatterns,
    taskTypes,
    complexity,
  );

  // Analyze dependencies and create batches
  const dependencies = this.analyzeDependencies(tasks);
  const batchGroups = this.createTaskBatches(tasks, dependencies);

  // Estimate total duration with parallel processing consideration
  const estimatedDuration = this.calculateOptimizedDuration(batchGroups);

  const result: DecompositionResult = {
    tasks,
    dependencies,
    estimatedDuration,
    recommendedStrategy: this.selectOptimalStrategy(objective, complexity),
    complexity,
    batchGroups,
    timestamp: new Date(),
    ttl: 1800000,
    accessCount: 0,
    lastAccessed: new Date(),
    data: { objectiveId: objective.id, strategy: 'auto' },
  };

  // Cache the result
  this.decompositionCache.set(cacheKey, result);
  this.updateMetrics(result, Date.now() - startTime);

  return result;
}
```

**Section sources**
- [src/swarm/strategies/auto.ts](file://src/swarm/strategies/auto.ts#L150-L300)

## Monitoring and Metrics

The swarm system includes comprehensive monitoring capabilities through the `SwarmMonitor` class, which tracks both agent-level and system-level metrics.

### Monitoring Architecture

The monitoring system collects and analyzes multiple dimensions of performance data:

- **Agent Metrics**: Individual agent performance, resource usage, and task success rates
- **System Metrics**: Overall system CPU, memory, load, and throughput
- **Alerting**: Real-time alerts for critical conditions (high resource usage, stalled agents, etc.)
- **History**: Long-term metric storage for trend analysis

```mermaid
classDiagram
class SwarmMonitor {
+logger : Logger
+config : MonitoringConfig
+agentMetrics : Map~string, AgentMetrics~
+systemMetrics : SystemMetrics[]
+alerts : Alert[]
+monitoringInterval : NodeJS.Timeout
+startTime : number
+taskStartTimes : Map~string, number~
+taskCompletionTimes : number[]
+lastThroughputCheck : number
+tasksInLastMinute : number
+start() : Promise~void~
+stop() : void
+collectMetrics() : Promise~void~
+registerAgent(agentId, name) : void
+unregisterAgent(agentId) : void
+taskStarted(agentId, taskId, description) : void
+taskCompleted(agentId, taskId, outputSize) : void
+taskFailed(agentId, taskId, error) : void
+checkAlerts() : void
+generateSystemMetrics() : SystemMetrics
}
class AgentMetrics {
+id : string
+name : string
+status : string
+currentTask? : string
+startTime? : number
+endTime? : number
+duration? : number
+cpuUsage? : number
+memoryUsage? : number
+taskCount : number
+successCount : number
+failureCount : number
+averageTaskDuration : number
+lastActivity : number
+outputSize? : number
+errorRate : number
}
class SystemMetrics {
+timestamp : number
+cpuUsage : number
+memoryUsage : number
+totalMemory : number
+freeMemory : number
+loadAverage : number[]
+activeAgents : number
+totalTasks : number
+completedTasks : number
+failedTasks : number
+pendingTasks : number
+averageTaskDuration : number
+throughput : number
}
class Alert {
+id : string
+timestamp : number
+level : string
+type : string
+message : string
+details? : any
}
SwarmMonitor --> AgentMetrics : "tracks"
SwarmMonitor --> SystemMetrics : "generates"
SwarmMonitor --> Alert : "emits"
```

**Diagram sources**
- [src/coordination/swarm-monitor.ts](file://src/coordination/swarm-monitor.ts#L1-L50)

**Section sources**
- [src/coordination/swarm-monitor.ts](file://src/coordination/swarm-monitor.ts#L1-L300)

### Metric Collection Workflow

The monitoring system follows a periodic collection pattern to ensure real-time visibility into swarm operations:

```mermaid
flowchart TD
Start([Start Monitoring]) --> CreateDir["Create History Directory"]
CreateDir --> StartInterval["Start Monitoring Interval"]
StartInterval --> CollectMetrics["Collect Metrics"]
CollectMetrics --> CheckAgents["Check Agent Health"]
CheckAgents --> DetectStalls["Detect Stalled Agents"]
DetectStalls --> CheckResources["Check System Resources"]
CheckResources --> GenerateAlerts["Generate Alerts if Needed"]
GenerateAlerts --> StoreMetrics["Store Metrics in History"]
StoreMetrics --> EmitEvents["Emit Monitoring Events"]
EmitEvents --> Wait["Wait for Next Interval"]
Wait --> CollectMetrics
style Start fill:#4CAF50,stroke:#388E3C
style CollectMetrics fill:#2196F3,stroke:#1976D2
```

**Section sources**
- [src/coordination/swarm-monitor.ts](file://src/coordination/swarm-monitor.ts#L150-L300)

## Result Aggregation and Output

The `SwarmJsonOutputAggregator` class provides comprehensive result aggregation for non-interactive swarm execution, collecting data from all agents and tasks into a structured JSON format.

### Output Aggregation Model

The aggregator collects and structures data across multiple dimensions:

- **Swarm Summary**: Overall swarm status, duration, and success rate
- **Agent Data**: Individual agent performance and outputs
- **Task Data**: Detailed task execution results and artifacts
- **Results**: Consolidated outputs, errors, and insights
- **Metrics**: Performance metrics and resource usage
- **Metadata**: Configuration and execution context

```mermaid
classDiagram
class SwarmJsonOutputAggregator {
+logger : Logger
+swarmId : string
+objective : string
+startTime : Date
+endTime? : Date
+configuration : Record~string, any~
+agents : Map~string, AgentOutputData~
+tasks : Map~string, TaskOutputData~
+outputs : string[]
+errors : string[]
+insights : string[]
+artifacts : Record~string, any~
+metrics : SwarmMetrics
+addAgent(agent) : void
+updateAgent(agentId, updates) : void
+addAgentOutput(agentId, output) : void
+addAgentError(agentId, error) : void
+addTask(task) : void
+updateTask(taskId, updates) : void
+addTaskResult(taskId, result) : void
+addArtifact(name, data) : void
+addInsight(insight) : void
+finalize() : SwarmOutputAggregate
+saveToFile(filePath) : Promise~void~
}
class SwarmOutputAggregate {
+swarmId : string
+objective : string
+startTime : string
+endTime : string
+duration : number
+status : string
+summary : SummaryData
+agents : AgentOutputData[]
+tasks : TaskOutputData[]
+results : ResultData
+metrics : SwarmMetrics
+metadata : Metadata
}
class AgentOutputData {
+agentId : string
+name : string
+type : string
+status : string
+startTime : string
+endTime? : string
+duration? : number
+tasksCompleted : number
+outputs : string[]
+errors : string[]
+metrics : AgentMetricsData
}
class TaskOutputData {
+taskId : string
+name : string
+type : string
+status : string
+assignedAgent? : string
+startTime : string
+endTime? : string
+duration? : number
+priority : string
+output? : string
+result? : TaskResult
+artifacts? : Record~string, any~
+error? : string
}
SwarmJsonOutputAggregator --> SwarmOutputAggregate : "produces"
SwarmJsonOutputAggregator --> AgentOutputData : "collects"
SwarmJsonOutputAggregator --> TaskOutputData : "collects"
```

**Diagram sources**
- [src/swarm/json-output-aggregator.ts](file://src/swarm/json-output-aggregator.ts#L1-L50)

**Section sources**
- [src/swarm/json-output-aggregator.ts](file://src/swarm/json-output-aggregator.ts#L1-L300)

## MCP Integration and Tooling

The swarm system integrates with the Multi-agent Collaboration Protocol (MCP) through a set of specialized tools that enable cross-system interoperability and agent coordination.

### MCP Tool Implementation

The `createSwarmTools` function returns an array of MCP tools that expose swarm functionality to external systems:

```typescript
function createSwarmTools(logger: ILogger): MCPTool[] {
  return [
    {
      name: 'dispatch_agent',
      description: 'Spawn a new agent in the swarm to handle a specific task',
      inputSchema: { /* schema definition */ },
      handler: async (input: any, context?: SwarmToolContext) => {
        // Implementation details
      },
    },
    {
      name: 'swarm_status',
      description: 'Get the current status of the swarm and all agents',
      inputSchema: { /* schema definition */ },
      handler: async (input: any, context?: SwarmToolContext) => {
        // Implementation details
      },
    },
    {
      name: 'swarm/create-objective',
      description: 'Create a new swarm objective with tasks and coordination',
      inputSchema: { /* schema definition */ },
      handler: async (input: any, context?: SwarmToolContext) => {
        // Implementation details
      },
    },
    {
      name: 'swarm/execute-objective',
      description: 'Execute a swarm objective',
      inputSchema: { /* schema definition */ },
      handler: async (input: any, context?: SwarmToolContext) => {
        // Implementation details
      },
    },
  ];
}
```

### Tool Categories

The MCP tools are organized into two main categories:

1. **Legacy Swarm Tools**: Basic agent management and status reporting
2. **Swarm Coordination Tools**: Advanced objective creation and execution

These tools enable external systems to interact with the swarm, creating objectives, monitoring progress, and retrieving results through a standardized protocol.

**Section sources**
- [src/mcp/swarm-tools.ts](file://src/mcp/swarm-tools.ts#L1-L300)

## Error Handling and Resilience

The swarm system implements comprehensive error handling and resilience mechanisms to ensure reliable operation in the face of failures and unexpected conditions.

### Failure Modes and Recovery

The system handles several key failure scenarios:

- **Agent Failures**: Failed agents are detected through heartbeat monitoring and their tasks are reassigned
- **Task Failures**: Failed tasks are retried according to configurable retry policies
- **Network Partitions**: The system continues operation with available agents and resumes coordination when connectivity is restored
- **Resource Exhaustion**: Resource monitoring detects high usage and triggers alerts or task throttling

### Circuit Breaker Pattern

The system implements a circuit breaker pattern to prevent cascading failures:

```mermaid
stateDiagram-v2
[*] --> Closed
Closed --> Open : "Failure threshold exceeded"
Open --> HalfOpen : "Timeout expired"
HalfOpen --> Closed : "Test call succeeds"
HalfOpen --> Open : "Test call fails"
```

When the failure rate exceeds a threshold, the circuit breaker opens, temporarily halting new task assignments to allow the system to recover. After a timeout period, it enters a half-open state to test recovery before fully closing.

**Section sources**
- [src/coordination/swarm-coordinator.ts](file://src/coordination/swarm-coordinator.ts#L500-L600)
- [src/coordination/swarm-monitor.ts](file://src/coordination/swarm-monitor.ts#L400-L450)