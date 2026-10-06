"""Omission and explicit clearing for nullable mutation fields."""


def optional_update[T](
    original: T | None, supplied: T | None, clear: bool = False
) -> T | None:
    if clear:
        return None
    return original if supplied is None else supplied
