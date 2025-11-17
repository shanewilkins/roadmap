"""Timezone management CLI commands."""

import click
from rich.console import Console
from rich.prompt import Confirm

from ..timezone_migration import TimezoneDataMigrator
from ..timezone_utils import get_timezone_manager

console = Console()


@click.group(name="timezone")
@click.pass_context
def timezone_group(ctx):
    """Timezone management and migration commands."""
    pass


@timezone_group.command("status")
@click.pass_context
def timezone_status(ctx):
    """Show current timezone configuration and data status."""
    core_obj = ctx.obj["core"]

    if not core_obj.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    # Show timezone manager status
    tz_manager = get_timezone_manager()
    console.print("🌍 Timezone Manager Status", style="bold blue")
    console.print(f"   User Timezone: {tz_manager.user_timezone}")
    console.print(f"   Current UTC Time: {tz_manager.now_utc()}")
    console.print(f"   Current Local Time: {tz_manager.now_local()}")

    # Analyze data
    migrator = TimezoneDataMigrator(core_obj)
    analysis = migrator.analyze_data()

    console.print("\n📊 Data Analysis", style="bold blue")
    migrator.print_analysis_report(analysis)

    if analysis["migration_required"]:
        console.print("\n⚠️  Migration Required", style="bold yellow")
        console.print(
            "Run 'roadmap timezone migrate' to convert naive datetimes to timezone-aware format"
        )
    else:
        console.print("\n✅ All datetime data is timezone-aware", style="bold green")


@timezone_group.command("migrate")
@click.option(
    "--timezone", default="UTC", help="Timezone to assume for existing naive datetimes"
)
@click.option(
    "--dry-run", is_flag=True, help="Show what would be migrated without making changes"
)
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def migrate_timezone_data(ctx, timezone: str, dry_run: bool, force: bool):
    """Migrate existing data to timezone-aware format."""
    core_obj = ctx.obj["core"]

    if not core_obj.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    # Validate timezone
    try:
        get_timezone_manager(timezone)
    except ValueError as e:
        console.print(f"❌ Invalid timezone '{timezone}': {e}", style="bold red")
        return

    # Analyze current state
    migrator = TimezoneDataMigrator(core_obj)
    analysis = migrator.analyze_data()

    if not analysis["migration_required"]:
        console.print(
            "✅ No migration required - all data is already timezone-aware",
            style="green",
        )
        return

    console.print("🔍 Migration Analysis:", style="bold blue")
    migrator.print_analysis_report(analysis)

    console.print("\n📋 Migration Plan:", style="bold blue")
    console.print(f"   • Assume timezone: {timezone}")
    console.print(f"   • Issues to migrate: {analysis['issues_with_naive_dates']}")
    console.print(
        f"   • Milestones to migrate: {analysis['milestones_with_naive_dates']}"
    )
    console.print(f"   • Mode: {'Dry run' if dry_run else 'Live migration'}")

    if not dry_run and not force:
        console.print(
            "\n⚠️  This will permanently modify your roadmap data!", style="bold yellow"
        )
        console.print("A backup will be created before migration.")

        if not Confirm.ask("Do you want to proceed with the migration?"):
            console.print("Migration cancelled.", style="yellow")
            return

    # Perform migration
    console.print("\n🚀 Starting migration...", style="bold blue")
    results = migrator.migrate_all_data(timezone, dry_run)

    if "error" in results:
        console.print(f"❌ Migration failed: {results['error']}", style="bold red")
        return

    # Show results
    console.print("\n📊 Migration Results:", style="bold blue")
    migrator.print_migration_report(
        results["results"] if "results" in results else results
    )

    if not dry_run:
        # Verify migration
        console.print("\n🔍 Verifying migration...", style="blue")
        verification = migrator.verify_migration()

        if verification["migration_successful"]:
            console.print("✅ Migration completed successfully!", style="bold green")
            console.print(f"   • {verification['issues_checked']} issues verified")
            console.print(
                f"   • {verification['milestones_checked']} milestones verified"
            )
        else:
            console.print("⚠️  Migration verification failed:", style="bold yellow")
            console.print(
                f"   • {verification['issues_with_naive_dates']} issues still have naive dates"
            )
            console.print(
                f"   • {verification['milestones_with_naive_dates']} milestones still have naive dates"
            )

        # Save log
        log_file = migrator.save_migration_log()
        console.print(f"\n📝 Migration log saved: {log_file}", style="blue")


@timezone_group.command("config")
@click.option("--timezone", help="Set user timezone preference")
@click.option("--show", is_flag=True, help="Show current timezone configuration")
@click.pass_context
def timezone_config(ctx, timezone: str | None, show: bool):
    """Configure timezone preferences."""
    core_obj = ctx.obj["core"]

    if not core_obj.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    tz_manager = get_timezone_manager()

    if show or (not timezone):
        console.print("🌍 Current Timezone Configuration:", style="bold blue")
        console.print(f"   User Timezone: {tz_manager.user_timezone}")
        console.print(f"   System Detected: {tz_manager._detect_system_timezone()}")
        console.print(f"   Current UTC: {tz_manager.now_utc()}")
        console.print(f"   Current Local: {tz_manager.now_local()}")

        console.print("\n🌐 Common Timezones:", style="bold blue")
        common_timezones = tz_manager.get_common_timezones()
        for _i, tz in enumerate(common_timezones[:10]):  # Show first 10
            console.print(f"   {tz}")

        if len(common_timezones) > 10:
            console.print(f"   ... and {len(common_timezones) - 10} more")

        return

    # Set new timezone
    try:
        # Validate timezone
        new_manager = get_timezone_manager(timezone)
        console.print(f"✅ Timezone set to: {timezone}", style="green")
        console.print(f"   Current time in {timezone}: {new_manager.now_local()}")

        # TODO: Save timezone preference to user config
        console.print(
            "ℹ️  Note: Timezone preference is set for this session only.", style="blue"
        )
        console.print("Future versions will support persistent timezone configuration.")

    except ValueError as e:
        console.print(f"❌ Invalid timezone '{timezone}': {e}", style="bold red")
        console.print(
            "Use 'roadmap timezone config --show' to see available timezones."
        )


@timezone_group.command("test")
@click.argument("date_string")
@click.option("--input-timezone", help="Timezone to assume for input")
@click.option("--display-timezone", help="Timezone for display")
@click.pass_context
def test_timezone_parsing(
    ctx, date_string: str, input_timezone: str | None, display_timezone: str | None
):
    """Test timezone parsing and formatting with different inputs."""
    tz_manager = get_timezone_manager(display_timezone)

    console.print("🧪 Testing Timezone Parsing:", style="bold blue")
    console.print(f"   Input: '{date_string}'")
    console.print(f"   Input Timezone: {input_timezone or tz_manager.user_timezone}")
    console.print(
        f"   Display Timezone: {display_timezone or tz_manager.user_timezone}"
    )

    try:
        # Parse the date
        parsed_dt = tz_manager.parse_user_input(date_string, input_timezone)
        console.print("\n✅ Parsing successful:", style="green")
        console.print(f"   UTC: {parsed_dt}")
        console.print(f"   Local: {tz_manager.format_for_user(parsed_dt)}")
        console.print(f"   Relative: {tz_manager.format_relative(parsed_dt)}")
        console.print(f"   ISO Format: {parsed_dt.isoformat()}")

    except ValueError as e:
        console.print(f"\n❌ Parsing failed: {e}", style="red")
        console.print("Examples of valid formats:", style="blue")
        console.print("   • 2025-12-31")
        console.print("   • 2025-12-31 23:59:59")
        console.print("   • 2025-12-31T23:59:59")
        console.print("   • 2025-12-31T23:59:59Z")
        console.print("   • 2025-12-31T23:59:59+05:00")
