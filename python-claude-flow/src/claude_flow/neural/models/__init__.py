"""
Neural network models for Claude-Flow.

This module provides various AI/ML models for task classification,
complexity estimation, pattern matching, and agent optimization.
"""

from .task_classifier import SimpleTransformerTaskClassifier, TaskFeatures, TaskCategory
from .complexity_estimator import GradientBoostingComplexityEstimator, ComplexityFeatures, ComplexityEstimate
from .pattern_matcher import SemanticPatternMatcher, Pattern, PatternCluster

__all__ = [
    'SimpleTransformerTaskClassifier',
    'TaskFeatures',
    'TaskCategory',
    'GradientBoostingComplexityEstimator',
    'ComplexityFeatures',
    'ComplexityEstimate',
    'SemanticPatternMatcher',
    'Pattern',
    'PatternCluster'
]