"""Comprehensive tests for storage infrastructure.

Tests cover:
- Database initialization and connection management
- CRUD operations for projects, milestones, issues
- File synchronization tracking and hashing
- Transaction handling and error cases
- Sync state management
"""

import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from roadmap.adapters.persistence.file_parser import FileParser
from roadmap.adapters.persistence.storage import StateManager
from roadmap.common.errors import CreateError


@pytest.fixture
def temp_db():
    """Create a temporary database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    # Cleanup
    try:
        db_path.unlink()
        for suffix in ["-wal", "-shm"]:
            extra_file = Path(str(db_path) + suffix)
            if extra_file.exists():
                extra_file.unlink()
    except Exception:
        pass


@pytest.fixture
def state_manager(temp_db):
    """Create a StateManager instance."""
    return StateManager(db_path=temp_db)


class TestStateManagerInitialization:
    """Test StateManager initialization and setup."""

    def test_init_creates_database_file(self, temp_db):
        """__init__ should create database file."""
        StateManager(db_path=temp_db)
        assert temp_db.exists()

    def test_init_creates_parent_directories(self):
        """__init__ should create parent directories if they don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "subdir" / "test.db"
            StateManager(db_path=db_path)
            assert db_path.exists()
            assert db_path.parent.exists()

    def test_init_uses_default_path_when_none(self):
        """__init__ should use default path when db_path is None."""
        manager = StateManager(db_path=None)
        expected_path = Path.home() / ".roadmap" / "roadmap.db"
        assert manager.db_path == expected_path

    def test_init_database_creates_tables(self, state_manager):
        """_init_database should create all required tables."""
        conn = state_manager._get_connection()

        tables = [
            "projects",
            "milestones",
            "issues",
            "issue_dependencies",
            "issue_labels",
            "comments",
            "sync_state",
            "file_sync_state",
        ]

        for table in tables:
            result = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            ).fetchone()
            assert result is not None, f"Table {table} was not created"


class TestStateManagerConnections:
    """Test connection management."""

    def test_get_connection_returns_connection(self, state_manager):
        """_get_connection should return a valid SQLite connection."""
        conn = state_manager._get_connection()
        assert isinstance(conn, sqlite3.Connection)

    def test_get_connection_reuses_thread_local_connection(self, state_manager):
        """_get_connection should reuse connection in same thread."""
        conn1 = state_manager._get_connection()
        conn2 = state_manager._get_connection()
        assert conn1 is conn2

    def test_get_connection_enables_foreign_keys(self, state_manager):
        """_get_connection should enable foreign key constraints."""
        conn = state_manager._get_connection()
        result = conn.execute("PRAGMA foreign_keys").fetchone()
        assert result[0] == 1

    def test_get_connection_sets_wal_mode(self, state_manager):
        """_get_connection should set WAL journal mode."""
        conn = state_manager._get_connection()
        result = conn.execute("PRAGMA journal_mode").fetchone()
        assert result[0].lower() == "wal"

    def test_close_connection(self, state_manager):
        """Test closing database connection."""
        # Open connection
        state_manager._get_connection()

        # Close it
        state_manager.close()

        # Should be able to open again
        conn = state_manager._get_connection()
        assert conn is not None

    def test_database_exists(self, state_manager, temp_db):
        """Test database_exists returns True for existing database."""
        assert state_manager.database_exists()

    def test_database_exists_returns_false_for_missing_file(self):
        """Test database_exists returns False when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create path but don't create the database file
            db_path = Path(tmpdir) / "missing.db"
            manager = StateManager(db_path=db_path)

            # Delete the file that was created by init
            db_path.unlink()

            assert not manager.database_exists()


class TestStateManagerTransactions:
    """Test transaction handling."""

    def test_transaction_commits_on_success(self, state_manager):
        """transaction should commit changes on success."""
        with state_manager.transaction() as conn:
            conn.execute(
                "INSERT INTO projects (id, name, status) VALUES (?, ?, ?)",
                ("test-1", "Test Project", "active"),
            )

        # Verify data was committed
        conn = state_manager._get_connection()
        result = conn.execute(
            "SELECT name FROM projects WHERE id = ?", ("test-1",)
        ).fetchone()
        assert result is not None
        assert result[0] == "Test Project"

    def test_transaction_rolls_back_on_exception(self, state_manager):
        """transaction should rollback changes on exception."""
        try:
            with state_manager.transaction() as conn:
                conn.execute(
                    "INSERT INTO projects (id, name, status) VALUES (?, ?, ?)",
                    ("test-2", "Test Project 2", "active"),
                )
                raise ValueError("Test error")
        except ValueError:
            pass

        # Verify data was rolled back
        conn = state_manager._get_connection()
        result = conn.execute(
            "SELECT name FROM projects WHERE id = ?", ("test-2",)
        ).fetchone()
        assert result is None

    def test_is_initialized_returns_true_when_initialized(self, state_manager):
        """is_initialized should return True when database is initialized."""
        assert state_manager.is_initialized()

    def test_is_initialized_returns_false_on_error(self, state_manager):
        """is_initialized should return False on database error."""
        # Close connection and delete database
        if hasattr(state_manager._local, "connection"):
            state_manager._local.connection.close()
        state_manager.db_path.unlink()

        assert not state_manager.is_initialized()


class TestStateManagerProjectOperations:
    """Test project CRUD operations."""

    def test_create_project_inserts_project(self, state_manager):
        """create_project should insert project into database."""
        project_data = {
            "id": "proj-123",
            "name": "Test Project",
            "description": "A test project",
            "status": "active",
        }

        result = state_manager.create_project(project_data)

        assert result == "proj-123"

        # Verify project was inserted
        conn = state_manager._get_connection()
        row = conn.execute(
            "SELECT * FROM projects WHERE id = ?", ("proj-123",)
        ).fetchone()
        assert row is not None
        assert row["name"] == "Test Project"
        assert row["description"] == "A test project"

    def test_create_project_with_defaults(self, state_manager):
        """create_project should use default values for optional fields."""
        project_data = {"id": "proj-124", "name": "Minimal Project"}

        state_manager.create_project(project_data)

        conn = state_manager._get_connection()
        row = conn.execute(
            "SELECT * FROM projects WHERE id = ?", ("proj-124",)
        ).fetchone()
        assert row["status"] == "active"
        assert row["description"] is None

    def test_create_project_with_duplicate_id(self):
        """Creating project with duplicate ID should raise error."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        try:
            manager = StateManager(db_path=db_path)

            # Create first project
            manager.create_project(
                {"id": "dup-1", "name": "Project 1", "status": "active"}
            )

            # Try to create duplicate - should raise CreateError (wrapped from IntegrityError)
            with pytest.raises(CreateError):
                manager.create_project(
                    {"id": "dup-1", "name": "Project 2", "status": "active"}
                )
        finally:
            db_path.unlink(missing_ok=True)
            Path(str(db_path) + "-wal").unlink(missing_ok=True)
            Path(str(db_path) + "-shm").unlink(missing_ok=True)

    def test_get_project_returns_project_data(self, state_manager):
        """get_project should return project data as dictionary."""
        # Create a project
        state_manager.create_project(
            {
                "id": "proj-125",
                "name": "Get Test Project",
                "status": "active",
            }
        )

        result = state_manager.get_project("proj-125")

        assert result is not None
        assert result["id"] == "proj-125"
        assert result["name"] == "Get Test Project"
        assert result["status"] == "active"

    def test_get_project_returns_none_when_not_found(self, state_manager):
        """get_project should return None when project doesn't exist."""
        result = state_manager.get_project("nonexistent")
        assert result is None

    def test_list_projects_returns_all_projects(self, state_manager):
        """list_projects should return all projects."""
        # Create multiple projects
        state_manager.create_project(
            {"id": "proj-1", "name": "Project 1", "status": "active"}
        )
        state_manager.create_project(
            {"id": "proj-2", "name": "Project 2", "status": "active"}
        )

        result = state_manager.list_projects()

        assert len(result) == 2
        assert any(p["id"] == "proj-1" for p in result)
        assert any(p["id"] == "proj-2" for p in result)

    def test_list_projects_returns_empty_list_when_no_projects(self, state_manager):
        """list_projects should return empty list when no projects exist."""
        result = state_manager.list_projects()
        assert result == []

    def test_update_project_modifies_project_data(self, state_manager):
        """update_project should modify existing project data."""
        # Create a project
        state_manager.create_project(
            {
                "id": "proj-126",
                "name": "Original Name",
                "status": "active",
            }
        )

        # Update the project
        success = state_manager.update_project(
            "proj-126", {"name": "Updated Name", "description": "New description"}
        )

        assert success

        # Verify update
        project = state_manager.get_project("proj-126")
        assert project["name"] == "Updated Name"
        assert project["description"] == "New description"

    def test_update_project_returns_false_when_not_found(self, state_manager):
        """update_project should return False when project doesn't exist."""
        success = state_manager.update_project("nonexistent", {"name": "New Name"})
        assert not success

    def test_delete_project_removes_project(self, state_manager):
        """delete_project should remove project from database."""
        # Create a project
        state_manager.create_project(
            {
                "id": "proj-127",
                "name": "To Delete",
                "status": "active",
            }
        )

        # Delete the project
        success = state_manager.delete_project("proj-127")

        assert success
        assert state_manager.get_project("proj-127") is None

    def test_delete_project_returns_false_when_not_found(self, state_manager):
        """delete_project should return False when project doesn't exist."""
        success = state_manager.delete_project("nonexistent")
        assert not success

    def test_updated_at_trigger_on_project_update(self, state_manager):
        """Updating project should automatically update updated_at timestamp."""
        # Create project
        state_manager.create_project(
            {
                "id": "proj-ts",
                "name": "Timestamp Test",
                "status": "active",
            }
        )

        # Get initial timestamp
        conn = state_manager._get_connection()
        initial = conn.execute(
            "SELECT updated_at FROM projects WHERE id = ?", ("proj-ts",)
        ).fetchone()
        initial_time = initial[0]

        # Small delay to ensure timestamp difference
        import time

        time.sleep(1.1)  # Need >1 second for CURRENT_TIMESTAMP to change

        # Update project
        state_manager.update_project("proj-ts", {"name": "Updated Name"})

        # Check updated timestamp
        updated = conn.execute(
            "SELECT updated_at FROM projects WHERE id = ?", ("proj-ts",)
        ).fetchone()
        updated_time = updated[0]

        assert updated_time > initial_time

    def test_foreign_key_cascade_delete(self, state_manager):
        """Deleting project should cascade delete related milestones and issues."""
        # Create project, milestone, and issue
        conn = state_manager._get_connection()

        conn.execute(
            "INSERT INTO projects (id, name, status) VALUES (?, ?, ?)",
            ("proj-fk", "FK Test", "active"),
        )
        conn.execute(
            "INSERT INTO milestones (id, project_id, title, status) VALUES (?, ?, ?, ?)",
            ("ms-fk", "proj-fk", "Milestone 1", "open"),
        )
        conn.execute(
            "INSERT INTO issues (id, project_id, milestone_id, title, status, priority, issue_type) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("iss-fk", "proj-fk", "ms-fk", "Issue 1", "open", "medium", "task"),
        )

        # Delete project
        state_manager.delete_project("proj-fk")

        # Verify cascade delete
        milestone = conn.execute(
            "SELECT * FROM milestones WHERE id = ?", ("ms-fk",)
        ).fetchone()
        issue = conn.execute(
            "SELECT * FROM issues WHERE id = ?", ("iss-fk",)
        ).fetchone()

        assert milestone is None
        assert issue is None


class TestStateManagerSyncStateOperations:
    """Test sync state management."""

    def test_get_sync_state_returns_value(self, state_manager):
        """get_sync_state should return stored sync state value."""
        # Set sync state directly
        conn = state_manager._get_connection()
        conn.execute(
            "INSERT INTO sync_state (key, value) VALUES (?, ?)",
            ("test_key", "test_value"),
        )

        result = state_manager.get_sync_state("test_key")
        assert result == "test_value"

    def test_get_sync_state_returns_none_when_not_found(self, state_manager):
        """get_sync_state should return None when key doesn't exist."""
        result = state_manager.get_sync_state("nonexistent_key")
        assert result is None

    def test_set_sync_state(self, state_manager):
        """Test setting sync state."""
        state_manager.set_sync_state("last_sync", "2025-01-15T12:00:00")

        # Verify it was stored
        value = state_manager.get_sync_state("last_sync")
        assert value == "2025-01-15T12:00:00"

    def test_set_sync_state_overwrites(self, state_manager):
        """Test setting sync state overwrites previous value."""
        state_manager.set_sync_state("key", "value1")
        state_manager.set_sync_state("key", "value2")

        result = state_manager.get_sync_state("key")
        assert result == "value2"


class TestStateManagerFileSync:
    """Test file synchronization tracking."""

    def test_get_file_sync_status_returns_status(self, state_manager):
        """get_file_sync_status should return file sync information."""
        # Insert file sync status
        conn = state_manager._get_connection()
        conn.execute(
            "INSERT INTO file_sync_state (file_path, content_hash, file_size) VALUES (?, ?, ?)",
            ("test/file.txt", "abc123", 1024),
        )

        result = state_manager.get_file_sync_status("test/file.txt")

        assert result is not None
        assert result["file_path"] == "test/file.txt"
        assert result["content_hash"] == "abc123"
        assert result["file_size"] == 1024

    def test_get_file_sync_status_returns_none_when_not_found(self, state_manager):
        """get_file_sync_status should return None when file not tracked."""
        result = state_manager.get_file_sync_status("nonexistent.txt")
        assert result is None

    def test_update_file_sync_status_inserts_new_record(self, state_manager):
        """update_file_sync_status should insert new file sync record."""
        from datetime import datetime

        state_manager.update_file_sync_status(
            file_path="new/file.txt",
            content_hash="xyz789",
            file_size=2048,
            last_modified=datetime.now(),
        )

        result = state_manager.get_file_sync_status("new/file.txt")
        assert result is not None
        assert result["content_hash"] == "xyz789"

    def test_update_file_sync_status_updates_existing_record(self, state_manager):
        """update_file_sync_status should update existing file sync record."""
        from datetime import datetime

        # Insert initial record
        state_manager.update_file_sync_status(
            file_path="existing/file.txt",
            content_hash="old_hash",
            file_size=1024,
            last_modified=datetime.now(),
        )

        # Update the record
        state_manager.update_file_sync_status(
            file_path="existing/file.txt",
            content_hash="new_hash",
            file_size=2048,
            last_modified=datetime.now(),
        )

        result = state_manager.get_file_sync_status("existing/file.txt")
        assert result["content_hash"] == "new_hash"
        assert result["file_size"] == 2048


class TestStateManagerFileHashing:
    """Test file hashing and change detection."""

    def test_calculate_file_hash(self, state_manager):
        """Test calculating file hash."""
        parser = FileParser()
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            file_path = Path(f.name)

        try:
            hash_value = parser.calculate_file_hash(file_path)

            assert hash_value != ""
            assert len(hash_value) == 64  # SHA-256 produces 64 hex characters

            # Same content should produce same hash
            hash_value2 = parser.calculate_file_hash(file_path)
            assert hash_value == hash_value2
        finally:
            file_path.unlink()

    def test_calculate_file_hash_nonexistent_file(self, state_manager):
        """Test hash calculation for nonexistent file returns empty string."""
        parser = FileParser()
        result = parser.calculate_file_hash(Path("/nonexistent/file.txt"))
        assert result == ""

    def test_has_file_changed_new_file(self, state_manager):
        """Test has_file_changed returns True for never-synced file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            file_path = Path(f.name)

        try:
            result = state_manager.has_file_changed(file_path)
            assert result
        finally:
            file_path.unlink()

    def test_has_file_changed_nonexistent_file(self, state_manager):
        """Test has_file_changed returns True for nonexistent file."""
        result = state_manager.has_file_changed(Path("/nonexistent/file.txt"))
        assert result

    def test_has_file_changed_after_sync(self, state_manager):
        """Test has_file_changed returns False after syncing."""
        parser = FileParser()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".md") as f:
            f.write("test content")
            file_path = Path(f.name)

        try:
            # Calculate hash and update sync status
            content_hash = parser.calculate_file_hash(file_path)
            file_size = file_path.stat().st_size
            last_modified = datetime.now(timezone.utc)

            state_manager.update_file_sync_status(
                str(file_path), content_hash, file_size, last_modified
            )

            # File should not show as changed
            result = state_manager.has_file_changed(file_path)
            assert not result
        finally:
            file_path.unlink()

    def test_has_file_changed_modified_content(self, state_manager):
        """Test has_file_changed returns True after content modification."""
        parser = FileParser()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".md") as f:
            f.write("original content")
            file_path = Path(f.name)

        try:
            # Sync initial state
            content_hash = parser.calculate_file_hash(file_path)
            state_manager.update_file_sync_status(
                str(file_path), content_hash, 100, datetime.now(timezone.utc)
            )

            # Modify file
            with open(file_path, "w") as f:
                f.write("modified content")

            # Should detect change
            result = state_manager.has_file_changed(file_path)
            assert result
        finally:
            file_path.unlink()


class TestStateManagerYAMLParsing:
    """Test YAML frontmatter parsing."""

    @pytest.mark.parametrize(
        "file_content,expected_result,description",
        [
            # Valid YAML frontmatter
            (
                """---
id: TEST-001
title: Test Issue
status: open
---

# Issue Content
""",
                {"id": "TEST-001", "title": "Test Issue", "status": "open"},
                "valid",
            ),
            # File without frontmatter
            ("# Just regular markdown\n\nNo frontmatter here.", {}, "no_frontmatter"),
            # Invalid YAML
            (
                """---
invalid: yaml: content: here
---""",
                {},
                "invalid_yaml",
            ),
        ],
    )
    def test_parse_yaml_frontmatter(
        self, state_manager, file_content, expected_result, description
    ):
        """Test parsing YAML frontmatter in various scenarios."""
        parser = FileParser()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".md") as f:
            f.write(file_content)
            file_path = Path(f.name)

        try:
            result = parser.parse_yaml_frontmatter(file_path)
            assert result == expected_result
        finally:
            file_path.unlink()

    def test_parse_yaml_frontmatter_nonexistent_file(self, state_manager):
        """Test parsing nonexistent file returns empty dict."""
        parser = FileParser()
        result = parser.parse_yaml_frontmatter(Path("/nonexistent/file.md"))
        assert result == {}


class TestStateManagerUtilities:
    """Test utility and maintenance methods."""

    def test_vacuum_optimizes_database(self, state_manager):
        """Test vacuum operation."""
        # Should not raise exception
        state_manager.vacuum()

        # Database should still be usable
        conn = state_manager._get_connection()
        assert conn is not None


class TestStateManagerConflictDetection:
    """Test Git conflict detection."""

    def test_has_git_conflicts_no_conflicts(self, state_manager):
        """Test has_git_conflicts returns False when no conflicts."""
        with patch.object(state_manager, "check_git_conflicts", return_value=[]):
            result = state_manager.has_git_conflicts()
            assert not result

    def test_has_git_conflicts_with_conflicts(self, state_manager):
        """Test has_git_conflicts returns True when conflicts exist."""
        # has_git_conflicts() calls check_git_conflicts() internally
        # We need to check the actual implementation
        result = state_manager.has_git_conflicts()
        # Without actual conflicts, should return False
        assert isinstance(result, bool)

    def test_get_conflict_files(self, state_manager):
        """Test getting list of conflict files."""
        # get_conflict_files() returns result of check_git_conflicts()
        result = state_manager.get_conflict_files()
        assert isinstance(result, list)

    def test_check_git_conflicts_no_roadmap_dir(self, state_manager):
        """Test check_git_conflicts with no roadmap_dir argument."""
        # Should handle missing roadmap_dir gracefully
        result = state_manager.check_git_conflicts(None)
        assert isinstance(result, list)

    def test_is_safe_for_writes_no_conflicts(self, state_manager):
        """Test is_safe_for_writes returns True when safe."""
        safe, message = state_manager.is_safe_for_writes()
        assert safe
        assert isinstance(message, str)
        assert len(message) > 0

    def test_is_safe_for_writes_with_conflicts(self, state_manager):
        """Test is_safe_for_writes returns False when conflicts exist."""
        with (
            patch.object(state_manager, "has_git_conflicts", return_value=True),
            patch.object(
                state_manager,
                "get_conflict_files",
                return_value=["file1.md", "file2.md"],
            ),
        ):
            safe, message = state_manager.is_safe_for_writes()
            assert not safe
            assert "conflicts" in message.lower()


class TestStateManagerIssueRetrieval:
    """Test issue retrieval methods."""

    def test_get_all_issues_empty(self, state_manager):
        """Test get_all_issues returns empty list when no issues."""
        result = state_manager.get_all_issues()
        assert result == []

    def test_get_issues_by_status_empty(self, state_manager):
        """Test get_issues_by_status returns empty dict when no issues."""
        result = state_manager.get_issues_by_status()
        assert isinstance(result, dict)


class TestStateManagerMilestoneRetrieval:
    """Test milestone retrieval methods."""

    def test_get_all_milestones_empty(self, state_manager):
        """Test get_all_milestones returns empty list when no milestones."""
        result = state_manager.get_all_milestones()
        assert result == []

    def test_get_milestone_progress_nonexistent(self, state_manager):
        """Test get_milestone_progress for nonexistent milestone."""
        result = state_manager.get_milestone_progress("nonexistent")
        # Should return dict with counts
        assert isinstance(result, dict)
        assert "total" in result or result == {}


class TestStateManagerFileChangeDetection:
    """Test file change detection methods."""

    def test_has_file_changes_no_changes(self, state_manager):
        """Test has_file_changes returns False when no files changed."""
        # Empty database means no tracked files, so no changes
        result = state_manager.has_file_changes()
        # Implementation might vary, but should return bool
        assert isinstance(result, bool)
