"""Tests for the temporary issue-to-Git branch bridge."""

from unittest.mock import MagicMock, patch

import pytest

from roadmap.core.services.issue.issue_creation_service import IssueCreationService


@pytest.fixture
def core() -> MagicMock:
    value = MagicMock()
    value.git.is_git_repository.return_value = True
    value.git.suggest_branch_name.return_value = "issue-1-test"
    return value


@pytest.fixture
def issue() -> MagicMock:
    value = MagicMock()
    value.id = "issue-1"
    return value


def test_branch_creation_uses_git_adapter(core: MagicMock, issue: MagicMock) -> None:
    core.git.create_branch_for_issue.return_value = True

    result = IssueCreationService(core).create_branch_for_issue(issue)

    assert result == (True, "issue-1-test")


def test_branch_creation_skips_non_git_directory(
    core: MagicMock, issue: MagicMock
) -> None:
    core.git.is_git_repository.return_value = False

    assert IssueCreationService(core).create_branch_for_issue(issue) == (False, None)


def test_branch_creation_stops_for_dirty_tree(
    core: MagicMock, issue: MagicMock
) -> None:
    core.git.create_branch_for_issue.return_value = False
    core.git._run_git_command.return_value = "M file.py"

    assert IssueCreationService(core).create_branch_for_issue(issue) == (
        False,
        "issue-1-test",
    )


def test_branch_creation_falls_back_to_subprocess(
    core: MagicMock, issue: MagicMock
) -> None:
    core.git.create_branch_for_issue.return_value = False
    core.git._run_git_command.return_value = None

    with patch("subprocess.run") as run:
        result = IssueCreationService(core).create_branch_for_issue(issue)

    assert result == (True, "issue-1-test")
    run.assert_called_once()
