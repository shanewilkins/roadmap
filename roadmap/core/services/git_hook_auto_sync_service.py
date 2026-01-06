"""Auto-sync service for Git hooks - handles GitHub sync on Git events.

This service integrates with Git hooks to automatically sync issues with GitHub
when Git events occur (commits, checkouts, merges). It provides:
- Post-commit auto-sync with optional user confirmation
- Configurable auto-sync behavior
- Sync history tracking via SyncMetadataService
- Smart conflict resolution
"""

from pathlib import Path
from typing import Any

from roadmap.adapters.sync.backend_factory import get_sync_backend
from roadmap.adapters.sync.sync_cache_orchestrator import SyncCacheOrchestrator
from roadmap.common.console import get_console
from roadmap.core.services.github_integration_service import GitHubIntegrationService
from roadmap.core.services.sync_metadata_service import SyncMetadataService


class GitHookAutoSyncConfig:
    """Configuration for git hook auto-sync behavior."""

    def __init__(
        self,
        auto_sync_enabled: bool = False,
        sync_on_commit: bool = False,
        sync_on_checkout: bool = False,
        sync_on_merge: bool = False,
        confirm_before_sync: bool = True,
        force_local: bool = False,
        force_github: bool = False,
    ):
        """Initialize auto-sync configuration.

        Args:
            auto_sync_enabled: Master switch for all auto-sync
            sync_on_commit: Auto-sync after commits
            sync_on_checkout: Auto-sync on branch changes
            sync_on_merge: Auto-sync on merge operations
            confirm_before_sync: Ask user before syncing
            force_local: Resolve conflicts by keeping local changes
            force_github: Resolve conflicts by keeping GitHub changes
        """
        self.auto_sync_enabled = auto_sync_enabled
        self.sync_on_commit = sync_on_commit
        self.sync_on_checkout = sync_on_checkout
        self.sync_on_merge = sync_on_merge
        self.confirm_before_sync = confirm_before_sync
        self.force_local = force_local
        self.force_github = force_github

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "auto_sync_enabled": self.auto_sync_enabled,
            "sync_on_commit": self.sync_on_commit,
            "sync_on_checkout": self.sync_on_checkout,
            "sync_on_merge": self.sync_on_merge,
            "confirm_before_sync": self.confirm_before_sync,
            "force_local": self.force_local,
            "force_github": self.force_github,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GitHookAutoSyncConfig":
        """Create from dictionary (loaded from storage)."""
        return cls(
            auto_sync_enabled=data.get("auto_sync_enabled", False),
            sync_on_commit=data.get("sync_on_commit", False),
            sync_on_checkout=data.get("sync_on_checkout", False),
            sync_on_merge=data.get("sync_on_merge", False),
            confirm_before_sync=data.get("confirm_before_sync", True),
            force_local=data.get("force_local", False),
            force_github=data.get("force_github", False),
        )


class GitHookAutoSyncService:
    """Service for handling automatic GitHub sync on Git events."""

    def __init__(self, core):
        """Initialize auto-sync service.

        Args:
            core: RoadmapCore instance
        """
        self.core = core
        self.console = get_console()
        self.metadata_service = SyncMetadataService(core)
        self.config = GitHookAutoSyncConfig()

    def set_config(self, config: GitHookAutoSyncConfig) -> None:
        """Set auto-sync configuration.

        Args:
            config: GitHookAutoSyncConfig instance
        """
        self.config = config

    def should_sync_on_event(self, event: str) -> bool:
        """Check if sync should occur for a given event.

        Args:
            event: Event name ('commit', 'checkout', 'merge')

        Returns:
            True if auto-sync is enabled and configured for this event
        """
        if not self.config.auto_sync_enabled:
            return False

        event_map = {
            "commit": self.config.sync_on_commit,
            "checkout": self.config.sync_on_checkout,
            "merge": self.config.sync_on_merge,
        }

        return event_map.get(event, False)

    def auto_sync_on_commit(
        self, commit_sha: str | None = None, confirm: bool = True
    ) -> bool:
        """Automatically sync issues on git commit.

        Args:
            commit_sha: Git commit SHA (optional, for logging)
            confirm: Whether to ask for confirmation

        Returns:
            True if sync completed successfully
        """
        if not self.should_sync_on_event("commit"):
            return False

        return self._perform_auto_sync(
            event="commit",
            commit_sha=commit_sha,
            confirm=confirm or self.config.confirm_before_sync,
        )

    def auto_sync_on_checkout(
        self, branch: str | None = None, confirm: bool = True
    ) -> bool:
        """Automatically sync issues on branch checkout.

        Args:
            branch: Branch name (optional, for logging)
            confirm: Whether to ask for confirmation

        Returns:
            True if sync completed successfully
        """
        if not self.should_sync_on_event("checkout"):
            return False

        return self._perform_auto_sync(
            event="checkout",
            branch=branch,
            confirm=confirm or self.config.confirm_before_sync,
        )

    def auto_sync_on_merge(
        self, commit_sha: str | None = None, confirm: bool = True
    ) -> bool:
        """Automatically sync issues on merge.

        Args:
            commit_sha: Merge commit SHA (optional, for logging)
            confirm: Whether to ask for confirmation

        Returns:
            True if sync completed successfully
        """
        if not self.should_sync_on_event("merge"):
            return False

        return self._perform_auto_sync(
            event="merge",
            commit_sha=commit_sha,
            confirm=confirm or self.config.confirm_before_sync,
        )

    def _perform_auto_sync(
        self,
        event: str,
        commit_sha: str | None = None,
        branch: str | None = None,
        confirm: bool = True,
    ) -> bool:
        """Internal method to perform auto-sync.

        Args:
            event: Event type ('commit', 'checkout', 'merge')
            commit_sha: Git commit SHA if applicable
            branch: Branch name if applicable
            confirm: Whether to ask for confirmation

        Returns:
            True if sync completed successfully
        """
        try:
            roadmap_root = Path.cwd()

            # Resolve GitHub config
            gh_service = GitHubIntegrationService(
                roadmap_root, roadmap_root / ".github/config.json"
            )
            config_result = gh_service.get_github_config()

            # Handle both tuple (real code) and dict (mocked code) returns
            if isinstance(config_result, tuple):
                owner, repo, token = config_result
                config = {"owner": owner, "repo": repo, "token": token}
            else:
                config = config_result

            if not config:
                # GitHub not configured - silently skip
                return False

            # Get linked issues
            linked_issues = [
                issue
                for issue in self.core.issues.all()
                if getattr(issue, "github_issue", None)
            ]

            if not linked_issues:
                # No linked issues - nothing to sync
                return False

            # Display what will be synced (brief, non-intrusive)
            self.console.print(f"[dim]🔄 Auto-syncing issues ({event})...[/dim]")

            # Get GitHub backend for sync
            backend = get_sync_backend("github", self.core, config)
            if not backend:
                self.console.print(
                    "[yellow]  ⚠️  GitHub backend not available - skipping sync[/yellow]"
                )
                return False

            # Create cache orchestrator for actual sync (uses three-way merge)
            from roadmap.core.services.sync_conflict_resolver import (
                SyncConflictResolver,
            )
            from roadmap.core.services.sync_state_comparator import (
                SyncStateComparator,
            )

            orchestrator = SyncCacheOrchestrator(
                self.core,
                backend,
                state_comparator=SyncStateComparator(),
                conflict_resolver=SyncConflictResolver(),
                show_progress=False,  # Silent mode for hooks
            )

            # Run sync detection (dry-run first to preview)
            report = orchestrator.sync_all_issues(
                dry_run=True,
                force_local=self.config.force_local,
                force_remote=self.config.force_github,
            )

            if not report.changes:
                self.console.print("[dim]  ✓ No changes to sync[/dim]")
                return True

            # Handle conflicts
            if report.conflicts_detected > 0:
                if self.config.force_local:
                    self.console.print(
                        "[dim]  ⚠️  Resolving conflicts with --force-local[/dim]"
                    )
                elif self.config.force_github:
                    self.console.print(
                        "[dim]  ⚠️  Resolving conflicts with --force-github[/dim]"
                    )
                else:
                    # Cannot proceed without conflict resolution
                    self.console.print(
                        "[yellow]  ⚠️  Conflicts detected - skipping sync. "
                        "Use 'roadmap sync --force-local' or '--force-remote' to resolve.[/yellow]"
                    )
                    return False

            # Ask for confirmation if enabled
            if confirm:
                self.console.print(f"  • {len(report.changes)} change(s) to apply")
                response = input("  Continue with sync? [y/N]: ").strip().lower() == "y"
                if not response:
                    self.console.print("[dim]  Sync cancelled[/dim]")
                    return False

            # Apply changes (dry-run=False)
            apply_report = orchestrator.sync_all_issues(
                dry_run=False,
                force_local=self.config.force_local,
                force_remote=self.config.force_github,
                show_progress=False,
            )

            if apply_report.error:
                self.console.print(f"[red]  ✗ Sync failed: {apply_report.error}[/red]")
                return False

            # Success
            self.console.print("[green]  ✓ Synced successfully[/green]")
            return True

        except Exception as e:
            # Log error but don't interrupt the git operation
            self.console.print(f"[yellow]  ⚠️  Auto-sync error: {str(e)}[/yellow]")
            return False

    def get_config(self) -> GitHookAutoSyncConfig:
        """Get current auto-sync configuration.

        Returns:
            Current GitHookAutoSyncConfig
        """
        return self.config

    def get_sync_stats(self) -> dict[str, Any]:
        """Get sync statistics from metadata service.

        Returns:
            Dictionary with sync statistics
        """
        all_issues = self.core.issues.all()
        linked_issues = [
            issue for issue in all_issues if getattr(issue, "github_issue", None)
        ]
        return self.metadata_service.get_statistics(linked_issues)

    def load_config_from_file(self, config_path: Path) -> bool:
        """Load auto-sync config from file.

        Args:
            config_path: Path to config file

        Returns:
            True if config loaded successfully
        """
        try:
            import json

            if not config_path.exists():
                return False

            with open(config_path) as f:
                data = json.load(f)

            config_data = data.get("auto_sync", {})
            if config_data:
                self.config = GitHookAutoSyncConfig.from_dict(config_data)
                return True

            return False
        except Exception:
            return False

    def save_config_to_file(self, config_path: Path) -> bool:
        """Save auto-sync config to file.

        Args:
            config_path: Path to config file

        Returns:
            True if config saved successfully
        """
        try:
            import json

            # Ensure parent directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)

            # Load existing config or create new
            config_dict = {}
            if config_path.exists():
                with open(config_path) as f:
                    config_dict = json.load(f)

            # Update auto_sync section
            config_dict["auto_sync"] = self.config.to_dict()

            # Save back to file
            with open(config_path, "w") as f:
                json.dump(config_dict, f, indent=2)

            return True
        except Exception:
            return False
