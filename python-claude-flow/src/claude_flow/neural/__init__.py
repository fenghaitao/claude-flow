"""
Neural network system for Claude-Flow

This module provides AI/ML capabilities:
- Pattern recognition and classification models
- Complexity estimation engines
- Reinforcement learning for optimization
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .neural_engine import NeuralEngine, SimpleReinforcementLearningOptimizer
    from .models.task_classifier import SimpleTransformerTaskClassifier, TaskFeatures, TaskCategory
    from .models.complexity_estimator import GradientBoostingComplexityEstimator, ComplexityFeatures
    from .models.pattern_matcher import SemanticPatternMatcher, Pattern, PatternCluster
    from .interfaces import (
        ModelType, TrainingPhase, ModelConfig, TrainingData, TrainingMetrics,
        PredictionResult, PatternMatchResult, NeuralModelInterface,
        TaskClassifierInterface, ComplexityEstimatorInterface,
        PatternMatcherInterface, NeuralEngineInterface
    )

__all__ = [
    "NeuralEngine",
    "SimpleReinforcementLearningOptimizer",
    "SimpleTransformerTaskClassifier",
    "TaskFeatures",
    "TaskCategory",
    "GradientBoostingComplexityEstimator",
    "ComplexityFeatures",
    "SemanticPatternMatcher",
    "Pattern",
    "PatternCluster",
    "ModelType",
    "TrainingPhase",
    "ModelConfig",
    "TrainingData",
    "TrainingMetrics",
    "PredictionResult",
    "PatternMatchResult",
    "NeuralModelInterface",
    "TaskClassifierInterface",
    "ComplexityEstimatorInterface",
    "PatternMatcherInterface",
    "NeuralEngineInterface"
]

# Lazy imports to avoid circular dependencies
def __getattr__(name: str):
    if name == "NeuralEngine":
        from .neural_engine import NeuralEngine
        return NeuralEngine
    elif name == "SimpleReinforcementLearningOptimizer":
        from .neural_engine import SimpleReinforcementLearningOptimizer
        return SimpleReinforcementLearningOptimizer
    elif name == "SimpleTransformerTaskClassifier":
        from .models.task_classifier import SimpleTransformerTaskClassifier
        return SimpleTransformerTaskClassifier
    elif name == "TaskFeatures":
        from .models.task_classifier import TaskFeatures
        return TaskFeatures
    elif name == "TaskCategory":
        from .models.task_classifier import TaskCategory
        return TaskCategory
    elif name == "GradientBoostingComplexityEstimator":
        from .models.complexity_estimator import GradientBoostingComplexityEstimator
        return GradientBoostingComplexityEstimator
    elif name == "ComplexityFeatures":
        from .models.complexity_estimator import ComplexityFeatures
        return ComplexityFeatures
    elif name == "SemanticPatternMatcher":
        from .models.pattern_matcher import SemanticPatternMatcher
        return SemanticPatternMatcher
    elif name == "Pattern":
        from .models.pattern_matcher import Pattern
        return Pattern
    elif name == "PatternCluster":
        from .models.pattern_matcher import PatternCluster
        return PatternCluster
    elif name in ["ModelType", "TrainingPhase", "ModelConfig", "TrainingData", "TrainingMetrics",
                  "PredictionResult", "PatternMatchResult", "NeuralModelInterface",
                  "TaskClassifierInterface", "ComplexityEstimatorInterface",
                  "PatternMatcherInterface", "NeuralEngineInterface"]:
        from .interfaces import (
            ModelType, TrainingPhase, ModelConfig, TrainingData, TrainingMetrics,
            PredictionResult, PatternMatchResult, NeuralModelInterface,
            TaskClassifierInterface, ComplexityEstimatorInterface,
            PatternMatcherInterface, NeuralEngineInterface
        )
        return locals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name__}'")
