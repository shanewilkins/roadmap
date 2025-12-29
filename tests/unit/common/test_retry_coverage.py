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

    def test_retry_with_on_retry_callback(self):
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

    def test_retry_callback_scenarios(self):
        """Test retry callback in various scenarios."""
        # Test 1: Basic callback on retry
        callback_mock = Mock()
        mock_func = Mock(side_effect=[ValueError("fail"), "success"])

        @retry(
            max_attempts=3,
            delay=0.01,
            exceptions=(ValueError,),
            on_retry=callback_mock,
        )
        def func1():
            return mock_func()

        result = func1()
        assert result == "success"
        assert callback_mock.call_count == 1
        args, _ = callback_mock.call_args
        assert isinstance(args[0], ValueError)
        assert args[1] == 1  # First attempt number

        # Test 2: Callback receives correct attempt numbers
        callback_mock2 = Mock()
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
            on_retry=callback_mock2,
        )
        def func2():
            return func_with_failures()

        result = func2()
        assert result == "success"
        assert callback_mock2.call_count == 3
        attempt_numbers = [call[0][1] for call in callback_mock2.call_args_list]
        assert attempt_numbers == [1, 2, 3]

        # Test 3: Callback errors are handled gracefully
        callback_mock3 = Mock(side_effect=RuntimeError("callback failed"))
        mock_func3 = Mock(side_effect=[ValueError("fail"), "success"])

        with patch("roadmap.common.retry.logger"):

            @retry(
                max_attempts=3,
                delay=0.01,
                exceptions=(ValueError,),
                on_retry=callback_mock3,
            )
            def func3():
                return mock_func3()

            result = func3()
            assert result == "success"
            assert callback_mock3.call_count == 1

    @pytest.mark.parametrize(
        "test_case",
        [
            ("metadata", None, None),
            ("function_args", (1, 2), {"c": 3}),
            ("exception_hierarchy", None, None),
        ],
    )
    def test_retry_function_behavior(self, test_case):
        """Test retry with function metadata, arguments, and exception hierarchy."""
        if test_case == "metadata":

            @retry(max_attempts=3, delay=0.01)
            def my_function():
                """My function docstring."""
                return "result"

            assert my_function.__name__ == "my_function"
            assert (
                my_function.__doc__ is not None
                and "My function docstring" in my_function.__doc__
            )
        elif test_case == "function_args":
            mock_func = Mock(side_effect=[ValueError("fail"), "success"])

            @retry(max_attempts=3, delay=0.01, exceptions=(ValueError,))
            def func_with_args(a, b, c=None):
                mock_func()
                return f"{a}-{b}-{c}"

            result = func_with_args(1, 2, c=3)
            assert result == "1-2-3"
            assert mock_func.call_count == 2
        elif test_case == "exception_hierarchy":

            class CustomError(ValueError):
                pass

            mock_func = Mock(side_effect=[CustomError("custom"), "success"])

            @retry(max_attempts=3, delay=0.01, exceptions=(ValueError,))
            def func():
                return mock_func()

            result = func()
            assert result == "success"
            assert mock_func.call_count == 2

    @pytest.mark.parametrize(
        "max_attempts,return_value,should_fail",
        [
            (1, None, True),
            (3, None, False),
            (3, 42, False),
        ],
    )
    def test_retry_edge_values(self, max_attempts, return_value, should_fail):
        """Test retry with edge case values."""
        if should_fail:
            mock_func = Mock(side_effect=ValueError("fail"))

            @retry(max_attempts=max_attempts, delay=0.01, exceptions=(ValueError,))
            def func():
                return mock_func()

            with pytest.raises(ValueError):
                func()

            assert mock_func.call_count == max_attempts
        else:
            if return_value is None:
                mock_func = Mock(return_value=None)
            else:
                mock_func = Mock(return_value=return_value)

            @retry(max_attempts=max_attempts, delay=0.0, exceptions=(ValueError,))
            def func():
                return mock_func()

            result = func()
            assert result == return_value
            assert mock_func.call_count == 1


class TestRetryEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.parametrize(
        "delay,scenario",
        [
            (0.001, "very_small"),
            (0.05, "small_with_backoff"),
            (0.0, "zero_delay"),
        ],
    )
    def test_retry_delay_scenarios(self, delay, scenario):
        """Test retry with various delay scenarios."""
        mock_func = Mock(side_effect=[ValueError("fail"), "success"])

        @retry(max_attempts=3, delay=delay, exceptions=(ValueError,))
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
