#!/usr/bin/env python3
"""
Roadmap Performance Demo

This script demonstrates the performance capabilities of the roadmap CLI tool,
including benchmarking operations and showing optimization features.
"""

import subprocess
import time
from datetime import datetime
from pathlib import Path


def run_timed_command(command: str, description: str) -> float:
    """Run a command and return execution time."""
    print(f"⏱️  Running: {description}")
    start_time = time.time()

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd="/Users/shane/roadmap/demo-project",
            capture_output=True,
            text=True,
            timeout=30,
        )

        end_time = time.time()
        execution_time = end_time - start_time

        if result.returncode == 0:
            print(f"   ✅ Completed in {execution_time:.3f} seconds")
        else:
            print(f"   ⚠️  Command failed but timed: {execution_time:.3f} seconds")

        return execution_time

    except subprocess.TimeoutExpired:
        print("   ⏰ Command timed out (30s)")
        return 30.0
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return 0.0


def main():
    """Run performance demonstration."""
    print("🚀 ROADMAP PERFORMANCE DEMO")
    print("=" * 28)
    print(f"Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Verify demo project exists
    demo_path = Path("/Users/shane/roadmap/demo-project")
    if not demo_path.exists():
        print("❌ Demo project not found. Please set up the demo project first.")
        return

    print("📊 PERFORMANCE BENCHMARKS")
    print("-" * 26)

    # Test various operations and measure performance
    tests = [
        ("poetry run roadmap issue list", "List all issues"),
        ("poetry run roadmap milestone list", "List milestones"),
        ("poetry run roadmap analytics summary", "Generate analytics summary"),
        ("poetry run roadmap git status", "Check Git status"),
        ("poetry run roadmap issue filter --status open", "Filter open issues"),
    ]

    times = []

    for command, description in tests:
        execution_time = run_timed_command(command, description)
        times.append((description, execution_time))

    print("\n\n📈 PERFORMANCE SUMMARY")
    print("-" * 22)
    print(f"{'Operation':<35} {'Time (seconds)':<15}")
    print("-" * 50)

    total_time = 0
    for description, execution_time in times:
        print(f"{description:<35} {execution_time:<15.3f}")
        total_time += execution_time

    print("-" * 50)
    print(f"{'TOTAL TIME':<35} {total_time:<15.3f}")

    # Calculate statistics
    valid_times = [t for _, t in times if t > 0]
    if valid_times:
        avg_time = sum(valid_times) / len(valid_times)
        min_time = min(valid_times)
        max_time = max(valid_times)

        print("\n📊 PERFORMANCE STATISTICS")
        print("-" * 26)
        print(f"Average operation time: {avg_time:.3f} seconds")
        print(f"Fastest operation:      {min_time:.3f} seconds")
        print(f"Slowest operation:      {max_time:.3f} seconds")

    print("\n🎯 PERFORMANCE FEATURES")
    print("-" * 24)
    print("✅ Efficient file-based storage with intelligent caching")
    print("✅ Pandas-powered analytics for large datasets")
    print("✅ Optimized filtering and search algorithms")
    print("✅ Lazy loading of data for improved responsiveness")
    print("✅ Background processing for visualization generation")
    print("✅ Memory-efficient handling of large issue collections")

    print("\n💡 PERFORMANCE TIPS")
    print("-" * 20)
    print("🔍 Use specific filters to reduce processing time")
    print("📊 Project analytics cache results for faster subsequent access")
    print("🎨 Chart generation happens in background for better UX")
    print("💾 File locking ensures data integrity during concurrent operations")

    print(f"\n⏰ Demo completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
