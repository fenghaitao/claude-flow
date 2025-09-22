"""
Neural network interfaces for Claude-Flow

This module defines interfaces for AI/ML capabilities including pattern recognition,
complexity estimation, and reinforcement learning.
"""

from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
from ..core.interfaces import BaseComponent


class ModelType(Enum):
    """Types of neural network models"""
    TASK_CLASSIFIER = "task_classifier"
    COMPLEXITY_ESTIMATOR = "complexity_estimator"
    PATTERN_MATCHER = "pattern_matcher"
    AGENT_OPTIMIZER = "agent_optimizer"
    PERFORMANCE_PREDICTOR = "performance_predictor"


class TrainingPhase(Enum):
    """Training phases"""
    INITIALIZATION = "initialization"
    TRAINING = "training"
    VALIDATION = "validation"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    INFERENCE = "inference"


@dataclass
class ModelConfig:
    """Configuration for neural network models"""
    model_type: ModelType
    architecture: str
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    input_shape: Optional[Tuple[int, ...]] = None
    output_shape: Optional[Tuple[int, ...]] = None
    training_config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrainingData:
    """Training data structure"""
    inputs: np.ndarray
    targets: np.ndarray
    validation_inputs: Optional[np.ndarray] = None
    validation_targets: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrainingMetrics:
    """Training performance metrics"""
    epoch: int
    loss: float
    accuracy: Optional[float] = None
    validation_loss: Optional[float] = None
    validation_accuracy: Optional[float] = None
    learning_rate: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    custom_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class PredictionResult:
    """Result of model prediction"""
    prediction: Any
    confidence: float
    probabilities: Optional[Dict[str, float]] = None
    explanation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PatternMatchResult:
    """Result of pattern matching"""
    pattern_id: str
    similarity_score: float
    pattern_data: Dict[str, Any]
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class NeuralModelInterface:
    """Interface for neural network models"""
    
    @abstractmethod
    async def initialize(self, config: ModelConfig) -> bool:
        """Initialize the model with configuration"""
        pass
    
    @abstractmethod
    async def train(self, training_data: TrainingData, epochs: int) -> List[TrainingMetrics]:
        """Train the model with given data"""
        pass
    
    @abstractmethod
    async def predict(self, inputs: np.ndarray) -> PredictionResult:
        """Make predictions on input data"""
        pass
    
    @abstractmethod
    async def evaluate(self, test_data: TrainingData) -> Dict[str, float]:
        """Evaluate model performance on test data"""
        pass
    
    @abstractmethod
    async def save_model(self, path: str) -> bool:
        """Save model to file"""
        pass
    
    @abstractmethod
    async def load_model(self, path: str) -> bool:
        """Load model from file"""
        pass
    
    @abstractmethod
    async def get_model_info(self) -> Dict[str, Any]:
        """Get model information and statistics"""
        pass


class TaskClassifierInterface(NeuralModelInterface):
    """Interface for task classification models"""
    
    @abstractmethod
    async def classify_task(self, task_description: str) -> PredictionResult:
        """Classify a task based on its description"""
        pass
    
    @abstractmethod
    async def get_task_categories(self) -> List[str]:
        """Get list of supported task categories"""
        pass
    
    @abstractmethod
    async def add_task_category(self, category: str, examples: List[str]) -> bool:
        """Add a new task category with examples"""
        pass
    
    @abstractmethod
    async def retrain_on_feedback(self, task_description: str, 
                                correct_category: str, confidence: float) -> bool:
        """Retrain model based on user feedback"""
        pass


class ComplexityEstimatorInterface(NeuralModelInterface):
    """Interface for complexity estimation models"""
    
    @abstractmethod
    async def estimate_complexity(self, task_features: Dict[str, Any]) -> PredictionResult:
        """Estimate task complexity"""
        pass
    
    @abstractmethod
    async def estimate_resources(self, task_features: Dict[str, Any]) -> Dict[str, Union[int, float]]:
        """Estimate required resources for task"""
        pass
    
    @abstractmethod
    async def estimate_duration(self, task_features: Dict[str, Any]) -> PredictionResult:
        """Estimate task duration"""
        pass
    
    @abstractmethod
    async def update_estimates(self, task_features: Dict[str, Any], 
                             actual_metrics: Dict[str, Union[int, float]]) -> bool:
        """Update model with actual performance metrics"""
        pass


class PatternMatcherInterface(NeuralModelInterface):
    """Interface for pattern matching models"""
    
    @abstractmethod
    async def find_patterns(self, data: Any, pattern_type: str) -> List[PatternMatchResult]:
        """Find patterns in data"""
        pass
    
    @abstractmethod
    async def learn_pattern(self, pattern_data: Dict[str, Any], pattern_type: str) -> str:
        """Learn a new pattern, return pattern ID"""
        pass
    
    @abstractmethod
    async def match_against_patterns(self, query_data: Any) -> List[PatternMatchResult]:
        """Match query data against learned patterns"""
        pass
    
    @abstractmethod
    async def get_pattern_info(self, pattern_id: str) -> Dict[str, Any]:
        """Get information about a specific pattern"""
        pass
    
    @abstractmethod
    async def delete_pattern(self, pattern_id: str) -> bool:
        """Delete a learned pattern"""
        pass


class AgentOptimizerInterface(NeuralModelInterface):
    """Interface for agent optimization using reinforcement learning"""
    
    @abstractmethod
    async def optimize_assignment(self, agents: List[Dict[str, Any]], 
                                tasks: List[Dict[str, Any]]) -> Dict[str, str]:
        """Optimize agent-task assignments"""
        pass
    
    @abstractmethod
    async def learn_from_outcome(self, assignment: Dict[str, str], 
                               outcome: Dict[str, Any]) -> bool:
        """Learn from assignment outcomes"""
        pass
    
    @abstractmethod
    async def suggest_improvements(self, agent_id: str) -> List[Dict[str, Any]]:
        """Suggest improvements for an agent"""
        pass
    
    @abstractmethod
    async def predict_performance(self, agent_id: str, task_id: str) -> PredictionResult:
        """Predict agent performance on a task"""
        pass


class PerformancePredictorInterface(NeuralModelInterface):
    """Interface for performance prediction models"""
    
    @abstractmethod
    async def predict_completion_time(self, task_features: Dict[str, Any], 
                                    agent_features: Dict[str, Any]) -> PredictionResult:
        """Predict task completion time"""
        pass
    
    @abstractmethod
    async def predict_success_probability(self, task_features: Dict[str, Any], 
                                        agent_features: Dict[str, Any]) -> PredictionResult:
        """Predict probability of task success"""
        pass
    
    @abstractmethod
    async def predict_resource_usage(self, task_features: Dict[str, Any]) -> Dict[str, PredictionResult]:
        """Predict resource usage (CPU, memory, etc.)"""
        pass
    
    @abstractmethod
    async def update_predictions(self, prediction_id: str, actual_result: Dict[str, Any]) -> bool:
        """Update model with actual results"""
        pass


class NeuralEngineInterface(BaseComponent):
    """Interface for the main neural engine coordinator"""
    
    @abstractmethod
    async def load_model(self, model_type: ModelType, model_path: Optional[str] = None) -> bool:
        """Load a specific model type"""
        pass
    
    @abstractmethod
    async def get_model(self, model_type: ModelType) -> Optional[NeuralModelInterface]:
        """Get a loaded model instance"""
        pass
    
    @abstractmethod
    async def train_model(self, model_type: ModelType, training_data: TrainingData) -> bool:
        """Train a specific model"""
        pass
    
    @abstractmethod
    async def predict_with_model(self, model_type: ModelType, inputs: Any) -> PredictionResult:
        """Make prediction using a specific model"""
        pass
    
    @abstractmethod
    async def auto_train(self, data_source: str) -> Dict[ModelType, bool]:
        """Automatically train all models with available data"""
        pass
    
    @abstractmethod
    async def get_model_status(self) -> Dict[ModelType, Dict[str, Any]]:
        """Get status of all loaded models"""
        pass
    
    @abstractmethod
    async def optimize_models(self) -> Dict[str, Any]:
        """Optimize all models for better performance"""
        pass


class TrainingManagerInterface:
    """Interface for managing model training"""
    
    @abstractmethod
    async def schedule_training(self, model_type: ModelType, 
                              training_config: Dict[str, Any]) -> str:
        """Schedule a training job, return job ID"""
        pass
    
    @abstractmethod
    async def monitor_training(self, job_id: str) -> Dict[str, Any]:
        """Monitor training job progress"""
        pass
    
    @abstractmethod
    async def stop_training(self, job_id: str) -> bool:
        """Stop a training job"""
        pass
    
    @abstractmethod
    async def get_training_history(self, model_type: ModelType) -> List[Dict[str, Any]]:
        """Get training history for a model type"""
        pass


class ModelRepositoryInterface:
    """Interface for model storage and versioning"""
    
    @abstractmethod
    async def save_model(self, model_type: ModelType, model: NeuralModelInterface, 
                       version: str, metadata: Dict[str, Any]) -> bool:
        """Save model with version information"""
        pass
    
    @abstractmethod
    async def load_model(self, model_type: ModelType, version: Optional[str] = None) -> Optional[NeuralModelInterface]:
        """Load model (latest version if not specified)"""
        pass
    
    @abstractmethod
    async def list_model_versions(self, model_type: ModelType) -> List[Dict[str, Any]]:
        """List all versions of a model type"""
        pass
    
    @abstractmethod
    async def delete_model_version(self, model_type: ModelType, version: str) -> bool:
        """Delete a specific model version"""
        pass
    
    @abstractmethod
    async def compare_models(self, model_type: ModelType, 
                           version1: str, version2: str) -> Dict[str, Any]:
        """Compare two model versions"""
        pass