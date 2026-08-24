"""Subprocess-boundary tests for local Git."""

import subprocess
from unittest.mock import patch

import pytest

from roadmap.adapters.outbound.git.local import SubprocessLocalGit
from roadmap.application.failures import ApplicationFailure


def _completed(arguments, returncode: int = 0, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess(arguments, returncode, stdout, stderr)


def test_inspection_uses_fixed_local_argv_and_disables_prompts(tmp_path) -> None:
    results = [
        _completed((), stdout="true\n"),
        _completed((), stdout="main\n"),
        _completed((), stdout="abc123\n"),
        _completed(
            (),
            stdout="?? odd name.txt\0 M tracked.txt\0R  new name.txt\0old name.txt\0",
        ),
    ]
    with patch(
        "roadmap.adapters.outbound.git.local.subprocess.run", side_effect=results
    ) as run:
        snapshot = SubprocessLocalGit(tmp_path).inspect_local_git()

    assert snapshot.changed_paths == (
        "new name.txt",
        "odd name.txt",
        "old name.txt",
        "tracked.txt",
    )
    for call in run.call_args_list:
        argv = call.args[0]
        assert argv[:3] == ("git", "-C", str(tmp_path.resolve()))
        assert call.kwargs["env"]["GIT_TERMINAL_PROMPT"] == "0"
        assert "shell" not in call.kwargs


def test_unsafe_branch_is_rejected_before_subprocess(tmp_path) -> None:
    with patch("roadmap.adapters.outbound.git.local.subprocess.run") as run:
        with pytest.raises(ApplicationFailure, match="unsafe"):
            SubprocessLocalGit(tmp_path).create_branch(
                "issue/x;touch-pwned", checkout=True
            )

    run.assert_not_called()


def test_timeout_becomes_stable_application_failure(tmp_path) -> None:
    with patch(
        "roadmap.adapters.outbound.git.local.subprocess.run",
        side_effect=subprocess.TimeoutExpired(("git",), 0.1),
    ):
        with pytest.raises(ApplicationFailure, match="timed out"):
            SubprocessLocalGit(tmp_path, timeout=0.1).inspect_local_git()


def test_missing_executable_becomes_stable_application_failure(tmp_path) -> None:
    with patch(
        "roadmap.adapters.outbound.git.local.subprocess.run",
        side_effect=FileNotFoundError,
    ):
        with pytest.raises(ApplicationFailure, match="not available"):
            SubprocessLocalGit(tmp_path).inspect_local_git()


def test_local_command_failure_is_translated_without_traceback(tmp_path) -> None:
    collision_check = _completed((), returncode=1)
    failed_branch = _completed((), returncode=128, stderr="fatal: cannot lock ref\n")
    with patch(
        "roadmap.adapters.outbound.git.local.subprocess.run",
        side_effect=[collision_check, failed_branch],
    ):
        with pytest.raises(ApplicationFailure, match="cannot lock ref"):
            SubprocessLocalGit(tmp_path).create_branch("issue/safe", checkout=False)
