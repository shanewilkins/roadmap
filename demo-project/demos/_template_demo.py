#!/usr/bin/env python3
"""
Demo Template for Roadmap CLI Features
=======================================

This is a template for creating new demo scripts in the demos/ directory.

Usage:
    python demos/your_demo_name.py

Features demonstrated:
    - Feature 1
    - Feature 2
    - Feature 3
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import roadmap modules if needed
# from roadmap.models import Issue, Milestone, Status, Priority
# from roadmap.core import RoadmapCore
# from roadmap.github_client import GitHubClient


def main():
    """Demonstrate the feature."""
    print("🎯 Feature Name Demo")
    print("=" * 50)
    print()

    print("🆕 New Feature Overview")
    print("-" * 25)
    print("Description of what this feature does...")
    print()

    print("💻 Command Examples")
    print("-" * 20)
    print("roadmap command --option value")
    print("roadmap command --another-option")
    print()

    print("🎨 Visual Examples")
    print("-" * 18)
    print("Show what the output looks like...")
    print()

    print("🚀 Workflow Benefits")
    print("-" * 20)
    print("✅ Benefit 1")
    print("✅ Benefit 2")
    print("✅ Benefit 3")
    print()

    print("🧪 Try It Out")
    print("-" * 12)
    print("1. roadmap init")
    print("2. roadmap command --setup")
    print("3. roadmap command --demo")
    print()

    print("=" * 50)
    print("🎉 Feature demo complete!")
    print("Ready to enhance your workflow.")


if __name__ == "__main__":
    main()
