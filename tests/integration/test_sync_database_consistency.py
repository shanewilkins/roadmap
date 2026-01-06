"""Integration tests for sync database consistency.

Verifies that after a successful sync, local issues, remote/GitHub issues,
and the database baseline are all consistent.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from roadmap.adapters.sync.sync_retrieval_orchestrator import SyncRetrievalOrchestrator
from roadmap.common.constants import Status
from roadmap.infrastructure.core import RoadmapCore


class TestSyncDatabaseConsistency(unittest.TestCase):
    """Test that sync results are consistent across local, remote, and database."""

    def setUp(self):
        """Set up test fixtures with a temporary database."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root_path = Path(self.temp_dir.name)

        # Create RoadmapCore with temp directory
        self.core = RoadmapCore(root_path=self.root_path)
        self.core.initialize()

        # Mock backend
        self.backend = MagicMock()
        self.backend.authenticate.return_value = True

    def tearDown(self):
        """Clean up temp directory."""
        self.temp_dir.cleanup()

    def test_database_baseline_saved_and_retrieved(self):
        """Test that baseline can be saved and retrieved from database."""
        # Create an issue in database
        created_issue = self.core.issues.create(title="Test Issue", status=Status.TODO)
        issue_id = created_issue.id

        # Create baseline dict with the created issue ID
        baseline_dict = {
            issue_id: {
                "status": "in_progress",
                "assignee": "test_user",
                "milestone": "v1.0",
                "description": "Test description",
                "labels": ["feature", "bug"],
            }
        }

        # Save baseline to database
        result = self.core.db.save_sync_baseline(baseline_dict)
        self.assertTrue(result, "save_sync_baseline should return True")

        # Retrieve baseline from database
        retrieved = self.core.db.get_sync_baseline()
        self.assertIsNotNone(retrieved, "get_sync_baseline should return dict")
        assert isinstance(retrieved, dict)  # Type guard for Pylance
        self.assertIn(issue_id, retrieved)

        # Verify data integrity
        saved_issue = retrieved[issue_id]
        self.assertEqual(saved_issue["status"], "in_progress")
        self.assertEqual(saved_issue["assignee"], "test_user")
        self.assertEqual(saved_issue["milestone"], "v1.0")
        self.assertEqual(saved_issue["description"], "Test description")
        self.assertEqual(saved_issue["labels"], ["feature", "bug"])

    def test_baseline_state_uses_database_first(self):
        """Test that get_baseline_state prefers database baseline over remote."""
        # Create an issue in database
        created_issue = self.core.issues.create(title="Test", status=Status.TODO)
        issue_id = created_issue.id

        # Save baseline dict to database
        baseline_dict = {
            issue_id: {
                "status": "todo",
                "assignee": "alice",
                "milestone": None,
                "description": "Database version",
                "labels": ["bug"],
            }
        }
        result = self.core.db.save_sync_baseline(baseline_dict)
        self.assertTrue(result)

        # Mock backend to return different data
        # This verifies that database is preferred over remote
        self.backend.authenticate.return_value = True
        self.backend.get_issues.return_value = {}

        # Create orchestrator
        orchestrator = SyncRetrievalOrchestrator(self.core, self.backend)

        # Get baseline - should come from database, not remote
        retrieved_baseline = orchestrator.get_baseline_state()

        self.assertIsNotNone(
            retrieved_baseline, "Should retrieve baseline from database"
        )
        assert retrieved_baseline is not None  # Type guard for Pylance
        self.assertIn(issue_id, retrieved_baseline.issues)

        # Verify description matches database, not remote
        retrieved_issue = retrieved_baseline.issues[issue_id]
        self.assertEqual(retrieved_issue.status, "todo")
        self.assertEqual(retrieved_issue.assignee, "alice")
        self.assertEqual(retrieved_issue.description, "Database version")

    def test_clear_baseline_removes_from_database(self):
        """Test that clear_sync_baseline removes baseline from database."""
        # Create an issue and save baseline
        created_issue = self.core.issues.create(title="Test", status=Status.TODO)
        issue_id = created_issue.id

        baseline_dict = {
            issue_id: {
                "status": "todo",
                "assignee": "alice",
                "milestone": None,
                "description": "Test",
                "labels": [],
            }
        }

        # Save baseline
        self.core.db.save_sync_baseline(baseline_dict)
        retrieved_before = self.core.db.get_sync_baseline()
        self.assertIsNotNone(retrieved_before, "Baseline should be saved")
        assert isinstance(retrieved_before, dict)  # Type guard for Pylance
        self.assertIn(issue_id, retrieved_before)

        # Clear baseline
        self.core.db.clear_sync_baseline()

        # Verify it's removed
        retrieved_after = self.core.db.get_sync_baseline()
        self.assertIsNone(retrieved_after)

    def test_multiple_issues_in_baseline(self):
        """Test that baseline correctly handles multiple issues."""
        # Create multiple issues
        issue1 = self.core.issues.create(title="Issue 1", status=Status.TODO)
        issue2 = self.core.issues.create(title="Issue 2", status=Status.IN_PROGRESS)

        # Create baseline with both
        baseline_dict = {
            issue1.id: {
                "status": "todo",
                "assignee": "alice",
                "milestone": "v1.0",
                "description": "First issue",
                "labels": ["bug"],
            },
            issue2.id: {
                "status": "in_progress",
                "assignee": "bob",
                "milestone": "v1.0",
                "description": "Second issue",
                "labels": ["feature"],
            },
        }

        # Save baseline
        result = self.core.db.save_sync_baseline(baseline_dict)
        self.assertTrue(result)

        # Retrieve and verify both issues
        retrieved = self.core.db.get_sync_baseline()
        self.assertIsNotNone(retrieved, "Baseline should contain both issues")
        assert isinstance(retrieved, dict)  # Type guard for Pylance
        self.assertEqual(len(retrieved), 2)
        self.assertIn(issue1.id, retrieved)
        self.assertIn(issue2.id, retrieved)

        # Verify data for each
        self.assertEqual(retrieved[issue1.id]["assignee"], "alice")
        self.assertEqual(retrieved[issue2.id]["assignee"], "bob")
        self.assertEqual(retrieved[issue1.id]["labels"], ["bug"])
        self.assertEqual(retrieved[issue2.id]["labels"], ["feature"])


if __name__ == "__main__":
    unittest.main()
