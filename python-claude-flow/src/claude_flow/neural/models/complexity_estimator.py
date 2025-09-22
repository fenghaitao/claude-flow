"""
Complexity Estimation Engine with Gradient Boosting

This module implements a gradient boosting-based system for estimating
task complexity, resource requirements, and duration predictions
for intelligent task routing and resource allocation.
"""

import asyncio
import json
import logging
import math
import pickle
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from claude_flow.core.interfaces import BaseComponent
from claude_flow.neural.interfaces import (
    ComplexityEstimatorInterface, ModelConfig, TrainingData,
    TrainingMetrics, PredictionResult, ModelType
)


logger = logging.getLogger(__name__)


@dataclass
class ComplexityFeatures:
    """Features for complexity estimation."""
    # Text-based features
    description_length: int = 0
    word_count: int = 0
    sentence_count: int = 0
    
    # Technical complexity indicators
    technical_terms_count: int = 0
    programming_keywords_count: int = 0
    complexity_keywords_count: int = 0
    
    # Task type features
    has_coding_component: bool = False
    has_design_component: bool = False
    has_testing_component: bool = False
    has_documentation_component: bool = False
    has_deployment_component: bool = False
    
    # Dependency and scope features
    external_dependencies_count: int = 0
    modules_affected_count: int = 0
    stakeholder_count: int = 0
    
    # Historical features
    similar_task_avg_duration: float = 0.0
    similar_task_success_rate: float = 0.0
    assignee_experience_level: float = 0.0
    
    # Priority and urgency
    priority_level: int = 3  # 1-5 scale
    is_urgent: bool = False
    has_deadline: bool = False
    
    def to_vector(self) -> np.ndarray:
        """Convert features to numerical vector."""
        return np.array([
            self.description_length / 1000.0,  # Normalized
            self.word_count / 100.0,
            self.sentence_count / 10.0,
            self.technical_terms_count / 20.0,
            self.programming_keywords_count / 15.0,
            self.complexity_keywords_count / 10.0,
            float(self.has_coding_component),
            float(self.has_design_component),
            float(self.has_testing_component),
            float(self.has_documentation_component),
            float(self.has_deployment_component),
            self.external_dependencies_count / 10.0,
            self.modules_affected_count / 5.0,
            self.stakeholder_count / 8.0,
            self.similar_task_avg_duration / 24.0,  # Normalized to days
            self.similar_task_success_rate,
            self.assignee_experience_level,
            self.priority_level / 5.0,
            float(self.is_urgent),
            float(self.has_deadline)
        ])


@dataclass
class ComplexityEstimate:
    """Complexity estimation result."""
    complexity_score: float  # 0-1 scale
    confidence: float
    duration_estimate_hours: float
    resource_estimates: Dict[str, float]
    risk_factors: List[str]
    recommendations: List[str]


class SimpleGradientBoostingTree:
    """Simplified gradient boosting implementation."""
    
    def __init__(self, n_estimators: int = 50, learning_rate: float = 0.1, max_depth: int = 3):
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth
        self.trees: List['SimpleDecisionTree'] = []
        self.initial_prediction = 0.0
    
    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train the gradient boosting model."""
        self.initial_prediction = np.mean(y)
        current_predictions = np.full(len(y), self.initial_prediction)
        
        for i in range(self.n_estimators):
            # Calculate residuals (negative gradients for MSE)
            residuals = y - current_predictions
            
            # Fit tree to residuals
            tree = SimpleDecisionTree(max_depth=self.max_depth)
            tree.fit(X, residuals)
            
            # Update predictions
            tree_predictions = tree.predict(X)
            current_predictions += self.learning_rate * tree_predictions
            
            self.trees.append(tree)
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions."""
        predictions = np.full(X.shape[0], self.initial_prediction)
        
        for tree in self.trees:
            predictions += self.learning_rate * tree.predict(X)
        
        return predictions


class SimpleDecisionTree:
    """Simple decision tree implementation."""
    
    def __init__(self, max_depth: int = 3):
        self.max_depth = max_depth
        self.tree = None
    
    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train the decision tree."""
        self.tree = self._build_tree(X, y, depth=0)
    
    def _build_tree(self, X: np.ndarray, y: np.ndarray, depth: int) -> Dict[str, Any]:
        """Recursively build decision tree."""
        # Base cases
        if depth >= self.max_depth or len(y) < 2:
            return {"prediction": np.mean(y)}
        
        best_split = self._find_best_split(X, y)
        if best_split is None:
            return {"prediction": np.mean(y)}
        
        feature_idx, threshold = best_split
        
        # Split data
        left_mask = X[:, feature_idx] <= threshold
        right_mask = ~left_mask
        
        if np.sum(left_mask) == 0 or np.sum(right_mask) == 0:
            return {"prediction": np.mean(y)}
        
        # Recursively build subtrees
        left_tree = self._build_tree(X[left_mask], y[left_mask], depth + 1)
        right_tree = self._build_tree(X[right_mask], y[right_mask], depth + 1)
        
        return {
            "feature_idx": feature_idx,
            "threshold": threshold,
            "left": left_tree,
            "right": right_tree
        }
    
    def _find_best_split(self, X: np.ndarray, y: np.ndarray) -> Optional[Tuple[int, float]]:
        """Find the best feature and threshold to split on."""
        best_split = None
        best_score = float('inf')
        
        n_features = X.shape[1]
        for feature_idx in range(n_features):
            feature_values = X[:, feature_idx]
            unique_values = np.unique(feature_values)
            
            for threshold in unique_values:
                left_mask = feature_values <= threshold
                right_mask = ~left_mask
                
                if np.sum(left_mask) == 0 or np.sum(right_mask) == 0:
                    continue
                
                # Calculate weighted MSE
                left_mse = np.mean((y[left_mask] - np.mean(y[left_mask])) ** 2) if np.sum(left_mask) > 0 else 0
                right_mse = np.mean((y[right_mask] - np.mean(y[right_mask])) ** 2) if np.sum(right_mask) > 0 else 0
                
                weighted_mse = (np.sum(left_mask) * left_mse + np.sum(right_mask) * right_mse) / len(y)
                
                if weighted_mse < best_score:
                    best_score = weighted_mse
                    best_split = (feature_idx, threshold)
        
        return best_split
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions."""
        predictions = np.zeros(X.shape[0])
        
        for i, x in enumerate(X):
            predictions[i] = self._predict_single(x, self.tree)
        
        return predictions
    
    def _predict_single(self, x: np.ndarray, node: Dict[str, Any]) -> float:
        """Predict single instance."""
        if "prediction" in node:
            return node["prediction"]
        
        if x[node["feature_idx"]] <= node["threshold"]:
            return self._predict_single(x, node["left"])
        else:
            return self._predict_single(x, node["right"])


class GradientBoostingComplexityEstimator(BaseComponent, ComplexityEstimatorInterface):
    """
    Gradient boosting-based complexity estimator.
    
    This implementation uses simplified gradient boosting to predict
    task complexity, duration, and resource requirements based on
    extracted features from task descriptions and metadata.
    """
    
    def __init__(self, n_estimators: int = 50, learning_rate: float = 0.1):
        super().__init__()
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        
        # Model configuration
        self.config: Optional[ModelConfig] = None
        
        # Models for different predictions
        self.complexity_model: Optional[SimpleGradientBoostingTree] = None
        self.duration_model: Optional[SimpleGradientBoostingTree] = None
        self.cpu_model: Optional[SimpleGradientBoostingTree] = None
        self.memory_model: Optional[SimpleGradientBoostingTree] = None
        
        # Training data and state
        self.training_examples: List[Tuple[ComplexityFeatures, Dict[str, float]]] = []
        self.is_trained = False
        
        # Feature processing
        self.feature_processor = ComplexityFeatureProcessor()
        
        # Historical data for learning
        self.historical_data: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.training_history: List[TrainingMetrics] = []
        
        # Prediction cache
        self.prediction_cache: Dict[str, ComplexityEstimate] = {}
        
    async def initialize(self, config: ModelConfig) -> bool:
        """Initialize the model with configuration."""
        try:
            self.config = config
            
            # Update configuration parameters
            if "n_estimators" in config.hyperparameters:
                self.n_estimators = config.hyperparameters["n_estimators"]
            
            if "learning_rate" in config.hyperparameters:
                self.learning_rate = config.hyperparameters["learning_rate"]
            
            # Initialize models
            self.complexity_model = SimpleGradientBoostingTree(
                n_estimators=self.n_estimators,
                learning_rate=self.learning_rate
            )
            self.duration_model = SimpleGradientBoostingTree(
                n_estimators=self.n_estimators,
                learning_rate=self.learning_rate
            )
            self.cpu_model = SimpleGradientBoostingTree(
                n_estimators=self.n_estimators,
                learning_rate=self.learning_rate
            )
            self.memory_model = SimpleGradientBoostingTree(
                n_estimators=self.n_estimators,
                learning_rate=self.learning_rate
            )
            
            self._initialized = True
            logger.info("Complexity estimator initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize complexity estimator: {e}")
            return False
    
    async def train(self, training_data: TrainingData, epochs: int) -> List[TrainingMetrics]:
        """Train the model with given data."""
        try:
            logger.info(f"Training complexity estimator for {epochs} iterations")
            
            # Parse training data
            X, y_complexity, y_duration, y_cpu, y_memory = self._parse_training_data(training_data)
            
            if len(X) == 0:
                logger.warning("No training data available")
                return []
            
            metrics_history = []
            
            # Train models (gradient boosting doesn't use epochs in the traditional sense)
            for iteration in range(epochs):
                # Train complexity model
                if self.complexity_model:
                    self.complexity_model.fit(X, y_complexity)
                    complexity_predictions = self.complexity_model.predict(X)
                    complexity_mse = np.mean((y_complexity - complexity_predictions) ** 2)
                
                # Train duration model
                if self.duration_model:
                    self.duration_model.fit(X, y_duration)
                    duration_predictions = self.duration_model.predict(X)
                    duration_mse = np.mean((y_duration - duration_predictions) ** 2)
                
                # Train resource models
                if self.cpu_model:
                    self.cpu_model.fit(X, y_cpu)
                
                if self.memory_model:
                    self.memory_model.fit(X, y_memory)
                
                # Calculate overall metrics
                overall_mse = (complexity_mse + duration_mse) / 2
                accuracy = 1.0 - min(overall_mse, 1.0)  # Convert MSE to accuracy-like metric
                
                metrics = TrainingMetrics(
                    epoch=iteration + 1,
                    loss=overall_mse,
                    accuracy=accuracy,
                    learning_rate=self.learning_rate,
                    custom_metrics={
                        "complexity_mse": complexity_mse,
                        "duration_mse": duration_mse
                    }
                )
                
                metrics_history.append(metrics)
                self.training_history.append(metrics)
                
                logger.debug(f"Iteration {iteration + 1}: loss={overall_mse:.4f}, accuracy={accuracy:.4f}")
            
            self.is_trained = True
            logger.info("Complexity estimator training completed")
            
            return metrics_history
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return []
    
    def _parse_training_data(self, training_data: TrainingData) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Parse training data into feature matrices and target vectors."""
        X = []
        y_complexity = []
        y_duration = []
        y_cpu = []
        y_memory = []
        
        # Assuming inputs are feature dictionaries and targets are result dictionaries
        for i in range(len(training_data.inputs)):
            try:
                # Extract features
                if isinstance(training_data.inputs[i], dict):
                    features = ComplexityFeatures(**training_data.inputs[i])
                else:
                    # Create features from text description
                    features = self.feature_processor.extract_features(str(training_data.inputs[i]))
                
                X.append(features.to_vector())
                
                # Extract targets
                if isinstance(training_data.targets[i], dict):
                    targets = training_data.targets[i]
                    y_complexity.append(targets.get("complexity", 0.5))
                    y_duration.append(targets.get("duration_hours", 2.0))
                    y_cpu.append(targets.get("cpu_usage", 0.5))
                    y_memory.append(targets.get("memory_usage", 0.5))
                else:
                    # Default values if targets are not structured
                    y_complexity.append(0.5)
                    y_duration.append(2.0)
                    y_cpu.append(0.5)
                    y_memory.append(0.5)
                
            except Exception as e:
                logger.warning(f"Failed to parse training example {i}: {e}")
                continue
        
        return (
            np.array(X) if X else np.array([]).reshape(0, 20),
            np.array(y_complexity),
            np.array(y_duration),
            np.array(y_cpu),
            np.array(y_memory)
        )
    
    async def predict(self, inputs: np.ndarray) -> PredictionResult:
        """Make predictions on input data."""
        try:
            # Extract features
            if isinstance(inputs, np.ndarray) and inputs.dtype.kind in {'U', 'S'}:
                features = self.feature_processor.extract_features(str(inputs.item()))
            elif isinstance(inputs, dict):
                features = ComplexityFeatures(**inputs)
            else:
                features = self.feature_processor.extract_features(str(inputs))
            
            feature_vector = features.to_vector()
            
            # Make predictions with trained models
            complexity_pred = 0.5
            duration_pred = 2.0
            cpu_pred = 0.5
            memory_pred = 0.5
            
            if self.is_trained:
                if self.complexity_model:
                    complexity_pred = np.clip(self.complexity_model.predict(feature_vector.reshape(1, -1))[0], 0, 1)
                
                if self.duration_model:
                    duration_pred = max(0.1, self.duration_model.predict(feature_vector.reshape(1, -1))[0])
                
                if self.cpu_model:
                    cpu_pred = np.clip(self.cpu_model.predict(feature_vector.reshape(1, -1))[0], 0, 1)
                
                if self.memory_model:
                    memory_pred = np.clip(self.memory_model.predict(feature_vector.reshape(1, -1))[0], 0, 1)
            
            # Calculate confidence based on feature quality
            confidence = self._calculate_confidence(features)
            
            # Generate result
            result = PredictionResult(
                prediction={
                    "complexity_score": float(complexity_pred),
                    "duration_hours": float(duration_pred),
                    "cpu_usage": float(cpu_pred),
                    "memory_usage": float(memory_pred)
                },
                confidence=confidence,
                explanation=self._generate_explanation(features, complexity_pred, duration_pred),
                metadata={
                    "feature_vector_size": len(feature_vector),
                    "has_coding_component": features.has_coding_component,
                    "technical_terms_count": features.technical_terms_count,
                    "is_urgent": features.is_urgent
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return PredictionResult(
                prediction={"complexity_score": 0.5, "duration_hours": 2.0},
                confidence=0.0,
                explanation=f"Prediction failed: {str(e)}"
            )
    
    def _calculate_confidence(self, features: ComplexityFeatures) -> float:
        """Calculate prediction confidence based on feature quality."""
        confidence = 0.5  # Base confidence
        
        # Increase confidence for well-defined features
        if features.description_length > 20:
            confidence += 0.1
        if features.technical_terms_count > 0:
            confidence += 0.1
        if features.similar_task_avg_duration > 0:
            confidence += 0.2
        if features.assignee_experience_level > 0:
            confidence += 0.1
        
        # Decrease confidence for missing information
        if features.word_count < 5:
            confidence -= 0.2
        if not any([features.has_coding_component, features.has_design_component, 
                   features.has_testing_component, features.has_documentation_component]):
            confidence -= 0.1
        
        return np.clip(confidence, 0.0, 1.0)
    
    def _generate_explanation(self, features: ComplexityFeatures, complexity: float, duration: float) -> str:
        """Generate explanation for the prediction."""
        explanations = []
        
        # Complexity assessment
        if complexity > 0.7:
            explanations.append("High complexity due to multiple technical components")
        elif complexity > 0.4:
            explanations.append("Moderate complexity with standard implementation")
        else:
            explanations.append("Low complexity for straightforward task")
        
        # Duration factors
        if duration > 8:
            explanations.append("Extended duration due to scope and dependencies")
        elif duration > 4:
            explanations.append("Standard development timeframe expected")
        else:
            explanations.append("Quick implementation possible")
        
        # Feature-based factors
        if features.has_coding_component:
            explanations.append("Includes programming work")
        if features.external_dependencies_count > 2:
            explanations.append("Multiple external dependencies identified")
        if features.is_urgent:
            explanations.append("Marked as urgent priority")
        
        return " | ".join(explanations)
    
    async def evaluate(self, test_data: TrainingData) -> Dict[str, float]:
        """Evaluate model performance on test data."""
        try:
            X, y_complexity, y_duration, y_cpu, y_memory = self._parse_training_data(test_data)
            
            if len(X) == 0:
                return {"error": "No test data available"}
            
            # Make predictions
            complexity_preds = self.complexity_model.predict(X) if self.complexity_model else np.full(len(X), 0.5)
            duration_preds = self.duration_model.predict(X) if self.duration_model else np.full(len(X), 2.0)
            
            # Calculate metrics
            complexity_mse = np.mean((y_complexity - complexity_preds) ** 2)
            duration_mse = np.mean((y_duration - duration_preds) ** 2)
            
            complexity_mae = np.mean(np.abs(y_complexity - complexity_preds))
            duration_mae = np.mean(np.abs(y_duration - duration_preds))
            
            return {
                "complexity_mse": float(complexity_mse),
                "duration_mse": float(duration_mse),
                "complexity_mae": float(complexity_mae),
                "duration_mae": float(duration_mae),
                "overall_score": float(1.0 - min((complexity_mse + duration_mse) / 2, 1.0))
            }
            
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return {"error": str(e)}
    
    async def save_model(self, path: str) -> bool:
        """Save model to file."""
        try:
            model_data = {
                "config": self.config.__dict__ if self.config else {},
                "n_estimators": self.n_estimators,
                "learning_rate": self.learning_rate,
                "is_trained": self.is_trained,
                "training_history": [metrics.__dict__ for metrics in self.training_history],
                "historical_data": dict(self.historical_data)
            }
            
            # Save models using pickle for the tree structures
            file_path = Path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path.with_suffix('.json'), 'w') as f:
                json.dump(model_data, f, indent=2, default=str)
            
            # Save models separately
            models = {
                "complexity_model": self.complexity_model,
                "duration_model": self.duration_model,
                "cpu_model": self.cpu_model,
                "memory_model": self.memory_model
            }
            
            with open(file_path.with_suffix('.pkl'), 'wb') as f:
                pickle.dump(models, f)
            
            logger.info(f"Model saved to {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
            return False
    
    async def load_model(self, path: str) -> bool:
        """Load model from file."""
        try:
            # Load metadata
            with open(Path(path).with_suffix('.json'), 'r') as f:
                model_data = json.load(f)
            
            # Restore configuration
            if model_data.get("config"):
                self.config = ModelConfig(**model_data["config"])
            
            self.n_estimators = model_data.get("n_estimators", 50)
            self.learning_rate = model_data.get("learning_rate", 0.1)
            self.is_trained = model_data.get("is_trained", False)
            
            # Restore training history
            self.training_history = [
                TrainingMetrics(**metrics) for metrics in model_data.get("training_history", [])
            ]
            
            # Restore historical data
            self.historical_data = defaultdict(list, model_data.get("historical_data", {}))
            
            # Load models
            with open(Path(path).with_suffix('.pkl'), 'rb') as f:
                models = pickle.load(f)
            
            self.complexity_model = models.get("complexity_model")
            self.duration_model = models.get("duration_model")
            self.cpu_model = models.get("cpu_model")
            self.memory_model = models.get("memory_model")
            
            logger.info(f"Model loaded from {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get model information and statistics."""
        return {
            "model_type": "GradientBoostingComplexityEstimator",
            "is_trained": self.is_trained,
            "n_estimators": self.n_estimators,
            "learning_rate": self.learning_rate,
            "training_examples": len(self.training_examples),
            "cache_size": len(self.prediction_cache),
            "last_training": self.training_history[-1].__dict__ if self.training_history else None,
            "has_complexity_model": self.complexity_model is not None,
            "has_duration_model": self.duration_model is not None,
            "has_cpu_model": self.cpu_model is not None,
            "has_memory_model": self.memory_model is not None
        }
    
    # ComplexityEstimatorInterface methods
    
    async def estimate_complexity(self, task_features: Dict[str, Any]) -> PredictionResult:
        """Estimate task complexity."""
        result = await self.predict(task_features)
        
        # Extract complexity-specific prediction
        complexity_score = result.prediction.get("complexity_score", 0.5)
        
        return PredictionResult(
            prediction=complexity_score,
            confidence=result.confidence,
            explanation=result.explanation,
            metadata=result.metadata
        )
    
    async def estimate_resources(self, task_features: Dict[str, Any]) -> Dict[str, Union[int, float]]:
        """Estimate required resources for task."""
        result = await self.predict(task_features)
        
        prediction = result.prediction
        return {
            "cpu_usage": prediction.get("cpu_usage", 0.5),
            "memory_usage": prediction.get("memory_usage", 0.5),
            "disk_usage": 0.3,  # Default estimate
            "network_usage": 0.2,  # Default estimate
            "estimated_cost": prediction.get("duration_hours", 2.0) * 50.0  # $50/hour
        }
    
    async def estimate_duration(self, task_features: Dict[str, Any]) -> PredictionResult:
        """Estimate task duration."""
        result = await self.predict(task_features)
        
        # Extract duration-specific prediction
        duration_hours = result.prediction.get("duration_hours", 2.0)
        
        return PredictionResult(
            prediction=duration_hours,
            confidence=result.confidence,
            explanation=result.explanation,
            metadata=result.metadata
        )
    
    async def update_estimates(self, task_features: Dict[str, Any], 
                             actual_metrics: Dict[str, Union[int, float]]) -> bool:
        """Update model with actual performance metrics."""
        try:
            # Store historical data for future training
            self.historical_data["feedback"].append({
                "features": task_features,
                "actual_metrics": actual_metrics,
                "timestamp": datetime.now().isoformat()
            })
            
            # Update training examples
            features = ComplexityFeatures(**task_features) if isinstance(task_features, dict) else self.feature_processor.extract_features(str(task_features))
            
            self.training_examples.append((features, actual_metrics))
            
            # Clear prediction cache to force recomputation
            self.prediction_cache.clear()
            
            logger.debug(f"Updated model with actual metrics: {actual_metrics}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update estimates: {e}")
            return False


class ComplexityFeatureProcessor:
    """Feature extraction for complexity estimation."""
    
    def __init__(self):
        self.technical_terms = {
            'api', 'database', 'algorithm', 'function', 'class', 'method',
            'framework', 'library', 'microservice', 'authentication', 'security',
            'optimization', 'refactoring', 'testing', 'deployment', 'ci/cd'
        }
        
        self.programming_keywords = {
            'code', 'programming', 'develop', 'implement', 'debug', 'script',
            'software', 'application', 'system', 'platform', 'module', 'component',
            'integration', 'interface', 'endpoint', 'service', 'backend', 'frontend'
        }
        
        self.complexity_keywords = {
            'complex', 'complicated', 'difficult', 'challenging', 'advanced',
            'sophisticated', 'intricate', 'multi-step', 'comprehensive', 'detailed',
            'extensive', 'thorough', 'in-depth', 'critical', 'sensitive'
        }
    
    def extract_features(self, task_description: str, metadata: Optional[Dict[str, Any]] = None) -> ComplexityFeatures:
        """Extract complexity features from task description and metadata."""
        text = task_description.lower()
        words = text.split()
        sentences = text.split('.')
        
        # Basic text features
        description_length = len(task_description)
        word_count = len(words)
        sentence_count = len(sentences)
        
        # Technical indicators
        technical_terms_count = sum(1 for word in words if word in self.technical_terms)
        programming_keywords_count = sum(1 for word in words if word in self.programming_keywords)
        complexity_keywords_count = sum(1 for word in words if word in self.complexity_keywords)
        
        # Component detection
        has_coding_component = any(word in text for word in ['code', 'program', 'develop', 'implement', 'script'])
        has_design_component = any(word in text for word in ['design', 'architecture', 'ui', 'ux', 'mockup'])
        has_testing_component = any(word in text for word in ['test', 'qa', 'validate', 'verify'])
        has_documentation_component = any(word in text for word in ['document', 'manual', 'guide', 'readme'])
        has_deployment_component = any(word in text for word in ['deploy', 'release', 'production', 'ci/cd'])
        
        # Dependency analysis (simple keyword matching)
        external_dependencies_count = text.count('dependency') + text.count('integrate') + text.count('external')
        modules_affected_count = text.count('module') + text.count('component') + text.count('service')
        stakeholder_count = text.count('team') + text.count('user') + text.count('client') + text.count('stakeholder')
        
        # Priority and urgency detection
        priority_level = 3  # Default medium priority
        if any(word in text for word in ['urgent', 'critical', 'asap', 'immediately']):
            priority_level = 5
        elif any(word in text for word in ['important', 'priority', 'soon']):
            priority_level = 4
        elif any(word in text for word in ['minor', 'low', 'when possible']):
            priority_level = 2
        
        is_urgent = any(word in text for word in ['urgent', 'asap', 'immediately', 'critical'])
        has_deadline = any(word in text for word in ['deadline', 'due', 'by', 'before'])
        
        # Historical features (would be populated from metadata in real implementation)
        similar_task_avg_duration = 0.0
        similar_task_success_rate = 0.0
        assignee_experience_level = 0.0
        
        if metadata:
            similar_task_avg_duration = metadata.get('similar_task_avg_duration', 0.0)
            similar_task_success_rate = metadata.get('similar_task_success_rate', 0.0)
            assignee_experience_level = metadata.get('assignee_experience_level', 0.0)
            priority_level = metadata.get('priority_level', priority_level)
        
        return ComplexityFeatures(
            description_length=description_length,
            word_count=word_count,
            sentence_count=sentence_count,
            technical_terms_count=technical_terms_count,
            programming_keywords_count=programming_keywords_count,
            complexity_keywords_count=complexity_keywords_count,
            has_coding_component=has_coding_component,
            has_design_component=has_design_component,
            has_testing_component=has_testing_component,
            has_documentation_component=has_documentation_component,
            has_deployment_component=has_deployment_component,
            external_dependencies_count=external_dependencies_count,
            modules_affected_count=modules_affected_count,
            stakeholder_count=stakeholder_count,
            similar_task_avg_duration=similar_task_avg_duration,
            similar_task_success_rate=similar_task_success_rate,
            assignee_experience_level=assignee_experience_level,
            priority_level=priority_level,
            is_urgent=is_urgent,
            has_deadline=has_deadline
        )