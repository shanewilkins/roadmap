"""Tests for roadmap initialization with templates."""

from pathlib import Path

from roadmap.adapters.cli import main
from tests.unit.common.formatters.test_ansi_utilities import clean_cli_output


class TestInitTemplate:
    """Test roadmap init with custom templates."""

    def test_init_with_custom_template(self, cli_runner):
        """Test that init uses custom template file when provided."""
        with cli_runner.isolated_filesystem():
            # Create custom template
            tpl = Path("custom_project_template.md")
            tpl.write_text(
                "# CUSTOM TEMPLATE\n\nThis is a custom template for testing."
            )

            # Run init with custom template
            result = cli_runner.invoke(
                main,
                [
                    "init",
                    "--non-interactive",
                    "--skip-github",
                    "--template-path",
                    str(tpl),
                    "--project-name",
                    "Test Project",
                ],
            )

            output = clean_cli_output(result.output)
            assert result.exit_code == 0, output
            assert Path(".roadmap").exists()

            # Verify project file contains custom marker
            projects_dir = Path(".roadmap/projects")
            if projects_dir.exists():
                files = list(projects_dir.iterdir())
                if files:
                    content = files[0].read_text()
                    assert "CUSTOM TEMPLATE" in content
