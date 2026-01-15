"""Unit tests for sync baseline persistence layer.

Tests verify that sync baseline operations properly save, retrieve, and clear
baseline state from the database, including schema integrity and data migration.
"""

import json
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from roadmap.adapters.persistence.database_manager import DatabaseManager
from roadmap.adapters.persistence.storage.state_manager import StateManager
from roadmap.common.logging import get_logger

logger = get_logger(__name__)


class TestSyncBaselineSchema(unittest.TestCase):
    """Test sync_base_state table schema and constraints."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.db_manager = DatabaseManager(str(self.db_path))

    def tearDown(self):
        """Clean up temp directory."""
        self.temp_dir.cleanup()

    def test_sync_base_state_table_exists(self):
        """Test that sync_base_state table is created."""
        conn = self.db_manager._get_connection()
        cursor = conn.cursor()

        # Query sqlite_master to check table existence
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='sync_base_state'
        """
        )
        result = cursor.fetchone()
        self.assertIsNotNone(result, "sync_base_state table should exist")

    def test_sync_base_state_columns(self):
        """Test that sync_base_state has correct columns."""
        conn = self.db_manager._get_connection()
        cursor = conn.cursor()

        # Get table info
        cursor.execute("PRAGMA table_info(sync_base_state)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]

        expected_columns = [
            "issue_id",
            "status",
            "assignee",
            "milestone",
            "description",
            "headline",
            "content",
            "labels",
            "synced_at",
        ]

        for col in expected_columns:
            self.assertIn(col, column_names, f"Column {col} should exist")

    def test_sync_base_state_primary_key(self):
        """Test that issue_id is primary key."""
        conn = self.db_manager._get_connection()
        cursor = conn.cursor()

        # Get primary key info
        cursor.execute("PRAGMA table_info(sync_base_state)")
        columns = cursor.fetchall()

        # Find issue_id column and check pk flag
        issue_id_col = [col for col in columns if col[1] == "issue_id"][0]
        self.assertEqual(issue_id_col[5], 1, "issue_id should be primary key")

    def test_insert_into_sync_base_state(self):
        """Test inserting baseline data."""
        with self.db_manager.transaction() as conn:
            conn.execute(
                """
                INSERT INTO sync_base_state
                (issue_id, status, assignee, milestone, description, headline, content, labels, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    "issue-1",
                    "open",
                    "alice@example.com",
                    "v1.0",
                    "Description",
                    "Headline",
                    "Content",
                    json.dumps(["feature", "bug"]),
                    datetime.now(UTC).isoformat(),
                ),
            )

        # Verify insert worked
        conn = self.db_manager._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sync_base_state")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 1)

    def test_duplicate_issue_id_constraint(self):
        """Test that duplicate issue_id raises error."""
        now = datetime.now(UTC).isoformat()

        with self.db_manager.transaction() as conn:
            conn.execute(
                """
                INSERT INTO sync_base_state
                (issue_id, status, assignee, milestone, description, headline, content, labels, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    "issue-1",
                    "open",
                    "alice",
                    None,
                    "Desc",
                    "Head",
                    "Content",
                    "[]",
                    now,
                ),
            )

        # Try to insert duplicate
        with self.assertRaises(sqlite3.IntegrityError):
            with self.db_manager.transaction() as conn:
                conn.execute(
                    """
                    INSERT INTO sync_base_state
                    (issue_id, status, assignee, milestone, description, headline, content, labels, synced_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        "issue-1",
                        "closed",
                        "bob",
                        None,
                        "Desc2",
                        "Head2",
                        "Content2",
                        "[]",
                        now,
                    ),
                )


class TestSyncBaselinePersistence(unittest.TestCase):
    """Test sync baseline save/load/clear operations."""

    def setUp(self):
        """Set up test fixtures with StateManager."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root_path = Path(self.temp_dir.name)
        self.root_path.mkdir(exist_ok=True)

        # Create database manager and state manager
        self.db_path = self.root_path / "test.db"
        self.state_manager = StateManager(db_path=str(self.db_path))

    def tearDown(self):
        """Clean up temp directory."""
        self.temp_dir.cleanup()

    def test_save_and_retrieve_baseline(self):
        """Test saving and retrieving baseline."""
        baseline = {
            "issue-1": {
                "status": "open",
                "assignee": "alice@example.com",
                "milestone": "v1.0",
                "headline": "Fix bug",
                "content": "Fix critical bug",
                "labels": ["bug", "critical"],
            },
            "issue-2": {
                "status": "closed",
                "assignee": "bob@example.com",
                "milestone": "v1.0",
                "headline": "Add feature",
                "content": "Add new feature",
                "labels": ["feature"],
            },
        }

        # Save baseline
        result = self.state_manager.save_sync_baseline(baseline)
        self.assertTrue(result, "save_sync_baseline should return True")

        # Retrieve baseline
        retrieved = self.state_manager.get_sync_baseline()
        self.assertIsNotNone(retrieved)
        assert isinstance(retrieved, dict)

        # Verify data
        self.assertEqual(len(retrieved), 2)
        self.assertIn("issue-1", retrieved)
        self.assertIn("issue-2", retrieved)

        issue_1 = retrieved["issue-1"]
        self.assertEqual(issue_1["status"], "open")
        self.assertEqual(issue_1["assignee"], "alice@example.com")
        self.assertEqual(issue_1["milestone"], "v1.0")
        self.assertEqual(issue_1["headline"], "Fix bug")
        self.assertEqual(issue_1["content"], "Fix critical bug")
        self.assertEqual(issue_1["labels"], ["bug", "critical"])

    def test_baseline_overwrites_previous(self):
        """Test that saving new baseline overwrites previous."""
        baseline_1 = {
            "issue-1": {
                "status": "open",
                "assignee": "alice",
                "milestone": None,
                "headline": "Old",
                "content": "Old",
                "labels": [],
            }
        }

        baseline_2 = {
            "issue-2": {
                "status": "closed",
                "assignee": "bob",
                "milestone": "v1.0",
                "headline": "New",
                "content": "New",
                "labels": ["feature"],
            }
        }

        # Save first baseline
        self.state_manager.save_sync_baseline(baseline_1)
        retrieved_1 = self.state_manager.get_sync_baseline()
        self.assertIsNotNone(retrieved_1)
        assert isinstance(retrieved_1, dict)  # Type guard
        self.assertEqual(len(retrieved_1), 1)
        self.assertIn("issue-1", retrieved_1)

        # Save second baseline
        self.state_manager.save_sync_baseline(baseline_2)
        retrieved_2 = self.state_manager.get_sync_baseline()
        self.assertIsNotNone(retrieved_2)
        assert isinstance(retrieved_2, dict)  # Type guard

        # Should have new issue, not old
        self.assertEqual(len(retrieved_2), 1)
        self.assertNotIn("issue-1", retrieved_2)
        self.assertIn("issue-2", retrieved_2)

    def test_clear_baseline(self):
        """Test clearing baseline."""
        baseline = {
            "issue-1": {
                "status": "open",
                "assignee": "alice",
                "milestone": None,
                "headline": "Test",
                "content": "Test",
                "labels": [],
            }
        }

        # Save baseline
        self.state_manager.save_sync_baseline(baseline)
        retrieved = self.state_manager.get_sync_baseline()
        self.assertIsNotNone(retrieved)

        # Clear baseline
        result = self.state_manager.clear_sync_baseline()
        self.assertTrue(result, "clear_sync_baseline should return True")

        # Verify cleared
        retrieved = self.state_manager.get_sync_baseline()
        self.assertIsNone(retrieved)

    def test_baseline_with_null_values(self):
        """Test baseline with null/None values."""
        baseline = {
            "issue-1": {
                "status": "open",
                "assignee": None,
                "milestone": None,
                "headline": "",
                "content": "",
                "labels": [],
            }
        }

        result = self.state_manager.save_sync_baseline(baseline)
        self.assertTrue(result)

        retrieved = self.state_manager.get_sync_baseline()
        self.assertIsNotNone(retrieved)
        assert isinstance(retrieved, dict)  # Type guard
        issue = retrieved["issue-1"]
        self.assertIsNone(issue["assignee"])
        self.assertIsNone(issue["milestone"])
        self.assertEqual(issue["labels"], [])

    def test_baseline_with_complex_labels(self):
        """Test baseline with various label formats."""
        baseline = {
            "issue-1": {
                "status": "open",
                "assignee": "alice",
                "milestone": "v1.0",
                "headline": "Test",
                "content": "Test",
                "labels": ["feature", "high-priority", "ui/ux", "bug-fix"],
            }
        }

        result = self.state_manager.save_sync_baseline(baseline)
        self.assertTrue(result)

        retrieved = self.state_manager.get_sync_baseline()
        self.assertIsNotNone(retrieved)
        assert isinstance(retrieved, dict)  # Type guard
        issue = retrieved["issue-1"]
        self.assertEqual(
            issue["labels"], ["feature", "high-priority", "ui/ux", "bug-fix"]
        )

    def test_baseline_empty_database(self):
        """Test get_sync_baseline on empty database."""
        retrieved = self.state_manager.get_sync_baseline()
        self.assertIsNone(retrieved)

    def test_baseline_with_special_characters(self):
        """Test baseline with special characters in fields."""
        baseline = {
            "issue-1": {
                "status": "open",
                "assignee": "alice+test@example.com",
                "milestone": "v1.0-rc1",
                "headline": "Fix: Bug with 'quotes' and \"double quotes\"",
                "content": "Test with unicode: café, 日本語, emoji 🚀",
                "labels": ["type/bug", "fix:urgent"],
            }
        }

        result = self.state_manager.save_sync_baseline(baseline)
        self.assertTrue(result)

        retrieved = self.state_manager.get_sync_baseline()
        self.assertIsNotNone(retrieved)
        assert isinstance(retrieved, dict)  # Type guard
        issue = retrieved["issue-1"]
        self.assertEqual(issue["assignee"], "alice+test@example.com")
        self.assertEqual(
            issue["headline"], "Fix: Bug with 'quotes' and \"double quotes\""
        )
        self.assertIn("café", issue["content"])
        self.assertIn("日本語", issue["content"])
        self.assertIn("🚀", issue["content"])

    def test_baseline_synced_at_timestamp(self):
        """Test that synced_at timestamp is preserved."""
        baseline = {
            "issue-1": {
                "status": "open",
                "assignee": "alice",
                "milestone": None,
                "headline": "Test",
                "content": "Test",
                "labels": [],
            }
        }

        result = self.state_manager.save_sync_baseline(baseline)
        self.assertTrue(result)

        retrieved = self.state_manager.get_sync_baseline()
        self.assertIsNotNone(retrieved)
        assert isinstance(retrieved, dict)  # Type guard
        issue = retrieved["issue-1"]

        # Verify synced_at exists and is ISO format
        self.assertIn("synced_at", issue)
        synced_at = issue["synced_at"]
        self.assertIsInstance(synced_at, str)

        # Should be parseable as ISO datetime
        try:
            datetime.fromisoformat(synced_at)
        except ValueError:
            self.fail(f"synced_at '{synced_at}' is not valid ISO format")


class TestSyncBaselineDataMigration(unittest.TestCase):
    """Test baseline data migration and schema compatibility."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root_path = Path(self.temp_dir.name)
        self.db_path = self.root_path / "test.db"
        self.db_manager = DatabaseManager(str(self.db_path))

    def tearDown(self):
        """Clean up temp directory."""
        self.temp_dir.cleanup()

    def test_baseline_with_missing_optional_fields(self):
        """Test loading baseline with missing optional fields."""
        now = datetime.now(UTC).isoformat()

        # Insert baseline with missing headline and content
        with self.db_manager.transaction() as conn:
            conn.execute(
                """
                INSERT INTO sync_base_state
                (issue_id, status, assignee, milestone, description, headline, content, labels, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                ("issue-1", "open", "alice", None, "Desc", None, None, "[]", now),
            )

        # Create state manager and retrieve
        state_manager = StateManager(db_path=str(self.db_path))

        retrieved = state_manager.get_sync_baseline()
        self.assertIsNotNone(retrieved)
        assert isinstance(retrieved, dict)  # Type guard
        issue = retrieved["issue-1"]

        # Fields should be present with default values
        self.assertIsNone(issue["headline"])
        self.assertIsNone(issue["content"])
        self.assertEqual(issue["labels"], [])

    def test_baseline_with_malformed_labels_json(self):
        """Test handling of malformed labels JSON."""
        now = datetime.now(UTC).isoformat()

        # Insert baseline with invalid JSON labels
        with self.db_manager.transaction() as conn:
            conn.execute(
                """
                INSERT INTO sync_base_state
                (issue_id, status, assignee, milestone, description, headline, content, labels, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    "issue-1",
                    "open",
                    "alice",
                    None,
                    "Desc",
                    "Head",
                    "Content",
                    "{invalid json}",
                    now,
                ),
            )

        # Create state manager and retrieve
        state_manager = StateManager(db_path=str(self.db_path))

        # Should still work with graceful fallback to empty labels
        retrieved = state_manager.get_sync_baseline()
        self.assertIsNotNone(retrieved)
        assert isinstance(retrieved, dict)  # Type guard
        issue = retrieved["issue-1"]
        self.assertEqual(issue["labels"], [])


if __name__ == "__main__":
    unittest.main()
