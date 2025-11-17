#!/usr/bin/env python3
"""
Export & Data Extraction Demo for Roadmap CLI
==============================================

This demo showcases the powerful export capabilities of the roadmap CLI
using real data from the main roadmap project. It demonstrates how to extract
data in various formats for analysis, reporting, and integration.
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
    print("📊 Export & Data Extraction Demo")
    print("=" * 50)
    print()
    print("This demo shows how to extract roadmap data in various formats:")
    print("  • CSV files for spreadsheet analysis")
    print("  • JSON for programmatic processing")
    print("  • Excel files for business reporting")
    print("  • Filtered exports for specific needs")
    print()

    # Check if main project exists
    roadmap_path = Path("/Users/shane/roadmap/.roadmap")
    if not roadmap_path.exists():
        print("❌ Main roadmap project not found. Please ensure you're in the roadmap project directory.")
        return

    print("📋 BASIC EXPORTS")
    print("-" * 17)
    print("Export all data in different formats:")

    # Basic exports
    run_command("poetry run roadmap export issues --format csv", "Export all issues to CSV")
    run_command("poetry run roadmap export issues --format json", "Export all issues to JSON")
    run_command("poetry run roadmap export milestones --format json", "Export milestones to JSON")

    print()
    print("🔍 FILTERED EXPORTS")
    print("-" * 20)
    print("Export specific subsets of data:")

    # Filtered exports
    run_command("poetry run roadmap export issues --format csv --milestone 'v1.0.0'", "Export issues for specific milestone")
    run_command("poetry run roadmap export issues --format json --priority critical", "Export critical priority issues")
    run_command("poetry run roadmap export issues --format csv --status done", "Export completed issues")

    print()
    print("📈 ANALYTICS EXPORTS")
    print("-" * 21)
    print("Export analytical data and reports:")

    # Analytics exports
    run_command("poetry run roadmap analytics enhanced --export analysis.json", "Export enhanced analytics")
    run_command("poetry run roadmap report generate --format json", "Generate comprehensive report")

    print()
    print("📁 EXPORT ORGANIZATION")
    print("-" * 23)
    print("Files are automatically organized in the artifacts directory:")

    # Show artifacts structure
    artifacts_path = Path("/Users/shane/roadmap/.roadmap/artifacts")
    if artifacts_path.exists():
        print(f"📂 Artifacts directory: {artifacts_path}")
        subdirs = ["csv", "excel", "json", "charts", "dashboards"]
        for subdir in subdirs:
            subdir_path = artifacts_path / subdir
            if subdir_path.exists():
                files = list(subdir_path.glob("*"))
                print(f"  📁 {subdir}/: {len(files)} files")
                for file in files[:3]:  # Show first 3 files
                    print(f"    • {file.name}")
                if len(files) > 3:
                    print(f"    ... and {len(files) - 3} more")

    print()
    print("🔧 ADVANCED USAGE")
    print("-" * 18)
    print("Custom output paths and batch processing:")

    # Advanced examples
    run_command("poetry run roadmap export issues --format csv --output custom-export.csv", "Custom output filename")

    print()
    print("💻 PROGRAMMATIC ACCESS")
    print("-" * 23)
    print("Use exported JSON data in your applications:")

    # Show how to use exported data
    print("""
    import json
    from pathlib import Path
    
    # Load exported issues
    artifacts_dir = Path('.roadmap/artifacts/json')
    latest_export = max(artifacts_dir.glob('roadmap-issues-*.json'))
    
    with open(latest_export) as f:
        issues = json.load(f)
    
    # Analyze the data
    total_issues = len(issues)
    open_issues = len([i for i in issues if i['status'] != 'done'])
    print(f"Total: {total_issues}, Open: {open_issues}")
    """)

    print()
    print("🎯 KEY FEATURES DEMONSTRATED")
    print("-" * 30)
    print("✅ Multiple export formats (CSV, JSON, Excel)")
    print("✅ Automatic file organization in subdirectories")
    print("✅ Filtered exports for specific data subsets")
    print("✅ Analytics and reporting data extraction")
    print("✅ Custom output paths and filenames")
    print("✅ Programmatic data access patterns")
    print("✅ Batch processing capabilities")

    print()
    print("🚀 NEXT STEPS")
    print("-" * 12)
    print("Try these export commands:")
    print("  poetry run roadmap export issues --format excel")
    print("  poetry run roadmap export issues --format csv --assignee $(whoami)")
    print("  poetry run roadmap analytics enhanced --export detailed-analysis.json")
    print("  poetry run roadmap timeline --format json")
    print()

    print("📖 Learn more: https://roadmap-cli.readthedocs.io/en/latest/exports/")

if __name__ == "__main__":
    main()
