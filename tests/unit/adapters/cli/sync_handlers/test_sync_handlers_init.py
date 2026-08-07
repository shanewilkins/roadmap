"""Tests for sync handler facade pre-sync routing."""

from unittest.mock import patch

from roadmap.adapters.cli.sync_handlers import handle_pre_sync_actions


def _defaults():
    return {
        "core": object(),
        "backend": object(),
        "base": False,
        "reset_baseline_flag": False,
        "clear_baseline_flag": False,
        "conflicts": False,
        "link": None,
        "unlink": False,
        "issue_id": None,
        "verbose": False,
        "console_inst": object(),
    }


def test_handle_pre_sync_actions_base_short_circuits():
    """Base flag should dispatch to show_baseline and return its result."""
    kwargs = _defaults()
    kwargs["base"] = True

    with patch(
        "roadmap.adapters.cli.sync_handlers.show_baseline", return_value=True
    ) as mock_show:
        result = handle_pre_sync_actions(**kwargs)

    assert result is True
    mock_show.assert_called_once_with(
        kwargs["core"], kwargs["backend"], kwargs["verbose"], kwargs["console_inst"]
    )


def test_handle_pre_sync_actions_precedence_uses_first_matching_flag():
    """When multiple flags are set, first branch should win and short-circuit."""
    kwargs = _defaults()
    kwargs["base"] = True
    kwargs["reset_baseline_flag"] = True

    with (
        patch(
            "roadmap.adapters.cli.sync_handlers.show_baseline", return_value=True
        ) as mock_show,
        patch("roadmap.adapters.cli.sync_handlers.reset_baseline") as mock_reset,
    ):
        result = handle_pre_sync_actions(**kwargs)

    assert result is True
    mock_show.assert_called_once()
    mock_reset.assert_not_called()


def test_handle_pre_sync_actions_link_unlink_path():
    """Link/unlink flags should delegate to handle_link_unlink."""
    kwargs = _defaults()
    kwargs["link"] = "123"
    kwargs["issue_id"] = "iss-1"

    with patch(
        "roadmap.adapters.cli.sync_handlers.handle_link_unlink", return_value=True
    ) as mock_handler:
        result = handle_pre_sync_actions(**kwargs)

    assert result is True
    mock_handler.assert_called_once_with(
        kwargs["core"],
        kwargs["backend"],
        kwargs["link"],
        kwargs["unlink"],
        kwargs["issue_id"],
        kwargs["console_inst"],
    )


def test_handle_pre_sync_actions_no_flags_returns_false():
    """When no pre-sync action is requested, function should return False."""
    assert handle_pre_sync_actions(**_defaults()) is False
