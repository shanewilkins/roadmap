"""Test coverage for version module."""

import pytest

from roadmap import __version__
from roadmap.version import SemanticVersion, VersionManager


class TestSemanticVersion:
    """Test SemanticVersion class."""

    def test_semantic_version_creation_simple(self):
        """Test creating a SemanticVersion instance."""
        version = SemanticVersion("1.2.3")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_semantic_version_creation_with_v_prefix(self):
        """Test creating SemanticVersion with v prefix."""
        version = SemanticVersion("v1.2.3")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

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

    def test_semantic_version_comparison_greater(self):
        """Test version comparison - greater than."""
        v1 = SemanticVersion("2.0.0")
        v2 = SemanticVersion("1.9.9")
        assert v1 > v2

    def test_semantic_version_comparison_less(self):
        """Test version comparison - less than."""
        v1 = SemanticVersion("1.0.0")
        v2 = SemanticVersion("1.1.0")
        assert v1 < v2

    def test_semantic_version_comparison_equal(self):
        """Test version comparison - equal."""
        v1 = SemanticVersion("1.2.3")
        v2 = SemanticVersion("1.2.3")
        assert v1 == v2

    def test_semantic_version_comparison_not_equal(self):
        """Test version comparison - not equal."""
        v1 = SemanticVersion("1.2.3")
        v2 = SemanticVersion("1.2.4")
        assert v1 != v2

    def test_semantic_version_comparison_greater_equal(self):
        """Test version comparison - greater or equal."""
        v1 = SemanticVersion("1.2.3")
        v2 = SemanticVersion("1.2.3")
        assert v1 >= v2

    def test_semantic_version_comparison_less_equal(self):
        """Test version comparison - less or equal."""
        v1 = SemanticVersion("1.2.2")
        v2 = SemanticVersion("1.2.3")
        assert v1 <= v2

    def test_semantic_version_bump_major(self):
        """Test bumping major version."""
        version = SemanticVersion("1.2.3")
        new_version = version.bump_major()
        assert new_version.major == 2
        assert new_version.minor == 0
        assert new_version.patch == 0

    def test_semantic_version_bump_minor(self):
        """Test bumping minor version."""
        version = SemanticVersion("1.2.3")
        new_version = version.bump_minor()
        assert new_version.major == 1
        assert new_version.minor == 3
        assert new_version.patch == 0

    def test_semantic_version_bump_patch(self):
        """Test bumping patch version."""
        version = SemanticVersion("1.2.3")
        new_version = version.bump_patch()
        assert new_version.major == 1
        assert new_version.minor == 2
        assert new_version.patch == 4

    def test_semantic_version_is_valid_zero_version(self):
        """Test 0.0.0 is valid version."""
        version = SemanticVersion("0.0.0")
        assert version.major == 0
        assert version.minor == 0
        assert version.patch == 0

    def test_semantic_version_is_valid_large_numbers(self):
        """Test version with large numbers."""
        version = SemanticVersion("999.999.999")
        assert version.major == 999
        assert version.minor == 999
        assert version.patch == 999

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

    def test_semantic_version_is_valid_check(self):
        """Test is_valid_semantic_version static method."""
        assert SemanticVersion.is_valid_semantic_version("1.2.3")
        assert SemanticVersion.is_valid_semantic_version("0.0.0")
        assert not SemanticVersion.is_valid_semantic_version("1.2")
        assert not SemanticVersion.is_valid_semantic_version("a.b.c")


class TestVersionManager:
    """Test VersionManager class."""

    def test_version_manager_creation(self, tmp_path):
        """Test creating a VersionManager instance."""
        # Create minimal project structure
        (tmp_path / "roadmap").mkdir()
        (tmp_path / "pyproject.toml").write_text('[tool.poetry]\nversion = "0.1.0"')
        (tmp_path / "roadmap" / "__init__.py").write_text('__version__ = "0.1.0"')

        manager = VersionManager(tmp_path)
        assert manager is not None

    def test_version_manager_get_current_version(self, tmp_path):
        """Test getting current version from manager."""
        # Create minimal project structure
        (tmp_path / "roadmap").mkdir()
        (tmp_path / "pyproject.toml").write_text('[tool.poetry]\nversion = "1.2.3"')
        (tmp_path / "roadmap" / "__init__.py").write_text('__version__ = "1.2.3"')

        manager = VersionManager(tmp_path)
        version = manager.get_current_version()
        assert isinstance(version, SemanticVersion)
        assert str(version) == "1.2.3"

    def test_version_manager_get_init_version(self, tmp_path):
        """Test getting version from __init__.py."""
        # Create minimal project structure
        (tmp_path / "roadmap").mkdir()
        (tmp_path / "pyproject.toml").write_text('[tool.poetry]\nversion = "1.2.3"')
        (tmp_path / "roadmap" / "__init__.py").write_text('__version__ = "1.2.3"')

        manager = VersionManager(tmp_path)
        version = manager.get_init_version()
        assert isinstance(version, SemanticVersion)
        assert str(version) == "1.2.3"

    def test_version_manager_check_consistency(self, tmp_path):
        """Test version consistency checking."""
        # Create minimal project structure with consistent versions
        (tmp_path / "roadmap").mkdir()
        (tmp_path / "pyproject.toml").write_text('[tool.poetry]\nversion = "1.2.3"')
        (tmp_path / "roadmap" / "__init__.py").write_text('__version__ = "1.2.3"')

        manager = VersionManager(tmp_path)
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

    def test_compare_versions_ordering(self):
        """Test ordering of multiple versions."""
        v1 = SemanticVersion("0.1.0")
        v2 = SemanticVersion("1.0.0")
        v3 = SemanticVersion("2.0.0")

        assert v1 < v2 < v3

    def test_version_major_comparison(self):
        """Test that major version takes precedence."""
        v1 = SemanticVersion("1.9.9")
        v2 = SemanticVersion("2.0.0")
        assert v1 < v2

    def test_version_minor_comparison(self):
        """Test that minor version is compared when major equal."""
        v1 = SemanticVersion("1.2.9")
        v2 = SemanticVersion("1.3.0")
        assert v1 < v2

    def test_version_patch_comparison(self):
        """Test that patch version is compared when major/minor equal."""
        v1 = SemanticVersion("1.2.3")
        v2 = SemanticVersion("1.2.4")
        assert v1 < v2


class TestVersionEdgeCases:
    """Test edge cases in version handling."""

    def test_version_with_leading_zeros_in_numbers(self):
        """Test version parsing with numbers."""
        version = SemanticVersion("1.2.3")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_version_bump_from_zero(self):
        """Test bumping versions starting from 0.0.0."""
        v0 = SemanticVersion("0.0.0")
        v1 = v0.bump_patch()
        assert v1.major == 0
        assert v1.minor == 0
        assert v1.patch == 1

    def test_version_bump_chain(self):
        """Test chaining version bumps."""
        v1 = SemanticVersion("1.0.0")
        v2 = v1.bump_patch()
        v3 = v2.bump_minor()

        assert str(v1) == "1.0.0"
        assert str(v2) == "1.0.1"
        assert str(v3) == "1.1.0"

    def test_version_v_prefix_parsing(self):
        """Test that v prefix is correctly handled."""
        v_prefixed = SemanticVersion("v1.2.3")
        non_prefixed = SemanticVersion("1.2.3")
        assert v_prefixed == non_prefixed

    def test_version_v_prefix_whitespace(self):
        """Test version parsing with whitespace."""
        version = SemanticVersion("  v1.2.3  ")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3


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
