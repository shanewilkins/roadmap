"""Result type for functional error handling.

This module provides a Result[T, E] type for railway-oriented programming,
enabling explicit error handling without exceptions. Based on Rust's Result type.

Examples:
    >>> def divide(a: int, b: int) -> Result[float, str]:
    ...     if b == 0:
    ...         return Err("Division by zero")
    ...     return Ok(a / b)
    ...
    >>> result = divide(10, 2)
    >>> if result.is_ok():
    ...     print(f"Success: {result.unwrap()}")
    ...
    >>> result = divide(10, 0)
    >>> if result.is_err():
    ...     print(f"Error: {result.unwrap_err()}")
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic, NoReturn, TypeVar, Union

T = TypeVar("T")  # Success type
E = TypeVar("E")  # Error type
U = TypeVar("U")  # Mapped success type


@dataclass(frozen=True)
class Ok(Generic[T]):
    """Success variant of Result type.

    Contains a successful value of type T.

    Attributes:
        value: The successful result value
    """

    value: T

    def is_ok(self) -> bool:
        """Check if this is an Ok variant.

        Returns:
            Always True for Ok
        """
        return True

    def is_err(self) -> bool:
        """Check if this is an Err variant.

        Returns:
            Always False for Ok
        """
        return False

    def unwrap(self) -> T:
        """Extract the success value.

        Returns:
            The contained value
        """
        return self.value

    def unwrap_err(self) -> NoReturn:
        """Attempt to extract error (raises exception).

        Raises:
            ValueError: Always, since Ok doesn't contain an error
        """
        raise ValueError(f"Called unwrap_err() on Ok value: {self.value}")

    def unwrap_or(self, default: T) -> T:
        """Extract value or return default.

        Args:
            default: Value to return if this is Err (unused)

        Returns:
            The contained value
        """
        return self.value

    def unwrap_or_else(self, op: Callable[[E], T]) -> T:
        """Extract value or compute from error.

        Args:
            op: Function to compute default from error (unused)

        Returns:
            The contained value
        """
        return self.value

    def map(self, op: Callable[[T], U]) -> Result[U, E]:
        """Map the success value through a function.

        Args:
            op: Function to transform the value

        Returns:
            Ok with transformed value
        """
        return Ok(op(self.value))

    def map_err(self, op: Callable[[E], Any]) -> Result[T, Any]:
        """Map the error through a function (no-op for Ok).

        Args:
            op: Function to transform error (unused)

        Returns:
            Self unchanged
        """
        return self

    def and_then(self, op: Callable[[T], Result[U, E]]) -> Result[U, E]:
        """Chain another Result-returning operation.

        Also known as flatMap or bind. Enables railway-oriented programming.

        Args:
            op: Function that takes success value and returns new Result

        Returns:
            Result from applying op to contained value
        """
        return op(self.value)

    def or_else(self, op: Callable[[E], Result[T, Any]]) -> Result[T, Any]:
        """Provide alternative on error (no-op for Ok).

        Args:
            op: Function to compute alternative Result (unused)

        Returns:
            Self unchanged
        """
        return self


@dataclass(frozen=True)
class Err(Generic[E]):
    """Error variant of Result type.

    Contains an error value of type E.

    Attributes:
        error: The error value
    """

    error: E

    def is_ok(self) -> bool:
        """Check if this is an Ok variant.

        Returns:
            Always False for Err
        """
        return False

    def is_err(self) -> bool:
        """Check if this is an Err variant.

        Returns:
            Always True for Err
        """
        return True

    def unwrap(self) -> NoReturn:
        """Attempt to extract value (raises exception).

        Raises:
            ValueError: Always, since Err doesn't contain a value
        """
        raise ValueError(f"Called unwrap() on Err value: {self.error}")

    def unwrap_err(self) -> E:
        """Extract the error value.

        Returns:
            The contained error
        """
        return self.error

    def unwrap_or(self, default: T) -> T:
        """Extract value or return default.

        Args:
            default: Value to return since this is Err

        Returns:
            The default value
        """
        return default

    def unwrap_or_else(self, op: Callable[[E], T]) -> T:
        """Extract value or compute from error.

        Args:
            op: Function to compute default from error

        Returns:
            Result of applying op to the error
        """
        return op(self.error)

    def map(self, op: Callable[[T], U]) -> Result[U, E]:
        """Map the success value through a function (no-op for Err).

        Args:
            op: Function to transform value (unused)

        Returns:
            Self unchanged (with correct type)
        """
        return Err(self.error)

    def map_err(self, op: Callable[[E], Any]) -> Result[T, Any]:
        """Map the error through a function.

        Args:
            op: Function to transform the error

        Returns:
            Err with transformed error
        """
        return Err(op(self.error))

    def and_then(self, op: Callable[[T], Result[U, E]]) -> Result[U, E]:
        """Chain another Result-returning operation (no-op for Err).

        Args:
            op: Function to chain (unused)

        Returns:
            Self unchanged (with correct type)
        """
        return Err(self.error)

    def or_else(self, op: Callable[[E], Result[T, Any]]) -> Result[T, Any]:
        """Provide alternative on error.

        Args:
            op: Function to compute alternative Result from error

        Returns:
            Result from applying op to error
        """
        return op(self.error)


# Type alias for Result[T, E]
Result = Union[Ok[T], Err[E]]


# Helper functions for working with Results


def wrap_result(func: Callable[..., T]) -> Callable[..., Result[T, Exception]]:
    """Decorator to convert exception-raising functions to Result-returning.

    Catches any exception and returns it as Err, or Ok on success.

    Args:
        func: Function that may raise exceptions

    Returns:
        Wrapped function that returns Result[T, Exception]

    Example:
        >>> @wrap_result
        ... def may_fail(x: int) -> int:
        ...     if x < 0:
        ...         raise ValueError("Negative")
        ...     return x * 2
        ...
        >>> result = may_fail(5)  # Ok(10)
        >>> result = may_fail(-1)  # Err(ValueError("Negative"))
    """

    def wrapper(*args: Any, **kwargs: Any) -> Result[T, Exception]:
        try:
            return Ok(func(*args, **kwargs))
        except Exception as e:
            return Err(e)

    return wrapper


def collect_results(results: list[Result[T, E]]) -> Result[list[T], E]:
    """Collect a list of Results into a Result of list.

    Returns Ok with list of all success values if all Results are Ok.
    Returns the first Err if any Result is Err.

    Args:
        results: List of Result values

    Returns:
        Ok with list of values, or first Err encountered

    Example:
        >>> results = [Ok(1), Ok(2), Ok(3)]
        >>> collect_results(results)  # Ok([1, 2, 3])
        >>>
        >>> results = [Ok(1), Err("fail"), Ok(3)]
        >>> collect_results(results)  # Err("fail")
    """
    values: list[T] = []
    for result in results:
        if result.is_err():
            return result  # type: ignore[return-value]
        values.append(result.unwrap())
    return Ok(values)


def partition_results(results: list[Result[T, E]]) -> tuple[list[T], list[E]]:
    """Partition a list of Results into successes and errors.

    Args:
        results: List of Result values

    Returns:
        Tuple of (success_values, error_values)

    Example:
        >>> results = [Ok(1), Err("a"), Ok(2), Err("b")]
        >>> successes, errors = partition_results(results)
        >>> successes  # [1, 2]
        >>> errors  # ["a", "b"]
    """
    successes: list[T] = []
    errors: list[E] = []
    for result in results:
        if result.is_ok():
            successes.append(result.unwrap())
        else:
            errors.append(result.unwrap_err())
    return successes, errors


def all_ok(results: list[Result[T, E]]) -> bool:
    """Check if all Results in a list are Ok.

    Args:
        results: List of Result values

    Returns:
        True if all are Ok, False if any are Err
    """
    return all(r.is_ok() for r in results)


def any_err(results: list[Result[T, E]]) -> bool:
    """Check if any Results in a list are Err.

    Args:
        results: List of Result values

    Returns:
        True if any are Err, False if all are Ok
    """
    return any(r.is_err() for r in results)


def first_err(results: list[Result[T, E]]) -> Result[None, E]:
    """Get the first error from a list of Results.

    Args:
        results: List of Result values

    Returns:
        First Err found, or Ok(None) if all are Ok
    """
    for result in results:
        if result.is_err():
            return Err(result.unwrap_err())
    return Ok(None)


# Export public API
__all__ = [
    "Ok",
    "Err",
    "Result",
    "wrap_result",
    "collect_results",
    "partition_results",
    "all_ok",
    "any_err",
    "first_err",
]
