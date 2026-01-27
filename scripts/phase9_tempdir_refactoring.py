#!/usr/bin/env python3
"""Phase 9: Temporary Directory Factory Creation & Refactoring Plan.

This script identifies the specific patterns of tmp_path usage and creates
a refactoring strategy for consolidating them into reusable fixtures.

Usage:
    python scripts/phase9_tempdir_refactoring.py
    python scripts/phase9_tempdir_refactoring.py --refactor-list
    python scripts/phase9_tempdir_refactoring.py --show-patterns
"""

import argparse
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


class TempDirAnalyzer:
    """Analyze temporary directory usage patterns in tests."""

    def __init__(self):
        """Initialize analyzer."""
        self.patterns: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.files_analyzed = 0

    def analyze_test_suite(self) -> None:
        """Scan all test files for tmp_path usage patterns."""
        test_dir = Path("tests")
        test_files = list(test_dir.rglob("test_*.py"))

        for test_file in test_files:
            self._analyze_file(test_file)

    def _analyze_file(self, filepath: Path) -> None:
        """Analyze single test file."""
        try:
            content = filepath.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return

        self.files_analyzed += 1
        rel_path = str(filepath).replace("/Users/shane/roadmap/", "")

        # Pattern 1: Simple mkdir/file operations
        if re.search(r"tmp_path\s*/\s*['\"]", content):
            self._record_pattern(
                "path_operations",
                rel_path,
                "tmp_path / 'dirname' or tmp_path / \"filename\"",
            )

        # Pattern 2: Git repo initialization
        if re.search(r"git.*init.*tmp_path|subprocess.*git.*cwd=tmp_path", content):
            self._record_pattern("git_repo", rel_path, "Git repo setup in tmp_path")

        # Pattern 3: File write/read
        if re.search(r"(tmp_path|project_root).*write|read_text", content):
            self._record_pattern(
                "file_operations", rel_path, "File read/write operations"
            )

        # Pattern 4: Roadmap structure (.roadmap/issues, .roadmap/milestones)
        if re.search(r"roadmap.*mkdir|\.roadmap", content):
            self._record_pattern(
                "roadmap_structure", rel_path, ".roadmap directory structure"
            )

        # Pattern 5: TOML/YAML config files
        if re.search(r"\.toml|\.yaml|\.yml|pyproject|config", content):
            self._record_pattern(
                "config_files", rel_path, "Config file (TOML/YAML) handling"
            )

        # Pattern 6: Python version management
        if re.search(r"__init__\.py.*version|__version__", content):
            self._record_pattern(
                "version_files", rel_path, "Version file handling (__init__.py)"
            )

        # Pattern 7: Isolation/cleanup setup
        if re.search(r"os\.chdir|original_cwd|finally", content):
            self._record_pattern("isolation", rel_path, "Directory isolation/cleanup")

        # Pattern 8: Database/state files
        if re.search(r"\.db|\.json|state|database", content):
            self._record_pattern(
                "state_files", rel_path, "Database/state file handling"
            )

    def _record_pattern(
        self, pattern_type: str, filepath: str, description: str
    ) -> None:
        """Record a pattern occurrence."""
        self.patterns[pattern_type].append(
            {"file": filepath, "description": description}
        )

    def get_pattern_summary(self) -> dict[str, int]:
        """Get count of each pattern type."""
        return {k: len(v) for k, v in self.patterns.items()}

    def get_top_patterns(self, top_n: int = 10) -> list[tuple[str, int]]:
        """Get top N patterns by frequency."""
        summary = self.get_pattern_summary()
        return sorted(summary.items(), key=lambda x: x[1], reverse=True)[:top_n]

    def get_high_impact_files(self) -> list[tuple[str, int]]:
        """Identify test files with most tmp_path usage."""
        file_counts = defaultdict(int)

        for patterns in self.patterns.values():
            for entry in patterns:
                file_counts[entry["file"]] += 1

        return sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:15]

    def print_summary(self) -> None:
        """Print analysis summary."""
        print("=" * 120)
        print("TEMPORARY DIRECTORY USAGE PATTERNS")
        print("=" * 120)
        print()
        print(f"Files analyzed: {self.files_analyzed}")
        print()

        print("PATTERN DISTRIBUTION:")
        print("-" * 120)
        for pattern_type, count in self.get_top_patterns():
            print(f"  {pattern_type:25s}: {count:3d} files")

        print()
        print("TOP 15 FILES WITH MOST USAGE:")
        print("-" * 120)
        for filepath, count in self.get_high_impact_files():
            print(f"  {filepath:70s}: {count:3d} patterns")

    def print_factory_recommendations(self) -> None:
        """Print recommended fixtures and factories to create."""
        patterns = self.get_pattern_summary()

        print()
        print("=" * 120)
        print("RECOMMENDED FIXTURES TO CREATE")
        print("=" * 120)
        print()

        recommendations = [
            {
                "name": "temp_file_factory",
                "pattern": "file_operations",
                "code": """
@pytest.fixture
def temp_file_factory(tmp_path):
    \"\"\"Factory for creating temporary files with content.\"\"\"

    class TempFileFactory:
        @staticmethod
        def create_toml(filename: str = "pyproject.toml", **content) -> Path:
            '''Create a temporary TOML file.'''
            import tomllib
            filepath = tmp_path / filename
            with open(filepath, "w") as f:
                toml.dump(content, f)
            return filepath

        @staticmethod
        def create_yaml(filename: str = "config.yaml", **content) -> Path:
            '''Create a temporary YAML file.'''
            import yaml
            filepath = tmp_path / filename
            with open(filepath, "w") as f:
                yaml.dump(content, f)
            return filepath

        @staticmethod
        def create_file(filename: str, content: str = "") -> Path:
            '''Create a temporary file with content.'''
            filepath = tmp_path / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content)
            return filepath

    return TempFileFactory()
""",
            },
            {
                "name": "git_repo_factory",
                "pattern": "git_repo",
                "code": """
@pytest.fixture
def git_repo_factory(tmp_path):
    \"\"\"Factory for initializing git repositories.\"\"\"

    class GitRepoFactory:
        @staticmethod
        def create_repo(
            initial_commit: bool = True,
            branch_name: str = "main"
        ) -> Path:
            '''Initialize a git repository with optional initial commit.'''
            subprocess.run(["git", "init", "-b", branch_name], cwd=tmp_path, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, check=True)

            if initial_commit:
                (tmp_path / "README.md").write_text("# Test Repo")
                subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
                subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_path, check=True)

            return tmp_path

        @staticmethod
        def create_with_branch(branch_name: str = "feature/test") -> Path:
            '''Create repo with additional branch.'''
            repo = GitRepoFactory.create_repo()
            subprocess.run(["git", "checkout", "-b", branch_name], cwd=tmp_path, check=True)
            subprocess.run(["git", "checkout", "main"], cwd=tmp_path, check=True)
            return repo

    return GitRepoFactory()
""",
            },
            {
                "name": "roadmap_structure_factory",
                "pattern": "roadmap_structure",
                "code": """
@pytest.fixture
def roadmap_structure_factory(tmp_path):
    \"\"\"Factory for creating .roadmap directory structures.\"\"\"

    class RoadmapStructureFactory:
        @staticmethod
        def create_minimal() -> Path:
            '''Create minimal .roadmap structure.'''
            roadmap_dir = tmp_path / ".roadmap"
            roadmap_dir.mkdir()
            (roadmap_dir / "issues").mkdir()
            (roadmap_dir / "milestones").mkdir()
            return roadmap_dir

        @staticmethod
        def create_with_config(**config_values) -> Path:
            '''Create .roadmap structure with config file.'''
            roadmap_dir = RoadmapStructureFactory.create_minimal()

            config = {
                "version": "1.0.0",
                "project_name": "Test Project",
            }
            config.update(config_values)

            config_file = roadmap_dir / "config.yaml"
            import yaml
            with open(config_file, "w") as f:
                yaml.dump(config, f)

            return roadmap_dir

        @staticmethod
        def create_full_with_issues(num_issues: int = 3) -> Path:
            '''Create .roadmap with issues populated.'''
            roadmap_dir = RoadmapStructureFactory.create_with_config()

            issues_dir = roadmap_dir / "issues"
            for i in range(num_issues):
                issue_file = issues_dir / f"TEST-{i:03d}.md"
                issue_file.write_text(f"# Issue TEST-{i:03d}\\n\\nTest issue content.")

            return roadmap_dir

    return RoadmapStructureFactory()
""",
            },
            {
                "name": "isolated_workspace",
                "pattern": "isolation",
                "code": """
@pytest.fixture
def isolated_workspace(tmp_path, monkeypatch):
    \"\"\"Fixture that provides isolated workspace with directory restoration.\"\"\"

    class IsolatedWorkspace:
        def __init__(self, tmp_dir: Path):
            self.root = tmp_dir
            self.original_cwd = None

        def __enter__(self):
            self.original_cwd = os.getcwd()
            os.chdir(str(self.root))
            return self.root

        def __exit__(self, *args):
            if self.original_cwd:
                os.chdir(self.original_cwd)

        def change_to(self, subdir: str) -> Path:
            '''Change to a subdirectory (relative to workspace root).'''
            target = self.root / subdir
            target.mkdir(parents=True, exist_ok=True)
            os.chdir(str(target))
            return target

    return IsolatedWorkspace(tmp_path)
""",
            },
        ]

        for i, rec in enumerate(recommendations, 1):
            count = patterns.get(rec["pattern"], 0)
            print(f"{i}. {rec['name'].upper()}")
            print(f"   Applies to: {count} test files")
            print(f"   Usage: Consolidates {rec['pattern']} patterns")
            print()
            print("   Code template:")
            print("   " + "\n   ".join(rec["code"].split("\n")))
            print()


def main():
    """Run analysis."""
    parser = argparse.ArgumentParser(description="Temp directory refactoring analysis")
    parser.add_argument(
        "--show-patterns", action="store_true", help="Show all pattern details"
    )
    parser.add_argument(
        "--refactor-list",
        action="store_true",
        help="Show refactoring priority list",
    )
    args = parser.parse_args()

    analyzer = TempDirAnalyzer()
    analyzer.analyze_test_suite()

    analyzer.print_summary()

    if args.show_patterns or not args.refactor_list:
        analyzer.print_factory_recommendations()

    if args.refactor_list:
        print()
        print("=" * 120)
        print("REFACTORING PRIORITY (by impact)")
        print("=" * 120)
        print()

        high_impact = analyzer.get_high_impact_files()
        for i, (filepath, count) in enumerate(high_impact[:8], 1):
            print(f"{i}. {filepath}")
            print(f"   Impact: {count} tmp_path usages")
            print("   Effort: ~15 minutes to refactor if fixtures available")
            print()


if __name__ == "__main__":
    main()
