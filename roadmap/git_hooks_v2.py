"""Git hooks v2 for automatic synchronization.

This module replaces the manual sync functionality with automatic
git hooks that sync issues and milestones on git operations.
"""

from datetime import datetime
from pathlib import Path

from git import Repo

from .database import get_state_manager
from .logging import get_logger, log_operation

logger = get_logger(__name__)


class GitHooksError(Exception):
    """Exception for git hooks operations."""

    pass


class AutoSyncManager:
    """Manages automatic synchronization via git hooks."""

    def __init__(self, repo_path: str | Path | None = None):
        """Initialize auto-sync manager.

        Args:
            repo_path: Path to git repository. Defaults to current directory.
        """
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.hooks_dir = self.repo_path / ".git" / "hooks"

        try:
            self.repo = Repo(str(self.repo_path))
        except Exception as e:
            raise GitHooksError(f"Failed to initialize git repository: {e}") from e

        logger.info("Initialized auto-sync manager", repo_path=str(self.repo_path))

    @log_operation("install_hooks")
    def install_hooks(self, force: bool = False) -> bool:
        """Install git hooks for auto-sync.

        Args:
            force: Overwrite existing hooks

        Returns:
            True if hooks were installed successfully
        """
        if not self.hooks_dir.exists():
            raise GitHooksError("Git hooks directory not found")

        hooks_to_install = {
            "pre-commit": self._get_pre_commit_hook(),
            "post-commit": self._get_post_commit_hook(),
            "post-checkout": self._get_post_checkout_hook(),
            "post-merge": self._get_post_merge_hook(),
        }

        installed_hooks = []

        for hook_name, hook_content in hooks_to_install.items():
            hook_path = self.hooks_dir / hook_name

            if hook_path.exists() and not force:
                logger.warning(f"Hook {hook_name} already exists, skipping")
                continue

            try:
                hook_path.write_text(hook_content)
                hook_path.chmod(0o755)  # Make executable
                installed_hooks.append(hook_name)
                logger.info(f"Installed hook: {hook_name}")
            except Exception as e:
                logger.error(f"Failed to install hook {hook_name}", error=str(e))
                return False

        logger.info("Git hooks installed successfully", hooks=installed_hooks)
        return True

    def uninstall_hooks(self) -> bool:
        """Uninstall roadmap git hooks."""
        hooks_to_remove = ["pre-commit", "post-commit", "post-checkout", "post-merge"]
        removed_hooks = []

        for hook_name in hooks_to_remove:
            hook_path = self.hooks_dir / hook_name

            if hook_path.exists():
                try:
                    # Check if it's our hook by looking for roadmap marker
                    content = hook_path.read_text()
                    if "# ROADMAP AUTO-SYNC HOOK" in content:
                        hook_path.unlink()
                        removed_hooks.append(hook_name)
                        logger.info(f"Removed hook: {hook_name}")
                except Exception as e:
                    logger.error(f"Failed to remove hook {hook_name}", error=str(e))
                    return False

        logger.info("Git hooks removed successfully", hooks=removed_hooks)
        return True

    def _get_pre_commit_hook(self) -> str:
        """Generate pre-commit hook script."""
        return f"""#!/bin/sh
# ROADMAP AUTO-SYNC HOOK
# This hook validates roadmap data before commits

python3 -c "
import sys
sys.path.insert(0, '{self.repo_path}')

try:
    from roadmap.git_hooks_v2 import validate_roadmap_data
    if not validate_roadmap_data():
        print('ERROR: Roadmap data validation failed')
        sys.exit(1)
except Exception as e:
    print(f'WARNING: Roadmap validation error: {{e}}')
    # Don't fail the commit on validation errors, just warn
"
"""

    def _get_post_commit_hook(self) -> str:
        """Generate post-commit hook script."""
        return f"""#!/bin/sh
# ROADMAP AUTO-SYNC HOOK
# This hook syncs roadmap data after commits

python3 -c "
import sys
sys.path.insert(0, '{self.repo_path}')

try:
    from roadmap.git_hooks_v2 import sync_after_commit
    sync_after_commit()
except Exception as e:
    print(f'WARNING: Auto-sync after commit failed: {{e}}')
    # Don't fail on sync errors
" &
"""

    def _get_post_checkout_hook(self) -> str:
        """Generate post-checkout hook script."""
        return f"""#!/bin/sh
# ROADMAP AUTO-SYNC HOOK
# This hook syncs roadmap data after branch checkouts

python3 -c "
import sys
sys.path.insert(0, '{self.repo_path}')

try:
    from roadmap.git_hooks_v2 import sync_after_checkout
    sync_after_checkout('$1', '$2', '$3')
except Exception as e:
    print(f'WARNING: Auto-sync after checkout failed: {{e}}')
" &
"""

    def _get_post_merge_hook(self) -> str:
        """Generate post-merge hook script."""
        return f"""#!/bin/sh
# ROADMAP AUTO-SYNC HOOK
# This hook syncs roadmap data after merges

python3 -c "
import sys
sys.path.insert(0, '{self.repo_path}')

try:
    from roadmap.git_hooks_v2 import sync_after_merge
    sync_after_merge('$1')
except Exception as e:
    print(f'WARNING: Auto-sync after merge failed: {{e}}')
" &
"""

    def check_hooks_status(self) -> dict[str, bool]:
        """Check which hooks are installed."""
        hooks = ["pre-commit", "post-commit", "post-checkout", "post-merge"]
        status = {}

        for hook_name in hooks:
            hook_path = self.hooks_dir / hook_name
            if hook_path.exists():
                try:
                    content = hook_path.read_text()
                    status[hook_name] = "# ROADMAP AUTO-SYNC HOOK" in content
                except Exception:
                    status[hook_name] = False
            else:
                status[hook_name] = False

        return status


# Hook handler functions (called by the actual git hooks)


def validate_roadmap_data() -> bool:
    """Validate roadmap data before commit."""
    try:
        state_manager = get_state_manager()
        if not state_manager.is_initialized():
            logger.info("Database not initialized, skipping validation")
            return True

        # Basic validation - ensure database is accessible
        projects = state_manager.list_projects()
        logger.debug(f"Validated {len(projects)} projects")
        return True

    except Exception as e:
        logger.error("Roadmap data validation failed", error=str(e))
        return False


@log_operation("sync_after_commit")
def sync_after_commit():
    """Sync roadmap data after commit."""
    try:
        state_manager = get_state_manager()
        if not state_manager.is_initialized():
            logger.info("Database not initialized, skipping sync")
            return

        # Get current commit hash
        repo = Repo(Path.cwd())
        commit_hash = str(repo.head.commit)

        # Update sync state
        state_manager.set_sync_state("last_commit_hash", commit_hash)
        state_manager.set_sync_state("last_sync_time", str(datetime.now()))

        logger.info("Synced after commit", commit=commit_hash[:8])

    except Exception as e:
        logger.error("Failed to sync after commit", error=str(e))


@log_operation("sync_after_checkout")
def sync_after_checkout(prev_head: str, new_head: str, branch_flag: str):
    """Sync roadmap data after checkout."""
    try:
        state_manager = get_state_manager()
        if not state_manager.is_initialized():
            logger.info("Database not initialized, skipping sync")
            return

        # Update sync state
        state_manager.set_sync_state("current_branch", new_head)
        state_manager.set_sync_state("last_checkout_time", str(datetime.now()))

        logger.info(
            "Synced after checkout", from_head=prev_head[:8], to_head=new_head[:8]
        )

    except Exception as e:
        logger.error("Failed to sync after checkout", error=str(e))


@log_operation("sync_after_merge")
def sync_after_merge(merge_flag: str):
    """Sync roadmap data after merge."""
    try:
        state_manager = get_state_manager()
        if not state_manager.is_initialized():
            logger.info("Database not initialized, skipping sync")
            return

        # Get current commit hash
        repo = Repo(Path.cwd())
        commit_hash = str(repo.head.commit)

        # Update sync state
        state_manager.set_sync_state("last_merge_commit", commit_hash)
        state_manager.set_sync_state("last_merge_time", str(datetime.now()))

        logger.info("Synced after merge", commit=commit_hash[:8])

    except Exception as e:
        logger.error("Failed to sync after merge", error=str(e))


def setup_auto_sync(repo_path: str | Path | None = None, force: bool = False) -> bool:
    """Set up automatic synchronization via git hooks.

    Args:
        repo_path: Path to git repository
        force: Overwrite existing hooks

    Returns:
        True if setup was successful
    """
    try:
        manager = AutoSyncManager(repo_path)
        return manager.install_hooks(force=force)
    except Exception as e:
        logger.error("Failed to set up auto-sync", error=str(e))
        return False


def remove_auto_sync(repo_path: str | Path | None = None) -> bool:
    """Remove automatic synchronization hooks.

    Args:
        repo_path: Path to git repository

    Returns:
        True if removal was successful
    """
    try:
        manager = AutoSyncManager(repo_path)
        return manager.uninstall_hooks()
    except Exception as e:
        logger.error("Failed to remove auto-sync", error=str(e))
        return False
