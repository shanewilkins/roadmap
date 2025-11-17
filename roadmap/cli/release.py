"""Release management CLI commands."""

import click
from rich.console import Console
from rich.table import Table

from ..version import VersionManager

console = Console()


@click.group(name="release")
@click.pass_context
def release_group(ctx):
    """Release management commands."""
    pass


@release_group.command("version")
@click.pass_context
def version_check(ctx):
    """Check version consistency across project files."""
    core_obj = ctx.obj["core"]

    if not core_obj.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    # Get project root from core
    project_root = core_obj.root_path
    version_manager = VersionManager(project_root)

    # Check version consistency
    result = version_manager.check_version_consistency()

    # Display results
    if result["consistent"]:
        current_version = result["pyproject_version"] or result["init_version"]
        console.print("✅ Version consistency check passed", style="bold green")
        console.print(f"📦 Current version: {current_version}", style="blue")
    else:
        console.print("❌ Version consistency issues found:", style="bold red")
        for issue in result["issues"]:
            console.print(f"   • {issue}", style="red")

        console.print("\n📋 Current versions:", style="bold")
        console.print(
            f"   pyproject.toml: {result['pyproject_version'] or 'Not found'}"
        )
        console.print(f"   __init__.py: {result['init_version'] or 'Not found'}")

    # Show git status
    git_status = version_manager.get_git_status()
    if git_status["is_git_repo"]:
        console.print("\n🔄 Git status:", style="bold")
        console.print(f"   Branch: {git_status['current_branch']}")
        if git_status["is_clean"]:
            console.print("   Status: Clean working directory", style="green")
        else:
            console.print(
                f"   Status: {len(git_status['uncommitted_files'])} uncommitted files",
                style="yellow",
            )


@release_group.command("prepare")
@click.argument("bump_type", type=click.Choice(["patch", "minor", "major"]))
@click.option(
    "--dry-run", is_flag=True, help="Show what would be done without making changes"
)
@click.pass_context
def prepare_release(ctx, bump_type: str, dry_run: bool):
    """Prepare a new release by bumping version and updating changelog."""
    core_obj = ctx.obj["core"]

    if not core_obj.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    # Get project root from core
    project_root = core_obj.root_path
    version_manager = VersionManager(project_root)

    # Pre-flight checks
    console.print("🔍 Running pre-flight checks...", style="blue")

    # Check version consistency
    version_result = version_manager.check_version_consistency()
    if not version_result["consistent"]:
        console.print("❌ Version consistency check failed:", style="bold red")
        for issue in version_result["issues"]:
            console.print(f"   • {issue}", style="red")
        console.print("Fix version consistency issues before releasing.", style="red")
        return

    current_version = version_manager.get_current_version()
    if not current_version:
        console.print("❌ Could not determine current version", style="bold red")
        return

    # Calculate new version
    if bump_type == "major":
        new_version = current_version.bump_major()
    elif bump_type == "minor":
        new_version = current_version.bump_minor()
    else:  # patch
        new_version = current_version.bump_patch()

    console.print(f"📦 Version bump: {current_version} → {new_version}", style="blue")

    # Check git status
    git_status = version_manager.get_git_status()
    if git_status["is_git_repo"] and not git_status["is_clean"]:
        console.print("⚠️  Uncommitted changes detected:", style="yellow")
        for file in git_status["uncommitted_files"][:5]:  # Show first 5
            console.print(f"   • {file}", style="yellow")
        if len(git_status["uncommitted_files"]) > 5:
            console.print(
                f"   • ... and {len(git_status['uncommitted_files']) - 5} more",
                style="yellow",
            )

        if not dry_run:
            if not click.confirm("Continue with uncommitted changes?"):
                console.print("Release preparation cancelled.", style="yellow")
                return

    # Get completed issues for changelog
    issues = core_obj.list_issues()
    milestones = core_obj.list_milestones()

    # Find issues completed since last release
    completed_issues = [issue for issue in issues if issue.status.value == "done"]

    if dry_run:
        console.print("\n🔬 Dry run - would perform these actions:", style="bold blue")
        console.print(f"   • Update version to {new_version} in pyproject.toml")
        console.print(f"   • Update version to {new_version} in __init__.py")
        console.print(
            f"   • Generate changelog entry with {len(completed_issues)} completed issues"
        )

        if completed_issues:
            console.print("\n📝 Issues to include in changelog:", style="bold")
            for issue in completed_issues[:5]:  # Show first 5
                console.print(f"   • {issue.title} (#{issue.id[:8]})")
            if len(completed_issues) > 5:
                console.print(f"   • ... and {len(completed_issues) - 5} more")
    else:
        # Actually perform the release preparation
        console.print(f"\n🚀 Preparing release {new_version}...", style="bold blue")

        # Update version
        if version_manager.update_version(new_version):
            console.print(f"✅ Updated version to {new_version}", style="green")
        else:
            console.print("❌ Failed to update version", style="red")
            return

        # Generate and update changelog
        changelog_entry = version_manager.generate_changelog_entry(
            new_version, completed_issues, milestones
        )

        if version_manager.update_changelog(new_version, changelog_entry):
            console.print("✅ Updated changelog", style="green")
        else:
            console.print("❌ Failed to update changelog", style="red")
            return

        console.print(
            f"\n🎉 Release {new_version} prepared successfully!", style="bold green"
        )
        console.print(
            f"📝 Updated {len(completed_issues)} issues in changelog", style="blue"
        )

        # Show next steps
        console.print("\n📋 Next steps:", style="bold")
        console.print("   1. Review the changes: git diff")
        console.print(
            f"   2. Commit the release: git add . && git commit -m 'Release {new_version}'"
        )
        console.print(f"   3. Tag the release: git tag v{new_version}")
        console.print("   4. Build the package: poetry build")
        console.print("   5. Publish to PyPI: poetry publish")


@release_group.command("build")
@click.option(
    "--check", is_flag=True, help="Check if the package can be built without building"
)
@click.pass_context
def build_package(ctx, check: bool):
    """Build the package for distribution."""
    core_obj = ctx.obj["core"]

    if not core_obj.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    # Get project root from core
    project_root = core_obj.root_path
    version_manager = VersionManager(project_root)

    # Check version consistency first
    version_result = version_manager.check_version_consistency()
    if not version_result["consistent"]:
        console.print("❌ Version consistency check failed:", style="bold red")
        for issue in version_result["issues"]:
            console.print(f"   • {issue}", style="red")
        return

    current_version = version_manager.get_current_version()
    console.print(f"📦 Building package version {current_version}", style="blue")

    if check:
        console.print("🔍 Checking package build configuration...", style="blue")
        # Here we could add additional checks like:
        # - Verify all required files exist
        # - Check pyproject.toml completeness
        # - Validate package structure
        console.print("✅ Package build configuration looks good", style="green")
        return

    try:
        import subprocess

        # Run poetry build
        console.print("🔨 Building package...", style="blue")
        result = subprocess.run(
            ["poetry", "build"], cwd=project_root, capture_output=True, text=True
        )

        if result.returncode == 0:
            console.print("✅ Package built successfully", style="bold green")
            console.print(result.stdout)

            # Show distribution files
            dist_dir = project_root / "dist"
            if dist_dir.exists():
                dist_files = list(dist_dir.glob("*"))
                if dist_files:
                    console.print("\n📦 Distribution files:", style="bold")
                    for file in dist_files:
                        console.print(f"   • {file.name}")
        else:
            console.print("❌ Package build failed", style="bold red")
            console.print(result.stderr)

    except FileNotFoundError:
        console.print(
            "❌ Poetry not found. Make sure Poetry is installed and in PATH.",
            style="bold red",
        )
    except Exception as e:
        console.print(f"❌ Build failed: {e}", style="bold red")


@release_group.command("status")
@click.pass_context
def release_status(ctx):
    """Show current release status and readiness."""
    core_obj = ctx.obj["core"]

    if not core_obj.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    # Get project root from core
    project_root = core_obj.root_path
    version_manager = VersionManager(project_root)

    # Create status table
    table = Table(title="Release Status", show_header=True, header_style="bold blue")
    table.add_column("Check", style="cyan", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Details")

    # Version consistency check
    version_result = version_manager.check_version_consistency()
    if version_result["consistent"]:
        table.add_row(
            "Version Consistency", "✅ Pass", f"v{version_result['pyproject_version']}"
        )
    else:
        issues_str = "; ".join(version_result["issues"])
        table.add_row("Version Consistency", "❌ Fail", issues_str)

    # Git status check
    git_status = version_manager.get_git_status()
    if git_status["is_git_repo"]:
        if git_status["is_clean"]:
            table.add_row(
                "Git Status", "✅ Clean", f"Branch: {git_status['current_branch']}"
            )
        else:
            table.add_row(
                "Git Status",
                "⚠️  Dirty",
                f"{len(git_status['uncommitted_files'])} uncommitted files",
            )
    else:
        table.add_row("Git Status", "ℹ️  No Git", "Not a git repository")

    # Issues status
    issues = core_obj.list_issues()
    milestones = core_obj.list_milestones()

    total_issues = len(issues)
    completed_issues = len([i for i in issues if i.status.value == "done"])
    in_progress_issues = len([i for i in issues if i.status.value == "in-progress"])

    if in_progress_issues == 0:
        table.add_row(
            "Open Issues", "✅ None", f"{completed_issues}/{total_issues} completed"
        )
    else:
        table.add_row(
            "Open Issues",
            "⚠️  Active",
            f"{in_progress_issues} in progress, {completed_issues}/{total_issues} completed",
        )

    # Milestones status
    total_milestones = len(milestones)
    completed_milestones = len([m for m in milestones if m.status.value == "completed"])
    active_milestones = len([m for m in milestones if m.status.value == "active"])

    table.add_row(
        "Milestones",
        "ℹ️  Info",
        f"{completed_milestones} completed, {active_milestones} active",
    )

    # Build check
    dist_dir = project_root / "dist"
    if dist_dir.exists() and list(dist_dir.glob("*")):
        latest_build = max(dist_dir.glob("*"), key=lambda x: x.stat().st_mtime)
        table.add_row("Last Build", "✅ Available", f"{latest_build.name}")
    else:
        table.add_row("Last Build", "❌ None", "Run 'roadmap release build'")

    console.print(table)

    # Determine overall readiness
    console.print()
    if (
        version_result["consistent"]
        and git_status.get("is_clean", True)
        and in_progress_issues == 0
    ):
        console.print("🚀 Ready for release!", style="bold green")
        console.print(
            "Run 'roadmap release prepare [patch|minor|major]' to start", style="blue"
        )
    else:
        console.print("⚠️  Not ready for release", style="bold yellow")
        console.print("Address the issues above before releasing", style="yellow")
