"""Tests for sync batch processing utilities."""

import asyncio

from roadmap.core.domain.issue import Issue
from roadmap.core.services.sync.batch_processor import (
    AsyncBatchProcessor,
    BatchProcessor,
    batch_issues_by_milestone,
    chunk_list,
)


def test_batch_processor_collects_results_and_errors_with_progress_indices():
    processor = BatchProcessor(max_workers=2, batch_size=2)
    progress_calls: list[tuple[int, int]] = []

    def _work(item: int) -> int:
        if item == 2:
            raise ValueError("bad item")
        return item * 10

    results, errors = processor.process_batch(
        [1, 2, 3],
        _work,
        on_progress=lambda idx, result: progress_calls.append((idx, result)),
    )

    assert sorted(results) == [10, 30]
    assert len(errors) == 1
    assert errors[0][0] == 2
    assert isinstance(errors[0][1], ValueError)

    reported_indices = {idx for idx, _ in progress_calls}
    assert reported_indices == {0, 2}


def test_async_batch_processor_collects_results_and_errors_with_progress_indices():
    processor = AsyncBatchProcessor(batch_size=2, max_concurrent=2)
    progress_calls: list[tuple[int, int]] = []

    async def _work(item: int) -> int:
        if item == 3:
            raise RuntimeError("nope")
        return item + 100

    async def _run() -> tuple[list[int], list[tuple[int, Exception]]]:
        return await processor.process_batch(
            [1, 2, 3, 4],
            _work,
            on_progress=lambda idx, result: progress_calls.append((idx, result)),
        )

    results, errors = asyncio.run(_run())

    assert sorted(results) == [101, 102, 104]
    assert len(errors) == 1
    assert errors[0][0] == 3
    assert isinstance(errors[0][1], RuntimeError)

    reported_indices = {idx for idx, _ in progress_calls}
    assert reported_indices == {0, 1, 3}


def test_chunk_list_splits_items_into_expected_sizes():
    assert chunk_list([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]


def test_batch_issues_by_milestone_groups_missing_to_default_bucket():
    issues = [
        Issue(id="1", title="Issue 1", milestone="M1"),
        Issue(id="2", title="Issue 2", milestone=None),
        Issue(id="3", title="Issue 3", milestone="M1"),
    ]

    grouped = batch_issues_by_milestone(issues)

    assert set(grouped.keys()) == {"M1", "_no_milestone"}
    assert [issue.id for issue in grouped["M1"]] == ["1", "3"]
    assert [issue.id for issue in grouped["_no_milestone"]] == ["2"]
