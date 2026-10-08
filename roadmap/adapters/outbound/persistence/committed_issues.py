"""Read canonical issue documents exclusively from a pinned local Git commit."""

import subprocess  # nosec B404
from pathlib import Path
from urllib.parse import quote

from roadmap.application.failures import ApplicationFailure, FailureCategory
from roadmap.application.use_cases.github_publish import CommittedIssue, CommittedIssues
from roadmap.domain.aggregates import Issue

from .documents import parse_document_text


class GitCommittedIssues:
    def __init__(self, workspace: Path) -> None:
        self._workspace = workspace.resolve()

    def _git(self, *arguments: str) -> str:
        try:
            result = subprocess.run(  # nosec B603
                ["git", "-C", str(self._workspace.parent), *arguments],
                check=True,
                capture_output=True,
                text=True,
                timeout=15,
            )
            return result.stdout
        except (OSError, subprocess.SubprocessError) as error:
            raise ApplicationFailure(
                FailureCategory.STORAGE_UNAVAILABLE,
                "Cannot read committed Roadmap issues from Git HEAD",
            ) from error

    def snapshot(self) -> CommittedIssues:
        try:
            root = Path(self._git("rev-parse", "--show-toplevel").strip())
            prefix = self._workspace.relative_to(root).as_posix()
            revision = self._git("rev-parse", "--verify", "HEAD^{commit}").strip()
            entries = self._git(
                "ls-tree",
                "-r",
                "-z",
                revision,
                "--",
                f"{prefix}/issues",
                f"{prefix}/archive/issues",
            )
            records: list[CommittedIssue] = []
            for entry in entries.split("\0"):
                if not entry:
                    continue
                metadata, path = entry.split("\t", 1)
                if not path.endswith(".md"):
                    continue
                if not metadata.startswith("100644 blob ") and not metadata.startswith(
                    "100755 blob "
                ):
                    raise ValueError("Canonical issue must be a regular committed file")
                raw = self._git("show", f"{revision}:{path}")
                envelope = parse_document_text(raw, Path(path), "issue")
                assert isinstance(envelope.aggregate, Issue)
                records.append(
                    CommittedIssue(envelope.aggregate, quote(path, safe="/"))
                )
            return CommittedIssues(revision, tuple(records))
        except (ValueError, UnicodeError) as error:
            raise ApplicationFailure(
                FailureCategory.INVALID_REQUEST, str(error)
            ) from error
