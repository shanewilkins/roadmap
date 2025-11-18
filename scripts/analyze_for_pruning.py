#!/usr/bin/env python3
"""
Analyze roadmap project for aggressive pruning candidates.
Identifies code not needed for v1.0 core features.
"""

import ast
import json
from collections import defaultdict
from pathlib import Path

# Core 1.0 features that MUST remain
CORE_1_0_FEATURES = {
    "issue_management",  # Create, list, update issues
    "milestone_management",  # Create, track milestones
    "progress_tracking",  # Calculate and display progress
    "github_integration",  # Basic GitHub import/export
    "data_persistence",  # Save/load roadmap files
    "cli_core_commands",  # Basic CLI infrastructure
}

# Modules we know are core
CORE_MODULES = {
    "models",  # Data models
    "core",  # Core functionality
    "parser",  # YAML/markdown parsing
    "database",  # SQLite persistence
    "file_utils",  # File operations
    "cli/core",  # Main CLI entry
    "cli/issue",  # Issue commands
    "cli/milestone",  # Milestone commands
    "cli/progress",  # Progress commands
}

# Known post-1.0 features (candidates for archival)
POST_1_0_FEATURES = {
    "analytics",  # Advanced analytics
    "predictive",  # Predictive features
    "enhanced_github",  # GitHub enterprise features
    "webhook_server",  # Webhook infrastructure
    "curation",  # Data curation
    "repository_scanner",  # Repo scanning
    "security_assessment",  # Security features
    "performance_sync",  # Performance optimizations
    "bulk_operations",  # Bulk operations
    "team_management",  # Team features (beyond basic assignment)
    "ci_tracking",  # CI/CD tracking
    "identity",  # Advanced identity management
    "timezone_migration",  # Timezone utilities
}


class ImportAnalyzer(ast.NodeVisitor):
    """Track imports in Python files."""

    def __init__(self):
        self.imports = set()
        self.from_imports = defaultdict(set)

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            for alias in node.names:
                self.from_imports[node.module].add(alias.name)
        self.generic_visit(node)


def analyze_roadmap_files():
    """Analyze roadmap package for usage patterns."""
    roadmap_dir = Path("/Users/shane/roadmap/roadmap")

    module_info = {}

    for py_file in roadmap_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        rel_path = py_file.relative_to(roadmap_dir)
        module_name = str(rel_path).replace("/", ".").replace(".py", "")

        try:
            content = py_file.read_text()
            tree = ast.parse(content)

            analyzer = ImportAnalyzer()
            analyzer.visit(tree)

            module_info[module_name] = {
                "file": str(rel_path),
                "lines": len(content.split("\n")),
                "imports": sorted(analyzer.imports),
                "from_imports": dict(analyzer.from_imports),
                "size_bytes": py_file.stat().st_size,
            }
        except Exception as e:
            print(f"Error analyzing {py_file}: {e}")

    return module_info


def categorize_modules(module_info: dict):
    """Categorize modules by feature area."""
    categorized = {
        "core_1_0": {},
        "post_1_0_candidates": {},
        "utility": {},
        "unknown": {},
    }

    for module_name, info in module_info.items():
        # Check if clearly core
        is_core = any(core in module_name for core in CORE_MODULES)

        # Check if post-1.0 feature
        is_post_1_0 = any(feat in module_name for feat in POST_1_0_FEATURES)

        # Classify
        if is_core or any(
            feat in module_name
            for feat in ["cli/issue", "cli/milestone", "cli/progress", "cli/core"]
        ):
            categorized["core_1_0"][module_name] = info
        elif is_post_1_0:
            categorized["post_1_0_candidates"][module_name] = info
        elif any(x in module_name for x in ["utils", "logging", "validation", "error"]):
            categorized["utility"][module_name] = info
        else:
            categorized["unknown"][module_name] = info

    return categorized


def calculate_stats(categorized: dict):
    """Calculate statistics."""
    stats = {}

    for category, modules in categorized.items():
        total_lines = sum(m["lines"] for m in modules.values())
        total_bytes = sum(m["size_bytes"] for m in modules.values())
        stats[category] = {
            "count": len(modules),
            "total_lines": total_lines,
            "total_bytes": total_bytes,
            "avg_lines": total_lines // len(modules) if modules else 0,
        }

    return stats


def print_analysis(module_info: dict, categorized: dict, stats: dict):
    """Print detailed analysis."""

    print("=" * 70)
    print("PROJECT PRUNING ANALYSIS - AGGRESSIVE V1.0 SIMPLIFICATION")
    print("=" * 70)
    print()

    print("📊 STATISTICS BY CATEGORY:")
    print()

    total_all = 0
    for category, s in stats.items():
        print(f"  {category}:")
        print(f"    • Modules: {s['count']}")
        print(f"    • Total lines: {s['total_lines']:,}")
        print(f"    • Total size: {s['total_bytes'] / 1024:.1f} KB")
        total_all += s["total_lines"]

    print(f"\n  🎯 TOTAL: {total_all:,} lines")
    print()

    print("=" * 70)
    print("✅ CORE 1.0 MODULES (MUST KEEP):")
    print("=" * 70)
    for module_name in sorted(categorized["core_1_0"].keys()):
        info = categorized["core_1_0"][module_name]
        print(f"  • {module_name:<40} {info['lines']:>6} lines")

    print()
    print("=" * 70)
    print("🎯 POST-1.0 ARCHIVAL CANDIDATES (SAFE TO REMOVE NOW):")
    print("=" * 70)

    post_1_0 = categorized["post_1_0_candidates"]
    removable_lines = sum(m["lines"] for m in post_1_0.values())
    removable_bytes = sum(m["size_bytes"] for m in post_1_0.values())

    for module_name in sorted(post_1_0.keys()):
        info = post_1_0[module_name]
        print(f"  • {module_name:<40} {info['lines']:>6} lines")

    print()
    print(
        f"  📦 TOTAL REMOVABLE: {removable_lines:,} lines ({removable_bytes / 1024:.1f} KB)"
    )
    percentage = (removable_lines / total_all) * 100 if total_all > 0 else 0
    print(f"     That's {percentage:.1f}% of current codebase")
    print()

    print("=" * 70)
    print("⚙️ UTILITY MODULES (CHECK FOR CROSS-CUTTING USAGE):")
    print("=" * 70)
    for module_name in sorted(categorized["utility"].keys()):
        info = categorized["utility"][module_name]
        print(f"  • {module_name:<40} {info['lines']:>6} lines")

    print()
    print("=" * 70)
    print("❓ UNKNOWN CLASSIFICATION (NEEDS REVIEW):")
    print("=" * 70)
    for module_name in sorted(categorized["unknown"].keys()):
        info = categorized["unknown"][module_name]
        print(f"  • {module_name:<40} {info['lines']:>6} lines")

    print()


if __name__ == "__main__":
    print("🔍 Analyzing roadmap package...")
    module_info = analyze_roadmap_files()
    print(f"   Found {len(module_info)} modules\n")

    categorized = categorize_modules(module_info)
    stats = calculate_stats(categorized)

    print_analysis(module_info, categorized, stats)

    # Save detailed report (convert sets to lists for JSON serialization)
    def convert_sets(obj):
        if isinstance(obj, set):
            return sorted(list(obj))
        elif isinstance(obj, dict):
            return {k: convert_sets(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_sets(item) for item in obj]
        return obj

    report = {
        "timestamp": "2025-11-18",
        "summary": {
            "total_modules": len(module_info),
            "statistics": stats,
        },
        "modules_by_category": {
            cat: {k: convert_sets(v) for k, v in modules.items()}
            for cat, modules in categorized.items()
        },
    }

    report_file = Path("/Users/shane/roadmap/pruning_analysis_report.json")
    report_file.write_text(json.dumps(report, indent=2))
    print(f"✅ Detailed report saved to: {report_file}")
