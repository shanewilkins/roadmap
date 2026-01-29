"""Test coverage for version module."""

import pytest

from roadmap import __version__
from roadmap.version import SemanticVersion, VersionManager


class TestSemanticVersion:
    """Test SemanticVersion class."""

    @pytest.mark.parametrize(
        "version_str,expected_major,expected_minor,expected_patch",
        [
            ("1.2.3", 1, 2, 3),
            ("v1.2.3", 1, 2, 3),
            ("0.0.0", 0, 0, 0),
            ("999.999.999", 999, 999, 999),
            ("  v1.2.3  ", 1, 2, 3),
        ],
    )
    def test_semantic_version_creation(
        self, version_str, expected_major, expected_minor, expected_patch
    ):
        """Test creating SemanticVersion with various inputs."""
        version = SemanticVersion(version_str)
        assert version.major == expected_major
        assert version.minor == expected_minor
        assert version.patch == expected_patch

    def test_semantic_version_string_representation(self):
        """Test string representation of SemanticVersion."""
        version = SemanticVersion("1.2.3")
        assert str(version) == "1.2.3"

    def test_semantic_version_repr(self):
        """Test repr of SemanticVersion."""
        version = SemanticVersion("1.2.3")
        assert "1.2.3" in repr(version)

    def test_semantic_version_raw_preserves_input(self):
        """Test that raw attribute preserves original input."""
        version = SemanticVersion("v1.2.3")
        assert "v1.2.3" in version.raw

    @pytest.mark.parametrize(
        "v1_str,v2_str,operator",
        [
            ("2.0.0", "1.9.9", "gt"),
            ("1.0.0", "1.1.0", "lt"),
            ("1.2.3", "1.2.3", "eq"),
            ("1.2.3", "1.2.4", "ne"),
            ("1.2.3", "1.2.3", "gte"),
            ("1.2.2", "1.2.3", "lte"),
        ],
    )
    def test_semantic_version_comparison(self, v1_str, v2_str, operator):
        """Test version comparison operations."""
        v1 = SemanticVersion(v1_str)
        v2 = SemanticVersion(v2_str)
        if operator == "gt":
            assert v1 > v2
        elif operator == "lt":
            assert v1 < v2
        elif operator == "eq":
            assert v1 == v2
        elif operator == "ne":
            assert v1 != v2
        elif operator == "gte":
            assert v1 >= v2
        elif operator == "lte":
            assert v1 <= v2

    @pytest.mark.parametrize(
        "version_str,bump_type,expected_major,expected_minor,expected_patch",
        [
            ("1.2.3", "major", 2, 0, 0),
            ("1.2.3", "minor", 1, 3, 0),
            ("1.2.3", "patch", 1, 2, 4),
            ("0.0.0", "patch", 0, 0, 1),
        ],
    )
    def test_semantic_version_bump(
        self, version_str, bump_type, expected_major, expected_minor, expected_patch
    ):
        """Test bumping version numbers."""
        version = SemanticVersion(version_str)
        if bump_type == "major":
            new_version = version.bump_major()
        elif bump_type == "minor":
            new_version = version.bump_minor()
        elif bump_type == "patch":
            new_version = version.bump_patch()
        assert new_version.major == expected_major
        assert new_version.minor == expected_minor
        assert new_version.patch == expected_patch

    def test_semantic_version_invalid_format_missing_patch(self):
        """Test that invalid format raises ValueError."""
        with pytest.raises(ValueError):
            SemanticVersion("1.2")

    def test_semantic_version_invalid_format_non_numeric(self):
        """Test that non-numeric version raises ValueError."""
        with pytest.raises(ValueError):
            SemanticVersion("a.b.c")

    def test_semantic_version_invalid_format_extra_dots(self):
        """Test that too many version parts raises ValueError."""
        with pytest.raises(ValueError):
            SemanticVersion("1.2.3.4")

    @pytest.mark.parametrize(
        "version_str,should_be_valid",
        [
            ("1.2.3", True),
            ("0.0.0", True),
            ("1.2", False),
            ("a.b.c", False),
            ("1.2.3.4", False),
        ],
    )
    def test_semantic_version_is_valid_check(self, version_str, should_be_valid):
        """Test is_valid_semantic_version static method."""
        assert SemanticVersion.is_valid_semantic_version(version_str) == should_be_valid


class TestVersionManager:
    """Test VersionManager class."""

    def test_version_manager_creation(self, roadmap_structure_factory):
        """Test creating a VersionManager instance."""
        # Factory handles project structure creation: more readable
        project_root = roadmap_structure_factory.create_project_structure()

        manager = VersionManager(project_root)
        assert manager is not None

    def test_version_manager_get_current_version(self, roadmap_structure_factory):
        """Test getting current version from manager."""
        # Factory handles project structure creation
        project_root = roadmap_structure_factory.create_project_structure(
            pyproject_version="1.2.3", init_version="1.2.3"
        )

        manager = VersionManager(project_root)
        version = manager.get_current_version()
        assert isinstance(version, SemanticVersion)
        assert str(version) == "1.2.3"

    def test_version_manager_get_init_version(self, roadmap_structure_factory):
        """Test getting version from __init__.py."""
        # Factory handles project structure creation
        project_root = roadmap_structure_factory.create_project_structure(
            pyproject_version="1.2.3", init_version="1.2.3"
        )

        manager = VersionManager(project_root)
        version = manager.get_init_version()
        assert isinstance(version, SemanticVersion)
        assert str(version) == "1.2.3"

    def test_version_manager_check_consistency(self, roadmap_structure_factory):
        """Test version consistency checking."""
        # Factory handles project structure with consistent versions
        project_root = roadmap_structure_factory.create_project_structure(
            pyproject_version="1.2.3", init_version="1.2.3"
        )

        manager = VersionManager(project_root)
        result = manager.check_version_consistency()
        assert result["consistent"]
        assert result["pyproject_version"] == "1.2.3"
        assert result["init_version"] == "1.2.3"


class TestVersionConstants:
    """Test version module constants."""

    def test_version_constant_exists(self):
        """Test that __version__ constant exists."""
        assert __version__ is not None
        assert isinstance(__version__, str)

    def test_version_constant_format(self):
        """Test that __version__ is in valid format."""
        assert len(__version__) > 0
        # Should start with a digit
        assert __version__[0].isdigit()

    def test_version_constant_is_semantic(self):
        """Test that __version__ can be parsed as semantic version."""
        version = SemanticVersion(__version__)
        assert version is not None


class TestVersionComparison:
    """Test version comparison operations."""

    @pytest.mark.parametrize(
        "v1_str,v2_str,operator,description",
        [
            ("0.1.0", "1.0.0", "lt", "ordering_v1_v2"),
            ("1.0.0", "2.0.0", "lt", "ordering_v2_v3"),
            ("1.9.9", "2.0.0", "lt", "major_precedence"),
            ("1.2.9", "1.3.0", "lt", "minor_precedence"),
            ("1.2.3", "1.2.4", "lt", "patch_precedence"),
        ],
    )
    def test_version_comparison_operations(self, v1_str, v2_str, operator, description):
        """Test version comparison with various precedence rules."""
        v1 = SemanticVersion(v1_str)
        v2 = SemanticVersion(v2_str)
        if operator == "lt":
            assert v1 < v2


class TestVersionEdgeCases:
    """Test edge cases in version handling."""

    def test_version_bump_chain(self):
        """Test chaining version bumps."""
        v1 = SemanticVersion("1.0.0")
        v2 = v1.bump_patch()
        v3 = v2.bump_minor()

        assert str(v1) == "1.0.0"
        assert str(v2) == "1.0.1"
        assert str(v3) == "1.1.0"

    @pytest.mark.parametrize(
        "version_str,should_be_handled",
        [
            ("1.2.3", True),
            ("v1.2.3", True),
            ("  v1.2.3  ", True),
            ("0.0.0", True),
            ("0.0.1", True),
        ],
    )
    def test_version_parsing_edge_cases(self, version_str, should_be_handled):
        """Test version parsing with various edge cases."""
        version = SemanticVersion(version_str)
        assert version is not None
        assert isinstance(version.major, int)


class TestVersionIntegration:
    """Integration tests for version functionality."""

    def test_version_lifecycle(self):
        """Test version lifecycle."""
        v1 = SemanticVersion("1.0.0")
        v2 = v1.bump_minor()
        v3 = v2.bump_patch()

        assert v1 < v2 < v3

    def test_version_sorting(self):
        """Test that versions sort correctly."""
        versions = [
            SemanticVersion("1.0.0"),
            SemanticVersion("0.9.0"),
            SemanticVersion("2.0.0"),
            SemanticVersion("1.1.0"),
            SemanticVersion("1.0.1"),
        ]

        sorted_versions = sorted(versions)

        for i in range(len(sorted_versions) - 1):
            assert sorted_versions[i] <= sorted_versions[i + 1]

    def test_version_manager_with_real_project(self):
        """Test that version manager works with real project structure."""
        from pathlib import Path

        # Get the actual project root
        project_root = Path(__file__).parent.parent.parent.parent

        manager = VersionManager(project_root)

        # Should be able to get versions without errors
        version = manager.get_current_version()
        assert version is not None
        assert isinstance(version, SemanticVersion)
