"""Factory functions for creating table column definitions (ColumnDef objects).

This module centralizes column definitions to eliminate duplication
across issue_table.py, milestone_table.py, and project_table.py.
"""

from roadmap.common.models import ColumnDef, ColumnType
from roadmap.core.domain import Priority, ProjectStatus, Status


def create_id_column(name: str = "id", width: int = 8) -> ColumnDef:
    """Create an ID column definition.

    Args:
        name: Column data name (default: "id")
        width: Column width (default: 8)

    Returns:
        ColumnDef object for ID column
    """
    return ColumnDef(
        name=name,
        display_name="ID",
        type=ColumnType.STRING,
        width=width,
        display_style="cyan",
        sortable=True,
        filterable=True,
    )


def create_title_column(name: str = "title", width: int = 25) -> ColumnDef:
    """Create a Title column definition.

    Args:
        name: Column data name (default: "title")
        width: Column width (default: 25)

    Returns:
        ColumnDef object for Title column
    """
    return ColumnDef(
        name=name,
        display_name="Title" if name == "title" else "Name",
        type=ColumnType.STRING,
        width=width,
        display_style="white",
        sortable=True,
        filterable=True,
    )


def create_priority_column(width: int = 10) -> ColumnDef:
    """Create a Priority column definition.

    Args:
        width: Column width (default: 10)

    Returns:
        ColumnDef object for Priority column
    """
    return ColumnDef(
        name="priority",
        display_name="Priority",
        type=ColumnType.ENUM,
        width=width,
        display_style="yellow",
        enum_values=[p.value for p in Priority],
        sortable=True,
        filterable=True,
    )


def create_status_column(
    enum_values: list[str] | None = None, width: int = 12, style: str = "green"
) -> ColumnDef:
    """Create a Status column definition.

    Args:
        enum_values: List of possible status values (default: Issue Status enum)
        width: Column width (default: 12)
        style: Display style (default: "green")

    Returns:
        ColumnDef object for Status column
    """
    if enum_values is None:
        enum_values = [s.value for s in Status]

    return ColumnDef(
        name="status",
        display_name="Status",
        type=ColumnType.ENUM,
        width=width,
        display_style=style,
        enum_values=enum_values,
        sortable=True,
        filterable=True,
    )


def create_progress_column(width: int = 10) -> ColumnDef:
    """Create a Progress column definition.

    Args:
        width: Column width (default: 10)

    Returns:
        ColumnDef object for Progress column
    """
    return ColumnDef(
        name="progress",
        display_name="Progress",
        type=ColumnType.STRING,
        width=width,
        display_style="blue",
        sortable=False,
        filterable=False,
    )


def create_assignee_column(width: int = 12) -> ColumnDef:
    """Create an Assignee column definition.

    Args:
        width: Column width (default: 12)

    Returns:
        ColumnDef object for Assignee column
    """
    return ColumnDef(
        name="assignee",
        display_name="Assignee",
        type=ColumnType.STRING,
        width=width,
        display_style="magenta",
        sortable=True,
        filterable=True,
    )


def create_estimate_column(width: int = 10) -> ColumnDef:
    """Create an Estimate column definition.

    Args:
        width: Column width (default: 10)

    Returns:
        ColumnDef object for Estimate column
    """
    return ColumnDef(
        name="estimate",
        display_name="Estimate",
        type=ColumnType.STRING,
        width=width,
        display_style="green",
        sortable=True,
        filterable=False,
    )


def create_milestone_column(width: int = 15) -> ColumnDef:
    """Create a Milestone column definition.

    Args:
        width: Column width (default: 15)

    Returns:
        ColumnDef object for Milestone column
    """
    return ColumnDef(
        name="milestone",
        display_name="Milestone",
        type=ColumnType.STRING,
        width=width,
        display_style="blue",
        sortable=True,
        filterable=True,
    )


def create_owner_column(width: int = 15) -> ColumnDef:
    """Create an Owner/Lead column definition.

    Args:
        width: Column width (default: 15)

    Returns:
        ColumnDef object for Owner column
    """
    return ColumnDef(
        name="owner",
        display_name="Owner",
        type=ColumnType.STRING,
        width=width,
        display_style="magenta",
        sortable=True,
        filterable=True,
    )


def create_description_column(width: int = 30) -> ColumnDef:
    """Create a Description column definition.

    Args:
        width: Column width (default: 30)

    Returns:
        ColumnDef object for Description column
    """
    return ColumnDef(
        name="description",
        display_name="Description",
        type=ColumnType.STRING,
        width=width,
        display_style="white",
        sortable=True,
        filterable=True,
    )


def create_due_date_column(width: int = 12) -> ColumnDef:
    """Create a Due Date column definition.

    Args:
        width: Column width (default: 12)

    Returns:
        ColumnDef object for Due Date column
    """
    return ColumnDef(
        name="due_date",
        display_name="Due Date",
        type=ColumnType.DATE,
        width=width,
        display_style="yellow",
        sortable=True,
        filterable=True,
    )


def create_comment_count_column(width: int = 9) -> ColumnDef:
    """Create a Comments column definition.

    Args:
        width: Column width (default: 9)

    Returns:
        ColumnDef object for Comments column
    """
    return ColumnDef(
        name="comment_count",
        display_name="Comments",
        type=ColumnType.STRING,
        width=width,
        display_style="dim",
        sortable=True,
        filterable=False,
    )


def create_issue_columns() -> list[ColumnDef]:
    """Create all columns for an issue table.

    Returns:
        List of ColumnDef objects for issue display
    """
    return [
        create_id_column(),
        create_title_column(),
        create_priority_column(),
        create_status_column(),
        create_progress_column(),
        create_assignee_column(),
        create_estimate_column(),
        create_milestone_column(),
        create_comment_count_column(),
    ]


def create_milestone_columns() -> list[ColumnDef]:
    """Create all columns for a milestone table.

    Returns:
        List of ColumnDef objects for milestone display
    """
    return [
        create_title_column(name="name", width=20),
        create_description_column(width=30),
        create_status_column(width=10),
        create_due_date_column(width=12),
        create_progress_column(width=12),
        create_estimate_column(width=12),
    ]


def create_project_columns() -> list[ColumnDef]:
    """Create all columns for a project table.

    Returns:
        List of ColumnDef objects for project display
    """
    return [
        create_id_column(),
        create_title_column(),
        create_status_column(
            enum_values=[s.value for s in ProjectStatus],
            style="magenta",
        ),
        create_priority_column(),
        create_owner_column(),
    ]
