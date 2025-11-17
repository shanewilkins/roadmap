"""Roadmap curation tools for identifying and managing orphaned issues and milestones."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from roadmap.core import RoadmapCore
from roadmap.models import (
    Issue,
    IssueType,
    Milestone,
    MilestoneStatus,
    Priority,
    Status,
)
from roadmap.timezone_utils import ensure_timezone_aware, now_utc


class OrphanageType(Enum):
    """Types of orphaned items."""

    UNASSIGNED_ISSUE = "unassigned_issue"  # Issue with no milestone
    INVALID_MILESTONE = "invalid_milestone"  # Issue references non-existent milestone
    ORPHANED_MILESTONE = "orphaned_milestone"  # Milestone with structural problems
    OLD_ORPHAN = "old_orphan"  # Orphaned for extended period


class MilestoneOrphanageReason(Enum):
    """Specific reasons why a milestone is orphaned."""

    EMPTY = "empty"  # Milestone has no issues assigned
    UNASSIGNED = "unassigned"  # Milestone not assigned to any roadmap
    STALE = "stale"  # Milestone hasn't been updated recently
    NO_PROGRESS = "no_progress"  # All issues are stale or blocked


@dataclass
class OrphanedItem:
    """Represents an orphaned item with metadata."""

    item_type: str  # "issue" or "milestone"
    item_id: str
    title: str
    orphanage_type: OrphanageType
    created: datetime
    updated: datetime
    priority: Priority | None = None
    status: Status | None = None
    assignee: str | None = None
    issue_type: IssueType | None = None
    milestone_name: str | None = None
    orphaned_days: int = 0
    recommendations: list[str] = None
    orphanage_reasons: list[str] = (
        None  # For milestones: specific reasons (empty, unassigned, etc.)
    )

    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []
        if self.orphanage_reasons is None:
            self.orphanage_reasons = []


@dataclass
class CurationReport:
    """Comprehensive curation analysis report."""

    total_issues: int
    total_milestones: int
    orphaned_issues: list[OrphanedItem]
    orphaned_milestones: list[
        OrphanedItem
    ]  # Now includes all milestone problems with reasons
    invalid_references: list[OrphanedItem]
    backlog_size: int
    recommendations: list[str]
    generated_at: datetime
    summary_stats: dict[str, Any]


class RoadmapCurator:
    """Manages curation of roadmap data, identifying and handling orphaned items."""

    def __init__(self, core: RoadmapCore):
        """Initialize the curator with a roadmap core instance."""
        self.core = core
        self.orphan_threshold_days = 30  # Days to consider item "old orphan"

    def analyze_orphaned_items(
        self,
        include_backlog: bool = False,
        min_age_days: int = 0,
        max_age_days: int | None = None,
    ) -> CurationReport:
        """Perform comprehensive analysis of orphaned items.

        Args:
            include_backlog: Whether to include backlog items as orphaned
            min_age_days: Minimum age in days for items to be considered
            max_age_days: Maximum age in days for items to be considered

        Returns:
            CurationReport with detailed analysis
        """
        if not self.core.is_initialized():
            raise ValueError("Roadmap not initialized")

        all_issues = self.core.list_issues()
        all_milestones = self.core.list_milestones()

        # Detect orphaned issues
        orphaned_issues = self._detect_orphaned_issues(
            all_issues, all_milestones, include_backlog, min_age_days, max_age_days
        )

        # Detect orphaned milestones
        orphaned_milestones = self._detect_orphaned_milestones(
            all_milestones, all_issues, min_age_days, max_age_days
        )

        # Detect invalid milestone references
        invalid_references = self._detect_invalid_milestone_references(
            all_issues, all_milestones, min_age_days, max_age_days
        )

        # Detect problematic milestones (consolidates empty and unassigned)
        problematic_milestones = self._detect_problematic_milestones(
            all_milestones, all_issues, min_age_days, max_age_days
        )

        # Combine orphaned milestones with problematic milestones
        all_orphaned_milestones = orphaned_milestones + problematic_milestones

        # Generate recommendations
        recommendations = self._generate_recommendations(
            orphaned_issues, all_orphaned_milestones, invalid_references
        )

        # Calculate summary statistics
        summary_stats = self._calculate_summary_stats(
            all_issues, all_milestones, orphaned_issues, orphaned_milestones
        )

        backlog_size = len([issue for issue in all_issues if issue.is_backlog])

        return CurationReport(
            total_issues=len(all_issues),
            total_milestones=len(all_milestones),
            orphaned_issues=orphaned_issues,
            orphaned_milestones=all_orphaned_milestones,
            invalid_references=invalid_references,
            backlog_size=backlog_size,
            recommendations=recommendations,
            generated_at=datetime.now(),
            summary_stats=summary_stats,
        )

    def _detect_orphaned_issues(
        self,
        issues: list[Issue],
        milestones: list[Milestone],
        include_backlog: bool,
        min_age_days: int,
        max_age_days: int | None,
    ) -> list[OrphanedItem]:
        """Detect issues that are orphaned."""
        orphaned = []
        milestone_names = {m.name for m in milestones}
        now = now_utc()

        for issue in issues:
            # Skip if age filters don't match - ensure both datetimes are timezone-aware
            issue_created = ensure_timezone_aware(issue.created)
            age_days = (now - issue_created).days
            if age_days < min_age_days:
                continue
            if max_age_days is not None and age_days > max_age_days:
                continue

            orphanage_type = None
            recommendations = []

            # Check if issue is in backlog (no milestone)
            if issue.is_backlog:
                if include_backlog:
                    orphanage_type = OrphanageType.UNASSIGNED_ISSUE
                    recommendations.extend(
                        self._get_issue_assignment_recommendations(issue, milestones)
                    )
                else:
                    # Skip backlog items if not including them
                    continue

            # Check if issue references invalid milestone
            elif issue.milestone and issue.milestone not in milestone_names:
                orphanage_type = OrphanageType.INVALID_MILESTONE
                recommendations.append(f"Milestone '{issue.milestone}' does not exist")
                recommendations.extend(
                    self._get_issue_assignment_recommendations(issue, milestones)
                )

            # Check if old orphan
            elif age_days > self.orphan_threshold_days and issue.is_backlog:
                orphanage_type = OrphanageType.OLD_ORPHAN
                recommendations.append(f"Issue has been orphaned for {age_days} days")
                recommendations.extend(
                    self._get_issue_assignment_recommendations(issue, milestones)
                )

            if orphanage_type:
                orphaned.append(
                    OrphanedItem(
                        item_type="issue",
                        item_id=issue.id,
                        title=issue.title,
                        orphanage_type=orphanage_type,
                        created=issue.created,
                        updated=issue.updated,
                        priority=issue.priority,
                        status=issue.status,
                        assignee=issue.assignee,
                        issue_type=issue.issue_type,
                        milestone_name=issue.milestone,
                        orphaned_days=age_days,
                        recommendations=recommendations,
                    )
                )

        return orphaned

    def _detect_orphaned_milestones(
        self,
        milestones: list[Milestone],
        issues: list[Issue],
        min_age_days: int,
        max_age_days: int | None,
    ) -> list[OrphanedItem]:
        """Detect milestones that are orphaned (no assigned issues)."""
        orphaned = []
        now = now_utc()

        for milestone in milestones:
            milestone_created = ensure_timezone_aware(milestone.created)
            age_days = (now - milestone_created).days
            if age_days < min_age_days:
                continue
            if max_age_days is not None and age_days > max_age_days:
                continue

            # Count issues assigned to this milestone
            assigned_issues = [
                issue for issue in issues if issue.milestone == milestone.name
            ]

            if not assigned_issues:
                recommendations = [
                    "Milestone has no assigned issues",
                    "Consider assigning relevant issues or archiving milestone",
                ]

                if milestone.status == MilestoneStatus.OPEN and age_days > 7:
                    recommendations.append("Consider closing if no longer needed")

                orphaned.append(
                    OrphanedItem(
                        item_type="milestone",
                        item_id=milestone.name,
                        title=milestone.name,
                        orphanage_type=OrphanageType.ORPHANED_MILESTONE,
                        created=milestone.created,
                        updated=milestone.updated,
                        orphaned_days=age_days,
                        recommendations=recommendations,
                        orphanage_reasons=[
                            "empty"
                        ],  # This method only detects empty milestones
                    )
                )

        return orphaned

    def _detect_invalid_milestone_references(
        self,
        issues: list[Issue],
        milestones: list[Milestone],
        min_age_days: int,
        max_age_days: int | None,
    ) -> list[OrphanedItem]:
        """Detect issues that reference non-existent milestones."""
        invalid = []
        milestone_names = {m.name for m in milestones}
        now = now_utc()

        for issue in issues:
            issue_created = ensure_timezone_aware(issue.created)
            age_days = (now - issue_created).days
            if age_days < min_age_days:
                continue
            if max_age_days is not None and age_days > max_age_days:
                continue

            if issue.milestone and issue.milestone not in milestone_names:
                recommendations = [
                    f"References non-existent milestone: '{issue.milestone}'",
                    "Move to backlog or assign to existing milestone",
                ]
                recommendations.extend(
                    self._get_issue_assignment_recommendations(issue, milestones)
                )

                invalid.append(
                    OrphanedItem(
                        item_type="issue",
                        item_id=issue.id,
                        title=issue.title,
                        orphanage_type=OrphanageType.INVALID_MILESTONE,
                        created=issue.created,
                        updated=issue.updated,
                        priority=issue.priority,
                        status=issue.status,
                        assignee=issue.assignee,
                        issue_type=issue.issue_type,
                        milestone_name=issue.milestone,
                        orphaned_days=age_days,
                        recommendations=recommendations,
                    )
                )

        return invalid

    def _detect_empty_milestones(
        self,
        milestones: list[Milestone],
        issues: list[Issue],
        min_age_days: int,
        max_age_days: int | None,
    ) -> list[OrphanedItem]:
        """Detect milestones with no issues assigned (legacy method - use _detect_problematic_milestones)."""
        return self._detect_orphaned_milestones(
            milestones, issues, min_age_days, max_age_days
        )

    def _detect_unassigned_milestones(
        self, milestones: list[Milestone], min_age_days: int, max_age_days: int | None
    ) -> list[OrphanedItem]:
        """Detect milestones that are not assigned to any roadmap (legacy method - use _detect_problematic_milestones)."""
        unassigned = []
        now = now_utc()

        # Get all milestones assigned to roadmaps
        assigned_milestone_names = self._get_roadmap_assigned_milestones()

        for milestone in milestones:
            milestone_created = ensure_timezone_aware(milestone.created)
            age_days = (now - milestone_created).days
            if age_days < min_age_days:
                continue
            if max_age_days is not None and age_days > max_age_days:
                continue

            if milestone.name not in assigned_milestone_names:
                recommendations = [
                    "Milestone not assigned to any roadmap",
                    "Consider assigning to a roadmap or archiving milestone",
                ]

                if milestone.status == MilestoneStatus.OPEN and age_days > 14:
                    recommendations.append(
                        "Consider assigning to roadmap or closing if no longer needed"
                    )

                unassigned.append(
                    OrphanedItem(
                        item_type="milestone",
                        item_id=milestone.name,
                        title=milestone.name,
                        orphanage_type=OrphanageType.ORPHANED_MILESTONE,
                        created=milestone.created,
                        updated=milestone.updated,
                        orphaned_days=age_days,
                        recommendations=recommendations,
                        orphanage_reasons=["unassigned"],
                    )
                )

        return unassigned

    def _detect_problematic_milestones(
        self,
        milestones: list[Milestone],
        issues: list[Issue],
        min_age_days: int,
        max_age_days: int | None,
    ) -> list[OrphanedItem]:
        """Detect milestones with structural problems (empty, unassigned, etc.)."""
        problematic = {}  # Use dict to consolidate milestones by name
        now = now_utc()

        # Get all milestones assigned to roadmaps
        assigned_milestone_names = self._get_roadmap_assigned_milestones()

        for milestone in milestones:
            milestone_created = ensure_timezone_aware(milestone.created)
            age_days = (now - milestone_created).days
            if age_days < min_age_days:
                continue
            if max_age_days is not None and age_days > max_age_days:
                continue

            reasons = []
            recommendations = []

            # Check if milestone is empty (no assigned issues)
            assigned_issues = [
                issue for issue in issues if issue.milestone == milestone.name
            ]
            if not assigned_issues:
                reasons.append("empty")
                recommendations.append("Milestone has no assigned issues")

            # Check if milestone is unassigned to any roadmap
            if milestone.name not in assigned_milestone_names:
                reasons.append("unassigned")
                recommendations.append("Milestone not assigned to any roadmap")

            # If milestone has problems, add it to the list
            if reasons:
                # Generate consolidated recommendations
                base_recommendations = recommendations.copy()
                if "empty" in reasons and "unassigned" in reasons:
                    base_recommendations.append(
                        "Consider assigning to a roadmap and adding relevant issues"
                    )
                elif "empty" in reasons:
                    base_recommendations.append(
                        "Consider assigning relevant issues or archiving milestone"
                    )
                elif "unassigned" in reasons:
                    base_recommendations.append(
                        "Consider assigning to a roadmap or archiving milestone"
                    )

                if milestone.status == MilestoneStatus.OPEN and age_days > 14:
                    base_recommendations.append("Consider closing if no longer needed")

                problematic[milestone.name] = OrphanedItem(
                    item_type="milestone",
                    item_id=milestone.name,
                    title=milestone.name,
                    orphanage_type=OrphanageType.ORPHANED_MILESTONE,
                    created=milestone.created,
                    updated=milestone.updated,
                    orphaned_days=age_days,
                    recommendations=base_recommendations,
                    orphanage_reasons=reasons,
                )

        return list(problematic.values())

    def _get_roadmap_assigned_milestones(self) -> set[str]:
        """Get all milestone names that are assigned to roadmaps."""
        assigned_milestones = set()

        try:
            roadmaps_dir = self.core.roadmap_dir / "roadmaps"
            if not roadmaps_dir.exists():
                return assigned_milestones

            # Get all roadmap files
            roadmap_files = list(roadmaps_dir.glob("*.md"))

            for file_path in roadmap_files:
                try:
                    content = file_path.read_text()
                    # Extract YAML frontmatter
                    if content.startswith("---"):
                        yaml_end = content.find("---", 3)
                        if yaml_end != -1:
                            yaml_content = content[3:yaml_end]
                            metadata = yaml.safe_load(yaml_content)

                            # Get milestones assigned to this roadmap
                            milestones_list = metadata.get("milestones", [])
                            if isinstance(milestones_list, list):
                                assigned_milestones.update(milestones_list)

                except Exception:
                    # Skip files that can't be parsed
                    continue

        except Exception:
            # Return empty set if any error occurs
            pass

        return assigned_milestones

    def _get_issue_assignment_recommendations(
        self, issue: Issue, milestones: list[Milestone]
    ) -> list[str]:
        """Get smart recommendations for where to assign an issue."""
        recommendations = []

        # Find milestones based on priority matching
        high_priority_milestones = []
        open_milestones = []

        for milestone in milestones:
            if milestone.status == MilestoneStatus.OPEN:
                open_milestones.append(milestone)

        # Priority-based recommendations
        if issue.priority in [Priority.CRITICAL, Priority.HIGH]:
            recommendations.append(
                "Consider assigning to next milestone due to high priority"
            )

        # Type-based recommendations
        if issue.issue_type == IssueType.BUG:
            recommendations.append(
                "Bugs should typically be assigned to current sprint/milestone"
            )
        elif issue.issue_type == IssueType.FEATURE:
            recommendations.append("Features can be assigned to future milestones")

        # Due date recommendations
        recent_milestones = [
            m for m in open_milestones if m.due_date and m.due_date > now_utc()
        ]
        if recent_milestones:
            next_milestone = min(recent_milestones, key=lambda m: m.due_date)
            recommendations.append(
                f"Consider assigning to '{next_milestone.name}' (next due: {next_milestone.due_date.strftime('%Y-%m-%d')})"
            )

        # Fallback recommendations if no specific ones were generated
        if not recommendations:
            if open_milestones:
                recommendations.append(
                    f"Consider assigning to one of {len(open_milestones)} available milestone(s)"
                )
            else:
                recommendations.append("Create a milestone or move to backlog")

        return recommendations

    def _generate_recommendations(
        self,
        orphaned_issues: list[OrphanedItem],
        orphaned_milestones: list[OrphanedItem],
        invalid_references: list[OrphanedItem],
    ) -> list[str]:
        """Generate high-level recommendations for roadmap curation."""
        recommendations = []

        total_orphaned = len(orphaned_issues) + len(invalid_references)

        if total_orphaned > 0:
            recommendations.append(
                f"Found {total_orphaned} orphaned issues that need attention"
            )

        if orphaned_issues:
            critical_orphaned = [
                item for item in orphaned_issues if item.priority == Priority.CRITICAL
            ]
            if critical_orphaned:
                recommendations.append(
                    f"{len(critical_orphaned)} critical issues are orphaned - assign immediately"
                )

        if invalid_references:
            recommendations.append(
                f"{len(invalid_references)} issues reference invalid milestones - needs correction"
            )

        # Count problematic milestones by type
        problematic_milestones = [
            item
            for item in orphaned_milestones
            if item.orphanage_type == OrphanageType.ORPHANED_MILESTONE
        ]
        if problematic_milestones:
            empty_count = len(
                [
                    item
                    for item in problematic_milestones
                    if "empty" in item.orphanage_reasons
                ]
            )
            unassigned_count = len(
                [
                    item
                    for item in problematic_milestones
                    if "unassigned" in item.orphanage_reasons
                ]
            )

            if empty_count > 0:
                recommendations.append(
                    f"{empty_count} milestones have no issues - consider archiving or assigning issues"
                )
            if unassigned_count > 0:
                recommendations.append(
                    f"{unassigned_count} milestones not assigned to roadmaps - consider roadmap assignment or archival"
                )

        # Workflow recommendations
        old_orphans = [
            item
            for item in orphaned_issues
            if item.orphaned_days > self.orphan_threshold_days
        ]
        if old_orphans:
            recommendations.append(
                f"{len(old_orphans)} issues have been orphaned for over {self.orphan_threshold_days} days"
            )

        return recommendations

    def _calculate_summary_stats(
        self,
        all_issues: list[Issue],
        all_milestones: list[Milestone],
        orphaned_issues: list[OrphanedItem],
        orphaned_milestones: list[OrphanedItem],
    ) -> dict[str, Any]:
        """Calculate summary statistics for the curation report."""
        total_orphaned = len(orphaned_issues) + len(orphaned_milestones)
        orphan_percentage = (
            (total_orphaned / (len(all_issues) + len(all_milestones))) * 100
            if (len(all_issues) + len(all_milestones)) > 0
            else 0
        )

        # Priority distribution of orphaned issues
        priority_dist = {}
        for item in orphaned_issues:
            if item.priority:
                priority_dist[item.priority.value] = (
                    priority_dist.get(item.priority.value, 0) + 1
                )

        # Status distribution of orphaned issues
        status_dist = {}
        for item in orphaned_issues:
            if item.status:
                status_dist[item.status.value] = (
                    status_dist.get(item.status.value, 0) + 1
                )

        # Age analysis
        ages = [item.orphaned_days for item in orphaned_issues + orphaned_milestones]
        avg_orphan_age = sum(ages) / len(ages) if ages else 0

        return {
            "total_orphaned": total_orphaned,
            "orphan_percentage": round(orphan_percentage, 1),
            "priority_distribution": priority_dist,
            "status_distribution": status_dist,
            "average_orphan_age_days": round(avg_orphan_age, 1),
            "oldest_orphan_days": max(ages) if ages else 0,
            "critical_orphans": len(
                [item for item in orphaned_issues if item.priority == Priority.CRITICAL]
            ),
            "high_priority_orphans": len(
                [item for item in orphaned_issues if item.priority == Priority.HIGH]
            ),
        }

    def bulk_assign_to_milestone(
        self, issue_ids: list[str], milestone_name: str
    ) -> tuple[list[str], list[str]]:
        """Bulk assign multiple issues to a milestone.

        Args:
            issue_ids: List of issue IDs to assign
            milestone_name: Name of milestone to assign to (or None for backlog)

        Returns:
            Tuple of (successful_ids, failed_ids)
        """
        successful = []
        failed = []

        for issue_id in issue_ids:
            if self.core.move_issue_to_milestone(issue_id, milestone_name):
                successful.append(issue_id)
            else:
                failed.append(issue_id)

        return successful, failed

    def bulk_move_to_backlog(self, issue_ids: list[str]) -> tuple[list[str], list[str]]:
        """Bulk move multiple issues to backlog.

        Args:
            issue_ids: List of issue IDs to move to backlog

        Returns:
            Tuple of (successful_ids, failed_ids)
        """
        return self.bulk_assign_to_milestone(issue_ids, None)

    def suggest_milestone_assignments(
        self, orphaned_issues: list[OrphanedItem]
    ) -> dict[str, list[str]]:
        """Suggest milestone assignments for orphaned issues.

        Args:
            orphaned_issues: List of orphaned issues to analyze

        Returns:
            Dictionary mapping milestone names to suggested issue IDs
        """
        suggestions = {}
        milestones = self.core.list_milestones()
        open_milestones = [m for m in milestones if m.status == MilestoneStatus.OPEN]

        if not open_milestones:
            return suggestions

        # Sort milestones by due date (next due first)
        open_milestones.sort(key=lambda m: m.due_date if m.due_date else datetime.max)

        for item in orphaned_issues:
            if item.item_type != "issue":
                continue

            suggested_milestone = None

            # High priority issues go to next milestone
            if item.priority in [Priority.CRITICAL, Priority.HIGH]:
                suggested_milestone = open_milestones[0].name
            # Bugs go to current/next milestone
            elif item.issue_type == IssueType.BUG:
                suggested_milestone = open_milestones[0].name
            # Features can go to later milestones
            elif item.issue_type == IssueType.FEATURE and len(open_milestones) > 1:
                suggested_milestone = open_milestones[1].name
            # Default to next milestone
            else:
                suggested_milestone = open_milestones[0].name

            if suggested_milestone:
                if suggested_milestone not in suggestions:
                    suggestions[suggested_milestone] = []
                suggestions[suggested_milestone].append(item.item_id)

        return suggestions

    def export_curation_report(
        self, report: CurationReport, output_path: Path, format: str = "json"
    ) -> None:
        """Export curation report to file.

        Args:
            report: CurationReport to export
            output_path: Path to save the report
            format: Output format ("json", "csv", "markdown")
        """
        if format == "json":
            self._export_json_report(report, output_path)
        elif format == "csv":
            self._export_csv_report(report, output_path)
        elif format == "markdown":
            self._export_markdown_report(report, output_path)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _export_json_report(self, report: CurationReport, output_path: Path) -> None:
        """Export report as JSON."""
        import json

        # Convert report to dictionary for JSON serialization
        report_dict = {
            "total_issues": report.total_issues,
            "total_milestones": report.total_milestones,
            "backlog_size": report.backlog_size,
            "generated_at": report.generated_at.isoformat(),
            "summary_stats": report.summary_stats,
            "recommendations": report.recommendations,
            "orphaned_issues": [
                {
                    "item_id": item.item_id,
                    "title": item.title,
                    "orphanage_type": item.orphanage_type.value,
                    "priority": item.priority.value if item.priority else None,
                    "status": item.status.value if item.status else None,
                    "assignee": item.assignee,
                    "milestone_name": item.milestone_name,
                    "orphaned_days": item.orphaned_days,
                    "recommendations": item.recommendations,
                }
                for item in report.orphaned_issues
            ],
            "orphaned_milestones": [
                {
                    "item_id": item.item_id,
                    "title": item.title,
                    "orphanage_type": item.orphanage_type.value,
                    "orphaned_days": item.orphaned_days,
                    "orphanage_reasons": getattr(item, "orphanage_reasons", []),
                    "recommendations": item.recommendations,
                }
                for item in report.orphaned_milestones
            ],
        }

        with open(output_path, "w") as f:
            json.dump(report_dict, f, indent=2)

    def _export_csv_report(self, report: CurationReport, output_path: Path) -> None:
        """Export report as CSV."""
        import csv

        with open(output_path, "w", newline="") as f:
            writer = csv.writer(f)

            # Write header
            writer.writerow(
                [
                    "Type",
                    "ID",
                    "Title",
                    "Orphanage Type",
                    "Priority",
                    "Status",
                    "Assignee",
                    "Milestone",
                    "Orphaned Days",
                    "Recommendations",
                ]
            )

            # Write orphaned issues
            for item in report.orphaned_issues:
                writer.writerow(
                    [
                        item.item_type,
                        item.item_id,
                        item.title,
                        item.orphanage_type.value,
                        item.priority.value if item.priority else "",
                        item.status.value if item.status else "",
                        item.assignee or "",
                        item.milestone_name or "",
                        item.orphaned_days,
                        "; ".join(item.recommendations),
                    ]
                )

            # Write orphaned milestones
            for item in report.orphaned_milestones:
                writer.writerow(
                    [
                        item.item_type,
                        item.item_id,
                        item.title,
                        item.orphanage_type.value,
                        "",  # priority
                        "",  # status
                        "",  # assignee
                        "",  # milestone
                        item.orphaned_days,
                        "; ".join(item.recommendations),
                    ]
                )

            # Note: No separate processing needed for empty/unassigned milestones
            # since they are now included in the main orphaned_milestones list

    def _export_markdown_report(
        self, report: CurationReport, output_path: Path
    ) -> None:
        """Export report as Markdown."""
        content = f"""# Roadmap Curation Report

Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}

## Summary

- **Total Issues**: {report.total_issues}
- **Total Milestones**: {report.total_milestones}
- **Backlog Size**: {report.backlog_size}
- **Orphaned Items**: {report.summary_stats['total_orphaned']} ({report.summary_stats['orphan_percentage']}%)
- **Critical Orphans**: {report.summary_stats['critical_orphans']}

## Recommendations

"""

        for rec in report.recommendations:
            content += f"- {rec}\n"

        if report.orphaned_issues:
            content += "\n## Orphaned Issues\n\n"
            content += "| ID | Title | Type | Priority | Status | Orphaned Days | Recommendations |\n"
            content += "|---|---|---|---|---|---|---|\n"

            for item in report.orphaned_issues:
                recs = "; ".join(item.recommendations)
                content += f"| {item.item_id} | {item.title} | {item.orphanage_type.value} | {item.priority.value if item.priority else ''} | {item.status.value if item.status else ''} | {item.orphaned_days} | {recs} |\n"

        if report.orphaned_milestones:
            content += "\n## Problematic Milestones\n\n"
            content += "| Name | Type | Issues | Orphaned Days | Recommendations |\n"
            content += "|---|---|---|---|---|\n"

            for item in report.orphaned_milestones:
                recs = "; ".join(item.recommendations)
                issues = ", ".join(getattr(item, "orphanage_reasons", [])) or "N/A"
                content += f"| {item.item_id} | {item.orphanage_type.value} | {issues} | {item.orphaned_days} | {recs} |\n"

        with open(output_path, "w") as f:
            f.write(content)
