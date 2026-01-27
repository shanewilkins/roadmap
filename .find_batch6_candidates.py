#!/usr/bin/env python3
"""Find next high-value test files for refactoring (5+ entities)."""

import re
from collections import defaultdict
from pathlib import Path

# Files already refactored in Phase 9a & 9b
REFACTORED = {
    "test_estimated_time.py",
    "test_github_conflict_detector.py",
    "test_sync_backend.py",
    "test_view_presenter_rendering.py",
    "test_view_presenters.py",
    "test_project_service_read_ops.py",
    "test_dtos_and_mappers.py",
    "test_project.py",
    "test_issue_github_field.py",
    "test_milestone_name_normalization_fixer.py",
    "test_project_service_write_ops.py",
    "test_issue_filters_query_and_workload.py",
    "test_data_integrity_three_way.py",
    "test_three_way_analysis.py",
}

tests_dir = Path("tests")
results = defaultdict(lambda: {"Issue": 0, "Milestone": 0, "Project": 0, "Comment": 0})

for test_file in sorted(tests_dir.rglob("test_*.py")):
    if test_file.name in REFACTORED:
        continue

    content = test_file.read_text()

    # Count Issue/Milestone/Project creations
    issue_count = len(re.findall(r"\bIssue\s*\(", content))
    milestone_count = len(re.findall(r"\bMilestone\s*\(", content))
    project_count = len(re.findall(r"\bProject\s*\(", content))
    comment_count = len(re.findall(r"\bComment\s*\(", content))

    total = issue_count + milestone_count + project_count + comment_count

    if total >= 5:
        results[test_file] = {
            "Issue": issue_count,
            "Milestone": milestone_count,
            "Project": project_count,
            "Comment": comment_count,
        }

# Sort by total count (descending)
sorted_files = sorted(results.items(), key=lambda x: sum(x[1].values()), reverse=True)

print("Top 20 high-value files for refactoring (5+ entities):\n")
for i, (file_path, counts) in enumerate(sorted_files[:20], 1):
    total = sum(counts.values())
    rel_path = file_path.relative_to("tests")
    print(f"{i:2d}. {rel_path}")
    parts = []
    if counts["Issue"] > 0:
        parts.append(f"{counts['Issue']} Issues")
    if counts["Milestone"] > 0:
        parts.append(f"{counts['Milestone']} Milestones")
    if counts["Project"] > 0:
        parts.append(f"{counts['Project']} Projects")
    if counts["Comment"] > 0:
        parts.append(f"{counts['Comment']} Comments")
    print(f"    Total: {total:2d} | {', '.join(parts)}")
    print()
