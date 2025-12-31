"""Test coverage for retry module."""

from unittest.mock import Mock, patch

import pytest

from roadmap.common.retry import (
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
        sleep_times = []

        # Mock time.sleep to capture sleep durations
        def mock_sleep(duration):
            sleep_times.append(duration)

        with patch("time.sleep", side_effect=mock_sleep):
            call_count = [0]

            @retry(max_attempts=4, delay=0.05, backoff=2.0, exceptions=(ValueError,))
            def func():
                call_count[0] += 1
                if call_count[0] < 4:
                    raise ValueError("fail")
                return "success"

            result = func()
            assert result == "success"
            assert call_count[0] == 4

        # Verify we captured the sleep calls (3 retries = 3 sleeps)
        assert len(sleep_times) == 3

        # Verify exponential backoff: 0.05, 0.1, 0.2
        assert (
            abs(sleep_times[0] - 0.05) < 0.001
        ), f"First sleep should be ~0.05, got {sleep_times[0]}"
        assert (
            abs(sleep_times[1] - 0.1) < 0.001
        ), f"Second sleep should be ~0.1, got {sleep_times[1]}"
        assert (
            abs(sleep_times[2] - 0.2) < 0.001
        ), f"Third sleep should be ~0.2, got {sleep_times[2]}"

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
