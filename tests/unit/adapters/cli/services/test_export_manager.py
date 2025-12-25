"""Tests for export manager service."""

import json
from pathlib import Path

import pytest

from roadmap.adapters.cli.services.export_manager import ExportManager
from roadmap.common.config_models import RoadmapConfig


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    return project_dir


@pytest.fixture
def export_manager(temp_project_dir):
    """Create an export manager with temporary project directory."""
    manager = ExportManager(project_root=temp_project_dir)
    # Mock the config with a real RoadmapConfig instance
    manager.config = RoadmapConfig()
    return manager


class TestExportManager:
    """Test ExportManager class."""

    def test_init_with_project_root(self, temp_project_dir):
        """Test initialization with project root."""
        manager = ExportManager(project_root=temp_project_dir)
        manager.config = RoadmapConfig()
        assert manager.project_root == temp_project_dir

    def test_init_default_project_root(self):
        """Test initialization with default project root."""
        manager = ExportManager()
        manager.config = RoadmapConfig()
        assert manager.project_root == Path.cwd()

    def test_get_export_dir_creates_directory(self, export_manager, temp_project_dir):
        """Test that get_export_dir creates the directory."""
        export_dir = export_manager.get_export_dir()
        assert export_dir.exists()
        assert export_dir.is_dir()

    def test_get_export_dir_relative_path(self, export_manager, temp_project_dir):
        """Test get_export_dir with relative path."""
        export_manager.config.export.directory = "exports"
        export_dir = export_manager.get_export_dir()
        assert export_dir == temp_project_dir / "exports"

    def test_get_export_dir_absolute_path(self, export_manager, temp_project_dir):
        """Test get_export_dir with absolute path."""
        export_manager.config.export.directory = "/tmp/exports"
        export_dir = export_manager.get_export_dir()
        assert export_dir == Path("/tmp/exports")

    def test_generate_export_filename(self, export_manager):
        """Test filename generation includes entity type and format."""
        filename = export_manager.generate_export_filename("issues", "json")
        assert "issues" in filename
        assert filename.endswith(".json")
        assert "-" in filename  # Has timestamp separator

    def test_get_export_path_uses_default_format(self, export_manager):
        """Test get_export_path uses default format from config."""
        export_manager.config.export.format = "csv"
        path = export_manager.get_export_path("issues")
        assert path.suffix == ".csv"

    def test_get_export_path_uses_provided_format(self, export_manager):
        """Test get_export_path respects provided format."""
        export_manager.config.export.format = "csv"
        path = export_manager.get_export_path("issues", "json")
        assert path.suffix == ".json"

    def test_export_json_dict(self, export_manager):
        """Test JSON export of dict."""
        data = {"name": "test", "value": 42}
        json_str = export_manager.export_json(data)
        parsed = json.loads(json_str)
        assert parsed["name"] == "test"
        assert parsed["value"] == 42

    def test_export_json_list(self, export_manager):
        """Test JSON export of list."""
        data = [{"name": "item1"}, {"name": "item2"}]
        json_str = export_manager.export_json(data)
        parsed = json.loads(json_str)
        assert len(parsed) == 2

    def test_export_json_with_pydantic_model(self, export_manager):
        """Test JSON export with Pydantic model."""
        from pydantic import BaseModel

        class Item(BaseModel):
            name: str
            value: int

        data = Item(name="test", value=42)
        json_str = export_manager.export_json(data)
        parsed = json.loads(json_str)
        assert parsed["name"] == "test"

    def test_export_json_to_file(self, export_manager, temp_project_dir):
        """Test JSON export writes to file."""
        data = {"name": "test"}
        output_path = temp_project_dir / "export.json"
        export_manager.export_json(data, output_path)
        assert output_path.exists()
        assert json.loads(output_path.read_text()) == data

    def test_export_csv_list_of_dicts(self, export_manager):
        """Test CSV export of list of dicts."""
        data = [{"name": "alice", "age": 30}, {"name": "bob", "age": 25}]
        csv_str = export_manager.export_csv(data)
        lines = csv_str.strip().split("\n")
        assert "name,age" in lines[0]
        assert len(lines) == 3  # header + 2 rows

    def test_export_csv_empty_list(self, export_manager):
        """Test CSV export of empty list."""
        csv_str = export_manager.export_csv([])
        assert csv_str == ""

    def test_export_csv_to_file(self, export_manager, temp_project_dir):
        """Test CSV export writes to file."""
        data = [{"name": "alice", "age": 30}]
        output_path = temp_project_dir / "export.csv"
        export_manager.export_csv(data, output_path)
        assert output_path.exists()
        content = output_path.read_text()
        assert "alice" in content

    def test_export_markdown_list_of_dicts(self, export_manager):
        """Test Markdown export of list of dicts."""
        data = [{"name": "alice", "age": 30}, {"name": "bob", "age": 25}]
        md_str = export_manager.export_markdown(data)
        assert "|" in md_str
        assert "alice" in md_str
        assert "bob" in md_str

    def test_export_markdown_empty_list(self, export_manager):
        """Test Markdown export of empty list."""
        md_str = export_manager.export_markdown([])
        assert md_str == ""

    def test_export_markdown_to_file(self, export_manager, temp_project_dir):
        """Test Markdown export writes to file."""
        data = [{"name": "alice"}]
        output_path = temp_project_dir / "export.md"
        export_manager.export_markdown(data, output_path)
        assert output_path.exists()
        content = output_path.read_text()
        assert "|" in content

    def test_export_data_json(self, export_manager):
        """Test export_data with JSON format."""
        data = [{"id": 1, "title": "Task"}]
        content, path = export_manager.export_data(data, "issues", "json")
        assert path.suffix == ".json"
        assert json.loads(content)[0]["id"] == 1

    def test_export_data_csv(self, export_manager):
        """Test export_data with CSV format."""
        data = [{"id": 1, "title": "Task"}]
        content, path = export_manager.export_data(data, "issues", "csv")
        assert path.suffix == ".csv"
        assert "Task" in content

    def test_export_data_markdown(self, export_manager):
        """Test export_data with Markdown format."""
        data = [{"id": 1, "title": "Task"}]
        content, path = export_manager.export_data(data, "issues", "markdown")
        assert path.suffix == ".markdown"
        assert "|" in content

    def test_export_data_uses_config_format(self, export_manager):
        """Test export_data uses config format when not specified."""
        export_manager.config.export.format = "csv"
        data = [{"id": 1}]
        content, path = export_manager.export_data(data, "issues")
        assert path.suffix == ".csv"

    def test_export_data_uses_custom_path(self, export_manager, temp_project_dir):
        """Test export_data with custom output path."""
        data = [{"id": 1}]
        custom_path = temp_project_dir / "custom.json"
        content, path = export_manager.export_data(
            data, "issues", "json", output_path=custom_path
        )
        assert path == custom_path
        assert custom_path.exists()

    def test_export_data_invalid_format(self, export_manager):
        """Test export_data raises error for invalid format."""
        data = [{"id": 1}]
        with pytest.raises(ValueError, match="Unsupported export format"):
            export_manager.export_data(data, "issues", "invalid")

    def test_add_to_gitignore_creates_file(self, export_manager, temp_project_dir):
        """Test _add_to_gitignore creates .gitignore if missing."""
        export_dir = temp_project_dir / "exports"
        export_manager._add_to_gitignore(export_dir)
        gitignore_path = temp_project_dir / ".gitignore"
        assert gitignore_path.exists()
        assert "exports/" in gitignore_path.read_text()

    def test_add_to_gitignore_appends_to_existing(
        self, export_manager, temp_project_dir
    ):
        """Test _add_to_gitignore appends to existing .gitignore."""
        gitignore_path = temp_project_dir / ".gitignore"
        gitignore_path.write_text("node_modules/\n")
        export_dir = temp_project_dir / "exports"
        export_manager._add_to_gitignore(export_dir)
        content = gitignore_path.read_text()
        assert "node_modules/" in content
        assert "exports/" in content

    def test_add_to_gitignore_skips_duplicate(self, export_manager, temp_project_dir):
        """Test _add_to_gitignore doesn't add duplicate entries."""
        gitignore_path = temp_project_dir / ".gitignore"
        gitignore_path.write_text("exports/\n")
        export_dir = temp_project_dir / "exports"
        export_manager._add_to_gitignore(export_dir)
        content = gitignore_path.read_text()
        # Should still have only one entry
        assert content.count("exports/") == 1

    def test_get_export_dir_adds_to_gitignore_when_configured(
        self, export_manager, temp_project_dir
    ):
        """Test get_export_dir adds to .gitignore when auto_gitignore is enabled."""
        export_manager.config.export.auto_gitignore = True
        export_manager.get_export_dir()
        gitignore_path = temp_project_dir / ".gitignore"
        assert gitignore_path.exists()
        content = gitignore_path.read_text()
        assert ".roadmap/exports/" in content

    def test_get_export_dir_skips_gitignore_when_disabled(
        self, export_manager, temp_project_dir
    ):
        """Test get_export_dir skips .gitignore when auto_gitignore is disabled."""
        export_manager.config.export.auto_gitignore = False
        export_manager.get_export_dir()
        gitignore_path = temp_project_dir / ".gitignore"
        assert not gitignore_path.exists()
