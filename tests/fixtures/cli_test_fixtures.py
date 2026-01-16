"""Fixtures for CLI integration testing.

Provides reusable fixtures for:
- CLI test setup and teardown
- Temporary roadmap project structures
- Config file management
- Project/milestone/issue creation via CLI
"""

from pathlib import Path

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli.core import init


@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_roadmap_dir(cli_runner):
    """Create a temporary isolated filesystem with basic roadmap structure."""
    with cli_runner.isolated_filesystem():
        roadmap_dir = Path(".roadmap")
        roadmap_dir.mkdir()
        yield roadmap_dir


@pytest.fixture
def temp_roadmap_with_projects(cli_runner):
    """Create a temporary roadmap with multiple projects."""
    with cli_runner.isolated_filesystem():
        roadmap_dir = Path(".roadmap")
        projects_dir = roadmap_dir / "projects"
        projects_dir.mkdir(parents=True)

        # Create sample projects
        for proj_name in ["main", "backend"]:
            project_file = projects_dir / f"{proj_name}.md"
            project_file.write_text(
                f"""---
id: {proj_name}_proj
name: {proj_name.title()} Project
description: Team project
status: active
---

# {proj_name.title()} Project

Project content
"""
            )

        yield (roadmap_dir, projects_dir)


@pytest.fixture
def temp_roadmap_with_config(cli_runner):
    """Create a temporary roadmap with shared config file."""
    with cli_runner.isolated_filesystem():
        roadmap_dir = Path(".roadmap")
        roadmap_dir.mkdir()

        config_file = roadmap_dir / "config.yaml"
        config_file.write_text(
            """user:
  name: alice
  email: alice@team.com
github:
  enabled: true
"""
        )

        yield (roadmap_dir, config_file)


@pytest.fixture
def temp_roadmap_with_git_context(cli_runner):
    """Create a temporary roadmap in a git repository context."""
    with cli_runner.isolated_filesystem():
        # Simulate git repo
        Path(".git").mkdir()
        roadmap_dir = Path(".roadmap")
        roadmap_dir.mkdir()
        yield roadmap_dir


@pytest.fixture
def temp_roadmap_team_scenario(cli_runner):
    """Create a temporary roadmap simulating a team scenario.

    Simulates:
    - Shared config (Alice's config)
    - Multiple projects
    - Team structure
    """
    with cli_runner.isolated_filesystem():
        roadmap_dir = Path(".roadmap")
        projects_dir = roadmap_dir / "projects"
        projects_dir.mkdir(parents=True)

        # Create shared config
        config_file = roadmap_dir / "config.yaml"
        config_file.write_text(
            """user:
  name: alice
  email: alice@team.com
github:
  enabled: false
"""
        )

        # Create team projects
        for proj_name in ["backend", "frontend"]:
            project_file = projects_dir / f"{proj_name}.md"
            project_file.write_text(
                f"""---
id: {proj_name}_proj
name: {proj_name.title()}
status: active
---

# {proj_name.title()}

Shared project
"""
            )

        yield (roadmap_dir, projects_dir, config_file)


@pytest.fixture
def cli_runner_with_init(cli_runner):
    """Create a CLI runner with initialized roadmap."""
    with cli_runner.isolated_filesystem():
        result = cli_runner.invoke(
            init,
            [
                "--yes",
                "--skip-github",
                "--skip-project",
            ],
        )
        assert result.exit_code == 0, f"Failed to initialize roadmap: {result.output}"
        from roadmap.infrastructure.coordination.core import RoadmapCore

        core = RoadmapCore()
        yield cli_runner, core
