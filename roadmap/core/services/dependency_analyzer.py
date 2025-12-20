"""Dependency analysis service for detecting issues in issue relationships.

Analyzes depends_on and blocks relationships to detect:
- Circular dependencies (A → B → A)
- Broken references (pointing to non-existent issues)
- Self-dependencies (issue depends on itself)
- Orphaned blockers (issue blocks non-existent issue)
- Deep dependency chains (chains > 5 levels)
"""

from dataclasses import dataclass, field

from roadmap.common.logging import get_logger
from roadmap.core.domain.issue import Issue

logger = get_logger(__name__)


class DependencyIssueType(str):
    """Types of dependency issues that can be found."""

    CIRCULAR = "circular_dependency"
    BROKEN = "broken_dependency"
    SELF = "self_dependency"
    ORPHANED_BLOCKER = "orphaned_blocker"
    DEEP_CHAIN = "deep_dependency_chain"
    MISSING_BIDIRECTIONAL = "missing_bidirectional"


@dataclass
class DependencyIssue:
    """A problem found in issue dependencies."""

    issue_id: str
    issue_type: DependencyIssueType
    message: str
    affected_issues: list[str] = field(default_factory=list)
    chain_length: int | None = None  # For deep chain issues
    severity: str = "warning"  # error, warning, info

    def __post_init__(self):
        """Set severity based on issue type."""
        if self.issue_type == DependencyIssueType.CIRCULAR:
            self.severity = "error"
        elif self.issue_type == DependencyIssueType.BROKEN:
            self.severity = "error"
        elif self.issue_type == DependencyIssueType.SELF:
            self.severity = "error"
        elif self.issue_type == DependencyIssueType.ORPHANED_BLOCKER:
            self.severity = "warning"
        elif self.issue_type == DependencyIssueType.DEEP_CHAIN:
            self.severity = "info"
        elif self.issue_type == DependencyIssueType.MISSING_BIDIRECTIONAL:
            self.severity = "warning"


@dataclass
class DependencyAnalysisResult:
    """Result of analyzing all dependencies."""

    total_issues: int
    issues_with_dependencies: int
    issues_with_problems: int
    problems: list[DependencyIssue] = field(default_factory=list)
    circular_chains: list[list[str]] = field(
        default_factory=list
    )  # Lists of issue IDs forming cycles

    @property
    def is_healthy(self) -> bool:
        """Check if all dependencies are healthy."""
        return (
            not any(p.severity == "error" for p in self.problems)
            and not self.circular_chains
        )

    @property
    def error_count(self) -> int:
        """Count of critical errors."""
        return len([p for p in self.problems if p.severity == "error"]) + len(
            self.circular_chains
        )

    @property
    def warning_count(self) -> int:
        """Count of warnings."""
        return len([p for p in self.problems if p.severity == "warning"])

    @property
    def info_count(self) -> int:
        """Count of informational issues."""
        return len([p for p in self.problems if p.severity == "info"])


class DependencyAnalyzer:
    """Analyzes issue dependency relationships for problems."""

    def __init__(self):
        """Initialize the analyzer."""
        self._issue_map: dict[str, Issue] = {}
        self._analyzed = False

    def analyze(self, issues: list[Issue]) -> DependencyAnalysisResult:
        """Analyze all dependencies in the issue set.

        Args:
            issues: List of all issues in the system

        Returns:
            DependencyAnalysisResult with all problems found
        """
        self._issue_map = {issue.id: issue for issue in issues}
        self._analyzed = True

        result = DependencyAnalysisResult(
            total_issues=len(issues),
            issues_with_dependencies=sum(1 for i in issues if i.depends_on or i.blocks),
            issues_with_problems=0,
        )

        # Check all issues
        for issue in issues:
            self._check_issue_dependencies(issue, result)

        result.issues_with_problems = len({p.issue_id for p in result.problems})

        return result

    def _check_issue_dependencies(self, issue: Issue, result: DependencyAnalysisResult):
        """Check dependencies for a single issue."""
        # Check depends_on
        for dep_id in issue.depends_on or []:
            # Check for self-dependency
            if dep_id == issue.id:
                result.problems.append(
                    DependencyIssue(
                        issue_id=issue.id,
                        issue_type=DependencyIssueType.SELF,
                        message="Issue depends on itself",
                        affected_issues=[dep_id],
                    )
                )
                continue

            # Check for broken dependency
            if dep_id not in self._issue_map:
                result.problems.append(
                    DependencyIssue(
                        issue_id=issue.id,
                        issue_type=DependencyIssueType.BROKEN,
                        message=f"Depends on non-existent issue {dep_id}",
                        affected_issues=[dep_id],
                    )
                )
                continue

            # Check for missing bidirectional link
            dep_issue = self._issue_map[dep_id]
            if issue.id not in (dep_issue.blocks or []):
                # This is a warning, not an error, as one-way deps are valid
                result.problems.append(
                    DependencyIssue(
                        issue_id=issue.id,
                        issue_type=DependencyIssueType.MISSING_BIDIRECTIONAL,
                        message=f"Depends on {dep_id} but {dep_id} does not list this as a blocker",
                        affected_issues=[dep_id],
                    )
                )

        # Check blocks
        for blocked_id in issue.blocks or []:
            # Check for self-block
            if blocked_id == issue.id:
                result.problems.append(
                    DependencyIssue(
                        issue_id=issue.id,
                        issue_type=DependencyIssueType.SELF,
                        message="Issue blocks itself",
                        affected_issues=[blocked_id],
                    )
                )
                continue

            # Check for orphaned blocker
            if blocked_id not in self._issue_map:
                result.problems.append(
                    DependencyIssue(
                        issue_id=issue.id,
                        issue_type=DependencyIssueType.ORPHANED_BLOCKER,
                        message=f"Blocks non-existent issue {blocked_id}",
                        affected_issues=[blocked_id],
                    )
                )
                continue

            # Check for missing bidirectional link
            blocked_issue = self._issue_map[blocked_id]
            if issue.id not in (blocked_issue.depends_on or []):
                result.problems.append(
                    DependencyIssue(
                        issue_id=issue.id,
                        issue_type=DependencyIssueType.MISSING_BIDIRECTIONAL,
                        message=f"Blocks {blocked_id} but {blocked_id} does not list this as a dependency",
                        affected_issues=[blocked_id],
                    )
                )

        # Check for deep chains
        if issue.depends_on:
            max_depth = self._find_max_chain_depth(issue.id, set(), 0)
            if max_depth > 5:
                result.problems.append(
                    DependencyIssue(
                        issue_id=issue.id,
                        issue_type=DependencyIssueType.DEEP_CHAIN,
                        message=f"Deep dependency chain ({max_depth} levels)",
                        affected_issues=issue.depends_on,
                        chain_length=max_depth,
                    )
                )

        # Check for circular dependencies
        if issue.depends_on:
            for dep_id in issue.depends_on:
                cycle = self._find_cycle_from(dep_id, issue.id, set())
                if cycle:
                    # Convert set to sorted list for consistent output
                    cycle_list = sorted(list(cycle) + [issue.id])
                    if cycle_list not in result.circular_chains:
                        result.circular_chains.append(cycle_list)
                        result.problems.append(
                            DependencyIssue(
                                issue_id=issue.id,
                                issue_type=DependencyIssueType.CIRCULAR,
                                message=f"Circular dependency detected: {' → '.join(cycle_list)} → {issue.id}",
                                affected_issues=cycle_list,
                            )
                        )

    def _find_cycle_from(
        self, current_id: str, target_id: str, visited: set[str]
    ) -> set[str] | None:
        """Find if there's a path from current_id back to target_id.

        Args:
            current_id: ID to start searching from
            target_id: ID we're trying to reach (forming a cycle)
            visited: IDs already visited in this search

        Returns:
            Set of IDs in the cycle if found, None otherwise
        """
        if current_id not in self._issue_map:
            return None

        if current_id in visited:
            return None  # Already visited this node, not our cycle

        if current_id == target_id:
            return {current_id}  # Found the cycle!

        visited.add(current_id)
        issue = self._issue_map[current_id]

        # Check all issues this one depends on
        for dep_id in issue.depends_on or []:
            result = self._find_cycle_from(dep_id, target_id, visited.copy())
            if result:
                result.add(current_id)
                return result

        return None

    def _find_max_chain_depth(
        self, current_id: str, visited: set[str], depth: int
    ) -> int:
        """Find the maximum dependency chain depth from current issue.

        Args:
            current_id: Issue ID to start from
            visited: Set of visited IDs (to avoid infinite loops)
            depth: Current depth in the chain

        Returns:
            Maximum chain depth found
        """
        if current_id not in self._issue_map:
            return depth

        if current_id in visited:
            return depth  # Cycle detected, return current depth

        visited.add(current_id)
        issue = self._issue_map[current_id]

        if not issue.depends_on:
            return depth  # No further dependencies

        # Find the maximum depth through any dependency
        max_depth = depth
        for dep_id in issue.depends_on:
            depth_through_dep = self._find_max_chain_depth(
                dep_id, visited.copy(), depth + 1
            )
            max_depth = max(max_depth, depth_through_dep)

        return max_depth

    def get_issues_affecting(self, issue_id: str) -> list[str]:
        """Get all issues that this one affects through dependency chain.

        Args:
            issue_id: The issue to start from

        Returns:
            List of issue IDs that would be affected if this issue changes
        """
        if issue_id not in self._issue_map:
            return []

        affected = set()
        self._collect_affected(issue_id, affected)
        return sorted(affected)

    def _collect_affected(self, issue_id: str, affected: set[str]):
        """Recursively collect all issues affected by this one.

        An issue is affected if this one blocks it (directly or indirectly).
        """
        if not self._analyzed:
            return

        # Find all issues that depend on this one (it affects them)
        if issue_id in self._issue_map:
            issue = self._issue_map[issue_id]
            for blocked_id in issue.blocks or []:
                if blocked_id in self._issue_map:
                    if blocked_id not in affected:
                        affected.add(blocked_id)
                        # Recursively get issues affected by the blocked issue
                        self._collect_affected(blocked_id, affected)
