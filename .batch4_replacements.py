import re
from pathlib import Path

files_and_entities = [
    ("tests/unit/core/domain/test_project.py", "Project", 22),
    ("tests/integration/workflows/test_sync_orchestrator_end_to_end.py", "Issue", 17),
    ("tests/unit/cli/test_daily_summary_service.py", "Issue", 12),
    ("tests/unit/cli/test_daily_summary_service.py", "Milestone", 4),
]

for filepath, entity, count in files_and_entities:
    content = Path(filepath).read_text()

    factory_map = {
        "Project": "ProjectBuilder",
        "Issue": "IssueBuilder",
        "Milestone": "MilestoneBuilder",
    }
    builder = factory_map[entity]

    print(f"\n{filepath}: {count} {entity} creations")

    # Count how many we can match
    pattern = rf"(\w+)\s*=\s*{entity}\("
    matches = re.findall(pattern, content)
    print(f"  Found {len(set(matches))} unique variables using {entity}()")
