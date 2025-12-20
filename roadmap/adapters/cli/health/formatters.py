"""Output formatters for health scan results.

Provides formatters for different output styles:
- PlainTextFormatter: Human-readable, indented text (default)
- JSONFormatter: Structured JSON for automation/piping
- CSVFormatter: Comma-separated values for spreadsheets
"""

import json
from abc import ABC, abstractmethod
from typing import Any

from roadmap.core.services.dependency_analyzer import DependencyAnalysisResult
from roadmap.core.services.entity_health_scanner import (
    EntityHealthReport,
    HealthSeverity,
)


class HealthFormatter(ABC):
    """Abstract base for health report formatters."""

    @abstractmethod
    def format_entity_reports(self, reports: list[EntityHealthReport]) -> str:
        """Format entity health reports.

        Args:
            reports: List of entity reports to format

        Returns:
            Formatted string ready for output
        """

    @abstractmethod
    def format_dependency_analysis(self, analysis: DependencyAnalysisResult) -> str:
        """Format dependency analysis results.

        Args:
            analysis: Dependency analysis result

        Returns:
            Formatted string ready for output
        """

    @abstractmethod
    def format_summary(
        self,
        entity_reports: list[EntityHealthReport],
        dependency_analysis: DependencyAnalysisResult | None = None,
    ) -> str:
        """Format a summary of all results.

        Args:
            entity_reports: Entity health reports
            dependency_analysis: Optional dependency analysis

        Returns:
            Formatted summary string
        """


class PlainTextFormatter(HealthFormatter):
    """Human-readable plain text formatter with indentation."""

    def format_entity_reports(self, reports: list[EntityHealthReport]) -> str:
        """Format entity reports as indented plain text."""
        if not reports:
            return "No entities to report.\n"

        output = []

        # Group by entity type
        by_type = {}
        for report in reports:
            entity_type = report.entity_type.value
            if entity_type not in by_type:
                by_type[entity_type] = []
            by_type[entity_type].append(report)

        for entity_type in sorted(by_type.keys()):
            output.append(f"\n{entity_type.upper()}S ({len(by_type[entity_type])})")
            output.append("-" * 60)

            for report in sorted(by_type[entity_type], key=lambda r: r.entity_id):
                output.append(self._format_entity_report(report))

        return "\n".join(output)

    def format_dependency_analysis(self, analysis: DependencyAnalysisResult) -> str:
        """Format dependency analysis as plain text."""
        output = []

        output.append("\nDEPENDENCY ANALYSIS")
        output.append("-" * 60)
        output.append(f"Total issues: {analysis.total_issues}")
        output.append(f"Issues with dependencies: {analysis.issues_with_dependencies}")
        output.append(f"Issues with problems: {analysis.issues_with_problems}")

        if not analysis.problems and not analysis.circular_chains:
            output.append("\n✓ All dependencies are healthy!")
            return "\n".join(output)

        if analysis.circular_chains:
            output.append(
                f"\n⚠ CIRCULAR DEPENDENCIES ({len(analysis.circular_chains)}):"
            )
            for chain in analysis.circular_chains:
                chain_str = " → ".join(chain) + " → " + chain[0]
                output.append(f"  • {chain_str}")

        if analysis.problems:
            # Group problems by type
            by_type = {}
            for problem in analysis.problems:
                if problem.issue_type not in by_type:
                    by_type[problem.issue_type] = []
                by_type[problem.issue_type].append(problem)

            for prob_type in sorted(by_type.keys()):
                problems = by_type[prob_type]
                output.append(f"\n{prob_type.upper()} ({len(problems)}):")
                for problem in sorted(problems, key=lambda p: p.issue_id):
                    icon = self._severity_icon(problem.severity)
                    output.append(f"  {icon} {problem.issue_id}: {problem.message}")

        return "\n".join(output)

    def format_summary(
        self,
        entity_reports: list[EntityHealthReport],
        dependency_analysis: DependencyAnalysisResult | None = None,
    ) -> str:
        """Format summary of all results."""
        output = []

        output.append("\n" + "=" * 60)
        output.append("HEALTH SCAN SUMMARY")
        output.append("=" * 60)

        # Entity summary
        total_entities = len(entity_reports)
        healthy = sum(1 for r in entity_reports if r.is_healthy)
        degraded = sum(1 for r in entity_reports if r.is_degraded)
        unhealthy = total_entities - healthy - degraded

        output.append(f"\nEntities: {total_entities} total")
        output.append(f"  ✓ Healthy: {healthy}")
        output.append(f"  ⚠ Degraded: {degraded}")
        output.append(f"  ✗ Unhealthy: {unhealthy}")

        error_count = sum(r.error_count for r in entity_reports)
        warning_count = sum(r.warning_count for r in entity_reports)
        info_count = sum(r.info_count for r in entity_reports)

        output.append(f"\nIssues found: {error_count + warning_count + info_count}")
        output.append(f"  ✗ Errors: {error_count}")
        output.append(f"  ⚠ Warnings: {warning_count}")
        output.append(f"  ℹ Info: {info_count}")

        # Dependency summary
        if dependency_analysis:
            output.append("\nDependencies:")
            output.append(f"  Total issues: {dependency_analysis.total_issues}")
            output.append(
                f"  With dependencies: {dependency_analysis.issues_with_dependencies}"
            )
            output.append(
                f"  With problems: {dependency_analysis.issues_with_problems}"
            )

            if dependency_analysis.circular_chains:
                output.append(
                    f"  Circular chains: {len(dependency_analysis.circular_chains)}"
                )

        output.append("\n" + "=" * 60)
        return "\n".join(output)

    def _format_entity_report(self, report: EntityHealthReport) -> str:
        """Format a single entity report."""
        lines = []

        # Header
        status_badge = self._status_badge(report)
        lines.append(f"\n  {status_badge} {report.entity_title} ({report.entity_id})")
        lines.append(f"    Status: {report.status}")

        if not report.issues:
            lines.append("    Issues: None found ✓")
        else:
            lines.append(f"    Issues: {report.issue_count}")
            for issue in report.issues:
                icon = self._severity_icon(issue.severity.value)
                lines.append(f"      {icon} {issue.code}: {issue.message}")

        return "\n".join(lines)

    @staticmethod
    def _status_badge(report: EntityHealthReport) -> str:
        """Get status badge for entity."""
        if report.is_healthy:
            return "✓"
        elif report.is_degraded:
            return "⚠"
        else:
            return "✗"

    @staticmethod
    def _severity_icon(severity: str) -> str:
        """Get icon for severity level."""
        if severity == HealthSeverity.ERROR or severity == "error":
            return "✗"
        elif severity == HealthSeverity.WARNING or severity == "warning":
            return "⚠"
        elif severity == HealthSeverity.CRITICAL or severity == "critical":
            return "⚠"
        else:
            return "ℹ"


class JSONFormatter(HealthFormatter):
    """JSON formatter for machine-readable output."""

    def format_entity_reports(self, reports: list[EntityHealthReport]) -> str:
        """Format entity reports as JSON."""
        data = [self._report_to_dict(report) for report in reports]
        return json.dumps(data, indent=2, default=str)

    def format_dependency_analysis(self, analysis: DependencyAnalysisResult) -> str:
        """Format dependency analysis as JSON."""
        data = {
            "total_issues": analysis.total_issues,
            "issues_with_dependencies": analysis.issues_with_dependencies,
            "issues_with_problems": analysis.issues_with_problems,
            "problems": [
                {
                    "issue_id": p.issue_id,
                    "issue_type": p.issue_type,
                    "message": p.message,
                    "severity": p.severity,
                    "affected_issues": p.affected_issues,
                    "chain_length": p.chain_length,
                }
                for p in analysis.problems
            ],
            "circular_chains": analysis.circular_chains,
        }
        return json.dumps(data, indent=2, default=str)

    def format_summary(
        self,
        entity_reports: list[EntityHealthReport],
        dependency_analysis: DependencyAnalysisResult | None = None,
    ) -> str:
        """Format summary as JSON."""
        total_entities = len(entity_reports)
        healthy = sum(1 for r in entity_reports if r.is_healthy)
        degraded = sum(1 for r in entity_reports if r.is_degraded)
        unhealthy = total_entities - healthy - degraded

        error_count = sum(r.error_count for r in entity_reports)
        warning_count = sum(r.warning_count for r in entity_reports)
        info_count = sum(r.info_count for r in entity_reports)

        data = {
            "summary": {
                "total_entities": total_entities,
                "healthy": healthy,
                "degraded": degraded,
                "unhealthy": unhealthy,
                "total_issues": error_count + warning_count + info_count,
                "errors": error_count,
                "warnings": warning_count,
                "info": info_count,
            },
            "entities": [self._report_to_dict(r) for r in entity_reports],
        }

        if dependency_analysis:
            data["dependencies"] = {
                "total_issues": dependency_analysis.total_issues,
                "with_dependencies": dependency_analysis.issues_with_dependencies,
                "with_problems": dependency_analysis.issues_with_problems,
                "circular_chains": len(dependency_analysis.circular_chains),
            }

        return json.dumps(data, indent=2, default=str)

    @staticmethod
    def _report_to_dict(report: EntityHealthReport) -> dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "entity_id": report.entity_id,
            "entity_type": report.entity_type.value,
            "entity_title": report.entity_title,
            "status": report.status,
            "is_healthy": report.is_healthy,
            "is_degraded": report.is_degraded,
            "issue_count": report.issue_count,
            "error_count": report.error_count,
            "warning_count": report.warning_count,
            "info_count": report.info_count,
            "issues": [
                {
                    "code": issue.code,
                    "message": issue.message,
                    "severity": issue.severity.value,
                    "category": issue.category,
                    "details": issue.details,
                }
                for issue in report.issues
            ],
        }


class CSVFormatter(HealthFormatter):
    """CSV formatter for spreadsheet import."""

    def format_entity_reports(self, reports: list[EntityHealthReport]) -> str:
        """Format entity reports as CSV."""
        if not reports:
            return "entity_id,entity_type,entity_title,status,is_healthy,issue_count,error_count,warning_count,info_count\n"

        lines = [
            "entity_id,entity_type,entity_title,status,is_healthy,issue_count,error_count,warning_count,info_count"
        ]

        for report in reports:
            lines.append(
                f"{report.entity_id},{report.entity_type.value},{self._escape_csv(report.entity_title)},"
                f"{report.status},{report.is_healthy},{report.issue_count},"
                f"{report.error_count},{report.warning_count},{report.info_count}"
            )

        return "\n".join(lines)

    def format_dependency_analysis(self, analysis: DependencyAnalysisResult) -> str:
        """Format dependency analysis as CSV."""
        if not analysis.problems:
            return "issue_id,issue_type,message,severity,affected_issues\n"

        lines = ["issue_id,issue_type,message,severity,affected_issues"]

        for problem in analysis.problems:
            affected_str = ";".join(problem.affected_issues)
            lines.append(
                f'{problem.issue_id},{problem.issue_type},"{self._escape_csv(problem.message)}",'
                f"{problem.severity},{affected_str}"
            )

        return "\n".join(lines)

    def format_summary(
        self,
        entity_reports: list[EntityHealthReport],
        dependency_analysis: DependencyAnalysisResult | None = None,
    ) -> str:
        """Format summary as CSV with metadata section then entity data."""
        output = []

        # Metadata section
        total_entities = len(entity_reports)
        healthy = sum(1 for r in entity_reports if r.is_healthy)
        degraded = sum(1 for r in entity_reports if r.is_degraded)
        unhealthy = total_entities - healthy - degraded

        error_count = sum(r.error_count for r in entity_reports)
        warning_count = sum(r.warning_count for r in entity_reports)
        info_count = sum(r.info_count for r in entity_reports)

        output.append("# Health Scan Summary")
        output.append("metric,value")
        output.append(f"total_entities,{total_entities}")
        output.append(f"healthy,{healthy}")
        output.append(f"degraded,{degraded}")
        output.append(f"unhealthy,{unhealthy}")
        output.append(f"total_issues,{error_count + warning_count + info_count}")
        output.append(f"errors,{error_count}")
        output.append(f"warnings,{warning_count}")
        output.append(f"info,{info_count}")

        # Entity data section
        output.append("\n# Entity Details")
        output.append(self.format_entity_reports(entity_reports))

        return "\n".join(output)

    @staticmethod
    def _escape_csv(value: str) -> str:
        """Escape string for CSV (handle quotes and commas)."""
        if "," in value or '"' in value or "\n" in value:
            return f'"{value.replace(chr(34), chr(34) + chr(34))}"'
        return value


# Formatter factory
def get_formatter(format_type: str) -> HealthFormatter:
    """Get a formatter instance by name.

    Args:
        format_type: One of 'plain', 'json', 'csv'

    Returns:
        Appropriate formatter instance

    Raises:
        ValueError: If format_type is not recognized
    """
    format_map = {
        "plain": PlainTextFormatter,
        "text": PlainTextFormatter,
        "json": JSONFormatter,
        "csv": CSVFormatter,
    }

    format_class = format_map.get(format_type.lower())
    if not format_class:
        raise ValueError(
            f"Unknown format: {format_type}. "
            f"Supported formats: {', '.join(format_map.keys())}"
        )

    return format_class()
