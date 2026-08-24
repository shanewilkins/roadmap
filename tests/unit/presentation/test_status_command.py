"""Status command boundary behavior."""

import json
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from roadmap.adapters.cli.status import status


def _core():
    core = MagicMock()
    core.planning.all_projects.return_value = ()
    core.planning.all_milestones.return_value = ()
    core.planning.all_issues.return_value = ()
    return core


def test_status_json_is_versioned_and_parseable():
    result = CliRunner().invoke(status, ["--format", "json"], obj={"core": _core()})

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == 1
    assert payload["kind"] == "roadmap.status"


def test_status_failure_is_nonzero_stderr_diagnostic():
    core = _core()
    core.planning.all_projects.side_effect = RuntimeError("broken canonical input")

    result = CliRunner().invoke(status, ["--format", "json"], obj={"core": core})

    assert result.exit_code == 1
    assert result.stdout == ""
    assert "broken canonical input" in result.stderr


def test_status_output_refuses_overwrite(tmp_path):
    target = tmp_path / "status.json"
    target.write_text("keep\n", encoding="utf-8")

    result = CliRunner().invoke(
        status,
        ["--format", "json", "--output", str(target)],
        obj={"core": _core()},
    )

    assert result.exit_code == 1
    assert target.read_text(encoding="utf-8") == "keep\n"


def test_rich_status_delegates_tables_to_output_manager():
    with patch("roadmap.adapters.cli.status.OutputManager") as manager:
        result = CliRunner().invoke(status, [], obj={"core": _core()})

    assert result.exit_code == 0
    assert manager.return_value.render_table.call_count == 2
