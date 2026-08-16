"""Valid Domain-to-Domain dependency."""

from roadmap.domain.value import WorkId


def is_present(work_id: WorkId) -> bool:
    """Return whether the fixture ID has content."""
    return bool(work_id.value)
