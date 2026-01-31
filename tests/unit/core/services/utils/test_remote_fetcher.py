"""Tests for RemoteFetcher utility.

Tests fetching remote data with retry logic and rate-limit handling.
"""

import time
from unittest.mock import Mock, patch

import pytest

from roadmap.core.services.utils.remote_fetcher import RemoteFetcher
from roadmap.core.services.utils.retry_policy import RetryPolicy


class TestHandleRateLimitFromResponse:
    """Test rate-limit detection in responses."""

    def test_handle_rate_limit_with_none_response(self):
        """Test returns 0.0 for None response."""
        result = RemoteFetcher._handle_rate_limit_from_response(None)
        assert result == 0.0

    def test_handle_rate_limit_with_dict_no_headers(self):
        """Test returns 0.0 for dict without headers."""
        response = {"data": "test"}
        result = RemoteFetcher._handle_rate_limit_from_response(response)
        assert result == 0.0

    def test_handle_rate_limit_with_dict_headers_not_empty(self):
        """Test returns 0.0 when rate limit not exhausted."""
        response = {
            "headers": {
                "X-RateLimit-Remaining": "100",
                "X-RateLimit-Reset": "9999999999",
            }
        }
        result = RemoteFetcher._handle_rate_limit_from_response(response)
        assert result == 0.0

    @patch("roadmap.core.services.utils.remote_fetcher.time.time")
    def test_handle_rate_limit_exhausted_with_reset(self, mock_time):
        """Test calculates wait time when rate limit exhausted."""
        now = 1000
        reset = 1010
        mock_time.return_value = now

        response = {
            "headers": {
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset),
            }
        }

        result = RemoteFetcher._handle_rate_limit_from_response(response)
        assert result == float(reset - now)

    @patch("roadmap.core.services.utils.remote_fetcher.time.time")
    def test_handle_rate_limit_lowercase_headers(self, mock_time):
        """Test handles lowercase header names."""
        now = 1000
        reset = 1010
        mock_time.return_value = now

        response = {
            "headers": {
                "x-ratelimit-remaining": "0",
                "x-ratelimit-reset": str(reset),
            }
        }

        result = RemoteFetcher._handle_rate_limit_from_response(response)
        assert result == float(reset - now)

    def test_handle_rate_limit_with_object_headers(self):
        """Test extracts headers from object response."""
        mock_response = Mock()
        mock_response.headers = {"X-RateLimit-Remaining": "100"}

        result = RemoteFetcher._handle_rate_limit_from_response(mock_response)
        assert result == 0.0

    def test_handle_rate_limit_with_raw_response_headers(self):
        """Test extracts headers from raw_response attribute."""
        mock_response = Mock()
        mock_response.headers = None
        mock_response.raw_response = {"headers": {"X-RateLimit-Remaining": "100"}}

        result = RemoteFetcher._handle_rate_limit_from_response(mock_response)
        assert result == 0.0

    def test_handle_rate_limit_exception_handling(self):
        """Test gracefully handles exceptions."""
        # Create object that raises exception on attribute access
        mock_response = Mock()
        mock_response.headers = None
        type(mock_response).raw_response = property(
            lambda self: (_ for _ in ()).throw(RuntimeError("test"))
        )

        result = RemoteFetcher._handle_rate_limit_from_response(mock_response)
        assert result == 0.0

    @patch("roadmap.core.services.utils.remote_fetcher.time.time")
    def test_handle_rate_limit_negative_wait_becomes_zero(self, mock_time):
        """Test negative wait times are clamped to 0."""
        now = 1010
        reset = 1000  # Reset time is in the past
        mock_time.return_value = now

        response = {
            "headers": {
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset),
            }
        }

        result = RemoteFetcher._handle_rate_limit_from_response(response)
        assert result == 0.0


class TestFetchIssue:
    """Test fetch_issue static method."""

    def test_fetch_issue_with_none_adapter(self):
        """Test returns None when adapter is None."""
        result = RemoteFetcher.fetch_issue(None, "ISSUE-1")
        assert result is None

    def test_fetch_issue_with_no_pull_issue_method(self):
        """Test returns None when adapter lacks pull_issue method."""
        adapter = Mock(spec=[])  # Empty spec, no pull_issue

        result = RemoteFetcher.fetch_issue(adapter, "ISSUE-1")
        assert result is None

    def test_fetch_issue_success(self):
        """Test successful issue fetch."""
        adapter = Mock()
        issue_data = {"id": "ISSUE-1", "title": "Test Issue"}
        adapter.pull_issue.return_value = issue_data

        result = RemoteFetcher.fetch_issue(adapter, "ISSUE-1")

        assert result == issue_data
        adapter.pull_issue.assert_called_once_with("ISSUE-1")

    @patch("roadmap.core.services.utils.remote_fetcher.time.sleep")
    def test_fetch_issue_with_rate_limit_response(self, mock_sleep):
        """Test fetch respects rate-limit from response."""
        adapter = Mock()
        issue_data = {
            "id": "ISSUE-1",
            "headers": {
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time()) + 5),
            },
        }
        adapter.pull_issue.return_value = issue_data

        with patch("roadmap.core.services.utils.remote_fetcher.time.time") as mock_time:
            mock_time.return_value = 1000
            result = RemoteFetcher.fetch_issue(adapter, "ISSUE-1")

        assert result == issue_data
        mock_sleep.assert_called_once()

    def test_fetch_issue_retries_on_exception(self):
        """Test fetch retries on exception."""
        adapter = Mock()
        adapter.pull_issue.side_effect = [
            Exception("Network error"),
            {"id": "ISSUE-1", "title": "Success"},
        ]

        with patch("roadmap.core.services.utils.remote_fetcher.time.sleep"):
            result = RemoteFetcher.fetch_issue(adapter, "ISSUE-1")

        assert result == {"id": "ISSUE-1", "title": "Success"}
        assert adapter.pull_issue.call_count == 2

    def test_fetch_issue_exhausts_retries(self):
        """Test fetch returns None after max retries."""
        adapter = Mock()
        adapter.pull_issue.side_effect = Exception("Network error")

        with patch("roadmap.core.services.utils.remote_fetcher.time.sleep"):
            result = RemoteFetcher.fetch_issue(adapter, "ISSUE-1")

        assert result is None
        # Default max retries = 3
        assert adapter.pull_issue.call_count == 3

    def test_fetch_issue_custom_retry_policy(self):
        """Test fetch uses custom retry policy."""
        adapter = Mock()
        adapter.pull_issue.side_effect = Exception("Network error")
        policy = RetryPolicy(max_retries=2, base_delay=0.1, factor=1.0)

        with patch("roadmap.core.services.utils.remote_fetcher.time.sleep"):
            result = RemoteFetcher.fetch_issue(adapter, "ISSUE-1", retry_policy=policy)

        assert result is None
        assert adapter.pull_issue.call_count == 2


class TestFetchIssues:
    """Test fetch_issues static method."""

    def test_fetch_issues_with_none_adapter(self):
        """Test returns empty list when adapter is None."""
        result = RemoteFetcher.fetch_issues(None, ["ISSUE-1", "ISSUE-2"])
        assert result == []

    def test_fetch_issues_with_empty_ids(self):
        """Test returns empty list for empty issue IDs."""
        adapter = Mock()
        result = RemoteFetcher.fetch_issues(adapter, [])
        assert result == []

    def test_fetch_issues_batch_api_success(self):
        """Test uses batch API when available."""
        adapter = Mock()
        issues = [
            {"id": "ISSUE-1", "title": "Issue 1"},
            {"id": "ISSUE-2", "title": "Issue 2"},
        ]
        adapter.pull_issues.return_value = issues

        result = RemoteFetcher.fetch_issues(adapter, ["ISSUE-1", "ISSUE-2"])

        assert result == issues
        adapter.pull_issues.assert_called_once()

    def test_fetch_issues_falls_back_to_individual_fetch(self):
        """Test falls back to individual fetch when batch API unavailable."""
        adapter = Mock(spec=[])  # No pull_issues method

        issue1 = {"id": "ISSUE-1"}
        issue2 = {"id": "ISSUE-2"}

        with patch(
            "roadmap.core.services.utils.remote_fetcher.RemoteFetcher.fetch_issue"
        ) as mock_fetch_issue:
            mock_fetch_issue.side_effect = [issue1, issue2]

            result = RemoteFetcher.fetch_issues(adapter, ["ISSUE-1", "ISSUE-2"])

        assert result == [issue1, issue2]
        assert mock_fetch_issue.call_count == 2

    @patch("roadmap.core.services.utils.remote_fetcher.time.sleep")
    def test_fetch_issues_batch_with_rate_limit(self, mock_sleep):
        """Test batch fetch respects rate limits."""
        adapter = Mock()
        issues = [{"id": "ISSUE-1"}, {"id": "ISSUE-2"}]
        response = {
            "data": issues,
            "headers": {
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time()) + 5),
            },
        }
        adapter.pull_issues.return_value = response

        with patch("roadmap.core.services.utils.remote_fetcher.time.time") as mock_time:
            mock_time.return_value = 1000
            result = RemoteFetcher.fetch_issues(adapter, ["ISSUE-1", "ISSUE-2"])

        assert result == response
        mock_sleep.assert_called_once()

    def test_fetch_issues_batch_retries(self):
        """Test batch fetch retries on exception."""
        adapter = Mock()
        adapter.pull_issues.side_effect = [
            Exception("Network error"),
            [{"id": "ISSUE-1"}, {"id": "ISSUE-2"}],
        ]

        with patch("roadmap.core.services.utils.remote_fetcher.time.sleep"):
            result = RemoteFetcher.fetch_issues(adapter, ["ISSUE-1", "ISSUE-2"])

        # After batch succeeds on retry, returns results
        assert adapter.pull_issues.call_count == 2  # Initial + 1 retry
        assert result == [{"id": "ISSUE-1"}, {"id": "ISSUE-2"}]

    def test_fetch_issues_batch_returns_empty_list_fallback(self):
        """Test returns empty list if batch returns empty."""
        adapter = Mock()
        adapter.pull_issues.return_value = []

        result = RemoteFetcher.fetch_issues(adapter, ["ISSUE-1", "ISSUE-2"])

        # Batch returns empty list, just returns it (no fallback)
        assert result == []

    @pytest.mark.parametrize(
        "ids,expected_count",
        [
            (["ISSUE-1"], 1),
            (["ISSUE-1", "ISSUE-2", "ISSUE-3"], 3),
            (["A", "B", "C", "D", "E"], 5),
        ],
    )
    def test_fetch_issues_with_various_counts(self, ids, expected_count):
        """Test fetch handles various issue count."""
        adapter = Mock()
        adapter.pull_issues.return_value = [{"id": iid} for iid in ids]

        result = RemoteFetcher.fetch_issues(adapter, ids)

        assert len(result) == expected_count

    def test_fetch_issues_custom_retry_policy(self):
        """Test fetch_issues uses custom retry policy."""
        adapter = Mock(spec=[])  # No pull_issues method
        policy = RetryPolicy(max_retries=1, base_delay=0.01, factor=1.0)

        with patch(
            "roadmap.core.services.utils.remote_fetcher.RemoteFetcher.fetch_issue"
        ) as mock_fetch_issue:
            mock_fetch_issue.return_value = None

            result = RemoteFetcher.fetch_issues(
                adapter, ["ISSUE-1"], retry_policy=policy
            )

        # Batch API not available, falls back to individual fetch
        assert result == [None]
        assert mock_fetch_issue.call_count == 1


class TestRemoteFetcherIntegration:
    """Integration tests for RemoteFetcher."""

    def test_fetch_single_issue_end_to_end(self):
        """Test end-to-end single issue fetch."""
        adapter = Mock()
        expected_issue = {
            "id": "ISSUE-1",
            "title": "Test Issue",
            "status": "open",
        }
        adapter.pull_issue.return_value = expected_issue

        result = RemoteFetcher.fetch_issue(adapter, "ISSUE-1")

        assert result == expected_issue

    def test_fetch_multiple_issues_end_to_end(self):
        """Test end-to-end multiple issue fetch with batch API."""
        adapter = Mock()
        expected_issues = [
            {"id": "ISSUE-1", "title": "Issue 1"},
            {"id": "ISSUE-2", "title": "Issue 2"},
            {"id": "ISSUE-3", "title": "Issue 3"},
        ]
        adapter.pull_issues.return_value = expected_issues

        result = RemoteFetcher.fetch_issues(adapter, ["ISSUE-1", "ISSUE-2", "ISSUE-3"])

        assert result == expected_issues

    @patch("roadmap.core.services.utils.remote_fetcher.time.sleep")
    def test_fetch_with_retry_and_rate_limit(self, mock_sleep):
        """Test fetch retries and handles rate limits."""
        adapter = Mock()

        # First call fails
        adapter.pull_issue.side_effect = [
            Exception("Temporary error"),
            {
                "id": "ISSUE-1",
                "title": "Success",
                "headers": {
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + 5),
                },
            },
        ]

        with patch("roadmap.core.services.utils.remote_fetcher.time.time") as mock_time:
            mock_time.return_value = 1000
            result = RemoteFetcher.fetch_issue(adapter, "ISSUE-1")

        assert result["id"] == "ISSUE-1"
        # One sleep for retry backoff, one for rate limit
        assert mock_sleep.call_count == 2
