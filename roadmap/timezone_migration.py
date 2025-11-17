"""Data migration utilities for timezone-aware datetime conversion.

This module provides utilities to migrate existing roadmap data from
timezone-naive to timezone-aware datetime format.
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from rich.console import Console
from rich.progress import Progress, TaskID
from rich.table import Table

from .core import RoadmapCore
from .file_utils import ensure_directory_exists
from .models import Issue, Milestone
from .timezone_utils import migrate_naive_datetime, now_utc
from .parser import IssueParser, MilestoneParser


console = Console()


class TimezoneDataMigrator:
    """Handles migration of roadmap data to timezone-aware format."""
    
    def __init__(self, roadmap_core: RoadmapCore):
        """Initialize migrator with roadmap core instance."""
        self.core = roadmap_core
        self.backup_dir = self.core.roadmap_dir / "backups" / "timezone_migration"
        self.migration_log: List[str] = []
    
    def analyze_data(self) -> dict:
        """Analyze existing data to determine migration scope."""
        analysis = {
            "total_issues": 0,
            "issues_with_naive_dates": 0,
            "total_milestones": 0,
            "milestones_with_naive_dates": 0,
            "naive_date_fields": [],
            "migration_required": False
        }
        
        # Analyze issues
        try:
            issues = self.core.list_issues()
            analysis["total_issues"] = len(issues)
            
            for issue in issues:
                naive_fields = []
                
                if issue.created and issue.created.tzinfo is None:
                    naive_fields.append("created")
                if issue.updated and issue.updated.tzinfo is None:
                    naive_fields.append("updated")
                if issue.due_date and issue.due_date.tzinfo is None:
                    naive_fields.append("due_date")
                if issue.actual_start_date and issue.actual_start_date.tzinfo is None:
                    naive_fields.append("actual_start_date")
                if issue.actual_end_date and issue.actual_end_date.tzinfo is None:
                    naive_fields.append("actual_end_date")
                if issue.handoff_date and issue.handoff_date.tzinfo is None:
                    naive_fields.append("handoff_date")
                
                if naive_fields:
                    analysis["issues_with_naive_dates"] += 1
                    analysis["naive_date_fields"].extend(naive_fields)
                    
        except Exception as e:
            console.print(f"⚠️  Error analyzing issues: {e}", style="yellow")
        
        # Analyze milestones
        try:
            milestones = self.core.list_milestones()
            analysis["total_milestones"] = len(milestones)
            
            for milestone in milestones:
                naive_fields = []
                
                if milestone.created and milestone.created.tzinfo is None:
                    naive_fields.append("created")
                if milestone.updated and milestone.updated.tzinfo is None:
                    naive_fields.append("updated")
                if milestone.due_date and milestone.due_date.tzinfo is None:
                    naive_fields.append("due_date")
                if milestone.actual_start_date and milestone.actual_start_date.tzinfo is None:
                    naive_fields.append("actual_start_date")
                if milestone.actual_end_date and milestone.actual_end_date.tzinfo is None:
                    naive_fields.append("actual_end_date")
                if milestone.last_progress_update and milestone.last_progress_update.tzinfo is None:
                    naive_fields.append("last_progress_update")
                
                if naive_fields:
                    analysis["milestones_with_naive_dates"] += 1
                    analysis["naive_date_fields"].extend(naive_fields)
                    
        except Exception as e:
            console.print(f"⚠️  Error analyzing milestones: {e}", style="yellow")
        
        # Determine if migration is required
        analysis["migration_required"] = (
            analysis["issues_with_naive_dates"] > 0 or 
            analysis["milestones_with_naive_dates"] > 0
        )
        
        # Count unique field types
        analysis["unique_naive_fields"] = list(set(analysis["naive_date_fields"]))
        
        return analysis
    
    def create_backup(self) -> bool:
        """Create backup of current data before migration."""
        try:
            # Create backup directory
            ensure_directory_exists(self.backup_dir)
            
            # Create timestamped backup
            timestamp = now_utc().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"pre_timezone_migration_{timestamp}"
            ensure_directory_exists(backup_path)
            
            # Copy issues directory
            if self.core.issues_dir.exists():
                import shutil
                shutil.copytree(
                    self.core.issues_dir, 
                    backup_path / "issues",
                    dirs_exist_ok=True
                )
            
            # Copy milestones directory
            if self.core.milestones_dir.exists():
                import shutil
                shutil.copytree(
                    self.core.milestones_dir, 
                    backup_path / "milestones",
                    dirs_exist_ok=True
                )
            
            # Copy config file
            if self.core.config_file.exists():
                import shutil
                shutil.copy2(self.core.config_file, backup_path / "config.yaml")
            
            self.migration_log.append(f"✅ Backup created at: {backup_path}")
            console.print(f"✅ Backup created at: {backup_path}", style="green")
            return True
            
        except Exception as e:
            self.migration_log.append(f"❌ Backup failed: {e}")
            console.print(f"❌ Backup failed: {e}", style="red")
            return False
    
    def migrate_issue(self, issue: Issue, assumed_timezone: str = "UTC") -> Issue:
        """Migrate a single issue to timezone-aware format."""
        # Create a copy to avoid modifying original
        migrated_issue = issue.model_copy()
        
        # Migrate datetime fields
        if issue.created and issue.created.tzinfo is None:
            migrated_issue.created = migrate_naive_datetime(issue.created, assumed_timezone)
        
        if issue.updated and issue.updated.tzinfo is None:
            migrated_issue.updated = migrate_naive_datetime(issue.updated, assumed_timezone)
        
        if issue.due_date and issue.due_date.tzinfo is None:
            migrated_issue.due_date = migrate_naive_datetime(issue.due_date, assumed_timezone)
        
        if issue.actual_start_date and issue.actual_start_date.tzinfo is None:
            migrated_issue.actual_start_date = migrate_naive_datetime(issue.actual_start_date, assumed_timezone)
        
        if issue.actual_end_date and issue.actual_end_date.tzinfo is None:
            migrated_issue.actual_end_date = migrate_naive_datetime(issue.actual_end_date, assumed_timezone)
        
        if issue.handoff_date and issue.handoff_date.tzinfo is None:
            migrated_issue.handoff_date = migrate_naive_datetime(issue.handoff_date, assumed_timezone)
        
        return migrated_issue
    
    def migrate_milestone(self, milestone: Milestone, assumed_timezone: str = "UTC") -> Milestone:
        """Migrate a single milestone to timezone-aware format."""
        # Create a copy to avoid modifying original
        migrated_milestone = milestone.model_copy()
        
        # Migrate datetime fields
        if milestone.created and milestone.created.tzinfo is None:
            migrated_milestone.created = migrate_naive_datetime(milestone.created, assumed_timezone)
        
        if milestone.updated and milestone.updated.tzinfo is None:
            migrated_milestone.updated = migrate_naive_datetime(milestone.updated, assumed_timezone)
        
        if milestone.due_date and milestone.due_date.tzinfo is None:
            migrated_milestone.due_date = migrate_naive_datetime(milestone.due_date, assumed_timezone)
        
        if milestone.actual_start_date and milestone.actual_start_date.tzinfo is None:
            migrated_milestone.actual_start_date = migrate_naive_datetime(milestone.actual_start_date, assumed_timezone)
        
        if milestone.actual_end_date and milestone.actual_end_date.tzinfo is None:
            migrated_milestone.actual_end_date = migrate_naive_datetime(milestone.actual_end_date, assumed_timezone)
        
        if milestone.last_progress_update and milestone.last_progress_update.tzinfo is None:
            migrated_milestone.last_progress_update = migrate_naive_datetime(milestone.last_progress_update, assumed_timezone)
        
        return migrated_milestone
    
    def migrate_all_data(self, assumed_timezone: str = "UTC", dry_run: bool = False) -> dict:
        """Migrate all roadmap data to timezone-aware format."""
        results = {
            "issues_migrated": 0,
            "milestones_migrated": 0,
            "errors": [],
            "dry_run": dry_run
        }
        
        if not dry_run:
            # Create backup first
            if not self.create_backup():
                return {"error": "Failed to create backup", "results": results}
        
        # Migrate issues
        try:
            issues = self.core.list_issues()
            
            with Progress() as progress:
                if issues:
                    task = progress.add_task("Migrating issues...", total=len(issues))
                    
                    for issue in issues:
                        try:
                            # Check if migration is needed
                            needs_migration = any([
                                issue.created and issue.created.tzinfo is None,
                                issue.updated and issue.updated.tzinfo is None,
                                issue.due_date and issue.due_date.tzinfo is None,
                                issue.actual_start_date and issue.actual_start_date.tzinfo is None,
                                issue.actual_end_date and issue.actual_end_date.tzinfo is None,
                                issue.handoff_date and issue.handoff_date.tzinfo is None,
                            ])
                            
                            if needs_migration:
                                migrated_issue = self.migrate_issue(issue, assumed_timezone)
                                
                                if not dry_run:
                                    # Update the issue using core method with specific timezone-aware fields
                                    try:
                                        update_fields = {}
                                        if migrated_issue.created != issue.created:
                                            update_fields['created'] = migrated_issue.created
                                        if migrated_issue.updated != issue.updated:
                                            update_fields['updated'] = migrated_issue.updated
                                        if migrated_issue.due_date != issue.due_date:
                                            update_fields['due_date'] = migrated_issue.due_date
                                        if migrated_issue.actual_start_date != issue.actual_start_date:
                                            update_fields['actual_start_date'] = migrated_issue.actual_start_date
                                        if migrated_issue.actual_end_date != issue.actual_end_date:
                                            update_fields['actual_end_date'] = migrated_issue.actual_end_date
                                        if migrated_issue.handoff_date != issue.handoff_date:
                                            update_fields['handoff_date'] = migrated_issue.handoff_date
                                        
                                        if update_fields:
                                            # Use core's update method
                                            self.core.update_issue(migrated_issue.id, **update_fields)
                                    except Exception as e:
                                        # If core update fails, try direct file manipulation
                                        issue_file = None
                                        for potential_file in self.core.issues_dir.glob(f"{migrated_issue.id}-*.md"):
                                            issue_file = potential_file
                                            break
                                        
                                        if issue_file and issue_file.exists():
                                            self._update_datetime_in_file(issue_file, issue, migrated_issue)
                                
                                results["issues_migrated"] += 1
                                self.migration_log.append(f"✅ Migrated issue: {issue.id} - {issue.title}")
                            
                            progress.advance(task)
                            
                        except Exception as e:
                            error_msg = f"Failed to migrate issue {issue.id}: {e}"
                            results["errors"].append(error_msg)
                            self.migration_log.append(f"❌ {error_msg}")
                            
        except Exception as e:
            error_msg = f"Failed to load issues: {e}"
            results["errors"].append(error_msg)
            self.migration_log.append(f"❌ {error_msg}")
        
        # Migrate milestones
        try:
            milestones = self.core.list_milestones()
            
            with Progress() as progress:
                if milestones:
                    task = progress.add_task("Migrating milestones...", total=len(milestones))
                    
                    for milestone in milestones:
                        try:
                            # Check if migration is needed
                            needs_migration = any([
                                milestone.created and milestone.created.tzinfo is None,
                                milestone.updated and milestone.updated.tzinfo is None,
                                milestone.due_date and milestone.due_date.tzinfo is None,
                                milestone.actual_start_date and milestone.actual_start_date.tzinfo is None,
                                milestone.actual_end_date and milestone.actual_end_date.tzinfo is None,
                                milestone.last_progress_update and milestone.last_progress_update.tzinfo is None,
                            ])
                            
                            if needs_migration:
                                migrated_milestone = self.migrate_milestone(milestone, assumed_timezone)
                                
                                if not dry_run:
                                    # Update the milestone using core method with specific timezone-aware fields
                                    try:
                                        update_fields = {}
                                        if migrated_milestone.due_date != milestone.due_date:
                                            update_fields['due_date'] = migrated_milestone.due_date
                                        
                                        if update_fields:
                                            # Only update due_date through core method since that's what it supports
                                            self.core.update_milestone(migrated_milestone.name, **update_fields)
                                        
                                        # For other datetime fields, update the file directly
                                        milestone_file = self.core.milestones_dir / f"{migrated_milestone.name}.md"
                                        if milestone_file.exists():
                                            self._update_datetime_in_file(milestone_file, milestone, migrated_milestone)
                                            
                                    except Exception as e:
                                        # If core update fails, try direct file manipulation
                                        milestone_file = self.core.milestones_dir / f"{migrated_milestone.name}.md"
                                        if milestone_file.exists():
                                            self._update_datetime_in_file(milestone_file, milestone, migrated_milestone)
                                
                                results["milestones_migrated"] += 1
                                self.migration_log.append(f"✅ Migrated milestone: {milestone.name}")
                            
                            progress.advance(task)
                            
                        except Exception as e:
                            error_msg = f"Failed to migrate milestone {milestone.name}: {e}"
                            results["errors"].append(error_msg)
                            self.migration_log.append(f"❌ {error_msg}")
                            
        except Exception as e:
            error_msg = f"Failed to load milestones: {e}"
            results["errors"].append(error_msg)
            self.migration_log.append(f"❌ {error_msg}")
        
        return results
    
    def verify_migration(self) -> dict:
        """Verify that migration was successful."""
        verification = {
            "issues_with_naive_dates": 0,
            "milestones_with_naive_dates": 0,
            "migration_successful": False,
            "issues_checked": 0,
            "milestones_checked": 0
        }
        
        # Check issues
        try:
            issues = self.core.list_issues()
            verification["issues_checked"] = len(issues)
            
            for issue in issues:
                has_naive = any([
                    issue.created and issue.created.tzinfo is None,
                    issue.updated and issue.updated.tzinfo is None,
                    issue.due_date and issue.due_date.tzinfo is None,
                    issue.actual_start_date and issue.actual_start_date.tzinfo is None,
                    issue.actual_end_date and issue.actual_end_date.tzinfo is None,
                    issue.handoff_date and issue.handoff_date.tzinfo is None,
                ])
                
                if has_naive:
                    verification["issues_with_naive_dates"] += 1
                    
        except Exception as e:
            console.print(f"⚠️  Error verifying issues: {e}", style="yellow")
        
        # Check milestones
        try:
            milestones = self.core.list_milestones()
            verification["milestones_checked"] = len(milestones)
            
            for milestone in milestones:
                has_naive = any([
                    milestone.created and milestone.created.tzinfo is None,
                    milestone.updated and milestone.updated.tzinfo is None,
                    milestone.due_date and milestone.due_date.tzinfo is None,
                    milestone.actual_start_date and milestone.actual_start_date.tzinfo is None,
                    milestone.actual_end_date and milestone.actual_end_date.tzinfo is None,
                    milestone.last_progress_update and milestone.last_progress_update.tzinfo is None,
                ])
                
                if has_naive:
                    verification["milestones_with_naive_dates"] += 1
                    
        except Exception as e:
            console.print(f"⚠️  Error verifying milestones: {e}", style="yellow")
        
        # Migration is successful if no naive dates remain
        verification["migration_successful"] = (
            verification["issues_with_naive_dates"] == 0 and 
            verification["milestones_with_naive_dates"] == 0
        )
        
        return verification
    
    def print_analysis_report(self, analysis: dict) -> None:
        """Print a detailed analysis report."""
        table = Table(title="Timezone Migration Analysis", show_header=True, header_style="bold blue")
        table.add_column("Category", style="cyan", no_wrap=True)
        table.add_column("Count", justify="right")
        table.add_column("Details")
        
        table.add_row("Total Issues", str(analysis["total_issues"]), "")
        table.add_row("Issues with Naive Dates", str(analysis["issues_with_naive_dates"]), 
                     f"{(analysis['issues_with_naive_dates']/max(1,analysis['total_issues'])*100):.1f}%")
        
        table.add_row("Total Milestones", str(analysis["total_milestones"]), "")
        table.add_row("Milestones with Naive Dates", str(analysis["milestones_with_naive_dates"]),
                     f"{(analysis['milestones_with_naive_dates']/max(1,analysis['total_milestones'])*100):.1f}%")
        
        table.add_row("Unique Date Fields", str(len(analysis["unique_naive_fields"])), 
                     ", ".join(analysis["unique_naive_fields"][:5]))
        
        migration_status = "✅ Required" if analysis["migration_required"] else "✅ Not Required"
        table.add_row("Migration Required", migration_status, "")
        
        console.print(table)
    
    def print_migration_report(self, results: dict) -> None:
        """Print a detailed migration report."""
        table = Table(title="Migration Results", show_header=True, header_style="bold blue")
        table.add_column("Category", style="cyan", no_wrap=True)
        table.add_column("Count", justify="right")
        table.add_column("Status")
        
        table.add_row("Issues Migrated", str(results["issues_migrated"]), "✅ Success")
        table.add_row("Milestones Migrated", str(results["milestones_migrated"]), "✅ Success")
        table.add_row("Errors", str(len(results["errors"])), 
                     "❌ Failed" if results["errors"] else "✅ None")
        
        mode = "🔬 Dry Run" if results["dry_run"] else "🚀 Live Migration"
        table.add_row("Mode", mode, "")
        
        console.print(table)
        
        if results["errors"]:
            console.print("\n❌ Errors encountered:", style="bold red")
            for error in results["errors"]:
                console.print(f"   • {error}", style="red")
    
    def save_migration_log(self) -> Path:
        """Save migration log to file."""
        log_file = self.backup_dir / f"migration_log_{now_utc().strftime('%Y%m%d_%H%M%S')}.txt"
        ensure_directory_exists(log_file.parent)
        
        with open(log_file, 'w') as f:
            f.write(f"Timezone Migration Log\n")
            f.write(f"Generated: {now_utc().isoformat()}\n")
            f.write("=" * 50 + "\n\n")
            
            for entry in self.migration_log:
                f.write(f"{entry}\n")
        
        return log_file
    
    def _update_datetime_in_file(self, file_path: Path, original_obj, migrated_obj) -> None:
        """Update datetime fields directly in markdown file."""
        try:
            # Read the current file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split into frontmatter and body
            if content.startswith('---\n'):
                parts = content.split('---\n', 2)
                if len(parts) >= 3:
                    frontmatter_content = parts[1]
                    body = parts[2]
                    
                    # Parse the frontmatter
                    import yaml
                    frontmatter_data = yaml.safe_load(frontmatter_content)
                    
                    # Update datetime fields that have changed
                    datetime_fields = ['created', 'updated', 'due_date', 'actual_start_date', 
                                     'actual_end_date', 'handoff_date', 'last_progress_update']
                    
                    for field in datetime_fields:
                        original_val = getattr(original_obj, field, None)
                        migrated_val = getattr(migrated_obj, field, None)
                        
                        if (original_val is not None and migrated_val is not None and 
                            original_val != migrated_val):
                            # Update the field with timezone-aware datetime
                            frontmatter_data[field] = migrated_val.isoformat()
                    
                    # Write back the updated content
                    updated_frontmatter = yaml.dump(frontmatter_data, default_flow_style=False, sort_keys=False)
                    updated_content = f"---\n{updated_frontmatter}---\n{body}"
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(updated_content)
                        
        except Exception as e:
            self.migration_log.append(f"❌ Failed to update file {file_path}: {e}")
            raise e