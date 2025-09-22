"""
Architect Agent Implementation for Claude-Flow

The Architect Agent specializes in system design, architecture planning,
and high-level solution design across various domains.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from .base_worker import BaseWorkerAgent
from ..interfaces import TaskDefinition, TaskResult, AgentConfig, AgentType, AgentCapability

logger = logging.getLogger(__name__)


class ArchitectAgent(BaseWorkerAgent):
    """
    Architect Agent - Specialized in system design and architecture
    
    Capabilities:
    - System architecture design
    - Technology stack selection
    - Design pattern recommendation
    - Scalability planning
    - Integration design
    - Performance architecture
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        base_config = config or AgentConfig(
            name="Architect Agent",
            agent_type=AgentType.ARCHITECT,
            capabilities=[
                AgentCapability(name="system_design", level=9, domain="architecture"),
                AgentCapability(name="technology_selection", level=8, domain="architecture"),
                AgentCapability(name="design_patterns", level=9, domain="architecture"),
                AgentCapability(name="scalability_planning", level=8, domain="architecture"),
                AgentCapability(name="integration_design", level=7, domain="architecture"),
                AgentCapability(name="performance_architecture", level=8, domain="architecture"),
                AgentCapability(name="security_architecture", level=7, domain="security"),
                AgentCapability(name="data_architecture", level=7, domain="data")
            ]
        )
        super().__init__(base_config)
        
        # Architect-specific configuration
        self.specialization = "architecture"
        self.preferred_task_types = ["design", "architecture", "planning", "analysis"]
        self.skill_level_mapping = {
            "architecture": 0.9,
            "system_design": 0.9,
            "technology_planning": 0.8,
            "design_patterns": 0.9,
            "scalability": 0.8,
            "integration": 0.7,
            "performance": 0.8,
            "security": 0.7,
            "data_architecture": 0.7,
            "microservices": 0.8,
            "cloud_architecture": 0.7,
            "api_design": 0.8
        }
        
        # Architecture knowledge base
        self.design_patterns = {
            "creational": ["singleton", "factory", "builder", "prototype"],
            "structural": ["adapter", "decorator", "facade", "composite", "proxy"],
            "behavioral": ["observer", "strategy", "command", "chain_of_responsibility", "mediator"]
        }
        
        self.architectural_patterns = {
            "microservices": {"pros": ["scalability", "independence"], "cons": ["complexity", "overhead"]},
            "monolithic": {"pros": ["simplicity", "consistency"], "cons": ["scalability", "technology_lock"]},
            "serverless": {"pros": ["auto_scaling", "cost_efficiency"], "cons": ["cold_starts", "vendor_lock"]},
            "event_driven": {"pros": ["loose_coupling", "scalability"], "cons": ["complexity", "debugging"]},
            "layered": {"pros": ["separation", "maintainability"], "cons": ["performance", "rigidity"]}
        }
        
        self.technology_stacks = {
            "web_frontend": ["react", "vue", "angular", "svelte"],
            "web_backend": ["nodejs", "python", "java", "go", "rust"],
            "mobile": ["react_native", "flutter", "native_ios", "native_android"],
            "database": ["postgresql", "mongodb", "redis", "elasticsearch"],
            "cloud": ["aws", "azure", "gcp", "kubernetes", "docker"],
            "messaging": ["kafka", "rabbitmq", "redis_pub_sub", "sqs"]
        }
        
        # Learning patterns for architecture decisions
        self.architecture_decisions: List[Dict[str, Any]] = []
    
    async def _execute_specialized_task(self, task: TaskDefinition) -> TaskResult:
        """Execute architecture-specific tasks"""
        try:
            task_type = task.requirements.get("type", "design")
            domain = task.requirements.get("domain", "general")
            
            # Route to appropriate architecture method
            if task_type == "design" or domain == "architecture":
                result_data = await self._design_system_architecture(task)
            elif task_type == "analysis":
                result_data = await self._analyze_existing_architecture(task)
            elif task_type == "planning":
                result_data = await self._create_architecture_plan(task)
            elif task_type == "review":
                result_data = await self._review_architecture(task)
            else:
                result_data = await self._handle_general_architecture_task(task)
            
            return TaskResult(
                task_id=task.id,
                agent_id=self.id,
                success=True,
                result_data=result_data
            )
            
        except Exception as e:
            logger.error(f"Architect agent failed to execute task {task.id}: {e}")
            return TaskResult(
                task_id=task.id,
                agent_id=self.id,
                success=False,
                error_message=str(e)
            )
    
    async def _estimate_specialized_effort(self, task: TaskDefinition, base_estimate: int) -> int:
        """Estimate effort for architecture tasks"""
        effort_multipliers = {
            "system_design": 1.5,
            "architecture": 1.3,
            "planning": 1.2,
            "analysis": 1.0,
            "review": 0.8,
            "documentation": 0.9
        }
        
        task_type = task.requirements.get("type", "general")
        multiplier = effort_multipliers.get(task_type, 1.0)
        
        # Adjust for complexity keywords
        description = task.description.lower()
        if any(word in description for word in ["enterprise", "distributed", "microservices"]):
            multiplier *= 1.8
        elif any(word in description for word in ["cloud", "scalable", "high-availability"]):
            multiplier *= 1.5
        elif any(word in description for word in ["simple", "basic", "straightforward"]):
            multiplier *= 0.7
        
        return int(base_estimate * multiplier)
    
    async def _learn_specialized_patterns(self, task: TaskDefinition, result: TaskResult, learning_entry: Dict[str, Any]) -> None:
        """Learn architecture-specific patterns"""
        # Record architecture decision
        if result.success and result.result_data:
            decision = {
                "task_id": task.id,
                "architecture_type": result.result_data.get("architecture_type"),
                "technology_stack": result.result_data.get("technology_stack"),
                "design_patterns": result.result_data.get("design_patterns", []),
                "success_factors": result.result_data.get("success_factors", []),
                "timestamp": datetime.now()
            }
            self.architecture_decisions.append(decision)
            
            # Update domain knowledge based on success
            domain = task.requirements.get("domain", "general")
            if domain in self.skill_level_mapping:
                current_skill = self.skill_level_mapping[domain]
                self.skill_level_mapping[domain] = min(1.0, current_skill + 0.03)
        
        # Keep decision history manageable
        if len(self.architecture_decisions) > 50:
            self.architecture_decisions = self.architecture_decisions[-50:]
    
    async def _design_system_architecture(self, task: TaskDefinition) -> Dict[str, Any]:
        """Design system architecture based on requirements"""
        # Update progress
        await self.report_progress(task.id, 0.1)
        
        # Analyze requirements
        requirements = await self._analyze_requirements(task)
        await self.report_progress(task.id, 0.3)
        
        # Select architectural pattern
        architecture_pattern = await self._select_architecture_pattern(requirements)
        await self.report_progress(task.id, 0.5)
        
        # Choose technology stack
        technology_stack = await self._select_technology_stack(requirements)
        await self.report_progress(task.id, 0.7)
        
        # Design components and interactions
        component_design = await self._design_components(requirements, architecture_pattern)
        await self.report_progress(task.id, 0.9)
        
        # Create architecture documentation
        documentation = await self._create_architecture_documentation(
            requirements, architecture_pattern, technology_stack, component_design
        )
        await self.report_progress(task.id, 1.0)
        
        return {
            "architecture_type": architecture_pattern,
            "technology_stack": technology_stack,
            "component_design": component_design,
            "requirements_analysis": requirements,
            "documentation": documentation,
            "success_factors": ["scalability", "maintainability", "performance"],
            "design_rationale": self._create_design_rationale(architecture_pattern, technology_stack)
        }
    
    async def _analyze_existing_architecture(self, task: TaskDefinition) -> Dict[str, Any]:
        """Analyze existing system architecture"""
        await self.report_progress(task.id, 0.2)
        
        # Extract architecture information from task description
        system_info = self._extract_system_info(task.description)
        
        await self.report_progress(task.id, 0.5)
        
        # Identify architecture patterns
        identified_patterns = self._identify_architecture_patterns(system_info)
        
        await self.report_progress(task.id, 0.7)
        
        # Assess architecture quality
        quality_assessment = self._assess_architecture_quality(system_info)
        
        await self.report_progress(task.id, 0.9)
        
        # Generate recommendations
        recommendations = self._generate_architecture_recommendations(quality_assessment)
        
        await self.report_progress(task.id, 1.0)
        
        return {
            "system_analysis": system_info,
            "identified_patterns": identified_patterns,
            "quality_assessment": quality_assessment,
            "recommendations": recommendations,
            "improvement_areas": ["scalability", "maintainability", "performance"]
        }
    
    async def _create_architecture_plan(self, task: TaskDefinition) -> Dict[str, Any]:
        """Create detailed architecture implementation plan"""
        await self.report_progress(task.id, 0.1)
        
        # Parse planning requirements
        requirements = self._parse_planning_requirements(task.description)
        
        await self.report_progress(task.id, 0.3)
        
        # Create implementation phases
        phases = self._create_implementation_phases(requirements)
        
        await self.report_progress(task.id, 0.6)
        
        # Define milestones and deliverables
        milestones = self._define_milestones(phases)
        
        await self.report_progress(task.id, 0.8)
        
        # Estimate resources and timeline
        resource_estimates = self._estimate_resources(phases)
        
        await self.report_progress(task.id, 1.0)
        
        return {
            "implementation_phases": phases,
            "milestones": milestones,
            "resource_estimates": resource_estimates,
            "timeline": self._create_timeline(phases, milestones),
            "risk_assessment": self._assess_implementation_risks(phases)
        }
    
    async def _review_architecture(self, task: TaskDefinition) -> Dict[str, Any]:
        """Review and provide feedback on architecture"""
        await self.report_progress(task.id, 0.2)
        
        # Parse architecture to review
        architecture_details = self._parse_architecture_for_review(task.description)
        
        await self.report_progress(task.id, 0.5)
        
        # Apply architecture review criteria
        review_results = self._apply_review_criteria(architecture_details)
        
        await self.report_progress(task.id, 0.8)
        
        # Generate feedback and suggestions
        feedback = self._generate_architecture_feedback(review_results)
        
        await self.report_progress(task.id, 1.0)
        
        return {
            "review_results": review_results,
            "feedback": feedback,
            "score": review_results.get("overall_score", 0.0),
            "strengths": review_results.get("strengths", []),
            "weaknesses": review_results.get("weaknesses", []),
            "improvement_suggestions": feedback.get("improvements", [])
        }
    
    async def _handle_general_architecture_task(self, task: TaskDefinition) -> Dict[str, Any]:
        """Handle general architecture-related tasks"""
        await self.report_progress(task.id, 0.5)
        
        # Provide general architecture guidance
        guidance = self._provide_architecture_guidance(task.description)
        
        await self.report_progress(task.id, 1.0)
        
        return {
            "guidance": guidance,
            "recommendations": ["Follow SOLID principles", "Consider scalability", "Plan for maintainability"],
            "best_practices": self._get_relevant_best_practices(task.description)
        }
    
    # Helper methods for architecture design
    
    def _analyze_requirements(self, task: TaskDefinition) -> Dict[str, Any]:
        """Analyze system requirements"""
        description = task.description.lower()
        
        # Identify requirement categories
        functional_reqs = []
        non_functional_reqs = []
        
        # Parse functional requirements
        if "user" in description:
            functional_reqs.append("user_management")
        if "data" in description or "database" in description:
            functional_reqs.append("data_management")
        if "api" in description:
            functional_reqs.append("api_endpoints")
        if "auth" in description:
            functional_reqs.append("authentication")
        
        # Parse non-functional requirements
        if "scale" in description or "performance" in description:
            non_functional_reqs.append("scalability")
        if "secure" in description:
            non_functional_reqs.append("security")
        if "available" in description:
            non_functional_reqs.append("availability")
        if "maintain" in description:
            non_functional_reqs.append("maintainability")
        
        return {
            "functional_requirements": functional_reqs,
            "non_functional_requirements": non_functional_reqs,
            "complexity_level": self._assess_complexity(description),
            "domain": task.requirements.get("domain", "general")
        }
    
    def _select_architecture_pattern(self, requirements: Dict[str, Any]) -> str:
        """Select appropriate architectural pattern"""
        complexity = requirements.get("complexity_level", "medium")
        nfr = requirements.get("non_functional_requirements", [])
        
        # Decision logic for architecture pattern
        if "scalability" in nfr and complexity == "high":
            return "microservices"
        elif "scalability" in nfr and complexity == "medium":
            return "modular_monolith"
        elif complexity == "low":
            return "layered_monolith"
        elif "event_driven" in str(requirements):
            return "event_driven"
        else:
            return "layered_architecture"
    
    def _select_technology_stack(self, requirements: Dict[str, Any]) -> Dict[str, List[str]]:
        """Select appropriate technology stack"""
        domain = requirements.get("domain", "general")
        complexity = requirements.get("complexity_level", "medium")
        
        # Technology selection based on requirements
        if domain == "web":
            return {
                "frontend": ["react", "typescript", "next.js"],
                "backend": ["node.js", "express", "typescript"],
                "database": ["postgresql", "redis"],
                "infrastructure": ["docker", "kubernetes", "nginx"]
            }
        elif domain == "api":
            return {
                "backend": ["python", "fastapi", "pydantic"],
                "database": ["postgresql", "redis"],
                "infrastructure": ["docker", "nginx", "prometheus"]
            }
        else:
            return {
                "backend": ["python", "flask"],
                "database": ["sqlite", "postgresql"],
                "infrastructure": ["docker"]
            }
    
    def _design_components(self, requirements: Dict[str, Any], pattern: str) -> Dict[str, Any]:
        """Design system components"""
        components = {}
        
        if pattern == "microservices":
            components = {
                "api_gateway": {"responsibility": "routing", "interfaces": ["http", "websocket"]},
                "user_service": {"responsibility": "user_management", "interfaces": ["grpc", "rest"]},
                "data_service": {"responsibility": "data_processing", "interfaces": ["grpc"]},
                "notification_service": {"responsibility": "notifications", "interfaces": ["queue"]}
            }
        elif pattern == "layered_architecture":
            components = {
                "presentation_layer": {"responsibility": "ui_logic", "dependencies": ["business_layer"]},
                "business_layer": {"responsibility": "business_logic", "dependencies": ["data_layer"]},
                "data_layer": {"responsibility": "data_access", "dependencies": ["database"]}
            }
        else:
            components = {
                "controller": {"responsibility": "request_handling"},
                "service": {"responsibility": "business_logic"},
                "repository": {"responsibility": "data_access"}
            }
        
        return components
    
    def _create_architecture_documentation(self, requirements: Dict[str, Any], pattern: str, 
                                        tech_stack: Dict[str, List[str]], components: Dict[str, Any]) -> str:
        """Create architecture documentation"""
        doc = f"""
# System Architecture Documentation

## Overview
Architecture Pattern: {pattern}
Complexity Level: {requirements.get('complexity_level', 'medium')}

## Requirements
Functional: {', '.join(requirements.get('functional_requirements', []))}
Non-Functional: {', '.join(requirements.get('non_functional_requirements', []))}

## Technology Stack
{self._format_tech_stack(tech_stack)}

## Component Design
{self._format_components(components)}

## Design Decisions
- Pattern Selection: {pattern} chosen for {self._explain_pattern_choice(pattern)}
- Technology choices based on requirements and team expertise
- Component separation follows single responsibility principle
        """
        return doc.strip()
    
    def _format_tech_stack(self, tech_stack: Dict[str, List[str]]) -> str:
        """Format technology stack for documentation"""
        formatted = []
        for category, technologies in tech_stack.items():
            formatted.append(f"- {category.title()}: {', '.join(technologies)}")
        return '\n'.join(formatted)
    
    def _format_components(self, components: Dict[str, Any]) -> str:
        """Format components for documentation"""
        formatted = []
        for name, details in components.items():
            responsibility = details.get('responsibility', 'unknown')
            formatted.append(f"- {name}: {responsibility}")
        return '\n'.join(formatted)
    
    def _explain_pattern_choice(self, pattern: str) -> str:
        """Explain why a pattern was chosen"""
        explanations = {
            "microservices": "scalability and independent deployment requirements",
            "layered_architecture": "clear separation of concerns and maintainability",
            "event_driven": "loose coupling and asynchronous processing needs",
            "modular_monolith": "balance between simplicity and modularity"
        }
        return explanations.get(pattern, "project requirements")
    
    def _create_design_rationale(self, pattern: str, tech_stack: Dict[str, List[str]]) -> str:
        """Create design rationale"""
        return f"Selected {pattern} architecture with {tech_stack} for optimal balance of performance, scalability, and maintainability."
    
    # Additional helper methods for other architecture tasks
    
    def _extract_system_info(self, description: str) -> Dict[str, Any]:
        """Extract system information from description"""
        return {
            "components": ["extracted from description"],
            "technologies": ["identified technologies"],
            "patterns": ["identified patterns"]
        }
    
    def _identify_architecture_patterns(self, system_info: Dict[str, Any]) -> List[str]:
        """Identify architecture patterns in existing system"""
        return ["layered", "mvc"]  # Simplified identification
    
    def _assess_architecture_quality(self, system_info: Dict[str, Any]) -> Dict[str, Any]:
        """Assess architecture quality"""
        return {
            "overall_score": 0.75,
            "strengths": ["modularity", "separation_of_concerns"],
            "weaknesses": ["tight_coupling", "scalability_issues"],
            "maintainability": 0.8,
            "scalability": 0.6,
            "performance": 0.7
        }
    
    def _generate_architecture_recommendations(self, assessment: Dict[str, Any]) -> List[str]:
        """Generate architecture improvement recommendations"""
        recommendations = []
        
        if assessment.get("scalability", 0) < 0.7:
            recommendations.append("Consider microservices architecture for better scalability")
        
        if assessment.get("maintainability", 0) < 0.8:
            recommendations.append("Improve code modularity and separation of concerns")
        
        if "tight_coupling" in assessment.get("weaknesses", []):
            recommendations.append("Introduce dependency injection and interfaces")
        
        return recommendations
    
    def _assess_complexity(self, description: str) -> str:
        """Assess system complexity from description"""
        complex_indicators = ["distributed", "microservices", "enterprise", "scalable", "high-availability"]
        simple_indicators = ["simple", "basic", "small", "single"]
        
        if any(indicator in description for indicator in complex_indicators):
            return "high"
        elif any(indicator in description for indicator in simple_indicators):
            return "low"
        else:
            return "medium"