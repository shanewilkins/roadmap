"""Test data factory for CLI command tests and general test helpers."""

import itertools
import random
import string


def random_id(prefix="id", length=6):
    return f"{prefix}-" + "".join(
        random.choices(string.ascii_lowercase + string.digits, k=length)
    )


def random_message(length=20):
    return "Test " + "".join(
        random.choices(string.ascii_letters + string.digits + " ", k=length)
    )


class TestDataFactory:
    _id_counter = itertools.count(100)

    @classmethod
    def issue_id(cls):
        return "a1b2c3d4"

    @classmethod
    def milestone_id(cls, variant=None):
        if variant == "other":
            return "f9g8h7i6"
        return "e5f6g7h8"

    @classmethod
    def comment_id(cls):
        return f"comment-{next(cls._id_counter)}"

    @classmethod
    def message(cls, length=20):
        return "Test message"

    @classmethod
    def options(cls, base=None):
        # Example: generate random CLI options
        opts = ["--type", "milestone"] if base == "milestone" else []
        return opts

    @classmethod
    def exit_codes(cls):
        return [0, 1, 2]
