"""Unit tests for version management module."""

import pytest

from roadmap.version import SemanticVersion, VersionManager


class TestSemanticVersion:
    """Test SemanticVersion class."""

    def test_parse_basic_version(self):
        """Test parsing a basic semantic version."""
        version = SemanticVersion("1.2.3")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_parse_version_with_v_prefix(self):
        """Test parsing version with 'v' prefix."""
        version = SemanticVersion("v1.2.3")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert str(version) == "1.2.3"

    def test_parse_version_with_spaces(self):
        """Test parsing version with surrounding spaces."""
        version = SemanticVersion("  1.2.3  ")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_invalid_version_format_missing_patch(self):
        """Test that version without patch raises error."""
        with pytest.raises(ValueError, match="Invalid semantic version format"):
            SemanticVersion("1.2")

    def test_invalid_version_format_too_many_parts(self):
        """Test that version with too many parts raises error."""
        with pytest.raises(ValueError, match="Invalid semantic version format"):
            SemanticVersion("1.2.3.4")

    def test_invalid_version_format_non_numeric(self):
        """Test that non-numeric version raises error."""
        with pytest.raises(ValueError, match="Invalid semantic version format"):
            SemanticVersion("a.b.c")

    def test_is_valid_semantic_version(self):
        """Test static validation method."""
        assert SemanticVersion.is_valid_semantic_version("1.2.3")
        assert SemanticVersion.is_valid_semantic_version("0.0.0")
        assert SemanticVersion.is_valid_semantic_version("10.20.30")
        assert not SemanticVersion.is_valid_semantic_version("1.2")
        assert not SemanticVersion.is_valid_semantic_version("1.2.3.4")
        assert not SemanticVersion.is_valid_semantic_version("v1.2.3")

    def test_bump_major(self):
        """Test major version bump."""
        version = SemanticVersion("1.2.3")
        bumped = version.bump_major()
        assert bumped.major == 2
        assert bumped.minor == 0
        assert bumped.patch == 0

    def test_bump_minor(self):
        """Test minor version bump."""
        version = SemanticVersion("1.2.3")
        bumped = version.bump_minor()
        assert bumped.major == 1
        assert bumped.minor == 3
        assert bumped.patch == 0

    def test_bump_patch(self):
        """Test patch version bump."""
        version = SemanticVersion("1.2.3")
        bumped = version.bump_patch()
        assert bumped.major == 1
        assert bumped.minor == 2
        assert bumped.patch == 4

    def test_str_representation(self):
        """Test string representation."""
        version = SemanticVersion("1.2.3")
        assert str(version) == "1.2.3"

    def test_repr_representation(self):
        """Test repr representation."""
        version = SemanticVersion("1.2.3")
        assert repr(version) == "SemanticVersion('1.2.3')"

    def test_equality(self):
        """Test equality comparison."""
        v1 = SemanticVersion("1.2.3")
        v2 = SemanticVersion("1.2.3")
        v3 = SemanticVersion("1.2.4")
        assert v1 == v2
        assert not (v1 == v3)
        assert not (v1 == "1.2.3")

    def test_less_than(self):
        """Test less than comparison."""
        v1 = SemanticVersion("1.2.3")
        v2 = SemanticVersion("1.2.4")
        v3 = SemanticVersion("1.3.0")
        v4 = SemanticVersion("2.0.0")
        assert v1 < v2
        assert v1 < v3
        assert v1 < v4
        assert not (v2 < v1)

    def test_less_than_or_equal(self):
        """Test less than or equal comparison."""
        v1 = SemanticVersion("1.2.3")
        v2 = SemanticVersion("1.2.3")
        v3 = SemanticVersion("1.2.4")
        assert v1 <= v2
        assert v1 <= v3
        assert not (v3 <= v1)

    def test_greater_than(self):
        """Test greater than comparison."""
        v1 = SemanticVersion("1.2.4")
        v2 = SemanticVersion("1.2.3")
        assert v1 > v2
        assert not (v2 > v1)

    def test_greater_than_or_equal(self):
        """Test greater than or equal comparison."""
        v1 = SemanticVersion("1.2.3")
        v2 = SemanticVersion("1.2.3")
        v3 = SemanticVersion("1.2.2")
        assert v1 >= v2
        assert v1 >= v3
        assert not (v3 >= v1)

    def test_comparison_with_invalid_type(self):
        """Test comparison with invalid type."""
        v1 = SemanticVersion("1.2.3")
        result = v1.__lt__("1.2.4")
        assert result is NotImplemented


class TestVersionManager:
    """Test VersionManager class."""

    def test_init(self, tmp_path):
        """Test VersionManager initialization."""
        manager = VersionManager(tmp_path)
        assert manager.project_root == tmp_path
        assert manager.pyproject_path == tmp_path / "pyproject.toml"

    def test_get_current_version_not_found(self, tmp_path):
        """Test getting version when file doesn't exist."""
        manager = VersionManager(tmp_path)
        version = manager.get_current_version()
        assert version is None

    def test_get_current_version_from_pyproject(self, tmp_path):
        """Test getting version from pyproject.toml."""
        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text('[tool.poetry]\nversion = "1.2.3"\n')

        manager = VersionManager(tmp_path)
        version = manager.get_current_version()
        assert version is not None
        assert str(version) == "1.2.3"

    def test_get_init_version_not_found(self, tmp_path):
        """Test getting version from __init__.py when not found."""
        init_dir = tmp_path / "roadmap"
        init_dir.mkdir()
        init_path = init_dir / "__init__.py"
        init_path.write_text("# No version here\n")

        manager = VersionManager(tmp_path)
        version = manager.get_init_version()
        assert version is None

    def test_get_init_version_from_file(self, tmp_path):
        """Test getting version from __init__.py."""
        init_dir = tmp_path / "roadmap"
        init_dir.mkdir()
        init_path = init_dir / "__init__.py"
        init_path.write_text('__version__ = "1.2.3"\n')

        manager = VersionManager(tmp_path)
        version = manager.get_init_version()
        assert version is not None
        assert str(version) == "1.2.3"

    def test_check_version_consistency_both_present(self, tmp_path):
        """Test version consistency check when both files present and match."""
        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text('[tool.poetry]\nversion = "1.2.3"\n')

        init_dir = tmp_path / "roadmap"
        init_dir.mkdir()
        init_path = init_dir / "__init__.py"
        init_path.write_text('__version__ = "1.2.3"\n')

        manager = VersionManager(tmp_path)
        result = manager.check_version_consistency()
        assert result["consistent"]
        assert result["pyproject_version"] == "1.2.3"
        assert result["init_version"] == "1.2.3"

    def test_check_version_consistency_missing_pyproject(self, tmp_path):
        """Test version consistency check when pyproject missing."""
        manager = VersionManager(tmp_path)
        result = manager.check_version_consistency()
        assert not result["consistent"]
        assert "No version found in pyproject.toml" in result["issues"]

    def test_check_version_consistency_mismatch(self, tmp_path):
        """Test version consistency check when versions don't match."""
        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text('[tool.poetry]\nversion = "1.2.3"\n')

        init_dir = tmp_path / "roadmap"
        init_dir.mkdir()
        init_path = init_dir / "__init__.py"
        init_path.write_text('__version__ = "1.2.4"\n')

        manager = VersionManager(tmp_path)
        result = manager.check_version_consistency()
        assert not result["consistent"]
        assert "version mismatch" in " ".join(result["issues"]).lower()
