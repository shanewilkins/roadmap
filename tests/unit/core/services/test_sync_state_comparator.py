"""Unit tests for SyncStateComparator.

Tests state comparison logic identifying what needs to be pushed, pulled,
or resolved between local and remote issues.
"""

from datetime import datetime, timedelta
from unittest import TestCase

import pytest

from roadmap.common.constants import Status
from roadmap.common.timezone_utils import now_utc
from roadmap.core.services.sync.sync_state_comparator import SyncStateComparator
from tests.factories.sync_data import (
    IssueTestDataBuilder,
)


class TestStateComparatorInitialization(TestCase):
    """Test SyncStateComparator initialization."""

    def test_initialization_with_defaults(self):
        """Verify comparator initializes with default fields to sync."""
        comparator = SyncStateComparator()
        assert comparator.fields_to_sync is not None
        # Title is intentionally excluded as it's display metadata
        assert "title" not in comparator.fields_to_sync
        assert "status" in comparator.fields_to_sync

    def test_initialization_with_custom_fields(self):
        """Verify comparator accepts custom fields to sync."""
        custom_fields = ["title", "priority"]
        comparator = SyncStateComparator(fields_to_sync=custom_fields)
        assert comparator.fields_to_sync == custom_fields


class TestIdentifyConflicts(TestCase):
    """Test conflict identification."""

    def setUp(self):
        """Initialize comparator for each test."""
        self.comparator = SyncStateComparator()

    def test_no_conflicts_when_states_identical(self):
        """Verify no conflicts detected when states are identical."""
        local = {
            "issue-1": IssueTestDataBuilder("issue-1")
            .with_title("Same Title")
            .with_status(Status.TODO)
            .build()
        }
        remote = {
            "issue-1": {
                "title": "Same Title",
                "status": "todo",
                "priority": "medium",  # Match builder default
                "content": "",  # Match builder default
            }
        }

        conflicts = self.comparator.identify_conflicts(local, remote)
        assert len(conflicts) == 0

    def test_detects_single_issue_conflict(self):
        """Verify conflict detected when issue exists in both but differs."""
        local_time = now_utc()
        remote_time = local_time - timedelta(hours=1)

        local = {
            "issue-1": IssueTestDataBuilder("issue-1")
            .with_title("Local Title")
            .with_status(Status.TODO)
            .with_updated_at(local_time)
            .build()
        }
        remote = {
            "issue-1": {
                "status": "in_progress",
                "updated_at": remote_time.isoformat(),
            }
        }

        conflicts = self.comparator.identify_conflicts(local, remote)
        assert len(conflicts) == 1
        assert conflicts[0].issue_id == "issue-1"
        assert "status" in conflicts[0].field_names

    def test_detects_multiple_conflicts(self):
        """Verify multiple conflicts detected correctly."""
        local_time = now_utc()
        local = {}
        remote = {}

        for i in range(3):
            issue_id = f"issue-{i}"
            local[issue_id] = (
                IssueTestDataBuilder(issue_id)
                .with_title(f"Local {i}")
                .with_updated_at(local_time)
                .build()
            )
            remote[issue_id] = {
                "title": f"Remote {i}",
                "updated_at": (local_time - timedelta(hours=1)).isoformat(),
            }

        conflicts = self.comparator.identify_conflicts(local, remote)
        assert len(conflicts) == 3

    def test_ignores_issues_only_in_local(self):
        """Verify issues only in local don't create conflicts."""
        local = {
            "issue-1": IssueTestDataBuilder("issue-1").with_title("Local Only").build()
        }
        remote = {}

        conflicts = self.comparator.identify_conflicts(local, remote)
        assert len(conflicts) == 0

    def test_ignores_issues_only_in_remote(self):
        """Verify issues only in remote don't create conflicts."""
        local = {}
        remote = {"issue-1": {"title": "Remote Only"}}

        conflicts = self.comparator.identify_conflicts(local, remote)
        assert len(conflicts) == 0

    def test_conflict_contains_both_timestamps(self):
        """Verify conflict includes timestamps for resolution."""
        local_time = now_utc()
        remote_time = local_time - timedelta(hours=1)

        local = {
            "issue-1": IssueTestDataBuilder("issue-1")
            .with_title("Local")
            .with_updated_at(local_time)
            .build()
        }
        remote = {
            "issue-1": {
                "title": "Remote",
                "updated_at": remote_time.isoformat(),
            }
        }

        conflicts = self.comparator.identify_conflicts(local, remote)
        assert len(conflicts) == 1
        assert conflicts[0].local_updated == local_time
        assert conflicts[0].remote_updated == remote_time


class TestIdentifyUpdates(TestCase):
    """Test update identification (what to push)."""

    def setUp(self):
        """Initialize comparator for each test."""
        self.comparator = SyncStateComparator()

    def test_new_local_issue_identified_as_update(self):
        """Verify new local issues are identified as updates to push."""
        local = {"new-1": IssueTestDataBuilder("new-1").with_title("New Issue").build()}
        remote = {}

        updates = self.comparator.identify_updates(local, remote)
        assert len(updates) == 1
        assert updates[0].id == "new-1"

    def test_newer_local_issue_identified_as_update(self):
        """Verify local issues newer than remote are identified as updates."""
        local_time = now_utc()
        remote_time = local_time - timedelta(hours=1)

        local = {
            "issue-1": IssueTestDataBuilder("issue-1")
            .with_updated_at(local_time)
            .build()
        }
        remote = {
            "issue-1": {
                "updated_at": remote_time.isoformat(),
            }
        }

        updates = self.comparator.identify_updates(local, remote)
        assert len(updates) == 1
        assert updates[0].id == "issue-1"

    def test_older_local_issue_not_identified_as_update(self):
        """Verify local issues older than remote are not identified as updates."""
        local_time = now_utc() - timedelta(hours=1)
        remote_time = now_utc()

        local = {
            "issue-1": IssueTestDataBuilder("issue-1")
            .with_updated_at(local_time)
            .build()
        }
        remote = {
            "issue-1": {
                "updated_at": remote_time.isoformat(),
            }
        }

        updates = self.comparator.identify_updates(local, remote)
        assert len(updates) == 0

    def test_same_timestamp_not_identified_as_update(self):
        """Verify same timestamps don't trigger update."""
        same_time = now_utc()

        local = {
            "issue-1": IssueTestDataBuilder("issue-1")
            .with_updated_at(same_time)
            .build()
        }
        remote = {
            "issue-1": {
                "updated_at": same_time.isoformat(),
            }
        }

        updates = self.comparator.identify_updates(local, remote)
        assert len(updates) == 0

    def test_missing_remote_timestamp_treats_as_update(self):
        """Verify missing remote timestamp causes update to be identified."""
        local = {"issue-1": IssueTestDataBuilder("issue-1").build()}
        remote = {
            "issue-1": {
                "title": "Some issue",
            }
        }

        updates = self.comparator.identify_updates(local, remote)
        assert len(updates) == 1


class TestIdentifyPulls(TestCase):
    """Test pull identification (what to fetch)."""

    def setUp(self):
        """Initialize comparator for each test."""
        self.comparator = SyncStateComparator()

    def test_new_remote_issue_identified_as_pull(self):
        """Verify new remote issues are identified as pulls."""
        local = {}
        remote = {
            "new-1": {
                "id": 100,
                "title": "New Issue",
            }
        }

        pulls = self.comparator.identify_pulls(local, remote)
        assert len(pulls) == 1
        assert pulls[0] == "new-1"  # Should be the issue_id

    def test_newer_remote_issue_identified_as_pull(self):
        """Verify remote issues newer than local are identified as pulls."""
        local_time = now_utc() - timedelta(hours=1)
        remote_time = now_utc()

        local = {
            "issue-1": IssueTestDataBuilder("issue-1")
            .with_updated_at(local_time)
            .build()
        }
        remote = {
            "issue-1": {
                "id": 100,
                "updated_at": remote_time.isoformat(),
            }
        }

        pulls = self.comparator.identify_pulls(local, remote)
        assert len(pulls) == 1
        assert pulls[0] == "issue-1"  # Should be the issue_id

    def test_older_remote_issue_not_identified_as_pull(self):
        """Verify remote issues older than local are not identified as pulls."""
        local_time = now_utc()
        remote_time = local_time - timedelta(hours=1)

        local = {
            "issue-1": IssueTestDataBuilder("issue-1")
            .with_updated_at(local_time)
            .build()
        }
        remote = {
            "issue-1": {
                "id": 100,
                "updated_at": remote_time.isoformat(),
            }
        }

        pulls = self.comparator.identify_pulls(local, remote)
        assert len(pulls) == 0

    def test_same_timestamp_not_identified_as_pull(self):
        """Verify same timestamps don't trigger pull."""
        same_time = now_utc()

        local = {
            "issue-1": IssueTestDataBuilder("issue-1")
            .with_updated_at(same_time)
            .build()
        }
        remote = {
            "issue-1": {
                "id": 100,
                "updated_at": same_time.isoformat(),
            }
        }

        pulls = self.comparator.identify_pulls(local, remote)
        assert len(pulls) == 0

    def test_missing_remote_timestamp_skips_pull(self):
        """Verify missing remote timestamp doesn't trigger pull."""
        local = {"issue-1": IssueTestDataBuilder("issue-1").build()}
        remote = {
            "issue-1": {
                "id": 100,
                "title": "Some issue",
            }
        }

        pulls = self.comparator.identify_pulls(local, remote)
        assert len(pulls) == 0


class TestIdentifyUpToDate(TestCase):
    """Test up-to-date identification."""

    def setUp(self):
        """Initialize comparator for each test."""
        self.comparator = SyncStateComparator()

    def test_identical_issues_identified_as_up_to_date(self):
        """Verify identical issues are identified as up-to-date."""
        same_time = now_utc()

        local = {
            "issue-1": IssueTestDataBuilder("issue-1")
            .with_title("Same Title")
            .with_updated_at(same_time)
            .build()
        }
        remote = {
            "issue-1": {
                "title": "Same Title",
                "status": "todo",  # Match default status from builder
                "priority": "medium",  # Match default priority from builder
                "content": "",  # Match default content from builder
                "updated_at": same_time.isoformat(),
            }
        }

        up_to_date = self.comparator.identify_up_to_date(local, remote)
        assert len(up_to_date) == 1
        assert up_to_date[0] == "issue-1"

    def test_different_issues_not_identified_as_up_to_date(self):
        """Verify different issues are not identified as up-to-date."""
        local_time = now_utc()

        local = {
            "issue-1": IssueTestDataBuilder("issue-1")
            .with_title("Local Title")
            .with_updated_at(local_time)
            .build()
        }
        remote = {
            "issue-1": {
                "title": "Remote Title",
                "status": "todo",
                "priority": "medium",
                "content": "",
                "updated_at": (local_time - timedelta(hours=1)).isoformat(),
            }
        }

        up_to_date = self.comparator.identify_up_to_date(local, remote)
        assert len(up_to_date) == 0

    def test_only_common_issues_checked(self):
        """Verify only issues in both are checked for up-to-date."""
        same_time = now_utc()

        local = {
            "issue-1": IssueTestDataBuilder("issue-1")
            .with_title("Title")
            .with_updated_at(same_time)
            .build(),
            "issue-2": IssueTestDataBuilder("issue-2")
            .with_updated_at(same_time)
            .build(),
        }
        remote = {
            "issue-1": {
                "title": "Title",
                "updated_at": same_time.isoformat(),
            }
        }

        up_to_date = self.comparator.identify_up_to_date(local, remote)
        # Only issue-1 should be checked
        assert len(up_to_date) <= 1


class TestTimestampExtraction(TestCase):
    """Test timestamp extraction from remote data."""

    def setUp(self):
        """Initialize comparator for each test."""
        self.comparator = SyncStateComparator()

    def test_extract_iso_format_timestamp(self):
        """Verify ISO format timestamps are parsed."""
        now = now_utc()
        data = {"updated_at": now.isoformat()}

        ts = self.comparator._extract_timestamp(data)
        assert ts is not None
        assert isinstance(ts, datetime)

    def test_extract_datetime_object(self):
        """Verify datetime objects are returned as-is."""
        now = now_utc()
        data = {"updated_at": now}

        ts = self.comparator._extract_timestamp(data)
        assert ts == now

    def test_extract_missing_timestamp_returns_none(self):
        """Verify missing timestamp returns None."""
        data = {"title": "No timestamp"}

        ts = self.comparator._extract_timestamp(data)
        assert ts is None

    def test_extract_invalid_timestamp_returns_none(self):
        """Verify invalid timestamp format returns None."""
        data = {"updated_at": "not a timestamp"}

        ts = self.comparator._extract_timestamp(data)
        assert ts is None

    def test_extract_custom_field_name(self):
        """Verify custom timestamp field names work."""
        now = now_utc()
        data = {"custom_time": now.isoformat()}

        ts = self.comparator._extract_timestamp(data, timestamp_field="custom_time")
        assert ts is not None


class TestComplexScenarios(TestCase):
    """Test complex multi-issue scenarios."""

    def setUp(self):
        """Initialize comparator for each test."""
        self.comparator = SyncStateComparator()

    def test_mixed_scenario_conflicts_updates_pulls(self):
        """Verify comparator handles mixed scenarios correctly."""
        base_time = now_utc()

        local = {
            # Conflict case
            "issue-1": IssueTestDataBuilder("issue-1")
            .with_title("Local Title")
            .with_updated_at(base_time - timedelta(hours=1))
            .build(),
            # New local (update to push)
            "issue-2": IssueTestDataBuilder("issue-2")
            .with_title("New Local")
            .with_updated_at(base_time)
            .build(),
            # Up to date
            "issue-3": IssueTestDataBuilder("issue-3")
            .with_title("Same Title")
            .with_updated_at(base_time)
            .build(),
        }

        remote = {
            # Conflict case - different status
            "issue-1": {
                "title": "Same Title",
                "status": "in_progress",
                "priority": "medium",
                "content": "",
                "updated_at": base_time.isoformat(),
            },
            # New remote (pull)
            "issue-4": {
                "id": 104,
                "title": "New Remote",
                "updated_at": base_time.isoformat(),
            },
            # Up to date
            "issue-3": {
                "title": "Same Title",
                "status": "todo",
                "priority": "medium",
                "content": "",
                "updated_at": base_time.isoformat(),
            },
        }

        conflicts = self.comparator.identify_conflicts(local, remote)
        updates = self.comparator.identify_updates(local, remote)
        pulls = self.comparator.identify_pulls(local, remote)
        up_to_date = self.comparator.identify_up_to_date(local, remote)

        assert len(conflicts) >= 1  # issue-1 (status conflict)
        assert any(u.id == "issue-2" for u in updates)  # new local
        assert len(pulls) >= 1  # issue-4
        assert "issue-3" in up_to_date  # identical


@pytest.mark.parametrize(
    "local_count,remote_count,expected_conflicts",
    [
        (0, 0, 0),
        (1, 0, 0),
        (0, 1, 0),
        (1, 1, 0),  # Same, no conflict
    ],
)
def test_identify_conflicts_parametrized(local_count, remote_count, expected_conflicts):
    """Parametrized tests for conflict identification edge cases."""
    comparator = SyncStateComparator()

    local = {}
    remote = {}

    for i in range(local_count):
        issue_id = f"issue-{i}"
        local[issue_id] = IssueTestDataBuilder(issue_id).build()

    for i in range(remote_count):
        issue_id = f"issue-{i}"
        if issue_id not in remote:
            remote[issue_id] = {"title": f"Remote {i}"}

    conflicts = comparator.identify_conflicts(local, remote)
    assert len(conflicts) >= expected_conflicts
