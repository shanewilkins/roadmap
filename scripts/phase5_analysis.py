#!/usr/bin/env python3
"""Analyze Phase 5 violations and create refactoring strategy."""

import csv

# Read violations
core_adapter = {"persistence": [], "sync": [], "github": [], "git": [], "other": []}
core_infra = []

with open("violation_baseline.csv") as f:
    reader = csv.DictReader(f)
    for row in reader:
        to = row["to_module"]
        if row["from_layer"] == "Core" and row["to_layer"] == "Adapters":
            if "persistence" in to:
                core_adapter["persistence"].append(row)
            elif "sync" in to:
                core_adapter["sync"].append(row)
            elif "github" in to:
                core_adapter["github"].append(row)
            elif "git" in to:
                core_adapter["git"].append(row)
            else:
                core_adapter["other"].append(row)
        elif row["from_layer"] == "Core" and row["to_layer"] == "Infrastructure":
            core_infra.append(row)

print("=" * 80)
print("PHASE 5 REFACTORING STRATEGY")
print("=" * 80)

print("\nCORE → ADAPTERS VIOLATIONS BY CATEGORY:")
print("-" * 80)

for category, violations in core_adapter.items():
    if violations:
        print(f"\n{category.upper()}: {len(violations)} violations")
        for v in violations:
            from_svc = v["from_module"].split(".")[-1]
            to_adapter = v["to_module"].split("adapters.")[-1]
            print(f"  {from_svc:45} → {to_adapter}")

print(f"\n\nCORE → INFRASTRUCTURE (transitive): {len(core_infra)} violations")
print("-" * 80)

infra_targets = {}
for v in core_infra:
    target = v["to_module"].split(".")[-1]
    if target not in infra_targets:
        infra_targets[target] = []
    infra_targets[target].append(v)

for target, violations in sorted(infra_targets.items()):
    print(f"\n→ {target}: {len(violations)} violations")
    for v in violations[:2]:  # Show first 2
        from_svc = v["from_module"].split(".")[-1]
        print(f"    {from_svc}")
    if len(violations) > 2:
        print(f"    ... and {len(violations) - 2} more")

print("\n" + "=" * 80)
print("RECOMMENDED EXECUTION ORDER (by ROI)")
print("=" * 80)

print("""
TIER 1: High Impact, Achievable (11 violations)
========================================
1. Persistence Gateway (7 violations) - Extract 7 parser/storage imports
2. Sync Gateway (2 violations) - Abstract sync service access
3. GitHub Gateway (2 violations) - Mediate GitHub adapter access

TIER 2: Medium Effort (13 violations)
========================================
4. Infrastructure Transitive (10 violations) - Resolve coordination layer
5. Git Adapter (2 violations) - Abstract git operations
6. Other (1 violation) - Misc

TOTAL: 24 violations to resolve
ESTIMATED TIME: Tier 1 (4-6 hrs), Tier 2 (6-8 hrs)
""")
