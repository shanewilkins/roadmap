#!/usr/bin/env python3
"""Debug script to test CLI context setup."""

from click.testing import CliRunner
from roadmap.cli import main

def test_main_callback():
    """Test if main callback is invoked."""
    
    # Add debug to main callback
    original_callback = main.callback
    
    def debug_callback(ctx):
        print(f"DEBUG: Main callback invoked!")
        print(f"DEBUG: ctx.obj before: {ctx.obj}")
        print(f"DEBUG: invoke_without_command: {main.invoke_without_command}")
        result = original_callback(ctx)
        print(f"DEBUG: ctx.obj after: {ctx.obj}")
        print(f"DEBUG: Has core? {'core' in ctx.obj}")
        return result
    
    main.callback = debug_callback
    
    runner = CliRunner()
    
    print("=" * 50)
    print("Testing: roadmap --help")
    result = runner.invoke(main, ['--help'])
    print(f"Exit code: {result.exit_code}")
    
    print("=" * 50)
    print("Testing: roadmap team --help")
    result = runner.invoke(main, ['team', '--help'])
    print(f"Exit code: {result.exit_code}")
    
    print("=" * 50)
    print("Testing: roadmap team forecast-capacity")
    try:
        result = runner.invoke(main, ['team', 'forecast-capacity'], catch_exceptions=False)
        print(f"Exit code: {result.exit_code}")
    except Exception as e:
        print(f"Exception: {e}")


if __name__ == "__main__":
    test_main_callback()