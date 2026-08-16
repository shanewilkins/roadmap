"""Safety and repeatability tests for the phase checkpoint journey runner."""

import tempfile
from pathlib import Path

import pytest

from scripts.checkpoint_journey import (
    DEFAULT_FIXTURE,
    REPOSITORY_ROOT,
    canonical_digests,
    validate_workspace,
    verify_fixture_digests,
)


def test_validate_workspace_accepts_dedicated_temporary_child(tmp_path):
    workspace = tmp_path / "checkpoint"
    assert validate_workspace(workspace) == workspace.resolve()


@pytest.mark.parametrize(
    "workspace",
    [
        REPOSITORY_ROOT / "checkpoint",
        Path(tempfile.gettempdir()),
        Path("/tmp").resolve(),
    ],
)
def test_validate_workspace_rejects_unsafe_targets(workspace):
    with pytest.raises(ValueError):
        validate_workspace(workspace)


def test_tracked_fixture_digests_are_stable():
    expected = verify_fixture_digests(DEFAULT_FIXTURE)
    assert expected == canonical_digests(DEFAULT_FIXTURE)
    assert len(expected) == 5
