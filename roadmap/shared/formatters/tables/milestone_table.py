"""Milestone table formatting and display."""

from roadmap.common.output_models import ColumnDef, ColumnType, TableData


class MilestoneTableFormatter:
    """Formats milestones for display and structured output."""

    @staticmethod
    def milestones_to_table_data(
        milestones: list, title: str = "Milestones", description: str = ""
    ) -> TableData:
        """Convert Milestone list to TableData for structured output.

        Args:
            milestones: List of Milestone objects.
            title: Optional table title.
            description: Optional filter description.

        Returns:
            TableData object ready for rendering in any format.
        """
        columns = [
            ColumnDef(
                name="name",
                display_name="Milestone",
                type=ColumnType.STRING,
                width=20,
                display_style="cyan",
                sortable=True,
                filterable=True,
            ),
            ColumnDef(
                name="description",
                display_name="Description",
                type=ColumnType.STRING,
                width=30,
                display_style="white",
                sortable=True,
                filterable=True,
            ),
            ColumnDef(
                name="status",
                display_name="Status",
                type=ColumnType.ENUM,
                width=10,
                display_style="green",
                enum_values=["open", "closed"],
                sortable=True,
                filterable=True,
            ),
            ColumnDef(
                name="due_date",
                display_name="Due Date",
                type=ColumnType.DATE,
                width=12,
                display_style="yellow",
                sortable=True,
                filterable=True,
            ),
            ColumnDef(
                name="progress",
                display_name="Progress",
                type=ColumnType.STRING,
                width=12,
                display_style="blue",
                sortable=False,
                filterable=False,
            ),
        ]

        rows = []
        for milestone in milestones:
            progress = ""
            if (
                hasattr(milestone, "calculated_progress")
                and milestone.calculated_progress
            ):
                progress = f"{milestone.calculated_progress:.0f}%"

            due_date_str = ""
            if hasattr(milestone, "due_date") and milestone.due_date:
                due_date_str = milestone.due_date.strftime("%Y-%m-%d")

            rows.append(
                [
                    milestone.name,
                    milestone.description or "",
                    milestone.status.value
                    if hasattr(milestone.status, "value")
                    else str(milestone.status),
                    due_date_str,
                    progress,
                ]
            )

        return TableData(
            columns=columns,
            rows=rows,
            title=title,
            description=description,
            total_count=len(milestones),
            returned_count=len(milestones),
        )
