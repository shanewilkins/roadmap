"""Formatters package - unified formatting utilities.

Organized into focused modules:
- text: Basic text, duration, status, operation formatting
- output: Generic TableData rendering (JSON, CSV, Markdown, plain-text)
- tables: Domain object to TableData conversion (Issue, Milestone, Project)
- kanban: Kanban board organization and layout

Use submodule imports for clarity:
  from roadmap.common.formatters.text import format_table, format_header
  from roadmap.common.formatters.output import OutputFormatter
  from roadmap.common.formatters.tables import IssueTableFormatter
  from roadmap.common.formatters.kanban import KanbanOrganizer, KanbanLayout
"""

from .kanban import KanbanLayout, KanbanOrganizer
from .tables import IssueTableFormatter, MilestoneTableFormatter, ProjectTableFormatter

__all__ = [
    "IssueTableFormatter",
    "MilestoneTableFormatter",
    "ProjectTableFormatter",
    "KanbanOrganizer",
    "KanbanLayout",
]
