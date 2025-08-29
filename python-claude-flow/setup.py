#!/usr/bin/env python3
"""
Setup script for Claude-Flow Python port
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = ""
if readme_path.exists():
    long_description = readme_path.read_text(encoding="utf-8")

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
install_requires = []
if requirements_path.exists():
    install_requires = [
        line.strip() for line in requirements_path.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="claude-flow",
    version="2.0.0-alpha.90",
    description="Enterprise-grade AI agent orchestration platform (Python port)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="rUv",
    author_email="info@ruv.net",
    url="https://github.com/ruvnet/claude-code-flow",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    install_requires=install_requires,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
        ],
        "ui": [
            "blessed>=1.20.0",
            "prompt-toolkit>=3.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "claude-flow=claude_flow.cli.main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords=[
        "claude", "ai", "agent", "orchestration", "mcp", "workflow",
        "automation", "swarm", "ruv-swarm", "github", "docker",
        "enterprise", "coordination", "multi-agent", "neural-networks",
        "cli", "tools", "alpha"
    ],
    project_urls={
        "Homepage": "https://github.com/ruvnet/claude-code-flow",
        "Repository": "https://github.com/ruvnet/claude-code-flow",
        "Documentation": "https://github.com/ruvnet/claude-code-flow#readme",
        "Issues": "https://github.com/ruvnet/claude-code-flow/issues",
    },
)
