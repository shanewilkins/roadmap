"""Filesystem layout adapter for canonical workspace initialization."""

from pathlib import Path

from .configuration import ConfigurationFiles


class FilesystemWorkspaceLayout:
    """Create only the directories and versioned policy owned by Roadmap."""

    def __init__(self, root_path: Path, roadmap_dir_name: str = ".roadmap"):
        self.root_path = root_path
        self.roadmap_dir = root_path / roadmap_dir_name
        self.configuration = ConfigurationFiles(
            self.roadmap_dir / "config.yaml",
            Path.home() / ".config" / "roadmap" / "config.yaml",
        )

    def is_initialized(self) -> bool:
        return self.roadmap_dir.is_dir() and self.configuration.project_path.is_file()

    def prepare(self) -> None:
        self.roadmap_dir.mkdir(parents=True, exist_ok=True)
        for name in ("issues", "milestones", "projects", "backups", "db"):
            (self.roadmap_dir / name).mkdir(exist_ok=True)
        self.configuration.initialize()
        self._ensure_gitignore()

    def _ensure_gitignore(self) -> None:
        path = self.root_path / ".gitignore"
        entries = (
            ".roadmap/db/*.db",
            ".roadmap/db/*.db-*",
            ".roadmap/db/*.lock",
        )
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        missing = tuple(item for item in entries if item not in existing.splitlines())
        if not missing:
            return
        prefix = "" if not existing or existing.endswith("\n") else "\n"
        path.write_text(existing + prefix + "\n".join(missing) + "\n", encoding="utf-8")
