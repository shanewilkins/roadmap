"""Safe backup-retention selection."""

import os
from datetime import UTC, datetime, timedelta

from roadmap.infrastructure.maintenance.cleanup import _candidates


def _backup(root, name: str, modified: datetime):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("backup\n", encoding="utf-8")
    timestamp = modified.timestamp()
    os.utime(path, (timestamp, timestamp))
    return path


def test_candidates_are_exact_deterministic_and_non_mutating(tmp_path):
    now = datetime(2026, 8, 24, tzinfo=UTC)
    newest = _backup(tmp_path, "issue-1_3.backup.md", now)
    middle = _backup(tmp_path, "issue-1_2.backup.md", now - timedelta(days=1))
    oldest = _backup(tmp_path, "issue-1_1.backup.md", now - timedelta(days=2))

    selected = _candidates(tmp_path, keep=1, days=None, now=now)

    assert selected == tuple(sorted((middle, oldest)))
    assert newest.exists() and middle.exists() and oldest.exists()


def test_age_rule_can_select_even_a_retained_recent_slot(tmp_path):
    now = datetime(2026, 8, 24, tzinfo=UTC)
    old = _backup(tmp_path, "issue-1_1.backup.md", now - timedelta(days=31))

    assert _candidates(tmp_path, keep=10, days=30, now=now) == (old,)
