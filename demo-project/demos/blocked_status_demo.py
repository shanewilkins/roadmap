#!/usr/bin/env python3
"""
Demo script showcasing the new "blocked" status functionality
in Roadmap CLI.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main():
    """Demonstrate blocked status functionality."""
    print("🚫 Roadmap CLI Blocked Status Feature Demo")
    print("=" * 50)

    print("\n🆕 New Blocked Status")
    print("-" * 25)

    print("The 'blocked' status helps track issues that are waiting on:")
    print("  • Dependencies from other teams")
    print("  • External approvals or reviews")
    print("  • Third-party integrations")
    print("  • Resource availability")
    print("  • Prerequisite tasks")

    print("\n📊 Status Progression")
    print("-" * 20)

    statuses = [
        ("todo", "📝", "white", "Ready to start"),
        ("in-progress", "🔄", "yellow", "Actively being worked on"),
        ("blocked", "🚫", "red", "Waiting on dependencies"),
        ("review", "👀", "blue", "Under review"),
        ("done", "✅", "green", "Completed"),
    ]

    for status, emoji, color, description in statuses:
        print(f"  {emoji} {status:<12} ({color:<6}) - {description}")

    print("\n💻 Command Examples")
    print("-" * 20)

    examples = [
        (
            "Mark issue as blocked",
            "roadmap issue block issue-123 --reason 'Waiting for API approval'",
        ),
        ("Update to blocked status", "roadmap issue update issue-123 --status blocked"),
        ("Unblock an issue", "roadmap issue unblock issue-123 --reason 'API approved'"),
        ("List blocked issues", "roadmap issue list --status blocked"),
        ("Create blocked issue", "roadmap issue create 'New feature' --status blocked"),
    ]

    for desc, cmd in examples:
        print(f"\n🔸 {desc}:")
        print(f"   {cmd}")

    print("\n🎨 Visual Indicators")
    print("-" * 20)

    print("In issue listings and status displays:")
    print("  • Blocked issues appear in RED text")
    print("  • Block/unblock commands use 🚫 and ✅ emojis")
    print("  • Status counts include blocked issues")
    print("  • GitHub labels: 'status:blocked' (orange/red color)")

    print("\n🔧 GitHub Integration")
    print("-" * 20)

    print("When syncing with GitHub:")
    print("  • Creates 'status:blocked' label automatically")
    print("  • Uses distinctive orange-red color (#d93f0b)")
    print("  • Syncs blocked status both ways")
    print("  • Maintains consistency across platforms")

    print("\n🎯 Workflow Integration")
    print("-" * 22)

    workflows = [
        "1. Start work: todo → in-progress",
        "2. Hit dependency: in-progress → blocked",
        "3. Dependency resolved: blocked → in-progress",
        "4. Complete work: in-progress → review → done",
    ]

    for workflow in workflows:
        print(f"  {workflow}")

    print("\n📋 Best Practices")
    print("-" * 17)

    practices = [
        "✅ Always specify --reason when blocking/unblocking",
        "✅ Use descriptive block reasons (what you're waiting for)",
        "✅ Regularly review blocked issues for status changes",
        "✅ Filter by blocked status to identify bottlenecks",
        "✅ Unblock issues as soon as dependencies are resolved",
        "✅ Track blocked issues in team standups",
    ]

    for practice in practices:
        print(f"  {practice}")

    print("\n🚀 Benefits")
    print("-" * 10)

    benefits = [
        "🎯 Clear visibility into workflow bottlenecks",
        "📊 Better project planning and estimation",
        "🤝 Improved team communication about dependencies",
        "📈 Data for process improvement",
        "🔍 Easy identification of issues needing attention",
        "⚡ Faster resolution of blocked work",
    ]

    for benefit in benefits:
        print(f"  {benefit}")

    print("\n🧪 Try It Out")
    print("-" * 12)

    print("Test the blocked status feature:")
    print("  1. roadmap init")
    print("  2. roadmap issue create 'Test issue'")
    print("  3. roadmap issue block <issue-id> --reason 'Testing'")
    print("  4. roadmap issue list --status blocked")
    print("  5. roadmap issue unblock <issue-id> --reason 'Test complete'")

    print("\n" + "=" * 50)
    print("🎉 Blocked status is ready to improve your workflow!")
    print("Better dependency tracking leads to better project outcomes.")


if __name__ == "__main__":
    main()
