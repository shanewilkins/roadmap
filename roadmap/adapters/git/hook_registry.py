"""Hook registry and detection for Git hooks."""

from pathlib import Path
from typing import Any

from structlog import get_logger

logger = get_logger()


class HookRegistry:
    """Registry and metadata for available Git hooks."""

    AVAILABLE_HOOKS = ["post-commit", "pre-push", "post-merge", "post-checkout"]

    @classmethod
    def get_available_hooks(cls) -> list[str]:
        """Get list of all available hook names."""
        return cls.AVAILABLE_HOOKS.copy()

    @classmethod
    def is_valid_hook(cls, hook_name: str) -> bool:
        """Check if hook name is valid."""
        return hook_name in cls.AVAILABLE_HOOKS

    @classmethod
    def validate_hooks(cls, hooks: list[str] | None) -> list[str]:
        """Validate and filter hook list.

        Args:
            hooks: List of hook names to validate

        Returns:
            Validated list of hook names
        """
        if hooks is None:
            return cls.get_available_hooks()
        return [h for h in hooks if cls.is_valid_hook(h)]


class HookStatus:
    """Utility for checking hook installation status."""

    @staticmethod
    def get_hook_file(hook_name: str, hooks_dir: Path) -> Path:
        """Get the file path for a hook."""
        return hooks_dir / hook_name

    @staticmethod
    def is_hook_installed(hook_file: Path) -> bool:
        """Check if hook file exists and is readable."""
        if not hook_file.exists():
            return False
        try:
            hook_file.read_text()
            return True
        except Exception as e:
            logger.error(
                "hook_install_check_failed", error=str(e), severity="operational"
            )
            return False

    @staticmethod
    def is_roadmap_hook(hook_file: Path) -> bool:
        """Check if hook file is a roadmap hook."""
        if not hook_file.exists():
            return False
        try:
            content = hook_file.read_text()
            return "roadmap-hook" in content
        except Exception as e:
            logger.error(
                "hook_content_check_failed", error=str(e), severity="operational"
            )
            return False

    @staticmethod
    def is_executable(hook_file: Path) -> bool:
        """Check if hook file is executable."""
        if not hook_file.exists():
            return False
        try:
            return bool(hook_file.stat().st_mode & 0o111)
        except Exception as e:
            logger.debug("hook_executable_check_failed", error=str(e))
            return False

    @staticmethod
    def get_status_dict(hook_name: str, hook_file: Path) -> dict[str, Any]:
        """Get complete status dictionary for a hook."""
        return {
            "installed": HookStatus.is_hook_installed(hook_file),
            "is_roadmap_hook": HookStatus.is_roadmap_hook(hook_file),
            "executable": HookStatus.is_executable(hook_file),
            "file_exists": hook_file.exists(),
            "file_path": str(hook_file) if hook_file.exists() else None,
        }
