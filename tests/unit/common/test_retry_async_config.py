"""Test coverage for retry module."""

import asyncio
import time
from unittest.mock import Mock

import pytest

from roadmap.common.services import (
    API_RETRY,
    DATABASE_RETRY,
    NETWORK_RETRY,
    RetryConfig,
    async_retry,
    retry,
)


class TestRetryIntegration:
    """Integration tests for retry functionality."""

    def test_retry_with_real_time_delays(self):
        """Test retry with measurable time delays."""
        start_time = time.time()
        attempt_times = []

        def track_attempts():
            attempt_times.append(time.time() - start_time)
            if len(attempt_times) < 3:
                raise ValueError("fail")
            return "success"

        @retry(max_attempts=5, delay=0.05, backoff=1.5, exceptions=(ValueError,))
        def func():
            return track_attempts()

        result = func()
        assert result == "success"
        assert len(attempt_times) == 3

        # First attempt should be near 0
        assert attempt_times[0] < 0.1

    def test_retry_class_method(self):
        """Test retry on class methods."""

        class MyClass:
            def __init__(self):
                self.attempts = 0

            @retry(max_attempts=3, delay=0.01, exceptions=(ValueError,))
            def method(self):
                self.attempts += 1
                if self.attempts < 3:
                    raise ValueError("fail")
                return "success"

        obj = MyClass()
        result = obj.method()
        assert result == "success"
        assert obj.attempts == 3

    def test_retry_with_state_changes(self):
        """Test retry with functions that have side effects."""
        state = {"counter": 0}

        @retry(max_attempts=4, delay=0.01, exceptions=(ValueError,))
        def func():
            state["counter"] += 1
            if state["counter"] < 3:
                raise ValueError("fail")
            return state["counter"]

        result = func()
        assert result == 3
        assert state["counter"] == 3


class TestAsyncRetry:
    """Test async retry decorator."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "side_effects,expected_calls,should_succeed",
        [
            (["success"], 1, True),
            ([ValueError("fail"), "success"], 2, True),
            ([ValueError("fail"), ValueError("fail"), ValueError("fail")], 3, False),
        ],
    )
    async def test_async_retry_scenarios(
        self, side_effects, expected_calls, should_succeed
    ):
        """Test async retry scenarios: success, with failures, exhaustion."""
        async_mock = Mock(side_effect=side_effects)

        @async_retry(max_attempts=3, delay=0.01, exceptions=(ValueError,))
        async def func():
            return async_mock()

        if should_succeed:
            result = await func()
            assert result == "success"
        else:
            with pytest.raises(ValueError):
                await func()

        assert async_mock.call_count == expected_calls

    @pytest.mark.asyncio
    async def test_async_retry_exponential_backoff(self):
        """Test async retry with exponential backoff."""
        call_count = [0]

        @async_retry(max_attempts=4, delay=0.05, backoff=2.0, exceptions=(ValueError,))
        async def func():
            call_count[0] += 1
            if call_count[0] < 4:
                raise ValueError("fail")
            return "success"

        result = await func()
        assert result == "success"
        assert call_count[0] == 4


class TestRetryConfig:
    """Test RetryConfig class."""

    @pytest.mark.parametrize(
        "max_attempts,delay,backoff,exceptions,description",
        [
            (5, 2.0, 3.0, (ValueError, TypeError), "custom"),
            (3, 1.0, 2.0, (Exception,), "defaults"),
        ],
    )
    def test_retry_config_scenarios(
        self, max_attempts, delay, backoff, exceptions, description
    ):
        """Test RetryConfig creation and properties."""
        config = RetryConfig(
            max_attempts=max_attempts,
            delay=delay,
            backoff=backoff,
            exceptions=exceptions,
        )

        assert config.max_attempts == max_attempts
        assert config.delay == delay
        assert config.backoff == backoff
        assert config.exceptions == exceptions

    def test_retry_config_as_decorator(self):
        """Test using RetryConfig as a decorator."""
        config = RetryConfig(max_attempts=3, delay=0.01, exceptions=(ValueError,))
        mock_func = Mock(side_effect=[ValueError("fail"), "success"])

        @config
        def func():
            return mock_func()

        result = func()
        assert result == "success"
        assert mock_func.call_count == 2

    def test_retry_config_async_decorator(self):
        """Test using RetryConfig as async decorator."""
        config = RetryConfig(max_attempts=3, delay=0.01, exceptions=(ValueError,))

        @config.async_decorator
        async def func():
            await asyncio.sleep(0)
            return "success"

        result = asyncio.run(func())
        assert result == "success"


class TestPredefinedRetryConfigs:
    """Test predefined retry configurations."""

    @pytest.mark.parametrize(
        "config_obj,expected_attempts,expected_delay,error_types",
        [
            (NETWORK_RETRY, 5, 1.0, [ConnectionError, TimeoutError]),
            (API_RETRY, 3, 0.5, [ConnectionError, TimeoutError]),
        ],
    )
    def test_predefined_config_properties(
        self, config_obj, expected_attempts, expected_delay, error_types
    ):
        """Test predefined retry configuration properties."""
        assert config_obj.max_attempts == expected_attempts
        assert config_obj.delay == expected_delay
        for error_type in error_types:
            assert error_type in config_obj.exceptions

    def test_database_retry_config(self):
        """Test DATABASE_RETRY configuration."""
        assert DATABASE_RETRY.max_attempts == 3
        assert DATABASE_RETRY.delay == 0.1
        assert DATABASE_RETRY.backoff == 2.0

    @pytest.mark.parametrize(
        "config_obj,exception_type",
        [
            (NETWORK_RETRY, ConnectionError),
            (API_RETRY, TimeoutError),
        ],
    )
    def test_retry_config_usage(self, config_obj, exception_type):
        """Test using predefined retry configurations."""
        mock_func = Mock(side_effect=[exception_type("fail"), "success"])

        @config_obj
        def func():
            return mock_func()

        result = func()
        assert result == "success"
        assert mock_func.call_count == 2

    def test_network_retry_doesnt_catch_other_errors(self):
        """Test NETWORK_RETRY doesn't catch non-network errors."""
        mock_func = Mock(side_effect=ValueError("value error"))

        @NETWORK_RETRY
        def func():
            return mock_func()

        with pytest.raises(ValueError):
            func()

        # Should fail on first attempt
        assert mock_func.call_count == 1
