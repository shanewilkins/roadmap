"""Processes pull results from sync operations.

Extracted from SyncMergeEngine to separate pull processing logic.
"""

from structlog import get_logger

logger = get_logger(__name__)


class PullResultProcessor:
    """Processes results from pull operations."""

    @staticmethod
    def process_pull_result(fetched) -> tuple[int, list, list]:
        """Process pull result and extract metrics.

        Args:
            fetched: Pull result (list or report object)

        Returns:
            Tuple of (pulled_count, pull_errors, pulled_remote_ids)
        """
        pulled_count = 0
        pull_errors = []
        pulled_remote_ids = []

        if isinstance(fetched, list):
            pulled_items = [r for r in fetched if r]
            pulled_count = len(pulled_items)
            for item in pulled_items:
                try:
                    rid = getattr(item, "backend_id", None) or getattr(item, "id", None)
                    if rid is not None:
                        pulled_remote_ids.append(str(rid))
                except Exception as e:
                    logger.debug("pulled_item_id_extraction_failed", error=str(e))
                    continue
        else:
            pull_report = fetched
            if getattr(pull_report, "errors", None):
                try:
                    err_keys = (
                        list(pull_report.errors.keys())
                        if isinstance(pull_report.errors, dict)
                        else []
                    )
                except Exception as e:
                    logger.debug("error_keys_extraction_failed", error=str(e))
                    err_keys = []
                pull_errors = err_keys
                logger.warning(
                    "pull_batch_had_errors",
                    error_count=len(pull_errors),
                    errors=str(pull_report.errors)[:200],
                )

            pulled_raw = getattr(pull_report, "pulled", None)
            if pulled_raw is None:
                pulled_count = 0
                pulled_remote_ids = []
            else:
                try:
                    pulled_iter = list(pulled_raw)
                except Exception as e:
                    logger.debug("pulled_iter_conversion_failed", error=str(e))
                    pulled_iter = [pulled_raw]
                pulled_remote_ids = [str(i) for i in pulled_iter]
                pulled_count = len(pulled_remote_ids)

        return pulled_count, pull_errors, pulled_remote_ids
