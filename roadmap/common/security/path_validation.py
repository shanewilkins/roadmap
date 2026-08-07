"""Path validation and security utilities."""

from pathlib import Path

from .exceptions import PathValidationError
from .logging import log_security_event


def _check_traversal_patterns(path_str: str, allow_absolute: bool) -> None:
    """Check for directory traversal patterns."""
    if ".." in path_str and not allow_absolute:
        raise PathValidationError(
            f"Path contains potential directory traversal: {path_str}"
        )


def _resolve_path_safely(path: Path) -> Path:
    """Resolve path safely, handling missing directories."""
    try:
        return path.resolve()
    except (FileNotFoundError, OSError):
        # If resolve() fails due to missing current directory, handle gracefully
        if path.is_absolute():
            return path
        else:
            # For relative paths when cwd is missing, return as-is (caller context should handle)
            return path


def _resolve_relative_to_base(path: Path, base_dir: Path) -> Path:
    """Resolve path relative to base directory."""
    try:
        return path.resolve()
    except (FileNotFoundError, OSError):
        # If resolve fails, work with absolute version or relative to base
        if path.is_absolute():
            return path
        else:
            return base_dir / path


def _resolve_base_safely(base_dir: Path) -> Path:
    """Resolve base directory safely."""
    try:
        return base_dir.resolve()
    except (FileNotFoundError, OSError):
        return base_dir


def _check_absolute_allowed(path: Path, allow_absolute: bool) -> None:
    """Check if absolute path is allowed."""
    if not allow_absolute and path.is_absolute():
        raise PathValidationError(f"Absolute paths not allowed: {path}")


def _check_within_base(
    resolved_path: Path, resolved_base: Path, original_path: Path
) -> None:
    """Check if path is within base directory."""
    try:
        resolved_path.relative_to(resolved_base)
    except ValueError as e:
        raise PathValidationError(
            f"Path outside allowed directory: {original_path}"
        ) from e


def _check_dangerous_components(resolved_path: Path) -> None:
    """Check for dangerous path components."""
    path_parts = resolved_path.parts
    dangerous_parts = {"..", ".", "~"}
    if any(part in dangerous_parts for part in path_parts):
        raise PathValidationError(
            f"Path contains dangerous components: {resolved_path}"
        )


def validate_path(
    path: str | Path,
    base_dir: str | Path | None = None,
    allow_absolute: bool = False,
) -> Path:
    """Validate that a path is safe and within allowed boundaries.

    Args:
        path: Path to validate
        base_dir: Base directory that path must be within (optional)
        allow_absolute: Whether to allow absolute paths

    Returns:
        Resolved safe path

    Raises:
        PathValidationError: If path is unsafe or outside boundaries
    """
    try:
        # Convert to Path object if string
        if isinstance(path, str):
            path = Path(path)

        # If no base directory specified, just check for basic safety
        if base_dir is None:
            # Still check for directory traversal patterns
            path_str = str(path)
            _check_traversal_patterns(path_str, allow_absolute)
            return _resolve_path_safely(path)

        # Convert base_dir to Path if needed
        if isinstance(base_dir, str):
            base_dir = Path(base_dir)

        # Resolve paths
        resolved_path = _resolve_relative_to_base(path, base_dir)
        resolved_base = _resolve_base_safely(base_dir)

        # Validate
        _check_absolute_allowed(path, allow_absolute)
        _check_within_base(resolved_path, resolved_base, path)
        _check_dangerous_components(resolved_path)

        log_security_event(
            "path_validated",
            {
                "path": str(path),
                "resolved_path": str(resolved_path),
                "base_dir": str(base_dir) if base_dir else None,
            },
        )

        return resolved_path

    except Exception as e:
        log_security_event(
            "path_validation_failed",
            {"path": str(path), "base_dir": str(base_dir), "error": str(e)},
        )
        raise
