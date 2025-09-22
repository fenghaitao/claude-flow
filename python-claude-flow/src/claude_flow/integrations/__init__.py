"""
External integrations for Claude-Flow

This module provides integrations with external services:
- Claude AI integration with connection pooling
- GitHub operations and repository management
- Docker and deployment services
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .claude.claude_client import ClaudeClient
    from .github.github_client import GitHubClient

__all__ = [
    "ClaudeClient",
    "GitHubClient",
]

# Lazy imports to avoid circular dependencies
def __getattr__(name: str):
    if name == "ClaudeClient":
        from .claude.claude_client import ClaudeClient
        return ClaudeClient
    elif name == "GitHubClient":
        from .github.github_client import GitHubClient
        return GitHubClient
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")