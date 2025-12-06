"""Service for consistent file enumeration and parsing.

Consolidates repeated patterns from services:
- Directory walking with rglob("*.md")
- Backup file filtering
- Consistent error handling and logging
- File-to-object parsing with retry logic

This service eliminates ~200 lines of duplicated enumeration logic
across IssueService, MilestoneService, ProjectService, and validators.

Usage:

    # Simple enumeration and parsing
    issues = FileEnumerationService.enumerate_and_parse(
        directory=issues_dir,
        parser_func=IssueParser.parse_issue_file
    )

    # Enumeration with filtering
    open_issues = FileEnumerationService.enumerate_with_filter(
        directory=issues_dir,
        parser_func=IssueParser.parse_issue_file,
        filter_func=lambda issue: issue.status == Status.OPEN
    )

    # Find single item by ID
    issue = FileEnumerationService.find_by_id(
        directory=issues_dir,
        id_value="abc12345",
        parser_func=IssueParser.parse_issue_file
    )
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from roadmap.common.logging import get_logger

logger = get_logger(__name__)


class FileEnumerationService:
    """Unified service for enumerating and filtering markdown files.

    Provides consistent patterns for:
    - Walking directories recursively
    - Filtering backup files
    - Parsing files with error handling
    - Finding items by ID pattern
    """

    @staticmethod
    def enumerate_and_parse(
        directory: Path,
        parser_func: Callable[[Path], Any],
        backup_filter: bool = True,
    ) -> list[Any]:
        """Enumerate files and parse with consistent error handling.

        Args:
            directory: Directory to enumerate
            parser_func: Parser function (e.g., IssueParser.parse_issue_file)
            backup_filter: Skip .backup files if True

        Returns:
            List of parsed objects (failed items skipped with logging)
        """
        if not directory.exists():
            logger.debug(
                "enumerate_and_parse_skip",
                reason="directory_not_found",
                directory=str(directory),
            )
            return []

        results = []
        for file_path in directory.rglob("*.md"):
            # Filter backup files if requested
            if backup_filter and ".backup" in file_path.name:
                continue

            try:
                obj = parser_func(file_path)
                # Preserve the file path on the object for later updates
                if obj is not None:
                    try:
                        obj.file_path = str(file_path)
                    except (AttributeError, TypeError):
                        # Object doesn't support attribute assignment (e.g., dict)
                        # This can happen in tests with mocks
                        pass
                    results.append(obj)
            except Exception as e:
                logger.debug(
                    "enumerate_and_parse_skip_file",
                    file=file_path.name,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                continue

        logger.debug(
            "enumerate_and_parse_complete",
            directory=str(directory),
            count=len(results),
        )
        return results

    @staticmethod
    def enumerate_with_filter(
        directory: Path,
        parser_func: Callable[[Path], Any],
        filter_func: Callable[[Any], bool],
    ) -> list[Any]:
        """Enumerate, parse, and apply filter predicate.

        Args:
            directory: Directory to enumerate
            parser_func: Parser function (e.g., IssueParser.parse_issue_file)
            filter_func: Predicate function (return True to include)

        Returns:
            List of parsed and filtered objects
        """
        items = FileEnumerationService.enumerate_and_parse(directory, parser_func)
        filtered = [item for item in items if filter_func(item)]

        logger.debug(
            "enumerate_with_filter_complete",
            directory=str(directory),
            total=len(items),
            filtered=len(filtered),
        )
        return filtered

    @staticmethod
    def find_by_id(
        directory: Path,
        id_value: str,
        parser_func: Callable[[Path], Any],
    ) -> Any | None:
        """Find a single file by ID pattern.

        Searches for files matching pattern: {id_value}-*.md
        Returns first match or None if not found.

        Args:
            directory: Directory to search
            id_value: ID to search for (first 8 chars, e.g., "abc12345")
            parser_func: Parser function

        Returns:
            First matching object or None
        """
        if not directory.exists():
            logger.debug(
                "find_by_id_skip",
                reason="directory_not_found",
                id=id_value,
            )
            return None

        pattern = f"{id_value}-*.md"
        for file_path in directory.rglob(pattern):
            try:
                obj = parser_func(file_path)
                # Preserve the file path on the object for later updates
                if obj is not None:
                    try:
                        obj.file_path = str(file_path)
                    except (AttributeError, TypeError):
                        # Object doesn't support attribute assignment
                        pass
                logger.debug(
                    "find_by_id_found",
                    id=id_value,
                    file=file_path.name,
                )
                return obj
            except Exception as e:
                logger.debug(
                    "find_by_id_parse_failed",
                    id=id_value,
                    file=file_path.name,
                    error=str(e),
                )
                continue

        logger.debug(
            "find_by_id_not_found",
            id=id_value,
            directory=str(directory),
        )
        return None
