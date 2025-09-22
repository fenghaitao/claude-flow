"""
Coder Agent Implementation for Claude-Flow

The Coder Agent specializes in software development, code implementation,
debugging, and code quality assurance across multiple programming languages.
"""

import logging
import re
from typing import Any, Dict, List, Optional
from datetime import datetime

from .base_worker import BaseWorkerAgent
from ..interfaces import TaskDefinition, TaskResult, AgentConfig, AgentType, AgentCapability

logger = logging.getLogger(__name__)


class CoderAgent(BaseWorkerAgent):
    """
    Coder Agent - Specialized in software development and implementation
    
    Capabilities:
    - Code implementation
    - Bug fixing and debugging
    - Code refactoring
    - Code review
    - Testing implementation
    - Documentation generation
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        base_config = config or AgentConfig(
            name="Coder Agent",
            agent_type=AgentType.CODER,
            capabilities=[
                AgentCapability(name="python_development", level=9, domain="coding"),
                AgentCapability(name="javascript_development", level=8, domain="coding"),
                AgentCapability(name="typescript_development", level=8, domain="coding"),
                AgentCapability(name="java_development", level=7, domain="coding"),
                AgentCapability(name="go_development", level=7, domain="coding"),
                AgentCapability(name="rust_development", level=6, domain="coding"),
                AgentCapability(name="debugging", level=9, domain="coding"),
                AgentCapability(name="refactoring", level=8, domain="coding"),
                AgentCapability(name="code_review", level=8, domain="quality"),
                AgentCapability(name="testing", level=7, domain="testing"),
                AgentCapability(name="documentation", level=7, domain="documentation")
            ]
        )
        super().__init__(base_config)
        
        # Coder-specific configuration
        self.specialization = "coding"
        self.preferred_task_types = ["coding", "implementation", "debugging", "refactoring", "testing"]
        self.skill_level_mapping = {
            "python": 0.9,
            "javascript": 0.8,
            "typescript": 0.8,
            "java": 0.7,
            "go": 0.7,
            "rust": 0.6,
            "c++": 0.6,
            "debugging": 0.9,
            "refactoring": 0.8,
            "testing": 0.7,
            "web_development": 0.8,
            "api_development": 0.8,
            "database": 0.7,
            "algorithms": 0.8,
            "data_structures": 0.8
        }
        
        # Programming languages and frameworks knowledge
        self.language_expertise = {
            "python": {
                "frameworks": ["django", "flask", "fastapi", "pandas", "numpy", "asyncio"],
                "testing": ["pytest", "unittest", "mock"],
                "tools": ["black", "pylint", "mypy", "poetry"]
            },
            "javascript": {
                "frameworks": ["react", "vue", "node.js", "express", "next.js"],
                "testing": ["jest", "mocha", "cypress"],
                "tools": ["eslint", "prettier", "webpack", "babel"]
            },
            "typescript": {
                "frameworks": ["react", "node.js", "next.js", "nestjs"],
                "testing": ["jest", "@testing-library"],
                "tools": ["tsc", "eslint", "prettier"]
            },
            "java": {
                "frameworks": ["spring", "spring_boot", "hibernate"],
                "testing": ["junit", "mockito"],
                "tools": ["maven", "gradle", "checkstyle"]
            }
        }
        
        # Code patterns and best practices
        self.design_patterns = {
            "singleton": {"use_case": "single_instance", "language_specific": True},
            "factory": {"use_case": "object_creation", "language_specific": False},
            "observer": {"use_case": "event_handling", "language_specific": False},
            "strategy": {"use_case": "algorithm_selection", "language_specific": False},
            "decorator": {"use_case": "behavior_extension", "language_specific": True}
        }
        
        # Code quality metrics
        self.code_quality_standards = {
            "complexity": {"max_cyclomatic": 10, "max_nesting": 4},
            "length": {"max_function_lines": 50, "max_class_lines": 500},
            "naming": {"snake_case": ["python"], "camelCase": ["javascript", "typescript", "java"]},
            "documentation": {"min_coverage": 0.8, "required_docstrings": True}
        }
        
        # Learning patterns for coding decisions
        self.coding_decisions: List[Dict[str, Any]] = []
    
    async def _execute_specialized_task(self, task: TaskDefinition) -> TaskResult:
        """Execute coding-specific tasks"""
        try:
            task_type = task.requirements.get("type", "coding")
            language = task.requirements.get("language", "python")
            
            # Route to appropriate coding method
            if task_type == "implementation" or task_type == "coding":
                result_data = await self._implement_code(task, language)
            elif task_type == "debugging":
                result_data = await self._debug_code(task, language)
            elif task_type == "refactoring":
                result_data = await self._refactor_code(task, language)
            elif task_type == "review":
                result_data = await self._review_code(task, language)
            elif task_type == "testing":
                result_data = await self._implement_tests(task, language)
            elif task_type == "documentation":
                result_data = await self._generate_documentation(task, language)
            else:
                result_data = await self._handle_general_coding_task(task, language)
            
            return TaskResult(
                task_id=task.id,
                agent_id=self.id,
                success=True,
                result_data=result_data
            )
            
        except Exception as e:
            logger.error(f"Coder agent failed to execute task {task.id}: {e}")
            return TaskResult(
                task_id=task.id,
                agent_id=self.id,
                success=False,
                error_message=str(e)
            )
    
    async def _estimate_specialized_effort(self, task: TaskDefinition, base_estimate: int) -> int:
        """Estimate effort for coding tasks"""
        effort_multipliers = {
            "implementation": 1.2,
            "coding": 1.2,
            "debugging": 0.8,
            "refactoring": 1.0,
            "review": 0.6,
            "testing": 0.9,
            "documentation": 0.7
        }
        
        task_type = task.requirements.get("type", "coding")
        language = task.requirements.get("language", "python")
        
        # Base multiplier from task type
        multiplier = effort_multipliers.get(task_type, 1.0)
        
        # Adjust for language expertise
        language_skill = self.skill_level_mapping.get(language, 0.5)
        language_multiplier = 2.0 - language_skill  # Higher skill = lower effort
        multiplier *= language_multiplier
        
        # Adjust for complexity keywords in description
        description = task.description.lower()
        if any(word in description for word in ["complex", "advanced", "optimization"]):
            multiplier *= 1.5
        elif any(word in description for word in ["simple", "basic", "straightforward"]):
            multiplier *= 0.7
        
        # Adjust for specific technologies
        if any(tech in description for tech in ["algorithm", "data structure", "performance"]):
            multiplier *= 1.3
        
        return int(base_estimate * multiplier)
    
    async def _learn_specialized_patterns(self, task: TaskDefinition, result: TaskResult, learning_entry: Dict[str, Any]) -> None:
        """Learn coding-specific patterns"""
        # Record coding decision
        if result.success and result.result_data:
            decision = {
                "task_id": task.id,
                "language": task.requirements.get("language", "python"),
                "task_type": task.requirements.get("type", "coding"),
                "patterns_used": result.result_data.get("patterns_used", []),
                "frameworks_used": result.result_data.get("frameworks_used", []),
                "code_quality_score": result.result_data.get("quality_score", 0.0),
                "performance_metrics": result.result_data.get("performance_metrics", {}),
                "timestamp": datetime.now()
            }
            self.coding_decisions.append(decision)
            
            # Update language-specific skills
            language = task.requirements.get("language", "python")
            if language in self.skill_level_mapping:
                current_skill = self.skill_level_mapping[language]
                self.skill_level_mapping[language] = min(1.0, current_skill + 0.02)
        
        # Keep decision history manageable
        if len(self.coding_decisions) > 100:
            self.coding_decisions = self.coding_decisions[-100:]
    
    async def _implement_code(self, task: TaskDefinition, language: str) -> Dict[str, Any]:
        """Implement code based on requirements"""
        # Update progress
        await self.report_progress(task.id, 0.1)
        
        # Analyze implementation requirements
        requirements = await self._analyze_implementation_requirements(task, language)
        await self.report_progress(task.id, 0.2)
        
        # Design code structure
        code_structure = await self._design_code_structure(requirements, language)
        await self.report_progress(task.id, 0.4)
        
        # Generate code implementation
        implementation = await self._generate_code_implementation(code_structure, language)
        await self.report_progress(task.id, 0.7)
        
        # Apply quality checks
        quality_result = await self._apply_quality_checks(implementation, language)
        await self.report_progress(task.id, 0.9)
        
        # Generate documentation
        documentation = await self._generate_code_documentation(implementation, language)
        await self.report_progress(task.id, 1.0)
        
        return {
            "implementation": implementation,
            "language": language,
            "structure": code_structure,
            "quality_score": quality_result.get("score", 0.0),
            "quality_issues": quality_result.get("issues", []),
            "documentation": documentation,
            "patterns_used": code_structure.get("patterns", []),
            "frameworks_used": self._identify_frameworks(implementation, language),
            "estimated_complexity": self._estimate_code_complexity(implementation)
        }
    
    async def _debug_code(self, task: TaskDefinition, language: str) -> Dict[str, Any]:
        """Debug existing code"""
        await self.report_progress(task.id, 0.1)
        
        # Parse code and error information
        code_info = self._parse_debug_requirements(task.description)
        await self.report_progress(task.id, 0.3)
        
        # Analyze the issue
        issue_analysis = self._analyze_debug_issue(code_info, language)
        await self.report_progress(task.id, 0.6)
        
        # Propose solutions
        solutions = self._generate_debug_solutions(issue_analysis, language)
        await self.report_progress(task.id, 0.8)
        
        # Create fixed code
        fixed_code = self._apply_debug_fixes(code_info, solutions, language)
        await self.report_progress(task.id, 1.0)
        
        return {
            "original_issue": code_info.get("issue", "Unknown"),
            "issue_analysis": issue_analysis,
            "solutions": solutions,
            "fixed_code": fixed_code,
            "confidence": issue_analysis.get("confidence", 0.5),
            "test_recommendations": self._generate_test_recommendations(fixed_code, language)
        }
    
    async def _refactor_code(self, task: TaskDefinition, language: str) -> Dict[str, Any]:
        """Refactor existing code"""
        await self.report_progress(task.id, 0.1)
        
        # Parse code to refactor
        code_info = self._parse_refactor_requirements(task.description)
        await self.report_progress(task.id, 0.3)
        
        # Identify refactoring opportunities
        opportunities = self._identify_refactor_opportunities(code_info, language)
        await self.report_progress(task.id, 0.5)
        
        # Apply refactoring patterns
        refactored_code = self._apply_refactoring_patterns(code_info, opportunities, language)
        await self.report_progress(task.id, 0.8)
        
        # Validate refactoring
        validation = self._validate_refactoring(code_info, refactored_code, language)
        await self.report_progress(task.id, 1.0)
        
        return {
            "original_code": code_info.get("code", ""),
            "refactored_code": refactored_code,
            "refactoring_patterns": opportunities.get("patterns", []),
            "improvements": opportunities.get("improvements", []),
            "validation_results": validation,
            "quality_improvement": validation.get("quality_delta", 0.0)
        }
    
    async def _review_code(self, task: TaskDefinition, language: str) -> Dict[str, Any]:
        """Review code for quality and best practices"""
        await self.report_progress(task.id, 0.2)
        
        # Parse code to review
        code_info = self._parse_code_for_review(task.description)
        await self.report_progress(task.id, 0.4)
        
        # Apply review criteria
        review_results = self._apply_code_review_criteria(code_info, language)
        await self.report_progress(task.id, 0.7)
        
        # Generate feedback
        feedback = self._generate_code_review_feedback(review_results, language)
        await self.report_progress(task.id, 1.0)
        
        return {
            "review_score": review_results.get("overall_score", 0.0),
            "strengths": review_results.get("strengths", []),
            "issues": review_results.get("issues", []),
            "suggestions": feedback.get("suggestions", []),
            "best_practices": feedback.get("best_practices", []),
            "security_concerns": review_results.get("security_issues", [])
        }
    
    async def _implement_tests(self, task: TaskDefinition, language: str) -> Dict[str, Any]:
        """Implement tests for code"""
        await self.report_progress(task.id, 0.1)
        
        # Parse testing requirements
        test_requirements = self._parse_test_requirements(task.description, language)
        await self.report_progress(task.id, 0.3)
        
        # Design test structure
        test_structure = self._design_test_structure(test_requirements, language)
        await self.report_progress(task.id, 0.6)
        
        # Generate test implementation
        test_implementation = self._generate_test_implementation(test_structure, language)
        await self.report_progress(task.id, 0.9)
        
        # Create test documentation
        test_docs = self._create_test_documentation(test_implementation, language)
        await self.report_progress(task.id, 1.0)
        
        return {
            "test_implementation": test_implementation,
            "test_framework": test_requirements.get("framework"),
            "coverage_estimate": test_structure.get("coverage_estimate", 0.0),
            "test_types": test_structure.get("test_types", []),
            "documentation": test_docs
        }
    
    async def _generate_documentation(self, task: TaskDefinition, language: str) -> Dict[str, Any]:
        """Generate code documentation"""
        await self.report_progress(task.id, 0.2)
        
        # Parse code for documentation
        code_info = self._parse_code_for_documentation(task.description)
        await self.report_progress(task.id, 0.5)
        
        # Generate documentation
        documentation = self._create_comprehensive_documentation(code_info, language)
        await self.report_progress(task.id, 1.0)
        
        return {
            "documentation": documentation,
            "format": "markdown",
            "sections": ["overview", "api", "examples", "installation"],
            "completeness_score": 0.85
        }
    
    async def _handle_general_coding_task(self, task: TaskDefinition, language: str) -> Dict[str, Any]:
        """Handle general coding tasks"""
        await self.report_progress(task.id, 0.5)
        
        # Provide general coding guidance
        guidance = self._provide_coding_guidance(task.description, language)
        
        await self.report_progress(task.id, 1.0)
        
        return {
            "guidance": guidance,
            "best_practices": self._get_language_best_practices(language),
            "recommended_tools": self._get_recommended_tools(language)
        }
    
    # Helper methods for code implementation
    
    def _analyze_implementation_requirements(self, task: TaskDefinition, language: str) -> Dict[str, Any]:
        """Analyze what needs to be implemented"""
        description = task.description.lower()
        
        # Identify implementation scope
        scope = []
        if "function" in description or "method" in description:
            scope.append("function")
        if "class" in description:
            scope.append("class")
        if "module" in description:
            scope.append("module")
        if "api" in description:
            scope.append("api")
        
        # Identify functionality
        functionality = []
        if "crud" in description:
            functionality.extend(["create", "read", "update", "delete"])
        if "auth" in description:
            functionality.append("authentication")
        if "validate" in description:
            functionality.append("validation")
        if "process" in description:
            functionality.append("data_processing")
        
        return {
            "scope": scope,
            "functionality": functionality,
            "language": language,
            "complexity": self._estimate_implementation_complexity(description),
            "domain": task.requirements.get("domain", "general")
        }
    
    def _design_code_structure(self, requirements: Dict[str, Any], language: str) -> Dict[str, Any]:
        """Design the structure of code to implement"""
        scope = requirements.get("scope", [])
        functionality = requirements.get("functionality", [])
        
        structure = {
            "modules": [],
            "classes": [],
            "functions": [],
            "patterns": []
        }
        
        # Design based on scope
        if "module" in scope:
            structure["modules"].append("main_module")
        
        if "class" in scope:
            structure["classes"].append({
                "name": "MainClass",
                "methods": functionality,
                "patterns": ["single_responsibility"]
            })
        
        if "function" in scope:
            for func in functionality:
                structure["functions"].append({
                    "name": f"{func}_handler",
                    "purpose": func,
                    "parameters": self._infer_parameters(func)
                })
        
        # Suggest appropriate patterns
        if len(functionality) > 3:
            structure["patterns"].append("facade")
        if "authentication" in functionality:
            structure["patterns"].append("decorator")
        
        return structure
    
    def _generate_code_implementation(self, structure: Dict[str, Any], language: str) -> str:
        """Generate actual code implementation"""
        # This is a simplified implementation generator
        # In a real system, this would use templates and more sophisticated generation
        
        code_parts = []
        
        # Generate imports
        imports = self._generate_imports(structure, language)
        if imports:
            code_parts.append(imports)
        
        # Generate classes
        for class_info in structure.get("classes", []):
            class_code = self._generate_class_code(class_info, language)
            code_parts.append(class_code)
        
        # Generate functions
        for func_info in structure.get("functions", []):
            func_code = self._generate_function_code(func_info, language)
            code_parts.append(func_code)
        
        return "\n\n".join(code_parts)
    
    def _generate_imports(self, structure: Dict[str, Any], language: str) -> str:
        """Generate appropriate imports for the language"""
        if language == "python":
            return "from typing import Dict, List, Optional\nimport logging"
        elif language == "javascript":
            return "// Import statements would go here"
        elif language == "typescript":
            return "import { Dictionary, Array } from 'types';"
        else:
            return "// Language-specific imports"
    
    def _generate_class_code(self, class_info: Dict[str, Any], language: str) -> str:
        """Generate class code for specific language"""
        if language == "python":
            return f'''class {class_info["name"]}:
    """Generated class for {class_info["name"]}"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def process(self) -> Dict[str, Any]:
        """Main processing method"""
        return {{"status": "success", "data": "processed"}}'''
        
        elif language == "javascript":
            return f'''class {class_info["name"]} {{
    constructor() {{
        this.logger = console;
    }}
    
    process() {{
        return {{ status: "success", data: "processed" }};
    }}
}}'''
        
        else:
            return f"// {class_info['name']} class implementation for {language}"
    
    def _generate_function_code(self, func_info: Dict[str, Any], language: str) -> str:
        """Generate function code for specific language"""
        if language == "python":
            params = ", ".join(func_info.get("parameters", ["data"]))
            return f'''def {func_info["name"]}({params}) -> Dict[str, Any]:
    """
    {func_info["purpose"].title()} handler function
    """
    # Implementation for {func_info["purpose"]}
    return {{"status": "success", "result": "completed"}}'''
        
        elif language == "javascript":
            params = ", ".join(func_info.get("parameters", ["data"]))
            return f'''function {func_info["name"]}({params}) {{
    // Implementation for {func_info["purpose"]}
    return {{ status: "success", result: "completed" }};
}}'''
        
        else:
            return f"// {func_info['name']} function implementation for {language}"
    
    def _apply_quality_checks(self, code: str, language: str) -> Dict[str, Any]:
        """Apply code quality checks"""
        issues = []
        score = 1.0
        
        # Simple quality checks (in real implementation, use proper linters)
        if len(code.split('\n')) > 100:
            issues.append("Code might be too long, consider breaking into smaller functions")
            score -= 0.1
        
        if language == "python" and "import *" in code:
            issues.append("Avoid wildcard imports")
            score -= 0.1
        
        # Check for documentation
        if '"""' not in code and "'''" not in code:
            issues.append("Missing documentation strings")
            score -= 0.2
        
        return {
            "score": max(0.0, score),
            "issues": issues,
            "suggestions": ["Add more comprehensive error handling", "Consider adding type hints"]
        }
    
    def _generate_code_documentation(self, code: str, language: str) -> str:
        """Generate documentation for the code"""
        return f"""# Code Documentation

## Overview
Generated code implementation in {language}

## Usage
```{language}
{code[:200]}...
```

## Features
- Error handling
- Type safety
- Logging integration

## Installation
Follow standard {language} installation procedures.
"""
    
    def _identify_frameworks(self, code: str, language: str) -> List[str]:
        """Identify frameworks used in the code"""
        frameworks = []
        language_frameworks = self.language_expertise.get(language, {}).get("frameworks", [])
        
        for framework in language_frameworks:
            if framework in code.lower():
                frameworks.append(framework)
        
        return frameworks
    
    def _estimate_code_complexity(self, code: str) -> str:
        """Estimate code complexity"""
        lines = len(code.split('\n'))
        
        if lines < 50:
            return "low"
        elif lines < 200:
            return "medium"
        else:
            return "high"
    
    def _infer_parameters(self, functionality: str) -> List[str]:
        """Infer function parameters based on functionality"""
        param_mapping = {
            "create": ["data", "options"],
            "read": ["id", "filters"],
            "update": ["id", "data"],
            "delete": ["id"],
            "authentication": ["credentials"],
            "validation": ["input_data"],
            "data_processing": ["raw_data", "config"]
        }
        
        return param_mapping.get(functionality, ["input_data"])
    
    def _estimate_implementation_complexity(self, description: str) -> str:
        """Estimate implementation complexity from description"""
        complex_indicators = ["algorithm", "optimization", "performance", "concurrent", "distributed"]
        simple_indicators = ["simple", "basic", "straightforward", "wrapper"]
        
        if any(indicator in description for indicator in complex_indicators):
            return "high"
        elif any(indicator in description for indicator in simple_indicators):
            return "low"
        else:
            return "medium"
    
    def _provide_coding_guidance(self, description: str, language: str) -> str:
        """Provide general coding guidance"""
        guidance = f"""
For {language} development:

1. Follow language-specific style guides
2. Use appropriate design patterns
3. Implement proper error handling
4. Add comprehensive tests
5. Document your code

Specific to your task: {description[:100]}...
Consider using {language}-specific best practices and frameworks.
"""
        return guidance.strip()
    
    def _get_language_best_practices(self, language: str) -> List[str]:
        """Get best practices for specific language"""
        practices = {
            "python": [
                "Follow PEP 8 style guide",
                "Use type hints",
                "Implement proper exception handling",
                "Use list comprehensions appropriately",
                "Follow the Zen of Python"
            ],
            "javascript": [
                "Use const/let instead of var",
                "Implement proper error handling",
                "Use modern ES6+ features",
                "Follow functional programming principles",
                "Use strict mode"
            ],
            "typescript": [
                "Use strict type checking",
                "Define proper interfaces",
                "Use generics appropriately",
                "Implement proper error handling",
                "Use enum for constants"
            ]
        }
        
        return practices.get(language, ["Follow language conventions", "Write clean, readable code"])
    
    def _get_recommended_tools(self, language: str) -> List[str]:
        """Get recommended tools for language"""
        tools = self.language_expertise.get(language, {}).get("tools", [])
        return tools if tools else ["standard_linter", "formatter", "test_runner"]