"""Local descriptive identity agrees with assignment normalization."""

import pytest

from roadmap.adapters.outbound.system import (
    ConfiguredCurrentIdentity,
    LocalAssigneeDirectory,
)


class GitIdentity:
    def __init__(self, name):
        self.name = name

    def user_identity(self):
        return self.name, None

    def create_branch(self, name: str, *, checkout: bool) -> None:
        raise AssertionError("Identity lookup must not create a branch")

    def inspect_local_git(self):
        raise AssertionError("Identity lookup needs only the Git user name")


@pytest.mark.parametrize(
    "configured,git_name,expected",
    [
        ("alice", "bob", "alice"),
        (" alice ", "bob", "alice"),
        (None, " Bob Smith ", "Bob Smith"),
        ("   ", " Bob Smith ", "Bob Smith"),
        ("", "bob", "bob"),
        (None, None, None),
        ("   ", "  ", None),
    ],
)
def test_identity_precedence_and_normalization(configured, git_name, expected):
    assert (
        ConfiguredCurrentIdentity(configured, GitIdentity(git_name)).current_identity()
        == expected
    )


@pytest.mark.parametrize(
    "name,expected",
    [
        (" Alice Smith ", "Alice Smith"),
        ("not-a-github-account", "not-a-github-account"),
        ("", None),
        ("   ", None),
    ],
)
def test_descriptive_assignee_normalization(name, expected):
    assert LocalAssigneeDirectory().canonical_assignee(name) == expected
