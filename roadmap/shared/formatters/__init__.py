"""
Formatters package - unified formatting utilities.

Organized into focused modules:
- text: Basic text, duration, status, operation formatting
- output: Generic TableData rendering (JSON, CSV, Markdown, plain-text)
- tables: Domain object to TableData conversion (Issue, Milestone, Project)
- export: Issue export with multiple format support
- kanban: Kanban board organization and layout

Use submodule imports for clarity:
  from roadmap.shared.formatters.text import format_table, format_header
  from roadmap.shared.formatters.output import OutputFormatter
  from roadmap.shared.formatters.tables import IssueTableFormatter
  from roadmap.shared.formatters.export import IssueExporter
  from roadmap.shared.formatters.kanban import KanbanOrganizer, KanbanLayout
"""

from .export import IssueExporter
from .kanban import KanbanLayout, KanbanOrganizer
from .tables import IssueTableFormatter, MilestoneTableFormatter, ProjectTableFormatter

__all__ = [
    "IssueExporter",
    "IssueTableFormatter",
    "MilestoneTableFormatter",
    "ProjectTableFormatter",
    "KanbanOrganizer",
    "KanbanLayout",
]
