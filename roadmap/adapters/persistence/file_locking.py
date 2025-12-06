"""File locking mechanism for roadmap YAML files."""

import errno
import fcntl
import json
import os
import tempfile
import time
from contextlib import AbstractContextManager
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any

from roadmap.common.file_utils import ensure_directory_exists


class FileLockError(Exception):
    """Exception raised for file locking errors."""

    pass


class FileLockTimeout(FileLockError):
    """Exception raised when file lock times out."""

    pass


class FileLock:
    """File lock implementation using fcntl (Unix/Linux/macOS) or msvcrt (Windows)."""

    def __init__(
        self, file_path: Path, timeout: float = 30.0, check_interval: float = 0.1
    ):
        self.file_path = file_path
        self.lock_path = file_path.with_suffix(file_path.suffix + ".lock")
        self.timeout = timeout
        self.check_interval = check_interval
        self.lock_file = None
        self.acquired = False

        # Lock metadata
        self.lock_info = {
            "pid": os.getpid(),
            "timestamp": datetime.now().isoformat(),
            "file": str(file_path),
            "host": os.uname().nodename if hasattr(os, "uname") else "unknown",
        }

    def __enter__(self):
        """Context manager entry."""
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()

    def acquire(self) -> bool:
        """Acquire the file lock."""
        if self.acquired:
            return True

        start_time = time.time()

        while time.time() - start_time < self.timeout:
            try:
                # Create lock file
                self.lock_file = open(self.lock_path, "w")

                # Try to acquire exclusive lock
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

                # Write lock metadata
                json.dump(self.lock_info, self.lock_file, indent=2)
                self.lock_file.flush()

                self.acquired = True
                return True

            except OSError as e:
                if e.errno in (errno.EAGAIN, errno.EACCES):
                    # Lock is already held, wait and retry
                    if self.lock_file:
                        self.lock_file.close()
                        self.lock_file = None
                    time.sleep(self.check_interval)
                    continue
                else:
                    # Other error
                    if self.lock_file:
                        self.lock_file.close()
                        self.lock_file = None
                    raise FileLockError(f"Failed to acquire lock: {e}") from e

        # Timeout reached
        if self.lock_file:
            self.lock_file.close()
            self.lock_file = None
        raise FileLockTimeout(f"Failed to acquire lock within {self.timeout} seconds")

    def release(self) -> bool:
        """Release the file lock."""
        if not self.acquired:
            return True

        try:
            if self.lock_file:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()
                self.lock_file = None

            # Remove lock file
            if self.lock_path.exists():
                self.lock_path.unlink()

            self.acquired = False
            return True

        except Exception as e:
            raise FileLockError(f"Failed to release lock: {e}") from e

    def is_locked(self) -> bool:
        """Check if the file is currently locked."""
        if not self.lock_path.exists():
            return False

        try:
            # Try to open and lock the file
            with open(self.lock_path) as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            return False  # No lock held
        except OSError:
            return True  # Lock is held

    def get_lock_info(self) -> dict[str, Any] | None:
        """Get information about the current lock holder."""
        if not self.lock_path.exists():
            return None

        try:
            with open(self.lock_path) as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

    def force_unlock(self) -> bool:
        """Force unlock by removing the lock file (use with caution)."""
        try:
            if self.lock_path.exists():
                self.lock_path.unlink()
            return True
        except Exception:
            return False


class LockManager:
    """Manager for handling multiple file locks and lock policies."""

    def __init__(self, default_timeout: float = 30.0):
        self.default_timeout = default_timeout
        self.active_locks: dict[str, FileLock] = {}
        self._global_lock = Lock()  # Thread safety

    def lock_file(
        self, file_path: Path, timeout: float | None = None
    ) -> AbstractContextManager[FileLock]:
        """Get a context manager for file locking."""
        timeout = timeout or self.default_timeout
        file_str = str(file_path)

        with self._global_lock:
            if file_str in self.active_locks:
                # Reuse existing lock
                return self.active_locks[file_str]

            # Create new lock
            lock = FileLock(file_path, timeout)
            self.active_locks[file_str] = lock
            return lock

    def is_file_locked(self, file_path: Path) -> bool:
        """Check if a file is currently locked."""
        lock = FileLock(file_path)
        return lock.is_locked()

    def get_lock_info(self, file_path: Path) -> dict[str, Any] | None:
        """Get lock information for a file."""
        lock = FileLock(file_path)
        return lock.get_lock_info()

    def force_unlock_file(self, file_path: Path) -> bool:
        """Force unlock a file (use with extreme caution)."""
        lock = FileLock(file_path)
        return lock.force_unlock()

    def cleanup_stale_locks(self, max_age_hours: float = 24.0) -> int:
        """Clean up stale lock files older than max_age_hours."""
        cleaned = 0
        max_age = timedelta(hours=max_age_hours)
        current_time = datetime.now()

        # Find all .lock files
        for lock_file in Path(".").rglob("*.lock"):
            try:
                # Check file age
                file_time = datetime.fromtimestamp(lock_file.stat().st_mtime)
                if current_time - file_time > max_age:
                    # Check if the lock is actually stale
                    lock = FileLock(lock_file.with_suffix(""))
                    if not lock.is_locked():
                        lock_file.unlink()
                        cleaned += 1
            except Exception:
                continue

        return cleaned

    def get_all_locks(
        self, search_dir: Path | None = None
    ) -> dict[str, dict[str, Any]]:
        """Get information about all current locks."""
        locks = {}
        search_path = search_dir or Path(".")

        for lock_file in search_path.rglob("*.lock"):
            try:
                original_file = lock_file.with_suffix("")
                lock = FileLock(original_file)
                lock_info = lock.get_lock_info()
                if lock_info:
                    locks[str(original_file)] = lock_info
            except Exception:
                continue

        return locks


class LockedFileOperations:
    """File operations with automatic locking."""

    def __init__(self, lock_manager: LockManager | None = None):
        self.lock_manager = lock_manager or LockManager()

    def read_file_locked(self, file_path: Path, timeout: float | None = None) -> str:
        """Read a file with locking."""
        with self.lock_manager.lock_file(file_path, timeout):
            return file_path.read_text(encoding="utf-8")

    def write_file_locked(
        self,
        file_path: Path,
        content: str,
        timeout: float | None = None,
        backup: bool = True,
    ) -> bool:
        """Write a file with locking and optional backup."""
        with self.lock_manager.lock_file(file_path, timeout):
            try:
                # Create backup if requested and file exists
                if backup and file_path.exists():
                    backup_path = file_path.with_suffix(f".backup.{int(time.time())}")
                    backup_path.write_text(
                        file_path.read_text(encoding="utf-8"), encoding="utf-8"
                    )

                # Ensure directory exists
                ensure_directory_exists(file_path.parent)

                # Write to temporary file first for atomic operation
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    dir=file_path.parent,
                    prefix=f".{file_path.name}.",
                    suffix=".tmp",
                    delete=False,
                ) as tmp_file:
                    tmp_file.write(content)
                    tmp_path = Path(tmp_file.name)

                # Atomic move
                tmp_path.replace(file_path)
                return True

            except Exception as e:
                # Clean up temp file if it exists
                if "tmp_path" in locals() and tmp_path.exists():
                    tmp_path.unlink()
                raise FileLockError(f"Failed to write file: {e}") from e

    def update_file_locked(
        self, file_path: Path, updater_func, timeout: float | None = None
    ) -> Any:
        """Update a file using an updater function with locking."""
        with self.lock_manager.lock_file(file_path, timeout):
            # Read current content
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
            else:
                content = ""

            # Apply updater function
            new_content = updater_func(content)

            # Write back if changed
            if new_content != content:
                self.write_file_locked(
                    file_path, new_content, timeout=None, backup=True
                )

            return new_content


# Global instances
lock_manager = LockManager()
locked_file_ops = LockedFileOperations(lock_manager)
