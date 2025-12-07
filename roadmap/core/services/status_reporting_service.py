"""Service for status reporting."""

from roadmap.infrastructure.core import RoadmapCore
from roadmap.infrastructure.health import HealthCheck, HealthStatus


class StatusReportingService:
    """Service for generating roadmap status reports."""

    @staticmethod
    def get_status_report(verbose: bool = False) -> dict:
        """Get comprehensive status report.

        Args:
            verbose: Include verbose details

        Returns:
            Status report dictionary
        """
        try:
            core = RoadmapCore()
            if not core.is_initialized():
                return {"initialized": False}

            report = {
                "initialized": True,
                "roadmap_dir": str(core.roadmap_dir),
                "has_projects": core.projects_dir.exists(),
                "has_issues": core.issues_dir.exists(),
                "has_milestones": core.milestones_dir.exists(),
                "has_artifacts": core.artifacts_dir.exists(),
            }

            if verbose:
                report.update(StatusReportingService._get_detailed_stats(core))

            return report
        except Exception as e:
            return {"initialized": False, "error": str(e)}

    @staticmethod
    def _get_detailed_stats(core: RoadmapCore) -> dict:
        """Get detailed statistics about roadmap content."""
        stats = {
            "project_count": 0,
            "issue_count": 0,
            "milestone_count": 0,
        }

        try:
            if core.projects_dir.exists():
                stats["project_count"] = len(list(core.projects_dir.glob("*.md")))

            if core.issues_dir.exists():
                stats["issue_count"] = len(list(core.issues_dir.rglob("*.md")))

            if core.milestones_dir.exists():
                stats["milestone_count"] = len(list(core.milestones_dir.glob("*.md")))
        except Exception:
            pass

        return stats

    @staticmethod
    def check_health() -> dict:
        """Check roadmap health status.

        Returns:
            Health status report
        """
        try:
            core = RoadmapCore()
            if not core.is_initialized():
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "message": "Roadmap not initialized",
                    "checks": {},
                }

            health_check = HealthCheck()
            all_checks = health_check.run_all_checks(core)

            # Determine overall status
            overall_status = HealthStatus.HEALTHY
            if all_checks:
                # Check if any checks are UNHEALTHY or DEGRADED
                for _check_name, check_result in all_checks.items():
                    status = (
                        check_result[0]
                        if isinstance(check_result, tuple)
                        else check_result.get("status")
                    )
                    if status == HealthStatus.UNHEALTHY:
                        overall_status = HealthStatus.UNHEALTHY
                        break
                    elif (
                        status == HealthStatus.DEGRADED
                        and overall_status == HealthStatus.HEALTHY
                    ):
                        overall_status = HealthStatus.DEGRADED

            return {
                "status": overall_status,
                "checks": all_checks,
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": str(e),
                "checks": {},
            }
