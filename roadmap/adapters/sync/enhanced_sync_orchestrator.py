"""Enhanced sync orchestrator that uses git-based baselines.

This module extends GenericSyncOrchestrator with intelligent baseline management
using git history and YAML sync_metadata instead of database state tables.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from structlog import get_logger

from roadmap.adapters.persistence.parser.issue import IssueParser
from roadmap.adapters.sync.generic_sync_orchestrator import GenericSyncOrchestrator
from roadmap.core.models.sync_state import SyncState
from roadmap.core.services.baseline_state_retriever import BaselineStateRetriever

logger = get_logger(__name__)


class EnhancedSyncOrchestrator(GenericSyncOrchestrator):
    """Sync orchestrator using git history and YAML-based baseline retrieval.

    This enhances the base GenericSyncOrchestrator with:
    1. Git history-based local baseline retrieval (no DB needed)
    2. YAML sync_metadata for remote baseline snapshots
    3. Intelligent baseline-less diff when no previous sync exists
    """

    def __init__(self, *args, **kwargs):
        """Initialize with baseline retriever."""
        super().__init__(*args, **kwargs)
        self.baseline_retriever = BaselineStateRetriever(self.core.issues_dir)
        self.sync_metadata_cache: dict[str, Any] = {}

    @property
    def issues_dir(self) -> Path:
        """Get issues directory from core."""
        # Navigate from roadmap_dir to issues directory
        roadmap_dir = self.core.roadmap_dir
        return roadmap_dir / "issues"

    def _build_baseline_state_from_git(
        self, last_synced: datetime | None
    ) -> SyncState | None:
        """Build baseline state by querying git history for each issue.

        Instead of loading from a sync_base_state database table, we reconstruct
        the baseline by reading each issue file as it existed at the last_synced
        timestamp.

        Args:
            last_synced: Timestamp of last sync (from sync_metadata)

        Returns:
            SyncState with issues reconstructed from git history, or None
        """
        if not last_synced:
            logger.debug(
                "baseline_no_last_synced",
                reason="first_sync_or_timestamp_missing",
            )
            return None

        try:
            logger.info(
                "baseline_state_reconstruction_start",
                last_synced=last_synced.isoformat(),
                reason="building_from_git_history",
            )

            baseline = SyncState(
                last_sync=last_synced,
                backend=self.backend.__class__.__name__.lower(),
            )

            # Get all current issue files
            try:
                local_issues = self.core.issues.list()
            except Exception as e:
                logger.warning(
                    "baseline_reconstruction_issue_list_failed",
                    error=str(e),
                )
                return None

            for issue in local_issues:
                try:
                    # Find the issue file
                    issue_file = self._find_issue_file(issue.id)
                    if not issue_file:
                        logger.debug(
                            "baseline_issue_file_not_found",
                            issue_id=issue.id,
                        )
                        continue

                    # Retrieve local baseline from git history
                    local_baseline = self.baseline_retriever.get_local_baseline(
                        issue_file, last_synced
                    )

                    if local_baseline:
                        baseline.issues[issue.id] = local_baseline
                        logger.debug(
                            "baseline_issue_reconstructed_from_git",
                            issue_id=issue.id,
                            status=local_baseline.status,
                        )
                    else:
                        logger.debug(
                            "baseline_issue_not_in_git_history",
                            issue_id=issue.id,
                            reason="file_did_not_exist_at_timestamp",
                        )

                except Exception as e:
                    logger.warning(
                        "baseline_reconstruction_issue_failed",
                        issue_id=issue.id,
                        error=str(e),
                    )
                    continue

            logger.info(
                "baseline_state_reconstruction_complete",
                reconstructed_count=len(baseline.issues),
                reason="using_git_history",
            )
            return baseline

        except Exception as e:
            logger.error(
                "baseline_state_reconstruction_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    def _build_baseline_state_from_sync_metadata(self) -> SyncState | None:
        """Build baseline state from sync_metadata YAML frontmatter.

        The remote baseline is stored in each issue's sync_metadata.remote_state,
        which represents the last-synced state from the remote backend.

        Args:
            None (uses all local issues)

        Returns:
            SyncState with remote baselines from sync_metadata
        """
        try:
            logger.debug(
                "baseline_remote_retrieval_start",
                reason="reading_sync_metadata_yaml",
            )

            # Get last_synced from first issue that has it
            last_synced_time = None
            try:
                local_issues = self.core.issues.list()
                for issue in local_issues:
                    issue_file = self._find_issue_file(issue.id)
                    if not issue_file:
                        continue

                    metadata = IssueParser.load_sync_metadata(issue_file)
                    if metadata and "last_synced" in metadata:
                        if isinstance(metadata["last_synced"], str):
                            last_synced_time = datetime.fromisoformat(
                                metadata["last_synced"]
                            )
                        else:
                            last_synced_time = metadata["last_synced"]
                        break
            except Exception as e:
                logger.warning(
                    "baseline_last_synced_extraction_failed",
                    error=str(e),
                )
                return None

            if not last_synced_time:
                logger.debug(
                    "baseline_no_last_synced_in_metadata",
                    reason="no_sync_metadata_found",
                )
                return None

            baseline = SyncState(
                last_sync=last_synced_time,
                backend="sync_metadata",
            )

            # Build from sync_metadata remote_state
            for issue in local_issues:
                try:
                    issue_file = self._find_issue_file(issue.id)
                    if not issue_file:
                        continue

                    remote_baseline = self.baseline_retriever.get_remote_baseline(
                        issue_file
                    )

                    if remote_baseline:
                        baseline.issues[issue.id] = remote_baseline
                        logger.debug(
                            "baseline_remote_loaded_from_metadata",
                            issue_id=issue.id,
                        )

                except Exception as e:
                    logger.warning(
                        "baseline_remote_retrieval_failed",
                        issue_id=issue.id,
                        error=str(e),
                    )
                    continue

            logger.info(
                "baseline_remote_retrieval_complete",
                count=len(baseline.issues),
                reason="from_sync_metadata_yaml",
            )
            return baseline

        except Exception as e:
            logger.error(
                "baseline_remote_retrieval_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    def _find_issue_file(self, issue_id: str) -> Path | None:
        """Find the actual file path for an issue.

        Issues can be in different directories based on milestone.

        Args:
            issue_id: Issue identifier

        Returns:
            Path to issue file, or None if not found
        """
        issues_dir = self.issues_dir
        if not issues_dir.exists():
            return None

        # Search in milestone directories and backlog
        search_dirs = [
            issues_dir / "backlog",
            issues_dir,  # Root level
        ]

        # Also search milestone directories
        for subdir in issues_dir.glob("*"):
            if subdir.is_dir() and subdir.name not in ["backlog", "archive"]:
                search_dirs.append(subdir)

        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            # Look for files matching issue_id prefix
            for file in search_dir.glob(f"{issue_id}-*.md"):
                return file

        return None

    def get_baseline_state(self) -> SyncState | None:
        """Get baseline state using git history and YAML metadata.

        Strategy:
        1. Try to load last_synced timestamp from any issue's sync_metadata
        2. Reconstruct local baseline from git history at that timestamp
        3. Load remote baseline from sync_metadata YAML

        Falls back to JSON file if available (for migration), then to no baseline.

        Returns:
            SyncState with local and remote baselines
        """
        try:
            logger.debug("baseline_state_retrieval_start")

            # First, try git-based approach
            remote_baseline = self._build_baseline_state_from_sync_metadata()

            if remote_baseline:
                # Now get local baseline from git history
                local_baseline = self._build_baseline_state_from_git(
                    remote_baseline.last_sync
                )

                if local_baseline:
                    # Merge: use git local baseline, keep remote from YAML
                    merged = SyncState(
                        last_sync=remote_baseline.last_sync,
                        backend=remote_baseline.backend,
                        issues={},
                    )

                    # Prefer git-reconstructed local baseline over YAML remote
                    # Remote is used for reference but git is source of truth
                    for issue_id, local_base in local_baseline.issues.items():
                        merged.issues[issue_id] = local_base

                    logger.info(
                        "baseline_state_loaded",
                        source="git_history_and_sync_metadata",
                        issue_count=len(merged.issues),
                    )
                    return merged
                else:
                    # Only have remote baseline from YAML
                    logger.info(
                        "baseline_state_loaded",
                        source="sync_metadata_only",
                        issue_count=len(remote_baseline.issues),
                    )
                    return remote_baseline

            # Fallback: try loading legacy JSON file
            logger.debug("baseline_fallback_to_json_file")
            json_baseline = self.state_manager.load_sync_state()
            if json_baseline:
                logger.info(
                    "baseline_state_loaded",
                    source="legacy_json_file",
                    issue_count=len(json_baseline.issues),
                )
                return json_baseline

            # No baseline available
            logger.info(
                "baseline_state_not_found",
                reason="first_sync_or_no_metadata",
            )
            return None

        except Exception as e:
            logger.error(
                "baseline_state_retrieval_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    def sync_all_issues(
        self,
        dry_run: bool = True,
        force_local: bool = False,
        force_remote: bool = False,
    ):
        """Override sync_all_issues to use git-based baselines."""
        try:
            # Use git-based baseline retrieval instead of JSON file
            logger.info("sync_starting_with_git_based_baselines")

            git_baseline = self.get_baseline_state()
            if git_baseline:
                # Temporarily replace state_manager's loaded state
                logger.info(
                    "using_git_based_baseline",
                    issue_count=len(git_baseline.issues),
                )

                # Call parent sync with git-based baseline
                # We'll do this by temporarily patching the state_manager
                original_load = self.state_manager.load_sync_state
                self.state_manager.load_sync_state = lambda: git_baseline

                try:
                    return super().sync_all_issues(
                        dry_run=dry_run,
                        force_local=force_local,
                        force_remote=force_remote,
                    )
                finally:
                    self.state_manager.load_sync_state = original_load
            else:
                # No baseline, proceed with parent sync
                logger.info(
                    "no_baseline_available_first_sync",
                )
                return super().sync_all_issues(
                    dry_run=dry_run,
                    force_local=force_local,
                    force_remote=force_remote,
                )

        except Exception as e:
            logger.error(
                "sync_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
