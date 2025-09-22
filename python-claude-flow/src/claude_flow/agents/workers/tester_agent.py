"""
Tester Agent Implementation for Claude-Flow

The Tester Agent specializes in software testing, quality assurance,
test automation, and test strategy development.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from .base_worker import BaseWorkerAgent
from ..interfaces import TaskDefinition, TaskResult, AgentConfig, AgentType, AgentCapability

logger = logging.getLogger(__name__)


class TesterAgent(BaseWorkerAgent):
    """
    Tester Agent - Specialized in software testing and quality assurance
    
    Capabilities:
    - Unit test development
    - Integration testing
    - End-to-end testing
    - Performance testing
    - Security testing
    - Test automation
    - Test strategy planning
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        base_config = config or AgentConfig(
            name="Tester Agent",
            agent_type=AgentType.TESTER,
            capabilities=[
                AgentCapability(name="unit_testing", level=9, domain="testing"),
                AgentCapability(name="integration_testing", level=8, domain="testing"),
                AgentCapability(name="e2e_testing", level=8, domain="testing"),
                AgentCapability(name="performance_testing", level=7, domain="testing"),
                AgentCapability(name="security_testing", level=6, domain="testing"),
                AgentCapability(name="test_automation", level=9, domain="testing"),
                AgentCapability(name="test_strategy", level=8, domain="testing"),
                AgentCapability(name="bug_reporting", level=9, domain="testing"),
                AgentCapability(name="test_data_management", level=7, domain="testing"),
                AgentCapability(name="quality_assurance", level=8, domain="quality")
            ]
        )
        super().__init__(base_config)
        
        # Tester-specific configuration
        self.specialization = "testing"
        self.preferred_task_types = ["testing", "quality_assurance", "validation", "verification"]
        self.skill_level_mapping = {
            "unit_testing": 0.9,
            "integration_testing": 0.8,
            "e2e_testing": 0.8,
            "performance_testing": 0.7,
            "security_testing": 0.6,
            "api_testing": 0.8,
            "ui_testing": 0.7,
            "load_testing": 0.6,
            "test_automation": 0.9,
            "test_planning": 0.8,
            "bug_analysis": 0.9,
            "quality_metrics": 0.8
        }
        
        # Testing frameworks and tools knowledge
        self.testing_frameworks = {
            "python": {
                "unit": ["pytest", "unittest", "nose2"],
                "integration": ["pytest", "testcontainers"],
                "e2e": ["selenium", "playwright", "cypress"],
                "performance": ["locust", "pytest-benchmark"],
                "mocking": ["unittest.mock", "pytest-mock", "responses"]
            },
            "javascript": {
                "unit": ["jest", "mocha", "jasmine"],
                "integration": ["supertest", "jest"],
                "e2e": ["cypress", "playwright", "webdriver"],
                "performance": ["lighthouse", "k6"],
                "mocking": ["jest", "sinon", "nock"]
            },
            "java": {
                "unit": ["junit", "testng", "mockito"],
                "integration": ["spring-test", "testcontainers"],
                "e2e": ["selenium", "cucumber"],
                "performance": ["jmeter", "gatling"],
                "mocking": ["mockito", "powermock"]
            }
        }
        
        # Test types and strategies
        self.test_strategies = {
            "unit": {
                "coverage_target": 0.8,
                "focus": ["business_logic", "edge_cases", "error_handling"],
                "isolation": True
            },
            "integration": {
                "coverage_target": 0.6,
                "focus": ["component_interaction", "data_flow", "external_services"],
                "isolation": False
            },
            "e2e": {
                "coverage_target": 0.4,
                "focus": ["user_workflows", "critical_paths", "system_integration"],
                "isolation": False
            },
            "performance": {
                "metrics": ["response_time", "throughput", "resource_usage"],
                "thresholds": {"response_time": "< 2s", "throughput": "> 100 req/s"},
                "scenarios": ["normal_load", "peak_load", "stress_test"]
            }
        }
        
        # Quality metrics and standards
        self.quality_standards = {
            "code_coverage": {"minimum": 0.8, "target": 0.9},
            "test_coverage": {"unit": 0.8, "integration": 0.6, "e2e": 0.4},
            "defect_density": {"target": "< 1 defect per 1000 LOC"},
            "test_execution_time": {"unit": "< 5 min", "integration": "< 30 min", "e2e": "< 2 hours"}
        }
        
        # Learning patterns for testing decisions
        self.testing_decisions: List[Dict[str, Any]] = []
    
    async def _execute_specialized_task(self, task: TaskDefinition) -> TaskResult:
        """Execute testing-specific tasks"""
        try:
            task_type = task.requirements.get("type", "testing")
            test_level = task.requirements.get("test_level", "unit")
            language = task.requirements.get("language", "python")
            
            # Route to appropriate testing method
            if task_type == "test_development" or task_type == "testing":
                result_data = await self._develop_tests(task, test_level, language)
            elif task_type == "test_strategy":
                result_data = await self._create_test_strategy(task, language)
            elif task_type == "test_execution":
                result_data = await self._execute_tests(task, test_level, language)
            elif task_type == "quality_assessment":
                result_data = await self._assess_quality(task, language)
            elif task_type == "bug_analysis":
                result_data = await self._analyze_bugs(task, language)
            elif task_type == "test_automation":
                result_data = await self._implement_test_automation(task, language)
            else:
                result_data = await self._handle_general_testing_task(task, language)
            
            return TaskResult(
                task_id=task.id,
                agent_id=self.id,
                success=True,
                result_data=result_data
            )
            
        except Exception as e:
            logger.error(f"Tester agent failed to execute task {task.id}: {e}")
            return TaskResult(
                task_id=task.id,
                agent_id=self.id,
                success=False,
                error_message=str(e)
            )
    
    async def _estimate_specialized_effort(self, task: TaskDefinition, base_estimate: int) -> int:
        """Estimate effort for testing tasks"""
        effort_multipliers = {
            "test_development": 1.0,
            "testing": 1.0,
            "test_strategy": 0.8,
            "test_execution": 0.6,
            "quality_assessment": 0.7,
            "bug_analysis": 0.5,
            "test_automation": 1.3
        }
        
        task_type = task.requirements.get("type", "testing")
        test_level = task.requirements.get("test_level", "unit")
        
        # Base multiplier from task type
        multiplier = effort_multipliers.get(task_type, 1.0)
        
        # Adjust for test level complexity
        level_multipliers = {
            "unit": 1.0,
            "integration": 1.3,
            "e2e": 1.8,
            "performance": 1.5,
            "security": 1.4
        }
        multiplier *= level_multipliers.get(test_level, 1.0)
        
        # Adjust for complexity keywords
        description = task.description.lower()
        if any(word in description for word in ["complex", "comprehensive", "automation"]):
            multiplier *= 1.4
        elif any(word in description for word in ["simple", "basic", "manual"]):
            multiplier *= 0.8
        
        return int(base_estimate * multiplier)
    
    async def _learn_specialized_patterns(self, task: TaskDefinition, result: TaskResult, learning_entry: Dict[str, Any]) -> None:
        """Learn testing-specific patterns"""
        # Record testing decision
        if result.success and result.result_data:
            decision = {
                "task_id": task.id,
                "test_type": task.requirements.get("test_level", "unit"),
                "language": task.requirements.get("language", "python"),
                "frameworks_used": result.result_data.get("frameworks_used", []),
                "coverage_achieved": result.result_data.get("coverage", 0.0),
                "test_count": result.result_data.get("test_count", 0),
                "execution_time": result.result_data.get("execution_time", 0),
                "defects_found": result.result_data.get("defects_found", 0),
                "timestamp": datetime.now()
            }
            self.testing_decisions.append(decision)
            
            # Update skill levels based on performance
            test_type = task.requirements.get("test_level", "unit")
            if test_type in self.skill_level_mapping:
                current_skill = self.skill_level_mapping[test_type]
                # Improve skill based on coverage achieved
                coverage = result.result_data.get("coverage", 0.0)
                if coverage > 0.8:
                    self.skill_level_mapping[test_type] = min(1.0, current_skill + 0.03)
        
        # Keep decision history manageable
        if len(self.testing_decisions) > 100:
            self.testing_decisions = self.testing_decisions[-100:]
    
    async def _develop_tests(self, task: TaskDefinition, test_level: str, language: str) -> Dict[str, Any]:
        """Develop tests based on requirements"""
        # Update progress
        await self.report_progress(task.id, 0.1)
        
        # Analyze testing requirements
        requirements = await self._analyze_testing_requirements(task, test_level, language)
        await self.report_progress(task.id, 0.2)
        
        # Design test structure
        test_structure = await self._design_test_structure(requirements, test_level, language)
        await self.report_progress(task.id, 0.4)
        
        # Generate test implementation
        test_implementation = await self._generate_test_implementation(test_structure, test_level, language)
        await self.report_progress(task.id, 0.7)
        
        # Create test data and fixtures
        test_data = await self._create_test_data(test_structure, test_level)
        await self.report_progress(task.id, 0.9)
        
        # Generate test documentation
        documentation = await self._generate_test_documentation(test_implementation, test_level)
        await self.report_progress(task.id, 1.0)
        
        return {
            "test_implementation": test_implementation,
            "test_structure": test_structure,
            "test_data": test_data,
            "documentation": documentation,
            "frameworks_used": self._identify_frameworks_used(test_structure, language),
            "estimated_coverage": test_structure.get("coverage_estimate", 0.0),
            "test_count": len(test_structure.get("test_cases", [])),
            "execution_strategy": self._create_execution_strategy(test_level)
        }
    
    async def _create_test_strategy(self, task: TaskDefinition, language: str) -> Dict[str, Any]:
        """Create comprehensive test strategy"""
        await self.report_progress(task.id, 0.1)
        
        # Analyze project requirements
        project_analysis = self._analyze_project_for_testing(task.description)
        await self.report_progress(task.id, 0.3)
        
        # Define test levels and types
        test_pyramid = self._design_test_pyramid(project_analysis)
        await self.report_progress(task.id, 0.5)
        
        # Create execution plan
        execution_plan = self._create_test_execution_plan(test_pyramid, language)
        await self.report_progress(task.id, 0.7)
        
        # Define quality gates
        quality_gates = self._define_quality_gates(project_analysis)
        await self.report_progress(task.id, 0.9)
        
        # Create risk assessment
        risk_assessment = self._assess_testing_risks(project_analysis)
        await self.report_progress(task.id, 1.0)
        
        return {
            "test_strategy": {
                "test_pyramid": test_pyramid,
                "execution_plan": execution_plan,
                "quality_gates": quality_gates,
                "risk_assessment": risk_assessment
            },
            "recommended_tools": self._recommend_testing_tools(language, project_analysis),
            "timeline_estimate": self._estimate_testing_timeline(test_pyramid),
            "resource_requirements": self._estimate_testing_resources(test_pyramid)
        }
    
    async def _execute_tests(self, task: TaskDefinition, test_level: str, language: str) -> Dict[str, Any]:
        """Execute existing tests"""
        await self.report_progress(task.id, 0.2)
        
        # Parse test execution requirements
        execution_config = self._parse_execution_requirements(task.description)
        await self.report_progress(task.id, 0.4)
        
        # Simulate test execution (in real implementation, would actually run tests)
        execution_results = self._simulate_test_execution(execution_config, test_level)
        await self.report_progress(task.id, 0.8)
        
        # Generate execution report
        execution_report = self._generate_execution_report(execution_results)
        await self.report_progress(task.id, 1.0)
        
        return {
            "execution_results": execution_results,
            "execution_report": execution_report,
            "coverage": execution_results.get("coverage", 0.0),
            "passed_tests": execution_results.get("passed", 0),
            "failed_tests": execution_results.get("failed", 0),
            "execution_time": execution_results.get("execution_time", 0),
            "defects_found": len(execution_results.get("failures", []))
        }
    
    async def _assess_quality(self, task: TaskDefinition, language: str) -> Dict[str, Any]:
        """Assess code/system quality"""
        await self.report_progress(task.id, 0.2)
        
        # Analyze quality metrics
        quality_metrics = self._analyze_quality_metrics(task.description)
        await self.report_progress(task.id, 0.5)
        
        # Apply quality standards
        quality_assessment = self._apply_quality_standards(quality_metrics)
        await self.report_progress(task.id, 0.8)
        
        # Generate recommendations
        recommendations = self._generate_quality_recommendations(quality_assessment)
        await self.report_progress(task.id, 1.0)
        
        return {
            "quality_score": quality_assessment.get("overall_score", 0.0),
            "metrics": quality_metrics,
            "assessment": quality_assessment,
            "recommendations": recommendations,
            "quality_gates_passed": quality_assessment.get("gates_passed", []),
            "quality_gates_failed": quality_assessment.get("gates_failed", [])
        }
    
    async def _analyze_bugs(self, task: TaskDefinition, language: str) -> Dict[str, Any]:
        """Analyze bugs and defects"""
        await self.report_progress(task.id, 0.3)
        
        # Parse bug information
        bug_info = self._parse_bug_information(task.description)
        await self.report_progress(task.id, 0.6)
        
        # Analyze bug patterns
        bug_analysis = self._analyze_bug_patterns(bug_info, language)
        await self.report_progress(task.id, 0.9)
        
        # Generate bug report
        bug_report = self._generate_bug_report(bug_analysis)
        await self.report_progress(task.id, 1.0)
        
        return {
            "bug_analysis": bug_analysis,
            "bug_report": bug_report,
            "severity": bug_analysis.get("severity", "medium"),
            "category": bug_analysis.get("category", "functional"),
            "reproduction_steps": bug_analysis.get("reproduction_steps", []),
            "suggested_fixes": bug_analysis.get("suggested_fixes", [])
        }
    
    async def _implement_test_automation(self, task: TaskDefinition, language: str) -> Dict[str, Any]:
        """Implement test automation"""
        await self.report_progress(task.id, 0.1)
        
        # Design automation framework
        automation_framework = self._design_automation_framework(task.description, language)
        await self.report_progress(task.id, 0.3)
        
        # Generate automation scripts
        automation_scripts = self._generate_automation_scripts(automation_framework, language)
        await self.report_progress(task.id, 0.6)
        
        # Create CI/CD integration
        cicd_integration = self._create_cicd_integration(automation_framework)
        await self.report_progress(task.id, 0.8)
        
        # Generate automation documentation
        automation_docs = self._generate_automation_documentation(automation_framework)
        await self.report_progress(task.id, 1.0)
        
        return {
            "automation_framework": automation_framework,
            "automation_scripts": automation_scripts,
            "cicd_integration": cicd_integration,
            "documentation": automation_docs,
            "maintenance_guide": self._create_maintenance_guide(automation_framework)
        }
    
    async def _handle_general_testing_task(self, task: TaskDefinition, language: str) -> Dict[str, Any]:
        """Handle general testing tasks"""
        await self.report_progress(task.id, 0.5)
        
        # Provide general testing guidance
        guidance = self._provide_testing_guidance(task.description, language)
        
        await self.report_progress(task.id, 1.0)
        
        return {
            "guidance": guidance,
            "best_practices": self._get_testing_best_practices(),
            "recommended_tools": self._get_recommended_testing_tools(language)
        }
    
    # Helper methods for testing implementation
    
    def _analyze_testing_requirements(self, task: TaskDefinition, test_level: str, language: str) -> Dict[str, Any]:
        """Analyze what needs to be tested"""
        description = task.description.lower()
        
        # Identify test scope
        scope = []
        if "function" in description or "unit" in description:
            scope.append("functions")
        if "integration" in description or "api" in description:
            scope.append("integration")
        if "ui" in description or "frontend" in description:
            scope.append("ui")
        if "performance" in description:
            scope.append("performance")
        
        # Identify test scenarios
        scenarios = []
        if "happy path" in description or "positive" in description:
            scenarios.append("positive_cases")
        if "edge case" in description or "boundary" in description:
            scenarios.append("edge_cases")
        if "error" in description or "exception" in description:
            scenarios.append("error_handling")
        if "negative" in description:
            scenarios.append("negative_cases")
        
        return {
            "scope": scope,
            "scenarios": scenarios,
            "test_level": test_level,
            "language": language,
            "complexity": self._estimate_testing_complexity(description),
            "coverage_target": self.test_strategies.get(test_level, {}).get("coverage_target", 0.8)
        }
    
    def _design_test_structure(self, requirements: Dict[str, Any], test_level: str, language: str) -> Dict[str, Any]:
        """Design structure of tests"""
        scope = requirements.get("scope", [])
        scenarios = requirements.get("scenarios", [])
        coverage_target = requirements.get("coverage_target", 0.8)
        
        test_cases = []
        
        # Generate test cases based on scope and scenarios
        for scope_item in scope:
            for scenario in scenarios:
                test_cases.append({
                    "name": f"test_{scope_item}_{scenario}",
                    "scope": scope_item,
                    "scenario": scenario,
                    "priority": self._determine_test_priority(scope_item, scenario)
                })
        
        # If no specific test cases, create default ones
        if not test_cases:
            test_cases = [
                {"name": "test_positive_case", "scope": "general", "scenario": "positive", "priority": "high"},
                {"name": "test_edge_case", "scope": "general", "scenario": "edge", "priority": "medium"},
                {"name": "test_error_handling", "scope": "general", "scenario": "error", "priority": "high"}
            ]
        
        return {
            "test_cases": test_cases,
            "framework": self._select_testing_framework(test_level, language),
            "coverage_estimate": coverage_target,
            "test_structure": self._create_test_file_structure(test_cases, language),
            "dependencies": self._identify_test_dependencies(test_level, language)
        }
    
    def _generate_test_implementation(self, test_structure: Dict[str, Any], test_level: str, language: str) -> str:
        """Generate actual test implementation"""
        framework = test_structure.get("framework")
        test_cases = test_structure.get("test_cases", [])
        
        if language == "python" and framework == "pytest":
            return self._generate_pytest_implementation(test_cases)
        elif language == "javascript" and framework == "jest":
            return self._generate_jest_implementation(test_cases)
        else:
            return self._generate_generic_test_implementation(test_cases, language)
    
    def _generate_pytest_implementation(self, test_cases: List[Dict[str, Any]]) -> str:
        """Generate pytest implementation"""
        imports = "import pytest\nfrom unittest.mock import Mock, patch\n\n"
        
        test_methods = []
        for case in test_cases:
            test_method = f'''def {case["name"]}():
    """Test {case["scenario"]} for {case["scope"]}"""
    # Arrange
    test_data = {{"input": "test_value"}}
    
    # Act
    result = function_under_test(test_data)
    
    # Assert
    assert result is not None
    assert result["status"] == "success"'''
            test_methods.append(test_method)
        
        return imports + "\n\n".join(test_methods)
    
    def _generate_jest_implementation(self, test_cases: List[Dict[str, Any]]) -> str:
        """Generate Jest implementation"""
        imports = "const { jest } = require('@jest/globals');\n\n"
        
        test_methods = []
        for case in test_cases:
            test_method = f'''test('{case["name"]}', () => {{
    // Arrange
    const testData = {{ input: 'test_value' }};
    
    // Act
    const result = functionUnderTest(testData);
    
    // Assert
    expect(result).toBeDefined();
    expect(result.status).toBe('success');
}});'''
            test_methods.append(test_method)
        
        return imports + "\n\n".join(test_methods)
    
    def _generate_generic_test_implementation(self, test_cases: List[Dict[str, Any]], language: str) -> str:
        """Generate generic test implementation"""
        return f"// Generic test implementation for {language}\n// {len(test_cases)} test cases generated"
    
    def _select_testing_framework(self, test_level: str, language: str) -> str:
        """Select appropriate testing framework"""
        frameworks = self.testing_frameworks.get(language, {})
        level_frameworks = frameworks.get(test_level, frameworks.get("unit", ["default"]))
        return level_frameworks[0] if level_frameworks else "default"
    
    def _determine_test_priority(self, scope: str, scenario: str) -> str:
        """Determine test priority"""
        high_priority = ["functions", "integration", "positive", "error"]
        
        if scope in high_priority or scenario in high_priority:
            return "high"
        elif scenario == "edge":
            return "medium"
        else:
            return "low"
    
    def _estimate_testing_complexity(self, description: str) -> str:
        """Estimate testing complexity"""
        complex_indicators = ["performance", "integration", "e2e", "automation", "security"]
        simple_indicators = ["unit", "basic", "simple"]
        
        if any(indicator in description for indicator in complex_indicators):
            return "high"
        elif any(indicator in description for indicator in simple_indicators):
            return "low"
        else:
            return "medium"
    
    def _provide_testing_guidance(self, description: str, language: str) -> str:
        """Provide general testing guidance"""
        return f"""
Testing Guidance for {language}:

1. Follow the testing pyramid principle
2. Aim for high test coverage (>80% for units)
3. Write clear, maintainable test cases
4. Use appropriate mocking and stubbing
5. Implement continuous testing in CI/CD

For your specific task: {description[:100]}...
Consider using {language}-specific testing frameworks and best practices.
"""
    
    def _get_testing_best_practices(self) -> List[str]:
        """Get general testing best practices"""
        return [
            "Write tests before fixing bugs (TDD)",
            "Keep tests independent and isolated",
            "Use descriptive test names",
            "Follow the AAA pattern (Arrange, Act, Assert)",
            "Test behavior, not implementation",
            "Maintain test code quality",
            "Use appropriate test data and fixtures",
            "Implement proper error handling in tests"
        ]
    
    def _get_recommended_testing_tools(self, language: str) -> List[str]:
        """Get recommended testing tools for language"""
        frameworks = self.testing_frameworks.get(language, {})
        all_tools = []
        
        for category, tools in frameworks.items():
            all_tools.extend(tools)
        
        return list(set(all_tools)) if all_tools else ["default_test_framework"]
    
    def _simulate_test_execution(self, config: Dict[str, Any], test_level: str) -> Dict[str, Any]:
        """Simulate test execution (placeholder for real execution)"""
        return {
            "total_tests": 25,
            "passed": 23,
            "failed": 2,
            "skipped": 0,
            "coverage": 0.85,
            "execution_time": 45.2,
            "failures": [
                {"test": "test_edge_case_1", "error": "AssertionError: Expected 'success' but got 'error'"},
                {"test": "test_integration_flow", "error": "ConnectionError: Unable to connect to test database"}
            ]
        }