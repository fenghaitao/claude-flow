"""
End-to-End tests for complete Claude-Flow workflows.

These tests simulate real-world usage scenarios from start to finish,
including CLI interactions, agent coordination, and system outputs.
"""

import asyncio
import json
import tempfile
import shutil
from pathlib import Path
import pytest
from unittest.mock import patch, AsyncMock
from click.testing import CliRunner

from claude_flow.cli.main import cli
from claude_flow.core.system import ClaudeFlowSystem
from claude_flow.agents.orchestrator import AgentOrchestrator
from claude_flow.config.models import ClaudeFlowConfig, ClaudeConfig


class TestCLIWorkflows:
    """Test CLI-based end-to-end workflows."""
    
    @pytest.fixture
    def cli_runner(self):
        """Create CLI runner for testing."""
        return CliRunner()
    
    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary project directory."""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            yield temp_dir
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.mark.e2e
    def test_project_initialization_workflow(self, cli_runner, temp_project_dir):
        """Test complete project initialization via CLI."""
        with cli_runner.isolated_filesystem():
            # Initialize new project
            result = cli_runner.invoke(cli, [
                'init', 
                '--name', 'test-project',
                '--template', 'web-api',
                '--no-interactive'
            ])
            
            assert result.exit_code == 0
            assert 'Project initialized successfully' in result.output
            
            # Verify project structure was created
            project_files = [
                'claude-flow.yaml',
                'requirements.txt',
                'README.md',
                'src/',
                'tests/'
            ]
            
            for file_path in project_files:
                assert Path(file_path).exists()
    
    @pytest.mark.e2e
    def test_feature_development_workflow(self, cli_runner, temp_project_dir):
        """Test complete feature development workflow."""
        config_content = {
            'claude': {
                'api_key': 'test-key-mock',
                'model': 'claude-3-5-haiku-20241022'
            },
            'project': {
                'name': 'E2E Test Project',
                'type': 'web-api'
            }
        }
        
        config_file = temp_project_dir / 'claude-flow.yaml'
        with open(config_file, 'w') as f:
            import yaml
            yaml.dump(config_content, f)
        
        with cli_runner.isolated_filesystem():
            # Copy config to test directory
            shutil.copy(config_file, 'claude-flow.yaml')
            
            # Mock Claude API responses
            with patch('claude_flow.claude.client.ClaudeClient.chat') as mock_chat:
                mock_chat.return_value = AsyncMock(
                    content="# API Design\\n\\nEndpoints:\\n- GET /api/users\\n- POST /api/users",
                    usage={'total_tokens': 150}
                )
                
                # Start feature development
                result = cli_runner.invoke(cli, [
                    'develop',
                    '--feature', 'user-management',
                    '--description', 'Add user CRUD operations',
                    '--auto-approve'
                ])
                
                assert result.exit_code == 0
                assert 'Feature development started' in result.output or 'Development complete' in result.output
    
    @pytest.mark.e2e
    def test_swarm_coordination_workflow(self, cli_runner, temp_project_dir):
        """Test swarm coordination via CLI."""
        with cli_runner.isolated_filesystem():
            # Create swarm configuration
            swarm_config = {
                'agents': {
                    'architect': {'count': 1, 'capabilities': ['design', 'planning']},
                    'coder': {'count': 2, 'capabilities': ['implementation', 'testing']},
                    'reviewer': {'count': 1, 'capabilities': ['code_review', 'quality_assurance']}
                },
                'workflow': {
                    'stages': ['design', 'implementation', 'review', 'testing']
                }
            }
            
            with open('swarm-config.yaml', 'w') as f:
                import yaml
                yaml.dump(swarm_config, f)
            
            # Start swarm
            result = cli_runner.invoke(cli, [
                'swarm', 'start',
                '--config', 'swarm-config.yaml',
                '--project', 'collaborative-development'
            ])
            
            # Should initialize swarm (even with mocked components)
            assert result.exit_code == 0
            assert 'Swarm started' in result.output or 'agents' in result.output.lower()
    
    @pytest.mark.e2e
    def test_monitoring_and_status_workflow(self, cli_runner):
        """Test monitoring and status checking workflow."""
        with cli_runner.isolated_filesystem():
            # Check system status
            result = cli_runner.invoke(cli, ['status'])
            
            # Should show system status
            assert result.exit_code == 0
            
            # Check agent status
            result = cli_runner.invoke(cli, ['agents', 'list'])
            assert result.exit_code == 0
            
            # Check memory usage
            result = cli_runner.invoke(cli, ['memory', 'stats'])
            assert result.exit_code == 0


class TestSystemWorkflows:
    """Test complete system workflows end-to-end."""
    
    @pytest.fixture
    async def claude_flow_system(self, claude_flow_config, temp_dir):
        """Create complete Claude-Flow system for testing."""
        # Update config for E2E testing
        claude_flow_config.claude.api_key = "test-key-e2e"
        claude_flow_config.database.sqlite.path = str(temp_dir / "e2e_test.db")
        
        system = ClaudeFlowSystem(claude_flow_config)
        await system.initialize()
        yield system
        await system.shutdown()
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_complete_project_lifecycle(self, claude_flow_system):
        """Test complete project from creation to delivery."""
        # Mock Claude API for controlled responses
        with patch.object(claude_flow_system.claude_client, 'chat') as mock_chat:
            # Mock different responses for different stages
            def mock_response(messages, **kwargs):
                if "architecture" in str(messages).lower():
                    return AsyncMock(
                        content="## Architecture Design\\n\\n### Components\\n- API Gateway\\n- User Service\\n- Database Layer",
                        usage={'total_tokens': 200}
                    )
                elif "implement" in str(messages).lower():
                    return AsyncMock(
                        content="```python\\nclass UserService:\\n    def create_user(self, data):\\n        pass\\n```",
                        usage={'total_tokens': 150}
                    )
                elif "test" in str(messages).lower():
                    return AsyncMock(
                        content="```python\\ndef test_create_user():\\n    assert user_service.create_user({}) is not None\\n```",
                        usage={'total_tokens': 100}
                    )
                else:
                    return AsyncMock(
                        content="Task completed successfully",
                        usage={'total_tokens': 50}
                    )
            
            mock_chat.side_effect = mock_response
            
            # Submit project request
            project_request = {
                "name": "E2E User Management System",
                "description": "Complete user management with authentication and CRUD operations",
                "requirements": [
                    "Design system architecture",
                    "Implement user registration",
                    "Add authentication system",
                    "Create user profile management",
                    "Write comprehensive tests",
                    "Generate documentation"
                ],
                "constraints": {
                    "technology": "Python/FastAPI",
                    "database": "PostgreSQL",
                    "timeline": "1 week"
                }
            }
            
            # Execute project through orchestrator
            result = await claude_flow_system.orchestrator.execute_project(project_request)
            
            # Verify project execution
            assert result is not None
            assert "project_id" in result
            assert result.get("status") in ["completed", "in_progress", "partially_completed"]
            
            # Verify tasks were created and assigned
            assert "tasks" in result
            assert len(result["tasks"]) > 0
            
            # Verify different types of tasks were generated
            task_types = {task.get("type") for task in result["tasks"]}
            expected_types = {"architecture", "implementation", "testing", "documentation"}
            assert len(task_types.intersection(expected_types)) > 0
            
            # Verify project artifacts were stored in memory
            project_memories = await claude_flow_system.memory_manager.search(
                query=f"project {result['project_id']}",
                limit=10
            )
            assert len(project_memories) > 0
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_collaborative_debugging_workflow(self, claude_flow_system):
        """Test collaborative debugging workflow."""
        with patch.object(claude_flow_system.claude_client, 'chat') as mock_chat:
            # Mock debugging responses
            mock_chat.return_value = AsyncMock(
                content="## Bug Analysis\\n\\nIssue: Null pointer exception\\nCause: Missing validation\\nSolution: Add input validation",
                usage={'total_tokens': 120}
            )
            
            # Submit bug report
            bug_report = {
                "title": "User registration fails with null pointer exception",
                "description": "Users cannot register when email field is empty",
                "severity": "high",
                "logs": "NullPointerException at line 42 in UserService.java",
                "reproduction_steps": [
                    "Navigate to registration page",
                    "Leave email field empty",
                    "Click submit button"
                ]
            }
            
            # Process through debugging workflow
            debug_result = await claude_flow_system.orchestrator.process_bug_report(bug_report)
            
            assert debug_result is not None
            assert "analysis" in debug_result
            assert "solution" in debug_result
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_code_review_workflow(self, claude_flow_system):
        """Test collaborative code review workflow."""
        with patch.object(claude_flow_system.claude_client, 'chat') as mock_chat:
            mock_chat.return_value = AsyncMock(
                content="## Code Review\\n\\n### Issues Found\\n- Missing error handling\\n- Inefficient database queries\\n\\n### Recommendations\\n- Add try-catch blocks\\n- Use batch queries",
                usage={'total_tokens': 180}
            )
            
            # Submit code for review
            code_submission = {
                "files": [
                    {
                        "path": "src/user_service.py",
                        "content": "class UserService:\\n    def get_users(self):\\n        return db.query('SELECT * FROM users')",
                        "changes": "Added user retrieval method"
                    }
                ],
                "description": "Implement user retrieval functionality",
                "reviewer_preferences": ["security", "performance", "maintainability"]
            }
            
            # Process code review
            review_result = await claude_flow_system.orchestrator.process_code_review(code_submission)
            
            assert review_result is not None
            assert "feedback" in review_result
            assert "recommendations" in review_result
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_learning_and_adaptation_workflow(self, claude_flow_system):
        """Test system learning and adaptation over multiple projects."""
        projects = [
            {
                "name": "Project Alpha - REST API",
                "type": "api_development",
                "requirements": ["REST endpoints", "authentication", "validation"]
            },
            {
                "name": "Project Beta - Web Dashboard", 
                "type": "frontend_development",
                "requirements": ["user interface", "data visualization", "responsive design"]
            },
            {
                "name": "Project Gamma - Data Pipeline",
                "type": "data_processing",
                "requirements": ["ETL pipeline", "data validation", "monitoring"]
            }
        ]
        
        with patch.object(claude_flow_system.claude_client, 'chat') as mock_chat:
            mock_chat.return_value = AsyncMock(
                content="Project completed with best practices applied",
                usage={'total_tokens': 100}
            )
            
            project_results = []
            
            # Execute multiple projects
            for project in projects:
                result = await claude_flow_system.orchestrator.execute_project(project)
                project_results.append(result)
                
                # Add artificial delay to simulate time passing
                await asyncio.sleep(0.1)
            
            # Verify all projects completed
            assert len(project_results) == 3
            
            # Verify learning patterns were captured
            learning_memories = await claude_flow_system.memory_manager.search(
                query="project patterns best practices",
                tags=["learning", "patterns"],
                limit=20
            )
            
            # Should have captured patterns from multiple projects
            assert len(learning_memories) > 0
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_error_recovery_and_resilience(self, claude_flow_system):
        """Test system error recovery and resilience."""
        # Simulate various failure scenarios
        failure_scenarios = [
            {"type": "api_timeout", "description": "Claude API timeout"},
            {"type": "memory_error", "description": "Memory storage failure"},
            {"type": "agent_crash", "description": "Agent process crash"},
            {"type": "network_error", "description": "Network connectivity issue"}
        ]
        
        recovery_results = []
        
        for scenario in failure_scenarios:
            try:
                # Simulate the failure based on type
                if scenario["type"] == "api_timeout":
                    with patch.object(claude_flow_system.claude_client, 'chat') as mock_chat:
                        mock_chat.side_effect = asyncio.TimeoutError("API timeout")
                        
                        # Submit simple task that should trigger retry logic
                        task = {"description": "Simple test task", "type": "analysis"}
                        result = await claude_flow_system.orchestrator.process_simple_task(task)
                        recovery_results.append({"scenario": scenario["type"], "recovered": True})
                
                elif scenario["type"] == "memory_error":
                    # Simulate memory error and recovery
                    with patch.object(claude_flow_system.memory_manager, 'store') as mock_store:
                        mock_store.side_effect = Exception("Memory storage failed")
                        
                        # Try to store data and verify graceful handling
                        try:
                            await claude_flow_system.memory_manager.store("test_key", {"data": "test"})
                        except Exception:
                            pass  # Expected to fail
                        
                        recovery_results.append({"scenario": scenario["type"], "recovered": True})
                
            except Exception as e:
                # Log the error but continue testing other scenarios
                recovery_results.append({"scenario": scenario["type"], "recovered": False, "error": str(e)})
        
        # Verify system maintained some level of functionality
        assert len(recovery_results) == len(failure_scenarios)
        
        # At least some scenarios should show recovery capability
        recovered_count = sum(1 for r in recovery_results if r.get("recovered", False))
        assert recovered_count > 0


class TestRealWorldScenarios:
    """Test real-world usage scenarios end-to-end."""
    
    @pytest.mark.e2e
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_microservices_development_scenario(self, claude_flow_system):
        """Test developing a complete microservices architecture."""
        microservices_project = {
            "name": "E-commerce Microservices Platform",
            "architecture": "microservices",
            "services": [
                {
                    "name": "user-service",
                    "responsibilities": ["user management", "authentication", "profiles"]
                },
                {
                    "name": "product-service", 
                    "responsibilities": ["product catalog", "inventory", "search"]
                },
                {
                    "name": "order-service",
                    "responsibilities": ["order processing", "payment", "fulfillment"]
                },
                {
                    "name": "notification-service",
                    "responsibilities": ["email", "SMS", "push notifications"]
                }
            ],
            "cross_cutting_concerns": [
                "API gateway",
                "Service discovery",
                "Configuration management",
                "Monitoring and logging",
                "Security"
            ]
        }
        
        with patch.object(claude_flow_system.claude_client, 'chat') as mock_chat:
            # Mock responses for different architectural components
            def microservices_mock(messages, **kwargs):
                message_text = str(messages).lower()
                if "architecture" in message_text or "design" in message_text:
                    return AsyncMock(
                        content="## Microservices Architecture\\n\\n### Service Design\\n- Each service is independently deployable\\n- API-first approach\\n- Event-driven communication",
                        usage={'total_tokens': 250}
                    )
                elif "user-service" in message_text:
                    return AsyncMock(
                        content="## User Service Implementation\\n\\n```python\\nfrom fastapi import FastAPI\\napp = FastAPI()\\n\\n@app.post('/users')\\ndef create_user(user_data):\\n    pass\\n```",
                        usage={'total_tokens': 200}
                    )
                elif "api gateway" in message_text:
                    return AsyncMock(
                        content="## API Gateway Configuration\\n\\n### Routing Rules\\n- /api/users/* -> user-service\\n- /api/products/* -> product-service\\n- /api/orders/* -> order-service",
                        usage={'total_tokens': 180}
                    )
                else:
                    return AsyncMock(content="Implementation completed", usage={'total_tokens': 100})
            
            mock_chat.side_effect = microservices_mock
            
            # Execute microservices development
            result = await claude_flow_system.orchestrator.execute_project(microservices_project)
            
            assert result is not None
            assert result.get("status") in ["completed", "in_progress"]
            
            # Verify service-specific tasks were created
            tasks = result.get("tasks", [])
            service_tasks = [t for t in tasks if any(service["name"] in t.get("description", "") for service in microservices_project["services"])]
            assert len(service_tasks) > 0
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_legacy_system_modernization_scenario(self, claude_flow_system):
        """Test modernizing a legacy system."""
        modernization_project = {
            "name": "Legacy System Modernization",
            "current_system": {
                "technology": "COBOL mainframe",
                "database": "DB2",
                "interfaces": "batch processing",
                "challenges": ["scalability", "maintenance", "integration"]
            },
            "target_system": {
                "technology": "Python microservices",
                "database": "PostgreSQL",
                "interfaces": "REST APIs",
                "deployment": "containerized"
            },
            "migration_strategy": "strangler fig pattern",
            "phases": [
                "assessment and planning",
                "API layer implementation", 
                "data migration",
                "service extraction",
                "testing and validation",
                "cutover planning"
            ]
        }
        
        with patch.object(claude_flow_system.claude_client, 'chat') as mock_chat:
            mock_chat.return_value = AsyncMock(
                content="## Modernization Plan\\n\\n### Phase 1: Assessment\\n- Code analysis complete\\n- Dependencies mapped\\n\\n### Phase 2: API Layer\\n- REST API wrapper implemented\\n- Legacy integration points identified",
                usage={'total_tokens': 300}
            )
            
            result = await claude_flow_system.orchestrator.execute_project(modernization_project)
            
            assert result is not None
            
            # Verify modernization-specific concerns were addressed
            tasks = result.get("tasks", [])
            modernization_keywords = ["migration", "legacy", "api", "modernization"]
            relevant_tasks = [
                t for t in tasks 
                if any(keyword in t.get("description", "").lower() for keyword in modernization_keywords)
            ]
            assert len(relevant_tasks) > 0
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_ai_ml_pipeline_development_scenario(self, claude_flow_system):
        """Test developing an AI/ML pipeline."""
        ml_project = {
            "name": "Customer Churn Prediction Pipeline",
            "type": "machine_learning",
            "data_sources": [
                "customer database",
                "transaction logs", 
                "support tickets",
                "product usage analytics"
            ],
            "pipeline_stages": [
                "data ingestion",
                "data preprocessing",
                "feature engineering",
                "model training",
                "model evaluation",
                "deployment",
                "monitoring"
            ],
            "models": ["random forest", "gradient boosting", "neural network"],
            "deployment_target": "cloud API endpoint"
        }
        
        with patch.object(claude_flow_system.claude_client, 'chat') as mock_chat:
            mock_chat.return_value = AsyncMock(
                content="## ML Pipeline Design\\n\\n### Data Pipeline\\n- ETL process for data ingestion\\n- Feature store for reusable features\\n\\n### Model Pipeline\\n- Automated training and evaluation\\n- A/B testing framework\\n- Model versioning",
                usage={'total_tokens': 280}
            )
            
            result = await claude_flow_system.orchestrator.execute_project(ml_project)
            
            assert result is not None
            
            # Verify ML-specific tasks were generated
            tasks = result.get("tasks", [])
            ml_keywords = ["data", "model", "training", "evaluation", "pipeline"]
            ml_tasks = [
                t for t in tasks
                if any(keyword in t.get("description", "").lower() for keyword in ml_keywords)
            ]
            assert len(ml_tasks) > 0


@pytest.mark.e2e
@pytest.mark.slow
class TestPerformanceAndScalability:
    """Test system performance and scalability end-to-end."""
    
    @pytest.mark.asyncio
    async def test_high_throughput_scenario(self, claude_flow_system):
        """Test system behavior under high throughput."""
        # Submit many small tasks concurrently
        tasks = []
        for i in range(20):
            task = {
                "name": f"High Throughput Task {i}",
                "type": "simple_analysis",
                "description": f"Analyze data set {i}"
            }
            tasks.append(task)
        
        with patch.object(claude_flow_system.claude_client, 'chat') as mock_chat:
            mock_chat.return_value = AsyncMock(
                content="Analysis completed successfully",
                usage={'total_tokens': 50}
            )
            
            import time
            start_time = time.time()
            
            # Process all tasks concurrently
            results = await asyncio.gather(*[
                claude_flow_system.orchestrator.process_simple_task(task)
                for task in tasks
            ], return_exceptions=True)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Verify performance
            successful_results = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_results) >= 15  # At least 75% success rate
            assert processing_time < 10.0  # Should complete within 10 seconds
    
    @pytest.mark.asyncio
    async def test_memory_efficiency_scenario(self, claude_flow_system):
        """Test memory efficiency with large datasets."""
        # Simulate processing large amounts of data
        large_datasets = []
        for i in range(10):
            dataset = {
                "name": f"Large Dataset {i}",
                "size": "100MB",
                "records": 1000000,
                "processing_requirements": ["aggregation", "filtering", "transformation"]
            }
            large_datasets.append(dataset)
        
        with patch.object(claude_flow_system.claude_client, 'chat') as mock_chat:
            mock_chat.return_value = AsyncMock(
                content="Large dataset processed successfully with optimized memory usage",
                usage={'total_tokens': 200}
            )
            
            # Process datasets sequentially to test memory management
            for dataset in large_datasets:
                result = await claude_flow_system.orchestrator.process_data_task(dataset)
                
                # Verify system remains responsive
                assert result is not None
                
                # Small delay to allow garbage collection
                await asyncio.sleep(0.05)
            
            # System should still be responsive after processing large datasets
            health_check = await claude_flow_system.health_check()
            assert health_check.get("status") == "healthy"