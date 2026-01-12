"""Export management service for handling data exports with config integration."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from structlog import get_logger

from roadmap.common.config_loader import ConfigLoader
from roadmap.common.console import get_console

logger = get_logger()
console = get_console()


class ExportManager:
    """Manages data exports using configuration system for defaults and locations."""

    def __init__(self, project_root: Path | None = None):
        """Initialize export manager.

        Args:
            project_root: Project root directory (defaults to cwd)
        """
        self.project_root = project_root or Path.cwd()
        self.config = ConfigLoader.load_config(self.project_root)

    def get_export_dir(self) -> Path:
        """Get the export directory, creating it if needed.

        Returns:
            Path to export directory
        """
        export_dir = self.config.export.directory

        # Handle relative vs absolute paths
        if export_dir.startswith("/"):
            # Absolute path
            path = Path(export_dir)
        else:
            # Relative to project root
            path = self.project_root / export_dir

        # Create directory if it doesn't exist
        path.mkdir(parents=True, exist_ok=True)

        # Add to .gitignore if configured
        if self.config.export.auto_gitignore:
            self._add_to_gitignore(path)

        return path

    def _add_to_gitignore(self, path: Path) -> None:
        """Add export directory to .gitignore if not already there.

        Args:
            path: Path to add to gitignore
        """
        gitignore_path = self.project_root / ".gitignore"

        # Make path relative for .gitignore
        try:
            rel_path = path.relative_to(self.project_root)
        except ValueError:
            # Path is absolute, can't make it relative
            rel_path = path

        # Read existing gitignore
        if gitignore_path.exists():
            content = gitignore_path.read_text()
        else:
            content = ""

        # Check if already present
        gitignore_entry = str(rel_path) + "/"
        if gitignore_entry in content:
            return  # Already there

        # Add to gitignore
        if content and not content.endswith("\n"):
            content += "\n"

        content += f"{gitignore_entry}\n"
        gitignore_path.write_text(content)
        logger.info("added_to_gitignore", path=str(rel_path))

    def generate_export_filename(self, entity_type: str, format_type: str) -> str:
        """Generate a timestamped export filename.

        Args:
            entity_type: Type of entity being exported (issues, milestones, projects)
            format_type: Export format (json, csv, markdown)

        Returns:
            Filename with timestamp
        """
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d-%H%M%S")
        return f"{entity_type}-{timestamp}.{format_type}"

    def get_export_path(self, entity_type: str, format_type: str | None = None) -> Path:
        """Get full export path with auto-generated filename.

        Args:
            entity_type: Type of entity being exported
            format_type: Export format (uses config default if not specified)

        Returns:
            Full path to export file
        """
        if format_type is None:
            format_type = self.config.export.format

        export_dir = self.get_export_dir()
        filename = self.generate_export_filename(entity_type, format_type)
        return export_dir / filename

    def export_json(self, data: Any, output_path: Path | None = None) -> str:
        """Export data as JSON.

        Args:
            data: Data to export (usually list or dict)
            output_path: Optional custom output path

        Returns:
            JSON string
        """
        if isinstance(data, list):
            # Convert objects to dicts if needed
            serializable = [
                item.model_dump() if hasattr(item, "model_dump") else item
                for item in data
            ]
        else:
            serializable = data.model_dump() if hasattr(data, "model_dump") else data

        json_str = json.dumps(serializable, indent=2, default=str)

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json_str)
            logger.info("exported_json", path=str(output_path))

        return json_str

    def export_csv(self, data: list[Any], output_path: Path | None = None) -> str:
        """Export data as CSV.

        Args:
            data: List of objects to export
            output_path: Optional custom output path

        Returns:
            CSV string
        """
        if not data:
            csv_str = ""
        else:
            import csv
            from io import StringIO

            # Get headers from first item
            first_item = data[0]
            if hasattr(first_item, "model_dump"):
                headers = first_item.model_dump().keys()
                rows = [item.model_dump() for item in data]
            else:
                headers = first_item.keys() if isinstance(first_item, dict) else []
                rows = data

            # Write CSV
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
            csv_str = output.getvalue()

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(csv_str)
            logger.info("exported_csv", path=str(output_path))

        return csv_str

    def export_markdown(self, data: list[Any], output_path: Path | None = None) -> str:
        """Export data as Markdown table.

        Args:
            data: List of objects to export
            output_path: Optional custom output path

        Returns:
            Markdown string
        """
        if not data:
            md_str = ""
        else:
            # Get headers from first item
            first_item = data[0]
            if hasattr(first_item, "model_dump"):
                headers = list(first_item.model_dump().keys())
                rows = [item.model_dump() for item in data]
            else:
                headers = (
                    list(first_item.keys()) if isinstance(first_item, dict) else []
                )
                rows = data

            # Build markdown table
            md_lines = [
                "| " + " | ".join(headers) + " |",
                "| " + " | ".join(["---"] * len(headers)) + " |",
            ]

            for row in rows:
                values = [
                    str(row.get(h, "")) if isinstance(row, dict) else ""
                    for h in headers
                ]
                md_lines.append("| " + " | ".join(values) + " |")

            md_str = "\n".join(md_lines)

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(md_str)
            logger.info("exported_markdown", path=str(output_path))

        return md_str

    def export_data(
        self,
        data: Any,
        entity_type: str,
        format_type: str | None = None,
        output_path: Path | None = None,
    ) -> tuple[str, Path]:
        """Export data in specified format.

        Args:
            data: Data to export
            entity_type: Type of entity being exported
            format_type: Export format (uses config default if not specified)
            output_path: Optional custom output path

        Returns:
            Tuple of (exported_content, file_path)
        """
        if format_type is None:
            format_type = self.config.export.format

        if output_path is None:
            output_path = self.get_export_path(entity_type, format_type)

        if format_type == "json":
            content = self.export_json(data, output_path)
        elif format_type == "csv":
            content = self.export_csv(
                data if isinstance(data, list) else [data], output_path
            )
        elif format_type == "markdown":
            content = self.export_markdown(
                data if isinstance(data, list) else [data], output_path
            )
        else:
            raise ValueError(f"Unsupported export format: {format_type}")

        return content, output_path
