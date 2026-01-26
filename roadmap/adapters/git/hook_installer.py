"""Hook installation and removal operations."""

from pathlib import Path

from structlog import get_logger

from .hook_registry import HookRegistry
from .hook_script_generator import HookContentGenerator

logger = get_logger()


class HookInstaller:
    """Handles installation and uninstallation of Git hooks."""

    def __init__(self, hooks_dir: Path | None):
        """Initialize with Git hooks directory.

        Args:
            hooks_dir: Path to .git/hooks directory, or None if not in repo
        """
        self.hooks_dir = hooks_dir

    def can_install(self) -> bool:
        """Check if hooks can be installed in this repository."""
        return self.hooks_dir is not None and self.hooks_dir.exists()

    def install(self, hooks: list[str] | None = None) -> bool:
        """Install specified hooks.

        Args:
            hooks: List of hook names to install, or None for all

        Returns:
            True if successful
        """
        if not self.can_install():
            return False

        hooks_to_install = HookRegistry.validate_hooks(hooks)

        try:
            for hook_name in hooks_to_install:
                self._install_single_hook(hook_name)
            return True
        except Exception as e:
            print(f"Error installing hooks: {e}")
            return False

    def uninstall(self, hooks: list[str] | None = None) -> bool:
        """Uninstall specified hooks (or all if not specified).

        Args:
            hooks: List of hook names to uninstall, or None for all

        Returns:
            True if successful
        """
        if not self.hooks_dir:
            return False

        hooks_to_remove = HookRegistry.validate_hooks(hooks)

        try:
            for hook_name in hooks_to_remove:
                self._uninstall_single_hook(hook_name)
            return True
        except Exception as e:
            logger.error("hook_uninstall_failed", error=str(e), severity="operational")
            return False

    def _install_single_hook(self, hook_name: str) -> None:
        """Install a single hook.

        Args:
            hook_name: Name of the hook to install
        """
        if not self.hooks_dir:
            return

        hook_file = self.hooks_dir / hook_name
        content = HookContentGenerator.generate(hook_name)

        # Write hook file
        hook_file.write_text(content)

        # Make it executable
        hook_file.chmod(0o755)

    def _uninstall_single_hook(self, hook_name: str) -> None:
        """Uninstall a single hook (if it's a roadmap hook).

        Args:
            hook_name: Name of the hook to uninstall
        """
        if not self.hooks_dir:
            return

        hook_file = self.hooks_dir / hook_name
        if not hook_file.exists():
            return

        # Only remove if it's our hook
        content = hook_file.read_text()
        if "roadmap-hook" in content:
            hook_file.unlink()
