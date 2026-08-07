"""Vanilla/Git assignee validator for git sync backend.

Used when the sync backend is vanilla/git, this validator accepts
any assignee without validation since there's no centralized user registry.
"""


class VanillaAssigneeValidator:
    """Validator that accepts any assignee without validation.

    Used for git/vanilla sync backend where there's no centralized
    user registry to validate against.
    """

    def validate(self, assignee: str) -> tuple[bool, str]:
        """Accept any non-empty assignee without validation.

        Args:
            assignee: Username to validate

        Returns:
            (True, "") if assignee is non-empty, otherwise (False, error message)
        """
        if not assignee or not assignee.strip():
            return False, "Assignee cannot be empty"
        return True, ""

    def get_canonical_assignee(self, assignee: str) -> str:
        """Return the assignee as-is (no mapping).

        Args:
            assignee: Input assignee name

        Returns:
            Same assignee name unchanged
        """
        return assignee
