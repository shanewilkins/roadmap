#!/usr/bin/env python3
"""
Enhanced Demo Data Generator for CloudSync Enterprise Platform
Creates 1000+ realistic issues across multiple milestones with proper distribution.
"""

import random
import subprocess
from pathlib import Path


def run_command(command, suppress_output=True):
    """Run a roadmap command and return success status."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=suppress_output,
            text=True,
            cwd="/Users/shane/roadmap/demo-project",
        )
        return result.returncode == 0
    except Exception:
        return False


def generate_issues_batch(milestone, count, developers, issue_templates):
    """Generate a batch of issues for a specific milestone."""
    print(f"  Creating {count} issues for {milestone}...")

    success_count = 0

    for i in range(count):
        # Select random template and customize
        template = random.choice(issue_templates)

        # Customize the issue title
        components = [
            "API gateway",
            "web interface",
            "mobile app",
            "database",
            "authentication service",
            "file storage system",
            "sync engine",
            "notification service",
            "analytics engine",
            "admin dashboard",
            "search service",
            "user management",
            "backup system",
            "collaboration tools",
            "performance monitor",
            "security module",
            "audit system",
        ]

        actions = [
            "Implement",
            "Fix",
            "Optimize",
            "Refactor",
            "Setup",
            "Configure",
            "Update",
            "Debug",
            "Create",
            "Build",
            "Add",
            "Address",
            "Develop",
            "Enhance",
            "Correct",
        ]

        features = [
            "real-time collaboration",
            "two-factor authentication",
            "role-based permissions",
            "disaster recovery",
            "mobile synchronization",
            "offline mode",
            "version history",
            "audit logging",
            "performance monitoring",
            "encryption at rest",
            "OAuth 2.0",
            "search functionality",
            "notification system",
            "analytics dashboard",
            "user management",
            "conflict resolution",
            "backup automation",
            "live document editing",
            "metadata extraction",
            "team workspaces",
            "usage metrics",
            "tagging system",
            "multi-region deployment",
            "error handling",
            "logging configuration",
            "database migration",
            "dependency updates",
            "security review",
            "test coverage",
            "code cleanup",
            "documentation",
            "monitoring setup",
            "performance optimization",
            "deployment scripts",
            "configuration management",
        ]

        # Generate varied issue titles
        component = random.choice(components)
        action = random.choice(actions)
        feature = random.choice(features)

        if template["type"] == "bug":
            bug_issues = [
                "memory leak",
                "slow query performance",
                "authentication failures",
                "sync conflicts",
                "permission errors",
                "timeout issues",
                "race condition",
                "data corruption",
                "download interruptions",
                "validation bypasses",
                "connection timeouts",
                "file corruption",
                "session expiry",
                "deadlock detection",
                "cache invalidation",
                "API rate limiting",
            ]
            issue_title = f"{action} {random.choice(bug_issues)} in {component}"
        else:
            issue_title = f"{action} {feature} for {component}"

        # Select assignee and priority
        assignee = (
            random.choice(developers) if random.random() < 0.85 else None
        )  # 85% assigned
        priority = random.choices(
            ["critical", "high", "medium", "low"],
            weights=[0.1, 0.25, 0.5, 0.15],  # Realistic priority distribution
        )[0]

        # Build command
        command_parts = [
            "poetry run roadmap issue create",
            f'"{issue_title}"',
            f"--type {template['type']}",
            f"--priority {priority}",
        ]

        if milestone:
            command_parts.append(f'--milestone "{milestone}"')

        if assignee:
            command_parts.append(f"--assignee {assignee}")

        # Add estimates for some issues
        if random.random() < 0.4:  # 40% have estimates
            estimate = random.choice([0.5, 1, 2, 3, 4, 5, 8, 13, 21])
            command_parts.append(f"--estimate {estimate}")

        command = " ".join(command_parts)

        if run_command(command):
            success_count += 1

            # Randomly start/close some issues to create realistic status distribution
            if random.random() < 0.3:  # 30% of issues get started
                # Get the last created issue ID (this is a simplification)
                time.sleep(0.1)  # Small delay to ensure file is written
                start_cmd = "poetry run roadmap issue start $(poetry run roadmap issue list | head -2 | tail -1 | cut -d' ' -f1)"
                run_command(start_cmd)

                # Some started issues get completed
                if random.random() < 0.4:  # 40% of started issues get completed
                    done_cmd = "poetry run roadmap issue done $(poetry run roadmap issue list | head -2 | tail -1 | cut -d' ' -f1)"
                    run_command(done_cmd)

        # Progress indicator
        if (i + 1) % 50 == 0:
            print(f"    ... {i + 1}/{count} issues created")

    print(f"  ✅ Successfully created {success_count}/{count} issues for {milestone}")
    return success_count


def main():
    print("🚀 Enhanced Demo Data Generator")
    print("=" * 50)
    print("Generating 1000+ issues for CloudSync Enterprise Platform")
    print()

    # Check if demo project exists
    demo_path = Path("/Users/shane/roadmap/demo-project")
    if not demo_path.exists():
        print("❌ Demo project not found. Please set up the demo project first.")
        return

    # Team members (same as before plus a few more)
    developers = [
        "alex.chen",
        "sarah.johnson",
        "michael.brown",
        "emily.davis",
        "david.kim",
        "lisa.taylor",
        "james.wilson",
        "maria.rodriguez",
        "robert.anderson",
        "jennifer.thomas",
        "karen.miller",
        "chris.lee",
        "amanda.white",
        "ryan.garcia",
        "nicole.thompson",
        "brandon.martinez",
    ]

    # Issue type templates with realistic distribution
    issue_templates = [
        {"type": "feature", "weight": 6},  # 60% features
        {"type": "bug", "weight": 3},  # 30% bugs
        {"type": "other", "weight": 1},  # 10% other
    ]

    # Expand templates based on weights
    weighted_templates = []
    for template in issue_templates:
        weighted_templates.extend([template] * template["weight"])

    # Milestone distribution - more issues in active milestones
    milestone_distribution = [
        ("v1.6.0 - Enhanced Security & Authentication", 120),
        ("v1.7.0 - Real-time Collaboration Features", 180),
        ("v1.8.0 - Advanced Analytics Dashboard", 200),
        ("v1.9.0 - Mobile Applications & API Enhancement", 250),
        ("v2.0.0 - AI-Powered Features & Enterprise Scale", 200),
        (None, 100),  # Backlog items
    ]

    total_issues_to_create = sum(count for _, count in milestone_distribution)
    print(f"📊 Plan: Create {total_issues_to_create} new issues")
    print("🎯 Distribution:")
    for milestone, count in milestone_distribution:
        milestone_name = milestone or "Backlog"
        print(f"  • {milestone_name}: {count} issues")
    print()

    # Get current issue count
    result = subprocess.run(
        "poetry run roadmap issue list | head -1 | grep -o '[0-9]\\+' | head -1",
        shell=True,
        capture_output=True,
        text=True,
        cwd="/Users/shane/roadmap/demo-project",
    )

    current_count = 0
    if result.returncode == 0 and result.stdout.strip():
        current_count = int(result.stdout.strip())

    print(f"📋 Current issues: {current_count}")
    print(f"🎯 Target total: {current_count + total_issues_to_create}")
    print()

    # Generate issues for each milestone
    total_created = 0

    for milestone, count in milestone_distribution:
        milestone_display = milestone or "Backlog"
        print(f"🔧 Generating issues for: {milestone_display}")

        created = generate_issues_batch(
            milestone, count, developers, weighted_templates
        )
        total_created += created
        print()

    # Final status
    print("=" * 50)
    print("✅ Generation complete!")
    print(f"📊 Created: {total_created} new issues")
    print(f"🎯 Estimated total: {current_count + total_created}")
    print()

    # Verify final count
    print("🔍 Verifying final count...")
    result = subprocess.run(
        "poetry run roadmap issue list | head -1",
        shell=True,
        capture_output=True,
        text=True,
        cwd="/Users/shane/roadmap/demo-project",
    )

    if result.returncode == 0:
        print(f"📋 Final count: {result.stdout.strip()}")

    print()
    print("🎉 Demo project is ready with 1000+ issues!")
    print("Try: cd demo-project && poetry run roadmap project")


if __name__ == "__main__":
    import time

    main()
