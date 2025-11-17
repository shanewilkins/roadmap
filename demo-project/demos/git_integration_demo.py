#!/usr/bin/env python3
"""
Git Integration Demo for Roadmap CLI
====================================

This demo showcases the powerful Git integration capabilities of the roadmap CLI
using the main roadmap project. It demonstrates automated workflow features,
branch management, and synchronization between Git activity and issue tracking.
"""

import subprocess
from pathlib import Path


def run_command(command, description):
    """Run a command and display the output."""
    print(f"\n🔧 {description}")
    print("=" * len(description) + "===")
    print(f"Command: {command}")
    print("-" * 50)

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd="/Users/shane/roadmap",
        )
        if result.returncode == 0:
            print(result.stdout)
        else:
            print(f"❌ Command failed: {result.stderr}")
    except Exception as e:
        print(f"❌ Error running command: {e}")


def main():
    print("🔗 Git Integration Demo")
    print("=" * 50)
    print()
    print("This demo shows how roadmap CLI integrates with Git for:")
    print("  • Automated branch creation for issues")
    print("  • Issue linking and status synchronization")
    print("  • Git hooks for workflow automation")
    print("  • Commit tracking and analysis")
    print("  • Branch-based issue management")
    print()

    # Check if main project exists and is a Git repo
    roadmap_path = Path("/Users/shane/roadmap/.roadmap")
    git_path = Path("/Users/shane/roadmap/.git")
    if not roadmap_path.exists():
        print("❌ Main roadmap project not found.")
        return
    if not git_path.exists():
        print("❌ Not a Git repository. Git integration requires a Git repo.")
        return

    print("📋 GIT STATUS & OVERVIEW")
    print("-" * 24)
    print("Check current Git and roadmap synchronization:")

    # Git status commands
    run_command("poetry run roadmap git-status", "Git repository and roadmap status")
    run_command(
        "poetry run roadmap git-link --status", "Show current branch-issue links"
    )

    print()
    print("🌿 BRANCH MANAGEMENT")
    print("-" * 20)
    print("Create and manage Git branches for issues:")

    # Branch management
    run_command("poetry run roadmap issue list | head -5", "List available issues")
    print("\n💡 To create a branch for an issue:")
    print("  poetry run roadmap git-branch ISSUE_ID")
    print("  # This creates a branch like: feature/ISSUE_ID-issue-title")

    print()
    print("🔄 SYNCHRONIZATION")
    print("-" * 18)
    print("Sync issue status with Git activity:")

    # Synchronization
    run_command("poetry run roadmap git-sync", "Sync issues with Git commits")
    run_command("poetry run roadmap workflow-sync-all", "Comprehensive workflow sync")

    print()
    print("📝 COMMIT TRACKING")
    print("-" * 18)
    print("Track commits related to issues:")

    # Commit tracking
    print("💡 View commits for an issue:")
    print("  poetry run roadmap git-commits ISSUE_ID")
    print("  # Shows all commits that reference the issue")

    print()
    print("🪝 GIT HOOKS SETUP")
    print("-" * 18)
    print("Install automated Git hooks for workflow integration:")

    # Git hooks
    run_command("poetry run roadmap git-hooks-install", "Install Git hooks")

    print("""
    🔧 Installed Hooks:
    • pre-commit: Validates issue references in commit messages
    • post-commit: Updates issue status based on commit activity
    • pre-push: Ensures proper issue linking before pushing
    """)

    print()
    print("⚙️ WORKFLOW AUTOMATION")
    print("-" * 23)
    print("Set up comprehensive workflow automation:")

    # Workflow automation
    run_command(
        "poetry run roadmap workflow-automation-setup", "Setup workflow automation"
    )

    print()
    print("📊 GIT ANALYTICS")
    print("-" * 17)
    print("Analyze Git activity and contributions:")

    # Git analytics
    run_command("poetry run roadmap activity", "Recent team activity from Git")

    print()
    print("🔧 EXAMPLE WORKFLOWS")
    print("-" * 20)
    print("Common Git + Roadmap workflows:")

    print("""
    📋 NEW FEATURE WORKFLOW:
    1. Create issue: poetry run roadmap issue create "Add login feature"
    2. Create branch: poetry run roadmap git-branch ISSUE_ID
    3. Work on feature and commit with issue reference
    4. Push and create PR: git push origin feature/ISSUE_ID-add-login-feature
    5. Auto-sync: Issue status updates based on PR status

    🐛 BUG FIX WORKFLOW:
    1. Create bug issue: poetry run roadmap issue create "Fix auth bug" --type bug
    2. Create hotfix branch: poetry run roadmap git-branch ISSUE_ID
    3. Fix bug with descriptive commits
    4. Issue automatically moves to 'in-progress' when commits are made
    5. Issue closes when PR is merged

    🔄 DAILY SYNC WORKFLOW:
    1. Morning: poetry run roadmap git-status
    2. Check activity: poetry run roadmap activity
    3. Sync changes: poetry run roadmap git-sync
    4. Review dashboard: poetry run roadmap dashboard
    """)

    print()
    print("🎯 INTEGRATION FEATURES")
    print("-" * 24)
    print("✅ Automatic branch creation with semantic naming")
    print("✅ Issue-commit linking via commit message parsing")
    print("✅ Status synchronization based on Git activity")
    print("✅ Pre-commit validation and hooks")
    print("✅ Activity tracking and team insights")
    print("✅ Workflow automation and triggers")
    print("✅ Branch protection and policy enforcement")

    print()
    print("🔒 SECURITY & VALIDATION")
    print("-" * 25)
    print("Git integration includes security features:")
    print("  • Commit message validation")
    print("  • Branch naming conventions")
    print("  • Issue reference verification")
    print("  • Secure hook installation")

    print()
    print("🚀 NEXT STEPS")
    print("-" * 12)
    print("Try these Git integration commands:")
    print("  poetry run roadmap git-hooks-install")
    print("  poetry run roadmap workflow-automation-setup")
    print(
        "  poetry run roadmap git-branch $(poetry run roadmap issue list | head -2 | tail -1 | cut -d' ' -f1)"
    )
    print("  poetry run roadmap git-sync")
    print("  poetry run roadmap activity")
    print()

    print("💡 Advanced usage:")
    print("  # Link current branch to an issue")
    print("  poetry run roadmap git-link ISSUE_ID")
    print("  ")
    print("  # View comprehensive Git status")
    print("  poetry run roadmap git-status --detailed")
    print()

    print(
        "📖 Learn more: https://roadmap-cli.readthedocs.io/en/latest/git-integration/"
    )


if __name__ == "__main__":
    main()
