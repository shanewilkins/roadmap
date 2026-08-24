"""Local-only Git subprocess boundary."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from roadmap.application.contracts import GitSnapshot
from roadmap.application.failures import ApplicationFailure, FailureCategory

_BRANCH = re.compile(r"[a-z0-9][a-z0-9._/-]*\Z")


def _changed_paths(porcelain: str) -> tuple[str, ...]:
    """Extract paths from NUL-delimited porcelain without decoding shell text."""
    records = porcelain.split("\0")
    paths: list[str] = []
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        if len(record) < 4 or record[2] != " ":
            continue
        paths.append(record[3:])
        if record[0] in "RC" or record[1] in "RC":
            if index < len(records) and records[index]:
                paths.append(records[index])
                index += 1
    return tuple(sorted(set(paths)))


class SubprocessLocalGit:
    """Run a fixed set of local Git commands without shell or network access."""

    def __init__(self, repository: Path, *, timeout: float = 10.0) -> None:
        self._repository = repository.resolve()
        self._timeout = timeout

    def inspect_local_git(self) -> GitSnapshot:
        repository = self._run(("rev-parse", "--is-inside-work-tree"), check=False)
        if repository.returncode != 0 or repository.stdout.strip() != "true":
            return GitSnapshot(False, None, None, ())
        branch_result = self._run(
            ("symbolic-ref", "--quiet", "--short", "HEAD"), check=False
        )
        head_result = self._run(("rev-parse", "--verify", "HEAD"), check=False)
        status = self._run(("status", "--porcelain=v1", "-z", "--untracked-files=all"))
        changed = _changed_paths(status.stdout)
        return GitSnapshot(
            True,
            branch_result.stdout.strip() if branch_result.returncode == 0 else None,
            head_result.stdout.strip() if head_result.returncode == 0 else None,
            changed,
        )

    def create_branch(self, name: str, *, checkout: bool) -> None:
        if (
            not _BRANCH.fullmatch(name)
            or ".." in name
            or "@{" in name
            or name.endswith((".", "/"))
        ):
            raise ApplicationFailure(
                FailureCategory.INVALID_REQUEST, "Generated Git branch name is unsafe"
            )
        collision = self._run(
            ("show-ref", "--verify", "--quiet", f"refs/heads/{name}"), check=False
        )
        if collision.returncode == 0:
            raise ApplicationFailure(
                FailureCategory.CONFLICT, f"Git branch already exists: {name}"
            )
        self._run(("switch", "-c", name) if checkout else ("branch", name))

    def user_identity(self) -> tuple[str | None, str | None]:
        name = self._run(("config", "--get", "user.name"), check=False)
        email = self._run(("config", "--get", "user.email"), check=False)
        return (
            name.stdout.strip() if name.returncode == 0 else None,
            email.stdout.strip() if email.returncode == 0 else None,
        )

    def _run(
        self, arguments: tuple[str, ...], *, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        if any(not value or "\0" in value for value in arguments):
            raise ApplicationFailure(
                FailureCategory.INVALID_REQUEST, "Invalid Git command argument"
            )
        environment = os.environ.copy()
        environment.update(
            {"GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0", "LC_ALL": "C"}
        )
        try:
            result = subprocess.run(
                ("git", "-C", str(self._repository), *arguments),
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
                env=environment,
            )
        except FileNotFoundError as error:
            raise ApplicationFailure(
                FailureCategory.STORAGE_UNAVAILABLE, "Git executable is not available"
            ) from error
        except subprocess.TimeoutExpired as error:
            raise ApplicationFailure(
                FailureCategory.STORAGE_UNAVAILABLE,
                f"Local Git command timed out after {self._timeout:g} seconds",
            ) from error
        if check and result.returncode != 0:
            detail = (
                result.stderr.strip().splitlines()[-1]
                if result.stderr.strip()
                else "command failed"
            )
            raise ApplicationFailure(
                FailureCategory.STORAGE_UNAVAILABLE,
                f"Local Git operation failed: {detail}",
            )
        return result
