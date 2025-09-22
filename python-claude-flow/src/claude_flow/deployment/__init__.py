"""
Deployment system for Claude-Flow

This module provides deployment and orchestration capabilities:
- Docker containerization support
- Kubernetes manifests and Helm charts
- Production deployment tools
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .docker_manager import DockerManager
    from .kubernetes_manager import KubernetesManager

__all__ = [
    "DockerManager",
    "KubernetesManager",
]

# Lazy imports to avoid circular dependencies
def __getattr__(name: str):
    if name == "DockerManager":
        from .docker_manager import DockerManager
        return DockerManager
    elif name == "KubernetesManager":
        from .kubernetes_manager import KubernetesManager
        return KubernetesManager
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")