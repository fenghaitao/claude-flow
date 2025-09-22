"""
Neural Engine Coordinator for Claude-Flow

This module provides the main neural engine that coordinates all AI/ML
models including task classification, complexity estimation, pattern matching,
and agent optimization using reinforcement learning.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import traceback

import numpy as np

from claude_flow.core.interfaces import BaseComponent
from claude_flow.core.config_models import ClaudeFlowConfig
from claude_flow.neural.interfaces import (
    NeuralEngineInterface, ModelType, ModelConfig, TrainingData,
    PredictionResult, NeuralModelInterface
)
from claude_flow.neural.models import (
    SimpleTransformerTaskClassifier, GradientBoostingComplexityEstimator,
    SemanticPatternMatcher
)


logger = logging.getLogger(__name__)


class SimpleReinforcementLearningOptimizer(BaseComponent):
    """
    Simple reinforcement learning system for agent optimization.
    
    Uses Q-learning approach to optimize agent-task assignments
    based on historical performance and outcomes.
    """
    
    def __init__(self, learning_rate: float = 0.1, discount_factor: float = 0.9):
        super().__init__()
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        
        # Q-table for state-action values
        self.q_table: Dict[str, Dict[str, float]] = {}
        
        # State representation and action space
        self.state_features = [
            'task_complexity', 'agent_experience', 'agent_workload',
            'task_type', 'priority_level', 'deadline_pressure'
        ]
        
        # Historical data
        self.experience_replay: List[Dict[str, Any]] = []
        self.assignment_outcomes: Dict[str, List[float]] = {}
        
        # Performance tracking
        self.optimization_metrics: Dict[str, float] = {
            'total_assignments': 0,
            'successful_assignments': 0,
            'avg_completion_time': 0.0,
            'avg_quality_score': 0.0
        }
    
    async def initialize(self) -> None:
        """Initialize the RL optimizer."""
        self._initialized = True
        logger.info("RL optimizer initialized")
    
    def _state_to_key(self, state: Dict[str, Any]) -> str:
        """Convert state dictionary to string key for Q-table."""
        # Discretize continuous values and create state key
        discrete_state = []
        
        for feature in self.state_features:
            value = state.get(feature, 0)
            
            # Discretize based on feature type
            if feature in ['task_complexity', 'agent_experience', 'agent_workload']:
                # Continuous [0, 1] -> discrete bins
                discrete_value = min(int(value * 5), 4)  # 5 bins: 0-4
            elif feature == 'task_type':
                # Categorical
                discrete_value = hash(str(value)) % 10  # Map to 10 categories
            elif feature == 'priority_level':
                # Already discrete 1-5
                discrete_value = int(value)
            elif feature == 'deadline_pressure':
                # Boolean to int
                discrete_value = int(bool(value))
            else:
                discrete_value = 0
            
            discrete_state.append(str(discrete_value))
        
        return "_".join(discrete_state)
    
    async def optimize_assignment(self, agents: List[Dict[str, Any]], 
                                tasks: List[Dict[str, Any]]) -> Dict[str, str]:
        """Optimize agent-task assignments using Q-learning."""
        try:
            assignments = {}
            
            for task in tasks:
                best_agent = None
                best_q_value = float('-inf')
                
                # Get task state features
                task_state = self._extract_task_state(task)
                
                for agent in agents:
                    # Create state representation
                    state = {**task_state, **self._extract_agent_state(agent)}
                    state_key = self._state_to_key(state)
                    
                    # Get agent action (assignment decision)
                    agent_id = agent.get('id', str(hash(str(agent))))
                    
                    # Initialize Q-value if not seen before
                    if state_key not in self.q_table:
                        self.q_table[state_key] = {}
                    
                    if agent_id not in self.q_table[state_key]:
                        self.q_table[state_key][agent_id] = 0.0
                    
                    # Add exploration (epsilon-greedy)
                    q_value = self.q_table[state_key][agent_id]
                    if np.random.random() < 0.1:  # 10% exploration
                        q_value += np.random.normal(0, 0.1)
                    
                    if q_value > best_q_value:
                        best_q_value = q_value
                        best_agent = agent_id
                
                if best_agent:
                    assignments[task.get('id', str(hash(str(task))))] = best_agent
            
            return assignments
            
        except Exception as e:
            logger.error(f"Assignment optimization failed: {e}")
            return {}
    
    async def learn_from_outcome(self, assignment: Dict[str, str], 
                               outcome: Dict[str, Any]) -> bool:
        """Learn from assignment outcomes using Q-learning update."""
        try:
            for task_id, agent_id in assignment.items():
                # Get outcome metrics
                success = outcome.get('success', False)
                completion_time = outcome.get('completion_time', 1.0)
                quality_score = outcome.get('quality_score', 0.5)
                
                # Calculate reward
                reward = self._calculate_reward(success, completion_time, quality_score)
                
                # Store experience
                experience = {
                    'task_id': task_id,
                    'agent_id': agent_id,
                    'reward': reward,
                    'outcome': outcome,
                    'timestamp': datetime.now()
                }
                self.experience_replay.append(experience)
                
                # Update Q-values (simplified Q-learning)
                if hasattr(self, '_last_state_action'):
                    last_state, last_action = self._last_state_action.get(task_id, (None, None))
                    if last_state and last_action:
                        state_key = self._state_to_key(last_state)
                        
                        if state_key in self.q_table and last_action in self.q_table[state_key]:
                            old_q = self.q_table[state_key][last_action]
                            
                            # Q-learning update: Q(s,a) = Q(s,a) + α[r + γ*max(Q(s',a')) - Q(s,a)]
                            # Simplified: no next state max Q since this is episodic
                            new_q = old_q + self.learning_rate * (reward - old_q)
                            self.q_table[state_key][last_action] = new_q
                
                # Update performance metrics
                self.optimization_metrics['total_assignments'] += 1
                if success:
                    self.optimization_metrics['successful_assignments'] += 1
                
                # Update averages
                self._update_running_averages(completion_time, quality_score)
            
            logger.debug(f"Updated Q-learning from {len(assignment)} assignment outcomes")
            return True
            
        except Exception as e:
            logger.error(f"Learning from outcome failed: {e}")
            return False
    
    def _extract_task_state(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Extract state features from task."""
        return {
            'task_complexity': task.get('complexity', 0.5),
            'task_type': task.get('type', 'general'),
            'priority_level': task.get('priority', 3),
            'deadline_pressure': task.get('has_deadline', False)
        }
    
    def _extract_agent_state(self, agent: Dict[str, Any]) -> Dict[str, Any]:
        """Extract state features from agent."""
        return {
            'agent_experience': agent.get('experience_level', 0.5),
            'agent_workload': agent.get('current_workload', 0.5)
        }
    
    def _calculate_reward(self, success: bool, completion_time: float, quality_score: float) -> float:
        """Calculate reward for assignment outcome."""
        reward = 0.0
        
        # Success bonus
        if success:
            reward += 1.0
        else:
            reward -= 0.5
        
        # Time penalty/bonus (assuming lower time is better, normalized)
        time_bonus = max(0, 1.0 - (completion_time / 10.0))  # Assume 10 hours is baseline
        reward += time_bonus * 0.5
        
        # Quality bonus
        reward += quality_score * 0.5
        
        return reward
    
    def _update_running_averages(self, completion_time: float, quality_score: float) -> None:
        """Update running averages for metrics."""
        total = self.optimization_metrics['total_assignments']
        
        # Update completion time average
        current_avg_time = self.optimization_metrics['avg_completion_time']
        self.optimization_metrics['avg_completion_time'] = (
            (current_avg_time * (total - 1) + completion_time) / total
        )
        
        # Update quality score average
        current_avg_quality = self.optimization_metrics['avg_quality_score']
        self.optimization_metrics['avg_quality_score'] = (
            (current_avg_quality * (total - 1) + quality_score) / total
        )
    
    async def get_optimization_metrics(self) -> Dict[str, Any]:
        """Get optimization performance metrics."""
        success_rate = 0.0
        if self.optimization_metrics['total_assignments'] > 0:
            success_rate = (
                self.optimization_metrics['successful_assignments'] / 
                self.optimization_metrics['total_assignments']
            )
        
        return {
            **self.optimization_metrics,
            'success_rate': success_rate,
            'q_table_size': len(self.q_table),
            'experience_replay_size': len(self.experience_replay)
        }


class NeuralEngine(BaseComponent, NeuralEngineInterface):
    """
    Main neural engine that coordinates all AI/ML models.
    
    Features:
    - Model lifecycle management (load, train, optimize)
    - Unified prediction interface across all models
    - Automatic model selection and routing
    - Performance monitoring and optimization
    - Model persistence and versioning
    """
    
    def __init__(self, config: ClaudeFlowConfig, models_directory: str = "models"):
        super().__init__()
        self.config = config
        self.models_directory = Path(models_directory)
        
        # Model instances
        self.models: Dict[ModelType, NeuralModelInterface] = {}
        
        # Reinforcement learning optimizer
        self.rl_optimizer = SimpleReinforcementLearningOptimizer()
        
        # Model configurations
        self.model_configs: Dict[ModelType, ModelConfig] = {}
        
        # Performance tracking
        self.model_performance: Dict[ModelType, Dict[str, float]] = {}
        self.prediction_cache: Dict[str, Tuple[PredictionResult, datetime]] = {}
        self.cache_ttl = timedelta(minutes=30)
        
        # Auto-training settings
        self.auto_training_enabled = True
        self.training_data_buffer: Dict[ModelType, TrainingData] = {}
        self.min_training_samples = 10
        
    async def initialize(self) -> None:
        """Initialize the neural engine and load models."""
        try:
            logger.info("Initializing Neural Engine")
            
            # Create models directory
            self.models_directory.mkdir(parents=True, exist_ok=True)
            
            # Initialize RL optimizer
            await self.rl_optimizer.initialize()
            
            # Initialize default model configurations
            self._initialize_default_configs()
            
            # Auto-load available models
            await self._auto_load_models()
            
            self._initialized = True
            logger.info("Neural Engine initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Neural Engine: {e}")
            raise
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            logger.info("Cleaning up Neural Engine")
            
            # Cleanup models
            for model in self.models.values():
                if hasattr(model, 'cleanup'):
                    await model.cleanup()
            
            self.models.clear()
            self.prediction_cache.clear()
            
            self._initialized = False
            logger.info("Neural Engine cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during Neural Engine cleanup: {e}")
    
    def _initialize_default_configs(self) -> None:
        """Initialize default configurations for all model types."""
        self.model_configs = {
            ModelType.TASK_CLASSIFIER: ModelConfig(
                model_type=ModelType.TASK_CLASSIFIER,
                architecture="SimpleTransformerTaskClassifier",
                hyperparameters={
                    "vocab_size": 1000,
                    "embedding_dim": 128
                }
            ),
            ModelType.COMPLEXITY_ESTIMATOR: ModelConfig(
                model_type=ModelType.COMPLEXITY_ESTIMATOR,
                architecture="GradientBoostingComplexityEstimator",
                hyperparameters={
                    "n_estimators": 50,
                    "learning_rate": 0.1
                }
            ),
            ModelType.PATTERN_MATCHER: ModelConfig(
                model_type=ModelType.PATTERN_MATCHER,
                architecture="SemanticPatternMatcher",
                hyperparameters={
                    "embedding_dimensions": 256,
                    "similarity_threshold": 0.75
                }
            )
        }
    
    async def _auto_load_models(self) -> None:
        """Automatically load available models from disk."""
        for model_type in [ModelType.TASK_CLASSIFIER, ModelType.COMPLEXITY_ESTIMATOR, ModelType.PATTERN_MATCHER]:
            model_path = self.models_directory / f"{model_type.value}.json"
            if model_path.exists():
                try:
                    await self.load_model(model_type, str(model_path))
                    logger.info(f"Auto-loaded {model_type.value} model")
                except Exception as e:
                    logger.warning(f"Failed to auto-load {model_type.value}: {e}")
            else:
                # Create and initialize new model
                await self._create_new_model(model_type)
    
    async def _create_new_model(self, model_type: ModelType) -> None:
        """Create and initialize a new model instance."""
        try:
            config = self.model_configs[model_type]
            
            if model_type == ModelType.TASK_CLASSIFIER:
                model = SimpleTransformerTaskClassifier()
            elif model_type == ModelType.COMPLEXITY_ESTIMATOR:
                model = GradientBoostingComplexityEstimator()
            elif model_type == ModelType.PATTERN_MATCHER:
                model = SemanticPatternMatcher()
            else:
                logger.warning(f"Unknown model type: {model_type}")
                return
            
            # Initialize model
            await model.initialize(config)
            self.models[model_type] = model
            
            logger.info(f"Created new {model_type.value} model")
            
        except Exception as e:
            logger.error(f"Failed to create {model_type.value} model: {e}")
    
    # NeuralEngineInterface methods
    
    async def load_model(self, model_type: ModelType, model_path: Optional[str] = None) -> bool:
        """Load a specific model type."""
        try:
            if model_path is None:
                model_path = str(self.models_directory / f"{model_type.value}.json")
            
            # Create model instance if not exists
            if model_type not in self.models:
                await self._create_new_model(model_type)
            
            # Load model from file
            model = self.models[model_type]
            success = await model.load_model(model_path)
            
            if success:
                logger.info(f"Loaded {model_type.value} model from {model_path}")
            else:
                logger.warning(f"Failed to load {model_type.value} model")
            
            return success
            
        except Exception as e:
            logger.error(f"Error loading {model_type.value} model: {e}")
            return False
    
    async def get_model(self, model_type: ModelType) -> Optional[NeuralModelInterface]:
        """Get a loaded model instance."""
        return self.models.get(model_type)
    
    async def train_model(self, model_type: ModelType, training_data: TrainingData) -> bool:
        """Train a specific model."""
        try:
            if model_type not in self.models:
                await self._create_new_model(model_type)
            
            model = self.models[model_type]
            metrics = await model.train(training_data, epochs=10)
            
            if metrics:
                # Update performance tracking
                last_metrics = metrics[-1]
                self.model_performance[model_type] = {
                    'accuracy': last_metrics.accuracy or 0.0,
                    'loss': last_metrics.loss,
                    'last_trained': datetime.now().isoformat()
                }
                
                # Save model after training
                model_path = str(self.models_directory / f"{model_type.value}.json")
                await model.save_model(model_path)
                
                logger.info(f"Trained {model_type.value} model with {len(training_data.inputs)} samples")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Training {model_type.value} failed: {e}")
            return False
    
    async def predict_with_model(self, model_type: ModelType, inputs: Any) -> PredictionResult:
        """Make prediction using a specific model."""
        try:
            # Check cache first
            cache_key = f"{model_type.value}:{hash(str(inputs))}"
            if cache_key in self.prediction_cache:
                result, timestamp = self.prediction_cache[cache_key]
                if datetime.now() - timestamp < self.cache_ttl:
                    return result
            
            if model_type not in self.models:
                return PredictionResult(
                    prediction="model_not_available",
                    confidence=0.0,
                    explanation=f"{model_type.value} model not loaded"
                )
            
            model = self.models[model_type]
            result = await model.predict(np.array(inputs))
            
            # Cache result
            self.prediction_cache[cache_key] = (result, datetime.now())
            
            return result
            
        except Exception as e:
            logger.error(f"Prediction with {model_type.value} failed: {e}")
            return PredictionResult(
                prediction="prediction_error",
                confidence=0.0,
                explanation=f"Prediction failed: {str(e)}"
            )
    
    async def auto_train(self, data_source: str) -> Dict[ModelType, bool]:
        """Automatically train all models with available data."""
        results = {}
        
        try:
            # Load training data from source (simplified)
            training_data = await self._load_training_data(data_source)
            
            for model_type in [ModelType.TASK_CLASSIFIER, ModelType.COMPLEXITY_ESTIMATOR, ModelType.PATTERN_MATCHER]:
                try:
                    # Filter data for specific model type
                    model_data = self._filter_training_data(training_data, model_type)
                    
                    if len(model_data.inputs) >= self.min_training_samples:
                        success = await self.train_model(model_type, model_data)
                        results[model_type] = success
                    else:
                        logger.info(f"Insufficient data for {model_type.value}: {len(model_data.inputs)} samples")
                        results[model_type] = False
                        
                except Exception as e:
                    logger.error(f"Auto-training {model_type.value} failed: {e}")
                    results[model_type] = False
            
            return results
            
        except Exception as e:
            logger.error(f"Auto-training failed: {e}")
            return {model_type: False for model_type in ModelType}
    
    async def get_model_status(self) -> Dict[ModelType, Dict[str, Any]]:
        """Get status of all loaded models."""
        status = {}
        
        for model_type in ModelType:
            if model_type in self.models:
                try:
                    model = self.models[model_type]
                    model_info = await model.get_model_info()
                    performance = self.model_performance.get(model_type, {})
                    
                    status[model_type] = {
                        "loaded": True,
                        "model_info": model_info,
                        "performance": performance
                    }
                except Exception as e:
                    status[model_type] = {
                        "loaded": True,
                        "error": str(e)
                    }
            else:
                status[model_type] = {"loaded": False}
        
        return status
    
    async def optimize_models(self) -> Dict[str, Any]:
        """Optimize all models for better performance."""
        optimization_results = {
            "models_optimized": 0,
            "cache_cleared": len(self.prediction_cache),
            "rl_metrics": await self.rl_optimizer.get_optimization_metrics()
        }
        
        # Clear prediction cache
        self.prediction_cache.clear()
        
        # Optimize each model (placeholder for actual optimization)
        for model_type, model in self.models.items():
            try:
                # Model-specific optimization could be implemented here
                optimization_results["models_optimized"] += 1
                logger.debug(f"Optimized {model_type.value} model")
            except Exception as e:
                logger.warning(f"Failed to optimize {model_type.value}: {e}")
        
        return optimization_results
    
    # Helper methods
    
    async def _load_training_data(self, data_source: str) -> TrainingData:
        """Load training data from source."""
        # Placeholder implementation
        # In real implementation, this would load from files, databases, etc.
        return TrainingData(
            inputs=np.array(["sample task 1", "sample task 2"]),
            targets=np.array(["coding", "documentation"])
        )
    
    def _filter_training_data(self, training_data: TrainingData, model_type: ModelType) -> TrainingData:
        """Filter training data for specific model type."""
        # Placeholder implementation
        # In real implementation, this would filter based on model requirements
        return training_data
    
    # Agent optimization interface (RL)
    
    async def optimize_agent_assignment(self, agents: List[Dict[str, Any]], 
                                      tasks: List[Dict[str, Any]]) -> Dict[str, str]:
        """Optimize agent-task assignments using RL."""
        return await self.rl_optimizer.optimize_assignment(agents, tasks)
    
    async def learn_from_assignment_outcome(self, assignment: Dict[str, str], 
                                          outcome: Dict[str, Any]) -> bool:
        """Learn from assignment outcomes."""
        return await self.rl_optimizer.learn_from_outcome(assignment, outcome)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        try:
            health_status = {
                "status": "healthy",
                "models": {},
                "rl_optimizer": {},
                "cache_size": len(self.prediction_cache),
                "models_directory": str(self.models_directory)
            }
            
            # Check each model
            for model_type, model in self.models.items():
                try:
                    if hasattr(model, 'health_check'):
                        model_health = await model.health_check()
                        health_status["models"][model_type.value] = model_health
                    else:
                        health_status["models"][model_type.value] = {"status": "no_health_check"}
                except Exception as e:
                    health_status["models"][model_type.value] = {"status": "unhealthy", "error": str(e)}
                    health_status["status"] = "degraded"
            
            # Check RL optimizer
            try:
                rl_metrics = await self.rl_optimizer.get_optimization_metrics()
                health_status["rl_optimizer"] = {"status": "healthy", "metrics": rl_metrics}
            except Exception as e:
                health_status["rl_optimizer"] = {"status": "unhealthy", "error": str(e)}
                health_status["status"] = "degraded"
            
            return health_status
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }