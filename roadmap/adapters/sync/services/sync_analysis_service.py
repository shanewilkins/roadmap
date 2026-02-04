"""Service for analyzing and classifying sync changes."""

from structlog import get_logger

from roadmap.core.services.sync.sync_state_comparator import SyncStateComparator
from roadmap.core.services.sync.sync_state_manager import SyncStateManager

logger = get_logger(__name__)


class SyncAnalysisService:
    """Handles change analysis and classification for sync operations."""

    def __init__(
        self,
        state_comparator: SyncStateComparator,
        state_manager: SyncStateManager,
    ):
        """Initialize analysis service.

        Args:
            state_comparator: Service for detecting changes
            state_manager: Service for managing baseline state
        """
        self.state_comparator = state_comparator
        self.state_manager = state_manager

    def load_baseline_safe(self):
        """Load baseline state but swallow errors and return None on failure.

        Returns:
            SyncState or None if not found
        """
        try:
            logger.debug("loading_sync_state")
            base_state = self.state_manager.load_sync_state_from_db()
            if base_state:
                logger.info(
                    "previous_sync_state_loaded",
                    base_issues_count=len(base_state.base_issues),
                    last_sync=base_state.last_sync_time.isoformat()
                    if base_state.last_sync_time
                    else None,
                )
            else:
                logger.info(
                    "no_previous_sync_state_found",
                    reason="first_sync_or_state_cleared",
                )
        except Exception:
            logger.warning("sync_state_load_warning", reason="will_treat_as_first_sync")
            base_state = None

        return base_state

    def analyze_and_classify(self, local_issues_dict, remote_issues_data, base_state):
        """Run comparator and classify changes into categories.

        Args:
            local_issues_dict: Dict of local Issue objects (id -> Issue)
            remote_issues_data: Dict of remote issue data (keyed by remote ID)
            base_state: Previous sync state or None

        Returns:
            Tuple of (changes, conflicts, local_only_changes, remote_only_changes,
                      no_changes, updates, pulls, up_to_date)
        """
        changes = self.state_comparator.analyze_three_way(
            local_issues_dict,
            remote_issues_data,
            base_state.base_issues if base_state else None,
        )

        conflicts = [c for c in changes if c.has_conflict]
        local_only_changes = [c for c in changes if c.is_local_only_change()]
        remote_only_changes = [c for c in changes if c.is_remote_only_change()]
        no_changes = [c for c in changes if c.conflict_type == "no_change"]

        updates = [c.local_state for c in local_only_changes if c.local_state]

        # For pulls, we need to pass the remote ID (GitHub issue number) to pull_issues()
        # After _normalize_remote_keys(), the remote_issues_data dict is keyed by local UUIDs,
        # but we need to extract the GitHub number from each SyncIssue
        pulls = []
        for c in remote_only_changes:
            if c.issue_id in remote_issues_data:
                remote_obj = remote_issues_data[c.issue_id]
                # Extract GitHub issue number (backend_id) from the SyncIssue
                github_number = None
                if isinstance(remote_obj, dict):
                    github_number = remote_obj.get("backend_id") or remote_obj.get(
                        "number"
                    )
                else:
                    github_number = getattr(remote_obj, "backend_id", None)

                if github_number:
                    pulls.append(str(github_number))
                else:
                    # Should not happen, but fallback to local ID if needed
                    pulls.append(c.issue_id)
            else:
                pulls.append(c.issue_id)

        up_to_date = [c.issue_id for c in no_changes]

        logger.debug(
            "three_way_analysis_complete",
            total_changes=len(changes),
            conflicts=len(conflicts),
            local_only=len(local_only_changes),
            remote_only=len(remote_only_changes),
            no_change=len(no_changes),
        )

        return (
            changes,
            conflicts,
            local_only_changes,
            remote_only_changes,
            no_changes,
            updates,
            pulls,
            up_to_date,
        )
