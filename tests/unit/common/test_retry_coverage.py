"""Test coverage for retry module."""

import asyncio
import time
from unittest.mock import Mock, patch

import pytest

from roadmap.common.retry import (
    API_RETRY,
    DATABASE_RETRY,
    NETWORK_RETRY,
    RetryConfig,
    async_retry,
    retry,
)


class TestRetryDecorator:
    """Test the retry decorator."""

    @pytest.mark.parametrize(
        "side_effects,max_attempts,expected_calls,should_succeed",
        [
            (["success"], 3, 1, True),
            ([ValueError("fail"), ValueError("fail"), "success"], 5, 3, True),
            ([ValueError("fail"), ValueError("fail"), ValueError("fail")], 3, 3, False),
        ],
    )
    def test_retry_basic_scenarios(
        self, side_effects, max_attempts, expected_calls, should_succeed
    ):
        """Test basic retry scenarios: first attempt, after failures, exhaustion."""
        mock_func = Mock(
            side_effect=side_effects if isinstance(side_effects, list) else side_effects
        )

        @retry(max_attempts=max_attempts, delay=0.01, exceptions=(ValueError,))
        def func():
            return mock_func()

        if should_succeed:
            result = func()
            assert result == "success"
        else:
            with pytest.raises(ValueError):
                func()

        assert mock_func.call_count == expected_calls

    @pytest.mark.parametrize(
        "exception_type,should_retry",
        [
            (ValueError, True),
            (TypeError, False),
        ],
    )
    def test_retry_exception_filtering(self, exception_type, should_retry):
        """Test retry only catches specified exceptions."""
        mock_func = Mock(side_effect=exception_type("error"))

        @retry(max_attempts=3, delay=0.01, exceptions=(ValueError,))
        def func():
            return mock_func()

        if should_retry:
            # ValueError should be caught and exhausted
            with pytest.raises(ValueError):
                func()
            assert mock_func.call_count == 3
        else:
            # TypeError should not be caught
            with pytest.raises(TypeError):
                func()
            assert mock_func.call_count == 1

    def test_retry_with_multiple_exceptions(self):
        """Test retry with multiple exception types."""
        mock_func = Mock(
            side_effect=[ValueError("val error"), TypeError("type error"), "success"]
        )

        @retry(
            max_attempts=5,
            delay=0.01,
            exceptions=(ValueError, TypeError),
        )
        def func():
            return mock_func()

        result = func()
        assert result == "success"
        assert mock_func.call_count == 3

    def test_retry_exponential_backoff(self):
        """Test that exponential backoff increases delays."""
        start_times = []

        @retry(max_attempts=4, delay=0.05, backoff=2.0, exceptions=(ValueError,))
        def func():
            start_times.append(time.time())
            if len(start_times) < 4:
                raise ValueError("fail")
            return "success"

        result = func()
        assert result == "success"
        assert len(start_times) == 4

        # Check that delays are increasing (approximately exponential)
        delay1 = start_times[1] - start_times[0]
        delay2 = start_times[2] - start_times[1]
        delay3 = start_times[3] - start_times[2]

        # Delays should be roughly: 0.05, 0.1, 0.2
        assert delay2 > delay1  # Second delay larger than first
        assert delay3 > delay2  # Third delay larger than second

    @pytest.mark.parametrize(
        "delay,backoff,description",
        [
            (0.05, 2.0, "exponential"),
            (0.01, 10.0, "large_backoff"),
            (0.0, 1.0, "zero_delay"),
        ],
    )
    def test_retry_delay_configurations(self, delay, backoff, description):
        """Test retry with various delay configurations."""
        mock_func = Mock(side_effect=[ValueError("fail"), "success"])

        @retry(max_attempts=3, delay=delay, backoff=backoff, exceptions=(ValueError,))
        def func():
            return mock_func()

        result = func()
        assert result == "success"
        assert mock_func.call_count == 2
        """Test retry with on_retry callback."""
        callback_mock = Mock()
        mock_func = Mock(side_effect=[ValueError("fail"), "success"])

        @retry(
            max_attempts=3,
            delay=0.01,
            exceptions=(ValueError,),
            on_retry=callback_mock,
        )
        def func():
            return mock_func()

        result = func()
        assert result == "success"

        # Callback should be called once on first failure
        assert callback_mock.call_count == 1
        args, _ = callback_mock.call_args
        assert isinstance(args[0], ValueError)
        assert args[1] == 1  # First attempt number

    def test_retry_callback_receives_correct_attempt_number(self):
        """Test that retry callback receives correct attempt numbers."""
        callback_mock = Mock()
        call_count = [0]

        def func_with_failures():
            call_count[0] += 1
            if call_count[0] < 4:
                raise ValueError("fail")
            return "success"

        @retry(
            max_attempts=5,
            delay=0.01,
            exceptions=(ValueError,),
            on_retry=callback_mock,
        )
        def func():
            return func_with_failures()

        result = func()
        assert result == "success"

        # Callback should be called 3 times (attempts 1, 2, 3)
        assert callback_mock.call_count == 3

        # Check attempt numbers
        attempt_numbers = [call[0][1] for call in callback_mock.call_args_list]
        assert attempt_numbers == [1, 2, 3]

    def test_retry_callback_error_is_logged(self):
        """Test that callback errors are handled gracefully."""
        callback_mock = Mock(side_effect=RuntimeError("callback failed"))
        mock_func = Mock(side_effect=[ValueError("fail"), "success"])

        with patch("roadmap.common.retry.logger"):

            @retry(
                max_attempts=3,
                delay=0.01,
                exceptions=(ValueError,),
                on_retry=callback_mock,
            )
            def func():
                return mock_func()

            result = func()
            assert result == "success"
            assert callback_mock.call_count == 1

    def test_retry_preserves_function_metadata(self):
        """Test that retry decorator preserves function metadata."""

        @retry(max_attempts=3, delay=0.01)
        def my_function():
            """My function docstring."""
            return "result"

        assert my_function.__name__ == "my_function"
        assert (
            my_function.__doc__ is not None
            and "My function docstring" in my_function.__doc__
        )

    def test_retry_with_function_arguments(self):
        """Test retry with positional and keyword arguments."""
        mock_func = Mock(side_effect=[ValueError("fail"), "success"])

        @retry(max_attempts=3, delay=0.01, exceptions=(ValueError,))
        def func(a, b, c=None):
            mock_func()
            return f"{a}-{b}-{c}"

        result = func(1, 2, c=3)
        assert result == "1-2-3"
        assert mock_func.call_count == 2

    def test_retry_with_zero_delay(self):
        """Test retry with zero delay."""
        mock_func = Mock(side_effect=[ValueError("fail"), "success"])

        @retry(max_attempts=3, delay=0.0, exceptions=(ValueError,))
        def func():
            return mock_func()

        result = func()
        assert result == "success"
        assert mock_func.call_count == 2

    def test_retry_with_large_backoff(self):
        """Test retry with large backoff factor."""
        mock_func = Mock(side_effect=[ValueError("fail"), "success"])

        @retry(max_attempts=3, delay=0.01, backoff=10.0, exceptions=(ValueError,))
        def func():
            return mock_func()

        result = func()
        assert result == "success"
        assert mock_func.call_count == 2

    def test_retry_max_attempts_one(self):
        """Test retry with max_attempts=1 (no retries)."""
        mock_func = Mock(side_effect=ValueError("fail"))

        @retry(max_attempts=1, delay=0.01, exceptions=(ValueError,))
        def func():
            return mock_func()

        with pytest.raises(ValueError):
            func()

        assert mock_func.call_count == 1

    def test_retry_returns_none(self):
        """Test retry works with functions returning None."""
        mock_func = Mock(return_value=None)

        @retry(max_attempts=3, delay=0.01)
        def func():
            return mock_func()

        result = func()
        assert result is None
        assert mock_func.call_count == 1

    def test_retry_with_exception_hierarchy(self):
        """Test retry catches exceptions from inheritance hierarchy."""

        class CustomError(ValueError):
            pass

        mock_func = Mock(side_effect=[CustomError("custom"), "success"])

        @retry(max_attempts=3, delay=0.01, exceptions=(ValueError,))
        def func():
            return mock_func()

        result = func()
        assert result == "success"
        assert mock_func.call_count == 2


class TestRetryEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_retry_with_very_small_delay(self):
        """Test retry with very small delay value."""
        mock_func = Mock(side_effect=[ValueError("fail"), "success"])

        @retry(max_attempts=3, delay=0.001, exceptions=(ValueError,))
        def func():
            return mock_func()

        result = func()
        assert result == "success"

    def test_retry_decorator_multiple_decorators(self):
        """Test retry can be used with other decorators."""

        def other_decorator(func):
            def wrapper(*args, **kwargs):
                return f"decorated({func(*args, **kwargs)})"

            return wrapper

        @other_decorator
        @retry(max_attempts=2, delay=0.01, exceptions=(ValueError,))
        def func():
            return "result"

        result = func()
        assert result == "decorated(result)"

    def test_retry_with_default_exception_any(self):
        """Test retry catches all exceptions by default."""
        mock_func = Mock(
            side_effect=[RuntimeError("error"), TypeError("type"), "success"]
        )

        @retry(max_attempts=4, delay=0.01)  # No exceptions specified
        def func():
            return mock_func()

        result = func()
        assert result == "success"
        assert mock_func.call_count == 3

    def test_retry_callback_with_different_exception_types(self):
        """Test callback receives different exception types."""
        exceptions_received = []

        def callback(exc, attempt):
            exceptions_received.append(type(exc).__name__)

        call_count = [0]

        def func_with_different_errors():
            call_count[0] += 1
            if call_count[0] == 1:
                raise ValueError("val")
            elif call_count[0] == 2:
                raise TypeError("type")
            return "success"

        @retry(
            max_attempts=4,
            delay=0.01,
            exceptions=(ValueError, TypeError),
            on_retry=callback,
        )
        def func():
            return func_with_different_errors()

        result = func()
        assert result == "success"
        assert exceptions_received == ["ValueError", "TypeError"]


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
    async def test_async_retry_success_first_attempt(self):
        """Test async retry succeeds on first attempt."""
        async_mock = Mock(return_value="success")

        @async_retry(max_attempts=3, delay=0.01)
        async def func():
            return async_mock()

        result = await func()
        assert result == "success"
        assert async_mock.call_count == 1

    @pytest.mark.asyncio
    async def test_async_retry_with_failures(self):
        """Test async retry after failures."""
        async_mock = Mock(side_effect=[ValueError("fail"), "success"])

        @async_retry(max_attempts=3, delay=0.01, exceptions=(ValueError,))
        async def func():
            return async_mock()

        result = await func()
        assert result == "success"
        assert async_mock.call_count == 2

    @pytest.mark.asyncio
    async def test_async_retry_exhausts_attempts(self):
        """Test async retry raises when attempts exhausted."""
        async_mock = Mock(side_effect=ValueError("persistent error"))

        @async_retry(max_attempts=2, delay=0.01, exceptions=(ValueError,))
        async def func():
            return async_mock()

        with pytest.raises(ValueError):
            await func()

        assert async_mock.call_count == 2

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

    def test_retry_config_creation(self):
        """Test RetryConfig initialization."""
        config = RetryConfig(
            max_attempts=5,
            delay=2.0,
            backoff=3.0,
            exceptions=(ValueError, TypeError),
        )

        assert config.max_attempts == 5
        assert config.delay == 2.0
        assert config.backoff == 3.0
        assert config.exceptions == (ValueError, TypeError)

    def test_retry_config_default_values(self):
        """Test RetryConfig with default values."""
        config = RetryConfig()

        assert config.max_attempts == 3
        assert config.delay == 1.0
        assert config.backoff == 2.0
        assert config.exceptions == (Exception,)

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

    def test_network_retry_config(self):
        """Test NETWORK_RETRY configuration."""
        assert NETWORK_RETRY.max_attempts == 5
        assert NETWORK_RETRY.delay == 1.0
        assert NETWORK_RETRY.backoff == 2.0
        assert ConnectionError in NETWORK_RETRY.exceptions
        assert TimeoutError in NETWORK_RETRY.exceptions

    def test_api_retry_config(self):
        """Test API_RETRY configuration."""
        assert API_RETRY.max_attempts == 3
        assert API_RETRY.delay == 0.5
        assert API_RETRY.backoff == 1.5
        assert ConnectionError in API_RETRY.exceptions
        assert TimeoutError in API_RETRY.exceptions

    def test_database_retry_config(self):
        """Test DATABASE_RETRY configuration."""
        assert DATABASE_RETRY.max_attempts == 3
        assert DATABASE_RETRY.delay == 0.1
        assert DATABASE_RETRY.backoff == 2.0

    def test_network_retry_usage(self):
        """Test using NETWORK_RETRY configuration."""
        mock_func = Mock(side_effect=[ConnectionError("fail"), "success"])

        @NETWORK_RETRY
        def func():
            return mock_func()

        result = func()
        assert result == "success"
        assert mock_func.call_count == 2

    def test_api_retry_with_timeout(self):
        """Test API_RETRY with timeout exception."""
        mock_func = Mock(side_effect=[TimeoutError("timeout"), "success"])

        @API_RETRY
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
