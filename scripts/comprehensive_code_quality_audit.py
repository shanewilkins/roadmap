#!/usr/bin/env python3
"""
Comprehensive Code Quality Audit
Analyzes all critical code quality metrics across the roadmap codebase.
Provides quantitative baseline for tracking improvements.
"""

import ast
import json
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

# ============================================================================
# CONFIGURATION
# ============================================================================

ROADMAP_DIR = Path("/Users/shane/roadmap/roadmap")
TEST_DIR = Path("/Users/shane/roadmap/tests")


# ============================================================================
# UTILITIES
# ============================================================================


def run_command(cmd: str) -> str:
    """Run shell command and return output."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout + result.stderr


# ============================================================================
# METRIC 1: FILE METRICS (Length, Lines)
# ============================================================================


def analyze_file_metrics():
    """Analyze file sizes and complexity."""
    metrics = {
        "total_files": 0,
        "total_lines": 0,
        "avg_lines_per_file": 0,
        "max_file_lines": 0,
        "max_file_name": "",
        "files_over_500_lines": [],
        "files_over_1000_lines": [],
    }

    all_lines = []

    for py_file in ROADMAP_DIR.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        content = py_file.read_text()
        lines = len(content.split("\n"))
        all_lines.append(lines)

        metrics["total_files"] += 1
        metrics["total_lines"] += lines

        if lines > metrics["max_file_lines"]:
            metrics["max_file_lines"] = lines
            metrics["max_file_name"] = str(py_file.relative_to(ROADMAP_DIR))

        if lines > 1000:
            metrics["files_over_1000_lines"].append(
                {"file": str(py_file.relative_to(ROADMAP_DIR)), "lines": lines}
            )
        elif lines > 500:
            metrics["files_over_500_lines"].append(
                {"file": str(py_file.relative_to(ROADMAP_DIR)), "lines": lines}
            )

    if metrics["total_files"] > 0:
        metrics["avg_lines_per_file"] = round(
            metrics["total_lines"] / metrics["total_files"], 1
        )

    return metrics, all_lines


# ============================================================================
# METRIC 2: CYCLOMATIC COMPLEXITY (via Radon)
# ============================================================================


def analyze_cyclomatic_complexity():
    """Analyze cyclomatic complexity using radon."""
    output = run_command("poetry run radon cc roadmap --json --exclude=tests 2>&1")

    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return {
            "total_functions": 0,
            "total_complexity": 0,
            "avg_complexity": 0.0,
            "max_complexity": 0,
            "max_complexity_function": "",
            "functions_high_complexity": [],
            "functions_very_high_complexity": [],
        }

    complexity_stats = {
        "total_functions": 0,
        "total_complexity": 0,
        "avg_complexity": 0.0,
        "max_complexity": 0,
        "max_complexity_function": "",
        "functions_high_complexity": [],
        "functions_very_high_complexity": [],
    }

    for file_path, file_data in data.items():
        if isinstance(file_data, dict):
            # Try different radon output formats
            functions_list = file_data.get("functions") or []
            if isinstance(functions_list, list):
                for item in functions_list:
                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                        func_name, func_metrics = item[0], item[1]
                        complexity = func_metrics.get("complexity", 0) if isinstance(func_metrics, dict) else 0
                    elif isinstance(item, dict):
                        func_name = item.get("name", "unknown")
                        complexity = item.get("complexity", 0)
                    else:
                        continue

                    complexity_stats["total_functions"] += 1
                    complexity_stats["total_complexity"] += complexity

                    if complexity > complexity_stats["max_complexity"]:
                        complexity_stats["max_complexity"] = complexity
                        complexity_stats["max_complexity_function"] = f"{file_path}::{func_name}"

                    if complexity > 20:
                        complexity_stats["functions_very_high_complexity"].append(
                            {
                                "function": f"{file_path}::{func_name}",
                                "complexity": complexity,
                            }
                        )
                    elif complexity > 10:
                        complexity_stats["functions_high_complexity"].append(
                            {
                                "function": f"{file_path}::{func_name}",
                                "complexity": complexity,
                            }
                        )

    if complexity_stats["total_functions"] > 0:
        complexity_stats["avg_complexity"] = round(
            complexity_stats["total_complexity"]
            / complexity_stats["total_functions"],
            2,
        )

    return complexity_stats


# ============================================================================
# METRIC 3: MAINTAINABILITY INDEX (via Radon)
# ============================================================================


def analyze_maintainability():
    """Analyze maintainability index using radon."""
    output = run_command("poetry run radon mi roadmap --json --exclude=tests 2>&1")

    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return {
            "files": [],
            "avg_index": 0.0,
            "min_index": 100.0,
            "max_index": 0.0,
            "files_poor": [],
            "files_caution": [],
            "files_good": [],
        }

    maintainability = {
        "files": [],
        "avg_index": 0.0,
        "min_index": 100.0,
        "max_index": 0.0,
        "files_poor": [],
        "files_caution": [],
        "files_good": [],
    }

    indices = []

    for file_path, file_data in data.items():
        if isinstance(file_data, dict):
            mi_value = None
            if isinstance(file_data, dict) and "mi" in file_data:
                mi_value = file_data["mi"]
            elif isinstance(file_data, (int, float)):
                mi_value = file_data

            if mi_value is not None:
                try:
                    mi = float(mi_value)
                    indices.append(mi)

                    maintainability["files"].append({"file": file_path, "mi": mi})

                    if mi < maintainability["min_index"]:
                        maintainability["min_index"] = mi
                    if mi > maintainability["max_index"]:
                        maintainability["max_index"] = mi

                    if mi < 40:
                        maintainability["files_poor"].append(
                            {"file": file_path, "mi": round(mi, 2)}
                        )
                    elif mi < 60:
                        maintainability["files_caution"].append(
                            {"file": file_path, "mi": round(mi, 2)}
                        )
                    else:
                        maintainability["files_good"].append(
                            {"file": file_path, "mi": round(mi, 2)}
                        )
                except (TypeError, ValueError):
                    pass

    if indices:
        maintainability["avg_index"] = round(sum(indices) / len(indices), 2)
        maintainability["min_index"] = round(maintainability["min_index"], 2)
        maintainability["max_index"] = round(maintainability["max_index"], 2)
    else:
        maintainability["min_index"] = 0.0
        maintainability["max_index"] = 0.0

    return maintainability


# ============================================================================
# METRIC 4: DRY VIOLATIONS (via Pylint)
# ============================================================================


def analyze_dry_violations():
    """Analyze DRY violations using pylint."""
    output = run_command("poetry run pylint --rcfile=.pylintrc roadmap 2>&1")

    dry_violations = {
        "total_violations": 0,
        "violation_pairs": [],
    }

    for line in output.split("\n"):
        if "R0801" in line:
            dry_violations["total_violations"] += 1

    return dry_violations


# ============================================================================
# METRIC 5: TEST COVERAGE
# ============================================================================


def analyze_test_coverage():
    """Analyze test coverage metrics."""
    output = run_command("poetry run pytest --cov=roadmap --cov-report=json 2>&1")

    coverage = {
        "total_coverage": 0.0,
        "lines_covered": 0,
        "lines_total": 0,
        "files_analyzed": 0,
    }

    # Try to parse from pytest output
    try:
        # Look for coverage percentage in output
        for line in output.split("\n"):
            if "TOTAL" in line or "coverage" in line.lower():
                # Parse coverage percentage
                if "%" in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if "%" in part:
                            try:
                                coverage["total_coverage"] = float(
                                    part.replace("%", "")
                                )
                            except ValueError:
                                pass
    except Exception:
        pass

    return coverage


# ============================================================================
# METRIC 6: DEAD CODE (via Vulture)
# ============================================================================


def analyze_dead_code():
    """Analyze dead code using vulture."""
    output = run_command(
        "poetry run vulture --min-confidence=80 roadmap --exclude=tests 2>&1"
    )

    dead_code = {
        "total_issues": len([l for l in output.split("\n") if "unused" in l.lower()]),
        "unused_variables": 0,
        "unused_functions": 0,
        "unused_classes": 0,
    }

    for line in output.split("\n"):
        if "unused variable" in line.lower():
            dead_code["unused_variables"] += 1
        elif "unused function" in line.lower():
            dead_code["unused_functions"] += 1
        elif "unused class" in line.lower():
            dead_code["unused_classes"] += 1

    return dead_code


# ============================================================================
# METRIC 7: SECURITY ISSUES (via Bandit)
# ============================================================================


def analyze_security():
    """Analyze security issues using bandit."""
    output = run_command("poetry run bandit -r roadmap -c .bandit -f json 2>&1")

    security = {
        "total_issues": 0,
        "high_severity": 0,
        "medium_severity": 0,
        "low_severity": 0,
    }

    try:
        data = json.loads(output)
        if "results" in data:
            for issue in data["results"]:
                security["total_issues"] += 1
                severity = issue.get("severity", "").upper()
                if severity == "HIGH":
                    security["high_severity"] += 1
                elif severity == "MEDIUM":
                    security["medium_severity"] += 1
                elif severity == "LOW":
                    security["low_severity"] += 1
    except (json.JSONDecodeError, KeyError):
        pass

    return security


# ============================================================================
# METRIC 8: TYPE CHECKING (via Pyright)
# ============================================================================


def analyze_type_coverage():
    """Analyze type checking issues."""
    output = run_command("poetry run pyright roadmap 2>&1")

    type_analysis = {
        "total_type_issues": 0,
        "errors": 0,
        "warnings": 0,
        "info": 0,
    }

    for line in output.split("\n"):
        if "error" in line.lower() and "Compiler" not in line:
            type_analysis["errors"] += 1
        elif "warning" in line.lower():
            type_analysis["warnings"] += 1
        elif "information" in line.lower():
            type_analysis["info"] += 1

    type_analysis["total_type_issues"] = (
        type_analysis["errors"]
        + type_analysis["warnings"]
        + type_analysis["info"]
    )

    return type_analysis


# ============================================================================
# METRIC 9: DOCUMENTATION (via Pydocstyle)
# ============================================================================


def analyze_documentation():
    """Analyze documentation coverage using pydocstyle."""
    output = run_command(
        "poetry run pydocstyle --convention=google roadmap 2>&1"
    )

    doc_metrics = {
        "total_violations": 0,
        "by_code": defaultdict(int),
        "missing_docstrings": 0,
        "formatting_issues": 0,
    }

    for line in output.split("\n"):
        # Parse pydocstyle output format: "file.py:line: CODE: message"
        if ".py:" in line:
            # Extract the error code (D###)
            for word in line.split():
                if word.startswith("D") and len(word) == 4 and word[1:].isdigit():
                    code_part = word
                    doc_metrics["total_violations"] += 1
                    doc_metrics["by_code"][code_part] += 1

                    # Categorize
                    if code_part in ["D102", "D103", "D104", "D105", "D107"]:
                        doc_metrics["missing_docstrings"] += 1
                    else:
                        doc_metrics["formatting_issues"] += 1
                    break

    return doc_metrics


# ============================================================================
# METRIC 10: CODE DISTRIBUTION & MODULARITY
# ============================================================================


def analyze_modularity():
    """Analyze code distribution across modules."""
    modularity = {
        "total_modules": 0,
        "largest_modules": [],
        "module_count_by_layer": {},
        "avg_functions_per_module": 0.0,
        "total_functions": 0,
    }

    module_sizes = []
    layer_counts = defaultdict(int)
    total_functions = 0

    for py_file in ROADMAP_DIR.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        modularity["total_modules"] += 1

        # Get layer (first part of path after roadmap/)
        rel_path = py_file.relative_to(ROADMAP_DIR)
        layer = str(rel_path).split("/")[0]
        layer_counts[layer] += 1

        # Count functions
        try:
            content = py_file.read_text()
            tree = ast.parse(content)
            func_count = len([n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)])
            total_functions += func_count
            module_sizes.append(
                {
                    "module": str(rel_path),
                    "functions": func_count,
                    "lines": len(content.split("\n")),
                }
            )
        except Exception:
            pass

    modularity["total_functions"] = total_functions
    modularity["module_count_by_layer"] = dict(layer_counts)

    # Get largest modules
    modularity["largest_modules"] = sorted(
        module_sizes, key=lambda x: x["functions"], reverse=True
    )[:10]

    if modularity["total_modules"] > 0:
        modularity["avg_functions_per_module"] = round(
            total_functions / modularity["total_modules"], 2
        )

    return modularity


# ============================================================================
# METRIC 11: IMPORT ANALYSIS (Concern Mixing)
# ============================================================================


def analyze_import_patterns():
    """Analyze import patterns to detect concern mixing."""
    import_analysis = {
        "total_files": 0,
        "avg_imports_per_file": 0.0,
        "avg_internal_imports_per_file": 0.0,
        "files_with_excessive_imports": [],  # > 20 imports
        "concern_mixing_candidates": [],  # Files mixing multiple concerns
    }

    total_imports = 0
    total_internal_imports = 0
    files_data = []

    for py_file in ROADMAP_DIR.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        try:
            content = py_file.read_text()
            tree = ast.parse(content)

            imports = []
            internal_imports = []

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                        if alias.name.startswith("roadmap"):
                            internal_imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
                        if node.module.startswith("roadmap"):
                            internal_imports.append(node.module)

            import_analysis["total_files"] += 1
            total_imports += len(imports)
            total_internal_imports += len(internal_imports)

            files_data.append(
                {
                    "file": str(py_file.relative_to(ROADMAP_DIR)),
                    "total_imports": len(imports),
                    "internal_imports": len(internal_imports),
                    "concerns": len(set(imp.split(".")[1] for imp in internal_imports if "." in imp)),
                }
            )

            if len(imports) > 20:
                import_analysis["files_with_excessive_imports"].append(
                    {
                        "file": str(py_file.relative_to(ROADMAP_DIR)),
                        "imports": len(imports),
                    }
                )

            # Detect concern mixing: multiple high-level concerns in one file
            if len(set(imp.split(".")[1] for imp in internal_imports if "." in imp)) > 3:
                import_analysis["concern_mixing_candidates"].append(
                    {
                        "file": str(py_file.relative_to(ROADMAP_DIR)),
                        "concern_count": len(
                            set(imp.split(".")[1] for imp in internal_imports if "." in imp)
                        ),
                    }
                )

        except Exception:
            pass

    if import_analysis["total_files"] > 0:
        import_analysis["avg_imports_per_file"] = round(
            total_imports / import_analysis["total_files"], 2
        )
        import_analysis["avg_internal_imports_per_file"] = round(
            total_internal_imports / import_analysis["total_files"], 2
        )

    return import_analysis


# ============================================================================
# METRIC 12: TESTING PATTERNS
# ============================================================================


def analyze_test_patterns():
    """Analyze test coverage and patterns."""
    test_metrics = {
        "total_test_files": 0,
        "total_test_functions": 0,
        "test_categories": {
            "unit": 0,
            "integration": 0,
            "security": 0,
            "other": 0,
        },
    }

    for test_file in TEST_DIR.rglob("test_*.py"):
        test_metrics["total_test_files"] += 1

        # Categorize
        if "unit" in str(test_file):
            test_metrics["test_categories"]["unit"] += 1
        elif "integration" in str(test_file):
            test_metrics["test_categories"]["integration"] += 1
        elif "security" in str(test_file):
            test_metrics["test_categories"]["security"] += 1
        else:
            test_metrics["test_categories"]["other"] += 1

        try:
            content = test_file.read_text()
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                    test_metrics["total_test_functions"] += 1
        except Exception:
            pass

    return test_metrics


# ============================================================================
# MAIN REPORT GENERATION
# ============================================================================


def generate_report():
    """Generate comprehensive code quality report."""
    print("\n" + "=" * 80)
    print("COMPREHENSIVE CODE QUALITY AUDIT - Roadmap CLI")
    print("=" * 80 + "\n")

    # File Metrics
    print("📊 FILE METRICS")
    print("-" * 80)
    file_metrics, all_lines = analyze_file_metrics()
    print(f"  Total Python files: {file_metrics['total_files']}")
    print(f"  Total lines of code: {file_metrics['total_lines']:,}")
    print(f"  Average lines per file: {file_metrics['avg_lines_per_file']}")
    print(f"  Max file size: {file_metrics['max_file_lines']} lines ({file_metrics['max_file_name']})")
    print(f"  Files over 1000 lines: {len(file_metrics['files_over_1000_lines'])}")
    print(f"  Files over 500 lines: {len(file_metrics['files_over_500_lines'])}")
    if file_metrics["files_over_1000_lines"]:
        print("\n  Largest files:")
        for f in sorted(
            file_metrics["files_over_1000_lines"],
            key=lambda x: x["lines"],
            reverse=True,
        )[:5]:
            print(f"    - {f['file']}: {f['lines']} lines")
    print()

    # Complexity
    print("🔄 CYCLOMATIC COMPLEXITY")
    print("-" * 80)
    complexity = analyze_cyclomatic_complexity()
    if complexity.get("total_functions", 0) > 0:
        print(f"  Total functions: {complexity['total_functions']}")
        print(f"  Average complexity: {complexity['avg_complexity']}")
        print(f"  Max complexity: {complexity['max_complexity']} ({complexity['max_complexity_function']})")
        print(f"  Functions with high complexity (>10): {len(complexity['functions_high_complexity'])}")
        print(f"  Functions with very high complexity (>20): {len(complexity['functions_very_high_complexity'])}")
        if complexity["functions_very_high_complexity"]:
            print("\n  Very high complexity functions:")
            for f in complexity["functions_very_high_complexity"][:5]:
                print(f"    - {f['function']}: {f['complexity']}")
    else:
        print("  ⚠️  Could not parse radon output (trying alternative method)")
        # Use simpler output
        output = run_command("poetry run radon cc roadmap --exclude=tests")
        complexity_count = len([l for l in output.split("\n") if ":" in l and not l.startswith(" ")])
        print(f"  Approximate functions analyzed: {complexity_count}")
    print()

    # Maintainability
    print("🏆 MAINTAINABILITY INDEX")
    print("-" * 80)
    maintainability = analyze_maintainability()
    if maintainability.get("avg_index", 0) > 0:
        print(f"  Average MI: {maintainability['avg_index']}")
        print(f"  Range: {maintainability['min_index']} - {maintainability['max_index']}")
        print(f"  Files in good condition (MI > 60): {len(maintainability['files_good'])}")
        print(f"  Files needing attention (MI 40-60): {len(maintainability['files_caution'])}")
        print(f"  Files in poor condition (MI < 40): {len(maintainability['files_poor'])}")
        if maintainability["files_poor"]:
            print("\n  Poorest files:")
            for f in sorted(
                maintainability["files_poor"], key=lambda x: x["mi"]
            )[:5]:
                print(f"    - {f['file']}: {f['mi']}")
    else:
        print("  ⚠️  Could not parse radon output (trying alternative method)")
        # Use simpler output
        output = run_command("poetry run radon mi roadmap --exclude=tests 2>&1 | tail -1")
        print(f"  {output.strip()}")
    print()

    # DRY Violations
    print("🔁 DRY VIOLATIONS")
    print("-" * 80)
    dry = analyze_dry_violations()
    print(f"  Total duplicate code violations: {dry['total_violations']}")
    print()

    # Dead Code
    print("💀 DEAD CODE DETECTION")
    print("-" * 80)
    dead = analyze_dead_code()
    print(f"  Total unused items: {dead['total_issues']}")
    print(f"    - Unused variables: {dead['unused_variables']}")
    print(f"    - Unused functions: {dead['unused_functions']}")
    print(f"    - Unused classes: {dead['unused_classes']}")
    print()

    # Security
    print("🔒 SECURITY ANALYSIS")
    print("-" * 80)
    security = analyze_security()
    print(f"  Total security issues: {security['total_issues']}")
    print(f"    - High severity: {security['high_severity']}")
    print(f"    - Medium severity: {security['medium_severity']}")
    print(f"    - Low severity: {security['low_severity']}")
    print()

    # Type Coverage
    print("🎯 TYPE CHECKING")
    print("-" * 80)
    types = analyze_type_coverage()
    print(f"  Total type issues: {types['total_type_issues']}")
    print(f"    - Errors: {types['errors']}")
    print(f"    - Warnings: {types['warnings']}")
    print()

    # Documentation
    print("📖 DOCUMENTATION COVERAGE")
    print("-" * 80)
    docs = analyze_documentation()
    print(f"  Total docstring violations: {docs['total_violations']}")
    print(f"    - Missing docstrings: {docs['missing_docstrings']}")
    print(f"    - Formatting issues: {docs['formatting_issues']}")
    print(f"  Violations by code:")
    for code, count in sorted(docs["by_code"].items(), key=lambda x: x[1], reverse=True):
        print(f"    - {code}: {count}")
    print()

    # Modularity
    print("🏗️  MODULARITY & ARCHITECTURE")
    print("-" * 80)
    modularity = analyze_modularity()
    print(f"  Total modules: {modularity['total_modules']}")
    print(f"  Total functions: {modularity['total_functions']}")
    print(f"  Average functions per module: {modularity['avg_functions_per_module']}")
    print(f"  Modules by layer:")
    for layer, count in sorted(
        modularity["module_count_by_layer"].items(), key=lambda x: x[1], reverse=True
    ):
        print(f"    - {layer}: {count} modules")
    print("\n  Largest modules (by function count):")
    for m in modularity["largest_modules"][:5]:
        print(
            f"    - {m['module']}: {m['functions']} functions, {m['lines']} lines"
        )
    print()

    # Imports & Concerns
    print("🔗 IMPORT PATTERNS & CONCERN MIXING")
    print("-" * 80)
    imports = analyze_import_patterns()
    print(f"  Total files analyzed: {imports['total_files']}")
    print(f"  Average imports per file: {imports['avg_imports_per_file']}")
    print(f"  Average internal imports per file: {imports['avg_internal_imports_per_file']}")
    print(f"  Files with excessive imports (>20): {len(imports['files_with_excessive_imports'])}")
    print(f"  Files mixing concerns (>3 concerns): {len(imports['concern_mixing_candidates'])}")
    if imports["files_with_excessive_imports"]:
        print("\n  Files with most imports:")
        for f in sorted(
            imports["files_with_excessive_imports"],
            key=lambda x: x["imports"],
            reverse=True,
        )[:5]:
            print(f"    - {f['file']}: {f['imports']} imports")
    if imports["concern_mixing_candidates"]:
        print("\n  Files mixing concerns:")
        for f in sorted(
            imports["concern_mixing_candidates"],
            key=lambda x: x["concern_count"],
            reverse=True,
        )[:5]:
            print(f"    - {f['file']}: {f['concern_count']} concerns")
    print()

    # Testing
    print("✅ TEST COVERAGE & PATTERNS")
    print("-" * 80)
    tests = analyze_test_patterns()
    print(f"  Total test files: {tests['total_test_files']}")
    print(f"  Total test functions: {tests['total_test_functions']}")
    print(f"  Test distribution:")
    for category, count in tests["test_categories"].items():
        print(f"    - {category}: {count} files")
    print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"✅ Codebase: {file_metrics['total_lines']:,} lines across {file_metrics['total_files']} modules")
    print(f"✅ Modularity: Avg {modularity['avg_functions_per_module']} functions/module, {modularity['total_functions']} total functions")
    print(f"✅ DRY: {dry['total_violations']} duplicate code violations detected")
    print(f"✅ Quality: {security['total_issues']} security issues, {dead['total_issues']} dead code items")
    print(f"✅ Testing: {tests['total_test_functions']} test functions across {tests['total_test_files']} files")
    print(f"✅ Type Safety: {types['total_type_issues']} type issues, {types['errors']} errors")
    print(f"✅ Documentation: {docs['total_violations']} docstring violations")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    generate_report()
