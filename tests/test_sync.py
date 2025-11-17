"""Tests for sync manager."""

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Mark all tests in this file as unit tests (primarily mock-based)
pytestmark = pytest.mark.unit

from roadmap.github_client import GitHubAPIError
from roadmap.models import (
    Issue,
    Milestone,
    MilestoneStatus,
    Priority,
    RoadmapConfig,
    Status,
)
from roadmap.sync import SyncConflict, SyncConflictStrategy, SyncManager, SyncStrategy


class TestSyncManager:
    """Test cases for SyncManager."""

    @pytest.fixture
    def mock_github_client(self):
        """Mock GitHubClient."""
        with patch("roadmap.sync.GitHubClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def sync_manager(self, mock_core, mock_config, mock_github_client):
        """Create SyncManager for testing."""
        with patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"}):
            return SyncManager(mock_core, mock_config)

    def test_initialization_with_valid_config(
        self, mock_core, mock_config, mock_github_client
    ):
        """Test sync manager initialization with valid config."""
        with patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"}):
            sync_manager = SyncManager(mock_core, mock_config)
            assert sync_manager.core == mock_core
            assert sync_manager.config == mock_config
            assert sync_manager.github_client is not None

    def test_initialization_without_github_config(self, mock_core):
        """Test sync manager initialization without GitHub config."""
        config = RoadmapConfig()
        config.github = {}

        sync_manager = SyncManager(mock_core, config)
        assert sync_manager.github_client is None

    @patch("roadmap.sync.get_credential_manager")
    def test_initialization_with_missing_token(
        self, mock_credential_manager, mock_core, mock_config
    ):
        """Test sync manager initialization with missing token."""
        mock_config.github["token"] = ""

        # Mock credential manager to return None
        mock_credential_manager.return_value.is_available.return_value = False
        mock_credential_manager.return_value.get_token.return_value = None

        with patch.dict("os.environ", {}, clear=True):
            sync_manager = SyncManager(mock_core, mock_config)
            # Should not create client if token is missing
            assert sync_manager.github_client is None

    def test_is_configured_true(self, sync_manager):
        """Test is_configured returns True when client exists."""
        assert sync_manager.is_configured() is True

    def test_is_configured_false(self, mock_core, mock_config):
        """Test is_configured returns False when no client."""
        sync_manager = SyncManager(mock_core, mock_config)
        sync_manager.github_client = None
        assert sync_manager.is_configured() is False

    def test_test_connection_success(self, sync_manager):
        """Test successful connection test."""
        sync_manager.github_client.test_authentication.return_value = {
            "login": "test_user"
        }
        sync_manager.github_client.test_repository_access.return_value = {
            "full_name": "test_owner/test_repo"
        }

        success, message = sync_manager.test_connection()

        assert success is True
        assert "Connected as test_user to test_owner/test_repo" in message

    def test_test_connection_failure(self, sync_manager):
        """Test failed connection test."""
        sync_manager.github_client.test_authentication.side_effect = GitHubAPIError(
            "Auth failed"
        )

        success, message = sync_manager.test_connection()

        assert success is False
        assert "Auth failed" in message

    def test_test_connection_no_client(self, mock_core, mock_config):
        """Test connection test with no client."""
        sync_manager = SyncManager(mock_core, mock_config)
        sync_manager.github_client = None

        success, message = sync_manager.test_connection()

        assert success is False
        assert "not configured" in message

    def test_setup_repository_success(self, sync_manager):
        """Test successful repository setup."""
        sync_manager.github_client.setup_default_labels.return_value = None

        success, message = sync_manager.setup_repository()

        assert success is True
        assert "set up successfully" in message
        sync_manager.github_client.setup_default_labels.assert_called_once()

    def test_setup_repository_failure(self, sync_manager):
        """Test failed repository setup."""
        sync_manager.github_client.setup_default_labels.side_effect = GitHubAPIError(
            "Setup failed"
        )

        success, message = sync_manager.setup_repository()

        assert success is False
        assert "Setup failed" in message

    def test_push_issue_new(self, sync_manager, mock_core):
        """Test pushing new issue to GitHub."""
        # Create test issue
        issue = Issue(
            id="test123",
            title="Test Issue",
            priority=Priority.HIGH,
            status=Status.TODO,
            content="Test content",
        )

        # Mock GitHub client responses
        sync_manager.github_client.priority_to_labels.return_value = ["priority:high"]
        sync_manager.github_client.status_to_labels.return_value = ["status:todo"]
        sync_manager.github_client.create_issue.return_value = {"number": 42}

        # Mock core methods
        mock_core.issues_dir = Path("/test/.roadmap/issues")

        with patch("roadmap.sync.IssueParser.save_issue_file") as mock_save:
            success, message, issue_number = sync_manager.push_issue(issue)

        assert success is True
        assert "Created GitHub issue #42" in message
        assert issue_number == 42
        assert issue.github_issue == 42

        # Verify GitHub client calls
        sync_manager.github_client.create_issue.assert_called_once()
        create_args = sync_manager.github_client.create_issue.call_args[1]
        assert create_args["title"] == "Test Issue"
        assert create_args["body"] == "Test content\n\n---\n*Created by roadmap CLI*"
        assert "priority:high" in create_args["labels"]
        assert "status:todo" in create_args["labels"]

        # Verify issue was saved
        mock_save.assert_called_once()

    def test_push_issue_existing(self, sync_manager):
        """Test pushing existing issue (update)."""
        issue = Issue(
            id="test123",
            title="Test Issue",
            github_issue=42,
            priority=Priority.HIGH,
            status=Status.DONE,
        )

        sync_manager.github_client.priority_to_labels.return_value = ["priority:high"]
        sync_manager.github_client.status_to_labels.return_value = ["status:done"]
        sync_manager.github_client.update_issue.return_value = {"number": 42}

        with patch("roadmap.sync.IssueParser.save_issue_file"):
            success, message, issue_number = sync_manager.push_issue(issue)

        assert success is True
        assert "Updated GitHub issue #42" in message
        assert issue_number == 42

        # Verify update call
        sync_manager.github_client.update_issue.assert_called_once()
        update_args = sync_manager.github_client.update_issue.call_args[1]
        assert update_args["issue_number"] == 42
        assert update_args["state"] == "closed"  # DONE status should close issue

    def test_push_issue_with_milestone(self, sync_manager):
        """Test pushing issue with milestone."""
        issue = Issue(title="Test Issue", milestone="v1.0")

        # Mock finding milestone
        sync_manager.github_client.get_milestones.return_value = [
            {"title": "v1.0", "number": 5}
        ]
        sync_manager.github_client.priority_to_labels.return_value = ["priority:medium"]
        sync_manager.github_client.status_to_labels.return_value = ["status:todo"]
        sync_manager.github_client.create_issue.return_value = {"number": 43}

        with patch("roadmap.sync.IssueParser.save_issue_file"):
            success, message, issue_number = sync_manager.push_issue(issue)

        assert success is True

        # Verify milestone was found and assigned
        create_args = sync_manager.github_client.create_issue.call_args[1]
        assert create_args["milestone"] == 5

    def test_push_issue_failure(self, sync_manager):
        """Test push issue failure."""
        issue = Issue(title="Test Issue")

        sync_manager.github_client.priority_to_labels.return_value = []
        sync_manager.github_client.status_to_labels.return_value = []
        sync_manager.github_client.create_issue.side_effect = GitHubAPIError(
            "Create failed"
        )

        success, message, issue_number = sync_manager.push_issue(issue)

        assert success is False
        assert "Create failed" in message
        assert issue_number is None

    def test_pull_issue_new(self, sync_manager, mock_core):
        """Test pulling new issue from GitHub."""
        github_issue = {
            "number": 42,
            "title": "GitHub Issue",
            "body": "Issue body",
            "state": "open",
            "labels": [{"name": "priority:high"}, {"name": "status:todo"}],
            "milestone": {"title": "v1.0"},
            "assignee": {"login": "test_user"},
        }

        sync_manager.github_client.get_issue.return_value = github_issue
        sync_manager.github_client.labels_to_priority.return_value = Priority.HIGH
        sync_manager.github_client.labels_to_status.return_value = Status.TODO

        # Mock no existing local issue
        mock_core.list_issues.return_value = []
        mock_core.issues_dir = Path("/test/.roadmap/issues")

        with patch("roadmap.sync.IssueParser.save_issue_file") as mock_save:
            success, message, issue = sync_manager.pull_issue(42)

        assert success is True
        assert "Created local issue" in message
        assert issue.title == "GitHub Issue"
        assert issue.content == "Issue body"
        assert issue.priority == Priority.HIGH
        assert issue.status == Status.TODO
        assert issue.milestone == "v1.0"
        assert issue.assignee == "test_user"
        assert issue.github_issue == 42

        mock_save.assert_called_once()

    def test_pull_issue_existing(self, sync_manager, mock_core):
        """Test pulling existing issue (update)."""
        # Existing local issue
        existing_issue = Issue(
            id="test123", title="Old Title", github_issue=42, content="Old content"
        )

        github_issue = {
            "number": 42,
            "title": "Updated Title",
            "body": "Updated body",
            "state": "closed",
            "labels": [{"name": "priority:critical"}],
            "milestone": None,
            "assignee": None,
        }

        sync_manager.github_client.get_issue.return_value = github_issue
        sync_manager.github_client.labels_to_priority.return_value = Priority.CRITICAL
        sync_manager.github_client.labels_to_status.return_value = None

        mock_core.list_issues.return_value = [existing_issue]
        mock_core.issues_dir = Path("/test/.roadmap/issues")

        with patch("roadmap.sync.IssueParser.save_issue_file") as mock_save:
            success, message, issue = sync_manager.pull_issue(42)

        assert success is True
        assert "Updated local issue" in message
        assert issue.title == "Updated Title"
        assert issue.content == "Updated body"
        assert issue.priority == Priority.CRITICAL
        assert issue.status == Status.DONE  # Closed GitHub issue should be DONE

        mock_save.assert_called_once()

    def test_pull_issue_failure(self, sync_manager):
        """Test pull issue failure."""
        sync_manager.github_client.get_issue.side_effect = GitHubAPIError("Not found")

        success, message, issue = sync_manager.pull_issue(42)

        assert success is False
        assert "Not found" in message
        assert issue is None

    def test_push_milestone_new(self, sync_manager, mock_core):
        """Test pushing new milestone to GitHub."""
        milestone = Milestone(
            name="v1.0",
            description="First release",
            due_date=datetime(2025, 12, 31),
            status=MilestoneStatus.OPEN,
        )

        sync_manager.github_client.create_milestone.return_value = {"number": 5}
        mock_core.milestones_dir = Path("/test/.roadmap/milestones")

        with patch("roadmap.sync.MilestoneParser.save_milestone_file") as mock_save:
            success, message, milestone_number = sync_manager.push_milestone(milestone)

        assert success is True
        assert "Created GitHub milestone #5" in message
        assert milestone_number == 5
        assert milestone.github_milestone == 5

        # Verify GitHub client call
        sync_manager.github_client.create_milestone.assert_called_once()
        create_args = sync_manager.github_client.create_milestone.call_args[1]
        assert create_args["title"] == "v1.0"
        assert create_args["description"] == "First release"
        assert create_args["due_date"] == datetime(2025, 12, 31)
        assert create_args["state"] == "open"

        mock_save.assert_called_once()

    def test_push_milestone_existing(self, sync_manager):
        """Test pushing existing milestone (update)."""
        milestone = Milestone(
            name="v1.0", github_milestone=5, status=MilestoneStatus.CLOSED
        )

        sync_manager.github_client.update_milestone.return_value = {"number": 5}

        with patch("roadmap.sync.MilestoneParser.save_milestone_file"):
            success, message, milestone_number = sync_manager.push_milestone(milestone)

        assert success is True
        assert "Updated GitHub milestone #5" in message

        # Verify update call
        sync_manager.github_client.update_milestone.assert_called_once()
        update_args = sync_manager.github_client.update_milestone.call_args[1]
        assert update_args["milestone_number"] == 5
        assert update_args["state"] == "closed"

    def test_sync_all_issues_push(self, sync_manager, mock_core):
        """Test syncing all issues (push direction)."""
        # Mock local issues
        issues = [Issue(id="1", title="Issue 1"), Issue(id="2", title="Issue 2")]
        mock_core.list_issues.return_value = issues

        # Mock successful pushes
        with patch.object(sync_manager, "push_issue") as mock_push:
            mock_push.side_effect = [(True, "Success 1", 1), (True, "Success 2", 2)]

            success_count, error_count, error_messages = sync_manager.sync_all_issues(
                "push"
            )

        assert success_count == 2
        assert error_count == 0
        assert len(error_messages) == 0
        assert mock_push.call_count == 2

    def test_sync_all_issues_push_with_errors(self, sync_manager, mock_core):
        """Test syncing all issues with some errors."""
        issues = [Issue(id="1", title="Issue 1"), Issue(id="2", title="Issue 2")]
        mock_core.list_issues.return_value = issues

        with patch.object(sync_manager, "push_issue") as mock_push:
            mock_push.side_effect = [
                (True, "Success", 1),
                (False, "Error occurred", None),
            ]

            success_count, error_count, error_messages = sync_manager.sync_all_issues(
                "push"
            )

        assert success_count == 1
        assert error_count == 1
        assert len(error_messages) == 1
        assert "Issue 2: Error occurred" in error_messages[0]

    def test_sync_all_issues_pull(self, sync_manager):
        """Test syncing all issues (pull direction)."""
        # Mock GitHub issues
        github_issues = [
            {"number": 1, "title": "Issue 1"},
            {"number": 2, "title": "Issue 2", "pull_request": {}},  # Should be skipped
        ]
        sync_manager.github_client.get_issues.return_value = github_issues

        with patch.object(sync_manager, "pull_issue") as mock_pull:
            mock_pull.return_value = (True, "Success", Mock())

            success_count, error_count, error_messages = sync_manager.sync_all_issues(
                "pull"
            )

        assert success_count == 1  # Only 1 issue, PR was skipped
        assert error_count == 0
        assert mock_pull.call_count == 1
        mock_pull.assert_called_with(1)  # Only issue 1, not the PR

    def test_sync_all_milestones_push(self, sync_manager, mock_core):
        """Test syncing all milestones (push direction)."""
        milestones = [Milestone(name="v1.0"), Milestone(name="v2.0")]
        mock_core.list_milestones.return_value = milestones

        with patch.object(sync_manager, "push_milestone") as mock_push:
            mock_push.side_effect = [(True, "Success 1", 1), (True, "Success 2", 2)]

            success_count, error_count, error_messages = (
                sync_manager.sync_all_milestones("push")
            )

        assert success_count == 2
        assert error_count == 0
        assert mock_push.call_count == 2

    def test_sync_all_milestones_pull(self, sync_manager, mock_core):
        """Test syncing all milestones (pull direction)."""
        github_milestones = [
            {
                "number": 1,
                "title": "v1.0",
                "description": "First release",
                "state": "open",
                "due_on": "2025-12-31T00:00:00Z",
            }
        ]
        sync_manager.github_client.get_milestones.return_value = github_milestones

        # Mock no existing local milestone
        mock_core.get_milestone.return_value = None
        mock_core.milestones_dir = Path("/test/.roadmap/milestones")

        with patch("roadmap.sync.MilestoneParser.save_milestone_file") as mock_save:
            success_count, error_count, error_messages = (
                sync_manager.sync_all_milestones("pull")
            )

        assert success_count == 1
        assert error_count == 0
        mock_save.assert_called_once()

        # Verify milestone data
        saved_milestone = mock_save.call_args[0][0]
        assert saved_milestone.name == "v1.0"
        assert saved_milestone.description == "First release"
        assert saved_milestone.github_milestone == 1

    def test_find_github_milestone(self, sync_manager):
        """Test finding GitHub milestone by name."""
        milestones = [{"title": "v1.0", "number": 1}, {"title": "v2.0", "number": 2}]
        sync_manager.github_client.get_milestones.return_value = milestones

        result = sync_manager._find_github_milestone("v1.0")
        assert result == 1

        result = sync_manager._find_github_milestone("v3.0")
        assert result is None

    def test_find_github_milestone_api_error(self, sync_manager):
        """Test finding GitHub milestone with API error."""
        sync_manager.github_client.get_milestones.side_effect = GitHubAPIError(
            "API error"
        )

        result = sync_manager._find_github_milestone("v1.0")
        assert result is None

    def test_sync_methods_without_client(self, mock_core, mock_config):
        """Test sync methods when GitHub client is not configured."""
        sync_manager = SyncManager(mock_core, mock_config)
        sync_manager.github_client = None

        # Test push_issue
        issue = Issue(title="Test")
        success, message, number = sync_manager.push_issue(issue)
        assert success is False
        assert "not configured" in message

        # Test pull_issue
        success, message, issue = sync_manager.pull_issue(1)
        assert success is False
        assert "not configured" in message

        # Test sync_all_issues
        success_count, error_count, error_messages = sync_manager.sync_all_issues(
            "pull"
        )
        assert success_count == 0
        assert error_count == 1
        assert "not configured" in error_messages[0]


class TestSyncStrategy:
    """Test conflict detection and resolution strategies."""

    def test_compare_timestamps_local_newer(self):
        """Test timestamp comparison when local is newer."""

        strategy = SyncStrategy()

        local_time = datetime(2024, 1, 15, 12, 0, 0)
        github_time = "2024-01-15T10:00:00Z"

        result = strategy.compare_timestamps(local_time, github_time)
        assert result == "local_newer"

    def test_compare_timestamps_remote_newer(self):
        """Test timestamp comparison when remote is newer."""

        strategy = SyncStrategy()

        local_time = datetime(2024, 1, 15, 10, 0, 0)
        github_time = "2024-01-15T12:00:00Z"

        result = strategy.compare_timestamps(local_time, github_time)
        assert result == "remote_newer"

    def test_compare_timestamps_same(self):
        """Test timestamp comparison when times are the same."""

        strategy = SyncStrategy()

        local_time = datetime(2024, 1, 15, 12, 0, 0)
        github_time = "2024-01-15T12:00:00Z"

        result = strategy.compare_timestamps(local_time, github_time)
        assert result == "same"

    def test_detect_issue_conflict(self):
        """Test issue conflict detection."""

        strategy = SyncStrategy()

        local_issue = Issue(
            id="test1",
            title="Test Issue",
            updated=datetime(2024, 1, 15, 12, 0, 0),
            github_issue=1,
        )

        github_issue = {
            "number": 1,
            "title": "Test Issue Updated",
            "updated_at": "2024-01-15T14:00:00Z",
        }

        conflict = strategy.detect_issue_conflict(local_issue, github_issue)
        assert conflict is not None
        assert conflict.item_type == "issue"
        assert conflict.item_id == "1"

    def test_detect_milestone_conflict(self):
        """Test milestone conflict detection."""

        strategy = SyncStrategy()

        local_milestone = Milestone(
            name="v1.0", updated=datetime(2024, 1, 15, 12, 0, 0), github_milestone=1
        )

        github_milestone = {
            "number": 1,
            "title": "v1.0",
            "updated_at": "2024-01-15T14:00:00Z",
        }

        conflict = strategy.detect_milestone_conflict(local_milestone, github_milestone)
        assert conflict is not None
        assert conflict.item_type == "milestone"
        assert conflict.item_id == "1"

    def test_resolve_conflict_newer_wins_local(self):
        """Test conflict resolution with newer_wins strategy (local newer)."""
        from roadmap.sync import SyncConflictStrategy, SyncStrategy

        strategy = SyncStrategy(SyncConflictStrategy.NEWER_WINS)

        local_issue = Issue(id="test1", title="Test")
        github_issue = {"number": 1, "title": "Test"}

        conflict = SyncConflict(
            "issue",
            "1",
            local_issue,
            github_issue,
            datetime(2024, 1, 15, 12, 0, 0),  # local newer
            datetime(2024, 1, 15, 10, 0, 0),  # remote older
        )

        resolution = strategy.resolve_conflict(conflict)
        assert resolution == "use_local"

    def test_resolve_conflict_newer_wins_remote(self):
        """Test conflict resolution with newer_wins strategy (remote newer)."""
        from roadmap.sync import SyncConflictStrategy, SyncStrategy

        strategy = SyncStrategy(SyncConflictStrategy.NEWER_WINS)

        local_issue = Issue(id="test1", title="Test")
        github_issue = {"number": 1, "title": "Test"}

        conflict = SyncConflict(
            "issue",
            "1",
            local_issue,
            github_issue,
            datetime(2024, 1, 15, 10, 0, 0),  # local older
            datetime(2024, 1, 15, 12, 0, 0),  # remote newer
        )

        resolution = strategy.resolve_conflict(conflict)
        assert resolution == "use_remote"

    def test_resolve_conflict_local_wins(self):
        """Test conflict resolution with local_wins strategy."""
        from roadmap.sync import SyncConflictStrategy, SyncStrategy

        strategy = SyncStrategy(SyncConflictStrategy.LOCAL_WINS)

        local_issue = Issue(id="test1", title="Test")
        github_issue = {"number": 1, "title": "Test"}

        conflict = SyncConflict(
            "issue",
            "1",
            local_issue,
            github_issue,
            datetime(2024, 1, 15, 10, 0, 0),  # local older
            datetime(2024, 1, 15, 12, 0, 0),  # remote newer
        )

        resolution = strategy.resolve_conflict(conflict)
        assert resolution == "use_local"

    def test_resolve_conflict_remote_wins(self):
        """Test conflict resolution with remote_wins strategy."""
        from roadmap.sync import SyncConflictStrategy, SyncStrategy

        strategy = SyncStrategy(SyncConflictStrategy.REMOTE_WINS)

        local_issue = Issue(id="test1", title="Test")
        github_issue = {"number": 1, "title": "Test"}

        conflict = SyncConflict(
            "issue",
            "1",
            local_issue,
            github_issue,
            datetime(2024, 1, 15, 12, 0, 0),  # local newer
            datetime(2024, 1, 15, 10, 0, 0),  # remote older
        )

        resolution = strategy.resolve_conflict(conflict)
        assert resolution == "use_remote"


class TestBidirectionalSync:
    """Test bidirectional synchronization functionality."""

    @pytest.fixture
    def sync_manager_with_strategy(self, mock_core):
        """Create sync manager with conflict strategy."""
        from roadmap.sync import SyncConflictStrategy, SyncManager

        config = RoadmapConfig()
        config.github = {
            "token": "test_token",
            "owner": "test_owner",
            "repo": "test_repo",
        }

        sync_manager = SyncManager(mock_core, config, SyncConflictStrategy.NEWER_WINS)
        sync_manager.github_client = Mock()
        return sync_manager

    def test_bidirectional_sync_no_conflicts(
        self, sync_manager_with_strategy, mock_core
    ):
        """Test bidirectional sync when no conflicts exist."""
        # Mock local and remote data with no conflicts
        local_issues = [Issue(id="1", title="Issue 1", github_issue=1)]
        mock_core.list_issues.return_value = local_issues

        github_issues = [
            {"number": 1, "title": "Issue 1", "updated_at": "2024-01-15T12:00:00Z"}
        ]
        sync_manager_with_strategy.github_client.get_issues.return_value = github_issues
        sync_manager_with_strategy.github_client.get_milestones.return_value = []

        mock_core.list_milestones.return_value = []

        # Mock no conflicts detected
        with patch.object(
            sync_manager_with_strategy.sync_strategy,
            "detect_issue_conflict",
            return_value=None,
        ):
            success_count, error_count, error_messages, conflicts = (
                sync_manager_with_strategy.bidirectional_sync()
            )

        assert success_count >= 1
        assert error_count == 0
        assert len(conflicts) == 0

    def test_bidirectional_sync_with_conflict_local_wins(
        self, sync_manager_with_strategy, mock_core
    ):
        """Test bidirectional sync with conflict resolved to local."""

        local_issue = Issue(
            id="1",
            title="Local Version",
            github_issue=1,
            updated=datetime(2024, 1, 15, 12, 0, 0),
        )
        mock_core.list_issues.return_value = [local_issue]

        github_issues = [
            {
                "number": 1,
                "title": "Remote Version",
                "updated_at": "2024-01-15T10:00:00Z",  # older
            }
        ]
        sync_manager_with_strategy.github_client.get_issues.return_value = github_issues
        sync_manager_with_strategy.github_client.get_milestones.return_value = []

        mock_core.list_milestones.return_value = []

        # Mock conflict detection and resolution
        conflict = SyncConflict(
            "issue",
            "1",
            local_issue,
            github_issues[0],
            datetime(2024, 1, 15, 12, 0, 0),  # local newer
            datetime(2024, 1, 15, 10, 0, 0),  # remote older
        )

        with patch.object(
            sync_manager_with_strategy.sync_strategy,
            "detect_issue_conflict",
            return_value=conflict,
        ):
            with patch.object(
                sync_manager_with_strategy,
                "push_issue",
                return_value=(True, "Success", 1),
            ):
                success_count, error_count, error_messages, conflicts = (
                    sync_manager_with_strategy.bidirectional_sync()
                )

        assert len(conflicts) == 1
        assert conflicts[0].item_type == "issue"

    def test_bidirectional_sync_new_local_issue(
        self, sync_manager_with_strategy, mock_core
    ):
        """Test bidirectional sync with new local issue to push."""
        local_issue = Issue(id="1", title="New Local Issue")  # No github_issue
        mock_core.list_issues.return_value = [local_issue]

        sync_manager_with_strategy.github_client.get_issues.return_value = []
        sync_manager_with_strategy.github_client.get_milestones.return_value = []

        mock_core.list_milestones.return_value = []

        with patch.object(
            sync_manager_with_strategy, "push_issue", return_value=(True, "Created", 1)
        ):
            success_count, error_count, error_messages, conflicts = (
                sync_manager_with_strategy.bidirectional_sync()
            )

        assert success_count == 1
        assert error_count == 0

    def test_bidirectional_sync_new_remote_issue(
        self, sync_manager_with_strategy, mock_core
    ):
        """Test bidirectional sync with new remote issue to pull."""
        mock_core.list_issues.return_value = []

        github_issues = [{"number": 1, "title": "New Remote Issue"}]
        sync_manager_with_strategy.github_client.get_issues.return_value = github_issues
        sync_manager_with_strategy.github_client.get_milestones.return_value = []

        mock_core.list_milestones.return_value = []

        with patch.object(
            sync_manager_with_strategy,
            "pull_issue",
            return_value=(True, "Created", Issue(id="1", title="New Remote Issue")),
        ):
            success_count, error_count, error_messages, conflicts = (
                sync_manager_with_strategy.bidirectional_sync()
            )

        assert success_count == 1
        assert error_count == 0

    def test_bidirectional_sync_milestones(self, sync_manager_with_strategy, mock_core):
        """Test bidirectional sync for milestones."""
        local_milestone = Milestone(name="v1.0", github_milestone=1)
        mock_core.list_milestones.return_value = [local_milestone]
        mock_core.list_issues.return_value = []

        github_milestones = [
            {
                "number": 1,
                "title": "v1.0",
                "updated_at": "2024-01-15T12:00:00Z",
                "state": "open",
                "description": "First release",
                "due_on": None,
            }
        ]
        sync_manager_with_strategy.github_client.get_issues.return_value = []
        sync_manager_with_strategy.github_client.get_milestones.return_value = (
            github_milestones
        )

        with patch.object(
            sync_manager_with_strategy.sync_strategy,
            "detect_milestone_conflict",
            return_value=None,
        ):
            success_count, error_count, error_messages, conflicts = (
                sync_manager_with_strategy.bidirectional_sync()
            )

        assert success_count >= 1
        assert error_count == 0


class TestSyncEnhancements:
    """Test enhanced sync methods with conflict checking."""

    @pytest.fixture
    def sync_manager(self, mock_core):
        """Create sync manager for testing."""
        config = RoadmapConfig()
        config.github = {"token": "test", "owner": "test", "repo": "test"}
        sync_manager = SyncManager(mock_core, config)
        sync_manager.github_client = Mock()
        return sync_manager

    def test_push_issue_with_conflict_check_no_conflict(self, sync_manager):
        """Test push_issue with conflict checking when no conflict exists."""
        issue = Issue(id="1", title="Test Issue", github_issue=1)

        # Mock GitHub issue with same timestamp
        github_issue = {
            "number": 1,
            "title": "Test Issue",
            "updated_at": issue.updated.isoformat() + "Z",
        }
        sync_manager.github_client.get_issue.return_value = github_issue

        with patch.object(
            sync_manager, "update_github_issue", return_value=(True, "Updated", 1)
        ):
            success, message, issue_number = sync_manager.push_issue(
                issue, check_conflicts=True
            )

        assert success is True
        assert issue_number == 1

    def test_push_issue_with_conflict_check_conflict_detected(self, sync_manager):
        """Test push_issue with conflict checking when conflict is detected."""
        # Set strategy to NEWER_WINS for this test to trigger the conflict
        sync_manager.sync_strategy.strategy = SyncConflictStrategy.NEWER_WINS

        issue = Issue(
            id="1",
            title="Local Version",
            github_issue=1,
            updated=datetime(2024, 1, 15, 10, 0, 0),  # older
        )

        # Mock GitHub issue with newer timestamp
        github_issue = {
            "number": 1,
            "title": "Remote Version",
            "updated_at": "2024-01-15T12:00:00Z",  # newer
        }
        sync_manager.github_client.get_issue.return_value = github_issue

        success, message, issue_number = sync_manager.push_issue(
            issue, check_conflicts=True
        )

        assert success is False
        assert "Remote version is newer" in message
        assert issue_number is None

    def test_pull_issue_with_conflict_check_no_conflict(self, sync_manager, mock_core):
        """Test pull_issue with conflict checking when no conflict exists."""
        github_issue = {
            "number": 1,
            "title": "Test Issue",
            "body": "Test content",
            "labels": [],
            "state": "open",
            "milestone": None,
            "assignee": None,
            "updated_at": "2024-01-15T12:00:00Z",
        }
        sync_manager.github_client.get_issue.return_value = github_issue

        # Mock proper return values for priority and status conversion
        sync_manager.github_client.labels_to_priority.return_value = Priority.MEDIUM
        sync_manager.github_client.labels_to_status.return_value = Status.TODO

        # Mock no existing local issue
        mock_core.list_issues.return_value = []

        with patch("roadmap.sync.IssueParser.save_issue_file"):
            success, message, local_issue = sync_manager.pull_issue(
                1, check_conflicts=True
            )

        assert success is True
        assert local_issue is not None

    def test_pull_issue_with_conflict_check_conflict_detected(
        self, sync_manager, mock_core
    ):
        """Test pull_issue with conflict checking when conflict is detected."""
        existing_issue = Issue(
            id="1",
            title="Local Version",
            github_issue=1,
            updated=datetime(2024, 1, 15, 12, 0, 0),  # newer
        )
        mock_core.list_issues.return_value = [existing_issue]

        github_issue = {
            "number": 1,
            "title": "Remote Version",
            "updated_at": "2024-01-15T10:00:00Z",  # older
        }
        sync_manager.github_client.get_issue.return_value = github_issue

        success, message, local_issue = sync_manager.pull_issue(1, check_conflicts=True)

        assert success is False
        assert "Local version is newer" in message
        assert local_issue == existing_issue
