"""Temporary directory factories for reducing hardcoded tmp_path usage.

This module provides factory fixtures for common temporary directory patterns:
- File operations (TOML, YAML, text files)
- Git repository initialization
- Roadmap directory structure creation
- Isolated workspaces with cleanup

Benefits:
- Centralizes tmp_path setup logic
- Makes tests more readable
- Easier to change temp directory handling in one place
- Reduces 585+ hardcoded tmp_path occurrences
"""

import os
import subprocess
from pathlib import Path
from typing import Any

import pytest
import toml


@pytest.fixture
def temp_file_factory(tmp_path):
    """Factory for creating temporary files with content.

    Reduces file_operations pattern from 37 test files.

    Usage:
        def test_something(temp_file_factory):
            config_file = temp_file_factory.create_toml("config.toml", version="1.0.0")

            text_file = temp_file_factory.create_file("README.md", "# Header")
    """

    class TempFileFactory:
        """Factory for creating temporary files."""

        @staticmethod
        def create_toml(filename: str = "pyproject.toml", **content) -> Path:
            """Create a temporary TOML file.

            Args:
                filename: Name of the TOML file
                **content: Key-value pairs to write as TOML

            Returns:
                Path to the created file
            """
            import toml

            filepath = tmp_path / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "w") as f:
                toml.dump(content, f)
            return filepath

        @staticmethod
        def create_yaml(filename: str = "config.yaml", **content) -> Path:
            """Create a temporary YAML file.

            Args:
                filename: Name of the YAML file
                **content: Key-value pairs to write as YAML

            Returns:
                Path to the created file
            """
            import yaml

            filepath = tmp_path / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "w") as f:
                yaml.dump(content, f)
            return filepath

        @staticmethod
        def create_file(filename: str, content: str = "") -> Path:
            """Create a temporary file with content.

            Args:
                filename: Name of the file (can include subdirectories)
                content: Text content to write

            Returns:
                Path to the created file
            """
            filepath = tmp_path / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content)
            return filepath

        @staticmethod
        def create_python_module(module_name: str, content: str) -> Path:
            """Create a Python module file.

            Args:
                module_name: Module name (e.g., "__init__.py", "helpers.py")
                content: Python code content

            Returns:
                Path to the created file
            """
            return TempFileFactory.create_file(module_name, content)

    return TempFileFactory()


@pytest.fixture
def git_repo_factory(tmp_path):
    """Factory for initializing git repositories.

    Reduces git_repo pattern from 3 test files.

    Usage:
        def test_git_operation(git_repo_factory):
            repo = git_repo_factory.create_repo()
            # Now tmp_path has a working git repository

            repo = git_repo_factory.create_with_branch("feature/test")
    """

    class GitRepoFactory:
        """Factory for initializing git repositories."""

        @staticmethod
        def create_repo(
            initial_commit: bool = True,
            branch_name: str = "main",
            user_name: str = "Test User",
            user_email: str = "test@example.com",
        ) -> Path:
            """Initialize a git repository with optional initial commit.

            Args:
                initial_commit: Whether to create an initial commit
                branch_name: Name of the initial branch
                user_name: Git user name
                user_email: Git user email

            Returns:
                Path to the repository root (tmp_path)
            """
            subprocess.run(
                ["git", "init", "-b", branch_name],
                cwd=tmp_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.name", user_name],
                cwd=tmp_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", user_email],
                cwd=tmp_path,
                check=True,
                capture_output=True,
            )

            if initial_commit:
                (tmp_path / "README.md").write_text("# Test Repository")
                subprocess.run(
                    ["git", "add", "README.md"],
                    cwd=tmp_path,
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    ["git", "commit", "-m", "Initial commit"],
                    cwd=tmp_path,
                    check=True,
                    capture_output=True,
                )

            return tmp_path

        @staticmethod
        def create_with_branch(branch_name: str = "feature/test") -> Path:
            """Create repo with additional branch.

            Args:
                branch_name: Name of the feature branch

            Returns:
                Path to the repository root
            """
            repo = GitRepoFactory.create_repo()
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=tmp_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "checkout", "main"],
                cwd=tmp_path,
                check=True,
                capture_output=True,
            )
            return repo

        @staticmethod
        def create_with_file(filename: str, content: str = "") -> Path:
            """Create repo with initial file.

            Args:
                filename: Name of the file to add
                content: Content to write

            Returns:
                Path to the repository root
            """
            repo = GitRepoFactory.create_repo(initial_commit=False)
            (tmp_path / filename).write_text(content)
            subprocess.run(
                ["git", "add", filename],
                cwd=tmp_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", f"Add {filename}"],
                cwd=tmp_path,
                check=True,
                capture_output=True,
            )
            return repo

    return GitRepoFactory()


@pytest.fixture
def roadmap_structure_factory(tmp_path):
    """Factory for creating .roadmap directory structures.

    Reduces roadmap_structure pattern from 62 test files.

    Usage:
        def test_roadmap_ops(roadmap_structure_factory):
            roadmap_dir = roadmap_structure_factory.create_minimal()
            # Now tmp_path/.roadmap exists with issues/ and milestones/

            roadmap_dir = roadmap_structure_factory.create_full_with_issues(5)
    """

    class RoadmapStructureFactory:
        """Factory for creating .roadmap directory structures."""

        @staticmethod
        def create_minimal() -> Path:
            """Create minimal .roadmap structure.

            Creates:
                .roadmap/
                  issues/
                  milestones/

            Returns:
                Path to the .roadmap directory
            """
            roadmap_dir = tmp_path / ".roadmap"
            roadmap_dir.mkdir(exist_ok=True)
            (roadmap_dir / "issues").mkdir(exist_ok=True)
            (roadmap_dir / "milestones").mkdir(exist_ok=True)
            return roadmap_dir

        @staticmethod
        def create_with_config(**config_values) -> Path:
            """Create .roadmap structure with config file.

            Args:
                **config_values: Config properties to set

            Returns:
                Path to the .roadmap directory
            """
            import yaml

            roadmap_dir = RoadmapStructureFactory.create_minimal()

            config: dict[str, Any] = {
                "version": "1.0.0",
                "project_name": "Test Project",
            }
            config.update(config_values)

            config_file = roadmap_dir / "config.yaml"
            with open(config_file, "w") as f:
                yaml.dump(config, f)

            return roadmap_dir

        @staticmethod
        def create_full_with_issues(
            num_issues: int = 3, issues_per_milestone: int = 0
        ) -> Path:
            """Create .roadmap with issues populated.

            Args:
                num_issues: Number of issues to create
                issues_per_milestone: If > 0, create milestones with issues

            Returns:
                Path to the .roadmap directory
            """
            roadmap_dir = RoadmapStructureFactory.create_with_config()

            issues_dir = roadmap_dir / "issues"
            for i in range(num_issues):
                issue_file = issues_dir / f"TEST-{i:03d}.md"
                issue_file.write_text(
                    f"---\nid: TEST-{i:03d}\ntitle: Test Issue {i}\nstatus: open\n---\n\n# Issue TEST-{i:03d}\n\nTest issue content."
                )

            if issues_per_milestone > 0:
                milestones_dir = roadmap_dir / "milestones"
                for m in range(
                    (num_issues + issues_per_milestone - 1) // issues_per_milestone
                ):
                    milestone_dir = milestones_dir / f"milestone-{m+1}"
                    milestone_dir.mkdir(parents=True, exist_ok=True)
                    (milestone_dir / ".milestone.md").write_text(
                        f"---\nname: Milestone {m+1}\n---\n\n# Milestone {m+1}\n"
                    )

            return roadmap_dir

        @staticmethod
        def create_project_structure(
            pyproject_version: str | None = "1.0.0",
            init_version: str | None = "1.0.0",
        ) -> Path:
            """Create a full project structure with pyproject.toml and __init__.py.

            This is useful for version management tests.

            Args:
                pyproject_version: Version to write in pyproject.toml (None to skip)
                init_version: Version to write in roadmap/__init__.py (None to skip)

            Returns:
                Path to the project root (tmp_path)
            """
            # Create roadmap package directory
            (tmp_path / "roadmap").mkdir(exist_ok=True)

            # Create pyproject.toml if version specified
            if pyproject_version:
                pyproject_file = tmp_path / "pyproject.toml"
                pyproject_data = {"tool": {"poetry": {"version": pyproject_version}}}
                with open(pyproject_file, "w") as f:
                    toml.dump(pyproject_data, f)

            # Create __init__.py if version specified
            if init_version:
                init_file = tmp_path / "roadmap" / "__init__.py"
                init_file.write_text(f'__version__ = "{init_version}"')

            return tmp_path

    return RoadmapStructureFactory()


@pytest.fixture
def isolated_workspace(tmp_path):
    """Fixture that provides isolated workspace with directory restoration.

    Reduces isolation pattern from 28 test files.

    Usage:
        def test_isolated_work(isolated_workspace):
            with isolated_workspace as workspace:
                # Now cwd is workspace root
                # Automatic restoration on exit
                pass

            # Or use directly:
            isolated_workspace.change_to("subdir")
    """

    class IsolatedWorkspace:
        """Context manager for isolated workspace."""

        def __init__(self, root: Path):
            """Initialize workspace.

            Args:
                root: Root path of the workspace
            """
            self.root = root
            self.original_cwd: str | None = None

        def __enter__(self) -> Path:
            """Enter context: change to workspace root.

            Returns:
                Path to workspace root
            """
            self.original_cwd = os.getcwd()
            os.chdir(str(self.root))
            return self.root

        def __exit__(self, *args: Any) -> None:
            """Exit context: restore original directory."""
            if self.original_cwd:
                os.chdir(self.original_cwd)

        def change_to(self, subdir: str) -> Path:
            """Change to a subdirectory (relative to workspace root).

            Args:
                subdir: Relative path to subdirectory

            Returns:
                Path to the subdirectory
            """
            target = self.root / subdir
            target.mkdir(parents=True, exist_ok=True)
            os.chdir(str(target))
            return target

        def get_path(self, *parts: str) -> Path:
            """Get a path relative to workspace root.

            Args:
                *parts: Path components

            Returns:
                Full path to the resource
            """
            return self.root.joinpath(*parts)

    return IsolatedWorkspace(tmp_path)
