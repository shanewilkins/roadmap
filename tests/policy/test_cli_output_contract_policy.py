"""Policy tests for CLI output contracts.

Guardrails:
1) Prevent growth of brittle raw stdout assertions in test files.
2) Enforce canonical stream-separation behavior for CLI runner usage.
"""

from __future__ import annotations

import re
from pathlib import Path

import click

_RAW_ASSERT_ALLOWLIST = {
    "tests/integration/archive/test_archive_duplicate_prevention.py",
    "tests/integration/archive/test_archive_restore_commands.py",
    "tests/integration/archive/test_archive_restore_lifecycle.py",
    "tests/integration/cli/test_cli_issue_commands.py",
    "tests/integration/cli/test_cli_milestone_commands.py",
    "tests/integration/cli/test_cli_root_commands.py",
    "tests/integration/data/test_overdue_filtering.py",
    "tests/integration/git/test_git_integration.py",
    "tests/integration/github/test_github_integration.py",
    "tests/integration/init/test_init_messaging.py",
    "tests/integration/init/test_init_team_onboarding.py",
    "tests/integration/lifecycle/test_issue_lifecycle.py",
    "tests/integration/lifecycle/test_milestone_lifecycle.py",
    "tests/integration/view/test_today_command.py",
    "tests/integration/view/test_today_command_expanded.py",
    "tests/integration/workflows/test_integration_workflows.py",
    "tests/unit/adapters/cli/config/test_commands_integration.py",
    "tests/unit/adapters/cli/test_critical_path_command.py",
    "tests/unit/adapters/cli/test_git_setup_auth.py",
    "tests/unit/adapters/cli/test_sync_command.py",
    "tests/unit/common/formatters/test_assertion_helpers.py",
    "tests/unit/presentation/git/test_commands.py",
    "tests/unit/presentation/test_close_errors.py",
    "tests/unit/presentation/test_core.py",
    "tests/unit/presentation/test_deps_add_validation_handling.py",
    "tests/unit/presentation/test_deps_group_output_integration.py",
    "tests/unit/presentation/test_init_credential_integration.py",
    "tests/unit/presentation/test_init_postvalidation.py",
    "tests/unit/presentation/test_init_templates_and_customization.py",
    "tests/unit/presentation/test_issue.py",
    "tests/unit/presentation/test_issue_start_auto_branch_config.py",
    "tests/unit/presentation/test_lookup_command.py",
    "tests/unit/presentation/test_project.py",
    "tests/unit/presentation/test_project_view_command.py",
    "tests/unit/presentation/test_status_errors_health.py",
    "tests/unit/presentation/test_sync_status_tables_command.py",
}


def _raw_assertion_files() -> set[str]:
    root = Path(__file__).resolve().parents[1]
    files: set[str] = set()

    for test_file in root.rglob("test_*.py"):
        text = test_file.read_text(errors="ignore")

        has_raw_assert = bool(re.search(r"assert\s+[^\n]*result\.output", text))
        if not has_raw_assert:
            continue

        has_normalization = bool(
            re.search(r"strip_ansi|clean_output|clean_cli_output", text)
        )
        has_structured = bool(
            re.search(
                r"--format\s*\"?\s*,?\s*\"json\"|--format\s+json|extract_json|CLIOutputParser|TableData",
                text,
            )
        )

        if not has_normalization and not has_structured:
            files.add(test_file.relative_to(root.parent).as_posix())

    return files


def test_raw_output_assertion_allowlist_no_growth() -> None:
    """Do not allow net-new brittle raw stdout assertion files."""
    current = _raw_assertion_files()
    assert current <= _RAW_ASSERT_ALLOWLIST, (
        "New raw result.output assertion files detected. "
        "Use structured JSON/TableData assertions or normalized output assertions instead.\n"
        f"New files: {sorted(current - _RAW_ASSERT_ALLOWLIST)}"
    )


@click.command()
def _stream_contract_probe() -> None:
    click.echo("payload-on-stdout")
    click.echo("diagnostic-on-stderr", err=True)


def test_cli_runner_strict_streams_contract(cli_runner_strict_streams) -> None:
    """Canonical strict runner must separate stdout and stderr."""
    result = cli_runner_strict_streams.invoke(_stream_contract_probe)

    assert result.exit_code == 0
    assert "payload-on-stdout" in result.output
    assert hasattr(result, "stderr")
    assert "diagnostic-on-stderr" in result.stderr
