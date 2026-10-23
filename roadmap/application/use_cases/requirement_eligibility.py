"""Shared governed-intent and maintenance eligibility facts."""

from roadmap.domain.aggregates import Issue
from roadmap.domain.requirements import Requirement, RequirementStatus


def is_governed(requirement: Requirement) -> bool:
    return requirement.acceptance_current and requirement.effective_status in {
        RequirementStatus.ACCEPTED,
        RequirementStatus.IN_PROGRESS,
        RequirementStatus.VERIFIED,
    }


def maintenance_justified(issue: Issue) -> bool:
    return "maintenance" in issue.labels and bool(issue.content.strip())
