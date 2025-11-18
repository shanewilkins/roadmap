"""
Advanced Repository Scanning for comprehensive project analysis and migration.

This module provides advanced repository scanning capabilities including:
- Full commit history analysis with pattern recognition
- Branch relationship mapping and lifecycle tracking
- Migration tools for existing projects
- Bulk operations for large-scale repository processing
- Performance-optimized scanning with caching
- Statistical analysis and reporting
"""

import json
import logging
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .bulk_operations import BulkOperationResult, BulkOperations
from .ci_tracking import CITracker
from .core import RoadmapCore
from .file_utils import ensure_directory_exists
from .git_integration import GitIntegration
from .models import Issue, IssueType, Priority, Status
from .parser import IssueParser

logger = logging.getLogger(__name__)


@dataclass
class RepositoryScanConfig:
    """Configuration for advanced repository scanning."""

    # Scanning scope
    max_commits: int = 10000
    max_branches: int = 500
    include_deleted_branches: bool = True
    scan_all_refs: bool = False

    # Date range filtering
    since_date: datetime | None = None
    until_date: datetime | None = None

    # Pattern recognition
    custom_patterns: list[str] = field(default_factory=list)
    ignore_patterns: list[str] = field(
        default_factory=lambda: [
            r"^Merge\s+(branch|pull request)",
            r"^Revert\s+",
            r"^\s*(wip|WIP|fixup|squash)",
        ]
    )

    # Performance options
    use_parallel_processing: bool = True
    max_workers: int = 4
    enable_caching: bool = True
    cache_duration_hours: int = 24

    # Migration options
    create_missing_issues: bool = False
    auto_link_issues: bool = True
    preserve_commit_history: bool = True

    # Analysis options
    analyze_commit_patterns: bool = True
    analyze_branch_patterns: bool = True
    generate_statistics: bool = True
    detect_duplicate_work: bool = True


@dataclass
class CommitAnalysis:
    """Detailed analysis of a single commit."""

    sha: str
    message: str
    author: str
    author_email: str
    date: datetime
    branch: str | None = None

    # Issue associations
    issue_ids: list[str] = field(default_factory=list)
    potential_issue_refs: list[str] = field(default_factory=list)

    # Progress indicators
    progress_markers: list[int] = field(default_factory=list)
    completion_markers: list[str] = field(default_factory=list)

    # Analysis results
    commit_type: str | None = None  # feat, fix, docs, etc.
    breaking_change: bool = False
    files_changed: int = 0
    lines_added: int = 0
    lines_deleted: int = 0

    # Metadata
    is_merge_commit: bool = False
    parent_commits: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class BranchAnalysis:
    """Detailed analysis of a git branch."""

    name: str
    created_date: datetime | None = None
    last_commit_date: datetime | None = None
    merge_date: datetime | None = None

    # Branch metadata
    base_branch: str | None = None
    head_commit: str | None = None
    commit_count: int = 0
    is_merged: bool = False
    is_deleted: bool = False

    # Issue associations
    issue_ids: list[str] = field(default_factory=list)
    primary_issue_id: str | None = None

    # Analysis results
    branch_type: str | None = None  # feature, bugfix, hotfix, etc.
    lifecycle_stage: str = "unknown"  # created, active, merged, abandoned
    total_progress: int = 0

    # Statistics
    commits: list[CommitAnalysis] = field(default_factory=list)
    contributors: set[str] = field(default_factory=set)
    files_touched: set[str] = field(default_factory=set)


@dataclass
class RepositoryScanResult:
    """Results from comprehensive repository scanning."""

    # Scan metadata
    scan_date: datetime = field(default_factory=datetime.now)
    config: RepositoryScanConfig = field(default_factory=RepositoryScanConfig)
    repository_path: Path | None = None

    # Raw data
    commits: list[CommitAnalysis] = field(default_factory=list)
    branches: list[BranchAnalysis] = field(default_factory=list)

    # Associations discovered
    issue_associations: dict[str, list[str]] = field(
        default_factory=dict
    )  # issue_id -> commit_shas
    commit_associations: dict[str, list[str]] = field(
        default_factory=dict
    )  # commit_sha -> issue_ids

    # Statistics
    total_commits_scanned: int = 0
    total_branches_scanned: int = 0
    issues_with_commits: int = 0
    commits_with_issues: int = 0

    # Migration results
    issues_created: list[str] = field(default_factory=list)
    issues_updated: list[str] = field(default_factory=list)
    associations_created: int = 0

    # Performance metrics
    scan_duration_seconds: float = 0.0
    commits_per_second: float = 0.0

    # Errors and warnings
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class AdvancedRepositoryScanner:
    """Advanced repository scanning with comprehensive analysis and migration tools."""

    def __init__(
        self, roadmap_core: RoadmapCore, config: RepositoryScanConfig | None = None
    ):
        """Initialize the advanced repository scanner.

        Args:
            roadmap_core: Core roadmap functionality
            config: Scanning configuration
        """
        self.roadmap_core = roadmap_core
        self.config = config or RepositoryScanConfig()
        self.git = GitIntegration()
        self.ci_tracker = CITracker(roadmap_core)
        self.bulk_ops = BulkOperations(max_workers=self.config.max_workers)

        # Pattern compilation for performance
        self._compiled_patterns = self._compile_patterns()
        self._cache: dict[str, Any] = {}

    def _compile_patterns(self) -> dict[str, list[re.Pattern]]:
        """Compile regex patterns for efficient matching."""
        patterns = {
            "commit_type": [
                re.compile(r"^(feat|feature)(\([^)]+\))?:", re.IGNORECASE),
                re.compile(r"^(fix|bugfix)(\([^)]+\))?:", re.IGNORECASE),
                re.compile(r"^(docs?)(\([^)]+\))?:", re.IGNORECASE),
                re.compile(r"^(style)(\([^)]+\))?:", re.IGNORECASE),
                re.compile(r"^(refactor)(\([^)]+\))?:", re.IGNORECASE),
                re.compile(r"^(test)(\([^)]+\))?:", re.IGNORECASE),
                re.compile(r"^(chore)(\([^)]+\))?:", re.IGNORECASE),
            ],
            "breaking_change": [
                re.compile(r"BREAKING\s+CHANGE", re.IGNORECASE),
                re.compile(r"!:", re.IGNORECASE),
            ],
            "branch_type": [
                re.compile(r"^feature/", re.IGNORECASE),
                re.compile(r"^(feat|ft)/", re.IGNORECASE),
                re.compile(r"^(bug|fix|hotfix)/", re.IGNORECASE),
                re.compile(r"^(docs?)/", re.IGNORECASE),
                re.compile(r"^(refactor|refact)/", re.IGNORECASE),
                re.compile(r"^(test|testing)/", re.IGNORECASE),
                re.compile(r"^(chore|maintenance)/", re.IGNORECASE),
            ],
            "ignore": [
                re.compile(pattern, re.IGNORECASE)
                for pattern in self.config.ignore_patterns
            ],
        }

        # Add custom patterns
        if self.config.custom_patterns:
            patterns["custom"] = [
                re.compile(p, re.IGNORECASE) for p in self.config.custom_patterns
            ]

        return patterns

    def _should_ignore_commit(self, message: str) -> bool:
        """Check if commit should be ignored based on patterns."""
        for pattern in self._compiled_patterns["ignore"]:
            if pattern.search(message):
                return True
        return False

    def _analyze_commit_type(self, message: str) -> str | None:
        """Determine commit type from message."""
        for pattern in self._compiled_patterns["commit_type"]:
            match = pattern.search(message)
            if match:
                return match.group(1).lower()
        return None

    def _analyze_branch_type(self, branch_name: str) -> str | None:
        """Determine branch type from name."""
        for i, pattern in enumerate(self._compiled_patterns["branch_type"]):
            if pattern.search(branch_name):
                types = [
                    "feature",
                    "feature",
                    "bugfix",
                    "docs",
                    "refactor",
                    "test",
                    "chore",
                ]
                return types[i] if i < len(types) else "other"
        return None

    def _get_commit_stats(self, sha: str) -> tuple[int, int, int]:
        """Get commit statistics (files changed, lines added, lines deleted)."""
        try:
            result = subprocess.run(
                ["git", "show", "--numstat", "--format=", sha],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.roadmap_core.root_path,
            )

            files_changed = 0
            lines_added = 0
            lines_deleted = 0

            for line in result.stdout.strip().split("\n"):
                if line and "\t" in line:
                    parts = line.split("\t")
                    if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                        files_changed += 1
                        lines_added += int(parts[0])
                        lines_deleted += int(parts[1])

            return files_changed, lines_added, lines_deleted

        except (subprocess.CalledProcessError, ValueError):
            return 0, 0, 0

    def _get_commit_details(self, sha: str) -> CommitAnalysis | None:
        """Get detailed analysis of a single commit."""
        try:
            # Get commit info
            result = subprocess.run(
                ["git", "show", "--format=%H|%s|%an|%ae|%ct|%P", "--name-only", sha],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.roadmap_core.root_path,
            )

            lines = result.stdout.strip().split("\n")
            if not lines:
                return None

            # Parse commit metadata
            header = lines[0].split("|")
            if len(header) < 6:
                return None

            commit_sha, message, author, author_email, timestamp_str, parents = header
            commit_date = datetime.fromtimestamp(int(timestamp_str))
            parent_commits = parents.split() if parents else []

            # Skip if should ignore
            if self._should_ignore_commit(message):
                return None

            # Get file statistics
            files_changed, lines_added, lines_deleted = self._get_commit_stats(sha)

            # Create analysis object
            analysis = CommitAnalysis(
                sha=commit_sha,
                message=message,
                author=author,
                author_email=author_email,
                date=commit_date,
                commit_type=self._analyze_commit_type(message),
                breaking_change=any(
                    p.search(message)
                    for p in self._compiled_patterns["breaking_change"]
                ),
                files_changed=files_changed,
                lines_added=lines_added,
                lines_deleted=lines_deleted,
                is_merge_commit=len(parent_commits) > 1,
                parent_commits=parent_commits,
            )

            # Extract issue associations
            analysis.issue_ids = self.ci_tracker.extract_issue_ids_from_commit(message)

            # Extract progress markers
            progress = self.ci_tracker.parse_progress_marker(message)
            if progress is not None:
                analysis.progress_markers.append(progress)

            # Check for completion markers
            for issue_id in analysis.issue_ids:
                if self.ci_tracker.parse_completion_marker(message, issue_id):
                    analysis.completion_markers.append(issue_id)

            return analysis

        except (subprocess.CalledProcessError, ValueError, IndexError) as e:
            logger.warning(f"Failed to analyze commit {sha}: {e}")
            return None

    def scan_commit_history(
        self, max_commits: int | None = None
    ) -> list[CommitAnalysis]:
        """Scan repository commit history with detailed analysis.

        Args:
            max_commits: Maximum commits to scan (uses config default if None)

        Returns:
            List of analyzed commits
        """
        max_commits = max_commits or self.config.max_commits
        commits = []

        try:
            # Build git log command
            cmd = ["git", "log", "--format=%H"]

            if max_commits > 0:
                cmd.append(f"--max-count={max_commits}")

            if self.config.since_date:
                cmd.append(f"--since={self.config.since_date.isoformat()}")

            if self.config.until_date:
                cmd.append(f"--until={self.config.until_date.isoformat()}")

            # Get commit SHAs
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                cwd=self.roadmap_core.root_path,
            )
            commit_shas = [
                sha.strip() for sha in result.stdout.strip().split("\n") if sha.strip()
            ]

            logger.info(f"Analyzing {len(commit_shas)} commits...")

            # Process commits
            if self.config.use_parallel_processing and len(commit_shas) > 10:
                # Parallel processing for large repositories
                with ThreadPoolExecutor(
                    max_workers=self.config.max_workers
                ) as executor:
                    future_to_sha = {
                        executor.submit(self._get_commit_details, sha): sha
                        for sha in commit_shas
                    }

                    for future in as_completed(future_to_sha):
                        analysis = future.result()
                        if analysis:
                            commits.append(analysis)
            else:
                # Sequential processing for smaller repositories
                for sha in commit_shas:
                    analysis = self._get_commit_details(sha)
                    if analysis:
                        commits.append(analysis)

            # Sort by date (newest first)
            commits.sort(key=lambda c: c.date, reverse=True)

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to scan commit history: {e}")

        return commits

    def scan_branch_history(self) -> list[BranchAnalysis]:
        """Scan repository branch history with detailed analysis.

        Returns:
            List of analyzed branches
        """
        branches = []

        try:
            # Get all branches (local and remote) - use simpler format
            result = subprocess.run(
                ["git", "branch", "-a"],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.roadmap_core.root_path,
            )

            branch_info = {}
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    # Clean branch name (remove * and whitespace)
                    name = line.strip().lstrip("* ").strip()

                    # Skip remote HEAD references
                    if "HEAD ->" in name or name == "HEAD":
                        continue

                    # Skip remote tracking branches that duplicate locals
                    if name.startswith("remotes/origin/"):
                        local_name = name.replace("remotes/origin/", "")
                        if local_name not in ["main", "master"] and any(
                            b_name == local_name for b_name in branch_info.keys()
                        ):
                            continue
                        name = local_name

                    if name and name not in ["HEAD"]:
                        # Get branch details separately
                        try:
                            # Get last commit info for this branch
                            commit_result = subprocess.run(
                                ["git", "log", "-1", "--format=%H|%ct", name],
                                capture_output=True,
                                text=True,
                                check=True,
                                cwd=self.roadmap_core.root_path,
                            )

                            if commit_result.stdout.strip():
                                commit_info = commit_result.stdout.strip().split("|")
                                if len(commit_info) >= 2:
                                    head_sha = commit_info[0]
                                    timestamp = int(commit_info[1])
                                    last_commit_date = datetime.fromtimestamp(timestamp)
                                else:
                                    head_sha = None
                                    last_commit_date = None
                            else:
                                head_sha = None
                                last_commit_date = None

                        except (subprocess.CalledProcessError, ValueError, IndexError):
                            head_sha = None
                            last_commit_date = None

                        branch_info[name] = {
                            "name": name,
                            "last_commit_date": last_commit_date,
                            "head_commit": head_sha,
                        }

            logger.info(f"Analyzing {len(branch_info)} branches...")

            # Analyze each branch
            for branch_name, info in branch_info.items():
                try:
                    analysis = BranchAnalysis(
                        name=branch_name,
                        head_commit=info["head_commit"],
                        last_commit_date=info["last_commit_date"],
                        branch_type=self._analyze_branch_type(branch_name),
                    )

                    # Extract issue IDs from branch name
                    analysis.issue_ids = self.ci_tracker.extract_issue_ids_from_branch(
                        branch_name
                    )
                    if analysis.issue_ids:
                        analysis.primary_issue_id = analysis.issue_ids[0]

                    # Get branch statistics
                    if analysis.head_commit:
                        try:
                            # Get commit count
                            count_result = subprocess.run(
                                ["git", "rev-list", "--count", analysis.head_commit],
                                capture_output=True,
                                text=True,
                                check=True,
                                cwd=self.roadmap_core.root_path,
                            )
                            analysis.commit_count = int(count_result.stdout.strip())
                        except (subprocess.CalledProcessError, ValueError):
                            analysis.commit_count = 0
                    else:
                        analysis.commit_count = 0

                    # Check if merged
                    if analysis.head_commit:
                        try:
                            merge_check = subprocess.run(
                                [
                                    "git",
                                    "merge-base",
                                    "--is-ancestor",
                                    analysis.head_commit,
                                    "HEAD",
                                ],
                                capture_output=True,
                                check=False,
                                cwd=self.roadmap_core.root_path,
                            )
                            analysis.is_merged = merge_check.returncode == 0
                        except subprocess.CalledProcessError:
                            analysis.is_merged = False
                    else:
                        analysis.is_merged = False

                    # Determine lifecycle stage
                    if analysis.is_merged:
                        analysis.lifecycle_stage = "merged"
                    elif branch_name in ["main", "master", "develop", "development"]:
                        analysis.lifecycle_stage = "main"
                    elif (
                        analysis.last_commit_date
                        and analysis.last_commit_date
                        < datetime.now() - timedelta(days=30)
                    ):
                        analysis.lifecycle_stage = "stale"
                    else:
                        analysis.lifecycle_stage = "active"

                    branches.append(analysis)

                except Exception as e:
                    logger.warning(f"Failed to analyze branch {branch_name}: {e}")

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to scan branch history: {e}")

        return branches

    def perform_comprehensive_scan(self) -> RepositoryScanResult:
        """Perform comprehensive repository analysis.

        Returns:
            Complete scan results with analysis and statistics
        """
        start_time = datetime.now()

        result = RepositoryScanResult(
            scan_date=start_time,
            config=self.config,
            repository_path=self.roadmap_core.root_path,
        )

        try:
            logger.info("Starting comprehensive repository scan...")

            # Scan commits
            logger.info("Scanning commit history...")
            result.commits = self.scan_commit_history()
            result.total_commits_scanned = len(result.commits)

            # Scan branches
            logger.info("Scanning branch history...")
            result.branches = self.scan_branch_history()
            result.total_branches_scanned = len(result.branches)

            # Build associations
            logger.info("Building issue associations...")
            for commit in result.commits:
                if commit.issue_ids:
                    result.commits_with_issues += 1
                    result.commit_associations[commit.sha] = commit.issue_ids

                    for issue_id in commit.issue_ids:
                        if issue_id not in result.issue_associations:
                            result.issue_associations[issue_id] = []
                        result.issue_associations[issue_id].append(commit.sha)

            result.issues_with_commits = len(result.issue_associations)

            # Finalize timing
            end_time = datetime.now()
            result.scan_duration_seconds = (end_time - start_time).total_seconds()

            if result.scan_duration_seconds > 0:
                result.commits_per_second = (
                    result.total_commits_scanned / result.scan_duration_seconds
                )

            logger.info(f"Scan completed in {result.scan_duration_seconds:.2f}s")
            logger.info(
                f"Found {result.issues_with_commits} issues with {result.commits_with_issues} commits"
            )

        except Exception as e:
            error_msg = f"Scan failed: {e}"
            result.errors.append(error_msg)
            logger.error(error_msg)

        return result

    def migrate_existing_project(
        self, create_issues: bool = False, auto_link: bool = True
    ) -> BulkOperationResult:
        """Migrate an existing project to roadmap tracking.

        Args:
            create_issues: Whether to create missing issues found in commits
            auto_link: Whether to automatically link existing commits to issues

        Returns:
            Migration operation results
        """
        migration_result = BulkOperationResult()
        migration_result.total_files = 1  # The repository itself

        try:
            logger.info("Starting project migration...")

            # Perform comprehensive scan
            scan_result = self.perform_comprehensive_scan()

            if scan_result.errors:
                for error in scan_result.errors:
                    migration_result.add_failure(self.roadmap_core.root_path, error)
                return migration_result

            # Create missing issues if requested
            if create_issues:
                logger.info("Creating missing issues...")
                created_count = 0

                for issue_id, commit_shas in scan_result.issue_associations.items():
                    # Check if issue exists
                    issue_file = self.roadmap_core.issues_dir / f"{issue_id}.yaml"

                    if not issue_file.exists():
                        # Create issue from commit history
                        commits_for_issue = [
                            c for c in scan_result.commits if issue_id in c.issue_ids
                        ]

                        if commits_for_issue:
                            # Use the first commit for issue details
                            first_commit = min(commits_for_issue, key=lambda c: c.date)

                            # Infer issue type from commit types
                            commit_types = [
                                c.commit_type
                                for c in commits_for_issue
                                if c.commit_type
                            ]
                            if "fix" in commit_types:
                                issue_type = IssueType.BUG
                            elif "feat" in commit_types:
                                issue_type = IssueType.FEATURE
                            else:
                                issue_type = IssueType.OTHER

                            # Create git_commits in proper format
                            git_commits = []
                            for commit in commits_for_issue:
                                git_commits.append(
                                    {
                                        "hash": commit.sha,
                                        "message": commit.message,
                                        "date": commit.date.isoformat(),
                                        "progress": commit.progress_markers[0]
                                        if commit.progress_markers
                                        else 0,
                                    }
                                )

                            # Create issue
                            issue = Issue(
                                id=issue_id,
                                title=f"Auto-created from commit: {first_commit.message[:50]}...",
                                issue_type=issue_type,
                                status=Status.DONE
                                if any(
                                    issue_id in c.completion_markers
                                    for c in commits_for_issue
                                )
                                else Status.IN_PROGRESS,
                                priority=Priority.MEDIUM,
                                created_date=first_commit.date.isoformat(),
                                git_commits=git_commits,
                            )

                            # Save issue
                            try:
                                IssueParser.save_issue_file(issue, issue_file)
                                created_count += 1
                                migration_result.add_success(
                                    issue_file,
                                    {
                                        "action": "created_issue",
                                        "issue_id": issue_id,
                                        "commits": len(commit_shas),
                                    },
                                )
                            except Exception as e:
                                migration_result.add_warning(
                                    issue_file,
                                    f"Failed to create issue {issue_id}: {e}",
                                )

                logger.info(f"Created {created_count} issues")
                migration_result.results.append(
                    {"action": "issues_created", "count": created_count}
                )

            # Link existing commits if requested
            if auto_link:
                logger.info("Linking commits to existing issues...")
                linked_count = 0

                for issue_id, commit_shas in scan_result.issue_associations.items():
                    issue_file = self.roadmap_core.issues_dir / f"{issue_id}.yaml"

                    if issue_file.exists():
                        try:
                            issue = IssueParser.parse_issue_file(issue_file)

                            # Add new commits that aren't already linked
                            existing_commit_hashes = {
                                c.get("hash", "") for c in (issue.git_commits or [])
                            }
                            new_commit_shas = [
                                sha
                                for sha in commit_shas
                                if sha not in existing_commit_hashes
                            ]

                            if new_commit_shas:
                                # Convert new commits to proper format
                                commits_for_issue = [
                                    c
                                    for c in scan_result.commits
                                    if c.sha in new_commit_shas
                                    and issue_id in c.issue_ids
                                ]
                                for commit in commits_for_issue:
                                    issue.git_commits.append(
                                        {
                                            "hash": commit.sha,
                                            "message": commit.message,
                                            "date": commit.date.isoformat(),
                                            "progress": commit.progress_markers[0]
                                            if commit.progress_markers
                                            else 0,
                                        }
                                    )
                                IssueParser.save_issue_file(issue, issue_file)
                                linked_count += len(new_commit_shas)

                                migration_result.add_success(
                                    issue_file,
                                    {
                                        "action": "linked_commits",
                                        "issue_id": issue_id,
                                        "new_commits": len(new_commit_shas),
                                    },
                                )

                        except Exception as e:
                            migration_result.add_warning(
                                issue_file,
                                f"Failed to link commits to issue {issue_id}: {e}",
                            )

                logger.info(f"Linked {linked_count} commits to existing issues")
                # Record associations created in the success data instead\n                linked_associations = linked_count

            # Record overall success
            migration_result.add_success(
                self.roadmap_core.root_path,
                {
                    "scan_results": {
                        "commits_scanned": scan_result.total_commits_scanned,
                        "branches_scanned": scan_result.total_branches_scanned,
                        "issues_found": scan_result.issues_with_commits,
                        "scan_duration": scan_result.scan_duration_seconds,
                    }
                },
            )

        except Exception as e:
            migration_result.add_failure(self.roadmap_core.root_path, str(e))

        finally:
            migration_result.finalize()

        return migration_result

    def export_scan_results(
        self, scan_result: RepositoryScanResult, output_file: Path | None = None
    ) -> Path:
        """Export scan results to JSON file.

        Args:
            scan_result: Scan results to export
            output_file: Output file path (auto-generated if None)

        Returns:
            Path to exported file
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = (
                self.roadmap_core.artifacts_dir / f"repository_scan_{timestamp}.json"
            )

        # Ensure artifacts directory exists
        ensure_directory_exists(output_file.parent)

        # Convert to serializable format
        export_data = {
            "scan_metadata": {
                "scan_date": scan_result.scan_date.isoformat(),
                "repository_path": str(scan_result.repository_path),
                "scan_duration_seconds": scan_result.scan_duration_seconds,
                "commits_per_second": scan_result.commits_per_second,
            },
            "statistics": {
                "total_commits_scanned": scan_result.total_commits_scanned,
                "total_branches_scanned": scan_result.total_branches_scanned,
                "issues_with_commits": scan_result.issues_with_commits,
                "commits_with_issues": scan_result.commits_with_issues,
                "associations_created": scan_result.associations_created,
            },
            "commits": [
                {
                    "sha": c.sha,
                    "message": c.message,
                    "author": c.author,
                    "date": c.date.isoformat(),
                    "issue_ids": c.issue_ids,
                    "commit_type": c.commit_type,
                    "files_changed": c.files_changed,
                    "lines_added": c.lines_added,
                    "lines_deleted": c.lines_deleted,
                    "progress_markers": c.progress_markers,
                    "completion_markers": c.completion_markers,
                }
                for c in scan_result.commits
            ],
            "branches": [
                {
                    "name": b.name,
                    "issue_ids": b.issue_ids,
                    "branch_type": b.branch_type,
                    "lifecycle_stage": b.lifecycle_stage,
                    "commit_count": b.commit_count,
                    "is_merged": b.is_merged,
                    "last_commit_date": b.last_commit_date.isoformat()
                    if b.last_commit_date
                    else None,
                }
                for b in scan_result.branches
            ],
            "associations": {
                "issue_to_commits": scan_result.issue_associations,
                "commit_to_issues": scan_result.commit_associations,
            },
            "errors": scan_result.errors,
            "warnings": scan_result.warnings,
        }

        with open(output_file, "w") as f:
            json.dump(export_data, f, indent=2, default=str)

        logger.info(f"Scan results exported to {output_file}")
        return output_file


# Global instance for easy access
def create_repository_scanner(
    roadmap_core: RoadmapCore, config: RepositoryScanConfig | None = None
) -> AdvancedRepositoryScanner:
    """Create a repository scanner instance."""
    return AdvancedRepositoryScanner(roadmap_core, config)
