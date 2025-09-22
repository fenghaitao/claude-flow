# Queen-Led Coordination

<cite>
**Referenced Files in This Document**   
- [Queen.ts](file://src/hive-mind/core/Queen.ts#L28-L773)
- [hive-agents.ts](file://src/cli/agents/hive-agents.ts#L628-L699)
- [daa-tools.js](file://src/mcp/implementations/daa-tools.js#L171-L219)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Queen Class Implementation](#queen-class-implementation)
3. [Strategic Planning and Decision Making](#strategic-planning-and-decision-making)
4. [Agent Coordination and Task Management](#agent-coordination-and-task-management)
5. [Queen-to-Agent Communication Model](#queen-to-agent-communication-model)
6. [Performance Monitoring and Optimization](#performance-monitoring-and-optimization)
7. [Queen Failure Scenarios and Solutions](#queen-failure-scenarios-and-solutions)
8. [Conclusion](#conclusion)

## Introduction
The Queen class serves as the central decision-making component in the swarm system, orchestrating the activities of worker agents and ensuring efficient task execution. This document provides a comprehensive analysis of the Queen's implementation, responsibilities, and interactions within the swarm architecture. The Queen is responsible for strategic planning, agent coordination, performance monitoring, and system governance, making it the pivotal element in maintaining swarm efficiency and effectiveness.

**Section sources**
- [Queen.ts](file://src/hive-mind/core/Queen.ts#L28-L773)

## Queen Class Implementation
The Queen class is implemented as an EventEmitter that extends the core coordination capabilities of the swarm system. It maintains several key data structures including a Map of agents, a task queue, and coordination strategies. The class is initialized with a configuration object that specifies the swarm ID, operational mode, and topology.

```mermaid
classDiagram
class Queen {
-id : string
-config : QueenConfig
-agents : Map<string, Agent>
-taskQueue : Map<string, Task>
-strategies : Map<string, CoordinationStrategy>
-db : DatabaseManager
-mcpWrapper : MCPToolWrapper
-isActive : boolean
+initialize() : Promise<void>
+registerAgent(agent : Agent) : Promise<void>
+onTaskSubmitted(task : Task) : Promise<QueenDecision>
+shutdown() : Promise<void>
-makeStrategicDecision(task : Task, analysis : any) : Promise<QueenDecision>
-selectOptimalStrategy(task : Task, analysis : any, neuralAnalysis : any) : CoordinationStrategy
-selectAgentsForTask(task : Task, strategy : CoordinationStrategy) : Promise<Agent[]>
-startCoordinationLoop() : void
-startOptimizationLoop() : void
}
class Agent {
+id : string
+type : AgentType
+capabilities : string[]
+status : string
+assignTask(taskId : string, executionPlan : any) : Promise<void>
+isResponsive() : boolean
}
class Task {
+id : string
+description : string
+priority : string
+requiredCapabilities : string[]
+maxAgents : number
+requireConsensus : boolean
}
class CoordinationStrategy {
+name : string
+description : string
+phases : string[]
+maxAgents : number
+coordinationPoints : string[]
+suitable_for : string[]
}
class QueenDecision {
+id : string
+taskId : string
+strategy : CoordinationStrategy
+selectedAgents : string[]
+executionPlan : any
+confidence : number
+rationale : string
+timestamp : Date
}
Queen --> Agent : "manages"
Queen --> Task : "processes"
Queen --> CoordinationStrategy : "uses"
Queen --> QueenDecision : "creates"
Queen --> DatabaseManager : "interacts with"
Queen --> MCPToolWrapper : "utilizes"
```

**Diagram sources**
- [Queen.ts](file://src/hive-mind/core/Queen.ts#L28-L773)

**Section sources**
- [Queen.ts](file://src/hive-mind/core/Queen.ts#L28-L773)

## Strategic Planning and Decision Making
The Queen's strategic planning capabilities are centered around the `makeStrategicDecision` method, which analyzes tasks and determines optimal execution strategies. When a task is submitted, the Queen first analyzes its requirements using MCP (Multi-agent Coordination Protocol) tools, then selects the most appropriate coordination strategy based on task complexity, priority, and system topology.

The decision-making process involves several key steps:
1. Task analysis to determine complexity and required capabilities
2. Strategy selection based on multiple factors including topology and priority
3. Agent selection by scoring available agents on capability match, type suitability, workload, and historical performance
4. Execution plan creation with defined phases, agent roles, and checkpoints

```mermaid
flowchart TD
Start([Task Submitted]) --> AnalyzeTask["Analyze Task Requirements"]
AnalyzeTask --> SelectStrategy["Select Optimal Strategy"]
SelectStrategy --> ScoreAgents["Score Available Agents"]
ScoreAgents --> SelectAgents["Select Top Agents"]
SelectAgents --> CreatePlan["Create Execution Plan"]
CreatePlan --> ApplyDecision["Apply Decision"]
ApplyDecision --> NotifyAgents["Notify Selected Agents"]
NotifyAgents --> StoreDecision["Store Decision for Learning"]
StoreDecision --> End([Decision Complete])
subgraph "Strategy Selection Logic"
SelectStrategy --> TopologyCheck{"Topology = hierarchical?"}
TopologyCheck --> |Yes| UseHierarchical["Use Hierarchical Cascade"]
TopologyCheck --> |No| ConsensusCheck{"Consensus Required?"}
ConsensusCheck --> |Yes| UseMesh["Use Mesh Consensus"]
ConsensusCheck --> |No| PriorityCheck{"Priority = critical?"}
PriorityCheck --> |Yes| UseFastTrack["Use Priority Fast Track"]
PriorityCheck --> |No| UseAdaptive["Use Adaptive Default"]
end
```

**Diagram sources**
- [Queen.ts](file://src/hive-mind/core/Queen.ts#L28-L773)

**Section sources**
- [Queen.ts](file://src/hive-mind/core/Queen.ts#L28-L773)

## Agent Coordination and Task Management
The Queen coordinates worker agents through a systematic process of task assignment, progress tracking, and result aggregation. When agents are created, they are automatically registered with the Queen, who maintains a registry of all active agents and their capabilities.

The task management workflow follows this sequence:
1. Task submission to the Queen
2. Strategic decision making and agent selection
3. Task assignment to selected agents
4. Continuous monitoring of task progress
5. Result collection and aggregation

```mermaid
sequenceDiagram
participant Queen as "Queen"
participant Agent1 as "Worker Agent 1"
participant Agent2 as "Worker Agent 2"
participant Agent3 as "Worker Agent 3"
participant DB as "Database"
Queen->>DB : Create Agent Records
loop Agent Registration
DB-->>Queen : Agent Registration Confirmation
end
User->>Queen : Submit Task
Queen->>Queen : Analyze Task Requirements
Queen->>Queen : Select Optimal Strategy
Queen->>Queen : Score and Select Agents
Queen->>Queen : Create Execution Plan
Queen->>Agent1 : Assign Task (Execution Plan)
Queen->>Agent2 : Assign Task (Execution Plan)
Queen->>Agent3 : Assign Task (Execution Plan)
loop Periodic Monitoring
Queen->>Queen : Check Task Progress
alt Task Stalled
Queen->>Queen : Handle Stalled Task
end
Queen->>Queen : Monitor Agent Health
alt Agent Failed
Queen->>Queen : Reassign Tasks
end
end
Agent1->>Queen : Report Task Completion
Agent2->>Queen : Report Task Completion
Agent3->>Queen : Report Task Completion
Queen->>Queen : Aggregate Results
Queen->>User : Return Aggregated Results
```

**Diagram sources**
- [Queen.ts](file://src/hive-mind/core/Queen.ts#L28-L773)
- [hive-agents.ts](file://src/cli/agents/hive-agents.ts#L628-L699)

**Section sources**
- [Queen.ts](file://src/hive-mind/core/Queen.ts#L28-L773)

## Queen-to-Agent Communication Model
The Queen communicates with worker agents through a structured message-passing system that ensures reliable coordination and information exchange. The communication model includes both direct agent assignment and broadcast mechanisms for system-wide notifications.

The message format includes the following key components:
- **from**: The sender's agent ID
- **to**: The recipient's agent ID (or null for broadcast)
- **message_type**: The type of communication (task_assignment, status_update, etc.)
- **content**: The message payload, typically containing task details or instructions
- **priority**: The message priority level
- **timestamp**: When the message was created

When the Queen assigns a task, it creates an execution plan that includes:
- Phases of execution
- Agent assignments with specific roles and responsibilities
- Coordination points for synchronization
- Checkpoints for progress verification
- A fallback plan for handling failures

```mermaid
flowchart LR
A[Queen] --> |Task Assignment| B[Worker Agents]
A --> |Status Requests| B
A --> |Reassignment| B
B --> |Progress Updates| A
B --> |Completion Reports| A
B --> |Error Notifications| A
subgraph "Message Structure"
C["Message Object"]
C --> D["from: string"]
C --> E["to: string"]
C --> F["message_type: string"]
C --> G["content: any"]
C --> H["priority: string"]
C --> I["timestamp: Date"]
end
subgraph "Execution Plan"
J["Execution Plan"]
J --> K["phases: string[]"]
J --> L["agentAssignments: AgentAssignment[]"]
J --> M["coordinationPoints: string[]"]
J --> N["checkpoints: Checkpoint[]"]
J --> O["fallbackPlan: FallbackPlan"]
end
```

**Diagram sources**
- [Queen.ts](file://src/hive-mind/core/Queen.ts#L28-L773)
- [daa-tools.js](file://src/mcp/implementations/daa-tools.js#L171-L219)

**Section sources**
- [Queen.ts](file://src/hive-mind/core/Queen.ts#L28-L773)

## Performance Monitoring and Optimization
The Queen continuously monitors system performance through two dedicated loops: a coordination loop that runs every 5 seconds and an optimization loop that runs every minute. These loops enable proactive system management and continuous improvement.

The coordination loop performs three key monitoring functions:
1. **Agent Health Monitoring**: Checks if agents are responsive and handles failures
2. **Task Progress Monitoring**: Identifies stalled tasks that haven't progressed in 10 minutes
3. **System Rebalancing**: Detects high agent utilization or task backlog that requires resource adjustment

The optimization loop focuses on long-term system improvement:
1. **Performance Pattern Analysis**: Uses MCP tools to identify performance trends
2. **Strategy Optimization**: Adjusts coordination strategies based on effectiveness
3. **Neural Pattern Training**: Trains neural networks on successful decisions for future learning

```mermaid
flowchart TD
A[Start Coordination Loop] --> B[Monitor Agent Health]
B --> C{Agent Failed?}
C --> |Yes| D[Handle Agent Failure]
C --> |No| E[Check Task Progress]
E --> F{Task Stalled?}
F --> |Yes| G[Handle Stalled Task]
F --> |No| H[Check Rebalancing Needs]
H --> I{Rebalance Needed?}
I --> |Yes| J[Emit Rebalance Event]
I --> |No| K[End Coordination Loop]
L[Start Optimization Loop] --> M[Analyze Performance Patterns]
M --> N{Recommendations Available?}
N --> |Yes| O[Apply Performance Recommendations]
N --> |No| P[Optimize Strategies]
P --> Q{Adjust Strategies?}
Q --> |Yes| R[Adjust Strategy Parameters]
Q --> |No| S[Train Neural Patterns]
S --> T{Sufficient Data?}
T --> |Yes| U[Train Neural Network]
T --> |No| V[End Optimization Loop]
```

**Diagram sources**
- [Queen.ts](file://src/hive-mind/core/Queen.ts#L28-L773)

**Section sources**
- [Queen.ts](file://src/hive-mind/core/Queen.ts#L28-L773)

## Queen Failure Scenarios and Solutions
The Queen implements several mechanisms to handle failure scenarios and ensure system resilience. While the Queen is a central component, the system includes safeguards to maintain functionality even when the Queen encounters issues.

### Agent Failure Handling
When an agent fails or becomes unresponsive, the Queen automatically reassigns its tasks to available agents:

```mermaid
flowchart TD
A[Detect Agent Failure] --> B[Check for Current Task]
B --> C{Agent has task?}
C --> |Yes| D[Reassign Task to Available Agent]
C --> |No| E[Update Agent Status to Offline]
D --> F[Update Database Task Assignment]
F --> G[Assign Task to New Agent]
G --> H[Emit Agent Failed Event]
E --> H
```

### Stalled Task Recovery
Tasks that stall (show no progress for 10 minutes) trigger a recovery process:

```mermaid
flowchart TD
A[Detect Stalled Task] --> B[Emit Task Stalled Event]
B --> C[System Can Implement Recovery]
C --> D[Reassign Task or Adjust Strategy]
```

### System Rebalancing
When system load becomes unbalanced, the Queen emits a rebalance event:

```mermaid
flowchart TD
A[Check System Stats] --> B{High Utilization or Backlog?}
B --> |Yes| C[Emit Rebalance Needed Event]
B --> |No| D[Continue Monitoring]
```

The primary solution for Queen failure scenarios is proactive monitoring and automatic recovery. The Queen continuously monitors agent health and task progress, automatically reassigning tasks when agents fail or tasks stall. For system-wide rebalancing, the Queen emits events that can be handled by higher-level system components.

**Section sources**
- [Queen.ts](file://src/hive-mind/core/Queen.ts#L28-L773)

## Conclusion
The Queen class serves as the central intelligence in the swarm system, providing strategic planning, agent coordination, and performance optimization capabilities. Through its sophisticated decision-making algorithms, the Queen analyzes tasks, selects optimal strategies, and assigns work to the most suitable agents. The continuous monitoring loops ensure system health and enable proactive optimization. The communication model provides a robust framework for task assignment and progress tracking, while the failure handling mechanisms maintain system resilience. This comprehensive implementation makes the Queen an effective central coordinator that can adapt to changing conditions and optimize swarm performance over time.