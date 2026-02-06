<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

## Roadmap CLI Tool Project

This is a Python command line tool called 'roadmap' built with uv for package management and designed for PyPI publishing.

### Project Structure
- Uses uv for dependency management and packaging
- CLI entry point defined in pyproject.toml
- Follows Python packaging best practices
- Includes testing with pytest
- Git repository with proper .gitignore
- Ready for PyPI publishing

### Development Guidelines
- Use uv commands for dependency and test execution
- Follow semantic versioning
- Include comprehensive tests
- Update changelog for releases
- Use type hints throughout the codebase
- Maintain POSIX compatibility throughout the codebase

### CLI Tool Features
- Command line interface using Click or argparse
- Proper error handling and user feedback
- Configuration file support
- Extensible command structure

### Policy Directives
- You may not commit, reset, or force push to the main branch without approval.
- You may not revert changes to the main branch without approval.
- You may not create new branches without approval.
- You may not run the full test suite without approval.
- You may not deploy to production without approval.
- You may not decide that a test failing is acceptable without approval.
- You may not merge pull requests without approval.
- Use the CLI git, not MCP
