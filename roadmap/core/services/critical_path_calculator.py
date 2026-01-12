"""Critical path analysis for issue dependencies.

Calculates which issues are on the critical path and impact project timeline.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from roadmap.core.domain.issue import Issue
from roadmap.core.domain.milestone import Milestone


@dataclass
class PathNode:
    """Represents an issue in the critical path analysis."""

    issue_id: str
    issue_title: str
    duration_hours: float
    dependencies: list[str] = field(default_factory=list)
    start_date: datetime | None = None
    end_date: datetime | None = None
    slack_time: float = 0.0  # Time available before blocking other tasks
    is_critical: bool = False


@dataclass
class CriticalPathResult:
    """Results from critical path analysis."""

    critical_path: list[PathNode]
    total_duration: float
    critical_issue_ids: list[str]
    blocking_issues: dict[str, list[str]]  # issue_id -> list of blocked issue_ids
    project_end_date: datetime | None = None
    issues_by_criticality: dict[str, list[str]] = field(default_factory=dict)


class CriticalPathCalculator:
    """Calculates critical path for issues based on dependencies."""

    def __init__(self):
        """Initialize calculator."""
        pass

    def calculate_critical_path(
        self, issues: list[Issue], milestone: Milestone | None = None
    ) -> CriticalPathResult:
        """Calculate critical path from issues with dependencies.

        Args:
            issues: List of issues to analyze
            milestone: Optional milestone context for date calculations

        Returns:
            CriticalPathResult with critical path information
        """
        if not issues:
            return CriticalPathResult(
                critical_path=[],
                total_duration=0.0,
                critical_issue_ids=[],
                blocking_issues={},
            )

        # Build dependency graph
        graph = self._build_dependency_graph(issues)

        # Calculate earliest start/end dates
        node_data = self._calculate_schedule(issues, graph)

        # Find critical path
        critical_path = self._find_critical_path(node_data, graph)

        # Analyze blocking relationships
        blocking_issues = self._analyze_blocking(issues)

        # Calculate slack time
        self._calculate_slack(node_data, critical_path)

        # Determine project end date
        project_end_date = self._calculate_project_end_date(node_data, milestone)

        return CriticalPathResult(
            critical_path=critical_path,
            total_duration=sum(node.duration_hours for node in critical_path),
            critical_issue_ids=[node.issue_id for node in critical_path],
            blocking_issues=blocking_issues,
            project_end_date=project_end_date,
            issues_by_criticality=self._group_by_criticality(issues, critical_path),
        )

    def _build_dependency_graph(self, issues: list[Issue]) -> dict[str, list[str]]:
        """Build dependency graph from issues.

        Args:
            issues: List of issues

        Returns:
            Dictionary mapping issue_id to list of dependent issue_ids
        """
        graph = {issue.id: issue.depends_on or [] for issue in issues}
        return graph

    def _calculate_schedule(
        self, issues: list[Issue], graph: dict[str, list[str]]
    ) -> dict[str, PathNode]:
        """Calculate earliest start and end times.

        Args:
            issues: List of issues
            graph: Dependency graph

        Returns:
            Dictionary mapping issue_id to PathNode
        """
        nodes = {}
        for issue in issues:
            duration = self._estimate_duration(issue)
            nodes[issue.id] = PathNode(
                issue_id=issue.id,
                issue_title=issue.title,
                duration_hours=duration,
                dependencies=graph.get(issue.id, []),
            )

        # Calculate earliest start/end times using topological sort
        start_times = {}
        visiting = set()  # Track nodes currently being processed to detect cycles

        def calculate_start_time(issue_id: str) -> float:
            if issue_id in start_times:
                return start_times[issue_id]

            # Detect circular dependencies
            if issue_id in visiting:
                # Return 0 for circular refs (they shouldn't exist, but graceful fallback)
                return 0.0

            visiting.add(issue_id)

            try:
                dependencies = graph.get(issue_id, [])
                if not dependencies:
                    start_times[issue_id] = 0.0
                    return 0.0

                # Max end time of all dependencies
                max_end_time = 0.0
                for dep_id in dependencies:
                    if dep_id in nodes:
                        dep_start = calculate_start_time(dep_id)
                        dep_duration = nodes[dep_id].duration_hours
                        max_end_time = max(max_end_time, dep_start + dep_duration)

                start_times[issue_id] = max_end_time
                return max_end_time
            finally:
                visiting.discard(issue_id)

        # Calculate all start times
        for issue_id in nodes:
            start_time = calculate_start_time(issue_id)
            nodes[issue_id].start_date = datetime.now(UTC) + timedelta(hours=start_time)
            nodes[issue_id].end_date = datetime.now(UTC) + timedelta(
                hours=start_time + nodes[issue_id].duration_hours
            )

        return nodes

    def _find_critical_path(
        self, nodes: dict[str, PathNode], graph: dict[str, list[str]]
    ) -> list[PathNode]:
        """Find the critical path (longest duration path through dependencies).

        Args:
            nodes: Dictionary of nodes with schedule info
            graph: Dependency graph

        Returns:
            List of PathNode objects on critical path, ordered by dependency
        """
        if not nodes:
            return []

        # Find leaf nodes (no blocks)
        leaf_nodes = [
            issue_id
            for issue_id, node in nodes.items()
            if not any(issue_id in graph.get(other_id, []) for other_id in nodes)
        ]

        if not leaf_nodes:
            # If no clear leaf, use nodes with latest end dates
            leaf_nodes = sorted(
                nodes.keys(),
                key=lambda x: nodes[x].end_date or datetime.now(UTC),
                reverse=True,
            )[:1]

        # Trace back from leaf nodes to find longest path
        critical_paths = []

        for leaf_id in leaf_nodes:
            path = self._trace_path_backward(leaf_id, nodes, graph)
            critical_paths.append(path)

        # Return longest path
        critical_path = max(critical_paths, key=lambda p: len(p), default=[])

        # Mark critical nodes
        for node in critical_path:
            node.is_critical = True

        return critical_path

    def _trace_path_backward(
        self, issue_id: str, nodes: dict[str, PathNode], graph: dict[str, list[str]]
    ) -> list[PathNode]:
        """Trace path backward from a node to root dependencies.

        Args:
            issue_id: Starting issue ID
            nodes: Node dictionary
            graph: Dependency graph

        Returns:
            List of nodes in dependency chain
        """
        path = []
        current_id = issue_id
        visited = set()  # Track visited nodes to prevent infinite loops

        while current_id in nodes:
            # Detect circular dependencies
            if current_id in visited:
                break

            visited.add(current_id)
            path.append(nodes[current_id])
            dependencies = graph.get(current_id, [])

            if not dependencies:
                break

            # Follow the dependency with longest duration
            current_id = max(
                dependencies,
                key=lambda d: nodes.get(d, PathNode("", "", 0)).duration_hours,
            )

        return list(reversed(path))

    def _estimate_duration(self, issue: Issue) -> float:
        """Estimate duration from issue estimated_hours field.

        Args:
            issue: Issue to estimate

        Returns:
            Duration in hours
        """
        if not issue.estimated_hours:
            return 4.0  # Default 4 hours

        return float(issue.estimated_hours)

    def _calculate_slack(
        self, nodes: dict[str, PathNode], critical_path: list[PathNode]
    ) -> None:
        """Calculate slack time for non-critical paths.

        Args:
            nodes: Dictionary of all nodes
            critical_path: List of critical path nodes
        """
        # Critical path nodes have no slack
        critical_ids = {node.issue_id for node in critical_path}

        if critical_path:
            max_end_time = max(
                (node.end_date or datetime.now(UTC)) for node in critical_path
            )

            for node_id, node in nodes.items():
                if node_id not in critical_ids and node.end_date:
                    slack_hours = (max_end_time - node.end_date).total_seconds() / 3600
                    node.slack_time = max(0.0, slack_hours)

    def _calculate_project_end_date(
        self,
        nodes: dict[str, PathNode],
        milestone: Milestone | None = None,
    ) -> datetime | None:
        """Calculate expected project completion date.

        Args:
            nodes: Dictionary of nodes
            milestone: Optional milestone with due date

        Returns:
            Expected project end date
        """
        if not nodes:
            return milestone.due_date if milestone else None

        # Project ends when all critical path items complete
        latest_end = max(
            (node.end_date for node in nodes.values() if node.end_date),
            default=None,
        )

        if latest_end and milestone and milestone.due_date:
            return min(latest_end, milestone.due_date)

        return latest_end or (milestone.due_date if milestone else None)

    def _analyze_blocking(self, issues: list[Issue]) -> dict[str, list[str]]:
        """Analyze which issues block others.

        Args:
            issues: List of issues

        Returns:
            Dictionary mapping issue_id to list of blocked issue_ids
        """
        blocking = {}

        for issue in issues:
            if issue.blocks:
                blocking[issue.id] = issue.blocks

        return blocking

    def _group_by_criticality(
        self, issues: list[Issue], critical_path: list[PathNode]
    ) -> dict[str, list[str]]:
        """Group issues by criticality level.

        Args:
            issues: List of all issues
            critical_path: List of critical path nodes

        Returns:
            Dictionary with criticality groups
        """
        critical_ids = {node.issue_id for node in critical_path}
        blocking_issues = set()
        blocked_issues = set()

        for issue in issues:
            if issue.blocks:
                blocking_issues.add(issue.id)
            if issue.depends_on:
                blocked_issues.add(issue.id)

        return {
            "critical": list(critical_ids),
            "blocking": list(blocking_issues),
            "blocked": list(blocked_issues),
            "independent": [
                issue.id
                for issue in issues
                if issue.id not in critical_ids
                and issue.id not in blocking_issues
                and issue.id not in blocked_issues
            ],
        }

    def find_blocking_issues(
        self, issues: list[Issue], target_issue_id: str
    ) -> list[Issue]:
        """Find all issues blocking a specific issue.

        Args:
            issues: List of all issues
            target_issue_id: ID of issue to check

        Returns:
            List of issues blocking the target
        """
        issue_map = {issue.id: issue for issue in issues}
        target = issue_map.get(target_issue_id)

        if not target or not target.depends_on:
            return []

        blocking = []
        for dep_id in target.depends_on:
            if dep_id in issue_map:
                blocking.append(issue_map[dep_id])

        return blocking

    def find_blocked_issues(
        self, issues: list[Issue], blocker_issue_id: str
    ) -> list[Issue]:
        """Find all issues blocked by a specific issue.

        Args:
            issues: List of all issues
            blocker_issue_id: ID of blocking issue

        Returns:
            List of issues blocked by the blocker
        """
        issue_map = {issue.id: issue for issue in issues}
        blocker = issue_map.get(blocker_issue_id)

        if not blocker or not blocker.blocks:
            return []

        blocked = []
        for blocked_id in blocker.blocks:
            if blocked_id in issue_map:
                blocked.append(issue_map[blocked_id])

        return blocked
