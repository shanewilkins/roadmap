"""Tests for Result type and error handling patterns."""

import pytest

from roadmap.common.result import (
    Err,
    Ok,
    Result,
    all_ok,
    any_err,
    collect_results,
    first_err,
    partition_results,
    wrap_result,
)


class TestOk:
    """Tests for Ok variant."""

    def test_is_ok_returns_true(self):
        result: Result[int, str] = Ok(42)
        assert result.is_ok()

    def test_is_err_returns_false(self):
        result: Result[int, str] = Ok(42)
        assert not result.is_err()

    def test_unwrap_returns_value(self):
        result: Result[int, str] = Ok(42)
        assert result.unwrap() == 42

    def test_unwrap_err_raises(self):
        result: Result[int, str] = Ok(42)
        with pytest.raises(ValueError, match="Called unwrap_err"):
            result.unwrap_err()

    def test_unwrap_or_returns_value(self):
        result: Result[int, str] = Ok(42)
        assert result.unwrap_or(100) == 42

    def test_unwrap_or_else_returns_value(self):
        result: Result[int, str] = Ok(42)
        assert result.unwrap_or_else(lambda e: 100) == 42

    def test_map_transforms_value(self):
        result: Result[int, str] = Ok(42)
        mapped = result.map(lambda x: x * 2)  # type: ignore[operator]
        assert mapped.is_ok()
        assert mapped.unwrap() == 84

    def test_map_err_is_noop(self):
        result: Result[int, str] = Ok(42)
        mapped = result.map_err(str.upper)
        assert mapped.is_ok()
        assert mapped.unwrap() == 42

    def test_and_then_chains_operation(self):
        result: Result[int, str] = Ok(42)
        chained = result.and_then(lambda x: Ok(x * 2))
        assert chained.is_ok()
        assert chained.unwrap() == 84

    def test_and_then_propagates_error(self):
        result: Result[int, str] = Ok(42)
        chained = result.and_then(lambda x: Err("failed"))
        assert chained.is_err()
        assert chained.unwrap_err() == "failed"

    def test_or_else_is_noop(self):
        result: Result[int, str] = Ok(42)
        alternative = result.or_else(lambda e: Ok(100))
        assert alternative.is_ok()
        assert alternative.unwrap() == 42


class TestErr:
    """Tests for Err variant."""

    def test_is_ok_returns_false(self):
        result: Result[int, str] = Err("error")
        assert not result.is_ok()

    def test_is_err_returns_true(self):
        result: Result[int, str] = Err("error")
        assert result.is_err()

    def test_unwrap_raises(self):
        result: Result[int, str] = Err("error")
        with pytest.raises(ValueError, match="Called unwrap"):
            result.unwrap()

    def test_unwrap_err_returns_error(self):
        result: Result[int, str] = Err("error")
        assert result.unwrap_err() == "error"

    def test_unwrap_or_returns_default(self):
        result: Result[int, str] = Err("error")
        assert result.unwrap_or(100) == 100

    def test_unwrap_or_else_computes_default(self):
        result: Result[int, str] = Err("error")
        assert result.unwrap_or_else(lambda e: len(e)) == 5

    def test_map_is_noop(self):
        result: Result[int, str] = Err("error")
        mapped: Result[int, str] = result.map(lambda x: 42)  # Never executes for Err
        assert mapped.is_err()
        assert mapped.unwrap_err() == "error"

    def test_map_err_transforms_error(self):
        result: Result[int, str] = Err("error")
        mapped = result.map_err(lambda e: e.upper())
        assert mapped.is_err()
        assert mapped.unwrap_err() == "ERROR"

    def test_and_then_is_noop(self):
        result: Result[int, str] = Err("error")
        chained: Result[int, str] = result.and_then(
            lambda x: Ok(42)
        )  # Never executes for Err
        assert chained.is_err()
        assert chained.unwrap_err() == "error"

    def test_or_else_provides_alternative(self):
        result: Result[int, str] = Err("error")
        alternative = result.or_else(lambda e: Ok(100))
        assert alternative.is_ok()
        assert alternative.unwrap() == 100

    def test_or_else_can_return_another_err(self):
        result: Result[int, str] = Err("error")
        alternative = result.or_else(lambda e: Err(f"wrapped: {e}"))
        assert alternative.is_err()
        assert alternative.unwrap_err() == "wrapped: error"


class TestWrapResult:
    """Tests for wrap_result decorator."""

    def test_wraps_successful_function(self):
        @wrap_result
        def succeed(x: int) -> int:
            return x * 2

        result = succeed(5)
        assert result.is_ok()
        assert result.unwrap() == 10

    def test_wraps_failing_function(self):
        @wrap_result
        def fail(x: int) -> int:
            raise ValueError("test error")

        result = fail(5)
        assert result.is_err()
        error = result.unwrap_err()
        assert isinstance(error, ValueError)
        assert str(error) == "test error"

    def test_preserves_different_exception_types(self):
        @wrap_result
        def type_fail() -> int:
            raise TypeError("wrong type")

        result = type_fail()
        assert result.is_err()
        assert isinstance(result.unwrap_err(), TypeError)


class TestCollectResults:
    """Tests for collect_results helper."""

    def test_collects_all_ok(self):
        results: list[Result[int, str]] = [Ok(1), Ok(2), Ok(3)]
        collected = collect_results(results)
        assert collected.is_ok()
        assert collected.unwrap() == [1, 2, 3]

    def test_returns_first_err(self):
        results: list[Result[int, str]] = [Ok(1), Err("error1"), Ok(3), Err("error2")]
        collected = collect_results(results)
        assert collected.is_err()
        assert collected.unwrap_err() == "error1"

    def test_empty_list(self):
        results: list[Result[int, str]] = []
        collected = collect_results(results)
        assert collected.is_ok()
        assert collected.unwrap() == []


class TestPartitionResults:
    """Tests for partition_results helper."""

    def test_partitions_mixed_results(self):
        results = [Ok(1), Err("a"), Ok(2), Err("b"), Ok(3)]
        successes, errors = partition_results(results)
        assert successes == [1, 2, 3]
        assert errors == ["a", "b"]

    def test_all_successes(self):
        results: list[Result[int, str]] = [Ok(1), Ok(2), Ok(3)]
        successes, errors = partition_results(results)
        assert successes == [1, 2, 3]
        assert errors == []

    def test_all_errors(self):
        results: list[Result[int, str]] = [Err("a"), Err("b"), Err("c")]
        successes, errors = partition_results(results)
        assert successes == []
        assert errors == ["a", "b", "c"]


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_all_ok_with_all_success(self):
        results: list[Result[int, str]] = [Ok(1), Ok(2), Ok(3)]
        assert all_ok(results)

    def test_all_ok_with_any_error(self):
        results: list[Result[int, str]] = [Ok(1), Err("error"), Ok(3)]
        assert not all_ok(results)

    def test_any_err_with_errors(self):
        results: list[Result[int, str]] = [Ok(1), Err("error"), Ok(3)]
        assert any_err(results)

    def test_any_err_with_no_errors(self):
        results: list[Result[int, str]] = [Ok(1), Ok(2), Ok(3)]
        assert not any_err(results)

    def test_first_err_returns_first_error(self):
        results: list[Result[int, str]] = [Ok(1), Err("error1"), Err("error2")]
        first = first_err(results)
        assert first.is_err()
        assert first.unwrap_err() == "error1"

    def test_first_err_with_no_errors(self):
        results: list[Result[int, str]] = [Ok(1), Ok(2), Ok(3)]
        first = first_err(results)
        assert first.is_ok()
        assert first.unwrap() is None


class TestRailwayOrientedProgramming:
    """Tests for chaining Results in railway-oriented style."""

    def test_successful_chain(self):
        """Test chaining multiple operations when all succeed."""

        def parse_int(s: str) -> Result[int, str]:
            try:
                return Ok(int(s))
            except ValueError:
                return Err(f"Not an int: {s}")

        def divide_by_two(n: int) -> Result[float, str]:
            return Ok(n / 2)

        def format_result(n: float) -> Result[str, str]:
            return Ok(f"Result: {n}")

        result = parse_int("42").and_then(divide_by_two).and_then(format_result)

        assert result.is_ok()
        assert result.unwrap() == "Result: 21.0"

    def test_chain_with_early_failure(self):
        """Test that error propagates through chain."""

        def parse_int(s: str) -> Result[int, str]:
            try:
                return Ok(int(s))
            except ValueError:
                return Err(f"Not an int: {s}")

        def divide_by_two(n: int) -> Result[float, str]:
            return Ok(n / 2)

        def format_result(n: float) -> Result[str, str]:
            return Ok(f"Result: {n}")

        result = (
            parse_int("not a number").and_then(divide_by_two).and_then(format_result)
        )

        assert result.is_err()
        assert result.unwrap_err() == "Not an int: not a number"

    def test_map_chain(self):
        """Test using map for simple transformations."""
        start: Result[int, str] = Ok(10)
        doubled: Result[int, str] = start.map(
            lambda x: 20
        )  # Testing chain, not operation
        added: Result[int, str] = doubled.map(
            lambda x: 25
        )  # Testing chain, not operation
        result: Result[str, str] = added.map(lambda x: "25")  # Final transformation

        assert result.is_ok()
        assert result.unwrap() == "25"
