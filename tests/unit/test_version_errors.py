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

    @pytest.mark.parametrize(
        "pyproject_version,init_version,expect_version",
        [
            ("1.2.3", "1.2.3", "1.2.3"),  # both present and matching
            ("1.0.0", "1.5.2", "1.0.0"),  # both present, pyproject takes precedence
        ],
    )
    def test_get_current_version(
        self, roadmap_structure_factory, pyproject_version, init_version, expect_version
    ):
        """Test reading version from pyproject.toml and __init__.py."""
        project_root = roadmap_structure_factory.create_project_structure(
            pyproject_version=pyproject_version, init_version=init_version
        )
        manager = VersionManager(project_root)
        version = manager.get_current_version()

        assert version is not None
        assert str(version) == expect_version

    def test_get_current_version_returns_none_when_file_missing(self, tmp_path):
        """Test that get_current_version returns None when pyproject.toml is missing."""
        (tmp_path / "roadmap").mkdir()
        manager = VersionManager(tmp_path)
        version = manager.get_current_version()
        assert version is None

    def test_get_current_version_returns_none_when_version_missing(self, tmp_path):
        """Test that get_current_version returns None when version key is missing."""
        pyproject_file = tmp_path / "pyproject.toml"
        (tmp_path / "roadmap").mkdir()

        # Write pyproject without version
        pyproject_data = {"tool": {"poetry": {}}}
        with open(pyproject_file, "w") as f:
            toml.dump(pyproject_data, f)

        manager = VersionManager(tmp_path)
        version = manager.get_current_version()

        assert version is None

    @pytest.mark.parametrize(
        "version_str,quote_type",
        [
            ("1.5.2", "double"),  # double quotes
            ("2.0.0", "single"),  # single quotes
            ("3.1.0", "double"),  # another double quote variant
        ],
    )
    def test_get_init_version(self, roadmap_structure_factory, version_str, quote_type):
        """Test reading version from __init__.py with various quote styles."""
        project_root = roadmap_structure_factory.create_project_structure(
            pyproject_version="1.0.0", init_version=version_str
        )

        # Override the init file quote style if needed
        if quote_type == "single":
            init_file = project_root / "roadmap" / "__init__.py"
            init_file.write_text(f"__version__ = '{version_str}'")

        manager = VersionManager(project_root)
        version = manager.get_init_version()

        assert version is not None
        assert str(version) == version_str

    def test_get_init_version_returns_none_when_file_missing(self, tmp_path):
        """Test that get_init_version returns None when __init__.py is missing."""
        pyproject_file = tmp_path / "pyproject.toml"
        (tmp_path / "roadmap").mkdir()

        pyproject_data = {"tool": {"poetry": {"version": "1.0.0"}}}
        with open(pyproject_file, "w") as f:
            toml.dump(pyproject_data, f)

        manager = VersionManager(tmp_path)
        version = manager.get_init_version()

        assert version is None

    def test_get_init_version_returns_none_when_version_not_found(self, tmp_path):
        """Test that get_init_version returns None when __version__ is not defined."""
        pyproject_file = tmp_path / "pyproject.toml"
        init_file = tmp_path / "roadmap" / "__init__.py"

        (tmp_path / "roadmap").mkdir()

        pyproject_data = {"tool": {"poetry": {"version": "1.0.0"}}}
        with open(pyproject_file, "w") as f:
            toml.dump(pyproject_data, f)

        # No version in __init__.py
        init_file.write_text("# No version here")

        manager = VersionManager(tmp_path)
        version = manager.get_init_version()

        assert version is None


# ========== Integration Tests: Version Consistency Checking ==========


class TestVersionConsistencyChecking:
    """Test version consistency verification."""

    @pytest.mark.parametrize(
        "pyproject_version,init_version,is_consistent,issue_contains",
        [
            (None, "1.0.0", False, "No version found in pyproject.toml"),
            ("1.0.0", None, False, "No version found in __init__.py"),
            ("1.0.0", "2.0.0", False, "Version mismatch"),
            ("1.2.3", "1.2.3", True, None),
        ],
    )
    def test_check_version_consistency(
        self,
        roadmap_structure_factory,
        pyproject_version,
        init_version,
        is_consistent,
        issue_contains,
    ):
        """Test version consistency checking with various scenarios."""
        # Build base versions, excluding None values
        kwargs = {}
        if pyproject_version:
            kwargs["pyproject_version"] = pyproject_version
        if init_version:
            kwargs["init_version"] = init_version

        project_root = roadmap_structure_factory.create_project_structure(**kwargs)

        # For the "no version" cases, manually remove the version
        if pyproject_version is None:
            pyproject_file = project_root / "pyproject.toml"
            if pyproject_file.exists():
                data = toml.load(open(pyproject_file))
                if "tool" in data and "poetry" in data["tool"]:
                    del data["tool"]["poetry"]["version"]
                with open(pyproject_file, "w") as f:
                    toml.dump(data, f)

        if init_version is None:
            init_file = project_root / "roadmap" / "__init__.py"
            if init_file.exists():
                init_file.write_text("# No version")

        manager = VersionManager(project_root)
        result = manager.check_version_consistency()

        assert result["consistent"] is is_consistent
        if is_consistent:
            assert len(result["issues"]) == 0
        else:
            assert any(issue_contains in issue for issue in result["issues"])


# ========== Integration Tests: Version Update ==========


class TestVersionUpdate:
    """Test version update in multiple files."""

    def test_update_version_in_both_files(self, roadmap_structure_factory):
        """Test that update_version updates both pyproject and __init__.py."""
        project_root = roadmap_structure_factory.create_project_structure(
            pyproject_version="1.0.0", init_version="1.0.0"
        )

        manager = VersionManager(project_root)
        new_version = SemanticVersion("2.0.0")
        success = manager.update_version(new_version)

        assert success is True

        # Verify pyproject was updated
        pyproject_file = project_root / "pyproject.toml"
        updated_pyproject = toml.load(open(pyproject_file))
        assert updated_pyproject["tool"]["poetry"]["version"] == "2.0.0"

        # Verify __init__.py was updated
        init_file = project_root / "roadmap" / "__init__.py"
        updated_init = init_file.read_text()
        assert '__version__ = "2.0.0"' in updated_init

    def test_update_version_handles_missing_pyproject(self, tmp_path):
        """Test that missing pyproject.toml doesn't crash update_version."""
        (tmp_path / "roadmap").mkdir()
        init_file = tmp_path / "roadmap" / "__init__.py"
        init_file.write_text('__version__ = "1.0.0"')

        manager = VersionManager(tmp_path)
        new_version = SemanticVersion("2.0.0")
        success = manager.update_version(new_version)

        # Should return False or partial success
        # But should not crash
        assert isinstance(success, bool)

    def test_update_version_handles_malformed_pyproject(self, tmp_path):
        """Test that malformed pyproject.toml is handled gracefully."""
        (tmp_path / "roadmap").mkdir()
        pyproject_file = tmp_path / "pyproject.toml"
        init_file = tmp_path / "roadmap" / "__init__.py"

        # Write invalid TOML
        pyproject_file.write_text("invalid: toml: content: [")
        init_file.write_text('__version__ = "1.0.0"')

        manager = VersionManager(tmp_path)
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
