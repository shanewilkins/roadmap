"""Service for populating and managing sync reports."""

from roadmap.core.services.sync.sync_report import SyncReport


class SyncReportService:
    """Handles populating sync report fields from analyzed changes."""

    @staticmethod
    def populate_report_fields(
        report: SyncReport,
        local_issues,
        active_issues_count,
        archived_issues_count,
        all_milestones,
        active_milestones_count,
        archived_milestones_count,
        remote_issues_count,
        remote_open_count,
        remote_closed_count,
        remote_milestones_count,
        conflicts,
        up_to_date,
        local_only_changes,
        remote_only_changes,
        changes,
    ):
        """Populate the SyncReport fields from computed values.

        Args:
            report: SyncReport to populate
            local_issues: List of local Issue objects
            active_issues_count: Count of active local issues
            archived_issues_count: Count of archived local issues
            all_milestones: List of all milestones
            active_milestones_count: Count of active milestones
            archived_milestones_count: Count of archived milestones
            remote_issues_count: Count of all remote issues
            remote_open_count: Count of open remote issues
            remote_closed_count: Count of closed remote issues
            remote_milestones_count: Count of remote milestones
            conflicts: List of conflicting changes
            up_to_date: List of up-to-date issues
            local_only_changes: List of local-only changes
            remote_only_changes: List of remote-only changes
            changes: All detected changes
        """
        report.total_issues = len(local_issues)
        report.active_issues = active_issues_count
        report.archived_issues = archived_issues_count
        report.total_milestones = len(all_milestones)
        report.active_milestones = active_milestones_count
        report.archived_milestones = archived_milestones_count
        report.remote_total_issues = remote_issues_count
        report.remote_open_issues = remote_open_count
        report.remote_closed_issues = remote_closed_count
        report.remote_total_milestones = remote_milestones_count
        report.conflicts_detected = len(conflicts)
        report.issues_up_to_date = len(up_to_date)
        report.issues_needs_push = len(local_only_changes)
        report.issues_needs_pull = len(remote_only_changes)
        report.changes = changes
