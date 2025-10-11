#!/usr/bin/env python3
"""
Visualization & Charts Demo for Roadmap CLI
===========================================

This demo showcases the visualization capabilities of the roadmap CLI
using real data from the main roadmap project. It demonstrates how to generate
interactive charts, dashboards, and visual reports.
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(command, description):
    """Run a command and display the output."""
    print(f"\n🔧 {description}")
    print("=" * len(description) + "===")
    print(f"Command: {command}")
    print("-" * 50)
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd="/Users/shane/roadmap")
        if result.returncode == 0:
            print(result.stdout)
        else:
            print(f"❌ Command failed: {result.stderr}")
    except Exception as e:
        print(f"❌ Error running command: {e}")

def main():
    print("🎨 Visualization & Charts Demo")
    print("=" * 50)
    print()
    print("This demo shows how to create visual insights from your roadmap data:")
    print("  • Interactive HTML charts and graphs")
    print("  • Project health dashboards")
    print("  • Team workload visualizations")
    print("  • Timeline and Gantt charts")
    print("  • Progress tracking visuals")
    print()
    
    # Check if main project exists
    roadmap_path = Path("/Users/shane/roadmap/.roadmap")
    if not roadmap_path.exists():
        print("❌ Main roadmap project not found. Please ensure you're in the roadmap project directory.")
        return
    
    print("📊 BASIC VISUALIZATIONS")
    print("-" * 24)
    print("Generate core charts and graphs:")
    
    # Basic visualizations
    run_command("poetry run roadmap visualize create", "Generate standard visualization suite")
    run_command("poetry run roadmap timeline", "Create project timeline")
    run_command("poetry run roadmap project", "Project analytics with charts")
    
    print()
    print("📈 ADVANCED DASHBOARDS")
    print("-" * 22)
    print("Create comprehensive dashboards:")
    
    # Advanced dashboards
    run_command("poetry run roadmap dashboard", "Personal daily dashboard")
    run_command("poetry run roadmap dashboard --team", "Team collaboration dashboard")
    run_command("poetry run roadmap analytics enhanced --visualize", "Enhanced analytics with charts")
    
    print()
    print("🎯 TARGETED VISUALIZATIONS")
    print("-" * 27)
    print("Charts for specific aspects:")
    
    # Targeted charts
    run_command("poetry run roadmap workload-analysis", "Team workload analysis")
    run_command("poetry run roadmap capacity-forecast", "Capacity forecasting charts")
    run_command("poetry run roadmap report generate --format html", "Visual HTML reports")
    
    print()
    print("📁 CHART ORGANIZATION")
    print("-" * 21)
    print("Generated charts are organized in the artifacts directory:")
    
    # Show charts structure
    artifacts_path = Path("/Users/shane/roadmap/.roadmap/artifacts")
    if artifacts_path.exists():
        charts_dir = artifacts_path / "charts"
        dashboards_dir = artifacts_path / "dashboards"
        
        if charts_dir.exists():
            chart_files = list(charts_dir.glob("*.html"))
            print(f"📊 Charts directory: {len(chart_files)} charts")
            for chart in chart_files[:5]:  # Show first 5 charts
                print(f"  • {chart.name}")
            if len(chart_files) > 5:
                print(f"  ... and {len(chart_files) - 5} more")
        
        if dashboards_dir.exists():
            dashboard_files = list(dashboards_dir.glob("*.html"))
            print(f"📋 Dashboards directory: {len(dashboard_files)} dashboards")
            for dashboard in dashboard_files[:3]:  # Show first 3 dashboards
                print(f"  • {dashboard.name}")
            if len(dashboard_files) > 3:
                print(f"  ... and {len(dashboard_files) - 3} more")
    
    print()
    print("🌐 VIEWING CHARTS")
    print("-" * 16)
    print("All charts are interactive HTML files that can be opened in any browser:")
    
    # Show how to view charts
    if artifacts_path.exists():
        charts_dir = artifacts_path / "charts"
        if charts_dir.exists() and list(charts_dir.glob("*.html")):
            latest_chart = max(charts_dir.glob("*.html"), key=lambda p: p.stat().st_mtime)
            print(f"💡 Open latest chart: file://{latest_chart.absolute()}")
    
    print("""
    🖱️  Interactive Features:
    • Hover for detailed information
    • Zoom and pan capabilities
    • Toggle data series on/off
    • Export charts as images
    • Responsive design for all screen sizes
    """)
    
    print()
    print("📊 CHART TYPES AVAILABLE")
    print("-" * 25)
    print("📈 Status Distribution - Pie charts showing issue status breakdown")
    print("📊 Milestone Progress - Bar charts tracking completion rates")
    print("⚡ Team Velocity - Line charts showing team productivity")
    print("👥 Workload Distribution - Horizontal bar charts for team balance")
    print("🗓️  Timeline Charts - Gantt-style project timelines")
    print("🔥 Burndown Charts - Progress tracking over time")
    print("🎯 Priority Analysis - Charts showing issue priority distribution")
    print("📋 Health Dashboards - Multi-panel project health overview")
    
    print()
    print("🔧 CUSTOMIZATION OPTIONS")
    print("-" * 25)
    print("Customize chart generation:")
    
    # Customization examples
    print("  • Filter data before visualization")
    print("  • Choose specific time ranges")
    print("  • Select team members or milestones")
    print("  • Combine multiple chart types")
    
    run_command("poetry run roadmap visualize create --milestone 'v1.0.0'", "Charts for specific milestone")
    
    print()
    print("🎯 KEY FEATURES DEMONSTRATED")
    print("-" * 30)
    print("✅ Interactive HTML charts with Plotly.js")
    print("✅ Comprehensive project health dashboards")
    print("✅ Team workload and capacity visualizations")
    print("✅ Timeline and Gantt chart generation")
    print("✅ Automatic chart organization and management")
    print("✅ Responsive design for all devices")
    print("✅ Export capabilities for presentations")
    print("✅ Real-time data updates")
    
    print()
    print("🚀 NEXT STEPS")
    print("-" * 12)
    print("Try these visualization commands:")
    print("  poetry run roadmap visualize create --help")
    print("  poetry run roadmap timeline --help")
    print("  poetry run roadmap dashboard --help")
    print("  poetry run roadmap analytics enhanced --visualize")
    print()
    print("💡 Open generated charts in your browser:")
    print("  open .roadmap/artifacts/charts/")
    print("  open .roadmap/artifacts/dashboards/")
    print()
    
    print("📖 Learn more: https://roadmap-cli.readthedocs.io/en/latest/visualization/")

if __name__ == "__main__":
    main()