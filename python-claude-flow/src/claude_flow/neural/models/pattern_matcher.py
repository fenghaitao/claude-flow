"""
Pattern Matching System with Semantic Embeddings

This module implements a semantic pattern matching system that can learn,
store, and match patterns in task descriptions, code snippets, and other
data using embeddings and similarity matching techniques.
"""

import asyncio
import json
import logging
import math
import pickle
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np

from claude_flow.core.interfaces import BaseComponent
from claude_flow.neural.interfaces import (
    PatternMatcherInterface, ModelConfig, TrainingData,
    TrainingMetrics, PredictionResult, PatternMatchResult, ModelType
)


logger = logging.getLogger(__name__)


@dataclass
class Pattern:
    """Represents a learned pattern."""
    pattern_id: str
    pattern_type: str
    description: str
    embedding: np.ndarray
    features: Dict[str, Any]
    examples: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    usage_count: int = 0
    success_rate: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type,
            "description": self.description,
            "embedding": self.embedding.tolist(),
            "features": self.features,
            "examples": self.examples,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "usage_count": self.usage_count,
            "success_rate": self.success_rate,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Pattern':
        """Create Pattern from dictionary."""
        return cls(
            pattern_id=data["pattern_id"],
            pattern_type=data["pattern_type"],
            description=data["description"],
            embedding=np.array(data["embedding"]),
            features=data["features"],
            examples=data.get("examples", []),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            usage_count=data.get("usage_count", 0),
            success_rate=data.get("success_rate", 1.0),
            metadata=data.get("metadata", {})
        )


@dataclass
class PatternCluster:
    """Represents a cluster of related patterns."""
    cluster_id: str
    patterns: List[str] = field(default_factory=list)  # Pattern IDs
    centroid: Optional[np.ndarray] = None
    cluster_type: str = "general"
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)


class SimpleEmbeddingGenerator:
    """Simple embedding generator for pattern matching."""
    
    def __init__(self, dimensions: int = 256):
        self.dimensions = dimensions
        
        # Vocabulary for different pattern types
        self.code_vocabulary = {
            'function', 'class', 'method', 'variable', 'import', 'return',
            'if', 'else', 'for', 'while', 'try', 'except', 'def', 'async',
            'await', 'lambda', 'yield', 'with', 'as', 'in', 'not', 'and', 'or'
        }
        
        self.task_vocabulary = {
            'implement', 'create', 'build', 'develop', 'design', 'test',
            'debug', 'fix', 'optimize', 'refactor', 'deploy', 'configure',
            'analyze', 'research', 'document', 'review', 'update', 'maintain'
        }
        
        self.domain_vocabulary = {
            'api', 'database', 'frontend', 'backend', 'ui', 'ux', 'security',
            'authentication', 'authorization', 'performance', 'scalability',
            'monitoring', 'logging', 'testing', 'deployment', 'ci', 'cd'
        }
    
    def generate_embedding(self, text: str, pattern_type: str = "general") -> np.ndarray:
        """Generate embedding for text based on pattern type."""
        text_lower = text.lower()
        tokens = text_lower.split()
        
        # Initialize embedding
        embedding = np.zeros(self.dimensions)
        
        # Select appropriate vocabulary
        if pattern_type == "code":
            vocab = self.code_vocabulary
        elif pattern_type == "task":
            vocab = self.task_vocabulary
        elif pattern_type == "domain":
            vocab = self.domain_vocabulary
        else:
            vocab = self.code_vocabulary | self.task_vocabulary | self.domain_vocabulary
        
        # Simple hash-based embedding with position weighting
        for i, token in enumerate(tokens):
            # Hash token to embedding dimension
            hash_val = hash(token) % self.dimensions
            position_weight = 1.0 / (i + 1)  # Decrease weight by position
            
            # Higher weight for vocabulary words
            if token in vocab:
                position_weight *= 2.0
            
            embedding[hash_val] += position_weight
        
        # Add pattern type specific features
        if pattern_type == "code":
            # Code pattern indicators
            if any(indicator in text_lower for indicator in ['def ', 'class ', 'import ']):
                embedding[-10:] += 0.5
        elif pattern_type == "task":
            # Task pattern indicators
            if any(verb in text_lower for verb in ['create', 'implement', 'build']):
                embedding[-5:] += 0.3
        
        # Normalize embedding
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        return embedding


class SemanticPatternMatcher(BaseComponent, PatternMatcherInterface):
    """
    Semantic pattern matching system using embeddings.
    
    This implementation provides pattern learning, storage, and matching
    capabilities using semantic embeddings and similarity computation.
    Suitable for identifying recurring patterns in tasks, code, and data.
    """
    
    def __init__(self, embedding_dimensions: int = 256, similarity_threshold: float = 0.75):
        super().__init__()
        self.embedding_dimensions = embedding_dimensions
        self.similarity_threshold = similarity_threshold
        
        # Model configuration
        self.config: Optional[ModelConfig] = None
        
        # Pattern storage
        self.patterns: Dict[str, Pattern] = {}
        self.pattern_clusters: Dict[str, PatternCluster] = {}
        
        # Embedding generator
        self.embedding_generator = SimpleEmbeddingGenerator(embedding_dimensions)
        
        # Pattern indices for fast retrieval
        self.type_index: Dict[str, Set[str]] = defaultdict(set)  # pattern_type -> pattern_ids
        self.embedding_matrix: Optional[np.ndarray] = None
        self.pattern_ids_list: List[str] = []
        
        # Training and statistics
        self.training_history: List[TrainingMetrics] = []
        self.match_statistics: Dict[str, int] = defaultdict(int)
        
        # Cache for pattern matching results
        self.match_cache: Dict[str, List[PatternMatchResult]] = {}
        
        # Auto-clustering parameters
        self.auto_clustering_enabled = True
        self.min_cluster_size = 3
        self.cluster_similarity_threshold = 0.8
        
    async def initialize(self, config: ModelConfig) -> bool:
        """Initialize the model with configuration."""
        try:
            self.config = config
            
            # Update configuration parameters
            if "embedding_dimensions" in config.hyperparameters:
                self.embedding_dimensions = config.hyperparameters["embedding_dimensions"]
            
            if "similarity_threshold" in config.hyperparameters:
                self.similarity_threshold = config.hyperparameters["similarity_threshold"]
            
            if "auto_clustering_enabled" in config.hyperparameters:
                self.auto_clustering_enabled = config.hyperparameters["auto_clustering_enabled"]
            
            # Initialize embedding generator with new dimensions
            self.embedding_generator = SimpleEmbeddingGenerator(self.embedding_dimensions)
            
            self._initialized = True
            logger.info("Pattern matcher initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize pattern matcher: {e}")
            return False
    
    async def train(self, training_data: TrainingData, epochs: int) -> List[TrainingMetrics]:
        """Train the model with given data."""
        try:
            logger.info(f"Training pattern matcher with {len(training_data.inputs)} examples")
            
            metrics_history = []
            
            # Parse training data and learn patterns
            patterns_learned = 0
            for i in range(len(training_data.inputs)):
                try:
                    # Extract pattern data
                    if isinstance(training_data.inputs[i], dict):
                        pattern_data = training_data.inputs[i]
                        pattern_type = str(training_data.targets[i]) if i < len(training_data.targets) else "general"
                    else:
                        pattern_data = {"text": str(training_data.inputs[i])}
                        pattern_type = str(training_data.targets[i]) if i < len(training_data.targets) else "general"
                    
                    # Learn pattern
                    pattern_id = await self.learn_pattern(pattern_data, pattern_type)
                    if pattern_id:
                        patterns_learned += 1
                        
                except Exception as e:
                    logger.warning(f"Failed to learn pattern from example {i}: {e}")
                    continue
            
            # Update embedding matrix
            self._update_embedding_matrix()
            
            # Perform clustering if enabled
            if self.auto_clustering_enabled:
                await self._auto_cluster_patterns()
            
            # Create training metrics
            for epoch in range(epochs):
                accuracy = patterns_learned / max(len(training_data.inputs), 1)
                
                metrics = TrainingMetrics(
                    epoch=epoch + 1,
                    loss=1.0 - accuracy,  # Simple loss based on learning success rate
                    accuracy=accuracy,
                    custom_metrics={
                        "patterns_learned": patterns_learned,
                        "total_patterns": len(self.patterns),
                        "clusters_formed": len(self.pattern_clusters)
                    }
                )
                
                metrics_history.append(metrics)
                self.training_history.append(metrics)
            
            logger.info(f"Pattern matcher training completed: {patterns_learned} patterns learned")
            return metrics_history
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return []
    
    async def predict(self, inputs: np.ndarray) -> PredictionResult:
        """Make predictions on input data."""
        try:
            # Convert input to text
            if isinstance(inputs, np.ndarray) and inputs.dtype.kind in {'U', 'S'}:
                query_text = str(inputs.item())
            else:
                query_text = str(inputs)
            
            # Find matching patterns
            matches = await self.match_against_patterns(query_text)
            
            if not matches:
                return PredictionResult(
                    prediction="no_patterns_matched",
                    confidence=0.0,
                    explanation="No similar patterns found"
                )
            
            # Get best match
            best_match = matches[0]
            
            return PredictionResult(
                prediction=best_match.pattern_id,
                confidence=best_match.confidence,
                probabilities={match.pattern_id: match.confidence for match in matches[:5]},
                explanation=f"Best match: {best_match.pattern_data.get('description', 'N/A')} (similarity: {best_match.similarity_score:.3f})",
                metadata={
                    "total_matches": len(matches),
                    "pattern_types": list(set(match.pattern_data.get('pattern_type', 'unknown') for match in matches)),
                    "avg_similarity": np.mean([match.similarity_score for match in matches])
                }
            )
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return PredictionResult(
                prediction="error",
                confidence=0.0,
                explanation=f"Prediction failed: {str(e)}"
            )
    
    async def evaluate(self, test_data: TrainingData) -> Dict[str, float]:
        """Evaluate model performance on test data."""
        try:
            correct_matches = 0
            total_tests = 0
            similarity_scores = []
            
            for i in range(len(test_data.inputs)):
                try:
                    # Get query and expected pattern type
                    query = str(test_data.inputs[i])
                    expected_type = str(test_data.targets[i]) if i < len(test_data.targets) else None
                    
                    # Find matches
                    matches = await self.match_against_patterns(query)
                    
                    if matches:
                        best_match = matches[0]
                        similarity_scores.append(best_match.similarity_score)
                        
                        # Check if match is correct (based on pattern type)
                        if expected_type and best_match.pattern_data.get('pattern_type') == expected_type:
                            correct_matches += 1
                    
                    total_tests += 1
                    
                except Exception as e:
                    logger.warning(f"Evaluation failed for test {i}: {e}")
                    continue
            
            # Calculate metrics
            accuracy = correct_matches / max(total_tests, 1)
            avg_similarity = np.mean(similarity_scores) if similarity_scores else 0.0
            
            return {
                "accuracy": accuracy,
                "avg_similarity": float(avg_similarity),
                "total_tests": total_tests,
                "correct_matches": correct_matches,
                "patterns_available": len(self.patterns),
                "match_coverage": len(similarity_scores) / max(total_tests, 1)
            }
            
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return {"error": str(e)}
    
    async def save_model(self, path: str) -> bool:
        """Save model to file."""
        try:
            # Prepare model data
            model_data = {
                "config": self.config.__dict__ if self.config else {},
                "embedding_dimensions": self.embedding_dimensions,
                "similarity_threshold": self.similarity_threshold,
                "auto_clustering_enabled": self.auto_clustering_enabled,
                "patterns": {pid: pattern.to_dict() for pid, pattern in self.patterns.items()},
                "pattern_clusters": {
                    cid: {
                        "cluster_id": cluster.cluster_id,
                        "patterns": cluster.patterns,
                        "centroid": cluster.centroid.tolist() if cluster.centroid is not None else None,
                        "cluster_type": cluster.cluster_type,
                        "description": cluster.description,
                        "created_at": cluster.created_at.isoformat()
                    } for cid, cluster in self.pattern_clusters.items()
                },
                "training_history": [metrics.__dict__ for metrics in self.training_history],
                "match_statistics": dict(self.match_statistics)
            }
            
            # Save to file
            file_path = Path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w') as f:
                json.dump(model_data, f, indent=2, default=str)
            
            logger.info(f"Pattern matcher saved to {path}")
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
            
            self.embedding_dimensions = model_data.get("embedding_dimensions", 256)
            self.similarity_threshold = model_data.get("similarity_threshold", 0.75)
            self.auto_clustering_enabled = model_data.get("auto_clustering_enabled", True)
            
            # Restore patterns
            self.patterns.clear()
            for pid, pattern_data in model_data.get("patterns", {}).items():
                self.patterns[pid] = Pattern.from_dict(pattern_data)
            
            # Restore clusters
            self.pattern_clusters.clear()
            for cid, cluster_data in model_data.get("pattern_clusters", {}).items():
                cluster = PatternCluster(
                    cluster_id=cluster_data["cluster_id"],
                    patterns=cluster_data["patterns"],
                    centroid=np.array(cluster_data["centroid"]) if cluster_data["centroid"] else None,
                    cluster_type=cluster_data["cluster_type"],
                    description=cluster_data["description"],
                    created_at=datetime.fromisoformat(cluster_data["created_at"])
                )
                self.pattern_clusters[cid] = cluster
            
            # Restore training history
            self.training_history = [
                TrainingMetrics(**metrics) for metrics in model_data.get("training_history", [])
            ]
            
            # Restore statistics
            self.match_statistics = defaultdict(int, model_data.get("match_statistics", {}))
            
            # Rebuild indices
            self._rebuild_indices()
            
            logger.info(f"Pattern matcher loaded from {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get model information and statistics."""
        return {
            "model_type": "SemanticPatternMatcher",
            "embedding_dimensions": self.embedding_dimensions,
            "similarity_threshold": self.similarity_threshold,
            "total_patterns": len(self.patterns),
            "pattern_types": list(self.type_index.keys()),
            "total_clusters": len(self.pattern_clusters),
            "auto_clustering_enabled": self.auto_clustering_enabled,
            "cache_size": len(self.match_cache),
            "match_statistics": dict(self.match_statistics),
            "last_training": self.training_history[-1].__dict__ if self.training_history else None
        }
    
    # PatternMatcherInterface methods
    
    async def find_patterns(self, data: Any, pattern_type: str) -> List[PatternMatchResult]:
        """Find patterns in data."""
        # Convert data to text
        if isinstance(data, dict):
            text = json.dumps(data)
        else:
            text = str(data)
        
        # Find matching patterns of the specified type
        all_matches = await self.match_against_patterns(text)
        
        # Filter by pattern type
        type_matches = [
            match for match in all_matches 
            if match.pattern_data.get('pattern_type') == pattern_type
        ]
        
        return type_matches
    
    async def learn_pattern(self, pattern_data: Dict[str, Any], pattern_type: str) -> str:
        """Learn a new pattern, return pattern ID."""
        try:
            # Generate unique pattern ID
            pattern_id = str(uuid.uuid4())
            
            # Extract text for embedding
            if "text" in pattern_data:
                text = pattern_data["text"]
            else:
                text = json.dumps(pattern_data)
            
            # Generate embedding
            embedding = self.embedding_generator.generate_embedding(text, pattern_type)
            
            # Extract features
            features = self._extract_pattern_features(text, pattern_type)
            
            # Create pattern
            pattern = Pattern(
                pattern_id=pattern_id,
                pattern_type=pattern_type,
                description=pattern_data.get("description", text[:100]),
                embedding=embedding,
                features=features,
                examples=[text],
                metadata=pattern_data
            )
            
            # Store pattern
            self.patterns[pattern_id] = pattern
            self.type_index[pattern_type].add(pattern_id)
            
            # Update embedding matrix
            self._update_embedding_matrix()
            
            # Clear cache
            self.match_cache.clear()
            
            logger.debug(f"Learned new pattern '{pattern_id}' of type '{pattern_type}'")
            return pattern_id
            
        except Exception as e:
            logger.error(f"Failed to learn pattern: {e}")
            return ""
    
    async def match_against_patterns(self, query_data: Any) -> List[PatternMatchResult]:
        """Match query data against learned patterns."""
        try:
            # Convert query to text
            if isinstance(query_data, dict):
                query_text = json.dumps(query_data)
            else:
                query_text = str(query_data)
            
            # Check cache
            cache_key = hash(query_text)
            if cache_key in self.match_cache:
                return self.match_cache[cache_key]
            
            if not self.patterns:
                return []
            
            # Generate query embedding
            query_embedding = self.embedding_generator.generate_embedding(query_text)
            
            # Calculate similarities
            matches = []
            for pattern_id, pattern in self.patterns.items():
                similarity = self._cosine_similarity(query_embedding, pattern.embedding)
                
                if similarity >= self.similarity_threshold:
                    confidence = min(similarity * 1.2, 1.0)  # Boost confidence slightly
                    
                    match = PatternMatchResult(
                        pattern_id=pattern_id,
                        similarity_score=similarity,
                        pattern_data=pattern.to_dict(),
                        confidence=confidence,
                        metadata={
                            "pattern_type": pattern.pattern_type,
                            "usage_count": pattern.usage_count,
                            "success_rate": pattern.success_rate
                        }
                    )
                    matches.append(match)
                    
                    # Update pattern usage
                    pattern.usage_count += 1
                    pattern.updated_at = datetime.now()
            
            # Sort by similarity score
            matches.sort(key=lambda x: x.similarity_score, reverse=True)
            
            # Update statistics
            self.match_statistics["total_queries"] += 1
            if matches:
                self.match_statistics["successful_matches"] += 1
            
            # Cache results
            self.match_cache[cache_key] = matches
            
            return matches
            
        except Exception as e:
            logger.error(f"Pattern matching failed: {e}")
            return []
    
    async def get_pattern_info(self, pattern_id: str) -> Dict[str, Any]:
        """Get information about a specific pattern."""
        if pattern_id not in self.patterns:
            return {}
        
        pattern = self.patterns[pattern_id]
        info = pattern.to_dict()
        
        # Add cluster information
        for cluster_id, cluster in self.pattern_clusters.items():
            if pattern_id in cluster.patterns:
                info["cluster_id"] = cluster_id
                info["cluster_type"] = cluster.cluster_type
                info["cluster_description"] = cluster.description
                break
        
        return info
    
    async def delete_pattern(self, pattern_id: str) -> bool:
        """Delete a learned pattern."""
        try:
            if pattern_id not in self.patterns:
                return False
            
            pattern = self.patterns[pattern_id]
            
            # Remove from type index
            self.type_index[pattern.pattern_type].discard(pattern_id)
            
            # Remove from clusters
            for cluster in self.pattern_clusters.values():
                if pattern_id in cluster.patterns:
                    cluster.patterns.remove(pattern_id)
            
            # Remove pattern
            del self.patterns[pattern_id]
            
            # Update embedding matrix
            self._update_embedding_matrix()
            
            # Clear cache
            self.match_cache.clear()
            
            logger.debug(f"Deleted pattern '{pattern_id}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete pattern '{pattern_id}': {e}")
            return False
    
    # Helper methods
    
    def _extract_pattern_features(self, text: str, pattern_type: str) -> Dict[str, Any]:
        """Extract features from pattern text."""
        features = {
            "length": len(text),
            "word_count": len(text.split()),
            "has_code_indicators": any(indicator in text.lower() for indicator in ['def ', 'class ', 'import ', 'function']),
            "has_task_indicators": any(verb in text.lower() for verb in ['create', 'implement', 'build', 'develop']),
            "complexity_level": "high" if len(text.split()) > 50 else "medium" if len(text.split()) > 20 else "low"
        }
        
        if pattern_type == "code":
            features.update({
                "has_functions": "def " in text or "function" in text,
                "has_classes": "class " in text,
                "has_imports": "import " in text,
                "language_indicators": [lang for lang in ['python', 'javascript', 'java', 'cpp'] if lang in text.lower()]
            })
        
        return features
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return np.dot(vec1, vec2) / (norm1 * norm2)
    
    def _update_embedding_matrix(self) -> None:
        """Update the embedding matrix for fast similarity computation."""
        if not self.patterns:
            self.embedding_matrix = None
            self.pattern_ids_list = []
            return
        
        embeddings = []
        pattern_ids = []
        
        for pattern_id, pattern in self.patterns.items():
            embeddings.append(pattern.embedding)
            pattern_ids.append(pattern_id)
        
        self.embedding_matrix = np.array(embeddings)
        self.pattern_ids_list = pattern_ids
    
    def _rebuild_indices(self) -> None:
        """Rebuild pattern indices after loading."""
        self.type_index.clear()
        
        for pattern_id, pattern in self.patterns.items():
            self.type_index[pattern.pattern_type].add(pattern_id)
        
        self._update_embedding_matrix()
    
    async def _auto_cluster_patterns(self) -> None:
        """Automatically cluster similar patterns."""
        if len(self.patterns) < self.min_cluster_size:
            return
        
        try:
            # Simple clustering based on similarity
            pattern_ids = list(self.patterns.keys())
            embeddings = [self.patterns[pid].embedding for pid in pattern_ids]
            
            clusters = []
            used_patterns = set()
            
            for i, pattern_id in enumerate(pattern_ids):
                if pattern_id in used_patterns:
                    continue
                
                # Find similar patterns
                cluster_patterns = [pattern_id]
                used_patterns.add(pattern_id)
                
                for j, other_id in enumerate(pattern_ids[i+1:], i+1):
                    if other_id in used_patterns:
                        continue
                    
                    similarity = self._cosine_similarity(embeddings[i], embeddings[j])
                    if similarity >= self.cluster_similarity_threshold:
                        cluster_patterns.append(other_id)
                        used_patterns.add(other_id)
                
                # Create cluster if it has enough patterns
                if len(cluster_patterns) >= self.min_cluster_size:
                    cluster_id = str(uuid.uuid4())
                    centroid = np.mean([embeddings[pattern_ids.index(pid)] for pid in cluster_patterns], axis=0)
                    
                    cluster = PatternCluster(
                        cluster_id=cluster_id,
                        patterns=cluster_patterns,
                        centroid=centroid,
                        cluster_type="auto",
                        description=f"Auto-generated cluster with {len(cluster_patterns)} patterns"
                    )
                    
                    self.pattern_clusters[cluster_id] = cluster
                    clusters.append(cluster)
            
            logger.debug(f"Auto-clustering created {len(clusters)} clusters from {len(self.patterns)} patterns")
            
        except Exception as e:
            logger.error(f"Auto-clustering failed: {e}")