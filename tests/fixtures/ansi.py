"""ANSI-output helpers shared by CLI integration tests."""

import re

_ANSI_ESCAPE = re.compile(
    "|".join(
        (
            r"\x1b\[[0-9;]*[mGKHJABCDEFnuslh]",
            r"\x1b\[[0-9;]*[ABCDEFGHJKSTmhl]",
            r"\x1b\([AB]",
            r"\x1b\].*?\x07",
            r"\x1b\].*?\x1b\\",
            r"\x1b[=>]",
            r"\x1b[HJ]",
            r"\x1b7\x1b8",
        )
    )
)


def strip_ansi(text: str | bytes) -> str:
    """Remove ANSI escape sequences and non-whitespace control characters."""
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="replace")
    clean = _ANSI_ESCAPE.sub("", text)
    return re.sub(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]", "", clean)


def normalize_whitespace(text: str) -> str:
    """Normalize spaces and blank lines for stable CLI assertions."""
    text = re.sub(r" +", " ", text)
    text = re.sub(r"\n+", "\n", text)
    return "\n".join(line.strip() for line in text.splitlines()).strip()


def clean_cli_output(text: str) -> str:
    """Return ANSI-free CLI output with normalized whitespace."""
    return normalize_whitespace(strip_ansi(text))
