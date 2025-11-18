from pathlib import Path

from roadmap.cli import main


def test_init_with_custom_template(cli_runner):
    runner = cli_runner
    with runner.isolated_filesystem():
        # Create a custom template file
        tpl = Path("custom_project_template.md")
        tpl.write_text("# CUSTOM TEMPLATE\n\nThis is a custom template for testing.")

        # Run init with template-path
        result = runner.invoke(
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

        assert result.exit_code == 0, result.output

        # Check .roadmap/projects for a created project file
        roadmap_dir = Path(".roadmap")
        assert roadmap_dir.exists()
        projects_dir = roadmap_dir / "projects"
        assert projects_dir.exists()

        files = list(projects_dir.iterdir())
        assert files, "No project files created"

        # Verify the project file contains our custom marker
        content = files[0].read_text()
        assert "CUSTOM TEMPLATE" in content
