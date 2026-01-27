#!/usr/bin/env python3
"""Phase 9: Identify priority factory targets by ROI and test impact.

This script analyzes test data usage patterns to prioritize which factories
would have the highest impact on test robustness and maintainability.

Metrics:
  - Test Impact: How many tests would benefit from a factory
  - Duplication Score: How many times a pattern is repeated
  - Maintenance Risk: How likely the pattern is to break tests when changed
  - ROI: Combined impact × duplication × maintenance risk

Usage:
    python scripts/phase9_factory_priority.py
    python scripts/phase9_factory_priority.py --details
    python scripts/phase9_factory_priority.py --pattern hardcoded-dates
"""

import argparse
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


class Phase9Analyzer:
    """Analyze test files for factory opportunities."""

    # Patterns that indicate hardcoded test data needing factories
    HARDCODED_PATTERNS = {
        "issue_creation": {
            "regex": r"Issue\(\s*(?:id=.*?)?(?:title=.*?)?",
            "description": "Issue() creation with hardcoded values",
            "risk": 8,  # High: many fields, easy to forget updates
        },
        "milestone_creation": {
            "regex": r"Milestone\(\s*(?:id=.*?)?(?:name=.*?)?",
            "description": "Milestone() creation with hardcoded values",
            "risk": 7,
        },
        "comment_creation": {
            "regex": r"Comment\(\s*(?:id=.*?)?(?:text=.*?)?",
            "description": "Comment() creation with hardcoded values",
            "risk": 6,
        },
        "project_creation": {
            "regex": r"Project\(\s*(?:id=.*?)?(?:name=.*?)?",
            "description": "Project() creation with hardcoded values",
            "risk": 8,
        },
        "datetime_hardcoded": {
            "regex": r"datetime\([0-9]{4},\s*[0-9]{1,2},\s*[0-9]{1,2}",
            "description": "Hardcoded datetime values",
            "risk": 7,  # Brittle: timezone-aware, leap year issues
        },
        "uuid_string": {
            "regex": r'["\']([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})["\']',
            "description": "Hardcoded UUID strings",
            "risk": 6,
        },
        "magic_numbers": {
            "regex": r"(?:priority|status|severity).*?=\s*[0-9]",
            "description": "Magic number assignments (priority, status, etc)",
            "risk": 8,  # High: easy to get wrong
        },
        "mock_spec": {
            "regex": r"Mock\(spec=",
            "description": "Mock with spec (consolidation opportunity)",
            "risk": 5,  # Medium: not data per se, but repetitive
        },
        "temporary_directory": {
            "regex": r"(?:TemporaryDirectory|tmp_path|tempfile\.mkdtemp)",
            "description": "Temporary directory setup",
            "risk": 4,  # Low: less likely to change
        },
        "string_constants": {
            "regex": r'(?:assert|expected|expected_)\w+\s*=\s*["\']',
            "description": "Hardcoded string constants for assertions",
            "risk": 6,  # Medium-high: brittle formatting assertions
        },
    }

    def __init__(self):
        """Initialize analyzer."""
        self.findings: dict[str, Any] = defaultdict(
            lambda: {
                "test_files": set(),
                "occurrences": 0,
                "lines": [],
                "example_code": None,
            }
        )

    def analyze_test_suite(self) -> None:
        """Scan all test files for hardcoded patterns."""
        test_dir = Path("tests")
        test_files = list(test_dir.rglob("test_*.py"))
        print(f"Scanning {len(test_files)} test files...\n")

        for test_file in test_files:
            self._analyze_file(test_file)

    def _analyze_file(self, filepath: Path) -> None:
        """Analyze single test file."""
        try:
            content = filepath.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return

        rel_path = str(filepath).replace("/Users/shane/roadmap/", "")

        for pattern_name, pattern_info in self.HARDCODED_PATTERNS.items():
            regex = pattern_info["regex"]
            matches = list(re.finditer(regex, content))

            if matches:
                lines = content.split("\n")
                for match in matches:
                    # Find line number
                    line_start = content[: match.start()].count("\n")
                    line_num = line_start + 1
                    line_code = (
                        lines[line_start].strip() if line_start < len(lines) else "???"
                    )

                    self.findings[pattern_name]["test_files"].add(rel_path)
                    self.findings[pattern_name]["occurrences"] += 1
                    self.findings[pattern_name]["lines"].append(
                        (rel_path, line_num, line_code)
                    )

                    # Store first example
                    if not self.findings[pattern_name]["example_code"]:
                        self.findings[pattern_name]["example_code"] = line_code

    def calculate_roi(self) -> list[tuple[str, dict[str, Any]]]:
        """Calculate ROI for each pattern."""
        roi_scores = []

        for pattern_name, data in self.findings.items():
            if not data["occurrences"]:
                continue

            pattern_info = self.HARDCODED_PATTERNS[pattern_name]
            test_count = len(data["test_files"])
            occurrence_count = data["occurrences"]
            maintenance_risk = pattern_info["risk"]

            # ROI = (test_count × occurrence_count) × (maintenance_risk / 10)
            # This prioritizes patterns affecting many tests, repeated often, with high risk
            roi = (test_count * occurrence_count) * (maintenance_risk / 10)

            roi_scores.append(
                (
                    pattern_name,
                    {
                        "roi": roi,
                        "test_impact": test_count,
                        "duplication_score": occurrence_count,
                        "avg_per_test": occurrence_count / test_count
                        if test_count
                        else 0,
                        "risk": maintenance_risk,
                        "description": pattern_info["description"],
                        "example": data["example_code"],
                    },
                )
            )

        return sorted(roi_scores, key=lambda x: x[1]["roi"], reverse=True)

    def print_summary(self, top_n: int = 10) -> None:
        """Print priority ranking."""
        roi_scores = self.calculate_roi()

        print("=" * 120)
        print("PHASE 9: FACTORY PRIORITY RANKING (by ROI)")
        print("=" * 120)
        print()
        print("ROI = (Test Impact × Duplication Score) × (Maintenance Risk / 10)")
        print(
            "      Impact = # tests affected  |  Duplication = # occurrences  |  Risk = 1-10 scale"
        )
        print()

        for i, (pattern_name, metrics) in enumerate(roi_scores[:top_n], 1):
            print(f"{i:2d}. {pattern_name.upper()}")
            print(f"    Description:      {metrics['description']}")
            print(f"    ROI Score:         {metrics['roi']:.1f}")
            print(f"    Test Impact:       {metrics['test_impact']} tests affected")
            print(f"    Duplication:       {metrics['duplication_score']} occurrences")
            print(
                f"    Avg per test:      {metrics['avg_per_test']:.1f} occurrences/test"
            )
            print(f"    Maintenance Risk:  {metrics['risk']}/10")
            print(f"    Example code:      {metrics['example']}")
            print()

        # Summary stats
        print("=" * 120)
        print("SUMMARY")
        print("=" * 120)
        total_patterns = len([s for s in roi_scores if s[1]["roi"] > 0])
        total_occurrences = sum(s[1]["duplication_score"] for s in roi_scores)
        affected_tests = len(
            set().union(*(self.findings[p]["test_files"] for p in self.findings))
        )

        print(f"Total patterns found:        {total_patterns}")
        print(f"Total hardcoded occurrences: {total_occurrences}")
        print(f"Test files affected:         {affected_tests}")
        print()

    def print_detailed_pattern(self, pattern_name: str) -> None:
        """Print detailed analysis for a specific pattern."""
        if pattern_name not in self.findings:
            print(f"❌ Pattern '{pattern_name}' not found")
            return

        data = self.findings[pattern_name]
        pattern_info = self.HARDCODED_PATTERNS[pattern_name]

        print("=" * 120)
        print(f"DETAILED ANALYSIS: {pattern_name.upper()}")
        print("=" * 120)
        print()
        print(f"Description:     {pattern_info['description']}")
        print(f"Risk Level:      {pattern_info['risk']}/10")
        print(f"Test Files:      {len(data['test_files'])}")
        print(f"Total Occurs:    {data['occurrences']}")
        print()

        print("AFFECTED TEST FILES:")
        print("-" * 120)
        for test_file in sorted(data["test_files"]):
            count = sum(1 for line in data["lines"] if line[0] == test_file)
            print(f"  {test_file:70s} ({count} occurrences)")

        print()
        print("OCCURRENCE LOCATIONS (first 20):")
        print("-" * 120)
        for file_path, line_num, code in data["lines"][:20]:
            rel_file = file_path.replace("tests/", "")
            print(f"  {rel_file}:{line_num:4d}")
            print(f"    → {code[:90]}")

        if len(data["lines"]) > 20:
            print(f"  ... and {len(data['lines']) - 20} more")

        print()
        print("FACTORY RECOMMENDATION:")
        print("-" * 120)
        if pattern_name == "issue_creation":
            print(
                f"""
Create IssueFactory in tests/factories/domain.py:

    class IssueFactory:
        @staticmethod
        def create_default(**kwargs) -> Issue:
            defaults = {{
                'id': 'TEST-001',
                'title': 'Test Issue',
                'status': Status.OPEN,
                'priority': Priority.MEDIUM,
                ...
            }}
            defaults.update(kwargs)
            return Issue(**defaults)

Then replace hardcoded Issue(...) with: IssueFactory.create_default(...)
Impact: Saves {data["occurrences"]} hardcoded instances, makes test changes centralized.
"""
            )
        elif pattern_name == "datetime_hardcoded":
            print("""
Create DateTimeFactory in tests/factories/utilities.py:

    class DateTimeFactory:
        @staticmethod
        def create_past_date(days_ago: int = 7) -> datetime:
            return now_utc() - timedelta(days=days_ago)

        @staticmethod
        def create_future_date(days_ahead: int = 7) -> datetime:
            return now_utc() + timedelta(days=days_ahead)

Impact: Eliminates timezone brittleness, makes date logic DRY.
""")
        else:
            print(
                f"Create a {pattern_name.title()}Factory following the pattern above."
            )

    def print_actionable_plan(self) -> None:
        """Print an actionable rollout plan."""
        roi_scores = self.calculate_roi()
        top_3 = roi_scores[:3]

        print("=" * 120)
        print("ACTIONABLE PHASE 9 ROLLOUT PLAN")
        print("=" * 120)
        print()

        for rank, (pattern_name, metrics) in enumerate(top_3, 1):
            print(f"TIER {rank}: {pattern_name.upper()}")
            print(
                f"  ROI: {metrics['roi']:.1f} | Impact: {metrics['test_impact']} tests | {metrics['duplication_score']} occurrences"
            )
            print("  Effort: ~30 min (create factory + replace instances)")
            print(
                f"  Benefit: Eliminates {metrics['duplication_score']} hardcoded values from test suite"
            )
            print()

        print("TOTAL EFFORT: ~2 hours for top 3 factories")
        print(
            "TOTAL BENEFIT: Reduces brittleness in ~{n} test files".format(
                n=len(set().union(*(self.findings[p[0]]["test_files"] for p in top_3)))
            )
        )


def main():
    """Run analysis."""
    parser = argparse.ArgumentParser(description="Phase 9 factory priority analysis")
    parser.add_argument(
        "--pattern",
        help="Show detailed analysis for a specific pattern",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Show top N patterns (default: 10)",
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="Show actionable rollout plan",
    )
    args = parser.parse_args()

    analyzer = Phase9Analyzer()
    analyzer.analyze_test_suite()

    if args.pattern:
        analyzer.print_detailed_pattern(args.pattern)
    else:
        analyzer.print_summary(top_n=args.top)

        if args.plan:
            print("\n")
            analyzer.print_actionable_plan()


if __name__ == "__main__":
    main()
