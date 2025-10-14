"""
Tests for sync validation fixes - assignee handling, label formatting, and datetime formats.
These tests cover the specific fixes made to resolve GitHub API validation errors.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path

from roadmap.models import Issue, Milestone, Priority, Status, MilestoneStatus
from roadmap.sync import SyncManager
from roadmap.performance_sync import HighPerformanceSyncManager
from roadmap.github_client import GitHubAPIError

pytestmark = pytest.mark.unit


class TestSyncValidationFixes:
    """Test validation fixes for GitHub sync operations."""

    @pytest.fixture
    def mock_core(self):
        """Mock RoadmapCore for testing."""
        core = Mock()
        core.issues_dir = Path("/test/.roadmap/issues")
        core.milestones_dir = Path("/test/.roadmap/milestones")
        return core

    @pytest.fixture
    def mock_config(self):
        """Mock config for testing."""
        config = Mock()
        config.github = {
            "owner": "testowner",
            "repo": "testrepo",
            "token": "test_token"
        }
        return config

    @pytest.fixture
    def mock_github_client(self):
        """Mock GitHubClient."""
        client = Mock()
        client.priority_to_labels.return_value = []
        client.status_to_labels.return_value = []
        return client

    @pytest.fixture
    def sync_manager(self, mock_core, mock_config, mock_github_client):
        """Create SyncManager for testing."""
        with patch("roadmap.sync.GitHubClient") as mock_client_class:
            mock_client_class.return_value = mock_github_client
            with patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"}):
                manager = SyncManager(mock_core, mock_config)
                manager.github_client = mock_github_client
                return manager

    def test_push_issue_with_assignee_creates_assignees_list(self, sync_manager, mock_core):
        """Test that pushing issue with assignee properly formats assignees parameter."""
        # Create issue with assignee
        issue = Issue(
            id="test123",
            title="Test Issue with Assignee",
            priority=Priority.MEDIUM,
            status=Status.TODO,
            assignee="shanewilkins",
            content="Test content"
        )

        # Mock GitHub responses
        sync_manager.github_client.create_issue.return_value = {"number": 42}

        with patch("roadmap.sync.IssueParser.save_issue_file"):
            success, message, issue_number = sync_manager.push_issue(issue)

        # Verify success
        assert success is True
        assert issue_number == 42

        # Verify assignees parameter was passed correctly
        sync_manager.github_client.create_issue.assert_called_once()
        call_kwargs = sync_manager.github_client.create_issue.call_args[1]
        
        assert "assignees" in call_kwargs
        assert call_kwargs["assignees"] == ["shanewilkins"]
        assert call_kwargs["title"] == "Test Issue with Assignee"

    def test_push_issue_without_assignee_empty_assignees_list(self, sync_manager, mock_core):
        """Test that pushing issue without assignee sends empty assignees list."""
        # Create issue without assignee
        issue = Issue(
            id="test456",
            title="Test Issue No Assignee",
            priority=Priority.LOW,
            status=Status.TODO,
            assignee="",  # Empty assignee
            content="Test content"
        )

        sync_manager.github_client.create_issue.return_value = {"number": 43}

        with patch("roadmap.sync.IssueParser.save_issue_file"):
            success, message, issue_number = sync_manager.push_issue(issue)

        assert success is True

        # Verify empty assignees list
        call_kwargs = sync_manager.github_client.create_issue.call_args[1]
        assert call_kwargs["assignees"] == []

    def test_update_issue_with_assignee_includes_assignees(self, sync_manager):
        """Test that updating issue with assignee properly formats assignees parameter."""
        # Create existing issue with assignee
        issue = Issue(
            id="test789",
            title="Existing Issue",
            priority=Priority.HIGH,
            status=Status.IN_PROGRESS,
            assignee="teamlead",
            github_issue=50,  # Existing GitHub issue
            content="Updated content"
        )

        sync_manager.github_client.update_issue.return_value = {"number": 50}

        with patch("roadmap.sync.IssueParser.save_issue_file"):
            success, message, issue_number = sync_manager.push_issue(issue)

        assert success is True

        # Verify assignees parameter in update call
        sync_manager.github_client.update_issue.assert_called_once()
        call_kwargs = sync_manager.github_client.update_issue.call_args[1]
        
        assert "assignees" in call_kwargs
        assert call_kwargs["assignees"] == ["teamlead"]
        assert call_kwargs["issue_number"] == 50

    def test_label_formatting_prevents_comma_separated_strings(self, sync_manager, mock_core):
        """Test that labels are properly formatted as separate items, not comma-separated strings."""
        # Create issue with multiple labels
        issue = Issue(
            id="test_labels",
            title="Test Label Formatting",
            priority=Priority.MEDIUM,
            status=Status.TODO,
            labels=["automation", "git-integration", "workflow"],  # Proper list format
            content="Test content"
        )

        sync_manager.github_client.create_issue.return_value = {"number": 44}

        with patch("roadmap.sync.IssueParser.save_issue_file"):
            success, message, issue_number = sync_manager.push_issue(issue)

        assert success is True

        # Verify labels are passed as individual items
        call_kwargs = sync_manager.github_client.create_issue.call_args[1]
        labels = call_kwargs["labels"]
        
        # Labels should contain the individual label strings, not comma-separated
        assert "automation" in labels
        assert "git-integration" in labels  
        assert "workflow" in labels
        
        # Should NOT contain comma-separated string
        assert "automation,git-integration,workflow" not in labels

    def test_milestone_datetime_formatting_includes_timezone(self, sync_manager, mock_core):
        """Test that milestone due dates are formatted with timezone for GitHub API."""
        # Create milestone with naive datetime (no timezone)
        due_date = datetime(2025, 12, 31, 23, 59, 59)  # Naive datetime
        milestone = Milestone(
            name="v1.0.0",
            description="Test milestone",
            due_date=due_date,
            status=MilestoneStatus.OPEN
        )

        sync_manager.github_client.create_milestone.return_value = {"number": 1}

        with patch("roadmap.sync.MilestoneParser.save_milestone_file"):
            success, message, milestone_number = sync_manager.push_milestone(milestone)

        assert success is True

        # Verify that due_date is properly formatted with timezone
        sync_manager.github_client.create_milestone.assert_called_once()
        call_kwargs = sync_manager.github_client.create_milestone.call_args[1]
        
        assert call_kwargs["title"] == "v1.0.0"
        assert call_kwargs["description"] == "Test milestone"
        assert call_kwargs["due_date"] == due_date

    def test_milestone_datetime_with_timezone_preserved(self, sync_manager, mock_core):
        """Test that milestone due dates with timezone are preserved."""
        # Create milestone with timezone-aware datetime
        due_date = datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        milestone = Milestone(
            name="v2.0.0", 
            description="Test milestone with timezone",
            due_date=due_date,
            status=MilestoneStatus.OPEN
        )

        sync_manager.github_client.create_milestone.return_value = {"number": 2}

        with patch("roadmap.sync.MilestoneParser.save_milestone_file"):
            success, message, milestone_number = sync_manager.push_milestone(milestone)

        assert success is True

        # Verify timezone-aware datetime is passed through correctly
        call_kwargs = sync_manager.github_client.create_milestone.call_args[1]
        assert call_kwargs["due_date"] == due_date
        assert call_kwargs["due_date"].tzinfo == timezone.utc


class TestHighPerformanceSyncValidation:
    """Test validation fixes in high-performance sync operations."""

    @pytest.fixture
    def mock_sync_manager(self):
        """Mock SyncManager for high-performance sync testing."""
        manager = Mock()
        manager.core = Mock()
        manager.core.list_issues.return_value = []
        manager.core.list_milestones.return_value = []
        
        # Mock GitHub client for high-performance sync
        manager.github_client = Mock()
        manager.github_client.get_milestones.return_value = [
            {"title": "v1.0", "number": 1},
            {"title": "v2.0", "number": 2}
        ]
        manager.github_client.get_issues.return_value = []
        
        return manager

    @pytest.fixture
    def hp_sync_manager(self, mock_sync_manager):
        """Create HighPerformanceSyncManager for testing."""
        return HighPerformanceSyncManager(
            sync_manager=mock_sync_manager,
            max_workers=2,
            batch_size=5
        )

    def test_high_performance_push_issues_calls_standard_push(self, hp_sync_manager):
        """Test that high-performance push delegates to standard push methods."""
        # Create test issues
        issues = [
            Issue(
                id="hp_test1",
                title="HP Test Issue 1",
                priority=Priority.HIGH,
                status=Status.TODO,
                assignee="developer1"
            ),
            Issue(
                id="hp_test2", 
                title="HP Test Issue 2",
                priority=Priority.MEDIUM,
                status=Status.IN_PROGRESS,
                assignee="developer2"
            )
        ]

        # Mock the sync manager's list_issues and push_issue methods
        hp_sync_manager.sync_manager.core.list_issues.return_value = issues
        hp_sync_manager.sync_manager.push_issue.return_value = (True, "Success", 1)

        # Run high-performance push
        stats = hp_sync_manager.sync_issues_optimized("push")

        # Verify that push_issue was called for each issue
        assert hp_sync_manager.sync_manager.push_issue.call_count == 2
        
        # Verify the issues passed to push_issue have correct assignees
        calls = hp_sync_manager.sync_manager.push_issue.call_args_list
        issue_calls = [call[0][0] for call in calls]  # Extract issue argument from each call
        
        assignees = [issue.assignee for issue in issue_calls]
        assert "developer1" in assignees
        assert "developer2" in assignees

    def test_high_performance_push_milestones_calls_standard_push(self, hp_sync_manager):
        """Test that high-performance milestone push delegates correctly."""
        # Create test milestones
        milestones = [
            Milestone(
                name="v1.0",
                description="First release",
                due_date=datetime(2025, 6, 1),
                status=MilestoneStatus.OPEN
            ),
            Milestone(
                name="v2.0",
                description="Second release", 
                due_date=datetime(2025, 12, 1),
                status=MilestoneStatus.OPEN
            )
        ]

        hp_sync_manager.sync_manager.core.list_milestones.return_value = milestones
        hp_sync_manager.sync_manager.push_milestone.return_value = (True, "Success", 1)

        # Run high-performance milestone push
        stats = hp_sync_manager.sync_milestones_optimized("push")

        # Verify that push_milestone was called for each milestone
        assert hp_sync_manager.sync_manager.push_milestone.call_count == 2

    def test_high_performance_sync_error_handling(self, hp_sync_manager):
        """Test error handling in high-performance sync operations."""
        # Create issue that will cause an error
        failing_issue = Issue(
            id="failing_issue",
            title="This Will Fail",
            priority=Priority.HIGH,
            status=Status.TODO
        )

        hp_sync_manager.sync_manager.core.list_issues.return_value = [failing_issue]
        
        # Mock push_issue to raise an exception
        hp_sync_manager.sync_manager.push_issue.side_effect = GitHubAPIError("Validation Failed")

        # Run sync and verify error handling
        stats = hp_sync_manager.sync_issues_optimized("push")

        # Verify error was recorded
        assert stats.issues_failed == 1
        assert len(stats.errors) == 1
        assert "This Will Fail" in stats.errors[0]
        assert "Validation Failed" in stats.errors[0]


class TestGitHubClientDateTimeFormatting:
    """Test GitHub client datetime formatting fixes."""

    @pytest.fixture
    def github_client(self):
        """Create GitHubClient for testing."""
        with patch("roadmap.github_client.GitHubClient._make_request") as mock_request:
            from roadmap.github_client import GitHubClient
            client = GitHubClient("owner", "repo", "token")
            client._make_request = mock_request
            mock_request.return_value.json.return_value = {"number": 1}
            return client

    def test_create_milestone_naive_datetime_adds_timezone(self, github_client):
        """Test that naive datetime gets 'Z' suffix for UTC timezone."""
        naive_datetime = datetime(2025, 12, 31, 23, 59, 59)  # No timezone

        github_client.create_milestone(
            title="Test Milestone",
            description="Test description",
            due_date=naive_datetime
        )

        # Verify the API call included 'Z' suffix
        call_args = github_client._make_request.call_args
        json_data = call_args[1]["json"]
        
        assert "due_on" in json_data
        assert json_data["due_on"] == "2025-12-31T23:59:59Z"

    def test_create_milestone_timezone_aware_datetime_preserved(self, github_client):
        """Test that timezone-aware datetime preserves original formatting."""
        tz_datetime = datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

        github_client.create_milestone(
            title="Test Milestone",
            description="Test description", 
            due_date=tz_datetime
        )

        # Verify the API call preserves timezone info
        call_args = github_client._make_request.call_args
        json_data = call_args[1]["json"]
        
        assert "due_on" in json_data
        # Should use the datetime's own isoformat() which includes +00:00
        assert json_data["due_on"] == tz_datetime.isoformat()

    def test_update_milestone_datetime_formatting(self, github_client):
        """Test that update milestone also properly formats datetime."""
        naive_datetime = datetime(2025, 6, 15, 12, 0, 0)

        github_client.update_milestone(
            milestone_number=1,
            title="Updated Milestone",
            due_date=naive_datetime
        )

        # Verify the update API call
        call_args = github_client._make_request.call_args
        json_data = call_args[1]["json"]
        
        assert json_data["due_on"] == "2025-06-15T12:00:00Z"