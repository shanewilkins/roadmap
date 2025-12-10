"""Comprehensive unit tests for audit logging module.

Tests cover all audit logging functions including entity operations,
state transitions, bulk actions, and audit report generation.
"""

import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from roadmap.infrastructure.logging.audit_logging import (
    generate_audit_report,
    get_current_user,
    log_bulk_action,
    log_entity_archived,
    log_entity_created,
    log_entity_deleted,
    log_entity_restored,
    log_entity_updated,
    log_state_transition,
)


class TestGetCurrentUser:
    """Test get_current_user function."""

    def test_get_user_from_environment_user_variable(self):
        """Test retrieving user from USER environment variable."""
        with patch.dict(os.environ, {"USER": "testuser"}):
            user = get_current_user()
            assert user == "testuser"

    def test_get_user_from_environment_username_variable(self):
        """Test retrieving user from USERNAME environment variable (Windows)."""
        with patch.dict(os.environ, {"USER": "", "USERNAME": "winuser"}, clear=False):
            user = get_current_user()
            assert user == "winuser"

    def test_get_user_from_git_config(self):
        """Test retrieving user from git config when environment not set."""
        with patch.dict(os.environ, {"USER": "", "USERNAME": ""}, clear=True):
            mock_repo = MagicMock()
            mock_config = MagicMock()
            mock_config.get_value.return_value = "git_user"
            mock_repo.config_reader.return_value = mock_config

            with patch("git.Repo") as mock_git_repo:
                mock_git_repo.return_value = mock_repo
                user = get_current_user()
                assert user == "git_user"

    def test_get_user_defaults_to_unknown(self):
        """Test that user defaults to 'unknown' when all sources fail."""
        with patch.dict(os.environ, {"USER": "", "USERNAME": ""}, clear=True):
            # Simulate git not being available by making import fail
            import sys

            git_backup = sys.modules.get("git")
            try:
                sys.modules["git"] = None
                user = get_current_user()
                assert user == "unknown"
            finally:
                if git_backup is not None:
                    sys.modules["git"] = git_backup
                elif "git" in sys.modules:
                    del sys.modules["git"]

    def test_get_user_handles_git_import_error(self):
        """Test graceful handling when git module is not available."""
        with patch.dict(os.environ, {"USER": "", "USERNAME": ""}, clear=True):
            # Simulate git import failure
            import sys

            git_backup = sys.modules.get("git")
            try:
                sys.modules["git"] = None
                user = get_current_user()
                assert user == "unknown"
            finally:
                if git_backup is not None:
                    sys.modules["git"] = git_backup
                elif "git" in sys.modules:
                    del sys.modules["git"]

    def test_get_user_handles_git_config_error(self):
        """Test graceful handling when git config access fails."""
        with patch.dict(os.environ, {"USER": "", "USERNAME": ""}, clear=True):
            mock_repo = MagicMock()
            mock_repo.config_reader.side_effect = Exception("Config error")

            with patch("git.Repo") as mock_git_repo:
                mock_git_repo.return_value = mock_repo
                user = get_current_user()
                assert user == "unknown"

    def test_get_user_handles_git_repo_error(self):
        """Test graceful handling when git repo cannot be found."""
        with patch.dict(os.environ, {"USER": "", "USERNAME": ""}, clear=True):
            with patch("git.Repo") as mock_git_repo:
                mock_git_repo.side_effect = Exception("No repo")
                user = get_current_user()
                assert user == "unknown"


class TestLogEntityCreated:
    """Test log_entity_created function."""

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    @patch("roadmap.infrastructure.logging.audit_logging.get_current_user")
    def test_log_entity_created_basic(self, mock_get_user, mock_logger):
        """Test basic entity creation logging."""
        mock_get_user.return_value = "testuser"
        entity_data = {"title": "Test Issue", "priority": "high"}

        log_entity_created("issue", "issue-123", entity_data)

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "audit_entity_created"
        assert call_args[1]["action"] == "create"
        assert call_args[1]["entity_type"] == "issue"
        assert call_args[1]["entity_id"] == "issue-123"
        assert call_args[1]["user"] == "testuser"
        assert call_args[1]["entity_data"] == entity_data
        assert "timestamp" in call_args[1]

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    @patch("roadmap.infrastructure.logging.audit_logging.get_current_user")
    def test_log_entity_created_with_reason(self, mock_get_user, mock_logger):
        """Test entity creation logging with reason."""
        mock_get_user.return_value = "testuser"
        entity_data = {"title": "Test Issue"}

        log_entity_created(
            "issue",
            "issue-123",
            entity_data,
            reason="Created from CLI",
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[1]["reason"] == "Created from CLI"

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    @patch("roadmap.infrastructure.logging.audit_logging.get_current_user")
    def test_log_entity_created_different_types(self, mock_get_user, mock_logger):
        """Test entity creation logging for different entity types."""
        mock_get_user.return_value = "testuser"

        for entity_type in ["issue", "milestone", "project", "custom_type"]:
            mock_logger.reset_mock()
            log_entity_created(entity_type, f"{entity_type}-1", {})

            call_args = mock_logger.info.call_args
            assert call_args[1]["entity_type"] == entity_type


class TestLogEntityUpdated:
    """Test log_entity_updated function."""

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    @patch("roadmap.infrastructure.logging.audit_logging.get_current_user")
    def test_log_entity_updated_basic(self, mock_get_user, mock_logger):
        """Test basic entity update logging."""
        mock_get_user.return_value = "testuser"
        before = {"title": "Old Title", "priority": "low"}
        after = {"title": "New Title", "priority": "high"}

        log_entity_updated("issue", "issue-123", before, after)

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "audit_entity_updated"
        assert call_args[1]["action"] == "update"
        assert call_args[1]["entity_type"] == "issue"
        assert call_args[1]["entity_id"] == "issue-123"
        assert call_args[1]["user"] == "testuser"
        assert call_args[1]["before_state"] == before
        assert call_args[1]["after_state"] == after
        assert "timestamp" in call_args[1]

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    @patch("roadmap.infrastructure.logging.audit_logging.get_current_user")
    def test_log_entity_updated_auto_detect_changed_fields(
        self, mock_get_user, mock_logger
    ):
        """Test that changed fields are automatically detected."""
        mock_get_user.return_value = "testuser"
        before = {"title": "Old", "priority": "low", "status": "open"}
        after = {"title": "New", "priority": "low", "status": "open"}

        log_entity_updated("issue", "issue-123", before, after)

        call_args = mock_logger.info.call_args
        # Only 'title' changed
        assert call_args[1]["changed_fields"] == ["title"]

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    @patch("roadmap.infrastructure.logging.audit_logging.get_current_user")
    def test_log_entity_updated_explicit_changed_fields(
        self, mock_get_user, mock_logger
    ):
        """Test entity update with explicit changed_fields."""
        mock_get_user.return_value = "testuser"
        before = {"a": 1, "b": 2}
        after = {"a": 1, "b": 2}

        log_entity_updated(
            "issue",
            "issue-123",
            before,
            after,
            changed_fields=["b"],
        )

        call_args = mock_logger.info.call_args
        assert call_args[1]["changed_fields"] == ["b"]

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    @patch("roadmap.infrastructure.logging.audit_logging.get_current_user")
    def test_log_entity_updated_with_reason(self, mock_get_user, mock_logger):
        """Test entity update logging with reason."""
        mock_get_user.return_value = "testuser"

        log_entity_updated(
            "issue",
            "issue-123",
            {"priority": "low"},
            {"priority": "high"},
            reason="User requested priority increase",
        )

        call_args = mock_logger.info.call_args
        assert call_args[1]["reason"] == "User requested priority increase"

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    @patch("roadmap.infrastructure.logging.audit_logging.get_current_user")
    def test_log_entity_updated_detects_multiple_changes(
        self, mock_get_user, mock_logger
    ):
        """Test detection of multiple field changes."""
        mock_get_user.return_value = "testuser"
        before = {"a": 1, "b": 2, "c": 3}
        after = {"a": 10, "b": 20, "c": 3}

        log_entity_updated("issue", "issue-123", before, after)

        call_args = mock_logger.info.call_args
        changed = set(call_args[1]["changed_fields"])
        assert changed == {"a", "b"}


class TestLogEntityDeleted:
    """Test log_entity_deleted function."""

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    @patch("roadmap.infrastructure.logging.audit_logging.get_current_user")
    def test_log_entity_deleted_permanent(self, mock_get_user, mock_logger):
        """Test permanent entity deletion logging."""
        mock_get_user.return_value = "testuser"
        entity_data = {"title": "Deleted Issue", "priority": "high"}

        log_entity_deleted("issue", "issue-123", entity_data)

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "audit_entity_deleted"
        assert call_args[1]["action"] == "delete"
        assert call_args[1]["entity_type"] == "issue"
        assert call_args[1]["entity_id"] == "issue-123"
        assert call_args[1]["user"] == "testuser"
        assert call_args[1]["entity_data"] == entity_data
        assert call_args[1]["deletion_method"] == "permanent"
        assert "timestamp" in call_args[1]

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    @patch("roadmap.infrastructure.logging.audit_logging.get_current_user")
    def test_log_entity_deleted_archive_method(self, mock_get_user, mock_logger):
        """Test entity deletion with archive method."""
        mock_get_user.return_value = "testuser"

        log_entity_deleted(
            "issue",
            "issue-123",
            {"title": "Deleted"},
            deletion_method="archive",
        )

        call_args = mock_logger.info.call_args
        assert call_args[1]["deletion_method"] == "archive"

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    @patch("roadmap.infrastructure.logging.audit_logging.get_current_user")
    def test_log_entity_deleted_soft_delete_method(self, mock_get_user, mock_logger):
        """Test entity deletion with soft-delete method."""
        mock_get_user.return_value = "testuser"

        log_entity_deleted(
            "issue",
            "issue-123",
            {"title": "Deleted"},
            deletion_method="soft-delete",
        )

        call_args = mock_logger.info.call_args
        assert call_args[1]["deletion_method"] == "soft-delete"

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    @patch("roadmap.infrastructure.logging.audit_logging.get_current_user")
    def test_log_entity_deleted_with_reason(self, mock_get_user, mock_logger):
        """Test entity deletion logging with reason."""
        mock_get_user.return_value = "testuser"

        log_entity_deleted(
            "issue",
            "issue-123",
            {"title": "Deleted"},
            reason="Duplicate entry",
        )

        call_args = mock_logger.info.call_args
        assert call_args[1]["reason"] == "Duplicate entry"


class TestLogEntityArchived:
    """Test log_entity_archived function."""

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    @patch("roadmap.infrastructure.logging.audit_logging.get_current_user")
    def test_log_entity_archived_basic(self, mock_get_user, mock_logger):
        """Test basic entity archival logging."""
        mock_get_user.return_value = "testuser"

        log_entity_archived("issue", "issue-123", "/archive/2025-01")

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "audit_entity_archived"
        assert call_args[1]["action"] == "archive"
        assert call_args[1]["entity_type"] == "issue"
        assert call_args[1]["entity_id"] == "issue-123"
        assert call_args[1]["user"] == "testuser"
        assert call_args[1]["archive_location"] == "/archive/2025-01"
        assert "timestamp" in call_args[1]

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    @patch("roadmap.infrastructure.logging.audit_logging.get_current_user")
    def test_log_entity_archived_with_retention(self, mock_get_user, mock_logger):
        """Test entity archival logging with retention period."""
        mock_get_user.return_value = "testuser"

        log_entity_archived(
            "issue",
            "issue-123",
            "/archive/2025-01",
            retention_days=90,
        )

        call_args = mock_logger.info.call_args
        assert call_args[1]["retention_days"] == 90

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    @patch("roadmap.infrastructure.logging.audit_logging.get_current_user")
    def test_log_entity_archived_with_reason(self, mock_get_user, mock_logger):
        """Test entity archival logging with reason."""
        mock_get_user.return_value = "testuser"

        log_entity_archived(
            "issue",
            "issue-123",
            "/archive/2025-01",
            reason="End of quarter cleanup",
        )

        call_args = mock_logger.info.call_args
        assert call_args[1]["reason"] == "End of quarter cleanup"


class TestLogEntityRestored:
    """Test log_entity_restored function."""

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    @patch("roadmap.infrastructure.logging.audit_logging.get_current_user")
    def test_log_entity_restored_basic(self, mock_get_user, mock_logger):
        """Test basic entity restoration logging."""
        mock_get_user.return_value = "testuser"

        log_entity_restored(
            "issue",
            "issue-123",
            "/archive/2025-01",
            "/projects/current",
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "audit_entity_restored"
        assert call_args[1]["action"] == "restore"
        assert call_args[1]["entity_type"] == "issue"
        assert call_args[1]["entity_id"] == "issue-123"
        assert call_args[1]["user"] == "testuser"
        assert call_args[1]["from_location"] == "/archive/2025-01"
        assert call_args[1]["to_location"] == "/projects/current"
        assert "timestamp" in call_args[1]

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    @patch("roadmap.infrastructure.logging.audit_logging.get_current_user")
    def test_log_entity_restored_with_reason(self, mock_get_user, mock_logger):
        """Test entity restoration logging with reason."""
        mock_get_user.return_value = "testuser"

        log_entity_restored(
            "milestone",
            "milestone-456",
            "/archive/2024-12",
            "/projects/active",
            reason="Reopening Q1 planning",
        )

        call_args = mock_logger.info.call_args
        assert call_args[1]["reason"] == "Reopening Q1 planning"
        assert call_args[1]["entity_type"] == "milestone"


class TestLogBulkAction:
    """Test log_bulk_action function."""

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    @patch("roadmap.infrastructure.logging.audit_logging.get_current_user")
    def test_log_bulk_action_basic(self, mock_get_user, mock_logger):
        """Test basic bulk action logging."""
        mock_get_user.return_value = "testuser"

        log_bulk_action("archive", "issue", 42)

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "audit_bulk_action"
        assert call_args[1]["action"] == "archive"
        assert call_args[1]["entity_type"] == "issue"
        assert call_args[1]["count"] == 42
        assert call_args[1]["user"] == "testuser"
        assert "timestamp" in call_args[1]

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    @patch("roadmap.infrastructure.logging.audit_logging.get_current_user")
    def test_log_bulk_action_with_criteria(self, mock_get_user, mock_logger):
        """Test bulk action logging with selection criteria."""
        mock_get_user.return_value = "testuser"
        criteria = {"status": "completed", "date_before": "2025-01-01"}

        log_bulk_action(
            "delete",
            "issue",
            15,
            selection_criteria=criteria,
        )

        call_args = mock_logger.info.call_args
        assert call_args[1]["selection_criteria"] == criteria

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    @patch("roadmap.infrastructure.logging.audit_logging.get_current_user")
    def test_log_bulk_action_with_reason(self, mock_get_user, mock_logger):
        """Test bulk action logging with reason."""
        mock_get_user.return_value = "testuser"

        log_bulk_action(
            "update",
            "milestone",
            10,
            reason="Mass priority reassignment",
        )

        call_args = mock_logger.info.call_args
        assert call_args[1]["reason"] == "Mass priority reassignment"

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    @patch("roadmap.infrastructure.logging.audit_logging.get_current_user")
    def test_log_bulk_action_different_actions(self, mock_get_user, mock_logger):
        """Test bulk actions with different action types."""
        mock_get_user.return_value = "testuser"

        for action in ["archive", "delete", "update", "restore"]:
            mock_logger.reset_mock()
            log_bulk_action(action, "issue", 5)

            call_args = mock_logger.info.call_args
            assert call_args[1]["action"] == action


class TestLogStateTransition:
    """Test log_state_transition function."""

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    @patch("roadmap.infrastructure.logging.audit_logging.get_current_user")
    def test_log_state_transition_basic(self, mock_get_user, mock_logger):
        """Test basic state transition logging."""
        mock_get_user.return_value = "testuser"

        log_state_transition("issue", "issue-123", "open", "closed")

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "audit_state_transition"
        assert call_args[1]["entity_type"] == "issue"
        assert call_args[1]["entity_id"] == "issue-123"
        assert call_args[1]["user"] == "testuser"
        assert call_args[1]["from_state"] == "open"
        assert call_args[1]["to_state"] == "closed"
        assert "timestamp" in call_args[1]

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    @patch("roadmap.infrastructure.logging.audit_logging.get_current_user")
    def test_log_state_transition_with_reason(self, mock_get_user, mock_logger):
        """Test state transition logging with reason."""
        mock_get_user.return_value = "testuser"

        log_state_transition(
            "milestone",
            "milestone-456",
            "planning",
            "in_progress",
            reason="Started Q1 2025 work",
        )

        call_args = mock_logger.info.call_args
        assert call_args[1]["reason"] == "Started Q1 2025 work"

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    @patch("roadmap.infrastructure.logging.audit_logging.get_current_user")
    def test_log_state_transition_multiple_states(self, mock_get_user, mock_logger):
        """Test state transitions with various state types."""
        mock_get_user.return_value = "testuser"

        transitions = [
            ("open", "in_progress"),
            ("in_progress", "review"),
            ("review", "closed"),
            ("active", "archived"),
        ]

        for from_state, to_state in transitions:
            mock_logger.reset_mock()
            log_state_transition("issue", "issue-123", from_state, to_state)

            call_args = mock_logger.info.call_args
            assert call_args[1]["from_state"] == from_state
            assert call_args[1]["to_state"] == to_state


class TestGenerateAuditReport:
    """Test generate_audit_report function."""

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    def test_generate_audit_report_basic(self, mock_logger):
        """Test basic audit report generation."""
        report = generate_audit_report("issue")

        assert report["entity_type"] == "issue"
        assert report["entity_id"] is None
        assert report["user"] is None
        assert report["start_time"] is None
        assert report["end_time"] is None
        assert "generated_at" in report

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "audit_report_requested"

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    def test_generate_audit_report_with_entity_id(self, mock_logger):
        """Test audit report for specific entity."""
        report = generate_audit_report("issue", entity_id="issue-123")

        assert report["entity_type"] == "issue"
        assert report["entity_id"] == "issue-123"

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    def test_generate_audit_report_with_user_filter(self, mock_logger):
        """Test audit report filtered by user."""
        report = generate_audit_report("issue", user="testuser")

        assert report["user"] == "testuser"

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    def test_generate_audit_report_with_time_range(self, mock_logger):
        """Test audit report with time range."""
        start = datetime.utcnow() - timedelta(days=7)
        end = datetime.utcnow()

        report = generate_audit_report("issue", start_time=start, end_time=end)

        assert report["start_time"] == start.isoformat()
        assert report["end_time"] == end.isoformat()

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    def test_generate_audit_report_all_parameters(self, mock_logger):
        """Test audit report with all parameters specified."""
        start = datetime(2025, 1, 1, 0, 0, 0)
        end = datetime(2025, 1, 31, 23, 59, 59)

        report = generate_audit_report(
            "milestone",
            entity_id="milestone-456",
            user="admin",
            start_time=start,
            end_time=end,
        )

        assert report["entity_type"] == "milestone"
        assert report["entity_id"] == "milestone-456"
        assert report["user"] == "admin"
        assert report["start_time"] == start.isoformat()
        assert report["end_time"] == end.isoformat()
        assert "generated_at" in report

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    def test_generate_audit_report_logs_request(self, mock_logger):
        """Test that report request is logged."""
        start = datetime(2025, 1, 1)
        end = datetime(2025, 1, 31)

        generate_audit_report(
            "issue",
            entity_id="issue-789",
            user="auditor",
            start_time=start,
            end_time=end,
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "audit_report_requested"
        assert call_args[1]["entity_type"] == "issue"
        assert call_args[1]["entity_id"] == "issue-789"
        assert call_args[1]["user"] == "auditor"

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    def test_generate_audit_report_datetime_formatting(self, mock_logger):
        """Test that datetime values are properly formatted to ISO format."""
        dt = datetime(2025, 6, 15, 14, 30, 45)
        report = generate_audit_report("issue", start_time=dt)

        assert report["start_time"] == "2025-06-15T14:30:45"


class TestAuditLoggingIntegration:
    """Integration tests for audit logging workflows."""

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    @patch("roadmap.infrastructure.logging.audit_logging.get_current_user")
    def test_complete_entity_lifecycle(self, mock_get_user, mock_logger):
        """Test complete lifecycle: create -> update -> archive -> restore."""
        mock_get_user.return_value = "lifecycle_user"

        # Create
        log_entity_created("issue", "issue-999", {"title": "Lifecycle Test"})
        assert mock_logger.info.call_count == 1

        # Update
        log_entity_updated(
            "issue",
            "issue-999",
            {"title": "Lifecycle Test", "status": "open"},
            {"title": "Lifecycle Test Updated", "status": "open"},
        )
        assert mock_logger.info.call_count == 2

        # Archive
        log_entity_archived("issue", "issue-999", "/archive/2025-01")
        assert mock_logger.info.call_count == 3

        # Restore
        log_entity_restored(
            "issue",
            "issue-999",
            "/archive/2025-01",
            "/projects/active",
        )
        assert mock_logger.info.call_count == 4

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    @patch("roadmap.infrastructure.logging.audit_logging.get_current_user")
    def test_state_transition_with_updates(self, mock_get_user, mock_logger):
        """Test state transitions interleaved with updates."""
        mock_get_user.return_value = "state_user"

        # Initial state
        log_state_transition("issue", "issue-001", "open", "in_progress")
        assert mock_logger.info.call_count == 1

        # Update while in progress
        log_entity_updated(
            "issue",
            "issue-001",
            {"status": "in_progress", "priority": "low"},
            {"status": "in_progress", "priority": "high"},
        )
        assert mock_logger.info.call_count == 2

        # Transition to closed
        log_state_transition("issue", "issue-001", "in_progress", "closed")
        assert mock_logger.info.call_count == 3

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    @patch("roadmap.infrastructure.logging.audit_logging.get_current_user")
    def test_bulk_operation_with_report(self, mock_get_user, mock_logger):
        """Test bulk action followed by audit report."""
        mock_get_user.return_value = "bulk_user"

        # Bulk action
        log_bulk_action(
            "archive",
            "issue",
            25,
            selection_criteria={"status": "completed"},
        )
        assert mock_logger.info.call_count == 1

        # Generate report
        start = datetime.utcnow() - timedelta(hours=1)
        end = datetime.utcnow()
        generate_audit_report(
            "issue",
            start_time=start,
            end_time=end,
        )
        assert mock_logger.info.call_count == 2

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    @patch("roadmap.infrastructure.logging.audit_logging.get_current_user")
    def test_all_audit_functions_use_consistent_user(self, mock_get_user, mock_logger):
        """Test that all audit functions use the same user context."""
        mock_get_user.return_value = "consistent_user"

        log_entity_created("issue", "i1", {})
        log_entity_updated("issue", "i2", {}, {})
        log_entity_deleted("issue", "i3", {})
        log_entity_archived("issue", "i4", "/archive")
        log_entity_restored("issue", "i5", "/archive", "/active")
        log_bulk_action("delete", "issue", 1)
        log_state_transition("issue", "i6", "open", "closed")

        # Verify all calls include the user
        for call in mock_logger.info.call_args_list[:-1]:  # Exclude report
            assert call[1]["user"] == "consistent_user"

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    @patch("roadmap.infrastructure.logging.audit_logging.get_current_user")
    def test_all_audit_functions_include_timestamps(self, mock_get_user, mock_logger):
        """Test that all audit functions include timestamps."""
        mock_get_user.return_value = "timestamp_user"

        log_entity_created("issue", "i1", {})
        log_entity_updated("issue", "i2", {}, {})
        log_entity_deleted("issue", "i3", {})
        log_entity_archived("issue", "i4", "/archive")
        log_entity_restored("issue", "i5", "/archive", "/active")
        log_bulk_action("delete", "issue", 1)
        log_state_transition("issue", "i6", "open", "closed")

        # Verify all calls include timestamps
        for call in mock_logger.info.call_args_list:
            assert "timestamp" in call[1]

    @patch("roadmap.infrastructure.logging.audit_logging.logger")
    def test_audit_report_returns_dict(self, mock_logger):
        """Test that audit report always returns a dictionary."""
        result = generate_audit_report("issue")
        assert isinstance(result, dict)

        result = generate_audit_report("milestone", entity_id="m1")
        assert isinstance(result, dict)

        result = generate_audit_report("project", user="testuser")
        assert isinstance(result, dict)
