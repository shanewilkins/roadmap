"""
Deprecated commands for backward compatibility.
"""

import click
from rich.console import Console

console = Console()

def register_deprecated_commands(main_group):
    """Register deprecated commands to the main CLI group."""
    
    @main_group.command()
    @click.option("--days", "-d", default=30, help="Number of days to forecast")
    @click.option("--assignee", "-a", help="Filter by specific assignee")
    @click.pass_context
    def capacity_forecast(ctx: click.Context, days: int, assignee: str):
        """[DEPRECATED] Forecast team capacity and bottlenecks.
        
        ⚠️  DEPRECATION WARNING: Use 'roadmap team forecast-capacity' instead.
        """
        console.print("⚠️  DEPRECATION WARNING: 'roadmap capacity-forecast' is deprecated.", style="yellow")
        console.print("   Use 'roadmap team forecast-capacity' instead for better organization.", style="yellow")
        
        # Delegate to new command
        from .team import _original_capacity_forecast
        _original_capacity_forecast(ctx, days, assignee)

    @main_group.command()
    @click.option("--assignee", "-a", help="Analyze workload for specific assignee")
    @click.option("--include-estimates", is_flag=True, help="Include time estimates in analysis")
    @click.option("--suggest-rebalance", is_flag=True, help="Suggest workload rebalancing")
    @click.pass_context
    def workload_analysis(ctx: click.Context, assignee: str, include_estimates: bool, suggest_rebalance: bool):
        """[DEPRECATED] Analyze team workload and capacity.
        
        ⚠️  DEPRECATION WARNING: Use 'roadmap team analyze-workload' instead.
        """
        console.print("⚠️  DEPRECATION WARNING: 'roadmap workload-analysis' is deprecated.", style="yellow")
        console.print("   Use 'roadmap team analyze-workload' instead for better organization.", style="yellow")
        
        # Delegate to new command
        from .team import _original_workload_analysis
        _original_workload_analysis(ctx, assignee, include_estimates, suggest_rebalance)

    @main_group.command()
    @click.argument("issue_id")
    @click.option("--consider-skills", is_flag=True, help="Consider team member skills")
    @click.option("--consider-availability", is_flag=True, help="Consider current workload")
    @click.option("--suggest-only", is_flag=True, help="Only suggest, don't assign")
    @click.pass_context
    def smart_assign(ctx: click.Context, issue_id: str, consider_skills: bool, consider_availability: bool, suggest_only: bool):
        """[DEPRECATED] Intelligently assign an issue to the best team member.
        
        ⚠️  DEPRECATION WARNING: Use 'roadmap team assign-smart' instead.
        """
        console.print("⚠️  DEPRECATION WARNING: 'roadmap smart-assign' is deprecated.", style="yellow")
        console.print("   Use 'roadmap team assign-smart' instead for better organization.", style="yellow")
        
        # Delegate to new command
        from .team import _original_smart_assign
        _original_smart_assign(ctx, issue_id, consider_skills, consider_availability, suggest_only)

    @main_group.command()
    @click.option("--assignee", "-a", help="Show dashboard for specific user")
    @click.option("--days", "-d", default=7, help="Number of days to include")
    @click.pass_context
    def dashboard(ctx: click.Context, assignee: str, days: int):
        """[DEPRECATED] Show your personalized daily dashboard.
        
        ⚠️  DEPRECATION WARNING: Use 'roadmap user show-dashboard' instead.
        """
        console.print("⚠️  DEPRECATION WARNING: 'roadmap dashboard' is deprecated.", style="yellow")
        console.print("   Use 'roadmap user show-dashboard' instead for better organization.", style="yellow")
        
        # Delegate to new command
        from .user import _original_dashboard
        _original_dashboard(ctx, assignee, days)