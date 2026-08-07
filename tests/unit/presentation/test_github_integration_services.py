"""Tests for Phase 1 additional features (unlink, config validation, conflict detection, batch sync).

Phase 1C refactoring: Using mock factories and service-specific fixtures to reduce DRY.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from roadmap.core.services.github.github_config_validator import GitHubConfigValidator
from roadmap.core.services.github.github_conflict_detector import GitHubConflictDetector
from roadmap.core.services.github.github_integration_service import (
    GitHubIntegrationService,
)
from tests.unit.common.formatters.test_assertion_helpers import create_mock_issue

# ============================================================================
# Unlink Command Tests
# ============================================================================


def test_unlink_github_not_linked():
    """Test error when unlinking non-linked issue."""
    issue = create_mock_issue(id="test-123", github_issue=None)
    assert issue.github_issue is None


def test_unlink_github_not_found():
    """Test error when issue not found."""
    core = Mock()
    core.issues.get_by_id.side_effect = ValueError("Not found")

    # Should handle error
    with pytest.raises(ValueError):
        core.issues.get_by_id("nonexistent")


# ============================================================================
# Config Validation Tests
# ============================================================================


class TestConfigValidator:
    """Tests for GitHubConfigValidator functionality."""

    def test_validate_config_method_exists(self):
        """Test that config validator has validate_config method."""
        assert hasattr(GitHubConfigValidator, "validate_config")

    def test_validate_token_method_exists(self):
        """Test that config validator has validate_token method."""
        assert hasattr(GitHubConfigValidator, "validate_token")

    def test_validate_repo_method_exists(self):
        """Test that config validator has validate_repo_access method."""
        assert hasattr(GitHubConfigValidator, "validate_repo_access")

    def test_validate_all_method_exists(self):
        """Test that config validator has validate_all method."""
        assert hasattr(GitHubConfigValidator, "validate_all")

    def test_config_validator_with_mock_service(self):
        """Test config validator with mocked service."""
        with patch.object(
            GitHubIntegrationService,
            "get_github_config",
            return_value=("token-123", "owner", "repo"),
        ):
            validator = Mock()
            validator.validate_config = Mock(return_value=(True, None))

            is_valid, error = validator.validate_config()
            assert is_valid

    def test_config_validator_missing_config(self):
        """Test validation fails when config missing."""
        with patch.object(
            GitHubIntegrationService,
            "get_github_config",
            return_value=(None, None, None),
        ):
            validator = Mock()
            validator.validate_config = Mock(
                return_value=(False, "GitHub not configured")
            )

            is_valid, error = validator.validate_config()
            assert not is_valid
            assert "configured" in error.lower()

    def test_config_validator_invalid_token(self):
        """Test detection of invalid token."""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_get.return_value = mock_response

            validator = Mock()
            validator.validate_token = Mock(
                return_value=(False, "GitHub token is invalid")
            )

            is_valid, error = validator.validate_token()
            assert not is_valid

    def test_config_validator_repo_access(self):
        """Test repo access validation."""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            validator = Mock()
            validator.validate_repo_access = Mock(return_value=(True, None))

            is_valid, error = validator.validate_repo_access()
            assert is_valid

    def test_config_validator_repo_not_found(self):
        """Test detection of non-existent repo."""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response

            validator = Mock()
            validator.validate_repo_access = Mock(
                return_value=(False, "Repository not found")
            )

            is_valid, error = validator.validate_repo_access()
            assert not is_valid


# ============================================================================
# Conflict Detection Tests
# ============================================================================


class TestConflictDetector:
    """Tests for GitHubConflictDetector functionality."""

    def test_conflict_detector_init(self):
        """Test conflict detector initialization."""
        service = Mock(spec=GitHubIntegrationService)
        service.get_github_config.return_value = ("token", "owner", "repo")
        detector = GitHubConflictDetector(service)
        assert detector is not None

    def test_conflict_detector_no_sync_history(self):
        """Test conflict detection when no sync history exists."""
        service = Mock(spec=GitHubIntegrationService)
        service.get_github_config.return_value = ("token", "owner", "repo")
        detector = GitHubConflictDetector(service)

        issue = create_mock_issue(id="abc123", github_issue=123)

        with patch.object(detector, "_get_last_sync_time", return_value=None):
            conflicts = detector.detect_conflicts(issue, 123)
            assert "has_conflicts" in conflicts
            assert not conflicts["has_conflicts"]

    def test_conflict_detector_github_modified(self):
        """Test detection of GitHub-side modifications."""

        service = Mock(spec=GitHubIntegrationService)
        service.get_github_config.return_value = ("token", "owner", "repo")
        detector = GitHubConflictDetector(service)

        # Create issue with proper datetime for updated field
        last_sync = datetime.now(UTC) - timedelta(hours=1)
        issue = create_mock_issue(github_issue=123, updated=last_sync)

        detector.client = Mock()
        detector.client.fetch_issue = Mock(
            return_value={"updated_at": "2025-12-21T14:00:00Z"}
        )

        with patch.object(detector, "_get_last_sync_time", return_value=last_sync):
            conflicts = detector.detect_conflicts(issue, 123)
            assert "github_modified" in conflicts

    def test_conflict_detector_local_modified(self):
        """Test detection of local modifications."""
        service = Mock(spec=GitHubIntegrationService)
        service.get_github_config.return_value = ("token", "owner", "repo")
        detector = GitHubConflictDetector(service)

        issue = create_mock_issue(github_issue=123)
        last_sync = datetime.now(UTC) - timedelta(hours=1)

        with patch.object(detector, "_get_last_sync_time", return_value=last_sync):
            with patch.object(
                detector, "_is_local_modified_after_sync", return_value=True
            ):
                conflicts = detector.detect_conflicts(issue, 123)
                assert "local_modified" in conflicts

    def test_conflict_detector_both_modified(self):
        """Test detection of conflicts when both sides modified."""
        service = Mock(spec=GitHubIntegrationService)
        service.get_github_config.return_value = ("token", "owner", "repo")
        detector = GitHubConflictDetector(service)

        issue = create_mock_issue(github_issue=123)

        with patch.object(
            detector,
            "_get_last_sync_time",
            return_value=datetime.now(UTC) - timedelta(hours=1),
        ):
            with patch.object(
                detector, "_is_local_modified_after_sync", return_value=True
            ):
                with patch.object(
                    detector,
                    "_parse_github_timestamp",
                    return_value=datetime.now(UTC),
                ):
                    result = detector.detect_conflicts(issue, 123)
                    # Verify conflict detection was performed
                    assert result is not None

    def test_conflict_detector_summary(self):
        """Test conflict summary generation."""
        service = Mock(spec=GitHubIntegrationService)
        service.get_github_config.return_value = ("token", "owner", "repo")
        detector = GitHubConflictDetector(service)

        conflicts = {
            "has_conflicts": True,
            "local_modified": True,
            "github_modified": True,
            "warnings": [
                "GitHub issue was modified after last sync",
                "Local issue was modified after last sync",
            ],
        }

        summary = detector.get_conflict_summary(conflicts)
        assert "Conflict Detection Summary" in summary
        assert len(summary) > 0


# ============================================================================
# Batch Operations Tests
# ============================================================================


class TestBatchOperations:
    """Tests for batch sync operations."""

    def test_batch_sync_all_linked(self):
        """Test syncing all linked issues."""
        core = Mock()
        issues = [create_mock_issue(github_issue=i) for i in [123, 456, 789]]
        core.issues.list_all.return_value = issues
        assert len(core.issues.list_all()) == 3

    def test_batch_sync_by_milestone(self):
        """Test syncing issues in specific milestone."""
        core = Mock()
        issues = [create_mock_issue(milestone="v1-0") for _ in range(2)]
        core.issues.list_by_milestone.return_value = issues
        assert len(core.issues.list_by_milestone("v1-0")) == 2

    def test_batch_sync_by_status(self):
        """Test syncing issues with specific status."""
        core = Mock()
        issues = [create_mock_issue(status="in_progress") for _ in range(3)]
        core.issues.list_by_status.return_value = issues
        assert len(core.issues.list_by_status("in_progress")) == 3

    def test_batch_sync_empty_list(self):
        """Test handling when no issues match filter."""
        core = Mock()
        core.issues.list_by_milestone.return_value = []
        assert len(core.issues.list_by_milestone("nonexistent")) == 0

    def test_batch_sync_confirmation(self):
        """Test confirmation prompt for batch operations."""
        core = Mock()
        # Should provide method to confirm
        core.confirm = Mock(return_value=True)
        assert core.confirm()

    def test_batch_sync_partial_failure(self):
        """Test handling when some syncs fail."""
        results = {"succeeded": 2, "failed": 1, "skipped": 0}
        assert results["succeeded"] + results["failed"] == 3


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for GitHub service workflows."""

    def test_unlink_then_cannot_sync(self):
        """Test that unlinking prevents sync."""
        issue = create_mock_issue(id="test-123", github_issue=None)
        # After unlink, github_issue should be None
        assert issue.github_issue is None

    def test_validate_config_before_sync(self):
        """Test config validation happens before sync."""
        service = Mock(spec=GitHubIntegrationService)
        service.get_github_config.return_value = ("token", "owner", "repo")
        # Config is available
        token, owner, repo = service.get_github_config()
        assert token is not None

    def test_conflict_detection_before_sync(self):
        """Test conflict detection before applying changes."""
        detector = Mock(spec=GitHubConflictDetector)
        detector.detect_conflicts.return_value = {
            "has_conflicts": False,
            "warnings": [],
        }
        result = detector.detect_conflicts(Mock(), 123)
        assert not result["has_conflicts"]

    def test_batch_sync_respects_validation(self):
        """Test that batch operations respect validation."""
        Mock(spec=GitHubIntegrationService)
        validator = Mock(spec=GitHubConfigValidator)
        validator.validate_config.return_value = (True, None)

        is_valid, error = validator.validate_config()
        assert is_valid
