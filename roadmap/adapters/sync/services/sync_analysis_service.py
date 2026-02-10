"""Service for analyzing and classifying sync changes."""

from datetime import UTC, datetime

from structlog import get_logger

from roadmap.core.services.sync.sync_state import IssueBaseState, SyncState
from roadmap.core.services.sync.sync_key_normalizer import normalize_remote_keys
from roadmap.core.services.sync.sync_state_comparator import SyncStateComparator
from roadmap.core.services.sync.sync_state_manager import SyncStateManager

logger = get_logger(__name__)


class SyncAnalysisService:
    """Handles change analysis and classification for sync operations."""

    def __init__(
        self,
        state_comparator: SyncStateComparator,
        state_manager: SyncStateManager,
        core=None,
    ):
        """Initialize analysis service.

        Args:
            state_comparator: Service for detecting changes
            state_manager: Service for managing baseline state
            core: Optional RoadmapCore for database baseline fallback
        """
        self.state_comparator = state_comparator
        self.state_manager = state_manager
        self.core = core

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
                base_state = self._load_baseline_from_core()
                if base_state:
                    logger.info(
                        "previous_sync_state_loaded",
                        base_issues_count=len(base_state.base_issues),
                        last_sync=base_state.last_sync_time.isoformat()
                        if base_state.last_sync_time
                        else None,
                        source="core_db",
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

    def _load_baseline_from_core(self) -> SyncState | None:
        if not self.core or not getattr(self.core, "db", None):
            return None

        db_baseline = self.core.db.get_sync_baseline()
        if not db_baseline:
            return None

        base_issues: dict[str, IssueBaseState] = {}
        for issue_id, data in db_baseline.items():
            base_issues[issue_id] = IssueBaseState(
                id=issue_id,
                status=data.get("status", "todo"),
                title=data.get("title", ""),
                assignee=data.get("assignee"),
                headline=data.get("headline", ""),
                content=data.get("content", ""),
                labels=data.get("labels", []),
            )

        return SyncState(last_sync_time=datetime.now(UTC), base_issues=base_issues)

    @staticmethod
    def _is_empty_remote_value(value) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return value.strip() == ""
        if isinstance(value, (list, tuple, set, dict)):
            return len(value) == 0
        return False

    @staticmethod
    def _local_value_for_field(issue, field: str):
        if issue is None:
            return None
        if field == "labels":
            return issue.labels or []
        if field == "assignee":
            return issue.assignee
        if field == "content":
            return issue.content
        return getattr(issue, field, None)

    def _should_reclassify_as_push(self, change) -> bool:
        if not change.remote_changes or not change.local_state:
            return False
        allowed_fields = {"labels", "assignee"}
        for field, diff in change.remote_changes.items():
            if field not in allowed_fields:
                return False
            remote_value = diff.get("to") if isinstance(diff, dict) else None
            if not self._is_empty_remote_value(remote_value):
                return False
            local_value = self._local_value_for_field(change.local_state, field)
            if self._is_empty_remote_value(local_value):
                return False
        return True

    def _reclassify_remote_only_changes(self, remote_only_changes):
        reclassified = [
            c for c in remote_only_changes if self._should_reclassify_as_push(c)
        ]
        remaining = [c for c in remote_only_changes if c not in reclassified]
        return reclassified, remaining

    @staticmethod
    def _extract_remote_id(remote_obj):
        if isinstance(remote_obj, dict):
            backend_id = remote_obj.get("backend_id") or remote_obj.get("number")
            if backend_id is not None:
                return str(backend_id)
            remote_ids = remote_obj.get("remote_ids") or {}
            backend_name = remote_obj.get("backend_name")
            if backend_name and backend_name in remote_ids:
                return str(remote_ids.get(backend_name))
            if "github" in remote_ids:
                return str(remote_ids.get("github"))
            return None

        backend_id = getattr(remote_obj, "backend_id", None)
        if backend_id is not None:
            return str(backend_id)
        backend_name = getattr(remote_obj, "backend_name", None)
        remote_ids = getattr(remote_obj, "remote_ids", None) or {}
        if backend_name and backend_name in remote_ids:
            return str(remote_ids.get(backend_name))
        if "github" in remote_ids:
            return str(remote_ids.get("github"))
        return None

    def _build_pull_ids(self, remote_only_changes, normalized_remote) -> list[str]:
        pulls: list[str] = []
        for change in remote_only_changes:
            if change.issue_id in normalized_remote:
                remote_obj = normalized_remote[change.issue_id]
                remote_id = self._extract_remote_id(remote_obj)
                if remote_id:
                    pulls.append(remote_id)
                    continue

            issue_id = str(change.issue_id)
            if issue_id.isdigit() or issue_id.startswith("_remote_"):
                pulls.append(issue_id)
            else:
                logger.debug(
                    "pull_id_unresolved",
                    issue_id=change.issue_id,
                    reason="no_remote_id",
                )
        return pulls

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

        reclassified, remote_only_changes = self._reclassify_remote_only_changes(
            remote_only_changes
        )
        if reclassified:
            local_only_changes = local_only_changes + reclassified

        updates = [c.local_state for c in local_only_changes if c.local_state]

        normalized_remote = remote_issues_data
        if self.state_comparator.backend is not None:
            _, normalized_remote = normalize_remote_keys(
                local_issues_dict,
                remote_issues_data,
                self.state_comparator.backend,
                logger=logger,
            )

        # For pulls, we need to pass the remote ID (GitHub issue number) to pull_issues()
        # Use normalized_remote so issue_id lookups match analysis keys.
        pulls = self._build_pull_ids(remote_only_changes, normalized_remote)

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
