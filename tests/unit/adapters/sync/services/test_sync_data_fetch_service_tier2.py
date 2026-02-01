"""Tests for SyncDataFetchService (Tier 2 coverage)."""

from unittest.mock import MagicMock, patch

import pytest

from roadmap.adapters.sync.services.sync_data_fetch_service import SyncDataFetchService
from roadmap.core.services.sync.sync_report import SyncReport


class TestSyncDataFetchService:
    """Test suite for SyncDataFetchService."""

    @pytest.fixture
    def mock_core(self):
        """Create mock RoadmapCore."""
        core = MagicMock()
        core.issues = MagicMock()
        return core

    @pytest.fixture
    def mock_backend(self):
        """Create mock SyncBackendInterface."""
        backend = MagicMock()
        backend.get_issues.return_value = {}
        return backend

    @pytest.fixture
    def service(self, mock_core, mock_backend):
        """Create service instance."""
        return SyncDataFetchService(mock_core, mock_backend)

    def test_init_stores_references(self, service, mock_core, mock_backend):
        """Test that initialization stores core and backend."""
        assert service.core is mock_core
        assert service.backend is mock_backend

    def test_fetch_remote_issues_success(self, service, mock_backend):
        """Test successful remote issues fetch."""
        remote_issues = {"123": {"title": "Issue 1"}, "456": {"title": "Issue 2"}}
        mock_backend.get_issues.return_value = remote_issues
        report = SyncReport()

        result = service.fetch_remote_issues(report)

        assert result == remote_issues
        assert report.error is None

    def test_fetch_remote_issues_returns_none(self, service, mock_backend):
        """Test when backend returns None."""
        mock_backend.get_issues.return_value = None
        report = SyncReport()

        result = service.fetch_remote_issues(report)

        assert result is None
        assert (
            report.error is not None and "Failed to fetch remote issues" in report.error
        )

    def test_fetch_remote_issues_connection_error(self, service, mock_backend):
        """Test handling of ConnectionError."""
        mock_backend.get_issues.side_effect = ConnectionError("Network failed")
        report = SyncReport()

        result = service.fetch_remote_issues(report)

        assert result is None
        assert (
            report.error is not None and "Failed to fetch remote issues" in report.error
        )

    def test_fetch_remote_issues_timeout_error(self, service, mock_backend):
        """Test handling of TimeoutError."""
        mock_backend.get_issues.side_effect = TimeoutError("Request timeout")
        report = SyncReport()

        result = service.fetch_remote_issues(report)

        assert result is None
        assert (
            report.error is not None and "Failed to fetch remote issues" in report.error
        )

    def test_fetch_remote_issues_generic_exception(self, service, mock_backend):
        """Test handling of generic exceptions."""
        mock_backend.get_issues.side_effect = RuntimeError("Unexpected error")
        report = SyncReport()

        result = service.fetch_remote_issues(report)

        assert result is None
        assert (
            report.error is not None and "Failed to fetch remote issues" in report.error
        )

    @patch("roadmap.adapters.sync.services.sync_data_fetch_service.logger")
    def test_fetch_remote_issues_logs_success(self, mock_logger, service, mock_backend):
        """Test logging on successful fetch."""
        mock_backend.get_issues.return_value = {"123": {}}
        report = SyncReport()

        service.fetch_remote_issues(report)

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "remote_issues_fetched" in call_args[0]

    @patch("roadmap.adapters.sync.services.sync_data_fetch_service.logger")
    def test_fetch_remote_issues_logs_connection_error(
        self, mock_logger, service, mock_backend
    ):
        """Test logging on connection error."""
        mock_backend.get_issues.side_effect = ConnectionError("Network")
        report = SyncReport()

        service.fetch_remote_issues(report)

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "remote_issues_fetch_error" in call_args[0]

    def test_fetch_local_issues_success(self, service, mock_core):
        """Test successful local issues fetch."""
        local_issues = [MagicMock(), MagicMock()]
        mock_core.issues.list_all_including_archived.return_value = local_issues
        report = SyncReport()

        result = service.fetch_local_issues(report)

        assert result == local_issues
        assert report.error is None

    def test_fetch_local_issues_empty_list(self, service, mock_core):
        """Test fetching empty local issues list."""
        mock_core.issues.list_all_including_archived.return_value = []
        report = SyncReport()

        result = service.fetch_local_issues(report)

        assert result == []
        assert report.error is None

    def test_fetch_local_issues_returns_none(self, service, mock_core):
        """Test when core returns None."""
        mock_core.issues.list_all_including_archived.return_value = None
        report = SyncReport()

        result = service.fetch_local_issues(report)

        assert result == []
        assert report.error is None

    def test_fetch_local_issues_os_error(self, service, mock_core):
        """Test handling of OSError."""
        mock_core.issues.list_all_including_archived.side_effect = OSError(
            "File not found"
        )
        report = SyncReport()

        result = service.fetch_local_issues(report)

        assert result is None
        assert (
            report.error is not None and "Failed to fetch local issues" in report.error
        )

    def test_fetch_local_issues_permission_error(self, service, mock_core):
        """Test handling of PermissionError (subclass of OSError)."""
        mock_core.issues.list_all_including_archived.side_effect = PermissionError(
            "Access denied"
        )
        report = SyncReport()

        result = service.fetch_local_issues(report)

        assert result is None
        assert (
            report.error is not None and "Failed to fetch local issues" in report.error
        )

    def test_fetch_local_issues_generic_exception(self, service, mock_core):
        """Test handling of generic exceptions."""
        mock_core.issues.list_all_including_archived.side_effect = RuntimeError(
            "Unexpected error"
        )
        report = SyncReport()

        result = service.fetch_local_issues(report)

        assert result is None
        assert (
            report.error is not None and "Failed to fetch local issues" in report.error
        )

    @patch("roadmap.adapters.sync.services.sync_data_fetch_service.logger")
    def test_fetch_local_issues_logs_success(self, mock_logger, service, mock_core):
        """Test logging on successful fetch."""
        mock_core.issues.list_all_including_archived.return_value = [MagicMock()]
        report = SyncReport()

        service.fetch_local_issues(report)

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "local_issues_fetched" in call_args[0]

    @patch("roadmap.adapters.sync.services.sync_data_fetch_service.logger")
    def test_fetch_local_issues_logs_os_error(self, mock_logger, service, mock_core):
        """Test logging on OS error."""
        mock_core.issues.list_all_including_archived.side_effect = OSError("File error")
        report = SyncReport()

        service.fetch_local_issues(report)

        mock_logger.error.assert_called_once()

    def test_fetch_remote_and_local_reports_independent(
        self, service, mock_backend, mock_core
    ):
        """Test that remote and local fetch reports are independent."""
        mock_backend.get_issues.return_value = {"123": {}}
        mock_core.issues.list_all_including_archived.return_value = []

        report1 = SyncReport()
        service.fetch_remote_issues(report1)

        report2 = SyncReport()
        service.fetch_local_issues(report2)

        assert report1.error is None
        assert report2.error is None

    def test_fetch_remote_issues_empty_dict(self, service, mock_backend):
        """Test fetching empty remote dict."""
        mock_backend.get_issues.return_value = {}
        report = SyncReport()

        result = service.fetch_remote_issues(report)

        assert result == {}
        assert report.error is None

    def test_fetch_multiple_remote_batches(self, service, mock_backend):
        """Test fetching remote issues in multiple calls."""
        batch1 = {"123": {"title": "Issue 1"}}
        batch2 = {"456": {"title": "Issue 2"}}

        mock_backend.get_issues.side_effect = [batch1, batch2]

        report1 = SyncReport()
        result1 = service.fetch_remote_issues(report1)

        report2 = SyncReport()
        result2 = service.fetch_remote_issues(report2)

        assert result1 == batch1
        assert result2 == batch2

    def test_fetch_multiple_local_batches(self, service, mock_core):
        """Test fetching local issues in multiple calls."""
        issues1 = [MagicMock(), MagicMock()]
        issues2 = [MagicMock()]

        mock_core.issues.list_all_including_archived.side_effect = [issues1, issues2]

        report1 = SyncReport()
        result1 = service.fetch_local_issues(report1)

        report2 = SyncReport()
        result2 = service.fetch_local_issues(report2)

        assert result1 == issues1
        assert result2 == issues2

    def test_fetch_preserves_issue_structure(self, service, mock_backend):
        """Test that issue structure is preserved."""
        issue = {
            "id": "123",
            "title": "Test",
            "status": "open",
            "labels": ["bug", "urgent"],
            "custom_field": "value",
        }
        mock_backend.get_issues.return_value = {"123": issue}
        report = SyncReport()

        result = service.fetch_remote_issues(report)

        assert result["123"] == issue

    @patch("roadmap.adapters.sync.services.sync_data_fetch_service.logger")
    def test_fetch_remote_issues_logs_debug(self, mock_logger, service, mock_backend):
        """Test debug logging is called."""
        mock_backend.get_issues.return_value = {}
        report = SyncReport()

        service.fetch_remote_issues(report)

        mock_logger.debug.assert_called_once_with("fetching_remote_issues")

    @patch("roadmap.adapters.sync.services.sync_data_fetch_service.logger")
    def test_fetch_local_issues_logs_debug(self, mock_logger, service, mock_core):
        """Test debug logging is called."""
        mock_core.issues.list_all_including_archived.return_value = []
        report = SyncReport()

        service.fetch_local_issues(report)

        mock_logger.debug.assert_called_once_with("fetching_local_issues")


class TestSyncDataFetchServiceIntegration:
    """Integration tests for SyncDataFetchService."""

    def test_full_data_fetch_flow(self):
        """Test full data fetch flow for both local and remote."""
        mock_core = MagicMock()
        mock_backend = MagicMock()

        mock_core.issues.list_all_including_archived.return_value = [
            MagicMock(),
            MagicMock(),
        ]
        mock_backend.get_issues.return_value = {"123": {"title": "Remote"}}

        service = SyncDataFetchService(mock_core, mock_backend)

        report = SyncReport()
        remote = service.fetch_remote_issues(report)
        local = service.fetch_local_issues(report)

        assert remote is not None and len(remote) == 1
        assert local is not None and len(local) == 2

    def test_error_recovery_flow(self):
        """Test error recovery in sequence."""
        mock_core = MagicMock()
        mock_backend = MagicMock()

        # First remote call fails
        mock_backend.get_issues.side_effect = ConnectionError("Network")
        # Local call succeeds
        mock_core.issues.list_all_including_archived.return_value = []

        service = SyncDataFetchService(mock_core, mock_backend)

        report1 = SyncReport()
        remote = service.fetch_remote_issues(report1)

        report2 = SyncReport()
        local = service.fetch_local_issues(report2)

        assert remote is None
        assert local == []
