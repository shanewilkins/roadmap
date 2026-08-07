"""Tests for temporary directory and workspace factory fixtures.

Validates that temp_file_factory, git_repo_factory, roadmap_structure_factory,
and isolated_workspace fixtures work correctly for test infrastructure.
"""

import pytest


def test_temp_file_factory_creates_toml(temp_file_factory):
    """Test that temp_file_factory.create_toml works."""
    config_file = temp_file_factory.create_toml(
        "test_config.toml", version="1.0.0", name="Test Project"
    )

    assert config_file.exists()
    assert config_file.name == "test_config.toml"
    content = config_file.read_text()
    assert "version" in content
    assert "1.0.0" in content


def test_git_repo_factory_creates_repo(git_repo_factory, tmp_path):
    """Test that git_repo_factory.create_repo works."""
    repo = git_repo_factory.create_repo()

    assert repo == tmp_path
    assert (tmp_path / ".git").exists()
    assert (tmp_path / "README.md").exists()


def test_roadmap_structure_factory_minimal(roadmap_structure_factory):
    """Test that roadmap_structure_factory.create_minimal works."""
    roadmap_dir = roadmap_structure_factory.create_minimal()

    assert roadmap_dir.exists()
    assert (roadmap_dir / "issues").exists()
    assert (roadmap_dir / "milestones").exists()


def test_roadmap_structure_factory_with_issues(roadmap_structure_factory):
    """Test that roadmap_structure_factory.create_full_with_issues works."""
    roadmap_dir = roadmap_structure_factory.create_full_with_issues(num_issues=3)

    issues_dir = roadmap_dir / "issues"
    assert issues_dir.exists()

    issue_files = list(issues_dir.glob("TEST-*.md"))
    assert len(issue_files) == 3


def test_isolated_workspace_context(isolated_workspace, tmp_path):
    """Test that isolated_workspace context manager works."""

    with isolated_workspace as workspace:
        assert workspace == tmp_path
        # We're inside the context manager, cwd should be changed
        # (This depends on whether pytest changed cwd, but the fixture handles it)
        (workspace / "test_file.txt").write_text("test")
        assert (workspace / "test_file.txt").exists()

    # After context, we should be able to verify the file existed
    assert (tmp_path / "test_file.txt").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
