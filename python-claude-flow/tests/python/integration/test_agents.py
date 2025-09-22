"""
Integration tests for agent coordination and orchestration.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import List, Dict, Any

from claude_flow.agents.queen import QueenAgent
from claude_flow.agents.workers import (
    ArchitectAgent, CoderAgent, TesterAgent, DocumentationAgent
)
from claude_flow.agents.base import AgentState, TaskPriority
from claude_flow.agents.orchestrator import AgentOrchestrator
from claude_flow.events.bus import EventBus, Event
from claude_flow.events.models import EventType
from claude_flow.memory.manager import MemoryManager
from claude_flow.config.models import ClaudeFlowConfig


class TestAgentCoordination:
    """Test coordination between different agent types."""
    
    @pytest.fixture
    async def orchestrator(self, claude_flow_config):
        """Create agent orchestrator for testing."""
        orchestrator = AgentOrchestrator(claude_flow_config)
        await orchestrator.initialize()
        yield orchestrator
        await orchestrator.shutdown()
    
    @pytest.fixture
    async def queen_agent(self, claude_flow_config, event_bus):
        """Create queen agent for testing."""
        queen = QueenAgent("queen_test", claude_flow_config, event_bus)
        await queen.initialize()
        yield queen
        await queen.shutdown()
    
    @pytest.fixture
    async def worker_agents(self, claude_flow_config, event_bus):
        """Create worker agents for testing."""
        agents = {
            "architect": ArchitectAgent("architect_test", claude_flow_config, event_bus),
            "coder": CoderAgent("coder_test", claude_flow_config, event_bus),
            "tester": TesterAgent("tester_test", claude_flow_config, event_bus),
            "docs": DocumentationAgent("docs_test", claude_flow_config, event_bus)
        }
        
        for agent in agents.values():
            await agent.initialize()
        
        yield agents
        
        for agent in agents.values():
            await agent.shutdown()
    
    @pytest.mark.asyncio
    async def test_queen_agent_initialization(self, queen_agent):
        """Test queen agent initialization and state."""
        assert queen_agent.state == AgentState.IDLE
        assert queen_agent.name == "queen_test"
        assert queen_agent.agent_type == "queen"
        assert len(queen_agent.active_tasks) == 0
    
    @pytest.mark.asyncio
    async def test_worker_agent_initialization(self, worker_agents):
        """Test worker agent initialization."""
        for agent_type, agent in worker_agents.items():
            assert agent.state == AgentState.IDLE
            assert agent.agent_type == agent_type
            assert agent.capabilities is not None
    
    @pytest.mark.asyncio
    async def test_task_assignment_flow(self, queen_agent, worker_agents, event_bus):
        """Test complete task assignment flow."""
        architect = worker_agents["architect"]
        coder = worker_agents["coder"]
        
        # Register workers with queen
        for worker in worker_agents.values():
            await queen_agent.register_worker(worker)
        
        # Create a complex task
        task = {
            "id": "integration_test_task",
            "type": "feature_development",
            "description": "Build a new API endpoint",
            "requirements": [
                "Design the API structure",
                "Implement the endpoint",
                "Write tests",
                "Document the API"
            ],
            "priority": TaskPriority.HIGH
        }
        
        # Queen should decompose and assign tasks
        subtasks = await queen_agent.decompose_task(task)
        
        assert len(subtasks) > 0
        
        # Assign tasks to appropriate workers
        assignments = await queen_agent.assign_tasks(subtasks)
        
        assert len(assignments) > 0
        
        # Verify task assignments
        architect_tasks = [t for t in assignments if t.get("assigned_to") == "architect_test"]
        coder_tasks = [t for t in assignments if t.get("assigned_to") == "coder_test"]
        
        assert len(architect_tasks) > 0  # Architecture tasks
        assert len(coder_tasks) > 0      # Coding tasks
    
    @pytest.mark.asyncio
    async def test_agent_communication(self, worker_agents, event_bus):
        """Test communication between agents via events."""
        architect = worker_agents["architect"]
        coder = worker_agents["coder"]
        
        received_events = []
        
        async def event_handler(event: Event):
            received_events.append(event)
        
        # Subscribe coder to architect events
        await event_bus.subscribe(EventType.TASK_COMPLETED, event_handler)
        
        # Architect completes design task
        design_event = Event(
            type=EventType.TASK_COMPLETED,
            data={
                "task_id": "design_api",
                "agent_id": architect.agent_id,
                "result": {
                    "api_design": {
                        "endpoints": ["/api/v1/users", "/api/v1/tasks"],
                        "models": ["User", "Task"]
                    }
                }
            },
            source=architect.agent_id
        )
        
        await event_bus.publish(design_event)
        await asyncio.sleep(0.1)  # Allow event processing
        
        # Coder should have received the design
        assert len(received_events) > 0
        assert received_events[0].data["task_id"] == "design_api"
    
    @pytest.mark.asyncio
    async def test_collaborative_workflow(self, orchestrator, event_bus):
        """Test complete collaborative workflow."""
        workflow_events = []
        
        async def workflow_tracker(event: Event):
            workflow_events.append(event)
        
        # Track all workflow events
        await event_bus.subscribe(EventType.TASK_CREATED, workflow_tracker)
        await event_bus.subscribe(EventType.TASK_ASSIGNED, workflow_tracker)
        await event_bus.subscribe(EventType.TASK_STARTED, workflow_tracker)
        await event_bus.subscribe(EventType.TASK_COMPLETED, workflow_tracker)
        
        # Submit complex project
        project = {
            "name": "User Management System",
            "description": "Complete user management with authentication",
            "deliverables": [
                "Architecture design",
                "Database schema",
                "API implementation", 
                "Frontend interface",
                "Unit tests",
                "Integration tests",
                "Documentation"
            ]
        }
        
        # Process through orchestrator
        result = await orchestrator.process_project(project)
        
        await asyncio.sleep(0.2)  # Allow all events to process
        
        # Verify workflow progression
        task_created_events = [e for e in workflow_events if e.type == EventType.TASK_CREATED]
        task_assigned_events = [e for e in workflow_events if e.type == EventType.TASK_ASSIGNED]
        
        assert len(task_created_events) > 0
        assert len(task_assigned_events) > 0
        
        # Verify result structure
        assert "project_id" in result
        assert "tasks" in result
        assert len(result["tasks"]) > 0
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, queen_agent, worker_agents):
        """Test error handling and task recovery."""
        coder = worker_agents["coder"]
        
        # Register worker
        await queen_agent.register_worker(coder)
        
        # Create task that will fail
        failing_task = {
            "id": "failing_task",
            "type": "impossible_task",
            "description": "Task designed to fail",
            "simulate_failure": True
        }
        
        # Assign task
        assignment = await queen_agent.assign_task(failing_task, coder)
        
        # Worker should report failure
        failure_result = await coder.execute_task(assignment)
        
        assert failure_result["status"] == "failed"
        assert "error" in failure_result
        
        # Queen should handle failure and potentially reassign
        recovery_action = await queen_agent.handle_task_failure(
            assignment, failure_result
        )
        
        assert recovery_action is not None
        assert recovery_action["action"] in ["retry", "reassign", "escalate"]
    
    @pytest.mark.asyncio
    async def test_load_balancing(self, queen_agent, event_bus):
        """Test load balancing across multiple workers."""
        # Create multiple coder agents
        coders = []
        for i in range(3):
            coder = CoderAgent(f"coder_{i}", queen_agent.config, event_bus)
            await coder.initialize()
            await queen_agent.register_worker(coder)
            coders.append(coder)
        
        try:
            # Create multiple similar tasks
            tasks = []
            for i in range(6):
                task = {
                    "id": f"coding_task_{i}",
                    "type": "implementation",
                    "description": f"Implement feature {i}",
                    "estimated_effort": 1.0
                }
                tasks.append(task)
            
            # Assign all tasks
            assignments = []
            for task in tasks:
                assignment = await queen_agent.assign_task(task)
                assignments.append(assignment)
                await asyncio.sleep(0.01)  # Small delay
            
            # Check load distribution
            assignment_counts = {}
            for assignment in assignments:
                worker_id = assignment.get("assigned_to", "unknown")
                assignment_counts[worker_id] = assignment_counts.get(worker_id, 0) + 1
            
            # Should have relatively even distribution
            assert len(assignment_counts) == 3  # All workers got tasks
            
            # No worker should have more than 3 tasks (6 tasks / 3 workers + 1)
            for count in assignment_counts.values():
                assert count <= 3
        
        finally:
            # Cleanup
            for coder in coders:
                await coder.shutdown()
    
    @pytest.mark.asyncio
    async def test_priority_task_handling(self, queen_agent, worker_agents):
        """Test priority-based task scheduling."""
        coder = worker_agents["coder"]
        await queen_agent.register_worker(coder)
        
        # Create tasks with different priorities
        tasks = [
            {
                "id": "low_priority_task",
                "priority": TaskPriority.LOW,
                "description": "Low priority work"
            },
            {
                "id": "critical_task", 
                "priority": TaskPriority.CRITICAL,
                "description": "Critical urgent work"
            },
            {
                "id": "normal_task",
                "priority": TaskPriority.NORMAL,
                "description": "Normal priority work"
            },
            {
                "id": "high_priority_task",
                "priority": TaskPriority.HIGH,
                "description": "High priority work"
            }
        ]
        
        # Submit all tasks
        for task in tasks:
            await queen_agent.submit_task(task)
        
        # Process tasks - should be handled by priority
        processed_tasks = []
        while len(processed_tasks) < 4:
            next_task = await queen_agent.get_next_task()
            if next_task:
                processed_tasks.append(next_task)
            else:
                break
        
        # Verify priority order
        assert len(processed_tasks) == 4
        assert processed_tasks[0]["id"] == "critical_task"
        assert processed_tasks[1]["id"] == "high_priority_task"
        assert processed_tasks[2]["id"] == "normal_task"
        assert processed_tasks[3]["id"] == "low_priority_task"


class TestAgentMemoryIntegration:
    """Test agent integration with memory system."""
    
    @pytest.fixture
    async def memory_manager(self, claude_flow_config):
        """Create memory manager for testing."""
        manager = MemoryManager(claude_flow_config)
        await manager.initialize()
        yield manager
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_shared_memory_access(self, worker_agents, memory_manager):
        """Test agents sharing information through memory."""
        architect = worker_agents["architect"]
        coder = worker_agents["coder"]
        
        # Architect stores design decisions
        design_data = {
            "api_design": {
                "version": "v1",
                "base_url": "/api/v1",
                "authentication": "JWT",
                "endpoints": {
                    "/users": {"methods": ["GET", "POST"]},
                    "/tasks": {"methods": ["GET", "POST", "PUT", "DELETE"]}
                }
            }
        }
        
        await memory_manager.store(
            key="project_api_design",
            data=design_data,
            agent_id=architect.agent_id,
            tags=["design", "api", "architecture"]
        )
        
        # Coder retrieves design for implementation
        retrieved_design = await memory_manager.retrieve(
            key="project_api_design"
        )
        
        assert retrieved_design is not None
        assert retrieved_design["api_design"]["version"] == "v1"
        assert "/users" in retrieved_design["api_design"]["endpoints"]
        
        # Coder stores implementation notes
        impl_data = {
            "implementation_status": {
                "/users": "completed",
                "/tasks": "in_progress"
            },
            "technical_notes": "Using FastAPI framework with SQLAlchemy ORM"
        }
        
        await memory_manager.store(
            key="project_implementation_status",
            data=impl_data,
            agent_id=coder.agent_id,
            tags=["implementation", "status", "progress"]
        )
        
        # Both agents can access shared project context
        project_memories = await memory_manager.search(
            query="project implementation",
            tags=["implementation", "design"]
        )
        
        assert len(project_memories) >= 2
    
    @pytest.mark.asyncio
    async def test_memory_based_learning(self, worker_agents, memory_manager):
        """Test agents learning from past experiences."""
        coder = worker_agents["coder"]
        
        # Store past coding patterns and solutions
        patterns = [
            {
                "pattern": "REST API endpoint implementation",
                "solution": "Use FastAPI with Pydantic models for validation",
                "success_rate": 0.95,
                "context": ["web_api", "python", "validation"]
            },
            {
                "pattern": "Database connection handling",
                "solution": "Use connection pooling with async SQLAlchemy",
                "success_rate": 0.90,
                "context": ["database", "async", "performance"]
            },
            {
                "pattern": "Error handling in API endpoints",
                "solution": "Custom exception handlers with proper HTTP status codes",
                "success_rate": 0.88,
                "context": ["error_handling", "http", "api"]
            }
        ]
        
        for i, pattern in enumerate(patterns):
            await memory_manager.store(
                key=f"coding_pattern_{i}",
                data=pattern,
                agent_id=coder.agent_id,
                tags=["coding_pattern", "best_practice"] + pattern["context"]
            )
        
        # When given new task, coder should find relevant patterns
        new_task = {
            "description": "Implement new REST API endpoint with proper error handling",
            "requirements": ["API", "error handling", "validation"]
        }
        
        relevant_patterns = await memory_manager.find_similar(
            query="REST API endpoint error handling",
            agent_id=coder.agent_id,
            limit=3
        )
        
        assert len(relevant_patterns) > 0
        
        # Should find patterns related to API and error handling
        found_api_pattern = any(
            "REST API" in pattern.get("data", {}).get("pattern", "")
            for pattern in relevant_patterns
        )
        found_error_pattern = any(
            "Error handling" in pattern.get("data", {}).get("pattern", "")
            for pattern in relevant_patterns
        )
        
        assert found_api_pattern or found_error_pattern


@pytest.mark.integration
class TestFullSystemIntegration:
    """Test complete system integration with all components."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_project_workflow(self, claude_flow_config):
        """Test complete end-to-end project workflow."""
        # Initialize all components
        event_bus = EventBus(claude_flow_config.events)
        await event_bus.initialize()
        
        memory_manager = MemoryManager(claude_flow_config)
        await memory_manager.initialize()
        
        orchestrator = AgentOrchestrator(claude_flow_config)
        await orchestrator.initialize()
        
        try:
            # Submit complex project
            project_request = {
                "name": "E-commerce Product Catalog",
                "description": "Build a product catalog API with search functionality",
                "requirements": [
                    "Design scalable architecture",
                    "Implement product CRUD operations",
                    "Add search and filtering",
                    "Include user authentication",
                    "Write comprehensive tests",
                    "Create API documentation",
                    "Set up monitoring"
                ],
                "timeline": "2 weeks",
                "priority": "high"
            }
            
            # Process project
            project_result = await orchestrator.execute_project(project_request)
            
            # Verify project execution
            assert project_result["status"] in ["completed", "in_progress"]
            assert "project_id" in project_result
            assert "tasks" in project_result
            assert len(project_result["tasks"]) > 0
            
            # Verify task distribution across agent types
            task_types = [task.get("agent_type") for task in project_result["tasks"]]
            assert "architect" in task_types  # Architecture tasks
            assert "coder" in task_types      # Implementation tasks
            
            # Verify memory storage of project artifacts
            project_memories = await memory_manager.search(
                query=f"project {project_result['project_id']}",
                limit=10
            )
            assert len(project_memories) > 0
            
        finally:
            # Cleanup
            await orchestrator.shutdown()
            await memory_manager.shutdown()
            await event_bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_fault_tolerance_and_recovery(self, claude_flow_config):
        """Test system fault tolerance and recovery mechanisms."""
        orchestrator = AgentOrchestrator(claude_flow_config)
        await orchestrator.initialize()
        
        try:
            # Submit project with intentional failure points
            risky_project = {
                "name": "Fault Tolerance Test",
                "requirements": [
                    "Task that will timeout",
                    "Task that will fail",
                    "Task that will succeed",
                    "Task depending on failed task"
                ],
                "simulate_failures": True
            }
            
            result = await orchestrator.execute_project(risky_project)
            
            # System should handle failures gracefully
            assert result["status"] in ["partially_completed", "completed"]
            
            # Should have recovery attempts logged
            recovery_logs = result.get("recovery_attempts", [])
            assert len(recovery_logs) > 0
            
        finally:
            await orchestrator.shutdown()
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self, claude_flow_config):
        """Test system performance under concurrent load."""
        orchestrator = AgentOrchestrator(claude_flow_config)
        await orchestrator.initialize()
        
        try:
            # Submit multiple projects concurrently
            projects = []
            for i in range(5):
                project = {
                    "name": f"Concurrent Project {i}",
                    "description": f"Test project {i} for load testing",
                    "requirements": [
                        "Simple implementation task",
                        "Basic testing task"
                    ]
                }
                projects.append(project)
            
            # Execute all projects concurrently
            import time
            start_time = time.time()
            
            results = await asyncio.gather(*[
                orchestrator.execute_project(project)
                for project in projects
            ], return_exceptions=True)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Verify all projects completed
            successful_results = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_results) == 5
            
            # Performance should be reasonable (adjust threshold as needed)
            assert execution_time < 30.0  # Should complete within 30 seconds
            
        finally:
            await orchestrator.shutdown()