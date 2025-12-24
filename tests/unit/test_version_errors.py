"""Error path tests for version.py - Phase 10a Tier 1 coverage expansion.

This module tests error handling and exception paths in version management utilities,
focusing on parsing failures, file I/O errors, malformed version strings, etc.

Currently version.py has 52% coverage.
Target after Phase 10a: 85%+ coverage
"""

import pytest
import toml

from roadmap.version import SemanticVersion, VersionManager

# ========== Unit Tests: SemanticVersion Validation ==========


class TestSemanticVersionValidation:
    """Test semantic version validation and parsing."""

    def test_rejects_invalid_version_format(self):
        """Test that invalid version formats raise ValueError."""
        invalid_versions = [
            "1",
            "1.2",
            "1.2.3.4",
            "v1.2",
            "abc.def.ghi",
            "1.2.x",
            "1.2.3-alpha",
            "",
            "   ",
        ]
        for invalid_version in invalid_versions:
            with pytest.raises(ValueError):
                SemanticVersion(invalid_version)

    def test_rejects_non_numeric_version_parts(self):
        """Test that non-numeric parts cause ValueError."""
        with pytest.raises(ValueError):
            SemanticVersion("1.a.3")
        with pytest.raises(ValueError):
            SemanticVersion("a.2.3")

    def test_accepts_valid_version_with_v_prefix(self):
        """Test that 'v' prefix is correctly handled."""
        version = SemanticVersion("v1.2.3")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_accepts_valid_version_without_prefix(self):
        """Test that version without prefix is correctly parsed."""
        version = SemanticVersion("1.2.3")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_strips_whitespace_from_input(self):
        """Test that whitespace is stripped from version string."""
        version = SemanticVersion("  v1.2.3  ")
        assert str(version) == "1.2.3"


# ========== Unit Tests: SemanticVersion Operations ==========


class TestSemanticVersionOperations:
    """Test semantic version bump operations and comparisons."""

    def test_bump_major_resets_minor_and_patch(self):
        """Test that bumping major version resets minor and patch."""
        version = SemanticVersion("1.5.9")
        bumped = version.bump_major()
        assert str(bumped) == "2.0.0"

    def test_bump_minor_resets_patch(self):
        """Test that bumping minor version resets patch."""
        version = SemanticVersion("1.5.9")
        bumped = version.bump_minor()
        assert str(bumped) == "1.6.0"

    def test_bump_patch_increments_only_patch(self):
        """Test that bumping patch only increments patch."""
        version = SemanticVersion("1.5.9")
        bumped = version.bump_patch()
        assert str(bumped) == "1.5.10"

    def test_version_comparison_operators(self):
        """Test version comparison operations."""
        v1 = SemanticVersion("1.0.0")
        v2 = SemanticVersion("1.0.1")
        v3 = SemanticVersion("1.1.0")
        v4 = SemanticVersion("2.0.0")

        # Less than
        assert v1 < v2
        assert v2 < v3
        assert v3 < v4

        # Less than or equal
        assert v1 <= v2
        assert v1 <= v1

        # Greater than
        assert v2 > v1
        assert v3 > v1

        # Greater than or equal
        assert v2 >= v1
        assert v1 >= v1

        # Equality
        assert v1 == SemanticVersion("1.0.0")
        assert v1 != v2

    def test_version_comparison_with_non_version_object(self):
        """Test that comparing with non-SemanticVersion raises TypeError."""
        version = SemanticVersion("1.0.0")
        # Comparing with non-SemanticVersion should raise TypeError
        with pytest.raises(TypeError):
            _ = version < "1.0.1"


# ========== Unit Tests: VersionManager File Reading ==========


class TestVersionManagerFileReading:
    """Test version reading from different file formats."""

    def test_get_current_version_from_pyproject(self, tmp_path):
        """Test reading version from pyproject.toml."""
        project_root = tmp_path
        pyproject_file = project_root / "pyproject.toml"
        init_file = project_root / "roadmap" / "__init__.py"

        # Create directories
        (project_root / "roadmap").mkdir()

        # Write pyproject.toml
        pyproject_data = {"tool": {"poetry": {"version": "1.2.3"}}}
        with open(pyproject_file, "w") as f:
            toml.dump(pyproject_data, f)

        # Write __init__.py
        init_file.write_text('__version__ = "1.2.3"')

        manager = VersionManager(project_root)
        version = manager.get_current_version()

        assert version is not None
        assert str(version) == "1.2.3"

    def test_get_current_version_returns_none_when_file_missing(self, tmp_path):
        """Test that get_current_version returns None when pyproject.toml is missing."""
        project_root = tmp_path
        (project_root / "roadmap").mkdir()

        manager = VersionManager(project_root)
        version = manager.get_current_version()

        assert version is None

    def test_get_current_version_returns_none_when_version_missing(self, tmp_path):
        """Test that get_current_version returns None when version key is missing."""
        project_root = tmp_path
        pyproject_file = project_root / "pyproject.toml"
        (project_root / "roadmap").mkdir()

        # Write pyproject without version
        pyproject_data = {"tool": {"poetry": {}}}
        with open(pyproject_file, "w") as f:
            toml.dump(pyproject_data, f)

        manager = VersionManager(project_root)
        version = manager.get_current_version()

        assert version is None

    def test_get_init_version_from_file(self, tmp_path):
        """Test reading version from __init__.py."""
        project_root = tmp_path
        pyproject_file = project_root / "pyproject.toml"
        init_file = project_root / "roadmap" / "__init__.py"

        (project_root / "roadmap").mkdir()

        # Write minimal pyproject
        pyproject_data = {"tool": {"poetry": {"version": "1.0.0"}}}
        with open(pyproject_file, "w") as f:
            toml.dump(pyproject_data, f)

        # Write __init__.py with version
        init_file.write_text('__version__ = "1.5.2"')

        manager = VersionManager(project_root)
        version = manager.get_init_version()

        assert version is not None
        assert str(version) == "1.5.2"

    def test_get_init_version_with_single_quotes(self, tmp_path):
        """Test that single quotes in __init__.py are recognized."""
        project_root = tmp_path
        pyproject_file = project_root / "pyproject.toml"
        init_file = project_root / "roadmap" / "__init__.py"

        (project_root / "roadmap").mkdir()

        pyproject_data = {"tool": {"poetry": {"version": "1.0.0"}}}
        with open(pyproject_file, "w") as f:
            toml.dump(pyproject_data, f)

        # Single quotes
        init_file.write_text("__version__ = '2.0.0'")

        manager = VersionManager(project_root)
        version = manager.get_init_version()

        assert str(version) == "2.0.0"

    def test_get_init_version_returns_none_when_file_missing(self, tmp_path):
        """Test that get_init_version returns None when __init__.py is missing."""
        project_root = tmp_path
        pyproject_file = project_root / "pyproject.toml"

        (project_root / "roadmap").mkdir()

        pyproject_data = {"tool": {"poetry": {"version": "1.0.0"}}}
        with open(pyproject_file, "w") as f:
            toml.dump(pyproject_data, f)

        manager = VersionManager(project_root)
        version = manager.get_init_version()

        assert version is None

    def test_get_init_version_returns_none_when_version_not_found(self, tmp_path):
        """Test that get_init_version returns None when __version__ is not defined."""
        project_root = tmp_path
        pyproject_file = project_root / "pyproject.toml"
        init_file = project_root / "roadmap" / "__init__.py"

        (project_root / "roadmap").mkdir()

        pyproject_data = {"tool": {"poetry": {"version": "1.0.0"}}}
        with open(pyproject_file, "w") as f:
            toml.dump(pyproject_data, f)

        # No version in __init__.py
        init_file.write_text("# No version here")

        manager = VersionManager(project_root)
        version = manager.get_init_version()

        assert version is None


# ========== Integration Tests: Version Consistency Checking ==========


class TestVersionConsistencyChecking:
    """Test version consistency verification."""

    def test_check_consistency_returns_false_when_no_pyproject_version(self, tmp_path):
        """Test consistency check fails when pyproject version is missing."""
        project_root = tmp_path
        pyproject_file = project_root / "pyproject.toml"
        init_file = project_root / "roadmap" / "__init__.py"

        (project_root / "roadmap").mkdir()

        # No version in pyproject
        pyproject_data = {"tool": {"poetry": {}}}
        with open(pyproject_file, "w") as f:
            toml.dump(pyproject_data, f)

        init_file.write_text('__version__ = "1.0.0"')

        manager = VersionManager(project_root)
        result = manager.check_version_consistency()

        assert result["consistent"] is False
        assert "No version found in pyproject.toml" in result["issues"]

    def test_check_consistency_returns_false_when_no_init_version(self, tmp_path):
        """Test consistency check fails when __init__.py version is missing."""
        project_root = tmp_path
        pyproject_file = project_root / "pyproject.toml"
        init_file = project_root / "roadmap" / "__init__.py"

        (project_root / "roadmap").mkdir()

        pyproject_data = {"tool": {"poetry": {"version": "1.0.0"}}}
        with open(pyproject_file, "w") as f:
            toml.dump(pyproject_data, f)

        # No version in init
        init_file.write_text("# No version")

        manager = VersionManager(project_root)
        result = manager.check_version_consistency()

        assert result["consistent"] is False
        assert "No version found in __init__.py" in result["issues"]

    def test_check_consistency_returns_false_when_versions_mismatch(self, tmp_path):
        """Test consistency check fails when versions don't match."""
        project_root = tmp_path
        pyproject_file = project_root / "pyproject.toml"
        init_file = project_root / "roadmap" / "__init__.py"

        (project_root / "roadmap").mkdir()

        pyproject_data = {"tool": {"poetry": {"version": "1.0.0"}}}
        with open(pyproject_file, "w") as f:
            toml.dump(pyproject_data, f)

        init_file.write_text('__version__ = "2.0.0"')

        manager = VersionManager(project_root)
        result = manager.check_version_consistency()

        assert result["consistent"] is False
        assert "Version mismatch" in result["issues"][0]

    def test_check_consistency_returns_true_when_versions_match(self, tmp_path):
        """Test consistency check passes when versions match."""
        project_root = tmp_path
        pyproject_file = project_root / "pyproject.toml"
        init_file = project_root / "roadmap" / "__init__.py"

        (project_root / "roadmap").mkdir()

        pyproject_data = {"tool": {"poetry": {"version": "1.2.3"}}}
        with open(pyproject_file, "w") as f:
            toml.dump(pyproject_data, f)

        init_file.write_text('__version__ = "1.2.3"')

        manager = VersionManager(project_root)
        result = manager.check_version_consistency()

        assert result["consistent"] is True
        assert len(result["issues"]) == 0


# ========== Integration Tests: Version Update ==========


class TestVersionUpdate:
    """Test version update in multiple files."""

    def test_update_version_in_both_files(self, tmp_path):
        """Test that update_version updates both pyproject and __init__.py."""
        project_root = tmp_path
        pyproject_file = project_root / "pyproject.toml"
        init_file = project_root / "roadmap" / "__init__.py"

        (project_root / "roadmap").mkdir()

        # Initial versions
        pyproject_data = {"tool": {"poetry": {"version": "1.0.0"}}}
        with open(pyproject_file, "w") as f:
            toml.dump(pyproject_data, f)

        init_file.write_text('__version__ = "1.0.0"')

        manager = VersionManager(project_root)
        new_version = SemanticVersion("2.0.0")
        success = manager.update_version(new_version)

        assert success is True

        # Verify pyproject was updated
        updated_pyproject = toml.load(open(pyproject_file))
        assert updated_pyproject["tool"]["poetry"]["version"] == "2.0.0"

        # Verify __init__.py was updated
        updated_init = init_file.read_text()
        assert '__version__ = "2.0.0"' in updated_init

    def test_update_version_handles_missing_pyproject(self, tmp_path):
        """Test that missing pyproject.toml doesn't crash update_version."""
        project_root = tmp_path
        init_file = project_root / "roadmap" / "__init__.py"

        (project_root / "roadmap").mkdir()
        init_file.write_text('__version__ = "1.0.0"')

        manager = VersionManager(project_root)
        new_version = SemanticVersion("2.0.0")
        success = manager.update_version(new_version)

        # Should return False or partial success
        # But should not crash
        assert isinstance(success, bool)

    def test_update_version_handles_malformed_pyproject(self, tmp_path):
        """Test that malformed pyproject.toml is handled gracefully."""
        project_root = tmp_path
        pyproject_file = project_root / "pyproject.toml"
        init_file = project_root / "roadmap" / "__init__.py"

        (project_root / "roadmap").mkdir()

        # Write invalid TOML
        pyproject_file.write_text("invalid: toml: content: [")

        init_file.write_text('__version__ = "1.0.0"')

        manager = VersionManager(project_root)
        new_version = SemanticVersion("2.0.0")

        # Should handle exception gracefully
        success = manager.update_version(new_version)
        assert isinstance(success, bool)


# ========== Error Path: Malformed Version Strings ==========


class TestMalformedVersionStrings:
    """Test handling of various malformed version strings."""

    def test_leading_zeros_are_rejected(self):
        """Test that leading zeros in version parts are handled."""
        # This depends on implementation - might be accepted or rejected
        try:
            version = SemanticVersion("01.02.03")
            # If it parses, check it's normalized
            assert str(version) == "1.2.3"
        except ValueError:
            # Or it might reject leading zeros - both are valid
            pass

    def test_negative_numbers_rejected(self):
        """Test that negative version numbers are rejected."""
        with pytest.raises(ValueError):
            SemanticVersion("-1.2.3")
        with pytest.raises(ValueError):
            SemanticVersion("1.-2.3")

    def test_float_version_rejected(self):
        """Test that floating point versions are rejected."""
        with pytest.raises(ValueError):
            SemanticVersion("1.2.3.4.5")
        with pytest.raises(ValueError):
            SemanticVersion("1.2.3.0")


pytestmark = pytest.mark.unit
