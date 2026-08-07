"""Health check result formatters for various output formats.

Supports:
- Plain text: Human-readable with status icons
- Plain text with details: Includes recommendations and fix commands
- JSON: Hierarchical structure with all details
- JSON simple: Flat structure for tool integration
"""

import json
from collections.abc import Mapping

import click

from roadmap.adapters.cli.health.enhancer import HealthCheckDetail, HealthCheckEnhancer
from roadmap.core.domain.health import HealthStatus
from roadmap.infrastructure.observability.health import HealthCheck


class HealthCheckFormatter:
    """Formats health check results in various output styles."""

    # Status display mappings
    STATUS_ICONS = {
        HealthStatus.HEALTHY: "✅",
        HealthStatus.DEGRADED: "⚠️",
        HealthStatus.UNHEALTHY: "❌",
    }

    STATUS_COLORS = {
        HealthStatus.HEALTHY: "green",
        HealthStatus.DEGRADED: "yellow",
        HealthStatus.UNHEALTHY: "red",
    }

    def __init__(self, core=None):
        """Initialize formatter.

        Args:
            core: Optional core instance for entity lookups
        """
        self.core = core
        self.enhancer = HealthCheckEnhancer(core)

    def format_plain(
        self,
        checks: Mapping[str, tuple[HealthStatus, str]],
        details: bool = False,
    ) -> str:
        """Format checks as plain text.

        Args:
            checks: Dict of check results from run_all_checks()
            details: If True, include recommendations and fix commands

        Returns:
            Formatted plain text string
        """
        lines = []

        # Format each check
        for check_name, (status, message) in checks.items():
            display_name = check_name.replace("_", " ").title()
            icon = self.STATUS_ICONS.get(status, "?")

            lines.append(f"{icon} {display_name}: {status.value.upper()}")
            if message:
                lines.append(f"  {message}")

            # Add details if requested
            if details:
                enhanced = self.enhancer.enhance_check_result(
                    check_name, status, message
                )
                self._append_details(lines, enhanced)

            lines.append("")

        # Add overall status
        overall_status = HealthCheck.get_overall_status(checks)
        overall_icon = self.STATUS_ICONS.get(overall_status, "?")
        overall_color = self.STATUS_COLORS.get(overall_status, "white")

        lines.append("─" * 40)
        click.secho(
            f"{overall_icon} Overall Status: {overall_status.value.upper()}",
            fg=overall_color,
            bold=True,
        )

        return "\n".join(lines)

    def format_json(
        self,
        checks: Mapping[str, tuple[HealthStatus, str]],
        details: bool = False,
        hierarchical: bool = True,
    ) -> str:
        """Format checks as JSON.

        Args:
            checks: Dict of check results from run_all_checks()
            details: If True, include detailed information
            hierarchical: If True, use nested structure; else flat

        Returns:
            JSON string
        """
        if hierarchical and details:
            return self._format_json_hierarchical(checks)
        elif hierarchical:
            return self._format_json_hierarchical_simple(checks)
        else:
            return self._format_json_flat(checks, details)

    def _format_json_hierarchical(
        self, checks: Mapping[str, tuple[HealthStatus, str]]
    ) -> str:
        """Format as hierarchical JSON with full details."""
        enhanced_checks = self.enhancer.enhance_all_checks(checks)

        # Group by status
        by_status = {
            HealthStatus.HEALTHY: [],
            HealthStatus.DEGRADED: [],
            HealthStatus.UNHEALTHY: [],
        }

        for _, enhanced in enhanced_checks.items():
            by_status[enhanced.status].append(enhanced)

        # Build hierarchical structure
        output = {
            "metadata": {
                "total_checks": len(checks),
                "healthy": len(by_status[HealthStatus.HEALTHY]),
                "degraded": len(by_status[HealthStatus.DEGRADED]),
                "unhealthy": len(by_status[HealthStatus.UNHEALTHY]),
                "overall_status": HealthCheck.get_overall_status(checks).value.upper(),
            },
            "checks": {
                "healthy": [c.to_dict() for c in by_status[HealthStatus.HEALTHY]],
                "degraded": [c.to_dict() for c in by_status[HealthStatus.DEGRADED]],
                "unhealthy": [c.to_dict() for c in by_status[HealthStatus.UNHEALTHY]],
            },
            "next_steps": self._get_next_steps(enhanced_checks),
        }

        return json.dumps(output, indent=2, default=str)

    def _format_json_hierarchical_simple(
        self, checks: Mapping[str, tuple[HealthStatus, str]]
    ) -> str:
        """Format as hierarchical JSON without details."""
        # Group by status
        by_status = {
            HealthStatus.HEALTHY: [],
            HealthStatus.DEGRADED: [],
            HealthStatus.UNHEALTHY: [],
        }

        for check_name, (status, message) in checks.items():
            by_status[status].append(
                {
                    "check": check_name,
                    "status": status.value.upper(),
                    "message": message,
                }
            )

        output = {
            "metadata": {
                "total_checks": len(checks),
                "healthy": len(by_status[HealthStatus.HEALTHY]),
                "degraded": len(by_status[HealthStatus.DEGRADED]),
                "unhealthy": len(by_status[HealthStatus.UNHEALTHY]),
                "overall_status": HealthCheck.get_overall_status(checks).value.upper(),
            },
            "checks": {
                "healthy": by_status[HealthStatus.HEALTHY],
                "degraded": by_status[HealthStatus.DEGRADED],
                "unhealthy": by_status[HealthStatus.UNHEALTHY],
            },
        }

        return json.dumps(output, indent=2, default=str)

    def _format_json_flat(
        self, checks: Mapping[str, tuple[HealthStatus, str]], details: bool = False
    ) -> str:
        """Format as flat JSON."""
        output = {
            "checks": {},
            "overall_status": HealthCheck.get_overall_status(checks).value.upper(),
        }

        for check_name, (status, message) in checks.items():
            check_data = {
                "status": status.value.upper(),
                "message": message,
            }

            if details:
                enhanced = self.enhancer.enhance_check_result(
                    check_name, status, message
                )
                check_data.update(enhanced.to_dict())

            output["checks"][check_name] = check_data

        return json.dumps(output, indent=2, default=str)

    def _append_details(self, lines: list, detail: HealthCheckDetail) -> None:
        """Append detailed information to output lines."""
        if detail.recommendations:
            lines.append("  Recommendations:")
            for rec in detail.recommendations:
                lines.append(f"    • {rec}")

        if detail.fix_commands:
            lines.append("  Fix Commands:")
            for cmd_info in detail.fix_commands:
                lines.append(f"    • {cmd_info['description']}")
                lines.append(f"      {cmd_info['command']}")

    def _get_next_steps(
        self, enhanced_checks: dict[str, HealthCheckDetail]
    ) -> list[str]:
        """Determine recommended next steps based on check results."""
        next_steps = []

        for enhanced in enhanced_checks.values():
            if enhanced.status == HealthStatus.UNHEALTHY:
                if enhanced.fix_commands:
                    next_steps.append(f"Run: {enhanced.fix_commands[0]['command']}")
                break

        if not next_steps:
            # Check for degraded items
            for enhanced in enhanced_checks.values():
                if enhanced.status == HealthStatus.DEGRADED:
                    if enhanced.fix_commands:
                        next_steps.append(
                            f"Consider: {enhanced.fix_commands[0]['command']}"
                        )

        if not next_steps:
            next_steps.append("All systems healthy! Run 'roadmap health' regularly.")

        return next_steps
