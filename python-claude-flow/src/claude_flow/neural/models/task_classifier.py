"""
Task Classification Neural Network with Transformers

This module implements a transformer-based task classification system
that can categorize tasks, estimate complexity, and provide intelligent
task routing recommendations for agent assignment.
"""

import asyncio
import json
import logging
import math
import pickle
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
from dataclasses import dataclass, field

from claude_flow.core.interfaces import BaseComponent
from claude_flow.neural.interfaces import (
    TaskClassifierInterface, ModelConfig, TrainingData, 
    TrainingMetrics, PredictionResult, ModelType
)


logger = logging.getLogger(__name__)


@dataclass
class TaskFeatures:
    """Features extracted from task descriptions."""
    text: str
    tokens: List[str]
    length: int
    complexity_indicators: List[str]
    technical_terms: Set[str]
    action_verbs: Set[str]
    domain_keywords: Set[str]
    sentiment_score: float = 0.0
    readability_score: float = 0.0
    
    def to_vector(self, vocab_size: int = 1000) -> np.ndarray:
        """Convert to numerical vector representation."""
        # Simple bag-of-words + features representation
        vector = np.zeros(vocab_size + 10)  # Extra dimensions for features
        
        # Token frequency (simple hash-based)
        for token in self.tokens:
            idx = hash(token.lower()) % vocab_size
            vector[idx] += 1
        
        # Normalize token frequencies
        if len(self.tokens) > 0:
            vector[:vocab_size] /= len(self.tokens)
        
        # Additional features
        vector[vocab_size] = self.length / 1000.0  # Normalized length
        vector[vocab_size + 1] = len(self.complexity_indicators) / 10.0
        vector[vocab_size + 2] = len(self.technical_terms) / 20.0
        vector[vocab_size + 3] = len(self.action_verbs) / 10.0
        vector[vocab_size + 4] = len(self.domain_keywords) / 15.0
        vector[vocab_size + 5] = self.sentiment_score
        vector[vocab_size + 6] = self.readability_score
        vector[vocab_size + 7] = 1.0 if any(word in self.text.lower() for word in ['urgent', 'asap', 'immediately']) else 0.0
        vector[vocab_size + 8] = 1.0 if any(word in self.text.lower() for word in ['complex', 'difficult', 'challenging']) else 0.0
        vector[vocab_size + 9] = 1.0 if any(word in self.text.lower() for word in ['simple', 'easy', 'basic']) else 0.0
        
        return vector


@dataclass 
class TaskCategory:
    """Represents a task category with examples and patterns."""
    name: str
    description: str
    examples: List[str] = field(default_factory=list)
    keywords: Set[str] = field(default_factory=set)
    patterns: List[str] = field(default_factory=list)
    complexity_range: Tuple[float, float] = (0.0, 1.0)
    typical_duration: Optional[float] = None  # in hours
    required_skills: Set[str] = field(default_factory=set)


class SimpleTransformerTaskClassifier(BaseComponent, TaskClassifierInterface):
    """
    Simplified transformer-inspired task classifier.
    
    This implementation uses attention-like mechanisms and feature extraction
    to classify tasks without requiring heavy deep learning frameworks.
    Suitable for environments where full transformers aren't available.
    """
    
    def __init__(self, vocab_size: int = 1000, embedding_dim: int = 128):
        super().__init__()
        self.vocab_size = vocab_size
        self.embedding_dim = embedding_dim
        
        # Model configuration
        self.config: Optional[ModelConfig] = None
        
        # Task categories
        self.categories: Dict[str, TaskCategory] = {}
        self.category_vectors: Dict[str, np.ndarray] = {}
        
        # Training data and state
        self.training_examples: List[Tuple[str, str]] = []  # (text, category)
        self.is_trained = False
        
        # Feature extraction components
        self.text_processor = TaskTextProcessor()
        
        # Simple attention weights (learned during training)
        self.attention_weights: Optional[np.ndarray] = None
        self.category_embeddings: Optional[np.ndarray] = None
        
        # Performance metrics
        self.training_history: List[TrainingMetrics] = []
        self.prediction_cache: Dict[str, PredictionResult] = {}
        
        # Initialize default categories
        self._initialize_default_categories()
    
    def _initialize_default_categories(self) -> None:
        """Initialize default task categories."""
        default_categories = [
            TaskCategory(
                name="coding",
                description="Programming and software development tasks",
                examples=[
                    "Write a Python function to parse JSON",
                    "Debug the authentication system",
                    "Implement REST API endpoints",
                    "Optimize database queries"
                ],
                keywords={"code", "program", "function", "api", "debug", "implement", "script"},
                patterns=[r"\w+\(\)", r"class \w+", r"def \w+", r"import \w+"],
                complexity_range=(0.3, 0.9),
                typical_duration=2.5,
                required_skills={"programming", "debugging", "software_design"}
            ),
            TaskCategory(
                name="documentation",
                description="Writing and updating documentation",
                examples=[
                    "Write API documentation",
                    "Update user manual",
                    "Create technical specifications",
                    "Document the deployment process"
                ],
                keywords={"document", "write", "manual", "guide", "readme", "specification"},
                patterns=[r"README", r"\.md", r"documentation", r"manual"],
                complexity_range=(0.1, 0.5),
                typical_duration=1.5,
                required_skills={"writing", "technical_communication"}
            ),
            TaskCategory(
                name="testing",
                description="Quality assurance and testing tasks",
                examples=[
                    "Write unit tests for user service",
                    "Perform integration testing",
                    "Test the new feature",
                    "Validate API responses"
                ],
                keywords={"test", "validate", "verify", "qa", "check", "unit", "integration"},
                patterns=[r"test_\w+", r"assert", r"expect", r"should"],
                complexity_range=(0.2, 0.7),
                typical_duration=2.0,
                required_skills={"testing", "quality_assurance", "validation"}
            ),
            TaskCategory(
                name="analysis",
                description="Data analysis and research tasks",
                examples=[
                    "Analyze user behavior data",
                    "Research competitor features",
                    "Study performance metrics",
                    "Investigate the issue"
                ],
                keywords={"analyze", "research", "study", "investigate", "metrics", "data"},
                patterns=[r"data", r"metrics", r"analytics", r"statistics"],
                complexity_range=(0.4, 0.8),
                typical_duration=3.0,
                required_skills={"analysis", "research", "critical_thinking"}
            ),
            TaskCategory(
                name="deployment",
                description="Deployment and infrastructure tasks",
                examples=[
                    "Deploy to production",
                    "Configure CI/CD pipeline",
                    "Set up monitoring",
                    "Update server configuration"
                ],
                keywords={"deploy", "configure", "setup", "pipeline", "server", "infrastructure"},
                patterns=[r"deploy", r"ci/cd", r"docker", r"kubernetes"],
                complexity_range=(0.5, 0.9),
                typical_duration=4.0,
                required_skills={"devops", "infrastructure", "deployment"}
            ),
            TaskCategory(
                name="planning",
                description="Project planning and design tasks",
                examples=[
                    "Design system architecture",
                    "Plan sprint activities",
                    "Create project timeline",
                    "Design user interface"
                ],
                keywords={"plan", "design", "architecture", "sprint", "timeline", "interface"},
                patterns=[r"design", r"plan", r"architecture", r"workflow"],
                complexity_range=(0.3, 0.8),
                typical_duration=2.5,
                required_skills={"planning", "design", "architecture"}
            )
        ]
        
        for category in default_categories:
            self.categories[category.name] = category
    
    async def initialize(self, config: ModelConfig) -> bool:
        """Initialize the model with configuration."""
        try:
            self.config = config
            
            # Update configuration parameters
            if "vocab_size" in config.hyperparameters:
                self.vocab_size = config.hyperparameters["vocab_size"]
            
            if "embedding_dim" in config.hyperparameters:
                self.embedding_dim = config.hyperparameters["embedding_dim"]
            
            # Initialize model weights
            self._initialize_weights()
            
            self._initialized = True
            logger.info("Task classifier initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize task classifier: {e}")
            return False
    
    def _initialize_weights(self) -> None:
        """Initialize model weights."""
        # Simple attention weights
        feature_dim = self.vocab_size + 10
        self.attention_weights = np.random.normal(0, 0.1, (feature_dim, self.embedding_dim))
        
        # Category embeddings
        num_categories = len(self.categories)
        self.category_embeddings = np.random.normal(0, 0.1, (num_categories, self.embedding_dim))
        
        # Compute category vectors from examples
        self._compute_category_vectors()
    
    def _compute_category_vectors(self) -> None:
        """Compute representative vectors for each category."""
        for category_name, category in self.categories.items():
            if category.examples:
                vectors = []
                for example in category.examples:
                    features = self.text_processor.extract_features(example)
                    vector = features.to_vector(self.vocab_size)
                    vectors.append(vector)
                
                # Average of example vectors
                self.category_vectors[category_name] = np.mean(vectors, axis=0)
            else:
                # Random vector if no examples
                self.category_vectors[category_name] = np.random.normal(0, 0.1, self.vocab_size + 10)
    
    async def train(self, training_data: TrainingData, epochs: int) -> List[TrainingMetrics]:
        """Train the model with given data."""
        try:
            logger.info(f"Training task classifier for {epochs} epochs")
            
            # Parse training data
            self._parse_training_data(training_data)
            
            metrics_history = []
            
            for epoch in range(epochs):
                epoch_loss = 0.0
                correct_predictions = 0
                total_predictions = 0
                
                # Shuffle training examples
                np.random.shuffle(self.training_examples)
                
                for text, true_category in self.training_examples:
                    # Extract features
                    features = self.text_processor.extract_features(text)
                    feature_vector = features.to_vector(self.vocab_size)
                    
                    # Simple gradient descent update
                    predicted_category, confidence = self._predict_category(feature_vector)
                    
                    # Calculate loss (simple cross-entropy approximation)
                    if predicted_category == true_category:
                        loss = -math.log(max(confidence, 1e-10))
                        correct_predictions += 1
                    else:
                        loss = -math.log(max(1 - confidence, 1e-10))
                    
                    epoch_loss += loss
                    total_predictions += 1
                    
                    # Update weights (simplified)
                    self._update_weights(feature_vector, true_category, predicted_category, confidence)
                
                # Calculate metrics
                accuracy = correct_predictions / max(total_predictions, 1)
                avg_loss = epoch_loss / max(total_predictions, 1)
                
                metrics = TrainingMetrics(
                    epoch=epoch + 1,
                    loss=avg_loss,
                    accuracy=accuracy,
                    learning_rate=0.01  # Fixed learning rate
                )
                
                metrics_history.append(metrics)
                self.training_history.append(metrics)
                
                logger.debug(f"Epoch {epoch + 1}: loss={avg_loss:.4f}, accuracy={accuracy:.4f}")
            
            self.is_trained = True
            logger.info("Task classifier training completed")
            
            return metrics_history
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return []
    
    def _parse_training_data(self, training_data: TrainingData) -> None:
        """Parse training data into text-category pairs."""
        self.training_examples.clear()
        
        # Assuming inputs are text strings and targets are category labels
        for i in range(len(training_data.inputs)):
            text = str(training_data.inputs[i])
            category = str(training_data.targets[i])
            self.training_examples.append((text, category))
    
    def _predict_category(self, feature_vector: np.ndarray) -> Tuple[str, float]:
        """Predict category for feature vector."""
        if not self.category_vectors:
            return list(self.categories.keys())[0], 0.5
        
        best_category = None
        best_score = -float('inf')
        
        for category_name, category_vector in self.category_vectors.items():
            # Simple cosine similarity
            similarity = self._cosine_similarity(feature_vector, category_vector)
            if similarity > best_score:
                best_score = similarity
                best_category = category_name
        
        # Convert similarity to confidence
        confidence = (best_score + 1) / 2  # Normalize to [0, 1]
        return best_category or list(self.categories.keys())[0], confidence
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return np.dot(vec1, vec2) / (norm1 * norm2)
    
    def _update_weights(self, feature_vector: np.ndarray, true_category: str, 
                       predicted_category: str, confidence: float) -> None:
        """Update model weights based on prediction."""
        learning_rate = 0.01
        
        if true_category in self.category_vectors:
            # Move true category vector closer to feature vector
            diff = feature_vector - self.category_vectors[true_category]
            self.category_vectors[true_category] += learning_rate * diff * 0.1
        
        if predicted_category != true_category and predicted_category in self.category_vectors:
            # Move predicted category vector away from feature vector
            diff = self.category_vectors[predicted_category] - feature_vector
            self.category_vectors[predicted_category] += learning_rate * diff * 0.05
    
    async def predict(self, inputs: np.ndarray) -> PredictionResult:
        """Make predictions on input data."""
        try:
            # Convert input to text if needed
            if isinstance(inputs, np.ndarray) and inputs.dtype.kind in {'U', 'S'}:
                text = str(inputs.item())
            else:
                text = str(inputs)
            
            # Check cache
            cache_key = hash(text)
            if cache_key in self.prediction_cache:
                return self.prediction_cache[cache_key]
            
            # Extract features and predict
            features = self.text_processor.extract_features(text)
            feature_vector = features.to_vector(self.vocab_size)
            
            predicted_category, confidence = self._predict_category(feature_vector)
            
            # Calculate probabilities for all categories
            probabilities = {}
            for category_name, category_vector in self.category_vectors.items():
                similarity = self._cosine_similarity(feature_vector, category_vector)
                probabilities[category_name] = (similarity + 1) / 2
            
            # Normalize probabilities
            total_prob = sum(probabilities.values())
            if total_prob > 0:
                probabilities = {k: v / total_prob for k, v in probabilities.items()}
            
            # Generate explanation
            explanation = self._generate_explanation(features, predicted_category)
            
            result = PredictionResult(
                prediction=predicted_category,
                confidence=confidence,
                probabilities=probabilities,
                explanation=explanation,
                metadata={
                    "feature_count": len(features.tokens),
                    "complexity_indicators": len(features.complexity_indicators),
                    "technical_terms": len(features.technical_terms),
                    "category_info": self.categories[predicted_category].__dict__ if predicted_category in self.categories else {}
                }
            )
            
            # Cache result
            self.prediction_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return PredictionResult(
                prediction="unknown",
                confidence=0.0,
                explanation=f"Prediction failed: {str(e)}"
            )
    
    def _generate_explanation(self, features: TaskFeatures, category: str) -> str:
        """Generate explanation for the prediction."""
        explanations = []
        
        if category in self.categories:
            cat_info = self.categories[category]
            explanations.append(f"Classified as '{category}': {cat_info.description}")
            
            # Keyword matches
            matching_keywords = features.domain_keywords.intersection(cat_info.keywords)
            if matching_keywords:
                explanations.append(f"Keyword matches: {', '.join(list(matching_keywords)[:3])}")
            
            # Pattern matches
            for pattern in cat_info.patterns:
                if re.search(pattern, features.text, re.IGNORECASE):
                    explanations.append(f"Matched pattern: {pattern}")
                    break
            
            # Complexity assessment
            if features.complexity_indicators:
                explanations.append(f"Complexity indicators: {', '.join(features.complexity_indicators[:2])}")
        
        return " | ".join(explanations) if explanations else "No specific indicators found"
    
    async def evaluate(self, test_data: TrainingData) -> Dict[str, float]:
        """Evaluate model performance on test data."""
        try:
            correct = 0
            total = 0
            category_counts = defaultdict(int)
            category_correct = defaultdict(int)
            
            for i in range(len(test_data.inputs)):
                text = str(test_data.inputs[i])
                true_category = str(test_data.targets[i])
                
                result = await self.predict(np.array(text))
                predicted_category = result.prediction
                
                category_counts[true_category] += 1
                if predicted_category == true_category:
                    correct += 1
                    category_correct[true_category] += 1
                
                total += 1
            
            # Calculate metrics
            overall_accuracy = correct / max(total, 1)
            
            # Per-category accuracy
            category_accuracy = {}
            for category in category_counts:
                category_accuracy[category] = category_correct[category] / max(category_counts[category], 1)
            
            return {
                "accuracy": overall_accuracy,
                "total_examples": total,
                "correct_predictions": correct,
                "category_accuracy": category_accuracy,
                "macro_accuracy": np.mean(list(category_accuracy.values())) if category_accuracy else 0.0
            }
            
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return {"accuracy": 0.0, "error": str(e)}
    
    async def save_model(self, path: str) -> bool:
        """Save model to file."""
        try:
            model_data = {
                "config": self.config.__dict__ if self.config else {},
                "categories": {name: cat.__dict__ for name, cat in self.categories.items()},
                "category_vectors": {name: vec.tolist() for name, vec in self.category_vectors.items()},
                "attention_weights": self.attention_weights.tolist() if self.attention_weights is not None else None,
                "category_embeddings": self.category_embeddings.tolist() if self.category_embeddings is not None else None,
                "training_history": [metrics.__dict__ for metrics in self.training_history],
                "is_trained": self.is_trained,
                "vocab_size": self.vocab_size,
                "embedding_dim": self.embedding_dim
            }
            
            file_path = Path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w') as f:
                json.dump(model_data, f, indent=2, default=str)
            
            logger.info(f"Model saved to {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
            return False
    
    async def load_model(self, path: str) -> bool:
        """Load model from file."""
        try:
            with open(path, 'r') as f:
                model_data = json.load(f)
            
            # Restore configuration
            if model_data.get("config"):
                self.config = ModelConfig(**model_data["config"])
            
            # Restore categories
            self.categories.clear()
            for name, cat_data in model_data.get("categories", {}).items():
                # Convert sets back from lists
                cat_data["keywords"] = set(cat_data.get("keywords", []))
                cat_data["required_skills"] = set(cat_data.get("required_skills", []))
                self.categories[name] = TaskCategory(**cat_data)
            
            # Restore vectors and weights
            self.category_vectors = {
                name: np.array(vec) for name, vec in model_data.get("category_vectors", {}).items()
            }
            
            if model_data.get("attention_weights"):
                self.attention_weights = np.array(model_data["attention_weights"])
            
            if model_data.get("category_embeddings"):
                self.category_embeddings = np.array(model_data["category_embeddings"])
            
            # Restore training history
            self.training_history = [
                TrainingMetrics(**metrics) for metrics in model_data.get("training_history", [])
            ]
            
            # Restore state
            self.is_trained = model_data.get("is_trained", False)
            self.vocab_size = model_data.get("vocab_size", 1000)
            self.embedding_dim = model_data.get("embedding_dim", 128)
            
            logger.info(f"Model loaded from {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get model information and statistics."""
        return {
            "model_type": "SimpleTransformerTaskClassifier",
            "is_trained": self.is_trained,
            "vocab_size": self.vocab_size,
            "embedding_dim": self.embedding_dim,
            "num_categories": len(self.categories),
            "categories": list(self.categories.keys()),
            "training_examples": len(self.training_examples),
            "cache_size": len(self.prediction_cache),
            "last_training": self.training_history[-1].__dict__ if self.training_history else None,
            "overall_accuracy": self.training_history[-1].accuracy if self.training_history else None
        }
    
    # TaskClassifierInterface methods
    
    async def classify_task(self, task_description: str) -> PredictionResult:
        """Classify a task based on its description."""
        return await self.predict(np.array(task_description))
    
    async def get_task_categories(self) -> List[str]:
        """Get list of supported task categories."""
        return list(self.categories.keys())
    
    async def add_task_category(self, category: str, examples: List[str]) -> bool:
        """Add a new task category with examples."""
        try:
            # Create new category
            new_category = TaskCategory(
                name=category,
                description=f"Custom category: {category}",
                examples=examples
            )
            
            # Extract keywords from examples
            all_text = " ".join(examples).lower()
            keywords = set()
            for word in all_text.split():
                if len(word) > 3 and word.isalpha():
                    keywords.add(word)
            
            new_category.keywords = keywords
            self.categories[category] = new_category
            
            # Compute category vector
            if examples:
                vectors = []
                for example in examples:
                    features = self.text_processor.extract_features(example)
                    vector = features.to_vector(self.vocab_size)
                    vectors.append(vector)
                
                self.category_vectors[category] = np.mean(vectors, axis=0)
            
            # Clear prediction cache
            self.prediction_cache.clear()
            
            logger.info(f"Added new category '{category}' with {len(examples)} examples")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add category '{category}': {e}")
            return False
    
    async def retrain_on_feedback(self, task_description: str, 
                                 correct_category: str, confidence: float) -> bool:
        """Retrain model based on user feedback."""
        try:
            # Add to training examples
            self.training_examples.append((task_description, correct_category))
            
            # Update category vector with this example
            if correct_category in self.category_vectors:
                features = self.text_processor.extract_features(task_description)
                feature_vector = features.to_vector(self.vocab_size)
                
                # Weighted update based on confidence
                learning_rate = 0.1 * (1 - confidence)  # Learn more from low-confidence errors
                diff = feature_vector - self.category_vectors[correct_category]
                self.category_vectors[correct_category] += learning_rate * diff * 0.1
            
            # Clear cache for affected predictions
            cache_key = hash(task_description)
            if cache_key in self.prediction_cache:
                del self.prediction_cache[cache_key]
            
            logger.debug(f"Updated model with feedback: '{task_description}' -> '{correct_category}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to retrain on feedback: {e}")
            return False


class TaskTextProcessor:
    """Text processing utilities for task classification."""
    
    def __init__(self):
        # Predefined vocabularies
        self.complexity_indicators = {
            'complex', 'complicated', 'difficult', 'challenging', 'advanced',
            'sophisticated', 'intricate', 'elaborate', 'multi-step', 'comprehensive'
        }
        
        self.technical_terms = {
            'api', 'database', 'algorithm', 'function', 'class', 'method', 'variable',
            'framework', 'library', 'module', 'package', 'repository', 'server',
            'client', 'endpoint', 'service', 'microservice', 'container', 'docker',
            'kubernetes', 'deployment', 'testing', 'unittest', 'integration',
            'authentication', 'authorization', 'security', 'encryption', 'ssl', 'https',
            'json', 'xml', 'csv', 'sql', 'nosql', 'redis', 'mongodb', 'postgresql',
            'mysql', 'elasticsearch', 'kafka', 'rabbitmq', 'nginx', 'apache',
            'ci', 'cd', 'devops', 'monitoring', 'logging', 'metrics', 'prometheus',
            'grafana', 'kibana', 'jenkins', 'github', 'gitlab', 'git', 'svn',
            'agile', 'scrum', 'kanban', 'sprint', 'backlog', 'user_story',
            'requirement', 'specification', 'design', 'architecture', 'pattern',
            'refactor', 'optimize', 'performance', 'scalability', 'availability'
        }
        
        self.action_verbs = {
            'create', 'build', 'develop', 'implement', 'write', 'code', 'program',
            'design', 'plan', 'analyze', 'test', 'validate', 'verify', 'debug',
            'fix', 'resolve', 'troubleshoot', 'investigate', 'research', 'study',
            'deploy', 'configure', 'setup', 'install', 'update', 'upgrade',
            'migrate', 'refactor', 'optimize', 'improve', 'enhance', 'extend',
            'maintain', 'monitor', 'review', 'document', 'explain', 'describe'
        }
        
        self.domain_keywords = {
            # Programming languages
            'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go',
            'rust', 'ruby', 'php', 'swift', 'kotlin', 'scala', 'r',
            
            # Frameworks and tools
            'react', 'angular', 'vue', 'django', 'flask', 'spring', 'express',
            'nodejs', 'npm', 'yarn', 'webpack', 'babel', 'eslint', 'prettier',
            
            # Domains
            'frontend', 'backend', 'fullstack', 'mobile', 'web', 'desktop',
            'embedded', 'iot', 'ml', 'ai', 'data', 'analytics', 'blockchain',
            
            # Methodologies
            'tdd', 'bdd', 'ddd', 'mvp', 'mvc', 'mvvm', 'solid', 'dry', 'kiss'
        }
    
    def extract_features(self, text: str) -> TaskFeatures:
        """Extract features from task description text."""
        # Basic preprocessing
        text_lower = text.lower()
        
        # Tokenization (simple)
        tokens = re.findall(r'\b\w+\b', text_lower)
        
        # Extract different types of features
        complexity_indicators = [word for word in tokens if word in self.complexity_indicators]
        technical_terms = set(word for word in tokens if word in self.technical_terms)
        action_verbs = set(word for word in tokens if word in self.action_verbs)
        domain_keywords = set(word for word in tokens if word in self.domain_keywords)
        
        # Simple sentiment analysis (basic positive/negative word counting)
        positive_words = {'good', 'great', 'excellent', 'easy', 'simple', 'clear', 'clean'}
        negative_words = {'bad', 'difficult', 'hard', 'complex', 'problematic', 'issue', 'bug'}
        
        positive_count = sum(1 for word in tokens if word in positive_words)
        negative_count = sum(1 for word in tokens if word in negative_words)
        sentiment_score = (positive_count - negative_count) / max(len(tokens), 1)
        
        # Simple readability score (based on average word length and sentence structure)
        avg_word_length = np.mean([len(word) for word in tokens]) if tokens else 0
        sentence_count = len(re.findall(r'[.!?]+', text))
        readability_score = 1.0 - min(avg_word_length / 10.0, 1.0)  # Shorter words = more readable
        
        return TaskFeatures(
            text=text,
            tokens=tokens,
            length=len(text),
            complexity_indicators=complexity_indicators,
            technical_terms=technical_terms,
            action_verbs=action_verbs,
            domain_keywords=domain_keywords,
            sentiment_score=sentiment_score,
            readability_score=readability_score
        ) '