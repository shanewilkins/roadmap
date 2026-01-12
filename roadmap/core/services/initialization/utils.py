"""Utility classes for initialization workflow."""

import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

from roadmap.common.console import get_console

console = get_console()


class InitializationLock:
    """Manages initialization lockfile to prevent concurrent inits."""

    def __init__(self, lock_path: Path):
        self.lock_path = lock_path

    def acquire(self) -> bool:
        """Acquire the lock. Returns False if already locked."""
        if self.lock_path.exists():
            return False
        try:
            self.lock_path.write_text(
                f"pid:{os.getpid()}\nstarted:{datetime.now(UTC).isoformat()}\n"
            )
            return True
        except Exception:
            console.print(
                "⚠️  Could not create init lockfile; proceeding with care",
                style="yellow",
            )
            return True  # Continue anyway

    def release(self) -> None:
        """Release the lock."""
        try:
            if self.lock_path.exists():
                self.lock_path.unlink()
        except Exception:
            pass


class InitializationManifest:
    """Tracks created files/directories for potential rollback."""

    def __init__(self, manifest_file: Path):
        self.manifest_file = manifest_file
        self.data: dict[str, list] = {"created": []}

    def add_path(self, path: Path) -> None:
        """Add a path to the manifest."""
        if path.exists():
            self.data["created"].append(str(path))
            self._save()

    def _save(self) -> None:
        """Save manifest to disk (best effort)."""
        try:
            self.manifest_file.write_text(json.dumps(self.data))
        except Exception:
            pass

    def rollback(self) -> None:
        """Remove all paths tracked in the manifest."""
        if not self.manifest_file.exists():
            return

        try:
            data = json.loads(self.manifest_file.read_text())
            for p in data.get("created", []):
                try:
                    ppath = Path(p)
                    if ppath.is_file():
                        ppath.unlink()
                    elif ppath.is_dir():
                        shutil.rmtree(ppath)
                except Exception:
                    pass
        except Exception:
            pass
