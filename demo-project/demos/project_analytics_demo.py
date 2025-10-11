#!/usr/bin/env python3
"""
Project-Level Analytics Demo for Roadmap CLI
=============================================

This demo showcases the powerful project-level analytics capabilities of the roadmap CLI
using the CloudSync Enterprise Platform demo project. It demonstrates how to get 
comprehensive insights into large-scale software projects.
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
        result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd="/Users/shane/roadmap/demo-project")
        if result.returncode == 0:
            print(result.stdout)
        else:
            print(f"❌ Command failed: {result.stderr}")
    except Exception as e:
        print(f"❌ Error running command: {e}")

def main():
    print("🚀 Project-Level Analytics Demo")
    print("=" * 50)
    print()
    print("This demo uses the CloudSync Enterprise Platform - a large-scale project with:")
    print("  • 296+ issues across 5 milestones")
    print("  • 10 developers + 1 product owner")
    print("  • Realistic issue distribution (bugs, features)")
    print("  • Multi-version roadmap (v1.6 → v2.0)")
    print()
    
    # Check if demo project exists
    demo_path = Path("/Users/shane/roadmap/demo-project")
    if not demo_path.exists():
        print("❌ Demo project not found. Please run the demo project setup first.")
        return
    
    print("🔍 PROJECT OVERVIEW")
    print("-" * 20)
    print("Get comprehensive project health and progress insights:")
    
    # Run project overview
    run_command("poetry run roadmap project", "Project Overview & Health Dashboard")
    
    print()
    print("📊 MILESTONE ANALYSIS")
    print("-" * 22)
    print("View detailed milestone progression and issue distribution:")
    
    # Run milestone list
    run_command("poetry run roadmap milestone list", "Milestone Status Overview")
    
    print()
    print("👥 TEAM WORKLOAD")
    print("-" * 17)
    print("Analyze team member assignments and workload balance:")
    
    # Run issue list with team focus
    run_command("poetry run roadmap issue list --open | head -30", "Open Issues by Team Member")
    
    print()
    print("🔍 FILTERING & ANALYSIS")
    print("-" * 24)
    print("Use powerful filtering to dive into specific areas:")
    
    # Show filtering examples
    run_command("poetry run roadmap issue list --type bug | head -20", "Bug Issues Only")
    run_command("poetry run roadmap issue list --priority critical | head -15", "Critical Priority Issues")
    
    print()
    print("📈 VISUALIZATION")
    print("-" * 17)
    print("Generate visual charts and dashboards:")
    
    # Show charts directory
    charts_dir = Path("/Users/shane/roadmap/demo-project/.roadmap/artifacts")
    if charts_dir.exists():
        chart_files = list(charts_dir.glob("*.html"))
        if chart_files:
            print(f"📊 Generated charts in: {charts_dir}")
            for chart in chart_files:
                print(f"  • {chart.name}")
            print()
            print("💡 Open these HTML files in your browser to view interactive charts!")
    
    print()
    print("🎯 KEY FEATURES DEMONSTRATED")
    print("-" * 30)
    print("✅ Project-level health metrics and completion tracking")
    print("✅ Milestone progression analysis with issue breakdown")  
    print("✅ Team workload distribution and balance analysis")
    print("✅ Technical debt indicators (bug percentage tracking)")
    print("✅ Issue type distribution across project phases")
    print("✅ Interactive HTML dashboards and visualizations")
    print("✅ Powerful filtering and querying capabilities")
    print()
    
    print("🚀 NEXT STEPS")
    print("-" * 12)
    print("Try these commands in the demo-project directory:")
    print("  cd demo-project")
    print("  poetry run roadmap project --format json")
    print("  poetry run roadmap project --format csv")
    print("  poetry run roadmap issue list --assignee alex.chen")
    print("  poetry run roadmap milestone list")
    print("  poetry run roadmap visualization create")
    print()
    
    print("📖 Learn more: https://roadmap-cli.readthedocs.io")

if __name__ == "__main__":
    main()