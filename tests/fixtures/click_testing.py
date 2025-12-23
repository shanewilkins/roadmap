"""
Comprehensive Click CLI testing infrastructure.

Provides reusable fixtures, helpers, and assertions for testing Click-based CLI applications.
This module encapsulates best practices for Click testing with proper output capture,
command execution, and assertion patterns.
"""

import re
from collections.abc import Callable

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli import main


class ClickTestResult:
    """Wrapper around Click's CliRunner result with enhanced assertion methods."""

    def __init__(self, runner_result):
        """Initialize with a Click CliRunner result object."""
        self.result = runner_result
        self.exit_code = runner_result.exit_code
        self.output = runner_result.output
        self.exception = runner_result.exception

    @property
    def clean_output(self) -> str:
        """Get output with ANSI codes stripped and whitespace normalized."""
        from tests.unit.shared.test_utils import clean_cli_output

        return clean_cli_output(self.output)

    @property
    def stripped_output(self) -> str:
        """Get output with ANSI codes stripped."""
        from tests.unit.shared.test_utils import strip_ansi

        return strip_ansi(self.output)

    def assert_success(self, msg: str = "Command should succeed") -> "ClickTestResult":
        """Assert that command exited with code 0."""
        assert self.exit_code == 0, f"{msg}\n\nOutput:\n{self.output}"
        return self

    def assert_failure(
        self, exit_code: int = 1, msg: str = "Command should fail"
    ) -> "ClickTestResult":
        """Assert that command failed with specific exit code."""
        assert (
            self.exit_code == exit_code
        ), f"{msg} (expected {exit_code}, got {self.exit_code})\n\nOutput:\n{self.output}"
        return self

    def assert_contains(
        self, text: str, clean: bool = True, msg: str = ""
    ) -> "ClickTestResult":
        """Assert that output contains text (with optional cleaning)."""
        output = self.clean_output if clean else self.output
        assert (
            text in output
        ), f"'{text}' not found in output.{f' {msg}' if msg else ''}\n\nOutput:\n{output}"
        return self

    def assert_not_contains(
        self, text: str, clean: bool = True, msg: str = ""
    ) -> "ClickTestResult":
        """Assert that output does not contain text."""
        output = self.clean_output if clean else self.output
        assert (
            text not in output
        ), f"'{text}' found in output but shouldn't be.{f' {msg}' if msg else ''}\n\nOutput:\n{output}"
        return self

    def assert_contains_all(
        self, texts: list[str], clean: bool = True
    ) -> "ClickTestResult":
        """Assert that output contains all provided texts."""
        output = self.clean_output if clean else self.output
        for text in texts:
            assert text in output, f"'{text}' not found in output.\n\nOutput:\n{output}"
        return self

    def assert_contains_any(
        self, texts: list[str], clean: bool = True
    ) -> "ClickTestResult":
        """Assert that output contains at least one of provided texts."""
        output = self.clean_output if clean else self.output
        assert any(
            text in output for text in texts
        ), f"None of {texts} found in output.\n\nOutput:\n{output}"
        return self

    def assert_matches_regex(
        self, pattern: str, clean: bool = True
    ) -> "ClickTestResult":
        """Assert that output matches regex pattern."""
        output = self.clean_output if clean else self.output
        assert re.search(
            pattern, output
        ), f"Pattern '{pattern}' not found in output.\n\nOutput:\n{output}"
        return self

    def assert_exception(self, exception_type=None) -> "ClickTestResult":
        """Assert that command raised an exception."""
        if exception_type:
            assert isinstance(
                self.exception, exception_type
            ), f"Expected {exception_type}, got {type(self.exception)}"
        else:
            assert (
                self.exception is not None
            ), "Expected an exception, but none was raised"
        return self

    def extract_first_match(
        self, pattern: str, group: int = 1, clean: bool = True
    ) -> str | None:
        """Extract first regex match from output."""
        output = self.clean_output if clean else self.output
        match = re.search(pattern, output)
        return match.group(group) if match else None

    def extract_all_matches(
        self, pattern: str, group: int = 1, clean: bool = True
    ) -> list[str]:
        """Extract all regex matches from output."""
        output = self.clean_output if clean else self.output
        return re.findall(pattern, output)


class ClickTestHelper:
    """Helper class for common Click testing patterns."""

    @staticmethod
    def create_id_extractor(pattern: str) -> Callable[[str], str | None]:
        """Create a function that extracts IDs from output using a regex pattern."""

        def extractor(output: str) -> str | None:
            from tests.unit.shared.test_utils import clean_cli_output

            clean_output = clean_cli_output(output)
            match = re.search(pattern, clean_output)
            return match.group(1) if match else None

        return extractor

    @staticmethod
    def extract_table_data(
        output: str, headers: list[str] | None = None
    ) -> list[dict[str, str]]:
        """Parse table output from CLI into list of dictionaries.

        Args:
            output: Raw CLI output containing a table
            headers: Optional list of header names (auto-detected if not provided)

        Returns:
            List of dictionaries with row data
        """
        from tests.unit.shared.test_utils import clean_cli_output

        clean_output = clean_cli_output(output)
        lines = clean_output.split("\n")

        if not lines:
            return []

        # Auto-detect headers if not provided
        if headers is None:
            # Look for header line (usually contains capitalized words)
            header_line = None
            for i, line in enumerate(lines):
                if any(word.isupper() for word in line.split()):
                    header_line = line
                    lines = lines[i + 1 :]
                    break

            if header_line:
                headers = [h.strip() for h in header_line.split() if h.strip()]
            else:
                return []

        # Parse data rows
        data = []
        for line in lines:
            if not line.strip():
                continue
            values = [v.strip() for v in line.split()]
            if len(values) > 0:
                # Create dict with headers, padding with empty strings if needed
                row = {
                    h: values[i] if i < len(values) else ""
                    for i, h in enumerate(headers)
                }
                data.append(row)

        return data


# Pytest Fixtures
# ===============


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide a Click CLI runner with isolated filesystem.

    Returns:
        CliRunner configured for testing
    """
    return CliRunner()


@pytest.fixture
def isolated_cli_runner() -> CliRunner:
    """Provide a Click CLI runner that uses isolated_filesystem.

    This runner runs commands in a temporary directory, which is useful
    for testing commands that create or modify files.

    Returns:
        CliRunner instance
    """
    return CliRunner()


@pytest.fixture
def click_test_result_wrapper() -> type:
    """Provide the ClickTestResult wrapper class."""
    return ClickTestResult


@pytest.fixture
def click_test_helper() -> type:
    """Provide the ClickTestHelper class."""
    return ClickTestHelper


@pytest.fixture
def cli_with_main(isolated_cli_runner):
    """Provide a runner with main CLI command.

    Returns:
        Tuple of (runner, main_command) for convenience
    """
    return isolated_cli_runner, main


@pytest.fixture
def run_command(isolated_cli_runner, click_test_result_wrapper):
    """Provide a convenient command runner function with isolated filesystem.

    Usage:
        result = run_command(["issue", "create", "My Issue"])
        result.assert_success().assert_contains("Created issue")

    Note:
        Commands are executed in an isolated temporary filesystem.
        Use this for tests that need filesystem isolation.
        For tests that don't need isolation, use isolated_cli_runner.invoke() directly.

    Returns:
        Function that runs a command and returns wrapped result
    """

    def _run_command(
        args: list[str],
        catch_exceptions: bool = False,
        input: str | None = None,
        env: dict[str, str] | None = None,
    ) -> ClickTestResult:
        """Run a command in an isolated filesystem and return wrapped result."""
        with isolated_cli_runner.isolated_filesystem():
            result = isolated_cli_runner.invoke(
                main,
                args,
                catch_exceptions=catch_exceptions,
                input=input,
                env=env,
            )
        return click_test_result_wrapper(result)

    return _run_command


@pytest.fixture
def isolated_roadmap_cli(isolated_cli_runner, click_test_result_wrapper):
    """Provide roadmap CLI runner with isolated filesystem and convenient methods.

    This is a higher-level fixture that combines runner, main command,
    and result wrapper for convenient CLI testing.

    Returns:
        Object with invoke method that returns ClickTestResult
    """

    class IsolatedRoadmapCLI:
        def __init__(self, runner, wrapper):
            self.runner = runner
            self.result_wrapper = wrapper

        def run(
            self,
            args: list[str],
            catch_exceptions: bool = False,
            input: str | None = None,
            env: dict[str, str] | None = None,
        ) -> ClickTestResult:
            """Run a roadmap command."""
            result = self.runner.invoke(
                main, args, catch_exceptions=catch_exceptions, input=input, env=env
            )
            return self.result_wrapper(result)

        def init(self, project_name: str = "test-project", **kwargs) -> ClickTestResult:
            """Convenience method to initialize roadmap."""
            args = [
                "init",
                "--non-interactive",
                "--skip-github",
                "--project-name",
                project_name,
            ]
            return self.run(args, **kwargs)

        def create_issue(self, title: str, **kwargs) -> ClickTestResult:
            """Convenience method to create issue."""
            args = ["issue", "create", title]
            return self.run(args, **kwargs)

        def create_milestone(self, name: str, **kwargs) -> ClickTestResult:
            """Convenience method to create milestone."""
            args = ["milestone", "create", name]
            return self.run(args, **kwargs)

        def create_project(self, name: str, **kwargs) -> ClickTestResult:
            """Convenience method to create project."""
            args = ["project", "create", name]
            return self.run(args, **kwargs)

        def list_issues(self, **kwargs) -> ClickTestResult:
            """Convenience method to list issues."""
            return self.run(["issue", "list"], **kwargs)

        def list_milestones(self, **kwargs) -> ClickTestResult:
            """Convenience method to list milestones."""
            return self.run(["milestone", "list"], **kwargs)

        def list_projects(self, **kwargs) -> ClickTestResult:
            """Convenience method to list projects."""
            return self.run(["project", "list"], **kwargs)

    return IsolatedRoadmapCLI(isolated_cli_runner, click_test_result_wrapper)


@pytest.fixture
def roadmap_cli_with_data(isolated_roadmap_cli, isolated_cli_runner):
    """Provide roadmap CLI with pre-initialized data (issues, milestones, projects).

    This fixture initializes a roadmap with sample data and provides
    convenient access to create additional items and their IDs.

    Yields:
        Tuple of (cli, data_dict) where data_dict contains created IDs
    """
    with isolated_cli_runner.isolated_filesystem():
        # Initialize roadmap
        isolated_roadmap_cli.init("Test Project").assert_success()

        # Create sample data
        issue_result = isolated_roadmap_cli.create_issue("Test Issue").assert_success()
        issue_id = ClickTestHelper.create_id_extractor(r"\[([^\]]+)\]")(
            issue_result.output
        )

        milestone_result = isolated_roadmap_cli.create_milestone(
            "v1.0.0"
        ).assert_success()
        milestone_id = ClickTestHelper.create_id_extractor(r"\[([^\]]+)\]")(
            milestone_result.output
        )

        isolated_roadmap_cli.create_project("test-project").assert_success()
        project_list = isolated_roadmap_cli.list_projects().assert_success()
        project_id = ClickTestHelper.create_id_extractor(r"(\w+)\s+test-project")(
            project_list.output
        )

        data = {
            "issue_id": issue_id,
            "issue_title": "Test Issue",
            "milestone_id": milestone_id,
            "milestone_name": "v1.0.0",
            "project_id": project_id,
            "project_name": "test-project",
        }

        yield isolated_roadmap_cli, data


# Integration with existing conftest fixtures
# ============================================


def pytest_configure(config):
    """Configure pytest with Click testing markers."""
    config.addinivalue_line(
        "markers", "click_test: mark test as a Click CLI integration test"
    )
    config.addinivalue_line(
        "markers", "cli_output: mark test as testing CLI output formatting"
    )
