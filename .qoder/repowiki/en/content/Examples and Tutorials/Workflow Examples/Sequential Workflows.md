# Sequential Workflows

<cite>
**Referenced Files in This Document**   
- [workflow.ts](file://src/cli/commands/workflow.ts#L67-L76)
- [types.ts](file://src/swarm/types.ts#L352-L391)
- [claude-code-interface.ts](file://src/swarm/claude-code-interface.ts#L115-L1265)
- [examples/02-workflows/sequential](file://examples/02-workflows/sequential)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Workflow Definition Structure](#workflow-definition-structure)
3. [Task Definition and Execution](#task-definition-and-execution)
4. [Sequential Execution Flow](#sequential-execution-flow)
5. [Dependency Management](#dependency-management)
6. [Error Handling and Failure Strategies](#error-handling-and-failure-strategies)
7. [State Propagation Between Tasks](#state-propagation-between-tasks)
8. [Performance Considerations](#performance-considerations)
9. [Common Issues and Solutions](#common-issues-and-solutions)

## Introduction
Sequential Workflows in Claude-Flow enable ordered execution of tasks where each step depends on the successful completion of the previous one. This pattern ensures predictable execution flow, making it ideal for processes requiring strict ordering such as content publishing pipelines, data processing chains, or multi-step validation workflows. The system orchestrates task scheduling, agent assignment, and state management to maintain consistency across sequential operations.

## Workflow Definition Structure

The structure of a workflow is defined by the `WorkflowDefinition` interface, which specifies the core components including tasks, dependencies, variables, and settings.

```mermaid
classDiagram
class WorkflowDefinition {
+string name
+string? version
+string? description
+Record<string, any>? variables
+AgentDefinition[]? agents
+TaskDefinition[] tasks
+Record<string, string[]>? dependencies
+WorkflowSettings? settings
}
```

**Diagram sources**  
- [workflow.ts](file://src/cli/commands/workflow.ts#L67-L76)

**Section sources**  
- [workflow.ts](file://src/cli/commands/workflow.ts#L67-L76)

## Task Definition and Execution

Each task within a sequential workflow is defined using the `TaskDefinition` interface, which includes execution parameters, constraints, input/output specifications, and tracking metadata.

```mermaid
classDiagram
class TaskDefinition {
+TaskId id
+TaskType type
+string name
+string description
+TaskRequirements requirements
+TaskConstraints constraints
+TaskPriority priority
+any input
+any? expectedOutput
+string instructions
+Record<string, any> context
+Record<string, any>? parameters
+any[]? examples
+TaskStatus status
+Date createdAt
+Date updatedAt
+AgentId? assignedTo
+Date? assignedAt
+Date? startedAt
+Date? completedAt
+TaskResult? result
+TaskError? error
+TaskAttempt[] attempts
+TaskStatusChange[] statusHistory
}
```

**Diagram sources**  
- [types.ts](file://src/swarm/types.ts#L352-L391)

**Section sources**  
- [types.ts](file://src/swarm/types.ts#L352-L391)

## Sequential Execution Flow

The sequential execution process follows a strict order where tasks are executed one after another based on dependency relationships. The orchestrator manages this flow through the `ClaudeCodeInterface`, which handles agent selection, task execution, and status updates.

```mermaid
sequenceDiagram
participant Orchestrator as "Workflow Orchestrator"
participant Scheduler as "Task Scheduler"
participant Agent as "Claude Agent"
participant Memory as "Memory Manager"
Orchestrator->>Scheduler : Start workflow execution
Scheduler->>Scheduler : Identify first task in sequence
Scheduler->>Orchestrator : Request agent for task
Orchestrator->>Orchestrator : Select optimal agent
Orchestrator->>Agent : Spawn agent with configuration
Agent-->>Orchestrator : Agent ready
Orchestrator->>Agent : Execute task with context
Agent->>Memory : Read/write task-specific state
Agent-->>Orchestrator : Return execution result
Orchestrator->>Scheduler : Update task status
alt Task successful
Scheduler->>Scheduler : Proceed to next dependent task
Scheduler->>Orchestrator : Request agent for next task
else Task failed
Scheduler->>Orchestrator : Apply failure strategy
Orchestrator->>Scheduler : Retry or abort workflow
end
Scheduler->>Orchestrator : Notify workflow completion
```

**Diagram sources**  
- [claude-code-interface.ts](file://src/swarm/claude-code-interface.ts#L115-L1265)

**Section sources**  
- [claude-code-interface.ts](file://src/swarm/claude-code-interface.ts#L115-L1265)

## Dependency Management

Dependencies between tasks are managed through the `dependencies` field in the workflow definition, which maps task IDs to arrays of prerequisite task IDs. This enables the orchestrator to determine execution order and block subsequent tasks until all dependencies are satisfied.

```mermaid
flowchart TD
A["Task A: Research Topic"] --> B["Task B: Draft Article"]
B --> C["Task C: Technical Review"]
C --> D["Task D: Editorial Review"]
D --> E["Task E: Publish Content"]
style A fill:#4CAF50,stroke:#388E3C
style B fill:#2196F3,stroke:#1976D2
style C fill:#FF9800,stroke:#F57C00
style D fill:#9C27B0,stroke:#7B1FA2
style E fill:#F44336,stroke:#D32F2F
```

**Diagram sources**  
- [workflow.ts](file://src/cli/commands/workflow.ts#L67-L76)

**Section sources**  
- [workflow.ts](file://src/cli/commands/workflow.ts#L67-L76)

## Error Handling and Failure Strategies

The system implements robust error handling mechanisms for sequential workflows, including retry logic, failure propagation, and configurable recovery strategies. When a task fails, the orchestrator can either retry the task or terminate the entire workflow based on configuration.

```mermaid
flowchart LR
Start([Task Execution]) --> Execute["Execute Task"]
Execute --> Success{"Success?"}
Success --> |Yes| Complete["Mark as Complete"]
Success --> |No| Retry{"Retries Remaining?"}
Retry --> |Yes| Increment["Increment Retry Count"]
Increment --> Execute
Retry --> |No| Fail["Mark as Failed"]
Fail --> Strategy{"Failure Strategy?"}
Strategy --> |Continue| Next["Proceed to Next Task"]
Strategy --> |Abort| Terminate["Terminate Workflow"]
Strategy --> |Skip| Next
Complete --> Next["Next Task in Sequence"]
Next --> End([Workflow Complete])
```

**Section sources**  
- [claude-code-interface.ts](file://src/swarm/claude-code-interface.ts#L115-L1265)

## State Propagation Between Tasks

State is propagated between sequential tasks through shared memory and context objects. Each completed task can store results in the memory manager, which subsequent tasks can access as input for their operations.

```mermaid
flowchart LR
Task1["Task 1: Generate Outline"] --> Store1["Store in Memory"]
Store1 --> Task2["Task 2: Write Section 1"]
Task2 --> Store2["Store Content in Memory"]
Store2 --> Task3["Task 3: Write Section 2"]
Task3 --> Store3["Store Content in Memory"]
Store3 --> Task4["Task 4: Compile Final Document"]
Task4 --> Output["Save Final Output"]
subgraph "Shared Memory"
MemoryStore["Key-Value Store"]
end
Store1 --> MemoryStore
Store2 --> MemoryStore
Store3 --> MemoryStore
Task2 -.-> MemoryStore
Task3 -.-> MemoryStore
Task4 -.-> MemoryStore
```

**Section sources**  
- [claude-code-interface.ts](file://src/swarm/claude-code-interface.ts#L115-L1265)

## Performance Considerations

Sequential workflows may introduce performance bottlenecks due to their linear nature. Key optimization strategies include agent pre-warming, efficient state management, and minimizing I/O operations between tasks.

```mermaid
graph LR
A["Performance Factors"] --> B["Agent Initialization Time"]
A --> C["State Serialization Overhead"]
A --> D["Task Switching Latency"]
A --> E["Memory Access Patterns"]
B --> F["Solution: Pre-warm Agent Pool"]
C --> G["Solution: Optimize Serialization"]
D --> H["Solution: Reduce Context Switching"]
E --> I["Solution: Cache Frequently Accessed Data"]
```

**Section sources**  
- [claude-code-interface.ts](file://src/swarm/claude-code-interface.ts#L115-L1265)

## Common Issues and Solutions

Common challenges in sequential workflows include blocking operations, state corruption, and partial failure recovery. The system addresses these through timeout mechanisms, state validation, and checkpointing.

```mermaid
flowchart TB
Issue1["Blocking Operations"] --> Solution1["Implement Timeouts"]
Issue2["State Corruption"] --> Solution2["Validate State Before Use"]
Issue3["Partial Failures"] --> Solution3["Support Checkpointing"]
Issue4["Resource Leaks"] --> Solution4["Ensure Proper Cleanup"]
Issue5["Deadlocks"] --> Solution5["Detect and Recover from Stalls"]
Solution1 --> Mechanism1["Task-level Timeouts"]
Solution2 --> Mechanism2["State Validation Hooks"]
Solution3 --> Mechanism3["Periodic Checkpoints"]
Solution4 --> Mechanism4["Guaranteed Cleanup Handlers"]
Solution5 --> Mechanism5["Health Monitoring System"]
```

**Section sources**  
- [claude-code-interface.ts](file://src/swarm/claude-code-interface.ts#L115-L1265)