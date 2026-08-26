"""Canonical initialization journeys."""

from pathlib import Path

import yaml

from roadmap.bootstrap import cli
from roadmap.bootstrap.core import create_core


def _invoke(cli_runner, *arguments: str):
    return cli_runner.invoke(cli, ["init", *arguments])


def test_dry_run_reports_complete_plan_without_writing(cli_runner) -> None:
    with cli_runner.isolated_filesystem():
        result = _invoke(cli_runner, "--dry-run", "--project-name", "Demo")

        assert result.exit_code == 0, result.exception
        assert "Would create canonical workspace" in result.stdout
        assert not Path(".roadmap").exists()


def test_initialization_creates_versioned_layout_and_first_project(cli_runner) -> None:
    with cli_runner.isolated_filesystem():
        result = _invoke(
            cli_runner,
            "--non-interactive",
            "--project-name",
            "Demo",
            "--description",
            "Canonical project",
        )

        assert result.exit_code == 0, result.exception
        root = Path(".roadmap")
        assert {
            "issues",
            "milestones",
            "projects",
            "backups",
            "db",
        } <= {path.name for path in root.iterdir() if path.is_dir()}
        assert yaml.safe_load((root / "config.yaml").read_text())["schema_version"] == 1
        projects = create_core(Path.cwd()).planning.all_projects()
        assert [(str(item.name), item.content.strip()) for item in projects] == [
            ("Demo", "Canonical project")
        ]


def test_repeated_initialization_preserves_existing_canonical_data(cli_runner) -> None:
    with cli_runner.isolated_filesystem():
        first = _invoke(cli_runner, "--project-name", "Demo")
        before = tuple(Path(".roadmap/projects").rglob("*.md"))[0].read_bytes()
        second = _invoke(cli_runner, "--project-name", "Different", "--force")

        assert first.exit_code == second.exit_code == 0
        assert "already initialized" in second.stdout
        assert tuple(Path(".roadmap/projects").rglob("*.md"))[0].read_bytes() == before
        assert len(create_core(Path.cwd()).planning.all_projects()) == 1


def test_skip_project_and_custom_directory_are_explicit(cli_runner) -> None:
    with cli_runner.isolated_filesystem():
        result = _invoke(cli_runner, "--name", ".planning", "--skip-project")

        assert result.exit_code == 0, result.exception
        assert Path(".planning/config.yaml").is_file()
        assert create_core(Path.cwd(), ".planning").planning.all_projects() == ()


def test_initialization_rejects_path_traversal(cli_runner) -> None:
    with cli_runner.isolated_filesystem():
        result = _invoke(cli_runner, "--name", "../outside", "--skip-project")

        assert result.exit_code == 2
        assert "one local directory name" in result.stderr
        assert not Path("../outside").exists()
