"""Tests for MilestoneNamingValidator."""

from pathlib import Path

import pytest

from roadmap.core.services.validators.milestone_naming_validator import (
    MilestoneNamingValidator,
)


class TestIsValidName:
    """Test is_valid_name validation."""

    @pytest.mark.parametrize(
        "name,expected",
        [
            # Valid version patterns (hyphen-separated for unambiguity)
            ("v0-7-0", True),
            ("v0-8-0", True),
            ("v1-0-0", True),
            # Legacy dot patterns still valid but not recommended
            ("v0.7.0", True),
            ("v0.8.0", True),
            # Valid sprint patterns
            ("sprint-1", True),
            ("sprint-q1-2025", True),
            ("sprint-january", True),
            # Valid phase patterns
            ("phase-alpha", True),
            ("phase-beta", True),
            ("phase-1", True),
            # Valid release patterns
            ("release-dec-2025", True),
            ("release-2025-q2", True),
            # Valid special collections
            ("backlog", True),
            ("future-post-v1-0", True),
            ("experimental", True),
            # Single character
            ("a", True),
            ("1", True),
            # Valid with numbers
            ("release1", True),
            ("v1", True),
            # Invalid: empty
            ("", False),
            # Invalid: spaces
            ("sprint 1", False),
            # Invalid: special chars
            ("sprint#1", False),
            ("sprint@1", False),
            ("sprint$1", False),
            ("sprint(1)", False),
            ("sprint/1", False),
            # Invalid: consecutive separators
            ("sprint--1", False),
            ("sprint__1", False),
            # Invalid: starts with hyphen
            ("-sprint", False),
            # Invalid: ends with hyphen
            ("sprint-", False),
            # Invalid: starts with underscore
            ("_sprint", False),
            # Invalid: ends with underscore
            ("sprint_", False),
        ],
    )
    def test_is_valid_name(self, name, expected):
        """Test name validation with various inputs."""
        result = MilestoneNamingValidator.is_valid_name(name)
        assert result == expected


class TestGetSafeName:
    """Test get_safe_name conversion."""

    @pytest.mark.parametrize(
        "input_name,expected_safe",
        [
            # Already safe names (new hyphenated pattern)
            ("v0-7-0", "v0-7-0"),
            ("v0-8-0", "v0-8-0"),
            ("v1-0-0", "v1-0-0"),
            ("sprint-1", "sprint-1"),
            ("phase-beta", "phase-beta"),
            # Legacy patterns with dots (still supported)
            ("v0.7.0", "v0.7.0"),
            # Names with spaces (removed, not replaced)
            ("sprint 1", "sprint1"),
            ("release dec 2025", "releasedec2025"),
            # Mixed case (lowercased)
            ("Sprint-1", "sprint-1"),
            ("PHASE-BETA", "phase-beta"),
            ("V0-7-0", "v0-7-0"),
            # Names with special chars (removed)
            ("sprint#1", "sprint1"),
            ("phase@beta", "phasebeta"),
            # Dots preserved
            ("v0.7.0", "v0.7.0"),
        ],
    )
    def test_get_safe_name(self, input_name, expected_safe):
        """Test safe name generation."""
        result = MilestoneNamingValidator.get_safe_name(input_name)
        assert result == expected_safe


class TestValidateWithFeedback:
    """Test validate_with_feedback with detailed error messages."""

    def test_valid_version_name(self):
        """Test valid version milestone."""
        valid, error = MilestoneNamingValidator.validate_with_feedback("v0-8-0")
        assert valid is True
        assert error is None

    def test_valid_sprint_name(self):
        """Test valid sprint milestone."""
        valid, error = MilestoneNamingValidator.validate_with_feedback("sprint-q1-2025")
        assert valid is True
        assert error is None

    def test_valid_phase_name(self):
        """Test valid phase milestone."""
        valid, error = MilestoneNamingValidator.validate_with_feedback("phase-beta")
        assert valid is True
        assert error is None

    def test_empty_name(self):
        """Test empty name validation."""
        valid, error = MilestoneNamingValidator.validate_with_feedback("")
        assert valid is False
        assert error is not None
        assert "empty" in error.lower()

    def test_name_too_long(self):
        """Test name length validation."""
        long_name = "a" * 101
        valid, error = MilestoneNamingValidator.validate_with_feedback(long_name)
        assert valid is False
        assert error is not None
        assert "100 characters" in error

    def test_invalid_characters(self):
        """Test invalid character detection."""
        valid, error = MilestoneNamingValidator.validate_with_feedback("sprint#1")
        assert valid is False
        assert error is not None
        assert "alphanumeric" in error.lower() or "characters" in error.lower()

    def test_consecutive_hyphens(self):
        """Test consecutive hyphen detection."""
        valid, error = MilestoneNamingValidator.validate_with_feedback("sprint--1")
        assert valid is False
        assert error is not None
        assert "consecutive" in error.lower()

    def test_consecutive_underscores(self):
        """Test consecutive underscore detection."""
        valid, error = MilestoneNamingValidator.validate_with_feedback("phase__beta")
        assert valid is False
        assert error is not None
        assert "consecutive" in error.lower()

    def test_name_with_space_suggests_safe_name(self):
        """Test that names with spaces suggest safe alternative."""
        valid, error = MilestoneNamingValidator.validate_with_feedback("sprint 1")
        assert valid is False
        assert error is not None
        assert "sprint-1" in error

    def test_name_with_uppercase_suggests_safe_name(self):
        """Test that uppercase names suggest safe alternative."""
        valid, error = MilestoneNamingValidator.validate_with_feedback("Sprint-1")
        assert valid is False
        assert error is not None
        assert "sprint-1" in error


class TestFindNamingConflicts:
    """Test find_naming_conflicts for directory scanning."""

    def test_no_conflicts_with_valid_names(self, temp_dir_context):
        """Test directory with compliant names."""
        with temp_dir_context() as tmpdir:
            milestones_dir = Path(tmpdir)

            # Create valid milestone files
            (milestones_dir / "v070.md").touch()
            (milestones_dir / "v080.md").touch()
            (milestones_dir / "backlog.md").touch()

            conflicts = MilestoneNamingValidator.find_naming_conflicts(milestones_dir)
            assert conflicts == []

    def test_detects_unsafe_names(self, temp_dir_context):
        """Test detection of names that need conversion."""
        with temp_dir_context() as tmpdir:
            milestones_dir = Path(tmpdir)

            # Create file with unsafe name (spaces, uppercase)
            (milestones_dir / "Sprint 1.md").touch()

            conflicts = MilestoneNamingValidator.find_naming_conflicts(milestones_dir)
            assert len(conflicts) > 0
            assert any("Sprint 1" in str(c) for c in conflicts)

    def test_detects_collisions(self, temp_dir_context):
        """Test detection of naming collisions."""
        with temp_dir_context() as tmpdir:
            milestones_dir = Path(tmpdir)

            # Create files that would collide when converted to safe names
            (milestones_dir / "Sprint-1.md").touch()
            (milestones_dir / "sprint-1.md").touch()

            conflicts = MilestoneNamingValidator.find_naming_conflicts(milestones_dir)
            # Both files map to "sprint-1", so there's a collision
            assert len(conflicts) >= 1

    def test_nonexistent_directory(self):
        """Test with nonexistent directory."""
        conflicts = MilestoneNamingValidator.find_naming_conflicts(
            Path("/nonexistent/path")
        )
        assert conflicts == []

    def test_empty_directory(self, temp_dir_context):
        """Test with empty directory."""
        with temp_dir_context() as tmpdir:
            milestones_dir = Path(tmpdir)
            conflicts = MilestoneNamingValidator.find_naming_conflicts(milestones_dir)
            assert conflicts == []
