"""Unit tests for sync backend factory helpers."""

from unittest.mock import Mock, patch

import pytest

from roadmap.adapters.sync.backend_factory import (
    detect_backend_from_config,
    get_backend_for_config,
    get_sync_backend,
)


@pytest.mark.parametrize(
    "config,expected",
    [
        ({"backend": "github"}, "github"),
        ({"backend": "git"}, "git"),
        ({"github": {"owner": "acme", "repo": "roadmap"}}, "github"),
        ({"github": {"owner": "acme"}}, "git"),
        ({}, "git"),
    ],
)
def test_detect_backend_from_config(config, expected):
    """Backend detection should prioritize explicit config, then github, then git."""
    assert detect_backend_from_config(config) == expected


def test_get_sync_backend_returns_github_backend_instance():
    """Factory should instantiate GitHub backend for github type."""
    core = Mock()
    config = {"token": "abc"}

    with patch("roadmap.adapters.sync.backend_factory.GitHubSyncBackend") as cls:
        instance = cls.return_value
        result = get_sync_backend("github", core, config)

    cls.assert_called_once_with(core, config)
    assert result is instance


@pytest.mark.parametrize("exc", [ValueError("not git"), RuntimeError("no remote")])
def test_get_sync_backend_returns_none_on_git_init_failure(exc):
    """Git backend creation failures should degrade to None."""
    core = Mock()

    with patch(
        "roadmap.adapters.sync.backend_factory.VanillaGitSyncBackend",
        side_effect=exc,
    ):
        result = get_sync_backend("git", core, {})

    assert result is None


def test_get_sync_backend_rejects_invalid_backend_type():
    """Invalid backend type should raise clear ValueError."""
    with pytest.raises(ValueError, match="Invalid backend type"):
        get_sync_backend("invalid", Mock(), {})  # type: ignore[arg-type]


def test_get_backend_for_config_detects_and_delegates():
    """get_backend_for_config should call detect + get_sync_backend."""
    core = Mock()
    config = {"backend": "github"}

    with (
        patch(
            "roadmap.adapters.sync.backend_factory.detect_backend_from_config",
            return_value="github",
        ) as detect,
        patch(
            "roadmap.adapters.sync.backend_factory.get_sync_backend",
            return_value=Mock(),
        ) as get_backend,
    ):
        get_backend_for_config(core, config)

    detect.assert_called_once_with(config)
    get_backend.assert_called_once_with("github", core, config)
