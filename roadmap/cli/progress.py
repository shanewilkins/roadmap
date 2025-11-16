"""
Progress calculation and reporting CLI commands.

This module provides CLI commands for manual progress recalculation and reporting,
implementing the CLI integration requirements from issue 515a927c.
"""

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TaskID
import os
from datetime import datetime

# Initialize console for rich output with test mode detection
is_testing = "PYTEST_CURRENT_TEST" in os.environ or os.environ.get("NO_COLOR") == "1"
console = Console(force_terminal=not is_testing, no_color=is_testing)

from ..progress import ProgressCalculationEngine, ProgressEventSystem


@click.group()
def recalculate_progress():
    """Recalculate milestone and project progress."""
    pass


@recalculate_progress.command("milestone")
@click.argument("milestone_name")
@click.option("--method", type=click.Choice(["effort_weighted", "count_based"]), default="effort_weighted", help="Calculation method")
@click.pass_context
def recalculate_milestone(ctx: click.Context, milestone_name: str, method: str):
    """Recalculate progress for a specific milestone."""
    core = ctx.obj["core"]
    
    try:
        # Load all data
        all_issues = core.list_issues()
        all_milestones = core.list_milestones()
        
        # Find the milestone
        milestone = None
        for m in all_milestones:
            if m.name == milestone_name:
                milestone = m
                break
        
        if not milestone:
            console.print(f"❌ Milestone '{milestone_name}' not found", style="bold red")
            return
        
        # Create progress engine and update
        engine = ProgressCalculationEngine(method=method)
        old_progress = milestone.calculated_progress
        
        updated = engine.update_milestone_progress(milestone, all_issues)
        
        if updated:
            # Save the updated milestone
            from roadmap.parser import MilestoneParser
            milestone_file = core.milestones_dir / f"{milestone.name}.md"
            MilestoneParser.save_milestone_file(milestone, milestone_file)
            
            console.print(f"✅ Updated milestone '{milestone_name}':", style="bold green")
            console.print(f"   Progress: {old_progress or 0:.1f}% → {milestone.calculated_progress:.1f}%")
            console.print(f"   Status: {milestone.status}")
            console.print(f"   Method: {method}")
        else:
            console.print(f"ℹ️  Milestone '{milestone_name}' progress unchanged", style="blue")
            console.print(f"   Current progress: {milestone.calculated_progress or 0:.1f}%")
    
    except Exception as e:
        console.print(f"❌ Failed to recalculate milestone progress: {e}", style="bold red")


@recalculate_progress.command("project")
@click.argument("project_id")
@click.option("--method", type=click.Choice(["effort_weighted", "count_based"]), default="effort_weighted", help="Calculation method")
@click.pass_context
def recalculate_project(ctx: click.Context, project_id: str, method: str):
    """Recalculate progress for a specific project."""
    core = ctx.obj["core"]
    
    try:
        # Load all data
        all_issues = core.list_issues()
        all_milestones = core.list_milestones()
        all_projects = core.list_projects()  # This method needs to be implemented
        
        # Find the project
        project = None
        for p in all_projects:
            if p.id.startswith(project_id):
                project = p
                break
        
        if not project:
            console.print(f"❌ Project '{project_id}' not found", style="bold red")
            return
        
        # Create progress engine and update
        engine = ProgressCalculationEngine(method=method)
        old_progress = project.calculated_progress
        
        updated = engine.update_project_progress(project, all_milestones, all_issues)
        
        if updated:
            # Save the updated project (this method needs to be implemented)
            core.save_project(project)
            
            console.print(f"✅ Updated project '{project.name}':", style="bold green")
            console.print(f"   Progress: {old_progress or 0:.1f}% → {project.calculated_progress:.1f}%")
            console.print(f"   Status: {project.status}")
            console.print(f"   Risk Level: {project.risk_level}")
            if project.projected_end_date:
                console.print(f"   Projected End: {project.projected_end_date.strftime('%Y-%m-%d')}")
            if project.schedule_variance:
                variance_str = f"{abs(project.schedule_variance)} days {'ahead' if project.schedule_variance < 0 else 'behind'}"
                console.print(f"   Schedule Variance: {variance_str}")
        else:
            console.print(f"ℹ️  Project '{project.name}' progress unchanged", style="blue")
            console.print(f"   Current progress: {project.calculated_progress or 0:.1f}%")
    
    except Exception as e:
        console.print(f"❌ Failed to recalculate project progress: {e}", style="bold red")


@recalculate_progress.command("all")
@click.option("--method", type=click.Choice(["effort_weighted", "count_based"]), default="effort_weighted", help="Calculation method")
@click.pass_context
def recalculate_all(ctx: click.Context, method: str):
    """Recalculate progress for all milestones and projects."""
    core = ctx.obj["core"]
    
    try:
        # Load all data
        all_issues = core.list_issues()
        all_milestones = core.list_milestones()
        all_projects = core.list_projects()
        
        # Create progress engine
        engine = ProgressCalculationEngine(method=method)
        
        console.print("🔄 Recalculating all progress...", style="bold blue")
        
        with Progress() as progress:
            task = progress.add_task("Updating progress...", total=len(all_milestones) + len(all_projects))
            
            # Update milestones
            updated_milestones = 0
            for milestone in all_milestones:
                if engine.update_milestone_progress(milestone, all_issues):
                    from roadmap.parser import MilestoneParser
                    milestone_file = core.milestones_dir / f"{milestone.name}.md"
                    MilestoneParser.save_milestone_file(milestone, milestone_file)
                    updated_milestones += 1
                progress.advance(task)
            
            # Update projects
            updated_projects = 0
            for project in all_projects:
                if engine.update_project_progress(project, all_milestones, all_issues):
                    from roadmap.parser import ProjectParser
                    project_file = core.projects_dir / f"{project.id}.md"
                    ProjectParser.save_project_file(project, project_file)
                    updated_projects += 1
                progress.advance(task)
        
        console.print(f"✅ Recalculation complete:", style="bold green")
        console.print(f"   {updated_milestones}/{len(all_milestones)} milestones updated")
        console.print(f"   {updated_projects}/{len(all_projects)} projects updated")
        console.print(f"   Method: {method}")
    
    except Exception as e:
        console.print(f"❌ Failed to recalculate progress: {e}", style="bold red")


@click.group()
def progress_reports():
    """View progress reports and status."""
    pass


@progress_reports.command("milestone")
@click.argument("milestone_name")
@click.option("--show-issues", is_flag=True, help="Show detailed issue breakdown")
@click.pass_context
def milestone_status(ctx: click.Context, milestone_name: str, show_issues: bool):
    """Show detailed progress status for a milestone."""
    core = ctx.obj["core"]
    
    try:
        # Load data
        all_issues = core.list_issues()
        all_milestones = core.list_milestones()
        
        # Find the milestone
        milestone = None
        for m in all_milestones:
            if m.name == milestone_name:
                milestone = m
                break
        
        if not milestone:
            console.print(f"❌ Milestone '{milestone_name}' not found", style="bold red")
            return
        
        # Display milestone status
        console.print(f"\n📍 Milestone: {milestone.name}", style="bold blue")
        console.print(f"Status: {milestone.status}")
        
        progress_value = milestone.calculated_progress or milestone.get_completion_percentage(all_issues)
        console.print(f"Progress: {progress_value:.1f}%")
        
        if milestone.due_date:
            console.print(f"Due Date: {milestone.due_date.strftime('%Y-%m-%d')}")
        
        if milestone.actual_start_date:
            console.print(f"Started: {milestone.actual_start_date.strftime('%Y-%m-%d')}")
        
        if milestone.actual_end_date:
            console.print(f"Completed: {milestone.actual_end_date.strftime('%Y-%m-%d')}")
        
        if milestone.risk_level:
            console.print(f"Risk Level: {milestone.risk_level}")
        
        # Show issue breakdown if requested
        if show_issues:
            milestone_issues = milestone.get_issues(all_issues)
            
            if milestone_issues:
                console.print(f"\n📋 Issues ({len(milestone_issues)} total):")
                
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("ID")
                table.add_column("Title", min_width=30)
                table.add_column("Status")
                table.add_column("Progress")
                table.add_column("Effort")
                
                for issue in sorted(milestone_issues, key=lambda x: x.status.value):
                    effort = f"{issue.estimated_hours:.1f}h" if issue.estimated_hours else "Not estimated"
                    progress_str = f"{issue.progress_percentage:.0f}%" if issue.progress_percentage else "0%"
                    
                    table.add_row(
                        issue.id[:8],
                        issue.title[:40] + "..." if len(issue.title) > 40 else issue.title,
                        issue.status.value,
                        progress_str,
                        effort
                    )
                
                console.print(table)
            else:
                console.print(f"\nNo issues assigned to this milestone")
    
    except Exception as e:
        console.print(f"❌ Failed to show milestone status: {e}", style="bold red")


@progress_reports.command("project")
@click.argument("project_id")
@click.option("--show-milestones", is_flag=True, help="Show detailed milestone breakdown")
@click.option("--show-timeline", is_flag=True, help="Show timeline information")
@click.pass_context
def project_status(ctx: click.Context, project_id: str, show_milestones: bool, show_timeline: bool):
    """Show detailed progress status for a project."""
    core = ctx.obj["core"]
    
    try:
        # Load data
        all_issues = core.list_issues()
        all_milestones = core.list_milestones()
        all_projects = core.list_projects()
        
        # Find the project
        project = None
        for p in all_projects:
            if p.id.startswith(project_id):
                project = p
                break
        
        if not project:
            console.print(f"❌ Project '{project_id}' not found", style="bold red")
            return
        
        # Display project status
        console.print(f"\n🎯 Project: {project.name}", style="bold blue")
        console.print(f"Status: {project.status}")
        console.print(f"Progress: {project.calculated_progress or 0:.1f}%")
        console.print(f"Priority: {project.priority}")
        console.print(f"Risk Level: {project.risk_level}")
        
        if project.owner:
            console.print(f"Owner: {project.owner}")
        
        # Timeline information
        if show_timeline:
            console.print(f"\n📅 Timeline:")
            if project.start_date:
                console.print(f"Start Date: {project.start_date.strftime('%Y-%m-%d')}")
            if project.target_end_date:
                console.print(f"Target End: {project.target_end_date.strftime('%Y-%m-%d')}")
            if project.projected_end_date:
                console.print(f"Projected End: {project.projected_end_date.strftime('%Y-%m-%d')}")
            if project.actual_end_date:
                console.print(f"Actual End: {project.actual_end_date.strftime('%Y-%m-%d')}")
            if project.schedule_variance:
                variance_str = f"{abs(project.schedule_variance)} days {'ahead' if project.schedule_variance < 0 else 'behind'}"
                console.print(f"Schedule Variance: {variance_str}")
            if project.completion_velocity:
                console.print(f"Velocity: {project.completion_velocity:.2f} milestones/week")
        
        # Show milestone breakdown if requested
        if show_milestones:
            project_milestones = project.get_milestones(all_milestones)
            
            if project_milestones:
                console.print(f"\n🎯 Milestones ({len(project_milestones)} total):")
                
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("Name", min_width=20)
                table.add_column("Status")
                table.add_column("Progress")
                table.add_column("Due Date")
                table.add_column("Issues")
                
                # Sort milestones by due date, handling timezone issues
                def get_sortable_date(milestone):
                    due_date = milestone.due_date
                    if due_date is None:
                        return datetime.min
                    # Convert timezone-aware dates to naive for comparison
                    if due_date.tzinfo is not None:
                        return due_date.replace(tzinfo=None)
                    return due_date
                
                for milestone in sorted(project_milestones, key=get_sortable_date):
                    progress_value = milestone.calculated_progress or milestone.get_completion_percentage(all_issues)
                    due_date_str = milestone.due_date.strftime('%Y-%m-%d') if milestone.due_date else "No due date"
                    issue_count = milestone.get_issue_count(all_issues)
                    
                    table.add_row(
                        milestone.name,
                        milestone.status.value,
                        f"{progress_value:.1f}%",
                        due_date_str,
                        str(issue_count)
                    )
                
                console.print(table)
            else:
                console.print(f"\nNo milestones assigned to this project")
    
    except Exception as e:
        console.print(f"❌ Failed to show project status: {e}", style="bold red")