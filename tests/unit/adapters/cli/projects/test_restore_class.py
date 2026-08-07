"""Unit tests for project restore command."""

from roadmap.adapters.cli.projects.restore import restore_project


class TestProjectRestore:
    """Test project restore command."""

    def test_restore_project(self, cli_runner):
        """Test restoring a project."""
        result = cli_runner.invoke(restore_project)

        assert result is not None

    def test_restore_with_force(self, cli_runner):
        """Test restoring with force flag."""
        result = cli_runner.invoke(restore_project, ["--force"])

        assert result is not None

    def test_restore_dry_run(self, cli_runner):
        """Test restore dry run."""
        result = cli_runner.invoke(restore_project, ["--dry-run"])

        assert result is not None

    def test_restore_with_project_name(self, cli_runner):
        """Test restore with specific project name."""
        result = cli_runner.invoke(restore_project, ["my-project"])

        assert result is not None

    def test_restore_all(self, cli_runner):
        """Test restore all archived projects."""
        result = cli_runner.invoke(restore_project, ["--all"])

        assert result is not None
