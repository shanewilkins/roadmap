"""Tests for PullResultProcessor behavior."""

from types import SimpleNamespace

from roadmap.adapters.sync.services.pull_result_processor import PullResultProcessor


def test_process_pull_result_list_extracts_ids_and_skips_falsy_items():
    fetched = [
        SimpleNamespace(backend_id="B-1"),
        None,
        SimpleNamespace(id=42),
        "",  # falsy, should be skipped
    ]

    pulled_count, pull_errors, pulled_remote_ids = (
        PullResultProcessor.process_pull_result(fetched)
    )

    assert pulled_count == 2
    assert pull_errors == []
    assert pulled_remote_ids == ["B-1", "42"]


def test_process_pull_result_report_extracts_error_keys_and_pulled_ids():
    report = SimpleNamespace(
        errors={"A": "bad", "B": "worse"},
        pulled=[101, "202"],
    )

    pulled_count, pull_errors, pulled_remote_ids = (
        PullResultProcessor.process_pull_result(report)
    )

    assert pulled_count == 2
    assert pull_errors == ["A", "B"]
    assert pulled_remote_ids == ["101", "202"]


def test_process_pull_result_report_handles_non_iterable_pulled_value():
    report = SimpleNamespace(
        errors=None,
        pulled=999,
    )

    pulled_count, pull_errors, pulled_remote_ids = (
        PullResultProcessor.process_pull_result(report)
    )

    assert pulled_count == 1
    assert pull_errors == []
    assert pulled_remote_ids == ["999"]
