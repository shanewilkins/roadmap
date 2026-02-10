"""Validation Coordinator - Coordinates validation operations.

Extracted from RoadmapCore to reduce god object complexity.
Provides a focused API for validation concerns.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from roadmap.common.errors.error_standards import OperationType, safe_operation
from roadmap.common.logging import get_logger
from roadmap.core.services import GitHubIntegrationService

if TYPE_CHECKING:
    from roadmap.infrastructure.coordination.core import RoadmapCore

logger = get_logger(__name__)


class ValidationCoordinator:
    """Coordinates all validation operations."""

    def __init__(
        self, github_service: GitHubIntegrationService, core: RoadmapCore | None = None
    ):
        """Initialize coordinator with GitHub service.

        Args:
            github_service: GitHubIntegrationService instance
            core: RoadmapCore instance for initialization checks
        """
        self._github_service = github_service
        self._core = core

    @safe_operation(OperationType.READ, "Configuration")
    def get_github_config(self) -> tuple[str | None, str | None, str | None]:
        """Get GitHub configuration from config file and credentials.

        Returns:
            Tuple of (token, owner, repo) or (None, None, None) if not configured
        """
        logger.info("getting_github_config")
        return self._github_service.get_github_config()

    @safe_operation(OperationType.READ, "RemoteLinks")
    def collect_remote_link_validation_data(
        self,
        issues_dir: Path,
        backend_name: str = "github",
    ) -> dict:
        """Collect YAML and database remote link data for validation.

        Args:
            issues_dir: Directory containing issue markdown files
            backend_name: Backend name to validate

        Returns:
            Dict with issue_files, total_files, yaml_remote_ids, unparseable_files, db_links
        """
        if not self._core:
            raise ValueError("ValidationCoordinator requires RoadmapCore")

        issue_files = sorted(issues_dir.glob("**/*.md")) if issues_dir.exists() else []
        yaml_remote_ids: dict[str, dict[str, str | int]] = {}
        unparseable_files: list[tuple[str, str]] = []

        if issue_files:
            from roadmap.adapters.persistence.parser.issue import IssueParser

            for file_path in issue_files:
                try:
                    issue = IssueParser.parse_issue_file(file_path)
                    if issue.remote_ids:
                        yaml_remote_ids[issue.id] = issue.remote_ids
                except Exception as e:
                    logger.warning(
                        "failed_to_parse_issue_file",
                        file_path=str(file_path),
                        error=str(e),
                    )
                    unparseable_files.append((str(file_path), str(e)))

        db_links = self._core.db.remote_links.get_all_links_for_backend(backend_name)

        return {
            "issue_files": issue_files,
            "total_files": len(issue_files),
            "yaml_remote_ids": yaml_remote_ids,
            "unparseable_files": unparseable_files,
            "db_links": db_links,
        }

    @safe_operation(OperationType.READ, "RemoteLinks")
    def build_remote_link_report(
        self,
        yaml_remote_ids: dict[str, dict[str, str | int]],
        db_links: dict[str, str | int],
    ) -> dict:
        """Build a report of remote link discrepancies and duplicates.

        Args:
            yaml_remote_ids: Mapping of issue_id -> backend_name -> remote_id
            db_links: Mapping of issue_uuid -> remote_id

        Returns:
            Dict with validation summary fields
        """
        yaml_issue_uuids = set(yaml_remote_ids.keys())
        db_issue_uuids = set(db_links.keys())

        missing_in_db = [
            uuid for uuid in yaml_issue_uuids if uuid not in db_issue_uuids
        ]
        extra_in_db = [uuid for uuid in db_issue_uuids if uuid not in yaml_issue_uuids]

        duplicate_remote_ids: dict[str, list[str]] = {}
        remote_id_map: dict[str, list[str]] = {}
        for issue_uuid, remote_id in db_links.items():
            remote_id_key = str(remote_id)
            remote_id_map.setdefault(remote_id_key, []).append(issue_uuid)

        for remote_id, issue_uuids in remote_id_map.items():
            if len(issue_uuids) > 1:
                duplicate_remote_ids[remote_id] = issue_uuids

        return {
            "files_with_remote_ids": len(yaml_remote_ids),
            "database_links": len(db_links),
            "missing_in_db": missing_in_db,
            "extra_in_db": extra_in_db,
            "duplicate_remote_ids": duplicate_remote_ids,
        }

    @safe_operation(OperationType.UPDATE, "RemoteLinks")
    def apply_remote_link_fixes(
        self,
        yaml_remote_ids: dict[str, dict[str, str | int]],
        report: dict,
        backend_name: str = "github",
        prune_extra: bool = False,
        dedupe: bool = False,
        dry_run: bool = False,
    ) -> dict:
        """Apply fixes for missing, extra, and duplicate remote links.

        Args:
            yaml_remote_ids: Mapping of issue_id -> backend_name -> remote_id
            report: Validation report dict
            backend_name: Backend name to fix
            prune_extra: Remove links missing from YAML
            dedupe: Remove duplicate remote_id links
            dry_run: If True, do not apply changes

        Returns:
            Dict with counts for fixed, removed, and deduped links
        """
        if not self._core:
            raise ValueError("ValidationCoordinator requires RoadmapCore")

        fixed_count = 0
        removed_count = 0
        deduped_count = 0

        for issue_uuid in report.get("missing_in_db", []):
            remote_ids = yaml_remote_ids.get(issue_uuid)
            if not remote_ids:
                continue
            if dry_run:
                fixed_count += 1
                continue

            for backend_key, remote_id in remote_ids.items():
                self._core.db.remote_links.link_issue(
                    issue_uuid,
                    backend_key,
                    remote_id,
                )
            fixed_count += 1

        if prune_extra:
            for issue_uuid in report.get("extra_in_db", []):
                if dry_run:
                    removed_count += 1
                    continue

                if self._core.db.remote_links.unlink_issue(issue_uuid, backend_name):
                    removed_count += 1

        if dedupe:
            duplicates = report.get("duplicate_remote_ids", {})
            yaml_issue_uuids = set(yaml_remote_ids.keys())

            for issue_uuids in duplicates.values():
                keep_uuid = next(
                    (uuid for uuid in issue_uuids if uuid in yaml_issue_uuids),
                    issue_uuids[0],
                )
                for issue_uuid in issue_uuids:
                    if issue_uuid == keep_uuid:
                        continue
                    if dry_run:
                        deduped_count += 1
                        continue

                    if self._core.db.remote_links.unlink_issue(
                        issue_uuid, backend_name
                    ):
                        deduped_count += 1

        return {
            "fixed_count": fixed_count,
            "removed_count": removed_count,
            "deduped_count": deduped_count,
        }
