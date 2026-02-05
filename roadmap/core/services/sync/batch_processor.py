"""Batch processing for parallel sync operations."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, Any, Callable

from structlog import get_logger

if TYPE_CHECKING:
    from roadmap.core.domain.issue import Issue

logger = get_logger(__name__)


class BatchProcessor:
    """Process items in parallel batches for improved performance."""

    def __init__(self, max_workers: int = 5, batch_size: int = 10):
        """Initialize batch processor.

        Args:
            max_workers: Maximum number of parallel workers
            batch_size: Number of items to process per batch
        """
        self.max_workers = max_workers
        self.batch_size = batch_size

    def process_batch(
        self,
        items: list[Any],
        process_func: Callable[[Any], Any],
        on_progress: Callable[[int, Any], None] | None = None,
    ) -> tuple[list[Any], list[tuple[Any, Exception]]]:
        """Process items in parallel batches.

        Args:
            items: List of items to process
            process_func: Function to apply to each item
            on_progress: Optional callback for progress updates (index, result)

        Returns:
            Tuple of (successful_results, failed_items_with_errors)
        """
        results = []
        errors = []

        # Split into batches
        batches = [
            items[i : i + self.batch_size]
            for i in range(0, len(items), self.batch_size)
        ]

        logger.info(
            "batch_processing_started",
            total_items=len(items),
            batches=len(batches),
            batch_size=self.batch_size,
            max_workers=self.max_workers,
            action="process_batch",
        )

        # Process each batch in parallel
        for batch_idx, batch in enumerate(batches):
            batch_results, batch_errors = self._process_single_batch(
                batch, process_func, batch_idx * self.batch_size, on_progress
            )
            results.extend(batch_results)
            errors.extend(batch_errors)

        logger.info(
            "batch_processing_completed",
            total_items=len(items),
            successful=len(results),
            failed=len(errors),
            action="process_batch",
        )

        return results, errors

    def _process_single_batch(
        self,
        batch: list[Any],
        process_func: Callable[[Any], Any],
        offset: int,
        on_progress: Callable[[int, Any], None] | None = None,
    ) -> tuple[list[Any], list[tuple[Any, Exception]]]:
        """Process a single batch using thread pool.

        Args:
            batch: Batch of items to process
            process_func: Function to apply to each item
            offset: Offset for progress reporting
            on_progress: Optional callback for progress updates

        Returns:
            Tuple of (results, errors)
        """
        results = []
        errors = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_item = {
                executor.submit(process_func, item): (idx + offset, item)
                for idx, item in enumerate(batch)
            }

            # Collect results as they complete
            for future in as_completed(future_to_item):
                idx, item = future_to_item[future]
                try:
                    result = future.result()
                    results.append(result)

                    if on_progress:
                        on_progress(idx, result)

                except Exception as e:
                    logger.error(
                        "batch_item_failed",
                        index=idx,
                        item=str(item)[:100],
                        error=str(e),
                        action="process_item",
                    )
                    errors.append((item, e))

        return results, errors


class AsyncBatchProcessor:
    """Async batch processor for async operations."""

    def __init__(self, batch_size: int = 10, max_concurrent: int = 5):
        """Initialize async batch processor.

        Args:
            batch_size: Number of items per batch
            max_concurrent: Maximum concurrent tasks
        """
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent

    async def process_batch(
        self,
        items: list[Any],
        process_func: Callable[[Any], Any],
        on_progress: Callable[[int, Any], None] | None = None,
    ) -> tuple[list[Any], list[tuple[Any, Exception]]]:
        """Process items asynchronously in batches.

        Args:
            items: List of items to process
            process_func: Async function to apply to each item
            on_progress: Optional callback for progress updates

        Returns:
            Tuple of (results, errors)
        """
        results = []
        errors = []

        # Split into batches
        batches = [
            items[i : i + self.batch_size]
            for i in range(0, len(items), self.batch_size)
        ]

        logger.info(
            "async_batch_processing_started",
            total_items=len(items),
            batches=len(batches),
            batch_size=self.batch_size,
            max_concurrent=self.max_concurrent,
            action="process_batch",
        )

        # Process batches
        for batch_idx, batch in enumerate(batches):
            batch_results, batch_errors = await self._process_single_batch(
                batch, process_func, batch_idx * self.batch_size, on_progress
            )
            results.extend(batch_results)
            errors.extend(batch_errors)

        logger.info(
            "async_batch_processing_completed",
            total_items=len(items),
            successful=len(results),
            failed=len(errors),
            action="process_batch",
        )

        return results, errors

    async def _process_single_batch(
        self,
        batch: list[Any],
        process_func: Callable[[Any], Any],
        offset: int,
        on_progress: Callable[[int, Any], None] | None = None,
    ) -> tuple[list[Any], list[tuple[Any, Exception]]]:
        """Process a single batch asynchronously.

        Args:
            batch: Batch of items to process
            process_func: Async function to apply
            offset: Offset for progress reporting
            on_progress: Optional callback for progress

        Returns:
            Tuple of (results, errors)
        """
        results = []
        errors = []

        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def process_with_semaphore(idx: int, item: Any):
            async with semaphore:
                try:
                    result = await process_func(item)
                    results.append(result)

                    if on_progress:
                        on_progress(idx + offset, result)

                    return result
                except Exception as e:
                    logger.error(
                        "async_batch_item_failed",
                        index=idx + offset,
                        item=str(item)[:100],
                        error=str(e),
                        action="process_item",
                    )
                    errors.append((item, e))
                    return None

        # Process all items in batch concurrently
        await asyncio.gather(
            *[process_with_semaphore(idx, item) for idx, item in enumerate(batch)],
            return_exceptions=True,
        )

        return results, errors


def chunk_list(items: list[Any], chunk_size: int) -> list[list[Any]]:
    """Split a list into chunks of specified size.

    Args:
        items: List to chunk
        chunk_size: Size of each chunk

    Returns:
        List of chunks
    """
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


def batch_issues_by_milestone(issues: list[Issue]) -> dict[str, list[Issue]]:
    """Group issues by milestone for batch processing.

    Args:
        issues: List of issues

    Returns:
        Dict mapping milestone names to issue lists
    """
    batches: dict[str, list[Issue]] = {}

    for issue in issues:
        milestone = issue.milestone or "_no_milestone"
        if milestone not in batches:
            batches[milestone] = []
        batches[milestone].append(issue)

    logger.info(
        "issues_batched_by_milestone",
        total_issues=len(issues),
        milestones=len(batches),
        action="batch_issues",
    )

    return batches
