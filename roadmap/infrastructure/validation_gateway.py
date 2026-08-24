"""Local parser access for retained validation services."""

from typing import Any


class ValidationGateway:
    """Keep parser construction at the infrastructure boundary."""

    @staticmethod
    def parse_issue_for_validation(file_path: Any) -> Any:
        from roadmap.adapters.persistence.parser import IssueParser

        return IssueParser.parse_issue_file(file_path)

    @staticmethod
    def parse_milestone_for_validation(file_path: Any) -> Any:
        from roadmap.adapters.persistence.parser import MilestoneParser

        return MilestoneParser.parse_milestone_file(file_path)

    @staticmethod
    def get_parser_module() -> Any:
        from roadmap.adapters.persistence import parser

        return parser
