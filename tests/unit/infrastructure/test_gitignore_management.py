"""Tests for .gitignore management during roadmap initialization."""

from pathlib import Path

from roadmap.core import RoadmapCore


class TestGitignoreManagement:
    """Test cases for .gitignore handling during roadmap initialization."""

    def test_gitignore_creation_with_new_file(self, temp_dir):
        """Test .gitignore creation when no .gitignore exists."""
        core = RoadmapCore()
        core.initialize()

        gitignore_path = Path(".gitignore")
        assert gitignore_path.exists()

        content = gitignore_path.read_text()

        # Check all roadmap patterns are present
        required_patterns = [
            ".roadmap/artifacts/",
            ".roadmap/backups/",
            ".roadmap/*.tmp",
            ".roadmap/*.lock",
        ]

        for pattern in required_patterns:
            assert pattern in content, f"Pattern {pattern} not found in .gitignore"

        # Check comment is present
        assert "Roadmap local data" in content

    def test_gitignore_update_existing_file(self, temp_dir):
        """Test .gitignore update when file already exists."""
        # Create existing .gitignore
        existing_content = """# Existing project .gitignore
*.pyc
__pycache__/
.env
node_modules/
"""
        Path(".gitignore").write_text(existing_content)

        core = RoadmapCore()
        core.initialize()

        gitignore_content = Path(".gitignore").read_text()

        # Check existing content is preserved
        assert "*.pyc" in gitignore_content
        assert "node_modules/" in gitignore_content

        # Check roadmap patterns were added
        required_patterns = [
            ".roadmap/artifacts/",
            ".roadmap/backups/",
            ".roadmap/*.tmp",
            ".roadmap/*.lock",
        ]

        for pattern in required_patterns:
            assert pattern in gitignore_content

    def test_gitignore_no_duplication(self, temp_dir):
        """Test that patterns are not duplicated when already present."""
        # Create .gitignore with some existing roadmap patterns
        existing_content = """# Project .gitignore
*.pyc

# Roadmap local data (generated exports, backups, temp files)
.roadmap/artifacts/
.roadmap/backups/

# Other stuff
node_modules/
"""
        Path(".gitignore").write_text(existing_content)

        core = RoadmapCore()
        core.initialize()

        gitignore_content = Path(".gitignore").read_text()
        lines = gitignore_content.splitlines()

        # Check no duplication
        pattern_counts = {}
        check_patterns = [
            ".roadmap/artifacts/",
            ".roadmap/backups/",
            ".roadmap/*.tmp",
            ".roadmap/*.lock",
        ]

        for pattern in check_patterns:
            count = sum(1 for line in lines if line.strip() == pattern)
            pattern_counts[pattern] = count

        # All patterns should appear exactly once
        for pattern, count in pattern_counts.items():
            assert count == 1, f"Pattern {pattern} appears {count} times (should be 1)"

    def test_gitignore_partial_patterns_existing(self, temp_dir):
        """Test adding missing patterns when some already exist."""
        # Create .gitignore with only some roadmap patterns
        existing_content = """# Project .gitignore
*.pyc
.roadmap/artifacts/
"""
        Path(".gitignore").write_text(existing_content)

        core = RoadmapCore()
        core.initialize()

        gitignore_content = Path(".gitignore").read_text()

        # Check all patterns are now present
        required_patterns = [
            ".roadmap/artifacts/",  # Was already there
            ".roadmap/backups/",  # Should be added
            ".roadmap/*.tmp",  # Should be added
            ".roadmap/*.lock",  # Should be added
        ]

        for pattern in required_patterns:
            assert pattern in gitignore_content

        # Check no duplication of existing pattern
        lines = gitignore_content.splitlines()
        artifacts_count = sum(
            1 for line in lines if line.strip() == ".roadmap/artifacts/"
        )
        assert (
            artifacts_count == 1
        ), "Existing .roadmap/artifacts/ pattern was duplicated"

    def test_gitignore_with_custom_roadmap_dir(self, temp_dir):
        """Test .gitignore patterns with custom roadmap directory name."""
        # Test with custom roadmap directory name
        core = RoadmapCore(roadmap_dir_name="custom_roadmap")
        core.initialize()

        gitignore_content = Path(".gitignore").read_text()

        # Check patterns use custom directory name
        expected_patterns = [
            "custom_roadmap/artifacts/",
            "custom_roadmap/backups/",
            "custom_roadmap/*.tmp",
            "custom_roadmap/*.lock",
        ]

        for pattern in expected_patterns:
            assert pattern in gitignore_content

    def test_gitignore_preserves_formatting(self, temp_dir):
        """Test that existing .gitignore formatting is preserved."""
        existing_content = """# Project .gitignore
*.pyc
*.pyo

# Build artifacts
dist/
build/

# IDE files
.vscode/
.idea/
"""
        Path(".gitignore").write_text(existing_content)

        core = RoadmapCore()
        core.initialize()

        gitignore_content = Path(".gitignore").read_text()

        # Check original content and formatting preserved
        assert "# Project .gitignore" in gitignore_content
        assert "# Build artifacts" in gitignore_content
        assert "# IDE files" in gitignore_content

        # Check roadmap patterns were appended correctly
        assert "# Roadmap local data" in gitignore_content

        # Verify structure: should have original content, then blank line, then roadmap content
        lines = gitignore_content.splitlines()
        roadmap_comment_index = next(
            i for i, line in enumerate(lines) if "Roadmap local data" in line
        )

        # Should have blank line before roadmap section
        assert lines[roadmap_comment_index - 1].strip() == ""
