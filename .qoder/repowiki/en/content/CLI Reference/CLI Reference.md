# CLI Reference

<cite>
**Referenced Files in This Document**   
- [bin/claude-flow.js](file://bin/claude-flow.js)
- [src/cli/simple-cli.js](file://src/cli/simple-cli.js)
- [src/cli/command-registry.js](file://src/cli/command-registry.js)
- [src/cli/help-text.js](file://src/cli/help-text.js)
- [src/cli/commands/hive-mind/index.ts](file://src/cli/commands/hive-mind/index.ts)
- [src/cli/commands/swarm.ts](file://src/cli/commands/swarm.ts)
- [src/cli/commands/memory.ts](file://src/cli/commands/memory.ts)
- [src/cli/commands/github.js](file://src/cli/simple-commands/github.js)
- [src/cli/commands/workflow.ts](file://src/cli/commands/workflow.ts)
- [src/cli/commands/utility.js](file://src/cli/simple-commands/utils.js)
</cite>

## Table of Contents
1. [Command Structure and Syntax](#command-structure-and-syntax)
2. [Global Options](#global-options)
3. [Hive-Mind Commands](#hive-mind-commands)
4. [Swarm Commands](#swarm-commands)
5. [Memory Commands](#memory-commands)
6. [Neural Commands](#neural-commands)
7. [GitHub Commands](#github-commands)
8. [Workflow Commands](#workflow-commands)
9. [Utility Commands](#utility-commands)
10. [Command Relationships and Workflows](#command-relationships-and-workflows)
11. [Common Issues and Troubleshooting](#common-issues-and-troubleshooting)
12. [Performance Considerations](#performance-considerations)

## Command Structure and Syntax

The Claude-Flow CLI follows a consistent command structure designed for both simplicity and advanced orchestration capabilities. The basic syntax pattern is:

```
claude-flow <command> [subcommand] [arguments] [options]
```

Commands are organized into categories with hierarchical subcommands. The system uses Commander.js for command parsing and validation. The CLI dispatcher in `bin/claude-flow.js` detects the optimal runtime environment and routes execution to the appropriate implementation.

The command execution flow begins with the dispatcher, which attempts to execute the JavaScript version of the CLI (`simple-cli.js`) first for maximum compatibility. If the JavaScript version is unavailable, it falls back to the TypeScript version using `tsx`.

```mermaid
flowchart TD
Start([CLI Execution]) --> Dispatcher["bin/claude-flow.js\nDispatcher"]
Dispatcher --> JSVersion{"simple-cli.js\nExists?"}
JSVersion --> |Yes| ExecuteJS["Execute Node.js\nVersion"]
JSVersion --> |No| TSVersions["Check TypeScript\nVersions"]
TSVersions --> TSExists{"simple-cli.ts\nExists?"}
TSExists --> |Yes| ExecuteTS["Execute with tsx"]
TSExists --> |No| Fallback["Show Fallback Help"]
ExecuteJS --> Registry["command-registry.js"]
ExecuteTS --> Registry
Registry --> Command["Execute Specific\nCommand Handler"]
Command --> Complete([Command Complete])
style Dispatcher fill:#f9f,stroke:#333
style Registry fill:#bbf,stroke:#333,color:#fff
style Command fill:#f96,stroke:#333
```

**Diagram sources**
- [bin/claude-flow.js](file://bin/claude-flow.js#L1-L148)
- [src/cli/simple-cli.js](file://src/cli/simple-cli.js#L1-L3430)
- [src/cli/command-registry.js](file://src/cli/command-registry.js#L1-L1088)

**Section sources**
- [bin/claude-flow.js](file://bin/claude-flow.js#L1-L148)
- [src/cli/simple-cli.js](file://src/cli/simple-cli.js#L1-L3430)

## Global Options

Claude-Flow provides a set of global options that can be used with most commands to modify their behavior:

```mermaid
flowchart LR
A[Global Options] --> B["--verbose, -v"]
A --> C["--help"]
A --> D["--config <path>"]
A --> E["--parallel"]
A --> F["--monitor"]
A --> G["--json"]
A --> H["--dry-run"]
B --> I["Enable detailed output\nwith performance metrics"]
C --> J["Show command-specific help"]
D --> K["Use custom\nenterprise configuration"]
E --> L["Enable parallel execution\n(default for swarms)"]
F --> M["Real-time monitoring\nand performance tracking"]
G --> N["Output in JSON format\nfor programmatic use"]
H --> O["Show configuration\nwithout executing"]
```

These options are processed by the `parseFlags` function in `utils.js` and made available to command handlers through the `CommandContext` object. The `--verbose` flag enables detailed logging that includes performance metrics and internal state information, which is particularly useful for debugging complex workflows.

The `--json` flag is implemented across most commands to provide machine-readable output, facilitating integration with other tools and automation scripts. This is particularly valuable in CI/CD pipelines where the output needs to be parsed programmatically.

**Section sources**
- [src/cli/simple-cli.js](file://src/cli/simple-cli.js#L1-L3430)
- [src/cli/utils.js](file://src/cli/utils.js#L1-L100)

## Hive-Mind Commands

The Hive-Mind command category provides collective intelligence swarm management capabilities, enabling coordinated multi-agent operations with centralized control.

```mermaid
classDiagram
class HiveMindCommand {
+description : string
+addCommand(command : Command)
+execute(context : CommandContext)
}
class Command {
<<interface>>
+name : string
+description : string
+handler : Function
}
class InitCommand {
+handler(context : CommandContext)
}
class SpawnCommand {
+handler(context : CommandContext)
}
class StatusCommand {
+handler(context : CommandContext)
}
class TaskCommand {
+handler(context : CommandContext)
}
class WizardCommand {
+handler(context : CommandContext)
}
class StopCommand {
+handler(context : CommandContext)
}
class PauseCommand {
+handler(context : CommandContext)
}
class ResumeCommand {
+handler(context : CommandContext)
}
class PsCommand {
+handler(context : CommandContext)
}
HiveMindCommand --> Command : "contains"
HiveMindCommand --> InitCommand : "addCommand"
HiveMindCommand --> SpawnCommand : "addCommand"
HiveMindCommand --> StatusCommand : "addCommand"
HiveMindCommand --> TaskCommand : "addCommand"
HiveMindCommand --> WizardCommand : "addCommand"
HiveMindCommand --> StopCommand : "addCommand"
HiveMindCommand --> PauseCommand : "addCommand"
HiveMindCommand --> ResumeCommand : "addCommand"
HiveMindCommand --> PsCommand : "addCommand"
```

**Diagram sources**
- [src/cli/commands/hive-mind/index.ts](file://src/cli/commands/hive-mind/index.ts#L1-L43)
- [src/cli/commands/hive-mind/init.js](file://src/cli/commands/hive-mind/init.js#L1-L50)
- [src/cli/commands/hive-mind/spawn.js](file://src/cli/commands/hive-mind/spawn.js#L1-L50)

### hive-mind wizard

The interactive setup wizard guides users through the configuration process:

**Invocation Syntax**
```
claude-flow hive-mind wizard
```

**Parameters**
- No positional parameters

**Options**
- None

**Return Values**
- Exit code 0 on successful completion
- Exit code 1 on error or interruption

**Examples**
```bash
# Start the interactive setup wizard
claude-flow hive-mind wizard

# The wizard will guide you through:
# 1. System configuration
# 2. Agent type selection
# 3. Memory settings
# 4. Network topology
# 5. Security configuration
```

### hive-mind spawn

Creates an intelligent swarm with a specific objective:

**Invocation Syntax**
```
claude-flow hive-mind spawn <task> [options]
```

**Parameters**
- `task`: The objective for the swarm to accomplish

**Options**
- `--claude`: Open Claude Code CLI after swarm creation
- `--strategy <type>`: Strategy type (research, development, analysis, testing, optimization, maintenance)
- `--mode <type>`: Coordination mode (centralized, distributed, hierarchical, mesh, hybrid)
- `--max-agents <n>`: Maximum number of agents (default: 5)
- `--parallel`: Enable parallel execution
- `--monitor`: Enable real-time monitoring

**Return Values**
- Swarm ID on success
- Error message on failure

**Examples**
```bash
# Create a swarm to build an API
claude-flow hive-mind spawn "Build a REST API" --strategy development --parallel

# Create a research swarm
claude-flow hive-mind spawn "Research cloud architecture" --strategy research --monitor

# Create a swarm and open Claude Code CLI
claude-flow hive-mind spawn "Implement feature" --claude
```

### hive-mind status

Displays the current status of active swarms:

**Invocation Syntax**
```
claude-flow hive-mind status [options]
```

**Parameters**
- None

**Options**
- `--verbose`: Show detailed information
- `--json`: Output in JSON format
- `--recent <n>`: Show only the most recent n swarms

**Return Values**
- Table of active swarms with status information
- JSON object when `--json` is specified

**Examples**
```bash
# Show basic status
claude-flow hive-mind status

# Show detailed status
claude-flow hive-mind status --verbose

# Get JSON output for scripting
claude-flow hive-mind status --json | jq '.activeSwarmCount'
```

## Swarm Commands

The Swarm command category enables multi-agent AI coordination for accomplishing complex objectives through parallel processing and neural optimization.

```mermaid
sequenceDiagram
participant User
participant CLI as simple-cli.js
participant Swarm as SwarmCoordinator
participant Agent1 as Agent 1
participant Agent2 as Agent 2
participant Memory as SwarmMemoryManager
User->>CLI : swarm "Build API" --parallel --monitor
CLI->>Swarm : createObjective("Build API")
Swarm->>Swarm : registerAgents(5)
Swarm->>Agent1 : assignTask(design)
Swarm->>Agent2 : assignTask(implement)
Agent1->>Memory : store("API design", designDoc)
Agent2->>Memory : store("implementation", code)
Memory-->>Swarm : confirmation
Swarm-->>CLI : progressUpdate
loop Monitoring
CLI->>Swarm : getStatus()
Swarm-->>CLI : statusReport
end
CLI-->>User : completionMessage
```

**Diagram sources**
- [src/cli/commands/swarm.ts](file://src/cli/commands/swarm.ts#L1-L640)
- [src/coordination/swarm-coordinator.js](file://src/coordination/swarm-coordinator.js#L1-L200)
- [src/memory/swarm-memory.js](file://src/memory/swarm-memory.js#L1-L100)

### swarm

Deploys intelligent multi-agent swarms to accomplish complex objectives:

**Invocation Syntax**
```
claude-flow swarm <objective> [options]
```

**Parameters**
- `objective`: The goal for the swarm to achieve

**Options**
- `--dry-run`: Show configuration without executing
- `--strategy <type>`: Strategy type (auto, research, development, analysis, testing, optimization)
- `--max-agents <n>`: Maximum number of agents (default: 5)
- `--timeout <minutes>`: Timeout in minutes (default: 60)
- `--research`: Enable research capabilities
- `--parallel`: Enable parallel execution
- `--review`: Enable peer review between agents
- `--monitor`: Enable real-time monitoring
- `--ui`: Use terminal UI
- `--background`: Run in background mode
- `--distributed`: Enable distributed coordination
- `--memory-namespace`: Memory namespace for swarm (default: swarm)
- `--persistence`: Enable task persistence (default: true)

**Return Values**
- Swarm ID and objective ID on success
- Error message on failure
- Progress updates during execution
- Final completion message

**Examples**
```bash
# Deploy a swarm to build a REST API
claude-flow swarm "Build a REST API" --strategy development --parallel --monitor

# Research cloud architecture options
claude-flow swarm "Research cloud architecture" --strategy research --research --max-agents 3

# Dry run to see configuration
claude-flow swarm "Implement feature" --strategy development --dry-run

# Run in background mode
claude-flow swarm "Analyze codebase" --background --timeout 120
```

## Memory Commands

The Memory command category provides persistent storage and retrieval capabilities for cross-session data and knowledge management.

```mermaid
classDiagram
class SimpleMemoryManager {
-filePath : string
-data : Record<string, MemoryEntry[]>
+load() : Promise<void>
+save() : Promise<void>
+store(key : string, value : string, namespace : string) : Promise<void>
+query(search : string, namespace? : string) : Promise<MemoryEntry[]>
+getStats() : Promise<MemoryStats>
+exportData(filePath : string) : Promise<void>
+importData(filePath : string) : Promise<void>
+cleanup(daysOld : number) : Promise<number>
}
class MemoryEntry {
+key : string
+value : string
+namespace : string
+timestamp : number
}
class MemoryStats {
+totalEntries : number
+namespaces : number
+namespaceStats : Record<string, number>
+sizeBytes : number
}
SimpleMemoryManager --> MemoryEntry
SimpleMemoryManager --> MemoryStats
```

**Diagram sources**
- [src/cli/commands/memory.ts](file://src/cli/commands/memory.ts#L1-L266)
- [src/memory/memory-store.json](file://src/memory/memory-store.json#L1-L50)

### memory store

Stores information in the persistent memory bank:

**Invocation Syntax**
```
claude-flow memory store <key> <value> [options]
```

**Parameters**
- `key`: Identifier for the stored data
- `value`: Data to store (can be quoted string)

**Options**
- `-n, --namespace <namespace>`: Target namespace (default: default)

**Return Values**
- Success confirmation with key, namespace, and size
- Error message on failure

**Examples**
```bash
# Store architectural decision
claude-flow memory store "architecture" "microservices with API gateway pattern"

# Store in specific namespace
claude-flow memory store "security-rules" "implement OAuth2" --namespace security

# Store configuration
claude-flow memory store "db-config" '{"host":"localhost","port":5432}' --namespace database
```

### memory query

Searches for stored memory entries:

**Invocation Syntax**
```
claude-flow memory query <search> [options]
```

**Parameters**
- `search`: Term to search for in keys or values

**Options**
- `-n, --namespace <namespace>`: Filter by namespace
- `-l, --limit <limit>`: Limit results (default: 10)

**Return Values**
- List of matching entries with key, namespace, value preview, and timestamp
- "No results found" message if no matches

**Examples**
```bash
# Search for all entries containing "API"
claude-flow memory query "API"

# Search in specific namespace
claude-flow memory query "security" --namespace security

# Limit results
claude-flow memory query "database" --limit 5
```

### memory stats

Displays statistics about the memory store:

**Invocation Syntax**
```
claude-flow memory stats
```

**Parameters**
- None

**Options**
- None

**Return Values**
- Total number of entries
- Number of namespaces
- Statistics by namespace
- Total size in bytes

**Examples**
```bash
# Show memory statistics
claude-flow memory stats
```

### memory export

Exports memory data to a file:

**Invocation Syntax**
```
claude-flow memory export <file>
```

**Parameters**
- `file`: Path to export file

**Options**
- None

**Return Values**
- Success confirmation with file path and entry count
- Error message on failure

**Examples**
```bash
# Export memory to backup file
claude-flow memory export backup-2025-08-04.json
```

## Neural Commands

Based on the repository analysis, while neural networking capabilities are mentioned in the documentation and help text, no specific "neural" command file was found in the codebase. The neural functionality appears to be integrated into other command categories, particularly Swarm and Hive-Mind commands.

The system references "WASM-powered cognitive patterns with SIMD optimization" and "Real WASM Neural Networks - ruv-fann powered actual neural processing" in its help text, indicating that neural processing is implemented but not exposed as a separate command category.

Neural capabilities are likely embedded within the swarm coordination and memory management systems, providing optimization and learning capabilities without requiring direct user interaction with neural-specific commands.

**Section sources**
- [src/cli/help-text.js](file://src/cli/help-text.js#L1-L1030)
- [src/cli/simple-cli.js](file://src/cli/simple-cli.js#L1-L3430)

## GitHub Commands

The GitHub command category provides specialized modes for GitHub workflow automation, enabling coordinated development and project management.

```mermaid
flowchart TD
A[GitHub Commands] --> B["github gh-coordinator"]
A --> C["github pr-manager"]
A --> D["github issue-tracker"]
A --> E["github release-manager"]
A --> F["github repo-architect"]
A --> G["github sync-coordinator"]
B --> H["GitHub workflow orchestration\nand coordination"]
C --> I["Pull request management\nwith multi-reviewer coordination"]
D --> J["Issue management\nand project coordination"]
E --> K["Release coordination\nand deployment pipelines"]
F --> L["Repository structure optimization"]
G --> M["Multi-package synchronization\nand version alignment"]
```

**Diagram sources**
- [src/cli/simple-commands/github.js](file://src/cli/simple-commands/github.js#L1-L200)
- [src/cli/command-registry.js](file://src/cli/command-registry.js#L1-L1088)

### github

The main GitHub command with multiple subcommands for workflow automation:

**Invocation Syntax**
```
claude-flow github <mode> <objective> [options]
```

**Parameters**
- `mode`: Specific GitHub workflow mode
- `objective`: Goal for the operation

**Options**
- `--verbose`: Detailed output
- `--json`: JSON output format
- `--dry-run`: Show configuration without executing

**Return Values**
- Operation-specific results
- Progress updates
- Completion status

**Examples**
```bash
# Coordinate pull request review
claude-flow github pr-manager "coordinate release with automated testing"

# Track and manage issues
claude-flow github issue-tracker "prioritize backlog items"

# Manage release process
claude-flow github release-manager "prepare v2.0.0 release"

# Optimize repository structure
claude-flow github repo-architect "improve monorepo organization"
```

## Workflow Commands

The Workflow command category manages tasks and workflows, providing coordination and execution capabilities for complex development processes.

```mermaid
flowchart LR
A[Workflow Commands] --> B["task create"]
A --> C["task list"]
A --> D["task workflow"]
A --> E["task coordination"]
B --> F["Create new task with objective"]
C --> G["List tasks with filtering"]
D --> H["Execute workflow from file"]
E --> I["Manage task coordination"]
```

**Diagram sources**
- [src/cli/commands/workflow.ts](file://src/cli/commands/workflow.ts#L1-L150)
- [src/cli/command-registry.js](file://src/cli/command-registry.js#L1-L1088)

### task

Manages individual tasks and workflows:

**Invocation Syntax**
```
claude-flow task <subcommand> [options]
```

**Subcommands**
- `create`: Create a new task
- `list`: List existing tasks
- `workflow`: Execute a workflow from file
- `coordination`: Manage task coordination

**Options**
- `--filter <status>`: Filter by task status
- `--priority <level>`: Set task priority
- `--assignee <agent>`: Assign to specific agent
- `--deadline <date>`: Set deadline

**Return Values**
- Task ID on creation
- List of tasks with status
- Workflow execution results
- Coordination status

**Examples**
```bash
# Create a research task
claude-flow task create research "Market analysis for new feature"

# List running tasks
claude-flow task list --filter running

# Execute workflow from file
claude-flow task workflow examples/dev-flow.json

# Check coordination status
claude-flow task coordination status
```

## Utility Commands

The Utility command category provides various helper commands for system management and maintenance.

```mermaid
flowchart TD
A[Utility Commands] --> B["init"]
A --> C["start"]
A --> D["status"]
A --> E["config"]
A --> F["mcp"]
A --> G["monitor"]
B --> H["Initialize system files\nand SPARC environment"]
C --> I["Start orchestration system"]
D --> J["System status and health"]
E --> K["System configuration"]
F --> L["MCP server management"]
G --> M["Real-time monitoring"]
```

**Diagram sources**
- [src/cli/command-registry.js](file://src/cli/command-registry.js#L1-L1088)
- [src/cli/simple-commands/init/index.js](file://src/cli/simple-commands/init/index.js#L1-L100)

### init

Initializes the Claude-Flow system with integration files and development environment:

**Invocation Syntax**
```
claude-flow init [options]
```

**Parameters**
- None

**Options**
- `--force`: Overwrite existing files
- `--minimal`: Minimal setup
- `--sparc`: Initialize with SPARC modes
- `--monitoring`: Enable token usage tracking

**Return Values**
- Success confirmation
- List of created files
- Error message on failure

**Examples**
```bash
# Initialize with SPARC modes (recommended)
claude-flow init --sparc

# Minimal setup, overwrite existing
claude-flow init --force --minimal

# Force SPARC setup
claude-flow init --sparc --force
```

### start

Starts the Claude-Flow orchestration system:

**Invocation Syntax**
```
claude-flow start [options]
```

**Parameters**
- None

**Options**
- `--daemon`: Start as background daemon
- `--port <port>`: Use custom MCP port
- `--verbose`: Show detailed system activity
- `--ui`: Launch terminal-based UI
- `--web`: Launch web-based UI

**Return Values**
- System startup confirmation
- Port information
- Error message on failure

**Examples**
```bash
# Start in interactive mode
claude-flow start

# Start as background daemon
claude-flow start --daemon

# Use custom port
claude-flow start --port 8080

# Launch with UI
claude-flow start --ui
```

### status

Displays comprehensive system status and health information:

**Invocation Syntax**
```
claude-flow status [options]
```

**Parameters**
- None

**Options**
- `--verbose`: Detailed system activity
- `--json`: JSON output format
- `--components`: Show component status

**Return Values**
- System health status
- Running processes
- Memory usage
- Agent status
- Error message on failure

**Examples**
```bash
# Show basic status
claude-flow status

# Show detailed status
claude-flow status --verbose

# Get JSON output
claude-flow status --json | jq '.systemHealth'
```

## Command Relationships and Workflows

Claude-Flow commands are designed to work together in coordinated workflows that enable complex AI agent orchestration. The system follows a hierarchical relationship where higher-level commands coordinate lower-level operations.

```mermaid
graph TD
A[Orchestration] --> B[Hive-Mind]
A --> C[Swarm]
B --> D[Agent Management]
C --> D
D --> E[Task Management]
E --> F[Memory Operations]
F --> G[GitHub Automation]
C --> H[Neural Optimization]
B --> H
H --> I[Performance Metrics]
I --> J[Monitoring]
J --> K[Configuration]
K --> L[Utility Commands]
style A fill:#f9f,stroke:#333
style B fill:#bbf,stroke:#333,color:#fff
style C fill:#bbf,stroke:#333,color:#fff
style D fill:#f96,stroke:#333
style E fill:#f96,stroke:#333
style F fill:#f96,stroke:#333
style G fill:#f96,stroke:#333
style H fill:#f96,stroke:#333
style I fill:#f96,stroke:#333
style J fill:#f96,stroke:#333
style K fill:#f96,stroke:#333
style L fill:#f96,stroke:#333
```

**Diagram sources**
- [src/cli/command-registry.js](file://src/cli/command-registry.js#L1-L1088)
- [src/cli/simple-cli.js](file://src/cli/simple-cli.js#L1-L3430)
- [src/cli/help-text.js](file://src/cli/help-text.js#L1-L1030)

### Typical Workflow: Enterprise Development

A common workflow for enterprise development combines multiple commands in sequence:

```bash
# 1. Initialize enterprise environment
npx claude-flow@2.0.0 init --sparc

# 2. Start orchestration with swarm intelligence
./claude-flow start --ui --swarm

# 3. Deploy intelligent multi-agent development workflow
./claude-flow swarm "build enterprise API" --strategy development --parallel --monitor

# 4. Store architectural decisions in memory
./claude-flow memory store "architecture" "microservices with API gateway pattern"

# 5. Automate GitHub workflows
./claude-flow github pr-manager "coordinate release with automated testing"

# 6. Monitor system status
./claude-flow status --verbose
```

### Advanced Workflow: Research and Development

For research and development projects, a different combination of commands is typically used:

```bash
# 1. Start interactive wizard for setup
claude-flow hive-mind wizard

# 2. Create a research swarm
claude-flow swarm "Research new technology" --strategy research --research --max-agents 3

# 3. Store research findings
claude-flow memory store "research-findings" "discovered new approach" --namespace research

# 4. Create development task based on research
claude-flow task create development "Implement new approach" --priority high

# 5. Deploy development swarm
claude-flow swarm "Implement feature" --strategy development --parallel

# 6. Verify implementation
claude-flow verify verify task-123 --agent coder
```

## Common Issues and Troubleshooting

Users may encounter various issues when working with Claude-Flow commands. This section addresses common problems and their solutions.

### Runtime Detection Issues

**Problem**: The CLI dispatcher fails to find a compatible runtime.

**Symptoms**:
- "No compatible runtime found" error message
- Unable to execute commands

**Solutions**:
1. Install tsx globally: `npm install -g tsx`
2. Use direct Node.js execution: `node src/cli/simple-cli.js <command>`
3. Ensure Node.js version 20+ is installed

**Root Cause**: The dispatcher prioritizes the JavaScript version for compatibility but falls back to TypeScript requiring tsx.

**Section sources**
- [bin/claude-flow.js](file://bin/claude-flow.js#L1-L148)

### Command Not Found

**Problem**: Specific commands are not recognized.

**Symptoms**:
- "Unknown command" error
- Help text does not list expected commands

**Solutions**:
1. Ensure the command is properly registered in `command-registry.js`
2. Check for typos in command names
3. Verify the command file exists in the appropriate directory
4. Restart the CLI process to reload command registry

### Memory Operations Fail

**Problem**: Memory store, query, or export operations fail.

**Symptoms**:
- Permission errors when writing to memory
- "Failed to store" error messages
- Empty results from queries

**Solutions**:
1. Ensure the `memory` directory exists and is writable
2. Check file permissions on `memory-store.json`
3. Verify disk space is available
4. Use absolute paths for export operations

**Section sources**
- [src/cli/commands/memory.ts](file://src/cli/commands/memory.ts#L1-L266)

### Swarm Execution Issues

**Problem**: Swarms fail to execute or hang during operation.

**Symptoms**:
- Swarm starts but makes no progress
- Timeout errors
- Agent registration failures

**Solutions**:
1. Check available system resources (CPU, memory)
2. Verify network connectivity for research capabilities
3. Reduce the number of agents with `--max-agents`
4. Increase timeout with `--timeout`
5. Run with `--dry-run` to validate configuration

## Performance Considerations

Optimizing command execution is crucial for efficient AI agent orchestration. This section provides guidance on performance considerations and optimization tips.

### Parallel Execution

The `--parallel` flag enables parallel execution of agents, which can provide significant performance improvements:

```mermaid
graph LR
A[Sequential Execution] --> |Time| B[4x]
C[Parallel Execution] --> |Time| D[1x]
E[Speed Improvement] --> F[2.8-4.4x]
style A fill:#f66,stroke:#333,color:#fff
style C fill:#6f6,stroke:#333,color:#fff
```

**Best Practices**:
- Use `--parallel` for independent tasks
- Limit `--max-agents` based on available CPU cores
- Monitor system resources during parallel execution

### Memory Management

Efficient memory operations are critical for performance:

**Optimization Tips**:
- Use specific namespaces to organize data
- Clean up old entries regularly with `memory cleanup`
- Avoid storing large binary data directly in memory
- Use `--limit` with queries to prevent excessive output

### Command Chaining

The system supports command chaining for complex workflows:

```bash
# Chain commands with && for sequential execution
claude-flow init --sparc && \
claude-flow start --daemon && \
claude-flow swarm "build API" --parallel

# Use background execution for long-running processes
claude-flow swarm "research topic" --background &

# Combine with monitoring
claude-flow swarm "develop feature" --monitor | tee swarm.log
```

### Caching and Reuse

The system implements caching mechanisms to improve performance:

- Memory queries are cached for frequently accessed data
- Agent configurations are reused when possible
- Workflow templates are cached for faster execution

Enable verbose mode with `--verbose` to see caching behavior and performance metrics.

**Section sources**
- [src/cli/commands/memory.ts](file://src/cli/commands/memory.ts#L1-L266)
- [src/cli/commands/swarm.ts](file://src/cli/commands/swarm.ts#L1-L640)
- [src/cli/simple-cli.js](file://src/cli/simple-cli.js#L1-L3430)