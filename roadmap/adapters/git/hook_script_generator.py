"""Hook script generation for Git hooks."""

import shutil


class HookContentGenerator:
    """Generates content for Git hook bash scripts."""

    BASH_TEMPLATE = """#!/bin/bash
# roadmap-hook: {hook_name}
# Auto-generated Git hook for roadmap integration

# Get the directory of this script
HOOK_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
REPO_ROOT="$(cd "$HOOK_DIR/../.." && pwd)"

# Change to repository root
cd "$REPO_ROOT"

# Execute roadmap hook handler
{python_exec} << 'PYTHON_HOOK_EOF'
import sys
sys.path.insert(0, '.')
try:
    from roadmap.adapters.git.git_hooks_manager import GitHookManager
    from roadmap.infrastructure.core import RoadmapCore
    core = RoadmapCore()
    hook_manager = GitHookManager(core)
    getattr(hook_manager, "{handler_name}")()
except Exception as e:
    # Silent fail to avoid breaking Git operations
    pass
PYTHON_HOOK_EOF
"""

    @staticmethod
    def get_python_executable() -> str:
        """Get the path to Python executable."""
        return shutil.which("python") or shutil.which("python3") or "python"

    @classmethod
    def generate(cls, hook_name: str) -> str:
        """Generate hook script content for given hook name.

        Args:
            hook_name: Name of the hook (e.g., 'post-commit')

        Returns:
            Complete bash script content for the hook
        """
        handler_name = hook_name.replace("-", "_")
        python_exec = cls.get_python_executable()

        return cls.BASH_TEMPLATE.format(
            hook_name=hook_name,
            handler_name=handler_name,
            python_exec=python_exec,
        )
